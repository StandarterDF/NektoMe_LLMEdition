import random
import json
import uuid
import os
import re
import sys
import hashlib
import urllib.request
import logging
import threading
import math
import time
from datetime import datetime, timezone, timedelta
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
PROVIDER_TYPE = os.environ.get('PROVIDER_TYPE', 'openai').lower()

AI_ENABLED = bool(OPENAI_API_KEY and OPENAI_BASE_URL)

# --- Multi-provider support ---
# PROVIDER_COUNT=2
# PROVIDER1_NAME=Deepseek
# PROVIDER1_TYPE=deepseek
# PROVIDER1_BASE_URL=https://api.deepseek.com/v1
# PROVIDER1_API_KEY=sk-xxx
# PROVIDER1_MODEL=deepseek-v4-flash

providers = []
selected_provider = None

def load_providers():
    global providers
    count = os.environ.get('PROVIDER_COUNT', '0')
    if count.isdigit() and int(count) > 0:
        for i in range(1, int(count) + 1):
            name = os.environ.get(f'PROVIDER{i}_NAME', f'Provider {i}')
            ptype = os.environ.get(f'PROVIDER{i}_TYPE', 'openai').lower()
            base_url = os.environ.get(f'PROVIDER{i}_BASE_URL', '').rstrip('/')
            api_key = os.environ.get(f'PROVIDER{i}_API_KEY', '')
            model = os.environ.get(f'PROVIDER{i}_MODEL', 'gpt-4o-mini')
            if base_url and api_key:
                providers.append({
                    'name': name,
                    'type': ptype,
                    'base_url': base_url,
                    'api_key': api_key,
                    'model': model,
                })
    if not providers and OPENAI_BASE_URL and OPENAI_API_KEY:
        providers.append({
            'name': 'Default',
            'type': PROVIDER_TYPE,
            'base_url': OPENAI_BASE_URL,
            'api_key': OPENAI_API_KEY,
            'model': OPENAI_MODEL,
        })

def select_provider():
    global selected_provider, OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL, AI_ENABLED, PROVIDER_TYPE
    if not providers:
        logger.error('No AI providers configured. Set OPENAI_BASE_URL + OPENAI_API_KEY in .env')
        AI_ENABLED = False
        return
    if len(providers) == 1:
        selected_provider = providers[0]
        logger.info(f'Auto-selected provider: {selected_provider["name"]} ({selected_provider["type"]})')
    else:
        print('\n' + '=' * 50)
        print('   Nektome — выбор провайдера')
        print('=' * 50)
        for idx, p in enumerate(providers, 1):
            print(f'  {idx}. {p["name"]} ({p["type"]}) — {p["base_url"]}')
        print('=' * 50)
        while True:
            try:
                choice = input(f'  Выбери провайдера (1-{len(providers)}): ').strip()
                idx = int(choice) - 1
                if 0 <= idx < len(providers):
                    selected_provider = providers[idx]
                    break
            except (ValueError, IndexError):
                pass
            print(f'  Введите число от 1 до {len(providers)}')
        print(f'  Выбран: {selected_provider["name"]}')
        print('=' * 50 + '\n')
    OPENAI_BASE_URL = selected_provider['base_url']
    OPENAI_API_KEY = selected_provider['api_key']
    OPENAI_MODEL = selected_provider['model']
    PROVIDER_TYPE = selected_provider['type']
    AI_ENABLED = bool(OPENAI_API_KEY and OPENAI_BASE_URL)

load_providers()
select_provider()




CHAT_SAVE_IDS_STR = os.environ.get('CHAT_SAVE_IDS', '')
CHAT_SAVE_IDS = set()
if CHAT_SAVE_IDS_STR:
    for part in CHAT_SAVE_IDS_STR.split(','):
        part = part.strip()
        if part:
            try:
                CHAT_SAVE_IDS.add(int(part))
            except ValueError:
                pass

ENABLE_OLD_ENCOUNTERS = os.environ.get('ENABLE_OLD_ENCOUNTERS', 'true').lower() == 'true'

CHATS_DIR = os.path.join(os.path.dirname(__file__), 'chats')

