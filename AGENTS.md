# Notes for AI agents

- Flask запущен в debug mode с авто-перезагрузкой. После изменения файлов не нужно перезапускать сервер — он сам подхватывает изменения.
- Виртуальное окружение: `venv\Scripts\python.exe`
- Для ручного запуска: `.\venv\Scripts\python.exe app.py`
- Сервер уже запущен на http://127.0.0.1:5000, перезапуск не требуется.
- Коммиты делать только по явной просьбе пользователя. Без команды не коммитить.
- Перед каждым пушем проверять, не засветилась ли конфиденциальная информация (API-ключи, токены, пароли) в файлах или git-истории. Использовать `git log -S` и `git grep` для поиска потенциальных утечек.
- Результаты тестов сохранять в папку `temp/` в корне проекта.

## Структура персонажа (Character)

### Модель данных
- `generators/char_model.py:6` — dataclass `Character`, 73 поля.
- `generators/char_generator.py:1032` — `character_to_dict()` — сериализация в JSON.

### Внешность (appearance)
- `generators/char_appearance.py` — генерация описания внешности.
- `generators/char_data.py` — пулы данных: цвет глаз (137), цвет волос (143), длина волос (149), причёски (151), типы телосложения (213), оттенки кожи (225), стили одежды (467).
- `generators/char_profiles.py:524` — body_sizes (5 уровней), beauty_levels (568, 4 уровня).
- `app.py:171` — секция `=== ВНЕШНОСТЬ ===` в system prompt.

### Психология / Тип личности
- `generators/char_profiles.py:2` — темпераменты (4 типа).
- `generators/char_profiles.py:27` — архетипы (12 Jungian).
- `generators/char_profiles.py:244` — MBTI (16 типов, `mbti_profiles`).
- `generators/char_profiles.py:392` — совместимость архетипов с MBTI.
- `generators/char_profiles.py:496` — социальные стили (3).
- `generators/char_data.py:621` — травмы (14 типов).

### Биография / Предыстория
- `generators/char_bio.py` — генерация биографии.
- `generators/char_profiles.py:424` — возрастные группы и события жизни.

### Характер и черты
- `generators/char_data.py` — пулы: положительные черты, отрицательные черты, хобби, привычки, страхи, мечты, ценности в отношениях, кулинарные/цветовые/музыкальные предпочтения.
- `generators/char_data.py:722-972` — "Spice" поля: жильё, питомец, привычки, красные/зелёные флаги, юмор, запах, здоровье и т.д.

### Стиль общения
- `generators/char_data.py:976` — writing_styles (8 стилей).
- `generators/char_data.py:1269` — lying_tendencies (5 уровней).
- `generators/char_data.py:1210` — skip_factors (триггеры для скипа).
- `generators/char_data.py:1228` — harassment_reactions.

### Приветствия (greetings / openers)
- `generators/char_data.py:1129` — `chat_openers_pool` (~100 фраз, первое сообщение персонажа). Каждый элемент — кортеж `(текст, вес)`. Выбор через `weighted_choice` в `char_generator.py:759`.
- `app.py:438` — `STOCK_ANSWERS` — 8 шаблонов ответов по типу отношения, каждому режиму (`greeting`, `agree`, `disagree`, `question`, `personal`).
- `app.py:556` — детектор приветствий в `fallback_reply()` (слова: привет, здравствуй, хай, хелло, салют, даров, ку, здарова).

### Семантические пулы данных
- `generators/char_data.py` — 1342 строки, все списки для генерации.
- `generators/char_profiles.py` — 709 строк: архетипы, MBTI, возрастные группы, размеры тела, красота, социальные стили.
