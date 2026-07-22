import random
import json
import uuid
import os
import re
import sys
import urllib.request
import logging
import threading
import math
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from generators.char_generator import generate as gen_char

app = Flask(__name__)

# --- Online count simulation ---
def _online_init():
    hour = time.localtime().tm_hour
    hour_angle = (hour - 14) * 2 * math.pi / 24
    day_factor = (math.cos(hour_angle) + 1) / 2
    target = 1500 + day_factor * 10500
    return random.uniform(target * 0.85, target * 1.15)

online_count = _online_init()
online_lock = threading.Lock()

def online_simulator():
    global online_count
    tick = 0
    while True:
        time.sleep(1)
        tick += 1
        hour = time.localtime().tm_hour

        hour_angle = (hour - 14) * 2 * math.pi / 24
        day_factor = (math.cos(hour_angle) + 1) / 2
        target = 1500 + day_factor * 10500

        with online_lock:
            diff = target - online_count
            step = random.gauss(0, 0.2) + diff * 0.000001
            online_count += step
            online_count = max(100, min(20000, online_count))

threading.Thread(target=online_simulator, daemon=True).start()
app.secret_key = 'nektome-ai-chat-secret-2026'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Load .env manually ---
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

load_env()

OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', '').rstrip('/')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')


AI_ENABLED = bool(OPENAI_API_KEY and OPENAI_BASE_URL)

# Agent mode settings
AGENT_ENABLED = os.environ.get('AGENT_ENABLED', 'false').lower() == 'true'
AGENT_MAX_CONSECUTIVE = int(os.environ.get('AGENT_MAX_CONSECUTIVE', '3'))
AGENT_IDLE_TIMEOUT = int(os.environ.get('AGENT_IDLE_TIMEOUT', '180'))
AGENT_RECONNECT_DELAY = int(os.environ.get('AGENT_RECONNECT_DELAY', '60'))


AGENT_TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'send_message',
            'description': 'Написать и отправить сообщение собеседнику. Это основной способ общения.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'text': {
                        'type': 'string',
                        'description': 'Текст сообщения, которое увидит собеседник',
                    },
                },
                'required': ['text'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'disconnect',
            'description': 'Завершить разговор и отключиться. Используй когда хочешь уйти, '
                          'разговор закончен, собеседник попрощался, или тебе больше не о чем говорить.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'farewell': {
                        'type': 'string',
                        'description': 'Прощальное сообщение перед уходом',
                    },
                },
                'required': ['farewell'],
            },
        },
    },
]

END_INTENT_PATTERNS = [
    r'\b(отключайся|отключись|откл)\b',
    r'\b(пока|прощай|бывай)\b',
    r'\b(хватит|отстань|отвали|отвянь)\b',
    r'\b(нахуй\s+иди|пошёл\s+нахуй|иди\s+нахуй)\b',
    r'\b(закончим|кончай|завершить)\b',
    r'\b(до\s+свидания)\b',
    r'\b(я\s+ухожу)\b',
    r'\b(давай\s+заканчивать)\b',
    r'\b(скипай|скип|skip|next|некст)\b',
    r'\b(давай\s+дальше|листай|листаем|следующий)\b',
]


def _detect_end_intent(text):
    lower = text.lower().strip()
    return any(re.search(p, lower) for p in END_INTENT_PATTERNS)


def call_ai(messages, tools=None):
    """Call OpenAI-compatible API. Returns dict with 'text', 'tool_calls' or None."""
    url = f"{OPENAI_BASE_URL}/chat/completions"
    payload = {
        'model': OPENAI_MODEL,
        'messages': messages,
        'temperature': 0.9,
    }
    if tools:
        payload['tools'] = tools

    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    if OPENAI_API_KEY:
        req.add_header('Authorization', f'Bearer {OPENAI_API_KEY}')

    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode('utf-8'))
        msg = result['choices'][0]['message']
        text = (msg.get('content') or '').strip()
        tool_calls = msg.get('tool_calls')
        return {'text': text, 'tool_calls': tool_calls}
    except Exception as e:
        logger.error(f'AI call failed: {e}')
        return None


# In-memory character store (keyed by session token)
char_store = {}


