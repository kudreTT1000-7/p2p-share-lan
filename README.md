# P2P Share LAN

Локальный распределённый менеджер файлов: обмен **без интернета**, только LAN.

Соседи находятся по **UDP broadcast**, файлы уходят по **TCP чанками**, целостность проверяется **SHA-256**. Интерфейс — **PyQt6**: список онлайн-пользователей, drag-and-drop, progress bar.

Учебный командный проект. Каркас модульный: сеть, ядро и UI живут в разных пакетах, чтобы вести параллельные Git-ветки без постоянных конфликтов.

## Стек

- Python 3.10+
- PyQt6
- стандартная библиотека: `socket`, `hashlib`, `json`, `logging`

## Архитектура

```
p2pshare/
  app/          фасад ApplicationController (единственная связь UI ↔ сеть)
  network/      UDP-discovery, TCP-чанки, протокол, реестр пиров
  core/         SHA-256, манифест, ошибки, сессия и resume
  ui/           главное окно, список пиров, drop-зона, прогресс
main.py         запуск
TZ.md           техническое задание
GIT_GUIDE.md    как сделать «красивую» историю веток на GitHub
```

Сейчас сокеты — **осознанные заглушки** с рабочими импортами и контрактами классов. GUI запускается. Хеширование и модели уже рабочие (покрыты тестами).

## Установка

```powershell
cd C:\Users\user\Documents\Offline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

Из корня репозитория:

```powershell
python main.py
```

или:

```powershell
python -m p2pshare
```

Имя в сети и порты:

```powershell
$env:P2P_DISPLAY_NAME = "Bomba"
$env:P2P_UDP_PORT = "37020"
$env:P2P_TCP_PORT = "37021"
python main.py
```

Два клиента на одном ПК — разные порты у второго экземпляра.

Каталог загрузок по умолчанию: `received_files/` (создаётся автоматически).

## Тесты

```powershell
pytest -q
```

## Что делать команде дальше

1. Прочитать [TZ.md](TZ.md) — критерии приёмки A1–A10.
2. Прочитать [GIT_GUIDE.md](GIT_GUIDE.md) — первый коммит, ветки, merge `--no-ff`.
3. Студент сети реализует `UDPDiscoveryService.start/poll` и `TCPChunkTransfer.send_file/receive_file`.
4. Студент UI не трогает сокеты: только `p2pshare/ui/` и сигналы контроллера.

## Лицензия

Учебный проект, все права у команды-автора.
