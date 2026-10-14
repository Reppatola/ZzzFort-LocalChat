# ZzzFort-LocalChat (Русская версия)

> **Локальный LLM-чат для Windows с SSD-памятью, переключением моделей и без Python-зависимостей.**

Минимальная самодостаточная система локального чата, построенная на **собственной сборке `llama.cpp`** для Windows (MinGW GCC 16.2.0). Без Open WebUI, без сервиса Ollama, без Python для самого чата — только один `.exe`, один HTML-файл и один скрипт-менеджер.

---

## ✨ Возможности

- **Свой `llama-server.exe`** — собран из исходников llama.cpp на MinGW GCC 16.2.0.
- **Переключение моделей в один клик** — выбор из выпадающего списка.
- **Загрузка моделей с SSD** — mmap держит веса на диске. Модель 14B использует всего ~0.7 ГБ private RAM при контексте 2K.
- **KV-кэш в q8_0** — на 40% меньше RAM, чем f16, без потери качества.
- **Ноль зависимостей для чата** — `chat.html` это один файл.
- **Автообнаружение моделей** — сканирует папку `models/`.
- **Полностью офлайн** — без интернета, без телеметрии, без аккаунтов.

---

## 🚀 Быстрый старт

**Требования:** Windows 10/11, ~15 ГБ свободного места на диске под каждую модель.

1. Клонируй репозиторий:
   ```cmd
   git clone https://github.com/Reppatola/ZzzFort-LocalChat.git
Создай рабочее пространство:

cmd
mkdir C:\ZzzFort
mkdir C:\ZzzFort\diskllm\bin
mkdir C:\ZzzFort\diskllm\models
Собери llama-server.exe — см. docs/BUILD.md.

Скачай модели — см. docs/MODELS.md.

Скопируй скрипты:

cmd
copy scripts\* C:\ZzzFort\
copy web\chat.html C:\ZzzFort\
Запусти:

cmd
C:\ZzzFort\start-chat.bat
Чат откроется по адресу http://127.0.0.1:8000/chat.html.

📊 Измеренная производительность
На 32 ГБ RAM / RTX 4060 (только CPU-инференс):

Модель	Контекст	KV тип	Private RAM	Working Set	Скорость (tok/s)
Qwen2.5-Coder 7B	2048	f16	0.38 ГБ	4.26 ГБ	4.78
Qwen2.5-Coder 14B	2048	f16	0.67 ГБ	8.39 ГБ	2.42
Qwen2.5-Coder 14B	8192	f16	1.81 ГБ	9.52 ГБ	2.42
Qwen2.5-Coder 14B	8192	q8_0	1.10 ГБ	8.83 ГБ	2.43
Ключевой вывод: private RAM не зависит от размера модели — только от размера KV-кэша.

🏗️ Архитектура
text
┌─────────────────┐         ┌──────────────────┐
│   chat.html     │ ──POST──│  model-manager   │
│   (браузер)     │         │  (порт 8090)     │
└────────┬────────┘         └────────┬─────────┘
         │                            │
         │                    ┌───────┴────────┐
         │                    │  taskkill +    │
         │                    │  llama-server  │
         │                    │  (порт 8082)   │
         │                    └───────┬────────┘
         │                            │
         └───────/v1/chat/completions─┘
Подробнее — docs/ARCHITECTURE.md.

📁 Структура репозитория
text
ZzzFort-LocalChat/
├── README.md              ← этот файл (русская версия)
├── README.en.md           ← английская версия
├── LICENSE                ← MIT
├── .gitignore
├── docs/
│   ├── BUILD.md
│   ├── MODELS.md
│   ├── ARCHITECTURE.md
│   └── NOTES.md
├── scripts/
│   ├── start-chat.bat
│   ├── model-manager.py
│   └── backup.bat
├── web/
│   └── chat.html
└── patches/
    ├── httplib.cpp.diff
    └── httplib.h.diff
НЕ в репозитории: модели (.gguf), llama-server.exe, DLL, venv, кэши.

🛠️ Сборка из исходников
Самое сложное — скомпилировать llama.cpp на Windows с MinGW GCC 16.2.0. Мы пропатчили два файла в cpp-httplib. Полный рецепт: docs/BUILD.md.

🧪 Проверенные конфигурации
Компонент	Версия
Windows	10.0.19045
MinGW-w64	GCC 16.2.0 (UCRT, POSIX threads)
llama.cpp	коммит df18bee
Python	3.12 (только для model-manager.py)
Модели	Qwen2.5-Coder 7B / 14B, Qwen3 8B
📜 Лицензия
MIT — свободно для всех. См. LICENSE.

🙏 Благодарности
llama.cpp

cpp-httplib

MinGW-w64 от WinLibs

Сообщество локальных LLM