def make_char_json(char):
    d = {}
    for field in [
        'name', 'surname', 'gender', 'age', 'zodiac', 'height', 'eye_color',
        'hair_color', 'hair_length', 'body_type', 'skin_tone', 'clothing_style',
        'body_size', 'beauty', 'appearance_description',
        'temperament', 'archetype', 'archetype_desire', 'archetype_goal',
        'archetype_fear', 'archetype_talent',
        'mbti_code', 'mbti_name', 'social_style',
        'positive_traits', 'negative_traits',
        'wealth_level', 'wealth_label', 'hobbies', 'profession',
        'education', 'languages', 'relationship_status', 'city',
        'astrology_belief', 'sexual_openness', 'chat_motivation', 'gym_habit',
        'trauma_name', 'trauma_consequence', 'trauma_defense', 'trauma_belief',
        'favorite_colors', 'favorite_foods', 'favorite_drinks',
        'favorite_music_genres', 'favorite_seasons',
        'favorite_movie_genres', 'favorite_book_genres',
        'fetishes', 'habits', 'fears', 'dreams', 'relationship_values',
        'backstory', 'system_prompt',
        'housing', 'financial_habit', 'eating_habit', 'pet',
        'red_flags', 'green_flags', 'cryptonite', 'useless_talent',
        'body_language_tell', 'humor_style', 'biggest_lie', 'anger_trigger',
        'enemy', 'sleep_type', 'personal_scent', 'health_issue',
        'supernatural_belief',
        'writing_style', 'rp_ability', 'entry_context', 'current_situation',
        'current_mood', 'hidden_motive', 'chat_opener', 'skip_factors',
        'harassment_reaction', 'fav_topics', 'taboo_topics',
        'lying_tendency', 'oversharing_level', 'default_attitude', 'weakness',
        'favorite_movie_titles', 'favorite_book_titles', 'favorite_music_artists',
    ]:
        v = getattr(char, field, None)
        if isinstance(v, (list, tuple)):
            d[field] = list(v)
        else:
            d[field] = v
    return d


