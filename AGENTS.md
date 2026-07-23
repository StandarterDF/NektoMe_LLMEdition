# Notes for AI agents

- Flask запущен в debug mode с авто-перезагрузкой. После изменения файлов не нужно перезапускать сервер — он сам подхватывает изменения.
- Виртуальное окружение: `venv\Scripts\python.exe`
- Сервер уже запущен на http://127.0.0.1:5000, перезапуск не требуется.
- Коммиты делать только по явной команде пользователя. Без команды не коммитить.
- Пример коммит-месседжа (кратко, по-русски): `type: краткое описание`
- Перед каждым пушем проверять, не засветилась ли конфиденциальная информация (API-ключи, токены, пароли) в файлах или git-истории. Использовать `git log -S` и `git grep` для поиска потенциальных утечек.
- Результаты тестов сохранять в папку `temp/` в корне проекта.

## Архитектура проекта

### Файлы

| Файл | Назначение |
|------|------------|
| `app.py` | Flask-сервер (веб-версия) |
| `bot.py` | Telegram-бот (полный аналог) |
| `generators/__init__.py` | Пакет генераторов (пустой) |
| `generators/char_generator.py` | Генератор персонажа (`generate()`) |
| `generators/char_model.py` | Dataclass `Character` (73 поля) + утилиты |
| `generators/char_data.py` | Все пулы данных (1342 строки) |
| `generators/char_profiles.py` | Профили: архетипы, MBTI, возрасты (709 строк) |
| `generators/char_appearance.py` | Генерация описания внешности |
| `generators/char_bio.py` | Генерация биографии |
| `generators/character_generator.py` | Альтернативный генератор (дублирует основной, НЕ ИСПОЛЬЗУЕТСЯ) |
| `requirements.txt` | `flask`, `python-telegram-bot` |

### .env настройки
```
OPENAI_BASE_URL    - URL API (например https://api.deepseek.com/v1)
OPENAI_API_KEY     - ключ API
OPENAI_MODEL       - модель (deepseek-v4-flash)
AGENT_ENABLED       - агент-режим (true/false)
AGENT_MAX_CONSECUTIVE - макс сообщений подряд от AI
AGENT_IDLE_TIMEOUT  - таймаут бездействия
AGENT_RECONNECT_DELAY - задержка переподключения агента
BOT_TOKEN          - токен Telegram бота
```

## app.py — структура

### Основные функции

| Функция | Строка | Описание |
|---------|--------|----------|
| `load_env()` | 54 | Читает .env |
| `call_ai(messages, tools)` | 103 | OpenAI-совместимый API вызов |
| `make_char_json(char)` | 135 | Character → dict (73 поля) |
| `build_system_prompt(char, mode, user_gender)` | 173 | Системный промпт (~180 строк) |
| `build_instruction(mode, user_gender)` | 358 | Инструкция AI (~100 строк) |
| `partner_age_groups(ages)` | 458 | Возрастные метки → age_group |
| `fallback_reply(char, msgs, user_msg)` | 730 | Шаблонный ответ (без AI) |
| `_gender_adapt(text, char_gender)` | 689 | Адаптация рода (жен→муж) |
| `apply_writing_style(text, style)` | 650 | Трансформация стиля письма |
| `_split_long_msg(text)` | 829 | Разбивка длинных сообщений |
| `oversharing_intro(level)` | 635 | Префикс откровенности |
| `_agent_maybe_reconnect()` | 809 | Переподключение агента |

### API endpoints (Flask)

| Route | Метод | Описание |
|-------|-------|----------|
| `/` | GET | index.html |
| `/api/generate` | POST | Создать персонажа |
| `/api/chat` | POST | Отправить сообщение |
| `/api/online` | GET | Онлайн счётчик |
| `/api/agent/poll` | POST | Polling агента |

### Данные в app.py

| Переменная | Строка | Описание |
|------------|--------|----------|
| `char_store` | 132 | dict[token] = {character, messages, topic, agent} |
| `STOCK_ANSWERS` | 562 | 8 attitude-шаблонов × 5 режимов |
| `OVERSHARING_PREFIXES` | 621 | 10 уровней префиксов откровенности |
| `FAREWELL_POOL` | 657 | 19 прощальных фраз |
| `WRITING_STYLE_TRANSFORM` | 643 | 4 стиля трансформации текста |
| `AGENT_TOOLS` | 83 | function-calling инструмент (send_message) |