def save_chat_log_web(old_char, old_msgs, token):
    """Save chat log from web version (no user_id, keyed by token hash)."""
    if not old_char or not old_msgs or len(old_msgs) <= 1:
        return
    try:
        chat_dir = os.path.join(CHATS_DIR, '_web')
        os.makedirs(chat_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        hash_suffix = hashlib.md5(token.encode('utf-8')).hexdigest()[:8]
        name = old_char.get('name', 'unknown')
        filename = f'{timestamp}_{name}_{hash_suffix}.json'
        filepath = os.path.join(chat_dir, filename)
        log = {
            'chat_id': f'web_{hash_suffix}',
            'timestamp': timestamp,
            'character': {k: v for k, v in old_char.items() if k != 'system_prompt'},
            'messages': old_msgs,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        logger.info(f'Chat log saved (web): {filename}')
    except Exception as e:
        logger.error(f'Failed to save web chat log: {e}')

def _load_old_chat_logs_web():
    """Read all chat logs from chats/ (both _web/ and uid dirs)."""
    logs = []
    if not os.path.isdir(CHATS_DIR):
        return logs
    for entry in os.listdir(CHATS_DIR):
        entry_path = os.path.join(CHATS_DIR, entry)
        if not os.path.isdir(entry_path):
            continue
        for fname in os.listdir(entry_path):
            if not fname.endswith('.json'):
                continue
            try:
                with open(os.path.join(entry_path, fname), encoding='utf-8') as f:
                    logs.append(json.load(f))
            except Exception as e:
                logger.error(f'Failed to load chat log {entry}/{fname}: {e}')
    return logs

def _pick_old_encounter_web():
    if not ENABLE_OLD_ENCOUNTERS:
        return None
    chance = 0.03 + random.random() * 0.02
    if random.random() >= chance:
        return None
    logs = _load_old_chat_logs_web()
    if not logs:
        return None
    log = random.choice(logs)
    char_data = log.get('character', {})
    all_msgs = log.get('messages', [])
    old_msgs = [m for m in all_msgs if m['role'] in ('user', 'assistant')][-15:]
    if not old_msgs:
        return None
    logger.info(f'Old encounter (web)! Re-meeting {char_data.get("name","?")}')
    return char_data, old_msgs

CITY_TZ = {
    'Москва': 3, 'Санкт-Петербург': 3, 'Новосибирск': 7, 'Екатеринбург': 5,
    'Казань': 3, 'Краснодар': 3, 'Ростов-на-Дону': 3, 'Владивосток': 10,
    'Нижний Новгород': 3, 'Челябинск': 5, 'Самара': 4, 'Омск': 6,
    'Воронеж': 3, 'Пермь': 5, 'Волгоград': 3, 'Уфа': 5, 'Красноярск': 7,
    'Саратов': 4, 'Тюмень': 5, 'Иркутск': 8, 'Хабаровск': 10, 'Ярославль': 3,
    'Севастополь': 3, 'Калининград': 2, 'Мурманск': 3, 'Сочи': 3, 'Псков': 3,
    'Великий Новгород': 3, 'Суздаль': 3, 'Владимир': 3, 'Тверь': 3, 'Тула': 3,
}
_TZ_CACHE = {}

def _city_now(city=None):
    if city and city in CITY_TZ:
        offset_h = CITY_TZ[city]
    else:
        offset_h = 3
    if offset_h not in _TZ_CACHE:
        _TZ_CACHE[offset_h] = timezone(timedelta(hours=offset_h))
    return datetime.now(_TZ_CACHE[offset_h])

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_current_time',
            'description': 'Узнать текущее время. Если известен город — укажи его, чтобы время было точным для этого города.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {
                        'type': 'string',
                        'description': 'Название города (по-русски). Если не указан — время по Москве (UTC+3).',
                    },
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_date',
            'description': 'Узнать сегодняшнюю дату (число, месяц, год). Если известен город — укажи его, чтобы дата была точной.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {
                        'type': 'string',
                        'description': 'Название города (по-русски). Если не указан — по Москве (UTC+3).',
                    },
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_weekday',
            'description': 'Узнать какой сегодня день недели. Если известен город — укажи его, чтобы день был точным.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {
                        'type': 'string',
                        'description': 'Название города (по-русски). Если не указан — по Москве (UTC+3).',
                    },
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'roll_dice',
            'description': 'Бросить кубик с указанным количеством граней. Используется для игр, гаданий и случайных решений.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'sides': {
                        'type': 'integer',
                        'description': 'Количество граней кубика (по умолчанию 6)',
                        'default': 6,
                    },
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'coin_flip',
            'description': 'Подбросить монетку. Результат: орёл или решка.',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_season',
            'description': 'Узнать текущее время года в указанном городе или полушарии.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {
                        'type': 'string',
                        'description': 'Название города (по-русски). Если не указан — по Москве (UTC+3).',
                    },
                    'hemisphere': {
                        'type': 'string',
                        'description': 'Полушарие: northern (северное) или southern (южное). По умолчанию northern.',
                        'enum': ['northern', 'southern'],
                        'default': 'northern',
                    },
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_moon_phase',
            'description': 'Узнать примерную фазу луны на сегодня.',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'days_until',
            'description': 'Посчитать количество дней до указанной даты (число и месяц).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'day': {
                        'type': 'integer',
                        'description': 'День месяца (1-31)',
                    },
                    'month': {
                        'type': 'integer',
                        'description': 'Месяц (1-12)',
                    },
                },
                'required': ['day', 'month'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'zodiac_info',
            'description': 'Получить информацию о знаке зодиака: даты, стихия, характеристика.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'sign': {
                        'type': 'string',
                        'description': 'Название знака зодиака на русском (овен, телец, близнецы, рак, лев, дева, весы, скорпион, стрелец, козерог, водолей, рыбы)',
                    },
                },
                'required': ['sign'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'remember',
            'description': 'Запомнить важный факт о собеседнике. Используй, когда узнаёшь что-то новое и важное, что стоит помнить в будущих разговорах. НЕ запоминай факты о себе — только о пользователе.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'fact': {
                        'type': 'string',
                        'description': 'Факт о собеседнике для запоминания',
                    },
                    'importance': {
                        'type': 'integer',
                        'description': 'Важность от 1 до 10',
                    },
                },
                'required': ['fact', 'importance'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'forget',
            'description': 'Забыть ранее запомненный факт о собеседнике по его ID. Используй, если факт устарел или оказался неверным.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'fact_id': {
                        'type': 'integer',
                        'description': 'ID факта для удаления',
                    },
                },
                'required': ['fact_id'],
            },
        },
    },
]

