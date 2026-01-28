# Game Screen Region Translator (EN→RU)

Инструмент для перевода текста с игровых экранов (особенно пиксельных шрифтов, как в Minecraft) с помощью OCR и DeepL/LibreTranslate.

## Возможности

- ✅ Глобальный хоткей (по умолчанию `CTRL+SHIFT+T`)
- ✅ Выделение области на экране мышью
- ✅ OCR для пиксельного текста с multi-pass обработкой
- ✅ Перевод EN→RU через DeepL или LibreTranslate
- ✅ Прозрачный оверлей с результатом поверх игры
- ✅ Click-through режим (оверлей не блокирует клики в игре)
- ✅ Кеширование переводов
- ✅ Поддержка multi-monitor и DPI scaling
- ✅ Fallback между backend'ами захвата (MSS → DXcam)

## Требования

- **Windows 7+** (требуется WinAPI для RegisterHotKey)
- **Python 3.9+**
- **Tesseract OCR** (требует отдельной установки)

### Установка Tesseract на Windows

1. Скачай установщик: https://github.com/UB-Mannheim/tesseract/wiki
2. Запусти `tesseract-ocr-w64-setup-v5.x.x.exe`
3. При установке выбери **"Additional script data"** для языков
4. По умолчанию устанавливается в `C:\Program Files\Tesseract-OCR`

Скрипт автоматически найдёт Tesseract. Если не найдёт, добавь строку в `.env`:
```
PYTESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Быстрый старт

### 1. Клонируй и установи зависимости

```bash
cd game_screen_region_translator
python -m venv venv

# На Windows:
venv\Scripts\activate

# На Linux/Mac (если захочешь портировать):
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Настрой API ключи

Создай файл `.env` в корне проекта:

```bash
# DeepL (бесплатный API)
# Зарегистрируйся на https://www.deepl.com/pro#developer
DEEPL_AUTH_KEY=your-api-key-here

# Или используй LibreTranslate (бесплатный сервис, но медленнее)
# Измени в config.json "provider": "libre"
```

**Рекомендация**: используй **DeepL бесплатный API** — точнее и быстрее.

### 3. Запусти из VS Code