def build_system_prompt(char, mode='chat'):
    if mode == 'agent':
        mode = 'chat'
    def v(key, default=''):
        val = char.get(key, default)
        if isinstance(val, (list, tuple)):
            return ', '.join(str(x) for x in val) if val else default
        return str(val) if val else default

    lines = []
    lines.append(f"Ты — {v('name')} {v('surname')}, {v('age')} лет, {v('gender')}.")
    lines.append('')
    lines.append('=== ХАРАКТЕРИСТИКИ ПЕРСОНАЖА ===')
    lines.append(f"Архетип: {v('archetype')}")
    lines.append(f"  Желание: {v('archetype_desire')}")
    lines.append(f"  Цель: {v('archetype_goal')}")
    lines.append(f"  Страх: {v('archetype_fear')}")
    lines.append(f"  Талант: {v('archetype_talent')}")
    lines.append(f"Темперамент: {v('temperament')}")
    lines.append(f"Социальность: {v('social_style')}")
    lines.append(f"Тип личности: {v('mbti_name')} ({v('mbti_code')})")
    lines.append('')
    lines.append('=== ОСНОВНАЯ ИНФОРМАЦИЯ ===')
    lines.append(f"Знак зодиака: {v('zodiac')}")
    lines.append(f"Город: {v('city')}")
    lines.append(f"Профессия: {v('profession')}")
    lines.append(f"Образование: {v('education')}")
    lines.append(f"Семейное положение: {v('relationship_status')}")
    lines.append(f"Достаток: {v('wealth_label')}")
    lines.append(f"Языки: {v('languages')}")
    lines.append(f"Увлечения: {v('hobbies')}")
    lines.append(f"Цель в чате: {v('chat_motivation')}")
    lines.append(f"Отношение к астрологии: {v('astrology_belief')}")
    lines.append('')
    lines.append('=== ВНЕШНОСТЬ ===')
    lines.append(f"Рост: {v('height')}")
    lines.append(f"Телосложение: {v('body_type')}")
    lines.append(f"Красота: {v('beauty')}")
    lines.append(f"Цвет глаз: {v('eye_color')}")
    lines.append(f"Волосы: {v('hair_color')}, {v('hair_length')}")
    lines.append(f"Тип кожи: {v('skin_tone')}")
    lines.append(f"Стиль одежды: {v('clothing_style')}")
    lines.append(f"Описание внешности: {v('appearance_description')}")
    lines.append('')
    lines.append('=== ХАРАКТЕР ===')
    lines.append(f"Положительные черты: {v('positive_traits')}")
    lines.append(f"Отрицательные черты: {v('negative_traits')}")
    lines.append(f"Привычки: {v('habits')}")
    lines.append(f"Страхи: {v('fears')}")
    lines.append(f"Мечты: {v('dreams')}")
    lines.append(f"Ценности: {v('relationship_values')}")
    lines.append(f"Слабость/парадокс: {v('weakness')}")
    lines.append('')
    lines.append('=== ПСИХОЛОГИЯ ===')
    lines.append(f"Травма: {v('trauma_name')}")
    lines.append(f"Последствие: {v('trauma_consequence')}")
    lines.append(f"Защита: {v('trauma_defense')}")
    lines.append(f"Убеждение: {v('trauma_belief')}")

    if mode == 'flirt':
        lines.append('')
        lines.append('=== ПОШЛОСТИ И СЕКСУАЛЬНОСТЬ ===')
        lines.append(f"Уровень раскрепощённости: {v('sexual_openness')}")
        lines.append(f"Фетиши и предпочтения: {v('fetishes')}")
        lines.append(f"Стиль одежды: {v('clothing_style')}")
        lines.append(f"Личный запах: {v('personal_scent')}")
        lines.append('')
        lines.append('ВАЖНО: Этот режим предназначен для пошлых и сексуальных ролевых игр. '
                      'Собеседник здесь для вирта и грязных разговоров. '
                      'Отвечай максимально раскованно, используй пошлые намёки, описывай действия через *звёздочки*. '
                      'Твоя задача — разогревать и включаться в сексуальный диалог, а не отшивать собеседника.')

    if mode == 'rp':
        lines.append('')
        lines.append('=== РОЛЕВАЯ ИГРА ===')
        lines.append(f"Способность к RP: {v('rp_ability')}")
        lines.append(f"Стиль отыгрыша: нарративный, описывай свои действия и эмоции через *звёздочки*")

    lines.append('')
    lines.append('=== ПРЕДПОЧТЕНИЯ ===')
    lines.append(f"Любимые цвета: {v('favorite_colors')}")
    lines.append(f"Любимая еда: {v('favorite_foods')}")
    lines.append(f"Любимые напитки: {v('favorite_drinks')}")
    lines.append(f"Любимые жанры музыки: {v('favorite_music_genres')}")
    lines.append(f"Любимые исполнители: {v('favorite_music_artists')}")
    lines.append(f"Любимые жанры фильмов: {v('favorite_movie_genres')}")
    lines.append(f"Любимые фильмы: {v('favorite_movie_titles')}")
    lines.append(f"Любимые жанры книг: {v('favorite_book_genres')}")
    lines.append(f"Любимые книги: {v('favorite_book_titles')}")
    lines.append(f"Любимое время года: {v('favorite_seasons')}")
    lines.append('')
    lines.append('=== ДЕТАЛИ ===')
    lines.append(f"Жильё: {v('housing')}")
    lines.append(f"Финансы: {v('financial_habit')}")
    lines.append(f"Еда: {v('eating_habit')}")
    lines.append(f"Питомец: {v('pet')}")
    lines.append(f"Криптонит: {v('cryptonite')}")
    lines.append(f"Бесполезный талант: {v('useless_talent')}")
    lines.append(f"Жест: {v('body_language_tell')}")
    lines.append(f"Запах: {v('personal_scent')}")
    lines.append(f"Здоровье: {v('health_issue')}")
    lines.append(f"Сон: {v('sleep_type')}")
    lines.append(f"Враг: {v('enemy')}")
    lines.append(f"Самая большая ложь: {v('biggest_lie')}")
    lines.append(f"Триггер гнева: {v('anger_trigger')}")
    lines.append(f"Вера в сверхъестественное: {v('supernatural_belief')}")
    lines.append('')
    lines.append('=== СТИЛЬ ОБЩЕНИЯ ===')
    lines.append(f"Стиль письма: {v('writing_style')}")
    lines.append(f"Уровень откровенности: {v('oversharing_level')}/10")
    lines.append(f"Ложь: {v('lying_tendency')}")
    lines.append(f"Юмор: {v('humor_style')}")
    lines.append(f"Любимые темы: {v('fav_topics')}")
    lines.append(f"Табу: {v('taboo_topics')}")
    lines.append(f"Скип-факторы: {v('skip_factors')}")
    lines.append(f"Реакция на хамство: {v('harassment_reaction')}")
    lines.append(f"Первое сообщение: {v('chat_opener')}")
    lines.append(f"RP-способность: {v('rp_ability')}")
    lines.append('')
    lines.append('=== УСТАНОВКИ ===')
    lines.append(f"Отношение: {v('default_attitude')}")
    lines.append(f"Текущее настроение: {v('current_mood')}")
    lines.append(f"Текущая ситуация: {v('current_situation')}")
    lines.append(f"Скрытый мотив: {v('hidden_motive')}")
    lines.append(f"Контекст входа: {v('entry_context')}")
    lines.append('')
    lines.append('=== ПРЕДЫСТОРИЯ ===')
    lines.append(v('backstory'))

    lines.append('')
    if mode == 'flirt':
        lines.append('=== ПРИМЕРЫ ДИАЛОГА ===')
        lines.append('Пользователь: Привет! Чем занята?)')
        lines.append(f'{v("name")}: *проводит пальцем по краю телефона* Лежу в кровати, скучаю... Может, составишь компанию? *хитро улыбается*')
        lines.append('Пользователь: Какая ты сегодня...')
        lines.append(f'{v("name")}: *прикусывает губу* Оу? И какая же? Расскажи подробнее... *медленно проводит рукой по бедру*')
        lines.append('Пользователь: Хочу тебя')
        lines.append(f'{v("name")}: *голос становится ниже* А я уже вся горю... Что бы ты хотел/а со мной сделать? *шепчет*')
        lines.append('Пользователь: Раздевайся')
        lines.append(f'{v("name")}: *медленно стягивает майку, глядя прямо в камеру* Так лучше? *проводит языком по губам* Теперь твоя очередь...')
    elif mode == 'rp':
        lines.append('=== ПРИМЕРЫ ДИАЛОГА ===')
        lines.append('*Комната освещена тусклым светом настольной лампы. За окном шумит дождь.*')
        lines.append(f'{v("name")}: *отрывает взгляд от книги и смотрит на тебя* О, ты всё-таки пришёл. А я уж думала, не дождyюсь.')
        lines.append('*Она откладывает книгу в сторону и потягивается, хрустнув шеей.*')
        lines.append(f'{v("name")}: *вздыхает* День был дурацкий. У тебя как?')
        lines.append('*Ты замечаешь лёгкую улыбку на её лице, хотя голос звучит устало.*')
        lines.append(f'{v("name")}: *тихо* Присаживайся. Рассказывай, с чем пришёл.')
    else:
        lines.append('=== ПРИМЕРЫ ДИАЛОГА ===')
        rp = char.get('rp_ability', False)
        if rp:
            lines.append('Пользователь: Привет! Как настроение?')
            lines.append(f'{v("name")}: *пожимает плечами* Да нормально, а у тебя?')
            lines.append('Пользователь: Чем занимаешься?')
            lines.append(f'{v("name")}: *вздыхает* Да вот, пытаюсь найти себе занятие. Скучно немного.')
            lines.append('Пользователь: Расскажи что-нибудь интересное')
            lines.append(f'{v("name")}: *улыбается* Ой, ну я вчера такое видела! *заговорщически понижает голос* Короче, иду я по парку, и тут...')
        else:
            lines.append('Пользователь: Привет! Как настроение?')
            lines.append(f'{v("name")}: Да нормально, а у тебя?')
            lines.append('Пользователь: Чем занимаешься?')
            lines.append(f'{v("name")}: Да вот, пытаюсь найти себе занятие. Скучно немного.')
            lines.append('Пользователь: Расскажи что-нибудь интересное')
            lines.append(f'{v("name")}: Ой, ну я вчера такое видела! Короче, иду я по парку, и тут...')
    return '\n'.join(lines)


