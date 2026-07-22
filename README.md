<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.0-000?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/LLM-OpenAI--compatible-FF6F00?style=for-the-badge&logo=openai" alt="LLM">
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=for-the-badge" alt="Status">
</p>

# Nektome

> Anonymный чат с AI-собеседниками. Глубокая генерация персонажей + реалистичный чат-интерфейс.

---

## 🚀 Быстрый старт

### Windows
```batch
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python app.py
```

### Linux / macOS
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Сервер запускается на **http://127.0.0.1:5000**.

## 🧱 Архитектура

| Файл | Роль |
|---|---|
| `app.py` | Flask-приложение: генерация, чат, online-симулятор, OpenAI API |
| `templates/index.html` | Single-page интерфейс: поиск → коннект → чат |
| `static/js/script.js` | Клиентская логика: поиск, отправка, модалки, online-счётчик |
| `static/css/style.css` | Полный набор стилей (ночная/дневная тема) |
| `generators/char_generator.py` | Генератор персонажа (7 уровней: архетип, травма, внешность, биография...) |
| `generators/char_model.py` | Pydantic-модель персонажа |
| `generators/char_data.py` | Все пулы данных: имена, хобби, бэкстори, openers, стили письма |
| `generators/char_profiles.py` | Архетипы, зодиаки, профессии, предпочтения |
| `generators/char_appearance.py` | Генератор внешности (рост, цвет глаз, стиль одежды) |
| `generators/char_bio.py` | Генератор биографии |

## ⚙️ Конфигурация

Задаётся через `.env`:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `OPENAI_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI-совместимый эндпоинт |
| `OPENAI_API_KEY` | — | API-ключ |
| `OPENAI_MODEL` | `deepseek-v4-flash` | Название модели |

## 🔌 API Routes

| Метод | Путь | Описание |
|---|---|---|
| 🟢 `GET` | `/` | Web UI (чат-интерфейс) |
| 🟢 `POST` | `/api/generate` | Сгенерировать персонажа (`partner_gender`, `partner_age`) |
| 🟢 `POST` | `/api/chat` | Отправить сообщение (`message`) |
| 🟢 `GET` | `/api/online` | Количество людей онлайн (симуляция) |

## 🎭 Генерация персонажа

7-уровневая архитектура генерации:

1. **Архетип + темперамент** — базовая структура личности (Юнг + Гиппократ)
2. **Внешность** — рост, телосложение, красота, цвет глаз/волос, стиль
3. **Биография** — травма, ключевые события, убеждения
4. **Spice-блоки** — 3-5 случайных деталей из 17 пулов (запах, враг, криптонит...)
5. **Профиль** — профессия, хобби, предпочтения, цели в чате
6. **Стиль общения** — манера письма, открытость, юмор, RP-способность
7. **Контекст** — настроение, ситуация, скрытый мотив, opener

Каждый персонаж уникален: комбинация пола, возраста, архетипа, травмы, стиля письма и RP даёт тысячи вариаций.

## 🖥 Web UI

Single-page интерфейс в стиле анонимного чата:

- **Поиск** — фильтры (пол, возраст, темы, цели), кнопка «Начать поиск»
- **Коннект** — спиннер + «Ищем собеседника...» + «Отменить»
- **Чат** — сообщения, индикатор печати, отправка, RP-формат
- **Завершение** — модалка подтверждения → кнопки «Новый собеседник» / «Изменить параметры»
- **Online** — симуляция количества людей в чате (день/ночь)
- 🌞 Светлая и 🌙 тёмная темы

## 📦 Зависимости

```
flask       python-dotenv    openai
```

---

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.0-000?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/LLM-OpenAI--compatible-FF6F00?style=for-the-badge&logo=openai" alt="LLM">
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=for-the-badge" alt="Status">
</p>