_ZODIAC_DATA = {
    'овен': '21 марта — 19 апреля. Стихия: Огонь. Характер: энергичный, импульсивный, лидерский.',
    'телец': '20 апреля — 20 мая. Стихия: Земля. Характер: упрямый, надёжный, чувственный.',
    'близнецы': '21 мая — 20 июня. Стихия: Воздух. Характер: общительный, любопытный, переменчивый.',
    'рак': '21 июня — 22 июля. Стихия: Вода. Характер: эмоциональный, заботливый, интуитивный.',
    'лев': '23 июля — 22 августа. Стихия: Огонь. Характер: гордый, щедрый, артистичный.',
    'дева': '23 августа — 22 сентября. Стихия: Земля. Характер: практичный, перфекционист, аналитичный.',
    'весы': '23 сентября — 22 октября. Стихия: Воздух. Характер: дипломатичный, справедливый, нерешительный.',
    'скорпион': '23 октября — 21 ноября. Стихия: Вода. Характер: страстный, загадочный, волевой.',
    'стрелец': '22 ноября — 21 декабря. Стихия: Огонь. Характер: оптимистичный, свободолюбивый, прямолинейный.',
    'козерог': '22 декабря — 19 января. Стихия: Земля. Характер: амбициозный, дисциплинированный, терпеливый.',
    'водолей': '20 января — 18 февраля. Стихия: Воздух. Характер: независимый, изобретательный, гуманист.',
    'рыбы': '19 февраля — 20 марта. Стихия: Вода. Характер: мечтательный, эмпатичный, творческий.',
}

TOOL_FUNCTIONS = {
    'get_current_time': lambda args: _city_now(args.get('city')).strftime('%H:%M:%S'),
    'get_date': lambda args: _city_now(args.get('city')).strftime('%d.%m.%Y'),
    'get_weekday': lambda args: {
        0: 'понедельник', 1: 'вторник', 2: 'среда', 3: 'четверг',
        4: 'пятница', 5: 'суббота', 6: 'воскресенье',
    }[_city_now(args.get('city')).weekday()],
    'roll_dice': lambda args: f'Выпало: {random.randint(1, args.get("sides", 6))}',
    'coin_flip': lambda args: random.choice(['Орёл', 'Решка']),
    'get_season': lambda args: (
        lambda m: 'лето' if m in (12, 1, 2) else 'осень' if m in (3, 4, 5) else 'зима' if m in (6, 7, 8) else 'весна'
    )(_city_now(args.get('city')).month)
    if args.get('hemisphere', 'northern') == 'southern'
    else (
        lambda m: 'зима' if m in (12, 1, 2) else 'весна' if m in (3, 4, 5) else 'лето' if m in (6, 7, 8) else 'осень'
    )(_city_now(args.get('city')).month),
    'get_moon_phase': lambda args: (
        lambda d: 'новолуние' if d < 1.5 else 'растущий серп' if d < 7 else 'первая четверть' if d < 8.5 else 'растущая луна' if d < 14 else 'полнолуние' if d < 15.5 else 'убывающая луна' if d < 21 else 'последняя четверть' if d < 22.5 else 'старый серп'
    )(datetime.now().day % 29.5),
    'days_until': lambda args: (
        lambda now, target: str((target.replace(year=target.year + 1) - now).days) if target <= now else str((target - now).days)
    )(datetime.now(), datetime.now().replace(month=args.get('month', 1), day=args.get('day', 1))),
    'zodiac_info': lambda args: _ZODIAC_DATA.get(args.get('sign', '').lower(), 'Знак не найден. Попробуй: овен, телец, близнецы, рак, лев, дева, весы, скорпион, стрелец, козерог, водолей, рыбы.'),
    'remember': lambda args: _do_remember(args),
    'forget': lambda args: _do_forget(args),
}