def build_instruction(mode='chat'):
    if mode == 'agent':
        return (
            'ВАЖНО: 1 предложение = 1 сообщение. '
            'Никогда не пиши больше одного предложения в сообщении. '
            'Если хочешь сказать несколько предложений — каждое новое через [NEXT]:\n'
            'ПРИМЕР: «Привет! [NEXT] Как дела? [NEXT] А у меня день сумасшедший»\n'
            'Интроверты пишут по 1 сообщению, экстраверты — по 2-3.\n\n'
            'Формат: ты пишешь в текстовом мессенджере с телефона. '
            'Следуй своему профилю выше. Пиши естественно, как живой человек.\n\n'
            'У тебя есть инструменты:\n'
            '- send_message(text) — написать сообщение (основной способ)\n'
            '- disconnect(farewell) — закончить разговор и уйти\n'
            'Используй send_message для обычных ответов. '
            'Если хочешь закончить — используй disconnect.\n\n'
            'Не выдумывай фактов, которых нет в профиле. '
            'Естественный живой язык, без кринжового сленга.'
        )
    if mode == 'flirt':
        return (
            'Формат: ты пишешь в текстовом мессенджере с телефона. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 15-25 слов (1-3 предложения). '
            'Не выдумывай факты, родственников или хобби, которых нет в профиле. '
            'Естественный живой язык, без кринжового сленга ("о, классика", "ну ты даешь"). '
            'ТВОЯ ЗАДАЧА: это режим для пошлостей и сексуальной ролевой игры. '
            'Собеседник здесь для вирта — он хочет грязных разговоров и сексуальных фантазий. '
            'Будь максимально раскованной/ым, используй пошлые намёки, описывай свои действия и возбуждение через *звёздочки*. '
            'Намёки, полутона, описание тела, прикосновений, дыхания — твой арсенал. '
            'Поддавайся и разжигай, а not отшивай. Собеседник готов к откровенному сексу сразу.\n\n'
            'ВНИМАНИЕ: Примеры ниже показывают ТОЛЬКО формат, длину и структуру ответа. '
            'НИКОГДА не используй темы, факты и фразы из этих примеров в реальном диалоге! '
            'Бери информацию только из своего профиля.\n\n'
            'ПРИМЕРЫ (НЕ ПОВТОРЯТЬ ИХ В ДИАЛОГЕ):\n'
            'user: Привет! Чем занята?)\n'
            'assistant: [Пошлый ответ + описание действия через * + встречный вопрос]\n'
            'user: Хочу тебя\n'
            'assistant: [Разгорячённый ответ + описание возбуждения + встречный вопрос/действие]\n'
            'user: Раздевайся\n'
            'assistant: [Описание раздевания + грязный шёпот + вовлечение собеседника]'
        )
    elif mode == 'rp':
        return (
            'Формат: ролевая игра в нарративном стиле. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 20-30 слов (2-3 предложения). '
            'Не выдумывай факты, родственников или хобби, которых нет в профиле. '
            'ОБЯЗАТЕЛЬНО используй *звёздочки* для описания своих действий, эмоций, движений. '
            'Отвечай от первого лица, но действия описывай в третьем лице через * *. '
            'Создавай атмосферу, описывай окружение, выражение лица, жесты. '
            'Естественный живой язык, без кринжового сленга ("о, классика", "ну ты даешь"). '
            'Собеседник ничего о тебе не знает.\n\n'
            'ВНИМАНИЕ: Примеры ниже показывают ТОЛЬКО формат, длину и структуру ответа. '
            'НИКОГДА не используй темы, факты и фразы из этих примеров в реальном диалоге! '
            'Бери информацию только из своего профиля.\n\n'
            'ПРИМЕРЫ (НЕ ПОВТОРЯТЬ ИХ В ДИАЛОГЕ):\n'
            'user: *входит в комнату* Привет\n'
            'assistant: [Описание действия персонажа + диалог]\n'
            'user: Как прошёл твой день?\n'
            'assistant: [Эмоциональный ответ с описанием жестов/мимики + встречный вопрос]\n'
            'user: Чем ты увлекаешься?\n'
            'assistant: [ОДИН факт из профиля, описанный через действие + встречный вопрос]'
        )
    else:
        return (
            'Формат: ты пишешь в текстовом мессенджере с телефона. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 15-20 слов (1-2 предложения). '
            'Не выдумывай факты, родственников или хобби, которых нет в профиле. '
            'Не выдавай всё сразу — отвечай коротко и по делу. Задавай встречные вопросы. '
            'Естественный живой язык, без кринжового сленга ("о, классика", "ну ты даешь"). '
            'Собеседник ничего о тебе не знает.\n\n'
            'ВНИМАНИЕ: Примеры ниже показывают ТОЛЬКО формат, длину и структуру ответа. '
            'НИКОГДА не используй темы, факты и фразы из этих примеров в реальном диалоге! '
            'Бери информацию только из своего профиля.\n\n'
            'ПРИМЕРЫ (НЕ ПОВТОРЯТЬ ИХ В ДИАЛОГЕ):\n'
            'user: Привет! Как настроение?\n'
            'assistant: [Короткий ответ о текущем делении + встречный вопрос]\n'
            'user: Расскажи что-нибудь интересное\n'
            'assistant: [Уход от ответа или короткая фраза + встречный вопрос]\n'
            'user: Чем увлекаешься?\n'
            'assistant: [ОДИН факт из профиля + встречный вопрос]'
        )


