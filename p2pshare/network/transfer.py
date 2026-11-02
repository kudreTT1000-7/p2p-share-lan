"""TCP-передача файла чанками 64 КиБ: JSON-метапакет, сырые куски, SHA-256."""

from __future__ import annotations

import logging
import socket
import threading
import uuid
from pathlib import Path
from typing import Callable

from p2pshare.core.config import AppConfig
from p2pshare.core.errors import IntegrityError, NetworkInterruptedError, TransferError
from p2pshare.core.hashing import SHA256Hasher
from p2pshare.core.integrity import IntegrityVerifier
from p2pshare.core.models import FileManifest, PeerInfo, TransferProgress, TransferStatus
from p2pshare.core.session import TransferSession
from p2pshare.network.protocol import Message, MessageType, ProtocolCodec, recv_exact

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[TransferProgress], None]
CONNECT_TIMEOUT_SEC = 12.0
IO_TIMEOUT_SEC = 30.0


def _unique_dest(directory: Path, file_name: str) -> Path:
    safe = Path(file_name).name or "unnamed"
    dest = directory / safe
    if not dest.exists():
        return dest
    stem = Path(safe).stem
    suffix = Path(safe).suffix
    index = 1
    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


class TCPChunkTransfer:
    def __init__(
        self,
        config: AppConfig,
        codec: ProtocolCodec | None = None,
        hasher: SHA256Hasher | None = None,
        verifier: IntegrityVerifier | None = None,
    ) -> None:
        self.config = config
        self.codec = codec or ProtocolCodec()
        self.hasher = hasher or SHA256Hasher()
        self.verifier = verifier or IntegrityVerifier(self.hasher)
        self._on_progress: ProgressCallback | None = None
        self._listening = False
        self._server_sock: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        self._on_progress = callback

    def start_server(self) -> None:
        self.config.ensure_directories()
        with self._lock:
            if self._listening:
                return
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((self.config.bind_host, self.config.tcp_port))
                sock.listen(16)
            except OSError as exc:
                sock.close()
                raise TransferError(
                    f"TCP {self.config.tcp_port} занят или недоступен: {exc}"
                ) from exc
            sock.settimeout(0.5)
            bound = sock.getsockname()[1]
            if self.config.tcp_port == 0:
                self.config.tcp_port = bound
            self._server_sock = sock
            self._listening = True
            self._accept_thread = threading.Thread(
                target=self._accept_loop,
                name="tcp-accept",
                daemon=True,
            )
            self._accept_thread.start()
        logger.info("TCP-сервер %s:%s", self.config.bind_host, self.config.tcp_port)

    def stop_server(self) -> None:
        with self._lock:
            self._listening = False
            sock = self._server_sock
            self._server_sock = None
            thread = self._accept_thread
            self._accept_thread = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        logger.info("TCP-сервер остановлен")

    def send_file(
        self,
        path: Path,
        peer: PeerInfo,
        transfer_id: str,
    ) -> TransferProgress:
        if not path.is_file():
            raise TransferError(f"Файл не найден: {path}")
        size = path.stat().st_size
        chunk_size = self.config.chunk_size
        chunk_count = (size + chunk_size - 1) // chunk_size if size else 0
        manifest = FileManifest(
            file_name=path.name,
            size_bytes=size,
            sha256="",
            chunk_size=chunk_size,
            chunk_count=chunk_count,
            source_path=path,
        )
        progress = TransferProgress(
            transfer_id=transfer_id,
            peer=peer,
            manifest=manifest,
            status=TransferStatus.CONNECTING,
            local_path=path,
        )
        worker = threading.Thread(
            target=self._send_worker,
            args=(path, peer, progress),
            name=f"tcp-send-{transfer_id[:8]}",
            daemon=True,
        )
        worker.start()
        return progress

    def receive_file(
        self,
        peer: PeerInfo,
        manifest: FileManifest,
        transfer_id: str,
    ) -> TransferProgress:
        progress = TransferProgress(
            transfer_id=transfer_id,
            peer=peer,
            manifest=manifest,
            status=TransferStatus.FAILED,
            error_message="Приём идёт входящим TCP-сервером, не этим методом",
        )
        self._emit(progress)
        return progress

    def _send_worker(self, path: Path, peer: PeerInfo, progress: TransferProgress) -> None:
        session = TransferSession(progress, self.config.temp_dir)
        sock: socket.socket | None = None
        try:
            progress.status = TransferStatus.VERIFYING
            self._emit(progress)
            built = self.verifier.build_manifest(path, self.config.chunk_size)
            progress.manifest = built
            session.mark_connecting()
            self._emit(progress)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(CONNECT_TIMEOUT_SEC)
            sock.connect((peer.host, peer.tcp_port))
            sock.settimeout(IO_TIMEOUT_SEC)

            session.mark_transferring()
            self._emit(progress)
            self.codec.write_message(
                sock,
                Message(
                    type=MessageType.FILE_OFFER,
                    protocol_version=self.config.protocol_version,
                    payload={
                        "transfer_id": progress.transfer_id,
                        "file_name": built.file_name,
                        "size_bytes": built.size_bytes,
                        "sha256": built.sha256,
                        "chunk_size": built.chunk_size,
                        "chunk_count": built.chunk_count,
                    },
                ),
            )
            reply = self.codec.read_message(sock)
            if reply.type == MessageType.FILE_REJECT:
                raise TransferError(str(reply.payload.get("reason") or "Получатель отказал"))
            if reply.type == MessageType.ERROR:
                raise TransferError(str(reply.payload.get("message") or "Ошибка получателя"))
            if reply.type != MessageType.FILE_ACCEPT:
                raise TransferError(f"Ожидался file_accept, пришло {reply.type.value}")

            with path.open("rb") as handle:
                index = 0
                while True:
                    payload = handle.read(built.chunk_size)
                    if not payload:
                        break
                    self.codec.write_message(
                        sock,
                        Message(
                            type=MessageType.CHUNK,
                            protocol_version=self.config.protocol_version,
                            payload={
                                "index": index,
                                "size": len(payload),
                                "sha256": self.hasher.hash_bytes(payload),
                            },
                        ),
                    )
                    sock.sendall(payload)
                    ack = self.codec.read_message(sock)
                    if ack.type == MessageType.ERROR:
                        raise TransferError(str(ack.payload.get("message") or "Ошибка на чанке"))
                    if ack.type != MessageType.CHUNK_ACK:
                        raise TransferError(f"Ожидался chunk_ack, пришло {ack.type.value}")
                    session.record_chunk(index, payload, write_to_disk=False)
                    index += 1
                    self._emit(progress)

            done = self.codec.read_message(sock)
            if done.type == MessageType.ERROR:
                raise IntegrityError(str(done.payload.get("message") or "Проверка SHA-256 не прошла"))
            if done.type != MessageType.COMPLETE:
                raise TransferError(f"Ожидался complete, пришло {done.type.value}")
            session.mark_completed(path)
            self._emit(progress)
            logger.info("Отправлено %s -> %s sha256=%s", path.name, peer.address, built.sha256[:12])
        except NetworkInterruptedError as exc:
            progress.status = TransferStatus.INTERRUPTED
            progress.error_message = str(exc)
            self._emit(progress)
            logger.warning("Обрыв отправки %s: %s", path, exc)
        except (IntegrityError, TransferError, OSError) as exc:
            session.mark_failed(str(exc))
            self._emit(progress)
            logger.error("Ошибка отправки %s: %s", path, exc)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

    def _accept_loop(self) -> None:
        while self._listening:
            sock = self._server_sock
            if sock is None:
                break
            try:
                client, addr = sock.accept()
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                if self._listening:
                    continue
                break
            worker = threading.Thread(
                target=self._handle_client,
                args=(client, addr),
                name=f"tcp-recv-{addr[0]}",
                daemon=True,
            )
            worker.start()

    def _handle_client(self, sock: socket.socket, addr: tuple) -> None:
        host = addr[0] if addr else "unknown"
        progress: TransferProgress | None = None
        session: TransferSession | None = None
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(IO_TIMEOUT_SEC)
            offer = self.codec.read_message(sock)
            if offer.type != MessageType.FILE_OFFER:
                self.codec.write_message(
                    sock,
                    Message(MessageType.ERROR, {"message": "Ожидался file_offer"}),
                )
                return
            payload = offer.payload
            transfer_id = str(payload.get("transfer_id") or uuid.uuid4())
            manifest = FileManifest(
                file_name=str(payload.get("file_name") or "unnamed"),
                size_bytes=int(payload.get("size_bytes") or 0),
                sha256=str(payload.get("sha256") or ""),
                chunk_size=int(payload.get("chunk_size") or self.config.chunk_size),
                chunk_count=int(payload.get("chunk_count") or 0),
            )
            if manifest.size_bytes < 0 or manifest.chunk_size <= 0:
                raise TransferError("Некорректный манифест файла")
            peer = PeerInfo(
                peer_id=f"tcp:{host}:{addr[1] if len(addr) > 1 else 0}",
                display_name=host,
                host=host,
                tcp_port=self.config.tcp_port,
            )
            progress = TransferProgress(
                transfer_id=transfer_id,
                peer=peer,
                manifest=manifest,
                status=TransferStatus.CONNECTING,
            )
            session = TransferSession(progress, self.config.temp_dir)
            session.reset_staging()
            if manifest.size_bytes == 0:
                session.staging_path.write_bytes(b"")
            session.mark_transferring()
            self._emit(progress)
            self.codec.write_message(
                sock,
                Message(
                    type=MessageType.FILE_ACCEPT,
                    protocol_version=self.config.protocol_version,
                    payload={"transfer_id": transfer_id, "resume_offset": 0},
                ),
            )

            received = 0
            index = 0
            while received < manifest.size_bytes:
                header = self.codec.read_message(sock)
                if header.type == MessageType.ERROR:
                    raise TransferError(str(header.payload.get("message") or "Ошибка отправителя"))
                if header.type != MessageType.CHUNK:
                    raise TransferError(f"Ожидался chunk, пришло {header.type.value}")
                size = int(header.payload.get("size") or 0)
                if size <= 0 or size > manifest.chunk_size:
                    raise TransferError(f"Некорректный размер чанка: {size}")
                if received + size > manifest.size_bytes:
                    raise TransferError("Чанк выходит за размер файла")
                data = recv_exact(sock, size)
                expected_hash = str(header.payload.get("sha256") or "")
                if expected_hash:
                    self.hasher.verify_bytes(data, expected_hash)
                session.record_chunk(index, data, write_to_disk=True)
                received += len(data)
                index += 1
                self.codec.write_message(
                    sock,
                    Message(
                        type=MessageType.CHUNK_ACK,
                        payload={"index": int(header.payload.get("index", index - 1))},
                    ),
                )
                self._emit(progress)

            progress.status = TransferStatus.VERIFYING
            self._emit(progress)
            self.verifier.verify_file(session.staging_path, manifest)
            dest = _unique_dest(self.config.download_dir, manifest.file_name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            session.staging_path.replace(dest)
            session.mark_completed(dest)
            self.codec.write_message(
                sock,
                Message(
                    type=MessageType.COMPLETE,
                    payload={"sha256": manifest.sha256, "path": dest.name},
                ),
            )
            self._emit(progress)
            logger.info("Принят %s от %s -> %s", manifest.file_name, host, dest)
        except NetworkInterruptedError as exc:
            if session is not None:
                progress = session.progress
                progress.status = TransferStatus.INTERRUPTED
                progress.error_message = str(exc)
                self._emit(progress)
            logger.warning("Обрыв приёма от %s: %s", host, exc)
            self._try_error(sock, str(exc))
        except (IntegrityError, TransferError, OSError, ValueError, TypeError) as exc:
            if session is not None:
                session.mark_failed(str(exc))
                self._emit(session.progress)
            logger.error("Ошибка приёма от %s: %s", host, exc)
            self._try_error(sock, str(exc))
        finally:
            try:
                sock.close()
            except OSError:
                pass

    def _try_error(self, sock: socket.socket, message: str) -> None:
        try:
            self.codec.write_message(sock, Message(MessageType.ERROR, {"message": message}))
        except Exception:
            return

    def _emit(self, progress: TransferProgress) -> None:
        callback = self._on_progress
        if callback is None:
            return
        try:
            callback(progress)
        except Exception:
            logger.exception("Ошибка callback прогресса")

    @property
    def is_listening(self) -> bool:
        return self._listening