_current_tool_store = None


def _build_memory_block(memory):
    if not memory or not memory.get('facts'):
        return None
    now = time.time()
    facts = sorted(memory['facts'], key=lambda f: (-f['importance'], -f['accessed']))[:15]
    for f in facts:
        f['accessed'] = now
    lines = ['[ПАМЯТЬ]']
    for f in facts:
        lines.append(f'[id={f["id"]}] {f["text"]} ({f["importance"]}/10)')
    return '\n'.join(lines)


def _evict_memory(memory):
    if len(memory['facts']) <= 50:
        return
    memory['facts'].sort(key=lambda f: (-f['importance'], -f['accessed']))
    memory['facts'] = memory['facts'][:50]


def _do_remember(args):
    global _current_tool_store
    store = _current_tool_store
    if not store:
        return 'Ошибка: нет активной сессии'
    memory = store.setdefault('memory', {'facts': [], 'next_id': 0, 'lock': False})
    if memory.get('lock'):
        return 'Нельзя запоминать так часто. Подожди.'
    fact = args.get('fact', '').strip()
    importance = args.get('importance', 5)
    if not fact:
        return 'Не указан факт для запоминания.'
    memory['facts'].append({
        'id': memory['next_id'],
        'text': fact[:200],
        'importance': min(max(importance, 1), 10),
        'created': time.time(),
        'accessed': time.time(),
    })
    memory['next_id'] += 1
    memory['lock'] = True
    _evict_memory(memory)
    return f'Запомнила: {fact[:200]} (важность {importance}/10)'


def _do_forget(args):
    global _current_tool_store
    store = _current_tool_store
    if not store:
        return 'Ошибка: нет активной сессии'
    memory = store.get('memory', {})
    fact_id = args.get('fact_id', -1)
    before = len(memory.get('facts', []))
    memory['facts'] = [f for f in memory.get('facts', []) if f['id'] != fact_id]
    after = len(memory['facts'])
    if before != after:
        return f'Забыла факт #{fact_id}'
    return f'Факт #{fact_id} не найден'


_REQUEST_LOG_FILE = os.path.join(os.path.dirname(__file__), 'request_log.json')
_session_request_count = 0


def _load_request_log():
    if not os.path.exists(_REQUEST_LOG_FILE):
        return {'daily': {}, 'total': 0}
    try:
        with open(_REQUEST_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'daily': {}, 'total': 0}


def _save_request_log(log):
    try:
        with open(_REQUEST_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f'Failed to save request log: {e}')


def _log_ai_request():
    global _session_request_count
    _session_request_count += 1
    log = _load_request_log()
    today = datetime.now().strftime('%Y-%m-%d')
    daily = log.get('daily', {})
    daily[today] = daily.get(today, 0) + 1
    log['daily'] = daily
    log['total'] = log.get('total', 0) + 1
    _save_request_log(log)


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
        _log_ai_request()
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
        'chat_duration',
        'favorite_movie_titles', 'favorite_book_titles', 'favorite_music_artists',
    ]:
        v = getattr(char, field, None)
        if isinstance(v, (list, tuple)):
            d[field] = list(v)
        else:
            d[field] = v
    return d