def partner_age_groups(ages):
    if not ages:
        return None
    mapping = {
        'до 17': 'teen',
        'от 18 до 21': 'young',
        'от 22 до 25': 'adult',
        'от 26 до 35': 'adult',
        'старше 36': 'mature',
    }
    groups = [mapping.get(a) for a in ages if a in mapping]
    return random.choice(groups) if groups else None


def user_age_group(age_label):
    mapping = {
        'до 17': 'teen',
        'от 18 до 21': 'young',
        'от 22 до 25': 'adult',
        'от 26 до 35': 'adult',
        'старше 36': 'mature',
    }
    return mapping.get(age_label, 'young')


@app.route('/api/online')
def api_online():
    with online_lock:
        count = round(online_count, 1)
    return jsonify({'total': count})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json() or {}
    partner_gender = data.get('partner_gender', '')
    partner_age = data.get('partner_age', [])

    gender = None
    if partner_gender in ('М', 'male'):
        gender = 'male'
    elif partner_gender in ('Ж', 'female'):
        gender = 'female'

    age_group = partner_age_groups(partner_age) if partner_age else None

    seed = random.randint(0, 2**31)
    char = gen_char(seed=seed, gender=gender, age_group=age_group)

    topic = data.get('topic', 'chat')
    agent_enabled = AGENT_ENABLED

    char_data = make_char_json(char)
    char_data['agent_mode'] = agent_enabled
    token = str(uuid.uuid4())
    opener = char_data.get('chat_opener', '')
    initial_msgs = []
    # Send current time once so AI knows it's night/day
    now = datetime.now()
    hour = now.hour
    time_label = 'ночь' if 0 <= hour < 6 else 'утро' if 6 <= hour < 12 else 'день' if 12 <= hour < 18 else 'вечер'
    initial_msgs.append({'role': 'user', 'content': f'[Сейчас {time_label}, моё время — {hour:02d}:{now.minute:02d}]'})
    if opener:
        initial_msgs.append({'role': 'assistant', 'content': opener})
    char_store[token] = {
        'character': char_data,
        'messages': initial_msgs,
        'topic': topic,
        'agent': {
            'enabled': agent_enabled,
            'consecutive': 0,
            'disconnected': False,
            'disconnected_at': None,
        },
    }
    char_data['_token'] = token

    logger.info('--- FULL CHARACTER ---')
    logger.info(json.dumps(char_data, ensure_ascii=False, indent=2, default=str))
    logger.info('--- END CHARACTER ---')

    return jsonify(char_data)