### System prompt секции
- ХАРАКТЕРИСТИКИ ПЕРСОНАЖА (архетип, темперамент, MBTI)
- ОСНОВНАЯ ИНФОРМАЦИЯ (zodiac, city, profession, и т.д.)
- ВНЕШНОСТЬ (рост, телосложение, глаза, волосы)
- ХАРАКТЕР (черты, привычки, страхи, мечты)
- ПСИХОЛОГИЯ (травма, защита)
- ПОШЛОСТИ И СЕКСУАЛЬНОСТЬ (только в flirt-режиме)
- РОЛЕВАЯ ИГРА (только в rp-режиме)
- ПРЕДПОЧТЕНИЯ (цвета, еда, музыка, фильмы)
- ДЕТАЛИ (жильё, питомец, привычки, флаги и т.д.)
- СТИЛЬ ОБЩЕНИЯ (стиль письма, ложь, юмор)
- УСТАНОВКИ (отношение, настроение, скрытый мотив)
- ПРЕДЫСТОРИЯ
- ПРИМЕРЫ ДИАЛОГА (зависят от режима и rp_ability)

## bot.py — структура

Бот — полный аналог веб-версии, но без агент-режима и онлайн-счётчика.

### Команды
| Команда | Описание |
|---------|----------|
| `/start` | Главное меню с настройками |
| `/next` | Новый персонаж |
| `/card` | Анкета текущего персонажа |
| `/settings` | Меню настроек |
| Любой текст | Общение с персонажем |

### Хендлеры
| Функция | Описание |
|---------|----------|
| `start()` | Приветствие + меню |
| `button_handler()` | Все inline кнопки (настройки, поиск) |
| `generate_character()` | Генерация персонажа (общая для /next и кнопки) |
| `show_card()` | Показ анкеты |
| `handle_message()` | Обработка сообщений в чате |
| `show_main_menu()` | Главное меню с текущими настройками |

### Settings (inline keyboard menu)
- **Пол собеседника**: male / female / any
- **Возраст**: до 17 / 18-21 / 22-25 / 26-35 / 36+ / Любой
- **Режим**: chat / flirt / rp
- Настройки хранятся в `user_data[user_id]['settings']`

### Состояние пользователя
```python
user_data[uid] = {
    'char': None | dict,       # char_data от make_char_json()
    'messages': [],            # [{role, content}, ...]
    'settings': { ... },
    'char_count': int,
}
```

## Процесс генерации персонажа

1. `gen_char(seed, gender, age_group, topic)` → Character (dataclass)
2. `make_char_json(char)` → dict (73 поля)
3. Устанавливается `user_gender` для адаптации рода
4. Инициализируется `messages`: [time_info, opener1, opener2, ...]
5. Opener берётся из `char_data['chat_opener']`, может содержать `[NEXT]` для разделения
6. Сохраняется в `user_data[uid]`

## Процесс чата

1. Пользователь пишет сообщение
2. Сообщение добавляется в `messages` с ролью `user`
3. Строится `build_system_prompt(char_data, mode, user_gender)`
4. Строится `build_instruction(mode, user_gender)`
5. Если `AI_ENABLED`: вызов `call_ai(messages)` (OpenAI-compatible)
6. Если AI вернул None или AI выключен: `fallback_reply(char_data, msgs, user_msg)`
7. Применяется `apply_writing_style(reply, style)`
8. Разбивается по `[NEXT]` на несколько сообщений
9. Каждая часть — отдельное сообщение в Telegram
10. Сохраняется в `messages` с ролью `assistant`

### Token [NEXT] и [DISCONNECT]
- `[NEXT]` в ответе AI — разделитель для отправки нескольких сообщений подряд
- `[DISCONNECT]` — AI завершает разговор, персонаж "отключается"

## Генераторы (generators/)

### char_generator.py (`generate()`)
- Единственная используемая функция: `generate(seed, gender, age_group, topic)`
- Возвращает `Character` dataclass
- Внутри: выбор пола → возраст → имя → темперамент → архетип → социальность → MBTI → тело/красота → рост/внешность → черты → профессия → доход → хобби → образование → языки → предпочтения → фетиши → привычки → страхи → мечты → ценности → травма → биография → spice-поля → стиль письма → opener

### char_model.py
- `Character` dataclass (73 поля, все обязательные)
- `weighted_choice(items, weights)` — взвешенный выбор
- `weighted_sample(pool, weights, k)` — взвешенная выборка без повторений
- `pick_from_pool(pool, profile, ...)` — выбор из пула с учётом профиля личности
- `zodiac_sign(day, month)` — знак зодиака

### char_data.py
- Все пулы данных: имена, фамилии, города, цвета глаз/волос, типы телосложения, тона кожи, черты характера, хобби, профессии, музыка/фильмы/книги, фетиши, привычки, страхи, мечты, ценности, стили одежды, травмы, жильё, питомцы, флаги, стили письма, opener'ы, lying tendencies, skip factors, harassment reactions, fav/taboo topics, default attitudes, paradoxes

### char_profiles.py
- Темпераменты (4): сангвиник/холерик/флегматик/меланхолик + их profile-модификаторы
- Архетипы (12 Jungian) с desire/goal/fear/talent/shadow/wound/backstory
- MBTI профили (16 типов) с personality traits
- Совместимость archetype→mbti
- Возрастные группы (4: teen/young/adult/mature) с profile_mod/professions/hobbies/fetishes/relationships
- body_sizes (5), beauty_levels (4) с profile-модификаторами и backstory
- Социальные стили (3): экстраверт/интроверт/амбиверт
- chat_motivations (14 типов) с weighted archetype_boost
- kinkiness_levels (4 уровня)