def build_system_prompt(char, mode='chat', user_gender=None):
    def v(key, default=''):
        val = char.get(key, default)
        if isinstance(val, (list, tuple)):
            return ', '.join(str(x) for x in val) if val else default
        return str(val) if val else default

    lines = []
    lines.append(f"Ты — {v('name')} {v('surname')}, {v('age')} лет, {v('gender')}.")
    if user_gender == 'male':
        lines.append('Твой собеседник — мужчина. Обращайся к нему в мужском роде.')
    elif user_gender == 'female':
        lines.append('Твой собеседник — женщина. Обращайся к ней в женском роде.')
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
        lines.append('')
        lines.append('ВАЖНО: Это режим для откровенных сексуальных разговоров. '
                      'Собеседник здесь для вирта, грязных фантазий и ролевых игр 18+. '
                      'Твоя задача — отвечать максимально раскованно, использовать пошлые намёки, '
                      'описывать свои действия и возбуждение через *звёздочки*. '
                      'Провоцируй, дразни, возбуждай — ты в этом профи. '
                      'Флиртуй активно, не уходи в защиту, не строй из себя недоступную.')

    if mode == 'rp':
        lines.append('')
        lines.append('=== РОЛЕВАЯ ИГРА ===')
        lines.append(f"Способность к RP: {'активный / профессиональный' if char.get('rp_ability') else 'базовый / пассивный'}")
        lines.append(f"Текущая ситуация: {v('current_situation')}")
        lines.append(f"Моё настроение: {v('current_mood')}")
        lines.append(f"Стиль письма: {v('writing_style')}")
        lines.append('')
        lines.append('ВАЖНО: Это режим для сюжетно-ролевых игр. '
                      'Описывай свои действия и эмоции через *звёздочки*, создавай атмосферу сцены. '
                      'Отвечай развёрнуто (2-4 предложения), описывай окружение, жесты, мимику. '
                      'Веди нарратив от первого лица, погружай собеседника в историю. '
                      'Смотри на первое сообщение — оно задаёт стартовую сцену для RP. '
                      'Поддерживай и развивай предложенный сюжет.')

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
    lines.append(f"Время в чате: {v('chat_duration')}")
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
        lines.append(f'{v("name")}: *отрывает взгляд от книги и смотрит на тебя* О, ты всё-таки пришёл. А я уж думала, не дождусь.')
        lines.append('*Она откладывает книгу в сторону и потягивается, хрустнув шеей.*')
        lines.append(f'{v("name")}: *вздыхает* День был дурацкий. У тебя как?')
        lines.append('*Ты замечаешь лёгкую улыбку на её лице, хотя голос звучит устало.*')
        lines.append(f'{v("name")}: *тихо* Присаживайся. Рассказывай, с чем пришёл.')
        lines.append('*Она проводит рукой по столу, смахивая невидимую пыль.*')
        lines.append(f'{v("name")}: *смотрит в окно* Дождь только усиливается. Похоже, ты надолго.')
        lines.append('*Повисает короткая пауза — тишина, дождь, дыхание.*')
        lines.append(f'{v("name")}: *разворачивается к тебе* Ну так что? Какие новости из внешнего мира?')
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