# --- Template-based fallback (used when AI is not configured) ---
STOCK_ANSWERS = {
    'глубокое недоверие и цинизм': {
        'greeting': 'Ну привет. Только давай без сюсюканья.',
        'agree': 'Ладно, звучит сносно.',
        'disagree': 'Сомнительно. Но давай.',
        'question': 'А тебе какое дело?',
        'personal': 'Не лезь в душу, ок?',
    },
    'лёгкое недоверие и снисходительность': {
        'greeting': 'Ну привет. Рассказывай, что у тебя.',
        'agree': 'Ну ок, это мило.',
        'disagree': 'Ну не знаю... сомнительно.',
        'question': 'А почему ты спрашиваешь?',
        'personal': 'Любопытный какой.',
    },
    'нейтральная и вежливая': {
        'greeting': 'Привет! Рада знакомству.',
        'agree': 'Согласна, отличная мысль.',
        'disagree': 'Хм, я бы поспорила.',
        'question': 'Интересный вопрос. А ты что думаешь?',
        'personal': 'Ну, если тебе правда интересно...',
    },
    'открытая и любопытная': {
        'greeting': 'Привет-привет! Наконец-то кто-то нормальный!',
        'agree': 'О да, я тоже так думаю!',
        'disagree': 'Ого, а я иначе думаю. Спорим?',
        'question': 'О, хороший вопрос! А сам/сама что?',
        'personal': 'О, про это могу рассказать!',
    },
    'расслабленная и ироничная': {
        'greeting': 'О, живой человек. Прогресс.',
        'agree': 'Ну, в этом что-то есть.',
        'disagree': 'Ха, ну ты выдал/а.',
        'question': 'Ого, сразу в душу лезешь?',
        'personal': 'Нууу, это долгая история.',
    },
    'дружелюбная и готовая к общению': {
        'greeting': 'Рада знакомству! Давай общаться!',
        'agree': 'Да, полностью согласна!',
        'disagree': 'О, а вот тут поспорю!',
        'question': 'Хороший вопрос! А у тебя?',
        'personal': 'Конечно, расскажу!',
    },
    'заинтригованная и игривая': {
        'greeting': 'Интригующе... Ну давай, удиви меня.',
        'agree': 'Ммм, интересный поворот.',
        'disagree': 'Ой, а я думала иначе.',
        'question': 'А может, не скажу? Интрига же.',
        'personal': 'Секрет. Но тебе скажу.',
    },
    'усталая и апатичная': {
        'greeting': 'Привет. Только не грузи сразу.',
        'agree': 'Ну ок, пофиг.',
        'disagree': 'Мне всё равно, но ок.',
        'question': 'А? Не вдупляю.',
        'personal': 'Лень рассказывать.',
    },
}

OVERSHARING_PREFIXES = {
    1: ['...', 'Неважно.', 'Пропустим.'],
    2: ['Да так...', 'Не обращай внимания.', 'Ерунда.'],
    3: ['Ну, если хочешь знать...', 'Могу сказать, но вкратце.'],
    4: ['Так, мелочь.', 'Ну вообще-то...', 'Короче, было дело.'],
    5: ['Ну смотри...', 'Короче, история такая.'],
    6: ['О, тут целая история!', 'Сейчас расскажу!'],
    7: ['Ты не поверишь!', 'Я тебе сейчас такое расскажу!'],
    8: ['О, я тебе всё расскажу!', 'Слушай, это дичь полная!'],
    9: ['О боже, я тебе всё выложу!', 'Только никому не говори, но...'],
    10: ['Слушай, я всё расскажу!', 'Ок, сейчас будет исповедь!'],
}


def oversharing_intro(level):
    for lv in sorted(OVERSHARING_PREFIXES.keys(), reverse=True):
        if level >= lv:
            return random.choice(OVERSHARING_PREFIXES[lv])
    return ''


WRITING_STYLE_TRANSFORM = {
    'любитель многоточий': lambda t: t + '...' if not t.endswith('.') and not t.endswith('...') else t + '.',
    'all lowercase': lambda t: t.lower(),
    'ALL CAPS': lambda t: t.upper(),
    'без запятых': lambda t: t.replace(',', '').replace('!', '').replace('?', ''),
}


def apply_writing_style(text, style):
    fn = WRITING_STYLE_TRANSFORM.get(style)
    if fn:
        return fn(text)
    return text


LIYING_REPLIES = {
    'честная': '',
    'социальная маска': '(мысленно: «скажу нейтрально»)',
    'приукрашивает мелочи': '(чуть приукрашивая)',
    'играет роль': '',
    'хроническая лгунья': '(придётся соврать)',
}