```bash
# Терминал в VS Code (Ctrl+`)
python main.py
```

Или прямо из Run Configuration в VS Code (F5).

## Использование

### Основной поток

1. **Запусти** `python main.py` — приложение фонится, иконка в трее (если есть)
2. **Нажми хоткей** `CTRL+SHIFT+T` (можно изменить в config.json)
3. **На экране появится полупрозрачный слой** — выделяешь область мышью
4. **Отпусти ЛКМ** — скрипт делает скриншот, запускает OCR+перевод
5. **Результат появляется поверх игры** в том же месте, где был оригинал
6. **Закрытие**:
   - Нажми `CTRL+SHIFT+ESC` (или другой хоткей close)
   - Или нажми `ESC`
   - Или повторный хоткей toggle

### Управление из трея

- Иконка в системном трее (если есть)
- ПКМ → "Change hotkey…" — смена хоткея
- ПКМ → "Click-through mode" — toggle для прозрачности оверлея мыши
- ПКМ → "Quit" — выход

### Горячие клавиши

| Комбинация | Действие |
|-----------|----------|
| `CTRL+SHIFT+T` | Вкл/выкл режим выделения (или отмена, или новое выделение) |
| `CTRL+SHIFT+ESC` | Закрыть оверлей результата |
| `ESC` (во время выделения) | Отменить выделение |
| `ESC` (во время результата) | Закрыть результат |

## Конфигурация

### config.json — главные параметры

```json
{
  "hotkeys": {
    "toggle": "CTRL+SHIFT+T",      // Хоткей включения режима выделения
    "close": "CTRL+SHIFT+ESC"       // Хоткей закрытия оверлея
  },
  "overlay": {
    "click_through": true,          // Оверлей прозрачен для мыши (не блокирует клики)
    "background_dimming": 0.55,     // 0.0-1.0, затемнение фона оверлея
    "base_font_size": 22,           // Базовый размер текста в оверлее
    "min_font_size": 12             // Минимальный (если не влезает)
  },
  "capture": {
    "backend_order": ["mss", "dxcam"],  // Порядок попыток захвата
    "black_threshold_mean": 8.0         // Порог для определения "чёрного" кадра
  },
  "ocr": {
    "scale_factor": 3,              // Увеличение перед OCR (3-4 хорошо для пиксельных шрифтов)
    "threshold_mode": "otsu",       // "otsu" или "adaptive"
    "try_shadow_removal": true,     // Пытаться убрать тень текста
    "min_text_length": 3            // Минимум символов в результате
  },
  "translation": {
    "provider": "deepl",            // "deepl" или "libre"
    "cache_ttl_sec": 90,            // Кеш перевода на 90 сек
    "max_chars_per_chunk": 2500     // Макс символов на 1 запрос к API
  }
}
```

### Смена провайдера перевода

**DeepL** (рекомендуется):
```json
"provider": "deepl"
```
Требует: `DEEPL_AUTH_KEY` в `.env`

**LibreTranslate** (бесплатный, медленнее):
```json
"provider": "libre"
```
Использует публичный сервис или твой свой (если запустил локально).

## Решение проблем

### ❌ "OCR returned empty text" или OCR выдаёт мусор

**Причины**:
- Шрифт слишком мелкий (Minecraft имеет очень маленький шрифт)
- Слабый контраст
- Фон с градиентом / эффекты

**Решение**:
1. Увеличь `scale_factor` в config.json: `4` или даже `5`
2. Попробуй другой `threshold_mode`: `"adaptive"` вместо `"otsu"`
3. Включи `try_shadow_removal: true`
4. Увеличь область выделения (легче читать)

### ❌ "All capture backends failed" или "near-black frame"

**Причины**:
- Игра в exclusive fullscreen (захват не работает)
- Драйвер видеокарты не поддерживает DXcam

**Решение**:
1. **Переведи игру в borderless windowed mode** ← самое важное!
2. Попробуй отключить backend DXcam в config.json: `"backend_order": ["mss"]`
3. Или наоборот, если MSS медленный: `"backend_order": ["dxcam"]`

### ❌ "Нет сети" или "Неверный ключ API"

**Причины**:
- DeepL ключ неверный или закончился лимит
- Интернет отключён

**Решение**:
1. Проверь ключ в `.env`: `DEEPL_AUTH_KEY`
2. На https://www.deepl.com/account посмотри остаток символов
3. Переключись на LibreTranslate (бесплатный, но медленнее)

### ❌ Хоткей не работает

**Причины**:
- Хоткей зарезервирован другой программой (Discord, OBS, Steam и т.д.)
- Неправильный синтаксис в config.json

**Решение**:
1. Смени на другую комбинацию в config.json, например `"CTRL+ALT+T"`
2. Проверь синтаксис: `"CTRL+SHIFT+T"` (без пробелов внутри)
3. Перезапусти скрипт

### ❌ DPI mismatch — выделение не совпадает с захватом

**Причины**:
- Система использует масштабирование (125%, 150%)
- Мониторы с разным DPI

**Решение**:
- Скрипт **уже это обрабатывает** через `enable_per_monitor_dpi_awareness()`
- Если всё равно не совпадает, проверь логи: `logs/app.log`

### ❌ Оверлей заблокировал управление игрой

**Решение**:
1. Убедись, что в config.json стоит `"click_through": true`
2. Если не помогает, нажми глобальный хоткей close или ESC

### ❌ "PYTESSERACT_PATH not found"

**Решение**:
1. Убедись, что Tesseract установлен
2. Добавь в `.env`:
```
PYTESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```
3. Замени путь на свой (если установил в другое место)

## Логи и отладка

Логи пишутся в **logs/app.log** и в консоль VS Code.

**Порядок на экране**:
```
INFO | Hotkey -> enter selection          (ты нажал хоткей)
INFO | State=SELECTION                    (режим выделения включен)
INFO | Selection -> rect_logical=...      (ты выделил область)
INFO | Capture backend selected: mss      (захват началась)
INFO | OCR -> start                       (OCR началась)
INFO | OCR -> best_pass=A_upscale_otsu    (выбран best pass)
INFO | Translate -> start                 (перевод началась)
INFO | Translate -> ok text_len=45        (перевод готов)
INFO | State=RESULT                       (оверлей показан)
```

Если ошибка — лог покажет `ERROR` с деталями.

## Упаковка в EXE (опционально)

Если хочешь распространять как standalone EXE:

```bash
pip install pyinstaller

pyinstaller --onefile --windowed --add-data "config.json:.;" main.py
```

Результат в `dist/main.exe`.

## Архитектура проекта

```
app/
  controller.py       — главный state machine (IDLE → SELECTION → PROCESSING → RESULT)
  hotkey.py          — WinAPI RegisterHotKey + Qt native event filter
  
  capture/
    capture_manager.py   — fallback logic (MSS → DXcam)
    mss_backend.py       — обычный захват
    dxcam_backend.py     — захват через Desktop Duplication API
    
  ocr/
    pipeline.py          — 4 pass'а (upscale+otsu, maxchannel, shadow removal, adaptive)
    
  translate/
    base.py              — интерфейс TranslatorProvider
    cache.py             — TTL кеш переводов
    deepl_provider.py    — DeepL с ретраями
    libre_provider.py    — LibreTranslate
    
  ui/
    selection_overlay.py — fullscreen layer для выделения
    result_overlay.py    — transparent overlay с результатом
    hotkey_dialog.py     — диалог смены хоткея
    tray.py             — иконка в трее + меню
    worker.py           — thread для OCR+перевод (не блокирует UI)
```

## Известные ограничения

- ❌ Exclusive fullscreen игр не поддерживается (используй borderless windowed)
- ❌ OCR для мелкого пиксельного текста <10px не гарантирован
- ⚠️ DeepL есть лимит на бесплатный API (~500K символов/месяц)
- ⚠️ Зависит от качества интернета (перевод может быть медленным на 3G)

## Лицензия

MIT (используй как хочешь)

---

**Вопросы?** Смотри логи (`logs/app.log`) или добавь больше debug-инфо в config.json (тогда выставь `"level": "DEBUG"`).

**Enjoy! 🎮🇷🇺**