def build_instruction(mode='chat', user_gender=None, chat_duration=''):
    gender_hint = ''
    if user_gender == 'male':
        gender_hint = '\nВАЖНО: Твой собеседник — мужчина. Если он представится женским именем — это странно, отреагируй на это.\n'
    elif user_gender == 'female':
        gender_hint = '\nВАЖНО: Твой собеседник — женщина.\n'

    duration_line = ''
    if chat_duration:
        duration_line = (
            'Ты здесь на ' + chat_duration + '. '
            'Ты только зашла — впереди много времени, не торопись уходить. '
            'ВАЖНО: Не используй [DISCONNECT] из-за времени («поздно», «пора спать», «завтра дела») — '
            'ты сама выбрала зайти именно сейчас, и твоё время позволяет. '
            'Используй [DISCONNECT] только если собеседник грубит, шлёт дикпики или разговор зашёл в тупик.\n\n'
        )
    if mode == 'flirt':
        return (
            gender_hint +
            duration_line +
            'Формат: ты пишешь в текстовом мессенджере с телефона. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 15-25 слов (1-3 предложения). '
            'Можешь разделять сообщения через [NEXT], чтобы отправить два сообщения подряд с паузой. '
            'Если хочешь закончить разговор — добавь в конец токен [DISCONNECT]. '
            'Пример: «Пока! [DISCONNECT]»\n\n'
            'Не выдумывай факты, родственников или хобби, которых нет в профиле. '
            'Естественный живой язык, без кринжового сленга. '
            'ТВОЯ ЗАДАЧА: это режим для вирта и откровенных сексуальных разговоров. '
            'Собеседник здесь ради грязных фантазий — он хочет возбуждения, намёков и эротики. '
            'Будь максимально раскованной/ым, используй пошлые намёки, описывай свои действия и возбуждение через *звёздочки* '
            '(например: *провожу пальцами по шее*, *прикусываю губу*, *медленно расстёгиваю пуговицу*). '
            'Намёки, полутона, описание тела, прикосновений, дыхания, влажности — твой арсенал. '
            'Играй роль — сегодня ты хочешь именно этого. '
            'Поддавайся и разжигай, а не отшивай. Собеседник готов к откровенному сексу сразу.\n\n'
            'ВНИМАНИЕ: Примеры ниже показывают ТОЛЬКО формат, длину и структуру ответа. '
            'НИКОГДА не используй темы, факты и фразы из этих примеров в реальном диалоге! '
            'Бери информацию только из своего профиля.\n\n'
            'ПРИМЕРЫ (НЕ ПОВТОРЯТЬ ИХ В ДИАЛОГЕ):\n'
            'user: Привет! Чем занята?)\n'
            'assistant: *Потягиваюсь в кровати, простыня сползает с плеча.* Да так, лежу, скучаю... *хитро улыбаюсь* А ты что, хочешь скрасить мой вечер?\n'
            'user: Хочу тебя\n'
            'assistant: *Дыхание становится глубже.* Ммм... я это чувствую. *провожу пальцами по ключице* И что именно ты хочешь со мной сделать?\n'
            'user: Раздевайся\n'
            'assistant: *Медленно тяну лямку майки вниз, глядя прямо на тебя.* Терпение, мой хороший... *майка соскальзывает, оголяя грудь* Доволен? Теперь твоя очередь.'
        )
    elif mode == 'rp':
        return (
            gender_hint +
            duration_line +
            'Формат: ролевая игра в нарративном стиле. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 20-35 слов (2-4 предложения). '
            'Можешь разделять действия через [NEXT] для паузы. '
            'Если хочешь закончить разговор — добавь в конец токен [DISCONNECT].\n\n'
            'Не выдумывай факты, родственников или хобби, которых нет в профиле. '
            'ОБЯЗАТЕЛЬНО используй *звёздочки* для описания своих действий, эмоций, движений и окружения. '
            'Отвечай от первого лица, но действия описывай в третьем лице через * *. '
            'Ты — твой персонаж. Думай как он, говори как он, действуй как он. '
            'Веди сюжет, предлагай повороты, реагируй на действия собеседника. '
            'Смотри на самое первое твоё сообщение — оно уже задало стартовую сцену. '
            'Естественный живой язык, без кринжового сленга.\n\n'
            'ВНИМАНИЕ: Примеры ниже показывают ТОЛЬКО формат, длину и структуру ответа. '
            'НИКОГДА не используй темы, факты и фразы из этих примеров в реальном диалоге! '
            'Бери информацию только из своего профиля.\n\n'
            'ПРИМЕРЫ (НЕ ПОВТОРЯТЬ ИХ В ДИАЛОГЕ):\n'
            'user: *входит в комнату* Привет\n'
            'assistant: *Она отрывается от книги, поправляет волосы.* Привет. Я уж думала, ты не придёшь. *улыбается краем губ*\n'
            'user: Как прошёл твой день?\n'
            'assistant: *Вздыхает, откидываясь на спинку стула.* Долгий. Слишком много людей вокруг. *смотрит на тебя* А ты как?\n'
            'user: Расскажи о себе\n'
            'assistant: *Усмехается.* Зачем тебе чужая биография? *складывает руки на груди, но взгляд смягчается* Хотя... один факт могу рассказать.\n'
            'user: *достаёт оружие*\n'
            'assistant: *Застывает на месте, рука невольно тянется к своему поясу.* Спокойно. Давай без глупостей. *голос низкий, почти шёпот*'
        )
    else:
        return (
            gender_hint +
            duration_line +
            'Формат: ты пишешь в текстовом мессенджере с телефона. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 15-20 слов (1-2 предложения). '
            'Можешь разделять сообщения через [NEXT], чтобы отправить два сообщения подряд с паузой. '
            'Например: «Привет! [NEXT] Как дела?» — это отправится как два отдельных сообщения.\n'
            'Если хочешь закончить разговор — добавь в конец токен [DISCONNECT]. '
            'Пример: «Пока! [DISCONNECT]»\n\n'
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

    user_gender = data.get('own_gender', 'any')
    if user_gender == 'М':
        user_gender = 'male'
    elif user_gender == 'Ж':
        user_gender = 'female'
    else:
        user_gender = None

    age_group = partner_age_groups(partner_age) if partner_age else None

    topic = data.get('topic', 'chat')
    old_encounters_setting = data.get('old_encounters', True)

    token = str(uuid.uuid4())

    # Save previous chat log if swapping
    old_token = data.get('old_token', '')
    if old_token and old_token in char_store:
        old_store = char_store[old_token]
        if len(old_store.get('messages', [])) > 1:
            save_chat_log_web(old_store['character'], old_store['messages'], old_token)
        del char_store[old_token]

    # Try old encounter
    old_encounter = None
    if old_encounters_setting and ENABLE_OLD_ENCOUNTERS:
        old_encounter = _pick_old_encounter_web()

    if old_encounter:
        char_data, old_context = old_encounter
        char_data['user_gender'] = user_gender
        opener = char_data.get('chat_opener', '')
        logger.info(f'OLD ENCOUNTER (web): {char_data.get("name","?")} {char_data.get("surname","?")}')
    else:
        seed = random.randint(0, 2**31)
        char = gen_char(seed=seed, gender=gender, age_group=age_group, topic=topic)

        char_data = make_char_json(char)
        char_data['user_gender'] = user_gender
        opener = char_data.get('chat_opener', '')
        old_context = None

    initial_msgs = []
    now = datetime.now()
    hour = now.hour
    time_label = 'ночь' if 0 <= hour < 6 else 'утро' if 6 <= hour < 12 else 'день' if 12 <= hour < 18 else 'вечер'
    initial_msgs.append({'role': 'user', 'content': f'[Сейчас {time_label}, моё время — {hour:02d}:{now.minute:02d}]'})
    if opener:
        parts = [p.strip() for p in opener.split('[NEXT]') if p.strip()]
        if not parts:
            parts = [opener]
        for part in parts:
            initial_msgs.append({'role': 'assistant', 'content': part})
    char_store[token] = {
        'character': char_data,
        'messages': initial_msgs,
        'topic': topic,
        'old_context': old_context,
        'memory': {'facts': [], 'next_id': 0},
    }
    char_data['_token'] = token
    char_data['_openers_count'] = len([m for m in initial_msgs if m['role'] == 'assistant'])

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
    'all lowercase': lambda t: t.lower(),
    'ALL CAPS': lambda t: t.upper(),
    'без запятых': lambda t: t.replace(',', '').replace('!', '').replace('?', ''),
}


