# Simsovet — AGENTS.md

## Stack
- Python 3 + PySide6 (Qt for Python, WebEngine)
- SQLite3 for browsing history (`data/simsovet.db`)
- Single-file app: `main.py`

## Commands
```bash
./install.sh          # first-time: apt+pip deps into .venv
./main.sh             # run the app (activates .venv)
```

## Project structure
```
main.py        # single-file PySide6 QWebEngineView browser
install.sh     # bootstrap: system deps, venv, pip install PySide6
main.sh        # launcher: cd to project root, source .venv, python main.py
data/          # gitignored — runtime-only (SQLite DB + Qt browser profile)
```

## Key points
- Always launch via `main.sh` (it sets the correct cwd so `data/` resolves).
- `data/` is gitignored; deleting it is safe — SQLite DB and Qt profile are recreated on launch.
- No tests, no linter, no typechecker, no CI. No test/fmt/lint commands exist.
- `.gitattributes` enforces LF line endings (`* text=auto eol=lf`).
- Icon `favicon.png` lives at project root, loaded if present.
- Windows: sets a custom AppUserModelID via ctypes.
- Sidebar quick-buttons hardcode: Alice (Yandex), Gemini, DeepSeek.
- History is SQLite-backed, WAL journal mode, last 3 entries shown in sidebar.