### char_appearance.py
- `generate_appearance(appearance_data, gender)` — генерация текстового описания внешности
- Вход: {eye_color, hair_color, hair_length, hair_style, body_type, body_size, beauty, clothing_style, distinctive_features}
- Использует шаблоны: лицо, фигура, волосы, одежда, особенности, общее впечатление
- `fashion_items` — предметы одежды по стилям

### char_bio.py
- `generate_backstory(archetype_data, age_group, age, gender, extra_fragments)` — биография
- `generate_bio(char, age_group)` — краткое био (1-2 предложения)

## Генерация персонажа (подробно)

### Возраст
- `age_group` определяет диапазон возраста: teen(13-17), young(18-21), adult(22-35), mature(36-55)
- Если age_group=None: weighted выбор [42, 42, 12, 4] (кроме flirt/rp)

### Пол
- `gender` = 'male'/'female'/None (случайный)

### Темперамент
- Влияет на personality_dims
- Архитип weighted по совместимости с темпераментом
- flit: смещение к холерику/сангвинику; rp: к флегматику/меланхолику

### MBTI
- weighted по совместимости с архетипом
- Фильтр: интроверты→I*, экстраверты→E*
- 29 personality dims, модифицируются: темпераментом → возрастом → социальностью → MBTI → body/beauty

### Тело и красота
- Body size: 5 уровней с profile-модификаторами и backstory
- Beauty: 4 уровня с profile-модификаторами и backstory
- BMI рассчитывается, влияет на body_type
- Gym habits от body_type

### Профессия
- от архетипа + profile + возрастной группы
- profession_group: руководитель/аналитик/творец/помощник/коммуникатор/мастер/страж/исследователь

### Доход (wealth)
- 6 уровней: очень низкий → очень высокий
- Влияет на хобби (стоимость), еду, финансовые привычки

### Травма
- 14 типов с последствиями, защитами, убеждениями
- Совместимость с архетипом (boost weights)
- flirt: исключает сексуальное насилие и отвержение внешности
- Форсированно включается в backstory

### Spice-поля
- Из 17 полей выбираются 3-5 случайных
- housing/financial_habit/eating_habit/pet/red_flags/green_flags/cryptonite/useless_talent/body_language_tell/humor_style/biggest_lie/anger_trigger/enemy/sleep_type/personal_scent/health_issue/supernatural_belief
- trauma/wealth влияют на принудительное включение некоторых полей

### Opener (первое сообщение)
- Выбор из пула ~100 фраз с весами
- Зависит от пола (мужские/женские специфичные)
- flirt/rp режимы добавляют свои пулы
- Может содержать `{name}`, `{age}`, `{city}`, `{mood}` и т.д. — заменяются на реальные значения

### Oversharing level
- 1-10, рассчитывается из personality dims
- Модифицируется травмой (закрытые травмы снижают, открытые повышают)
- Модифицируется chat_motivation, lying_tendency, topic

### Lying tendency
- 5 уровней: честная / социальная маска / приукрашивает / играет роль / хроническая лгунья
- "играет роль" добавляет случайную роль из _lying_roles
- Влияет на префиксы в fallback_reply (15% шанс)

### Default attitude
- Случайный выбор из default_attitudes_pool
- Определяет STOCK_ANSWERS в fallback_reply

## Reused code patterns
- `sys.path.insert(0, os.path.dirname(__file__))` — добавление корня в path
- `load_env()` — ручная загрузка .env (без dotenv)
- Генератор использует `random.seed()` для детерминированной генерации
- Все AI вызовы идут через `urllib.request` (без openai библиотеки)
- Ответы могут содержать `[NEXT]` (разделение сообщений) и `[DISCONNECT]` (завершение)
- Максимальная длина сообщения: `_MAX_MSG_LEN = 280` (разбивка через `_split_long_msg`)

## Примечания

- `generators/character_generator.py` — старый/альтернативный генератор. НЕ ИСПОЛЬЗУЕТСЯ в app.py/bot.py. Основной: `generators/char_generator.py`
- В app.py есть дубликат функции `_agent_maybe_reconnect()` (строки 809 и 850) — баг/копипаста
- В app.py `secret_key` жёстко закодирован — `'nektome-ai-chat-secret-2026'` (не секрет)
- bot.py НЕ импортирует код из app.py — имеет собственные копии всех функций
- Все inline keyboards в bot.py используют callback_data с префиксами (`gender_male`, `age_от 18 до 21`, `topic_chat`)
- Fallback-ответы (`fallback_reply`) используют pypy-совместимый регекс без advanced features