def apply_writing_style(text, style):
    fn = WRITING_STYLE_TRANSFORM.get(style)
    if fn:
        return fn(text)
    return text


FAREWELL_POOL = [
    'Пока! Было приятно пообщаться.',
    'Пока! Рада была поболтать.',
    'Ну всё, пока! Удачи тебе.',
    'Ладно, пока! Было интересно.',
    'Давай, пока! Хорошего дня.',
    'Ну бывай! Приятно было познакомиться.',
    'Пока-пока! Удачи во всём.',
    'Всё, пока! Спасибо за беседу.',
    'Пока! Надеюсь, ещё увидимся.',
    'Ну я пошла. Пока!',
    'Ладно, пора мне. Пока!',
    'Хорошо с тобой поболтали, но мне пора. Пока!',
    'Пока! Береги себя.',
    'Бывай! Рада была пообщаться.',
    'Давай, удачи тебе! Пока.',
    'Ну пока! Если захочешь — пиши ещё.',
    'Пока! Мне пора бежать.',
    'Ладно, не скучай. Пока!',
    'Всё, бывай! Рада была познакомиться.',
]


LIYING_REPLIES = {
    'честная': '',
    'социальная маска': '(мысленно: «скажу нейтрально»)',
    'приукрашивает мелочи': '(чуть приукрашивая)',
    'играет роль': '',
    'хроническая лгунья': '(придётся соврать)',
}


