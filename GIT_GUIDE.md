# Инструкция по Git для команды

Цель: на GitHub видна **настоящая** история: каркас в `main`, две feature-ветки, **слияния с merge-commit** (ромбики в Network graph). Преподаватель часто смотрит не только код, но и вклад веток.

Делайте команды **из корня проекта**. Ниже — PowerShell (Windows). На Git Bash / Linux замените `type` на `cat`, активацию venv — на `source .venv/bin/activate`.

---

## 0. Один раз: аккаунты и правило «не пушить в main напрямую»

1. У всех есть аккаунт GitHub, репозиторий **один на команду**.
2. После первого push включите в GitHub: **Settings → Branches → Add branch protection rule** для `main`:
   - Require a pull request before merging (если преподаватель это любит), **или** хотя бы договоритесь в чате не коммитить в `main` локально кроме стартового.
3. Сообщения коммитов — на русском или английском, но **одинаково** и по делу (`feat:`, `fix:`, `docs:` — плюс для дотошного проверяющего).

Проверка, что git видит вас (не меняйте чужой `user.name` без нужды):

```powershell
git config user.name
git config user.email
```

---

## 1. Первый коммит каркаса в `main`

Делает **один** человек (тимлид), остальные потом клонируют.

```powershell
cd C:\Users\user\Documents\Offline

git init
git checkout -b main

git add TZ.md README.md GIT_GUIDE.md requirements.txt .gitignore main.py p2pshare tests
git status
```

Убедитесь, что в индекс **не** попали `.venv/`, `__pycache__/`, секреты.

```powershell
git commit -m "feat: каркас P2P Share LAN (network, core, ui) и документация ТЗ"
```

Создайте пустой репозиторий на GitHub (без README — он уже есть локально), затем:

```powershell
git remote add origin https://github.com/ORG_OR_USER/REPO.git
git push -u origin main
```

Остальные:

```powershell
git clone https://github.com/ORG_OR_USER/REPO.git
cd REPO
```

---

## 2. Студент 1 — ветка `feature-network`

**Задача:** сокеты UDP/TCP, чанки, ACK, обрыв соединения. Трогает в основном `p2pshare/network/`.

```powershell
git checkout main
git pull origin main
git checkout -b feature-network
```

Пишет код (пример: реализовать отправку HELLO). После правок:

```powershell
git add p2pshare/network
git add tests
git status
git commit -m "feat(network): UDP-discovery соседей и каркас TCP-чанков"
git push -u origin feature-network
```

Если работы несколько вечеров — **несколько коммитов**, не один гигантский:

```powershell
git add p2pshare/network/transfer.py p2pshare/core/session.py
git commit -m "feat(network): передача файла чанками и resume offset"
git push
```

На GitHub: **Pull request** `feature-network` → `main`. Пока **не мержить**, если параллельно идёт UI (или мержить можно — UI ветка стартовала от того же `main`, см. §4).

---

## 3. Студент 2 — ветка `feature-ui`

**Важно:** ветку создавать от `main`, **не** от `feature-network`. Иначе история склеится в одну линию и пропадёт картинка двух независимых линий.

```powershell
git checkout main
git pull origin main
git checkout -b feature-ui
```

Работа только в `p2pshare/ui/` (и при необходимости подписи в README). Пример коммита:

```powershell
git add p2pshare/ui
git commit -m "feat(ui): список пиров, drag-and-drop и progress bar"
git push -u origin feature-ui
```

Второй коммит (полировка):

```powershell
git add p2pshare/ui/styles.py p2pshare/ui/main_window.py
git commit -m "fix(ui): статусы ошибок обрыва сети в прогрессе"
git push
```

Pull request `feature-ui` → `main`.

---

## 4. Правильное слияние, чтобы граф был «с ромбами»

### Почему не `git merge` по умолчанию / не squash

- **fast-forward** — ветка просто наезжает на `main`, на графике **нет развилки**.
- **squash** — все коммиты ветки схлопываются в один, вклад по файлам виден, но **история веток бедная**.

Нужно: **merge commit** (`--no-ff`) или кнопка GitHub **Create a merge commit** (не Squash, не Rebase).

### 4.1. Через GitHub (предпочтительно)

1. Откройте PR `feature-network` → `main`.
2. Merge: выберите **Create a merge commit** → Confirm.
3. То же для `feature-ui`.

Если вторая ветка отстала от `main` после первого merge:

на GitHub: **Update branch** (merge main into feature-ui) — появится ещё один merge-commit, это нормально и даже хорошо.

Либо локально у студента 2:

```powershell
git checkout feature-ui
git fetch origin
git merge --no-ff origin/main
# разрешить конфликты, если есть (см. §5)
git push
```

Потом merge PR в `main`.

### 4.2. Через терминал (если без PR)

Тимлид:

```powershell
git checkout main
git pull origin main

git merge --no-ff feature-network -m "merge: сеть UDP/TCP в main"
git push origin main

git merge --no-ff feature-ui -m "merge: интерфейс PyQt6 в main"
git push origin main
```

Флаг `--no-ff` обязателен.

### 4.3. Как проверить, что преподаватель увидит развилки

```powershell
git log --oneline --graph --decorate --all
```

Ожидаемый вид (схематично):

```
*   merge: интерфейс PyQt6 в main
|\
| * feat(ui): ...
| * feat(ui): ...
* |   merge: сеть UDP/TCP в main
|\|
| * feat(network): ...
| * feat(network): ...
|/
* feat: каркас P2P Share LAN ...
```

На GitHub: **Insights → Network**.

---

## 5. Конфликты (если всё же пересеклись)

Типичное место — `p2pshare/app/controller.py` (его лучше почти не менять в feature-ветках).

```powershell
git status
# открыть файлы с <<<<<<<
# оставить обе правки осмысленно, удалить маркеры
git add путь/к/файлу
git commit -m "merge: разрешён конфликт в controller"
```

Не делайте `git push --force` в `main` и в общие feature-ветки, если с ними уже работает второй человек.

---

## 6. Мини-роль третьего студента (по желанию)

```powershell
git checkout main
git pull
git checkout -b feature-core
# тесты, доработка resume в core/session.py
git add p2pshare/core tests
git commit -m "feat(core): запись чанков на диск и проверка SHA-256 после сборки"
git push -u origin feature-core
```

Слияние так же: `--no-ff` / merge commit.

---

## 7. Чеклист перед сдачей

- [ ] В `main` есть начальный коммит каркаса.
- [ ] Есть ветки `feature-network` и `feature-ui` (не удаляйте их сразу после merge — пусть поживут на GitHub до защиты).
- [ ] В `git log --graph --all` видны merge-коммиты.
- [ ] Сообщения коммитов понятные, не `fix`, `asdf`, `update`.
- [ ] В репозитории нет `.venv`, паролей, огромных бинарников.
- [ ] README открывается на GitHub, ТЗ лежит в `TZ.md`.

---

## 8. Чего не делать

| Нельзя | Почему |
|---|---|
| Все коммиты сразу в `main` | Нет веток — нет баллов за процесс |
| Одна ветка `dev`, куда пишут все | История плоская, конфликты постоянные |
| `git merge` без `--no-ff`, если Git сделал fast-forward | Нет узла слияния |
| Squash merge всех PR | Ветки исчезают из графа |
| Переписывать историю `rebase -i` уже запушенных веток | Расхождение у одногруппников |
| Копировать чужие коммиты одним архивом без git | Преподаватель смотрит даты и авторов |