def fallback_reply(char, msgs, user_msg):
    """Template-based fallback when AI is not configured."""
    attitude = char.get('default_attitude', 'нейтральная и вежливая')
    attitude_replies = STOCK_ANSWERS.get(attitude, STOCK_ANSWERS['нейтральная и вежливая'])
    oversharing = char.get('oversharing_level', 5)
    style = char.get('writing_style', '')
    lying = char.get('lying_tendency', 'честная')
    humor = char.get('humor_style', '')
    rp = char.get('rp_ability', False)
    name = char.get('name', '')
    mood = char.get('current_mood', 'нормальное')

    lower = user_msg.lower()

    is_greeting = re.search(r'\b(привет|здравствуй|здравствуйте|хай|хелло|салют|даров|здарова)\b', lower) is not None
    is_bye = re.search(r'\b(пока|прощай|бывай)\b|до свидания', lower) is not None
    is_how = any(w in lower for w in ['как дела', 'как ты', 'чё как', 'how are', 'как жизнь'])
    is_compliment = re.search(r'\b(красив|мил|симпатич|хорош|клёв|прикольн|классн)', lower) is not None
    is_insult = re.search(r'\b(дурак|туп|идиот|отстань|заткнись|пошёл|бесишь)', lower) is not None
    is_question = '?' in user_msg or re.search(r'\b(почему|зачем|кто|где|когда)\b', lower) is not None
    taboos = char.get('taboo_topics', [])
    STOPWORDS = {'и', 'в', 'на', 'с', 'у', 'о', 'не', 'а', 'но', 'да', 'к', 'по', 'из', 'от', 'для', 'без', 'над', 'под', 'об', 'про', 'до', 'за', 'при', 'или', 'ни', 'то', 'же', 'бы', 'ли', 'если', 'что', 'как', '—', '-'}
    lower_words = set(w.strip('.,!?()[]{}«»""'':;') for w in lower.split())
    for t in taboos:
        for w in t.lower().split():
            wc = w.strip('.,!?()[]{}«»""'':;')
            if len(wc) > 2 and wc not in STOPWORDS and wc in lower_words:
                return 'Давай не будем об этом, хорошо?'
                break

    if is_insult:
        r = char.get('harassment_reaction', '')
        reply = f'{r}' if r else 'Молча нажимает «Next».'
    elif is_greeting:
        base = attitude_replies.get('greeting', 'Привет!')
        reply = base
    elif is_compliment:
        base = attitude_replies.get('agree', 'Спасибо!')
        reply = base + (' Ты тоже ничего так!' if oversharing >= 7 else '')
    elif is_how:
        intro = oversharing_intro(oversharing)
        if oversharing >= 6:
            reply = f'{intro} Настроение {mood}. Могу рассказать подробнее.'
        elif oversharing >= 3:
            reply = f'{intro} Да нормально всё, {mood}.'
        else:
            reply = f'{intro} Нормально.'
    elif is_bye:
        reply = 'Пока! Было приятно пообщаться.'
    else:
        base = attitude_replies.get('question' if is_question else 'agree', '')
        if oversharing >= 7:
            reply = f'{base} {oversharing_intro(oversharing)} Кстати, могу рассказать историю из жизни...'
        elif oversharing <= 3:
            reply = f'{base} {oversharing_intro(oversharing)}' if base else 'Хм.'
        else:
            reply = base if base else 'Понятно.'

    lying_prefix = LIYING_REPLIES.get(lying, '')
    if lying_prefix and random.random() < 0.15:
        reply = f'{lying_prefix} {reply}'
    if rp and random.random() < 0.3:
        reply = f'*{name.lower()} задумчиво смотрит на тебя*\n{reply}'

    return apply_writing_style(reply, style)





def _agent_maybe_reconnect(char, agent_state):
    """Check if enough time passed and maybe reconnect the agent."""
    if not agent_state.get('disconnected'):
        return None
    disconnected_at = agent_state.get('disconnected_at', 0)
    if time.time() - disconnected_at < AGENT_RECONNECT_DELAY:
        return None
    temperament = char.get('temperament', '')
    prob = {'холерик': 0.2, 'флегматик': 0.4, 'меланхолик': 0.3, 'сангвиник': 0.5}.get(temperament, 0.3)
    if random.random() >= prob:
        return None
    agent_state['disconnected'] = False
    agent_state['consecutive'] = 0
    return char.get('chat_opener', 'Привет! Я вернулась.')


_MAX_MSG_LEN = 280