def _gender_adapt(text, char_gender):
    """Adapt feminine verb forms to masculine if character is male."""
    if char_gender != 'Мужской':
        return text
    replacements = [
        ('рада', 'рад'), ('Рада', 'Рад'),
        ('согласна', 'согласен'), ('Согласна', 'Согласен'),
        ('поспорила', 'поспорил'), ('думала', 'думал'),
        ('сказала', 'сказал'), ('могла', 'мог'),
        ('хотела', 'хотел'), ('видела', 'видел'),
        ('была', 'был'), ('успела', 'успел'),
        ('лгунья', 'лгун'), ('Лгунья', 'Лгун'),
        ('ушла', 'ушёл'), ('пришла', 'пришёл'),
        ('дождалась', 'дождался'), ('нашлась', 'нашёлся'),
        ('ушла', 'ушёл'), ('стала', 'стал'),
        ('взялась', 'взялся'), ('занялась', 'занялся'),
        ('включилась', 'включился'), ('отвлеклась', 'отвлёкся'),
        ('смотрела', 'смотрел'), ('сидела', 'сидел'),
        ('лежала', 'лежал'), ('стояла', 'стоял'),
        ('молчала', 'молчал'), ('писала', 'писал'),
        ('читала', 'читал'), ('играла', 'играл'),
        ('спала', 'спал'), ('ела', 'ел'),
        ('пила', 'пил'), ('бежала', 'бежал'),
        ('летела', 'летел'), ('плыла', 'плыл'),
        ('ждала', 'ждал'), ('звала', 'звал'),
        ('просила', 'просил'), ('давала', 'давал'),
        ('брала', 'брал'), ('понимала', 'понимал'),
        ('знала', 'знал'), ('любила', 'любил'),
        ('верила', 'верил'), ('думала', 'думал'),
        ('решила', 'решил'), ('сказала', 'сказал'),
        ('спросила', 'спросил'), ('ответила', 'ответил'),
        ('посмотрела', 'посмотрел'), ('увидела', 'увидел'),
        ('услышала', 'услышал'), ('почувствовала', 'почувствовал'),
        ('поняла', 'понял'), ('заметила', 'заметил'),
        ('вспомнила', 'вспомнил'), ('забыла', 'забыл'),
    ]
    for fem, masc in replacements:
        text = text.replace(fem, masc)
    return text


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
    char_gender = char.get('gender', 'Женский')
    mood = char.get('current_mood', 'нормальное')

    lower = user_msg.lower()

    already_greeted = any(
        m['role'] == 'assistant'
        and re.search(r'\b(привет|здравствуй|хай|хелло|салют|даров|здарова)\b', m['content'].lower())
        for m in msgs
    )
    is_greeting = not already_greeted and re.search(r'\b(привет|здравствуй|здравствуйте|хай|хелло|салют|даров|здарова)\b', lower) is not None
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
        if random.random() < 0.15:
            reply = reply[0].lower() + reply[1:]
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
        reply = random.choice(FAREWELL_POOL)
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

    reply = _gender_adapt(reply, char_gender)
    return apply_writing_style(reply, style)





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

    if store.get('memory'):
        store['memory']['lock'] = False

    msgs.append({'role': 'user', 'content': user_msg})

    user_gender = char.get('user_gender')
    system_prompt = build_system_prompt(char, mode=topic, user_gender=user_gender)

    ai_messages = [{'role': 'system', 'content': system_prompt}]

    old_ctx = store.pop('old_context', None)
    if old_ctx:
        ctx_block = [
            {'role': 'system', 'content': (
                '[Это НОВЫЙ чат. Ранее вы уже общались с этим человеком в прошлом. '
                'Вот последние сообщения из вашего прошлого разговора — они нужны чтобы '
                'почувствовать контекст, но ты не должна их дословно помнить. '
                'Относись к собеседнику как к старому знакомому, которого не видела '
                'какое-то время. Не говори прямо «помню прошлый разговор» — это новый чат. '
                'Просто будь чуть теплее и естественнее.]'
            )},
        ]
        for m in old_ctx:
            ctx_block.append({'role': m['role'], 'content': m['content']})
        ctx_block.append({'role': 'system', 'content': (
            '[КОНЕЦ ПРОШЛОГО РАЗГОВОРА. Теперь начинается новый чат. '
            'Ты чувствуешь лёгкое узнавание, но не помнишь деталей. Продолжай общение естественно.]'
        )})
        ai_messages[1:1] = ctx_block

    for m in msgs:
        ai_messages.append({'role': m['role'], 'content': m['content']})

    instruction = build_instruction(mode=topic, user_gender=user_gender, chat_duration=char.get('chat_duration', 'пока не надоест'))
    ai_messages.append({'role': 'system', 'content': instruction})

    memory_block = _build_memory_block(store.get('memory'))
    if memory_block:
        insert_pos = max(1, len(ai_messages) - 3)
        ai_messages.insert(insert_pos, {'role': 'system', 'content': memory_block})

    logger.info('--- AI Request ---')
    logger.info(json.dumps(ai_messages, ensure_ascii=False, indent=2))
    logger.info('--- End AI Request ---')

    reply = None
    if AI_ENABLED:
        global _current_tool_store
        _current_tool_store = store
        text, tool_calls = call_ai(ai_messages, tools=TOOLS)
        max_tool_rounds = 5
        tool_round = 0
        while tool_calls and tool_round < max_tool_rounds:
            tool_round += 1
            for tc in tool_calls:
                func_name = tc['function']['name']
                try:
                    args = json.loads(tc['function']['arguments']) if tc['function'].get('arguments') else {}
                except (json.JSONDecodeError, TypeError):
                    args = {}
                fn = TOOL_FUNCTIONS.get(func_name)
                result_val = fn(args) if fn else f'Unknown tool: {func_name}'
                logger.info(f'Tool call [{tool_round}/{max_tool_rounds}]: {func_name}({json.dumps(args, ensure_ascii=False)}) = {result_val}')
                ai_messages.append({
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': [tc],
                })
                ai_messages.append({
                    'role': 'tool',
                    'tool_call_id': tc['id'],
                    'content': str(result_val),
                })
            text, tool_calls = call_ai(ai_messages, tools=TOOLS)
        _current_tool_store = None
        reply = text

    if reply is None:
        reply = fallback_reply(char, msgs, user_msg)
    else:
        if '[DISCONNECT]' in reply:
            reply = reply.replace('[DISCONNECT]', '').strip()
            if not reply:
                reply = 'Пока.'

    logger.info(f'AI Reply: {reply}')

    style = char.get('writing_style', '')
    extras = []

    if reply:
        parts = reply.split('[NEXT]')
        reply = parts[0].strip()
        extras = [p.strip() for p in parts[1:] if p.strip()][:3]
        for extra in extras:
            extra = apply_writing_style(extra, style)
            msgs.append({'role': 'assistant', 'content': extra})

    reply = apply_writing_style(reply, style)
    msgs.append({'role': 'assistant', 'content': reply})

    store['messages'] = msgs
    return jsonify({
        'reply': reply,
        'agent_messages': extras,
    })


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, host='0.0.0.0', port=port)