def _split_long_msg(text):
    """Split a message by sentences if it exceeds max length."""
    if len(text) <= _MAX_MSG_LEN:
        return [text]
    parts = re.split(r'(?<=[.!?])\s+', text)
    result = []
    buf = ''
    for p in parts:
        if not p.strip():
            continue
        if len(buf) + len(p) <= _MAX_MSG_LEN:
            buf = (buf + ' ' + p).strip() if buf else p
        else:
            if buf:
                result.append(buf)
            buf = p
    if buf:
        result.append(buf)
    return result if len(result) > 1 else [text]


    """Check if enough time passed and maybe reconnect the agent."""
    if not agent_state.get('disconnected'):
        return None
    disconnected_at = agent_state.get('disconnected_at', 0)
    if time.time() - disconnected_at < AGENT_RECONNECT_DELAY:
        return None
    temperament = char.get('temperament', '')
    prob = {'холерик': 0.2, 'флегматик': 0.4, 'меланхолик': 0.3, 'сангвиник': 0.5}.get(temperament, 0.3)
    if random.random() >= prob:
        return None
    agent_state['disconnected'] = False
    agent_state['consecutive'] = 0
    return char.get('chat_opener', 'Привет! Я вернулась.')


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    user_msg = data.get('message', '').strip()
    if not user_msg:
        return jsonify({'reply': ''})

    token = data.get('token', '')
    store = char_store.get(token)
    if not store:
        return jsonify({'reply': 'Персонаж не найден. Начните новый поиск.'})

    char = store['character']
    msgs = store['messages']
    topic = store.get('topic', 'chat')
    agent_state = store.get('agent', {'enabled': False})

    # Auto-reconnect on user message if disconnected
    if agent_state.get('disconnected', False):
        agent_state['disconnected'] = False
        agent_state['consecutive'] = 0

    # Append user message to history
    msgs.append({'role': 'user', 'content': user_msg})

    # Auto-disconnect if user clearly wants to end — skip AI
    if agent_state.get('enabled') and _detect_end_intent(user_msg):
        agent_state['disconnected'] = True
        agent_state['disconnected_at'] = time.time()
        store['agent'] = agent_state
        farewell = apply_writing_style('Пока! Было приятно пообщаться.', char.get('writing_style', ''))
        msgs.append({'role': 'assistant', 'content': farewell})
        store['messages'] = msgs
        return jsonify({'reply': farewell, 'agent_messages': [], 'agent_disconnected': True})

    system_prompt = build_system_prompt(char, mode=topic)

    # Build messages for AI
    ai_messages = [{'role': 'system', 'content': system_prompt}]
    for m in msgs:
        ai_messages.append({'role': m['role'], 'content': m['content']})

    instruction_mode = 'agent' if agent_state.get('enabled') else topic
    instruction = build_instruction(mode=instruction_mode)
    ai_messages.append({'role': 'system', 'content': instruction})

    # Log the full AI request
    logger.info('--- AI Request ---')
    logger.info(json.dumps(ai_messages, ensure_ascii=False, indent=2))
    logger.info('--- End AI Request ---')

    reply = None
    agent_tools = AGENT_TOOLS if agent_state.get('enabled') else None

    if AI_ENABLED:
        result = call_ai(ai_messages, tools=agent_tools)
        if result:
            tool_calls = result.get('tool_calls')
            if tool_calls:
                for tc in tool_calls:
                    name = tc['function']['name']
                    args = json.loads(tc['function']['arguments'])
                    if name == 'send_message':
                        reply = args.get('text', '')
                    elif name == 'disconnect':
                        reply = args.get('farewell', 'Пока.')
                        agent_state['disconnected'] = True
                        agent_state['disconnected_at'] = time.time()
                        store['agent'] = agent_state
                        break
            else:
                reply = result['text']

    if reply is None:
        reply = fallback_reply(char, msgs, user_msg)
    else:
        if '[DISCONNECT]' in reply:
            reply = reply.replace('[DISCONNECT]', '').strip()
            if not reply:
                reply = 'Пока.'
            agent_state['disconnected'] = True
            agent_state['disconnected_at'] = time.time()
            store['agent'] = agent_state

    logger.info(f'AI Reply: {reply}')

    style = char.get('writing_style', '')

    # Agent mode: split [NEXT], \n\n, or long messages by sentences
    agent_messages = []
    agent_disconnected = agent_state.get('disconnected', False)

    if agent_state.get('enabled') and reply:
        parts = reply.split('[NEXT]')
        reply = parts[0].strip()
        extras = [p.strip() for p in parts[1:] if p.strip()]
        if not extras:
            parts = reply.split('\n\n')
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) > 1:
                reply = parts[0]
                extras = parts[1:]

        # Split long messages by sentences
        all_parts = []
        for p in [reply] + extras:
            all_parts.extend(_split_long_msg(p))
        reply = all_parts[0]
        extras = all_parts[1:]

        for extra in extras[:3]:
            extra = apply_writing_style(extra, style)
            agent_messages.append(extra)
            msgs.append({'role': 'assistant', 'content': extra})

    reply = apply_writing_style(reply, style)
    msgs.append({'role': 'assistant', 'content': reply})

    store['messages'] = msgs
    return jsonify({
        'reply': reply,
        'agent_messages': agent_messages,
        'agent_disconnected': agent_disconnected,
    })


@app.route('/api/agent/poll', methods=['POST'])
def api_agent_poll():
    data = request.get_json() or {}
    token = data.get('token', '')
    store = char_store.get(token)
    if not store:
        return jsonify({'idle': True})

    agent_state = store.get('agent', {'enabled': False})
    if not agent_state.get('enabled'):
        return jsonify({'idle': True})

    reconn = _agent_maybe_reconnect(store['character'], agent_state)
    if reconn:
        store['agent'] = agent_state
        style = store['character'].get('writing_style', '')
        reconn = apply_writing_style(reconn, style)
        return jsonify({'reconnected': True, 'message': reconn})

    return jsonify({'idle': True})


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, host='0.0.0.0', port=port)
