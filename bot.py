import random
import json
import uuid
import os
import re
import re
import sys
import hashlib
import asyncio
import urllib.request
import logging
import time
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from generators.char_generator import generate as gen_char

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

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

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', '').rstrip('/')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
PROVIDER_TYPE = os.environ.get('PROVIDER_TYPE', 'openai').lower()

BOT_PROXY_URL = os.environ.get('BOT_PROXY_URL', '') or None
BOT_USE_PROXY = os.environ.get('BOT_USE_PROXY', 'false').lower() == 'true'

# --- Multi-provider support ---
# Format in .env:
#   PROVIDER_COUNT=2
#   PROVIDER1_NAME=Deepseek
#   PROVIDER1_TYPE=deepseek
#   PROVIDER1_BASE_URL=https://api.deepseek.com/v1
#   PROVIDER1_API_KEY=sk-xxx
#   PROVIDER1_MODEL=deepseek-v4-flash
# If PROVIDER_COUNT is not set, falls back to single OPENAI_* + PROVIDER_TYPE

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

def _check_connection(label, proxy_url=None):
    try:
        req = urllib.request.Request('https://api.telegram.org')
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({'https': proxy_url, 'http': proxy_url}) if proxy_url
            else urllib.request.ProxyHandler({})
        )
        opener.open(req, timeout=10)
        logger.info(f'Connection check [{label}]: OK')
        return True
    except Exception as e:
        logger.warning(f'Connection check [{label}]: FAILED ({e})')
        return False

_check_connection('direct')
if BOT_USE_PROXY and BOT_PROXY_URL:
    _check_connection('proxy', BOT_PROXY_URL)

if not BOT_TOKEN:
    logger.error('BOT_TOKEN not set in .env')
    sys.exit(1)

ALLOWED_IDS_STR = os.environ.get('ALLOWED_IDS', '')
ALLOWED_IDS = set()
if ALLOWED_IDS_STR:
    for part in ALLOWED_IDS_STR.split(','):
        part = part.strip()
        if part:
            try:
                ALLOWED_IDS.add(int(part))
            except ValueError:
                pass

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

def save_chat_log(uid, char_data, messages):
    if not CHAT_SAVE_IDS or uid not in CHAT_SAVE_IDS:
        return
    try:
        chat_dir = os.path.join(CHATS_DIR, str(uid))
        os.makedirs(chat_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name = char_data.get('name', 'unknown')
        surname = char_data.get('surname', '')
        raw = f'{timestamp}_{name}_{surname}'.encode('utf-8')
        hash_suffix = hashlib.md5(raw).hexdigest()[:8]
        filename = f'{timestamp}_{hash_suffix}.json'
        filepath = os.path.join(chat_dir, filename)
        log = {
            'chat_id': uid,
            'timestamp': timestamp,
            'character': {k: v for k, v in char_data.items() if k != 'system_prompt'},
            'messages': messages,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        logger.info(f'Chat log saved for user {uid}: {filename}')
    except Exception as e:
        logger.error(f'Failed to save chat log for user {uid}: {e}')

def _load_old_chat_logs(uid):
    logs = []
    chat_dir = os.path.join(CHATS_DIR, str(uid))
    if not os.path.isdir(chat_dir):
        return logs
    for fname in os.listdir(chat_dir):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(chat_dir, fname), encoding='utf-8') as f:
                logs.append(json.load(f))
        except Exception as e:
            logger.error(f'Failed to load chat log {fname}: {e}')
    return logs

def _pick_old_encounter(uid):
    if not ENABLE_OLD_ENCOUNTERS:
        return None
    chance = 0.03 + random.random() * 0.02
    if random.random() >= chance:
        return None
    logs = _load_old_chat_logs(uid)
    if not logs:
        return None
    log = random.choice(logs)
    char_data = log.get('character', {})
    all_msgs = log.get('messages', [])
    # take last 15 messages that are user/assistant pairs
    old_msgs = [m for m in all_msgs if m['role'] in ('user', 'assistant')][-15:]
    if not old_msgs:
        return None
    logger.info(f'Old encounter! User {uid} re-meets {char_data.get("name","?")}')
    return char_data, old_msgs

def is_allowed(user_id):
    return not ALLOWED_IDS or user_id in ALLOWED_IDS

user_data = {}
DATA_FILE = os.path.join(os.path.dirname(__file__), 'bot_data.json')

def save_user_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f'Failed to save user data: {e}')

def load_user_data():
    global user_data
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        for uid, data in loaded.items():
            uid = int(uid)
            if uid not in user_data:
                user_data[uid] = data
                user_data[uid].setdefault('settings', {
                    'partner_gender': 'any',
                    'partner_age': [],
                    'own_gender': 'any',
                    'topic': 'chat',
                    'old_encounters': False,
                })
                user_data[uid]['settings'].setdefault('old_encounters', False)
    except Exception as e:
        logger.error(f'Failed to load user data: {e}')

load_user_data()

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

_BUILTIN_TOOLS = [
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

_TOOL_FUNCTIONS_MAP = {
    'get_current_time': lambda args: _city_now(args.get('city')).strftime('%H:%M:%S'),
    'get_date': lambda args: _city_now(args.get('city')).strftime('%d.%m.%Y'),
    'get_weekday': lambda args: {
        0: 'понедельник', 1: 'вторник', 2: 'среда', 3: 'четверг',
        4: 'пятница', 5: 'суббота', 6: 'воскресенье',
    }[_city_now(args.get('city')).weekday()],
    'roll_dice': lambda args: f'Выпало: {random.randint(1, args.get("sides", 6))}',
    'coin_flip': lambda args: random.choice(['Орёл', 'Решка']),
    'get_season': lambda args: _calc_season(args.get('hemisphere', 'northern'), args.get('city')),
    'get_moon_phase': lambda args: _calc_moon_phase(),
    'days_until': lambda args: _calc_days_until(args.get('day', 1), args.get('month', 1)),
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

def _calc_season(hemisphere, city=None):
    m = _city_now(city).month
    if hemisphere == 'southern':
        if m in (12, 1, 2): return 'лето'
        if m in (3, 4, 5): return 'осень'
        if m in (6, 7, 8): return 'зима'
        return 'весна'
    else:
        if m in (12, 1, 2): return 'зима'
        if m in (3, 4, 5): return 'весна'
        if m in (6, 7, 8): return 'лето'
        return 'осень'

def _calc_moon_phase():
    d = datetime.now().day
    cycle_pos = d % 29.5
    if cycle_pos < 1.5: return 'новолуние'
    if cycle_pos < 7: return 'растущий серп'
    if cycle_pos < 8.5: return 'первая четверть'
    if cycle_pos < 14: return 'растущая луна'
    if cycle_pos < 15.5: return 'полнолуние'
    if cycle_pos < 21: return 'убывающая луна'
    if cycle_pos < 22.5: return 'последняя четверть'
    return 'старый серп'

def _calc_days_until(day, month):
    now = datetime.now()
    target = now.replace(month=month, day=day)
    if target <= now:
        target = target.replace(year=target.year + 1)
    return str((target - now).days)

def get_tools():
    admin_config = load_admin_config()
    disabled = admin_config.get('disabled_tools', [])
    return [t for t in _BUILTIN_TOOLS if t['function']['name'] not in disabled]

def get_tool_functions():
    return _TOOL_FUNCTIONS_MAP

ADMIN_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'admin_settings.json')

def load_admin_config():
    if not os.path.exists(ADMIN_CONFIG_FILE):
        return {'disabled_tools': []}
    try:
        with open(ADMIN_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'disabled_tools': []}

def save_admin_config(config):
    try:
        with open(ADMIN_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f'Failed to save admin config: {e}')

def call_ai(messages, tools=None):
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
        return text, tool_calls
    except Exception as e:
        logger.error(f'AI call failed: {e}')
        return None, None

def check_deepseek_balance():
    url = OPENAI_BASE_URL.rstrip('/')
    if url.endswith('/v1'):
        url = url[:-3]
    url = url.rstrip('/') + '/user/balance'
    req = urllib.request.Request(url, method='GET')
    req.add_header('Accept', 'application/json')
    if OPENAI_API_KEY:
        req.add_header('Authorization', f'Bearer {OPENAI_API_KEY}')
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        return data
    except Exception as e:
        logger.error(f'Balance check failed: {e}')
        return None

_REQUEST_LOG_FILE = os.path.join(os.path.dirname(__file__), 'request_log.json')
_session_request_count = 0
_session_start = time.time()

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

def _get_request_stats():
    log = _load_request_log()
    daily = log.get('daily', {})
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = daily.get(today, 0)
    last_7 = 0
    last_30 = 0
    from datetime import timedelta
    for i in range(30):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        if i < 7:
            last_7 += daily.get(day, 0)
        last_30 += daily.get(day, 0)
    total = log.get('total', 0)
    return _session_request_count, last_7, last_30, total

def format_balance(data):
    balance_infos = data.get('balance_infos', [])
    if not balance_infos:
        return 'Не удалось получить баланс.'
    info = balance_infos[0]
    currency = info.get('currency', 'USD')
    total = info.get('total_balance', '0')
    topped_up = info.get('topped_up_balance', '0')
    session, week, month, all_time = _get_request_stats()
    return (
        f'💰 *Баланс Deepseek*\n\n'
        f'Всего: `{total}` {currency}\n'
        f'Пополнено: `{topped_up}` {currency}\n\n'
        f'📊 *Статистика AI запросов*\n'
        f'За текущий запуск: {session}\n'
        f'За 7 дней: {week}\n'
        f'За 30 дней: {month}\n'
        f'Всего: {all_time}'
    )

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

def build_instruction(mode='chat', user_gender=None, oversharing=5, chat_duration=''):
    gender_hint = ''
    if user_gender == 'male':
        gender_hint = '\nВАЖНО: Твой собеседник — мужчина. Если он представится женским именем — это странно, отреагируй на это.\n'
    elif user_gender == 'female':
        gender_hint = '\nВАЖНО: Твой собеседник — женщина.\n'

    if mode == 'flirt':
        return (
            gender_hint +
            'Формат: ты пишешь в текстовом мессенджере с телефона. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 15-25 слов (1-3 предложения). '
            'Можешь разделять сообщения через [NEXT], чтобы отправить два сообщения подряд с паузой. '
            'Ты здесь на ' + chat_duration + '. Ты только зашла — впереди много времени, не торопись уходить. '
            'Если хочешь закончить разговор — добавь в конец токен [DISCONNECT]. '
            'Пример: «Пока! [DISCONNECT]»\n'
            'ВАЖНО: Не используй [DISCONNECT] из-за времени («поздно», «пора спать», «завтра дела») — '
            'ты сама выбрала зайти именно сейчас, и твоё время позволяет. '
            'Используй [DISCONNECT] только если собеседник грубит, шлёт дикпики или разговор зашёл в тупик.\n\n'
            f'Твой уровень откровенности — {oversharing}/10. '
            'Если не хочешь отвечать на личные вопросы — уклоняйся или переводи в пошлость.\n\n'
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
            'Формат: ролевая игра в нарративном стиле. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 20-35 слов (2-4 предложения). '
            'Можешь разделять действия через [NEXT] для паузы. '
            'Ты здесь на ' + chat_duration + '. Ты только зашла — впереди много времени, не торопись уходить. '
            'Если хочешь закончить разговор — добавь в конец токен [DISCONNECT].\n'
            'ВАЖНО: Не используй [DISCONNECT] из-за времени («поздно», «пора спать», «завтра дела») — '
            'ты сама выбрала зайти именно сейчас, и твоё время позволяет. '
            'Используй [DISCONNECT] только если собеседник грубит или разговор зашёл в тупик.\n\n'
            f'Твой уровень откровенности — {oversharing}/10. '
            'Если персонаж не хочет отвечать на вопрос — он уклоняется или переводит тему.\n\n'
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
            'Формат: ты пишешь в текстовом мессенджере с телефона. '
            'Следуй своему профилю выше. Пиши МАКСИМУМ 15-20 слов (1-2 предложения). '
            'Можешь разделять сообщения через [NEXT], чтобы отправить два сообщения подряд с паузой. '
            'Например: «Привет! [NEXT] Как дела?» — это отправится как два отдельных сообщения.\n'
            'Ты здесь на ' + chat_duration + '. Ты только зашла — впереди много времени, не торопись уходить. '
            'Если хочешь закончить разговор — добавь в конец токен [DISCONNECT]. '
            'Пример: «Пока! [DISCONNECT]»\n'
            'ВАЖНО: Не используй [DISCONNECT] из-за времени («поздно», «пора спать», «завтра дела») — '
            'ты сама выбрала зайти именно сейчас, и твоё время позволяет. '
            'Используй [DISCONNECT] только если собеседник грубит, шлёт дикпики или разговор зашёл в тупик.\n\n'
            f'Твой уровень откровенности — {oversharing}/10. Чем он ниже, тем чаще ты уклоняешься от личных вопросов (возраст, город, работа, отношения). '
            'Если не хочешь отвечать — уклоняйся или меняй тему.\n\n'
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

def _gender_adapt(text, char_gender):
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
        ('стала', 'стал'), ('взялась', 'взялся'),
        ('занялась', 'занялся'), ('включилась', 'включился'),
        ('отвлеклась', 'отвлёкся'), ('смотрела', 'смотрел'),
        ('сидела', 'сидел'), ('лежала', 'лежал'),
        ('стояла', 'стоял'), ('молчала', 'молчал'),
        ('писала', 'писал'), ('читала', 'читал'),
        ('играла', 'играл'), ('спала', 'спал'),
        ('ела', 'ел'), ('пила', 'пил'),
        ('бежала', 'бежал'), ('летела', 'летел'),
        ('плыла', 'плыл'), ('ждала', 'ждал'),
        ('звала', 'звал'), ('просила', 'просил'),
        ('давала', 'давал'), ('брала', 'брал'),
        ('понимала', 'понимал'), ('знала', 'знал'),
        ('любила', 'любил'), ('верила', 'верил'),
        ('думала', 'думал'), ('решила', 'решил'),
        ('спросила', 'спросил'), ('ответила', 'ответил'),
        ('посмотрела', 'посмотрел'), ('увидела', 'увидел'),
        ('услышала', 'услышал'), ('почувствовала', 'почувствовал'),
        ('поняла', 'понял'), ('заметила', 'заметил'),
        ('вспомнила', 'вспомнил'), ('забыла', 'забыл'),
    ]
    for fem, masc in replacements:
        text = text.replace(fem, masc)
    return text

def apply_writing_style(text, style):
    if style == 'all lowercase':
        return text.lower()
    elif style == 'ALL CAPS':
        return text.upper()
    elif style == 'без запятых':
        return text.replace(',', '').replace('!', '').replace('?', '')
    return text


_re_sentence_split = re.compile(r'(.*?(?:[.!?](?:\s|$)|$))')


def _split_sentences(text):
    parts = _re_sentence_split.findall(text)
    return [p.strip() for p in parts if p.strip()]


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

EVASIVE_ANSWERS = [
    'Не скажу, извини',
    'Секрет',
    'А тебе зачем?',
    'Это личное',
    'Я не хочу об этом говорить',
    'Может, не надо?',
    'Давай не об этом',
    'Пропустим',
    'Я не отвечу на этот вопрос',
    'Без комментариев',
    'Не люблю говорить о себе',
    'Я пас',
    'Давай сменим тему',
    'Оставлю это при себе',
]

PERSONAL_QUESTION_PATTERNS = [
    (r'\b(сколько тебе лет|твой возраст|возраст|тебе сколько|старше|младше)\b', 'age'),
    (r'\b(откуда ты|где ты жив[её]шь|твой город|из какого ты города|откуда)\b', 'city'),
    (r'\b(где работаешь|кем работаешь|твоя профессия|кто по профессии|где трудишься)\b', 'profession'),
    (r'\b(где учишься|где уч[иё]шься|твоя уч[её]ба)\b', 'education'),
    (r'\b(как тебя зовут|тво[её] имя|как звать|как тво[её] имя|как называть)\b', 'name'),
    (r'\b(есть парень|есть девушка|твой парень|твоя девушка|в отношениях|свобод[её]н|встречаешься)\b', 'relationship'),
    (r'\b(покажи фото|фото|скинь фото|селфи|внешность|как выглядишь)\b', 'photo'),
    (r'\b(номер телефона|телефон|позвони|звони|как связаться)\b', 'phone'),
    (r'\b(адрес|где жив[её]шь|домашний адрес|где находишься)\b', 'address'),
    (r'\b(фамилия|твоя фамилия|какая фамилия)\b', 'surname'),
]

LIYING_REPLIES = {
    'честная': '',
    'социальная маска': '(мысленно: «скажу нейтрально»)',
    'приукрашивает мелочи': '(чуть приукрашивая)',
    'играет роль': '',
    'хроническая лгунья': '(придётся соврать)',
}

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

def fallback_reply(char, msgs, user_msg):
    attitude = char.get('default_attitude', 'нейтральная и вежливая')
    attitude_replies = STOCK_ANSWERS.get(attitude, STOCK_ANSWERS['нейтральная и вежливая'])
    oversharing = char.get('oversharing_level', 5)
    style = char.get('writing_style', '')
    lying = char.get('lying_tendency', 'честная')
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

    is_personal = False
    for pattern, _ in PERSONAL_QUESTION_PATTERNS:
        if re.search(pattern, lower):
            is_personal = True
            break
    evade_chance = max(0, 1.0 - oversharing / 10)
    if is_personal and random.random() < evade_chance:
        return random.choice(EVASIVE_ANSWERS)

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

def format_character_card(char):
    name = char.get('name', '?')
    surname = char.get('surname', '')
    age = char.get('age', '?')
    gender = char.get('gender', '?')
    city = char.get('city', '?')
    profession = char.get('profession', '?')
    zodiac = char.get('zodiac', '?')
    temperament = char.get('temperament', '?')
    archetype = char.get('archetype', '?')
    mbti = f"{char.get('mbti_code', '?')} ({char.get('mbti_name', '?')})"
    mood = char.get('current_mood', '?')
    opener = char.get('chat_opener', '')
    desc = char.get('appearance_description', '')
    backstory = char.get('backstory', '')

    text = (
        f"🎭 *{name} {surname}*, {age} лет, {gender}\n"
        f"📍 {city} | {zodiac}\n"
        f"💼 {profession}\n\n"
        f"🧠 {temperament} | {archetype}\n"
        f"📋 {mbti}\n"
        f"🌊 Текущее настроение: {mood}\n\n"
        f"*Описание:* {desc[:200]}{'...' if len(desc) > 200 else ''}\n\n"
        f"*Предыстория:* {backstory[:300]}{'...' if len(backstory) > 300 else ''}"
    )

    if opener:
        text += f'\n\n*Первое сообщение:* _{opener}_'

    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    if uid not in user_data:
        user_data[uid] = {
            'char': None,
            'messages': [],
            'settings': {
                'partner_gender': 'any',
                'partner_age': [],
                'own_gender': 'any',
                'topic': 'chat',
                'old_encounters': False,
            },
            'char_count': 0,
            'msg_count': 0,
            'prompt_count': 0,
        }
        save_user_data()
        logger.info(f'User {uid} registered')

    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    uid = update.effective_user.id
    settings = user_data.get(uid, {}).get('settings', {})
    is_chatting = user_data.get(uid, {}).get('char') is not None
    char_count = user_data.get(uid, {}).get('char_count', 0)

    gender_map = {'male': 'Мужской', 'female': 'Женский', 'any': 'Любой'}
    age_map = {'до 17': 'до 17', 'от 18 до 21': '18-21', 'от 22 до 25': '22-25', 'от 26 до 35': '26-35', 'старше 36': '36+'}
    topic_map = {'chat': 'Обычный', 'flirt': 'Флирт 18+', 'rp': 'Ролевая игра'}

    gender_text = gender_map.get(settings.get('partner_gender', 'any'), 'Любой')
    own_gender_text = gender_map.get(settings.get('own_gender', 'any'), 'Любой')
    age_text = ', '.join(str(age_map.get(a, a)) for a in settings.get('partner_age', [])) if settings.get('partner_age') else 'Любой'
    topic_text = topic_map.get(settings.get('topic', 'chat'), 'Обычный')

    old_enc = settings.get('old_encounters', False)
    forced_old = uid in CHAT_SAVE_IDS and ENABLE_OLD_ENCOUNTERS
    if forced_old or (old_enc and ENABLE_OLD_ENCOUNTERS):
        old_text = 'Старые встречи: ✓'
    else:
        old_text = 'Старые встречи: ✗'

    buttons = [
        [InlineKeyboardButton(f"Пол собеседника: {gender_text}", callback_data='set_gender')],
        [InlineKeyboardButton(f"Мой пол: {own_gender_text}", callback_data='set_own_gender')],
        [InlineKeyboardButton(f"Возраст: {age_text}", callback_data='set_age')],
        [InlineKeyboardButton(f"Режим: {topic_text}", callback_data='set_topic')],
        [InlineKeyboardButton(old_text, callback_data='set_old_encounters')],
    ]
    buttons.append([InlineKeyboardButton("🔍 Поиск собеседника", callback_data='next_char')])
    if uid in ALLOWED_IDS:
        buttons.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data='admin_panel')])
    buttons.append([InlineKeyboardButton("❓ Помощь", callback_data='help')])

    text = (
        f"*Nektome — случайный чат в Telegram* 🤖\n\n"
        f"Настройки текущего поиска:\n"
        f"• Пол собеседника: {gender_text}\n"
        f"• Мой пол: {own_gender_text}\n"
        f"• Возраст: {age_text}\n"
        f"• Режим: {topic_text}\n"
        f"• Старые встречи: {'✓ (принудительно)' if forced_old else ('✓' if old_enc and ENABLE_OLD_ENCOUNTERS else '✗')}\n"
    )
    if not is_chatting:
        text += "\n💬 Сейчас ни с кем не общаетесь"

    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    data = query.data

    if data == 'help':
        await show_help(update, context)
        return

    if data == 'set_gender':
        buttons = [
            [InlineKeyboardButton("Любой", callback_data='gender_any')],
            [InlineKeyboardButton("Мужской", callback_data='gender_male')],
            [InlineKeyboardButton("Женский", callback_data='gender_female')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_menu')],
        ]
        await query.edit_message_text("Выбери пол собеседника:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith('gender_'):
        gender = data.replace('gender_', '')
        if uid in user_data:
            user_data[uid]['settings']['partner_gender'] = gender
            save_user_data()
            logger.info(f'User {uid} set partner_gender={gender}')
        await show_main_menu(update, context, edit=True)
        return

    if data == 'set_own_gender':
        buttons = [
            [InlineKeyboardButton("Любой", callback_data='own_gender_any')],
            [InlineKeyboardButton("Мужской", callback_data='own_gender_male')],
            [InlineKeyboardButton("Женский", callback_data='own_gender_female')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_menu')],
        ]
        await query.edit_message_text("Выбери свой пол:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith('own_gender_'):
        own_gender = data.replace('own_gender_', '')
        if uid in user_data:
            user_data[uid]['settings']['own_gender'] = own_gender
            save_user_data()
            logger.info(f'User {uid} set own_gender={own_gender}')
        await show_main_menu(update, context, edit=True)
        return

    if data == 'set_age':
        curr_ages = user_data.get(uid, {}).get('settings', {}).get('partner_age', [])
        def age_btn(label, val):
            mark = ' ✓' if val in curr_ages else ''
            return InlineKeyboardButton(f"{label}{mark}", callback_data=f'age_{val}')
        buttons = [
            [InlineKeyboardButton("Сбросить все" if curr_ages else "Любой", callback_data='age_any')],
            [age_btn("до 17", 'до 17'),
             age_btn("18-21", 'от 18 до 21')],
            [age_btn("22-25", 'от 22 до 25'),
             age_btn("26-35", 'от 26 до 35')],
            [age_btn("36+", 'старше 36')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_menu')],
        ]
        await query.edit_message_text("Выбери возраст собеседника (можно несколько):", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith('age_'):
        age_val = data.replace('age_', '')
        if uid not in user_data:
            await start(update, context)
            return
        if age_val == 'any':
            user_data[uid]['settings']['partner_age'] = []
        else:
            ages = user_data[uid]['settings'].get('partner_age', [])
            if age_val in ages:
                ages.remove(age_val)
            else:
                ages.append(age_val)
            user_data[uid]['settings']['partner_age'] = ages
        save_user_data()
        await show_main_menu(update, context, edit=True)
        return

    if data == 'set_topic':
        buttons = [
            [InlineKeyboardButton("Обычный чат", callback_data='topic_chat')],
            [InlineKeyboardButton("Флирт 18+", callback_data='topic_flirt')],
            [InlineKeyboardButton("Ролевая игра", callback_data='topic_rp')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_menu')],
        ]
        await query.edit_message_text("Выбери режим общения:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith('topic_'):
        topic = data.replace('topic_', '')
        if uid in user_data:
            user_data[uid]['settings']['topic'] = topic
            save_user_data()
            logger.info(f'User {uid} set topic={topic}')
        await show_main_menu(update, context, edit=True)
        return

    if data == 'set_old_encounters':
        if uid in CHAT_SAVE_IDS:
            await query.answer('Старые встречи принудительно включены (ID в CHAT_SAVE_IDS)', show_alert=True)
            return
        if uid in user_data:
            user_data[uid]['settings']['old_encounters'] = not user_data[uid]['settings'].get('old_encounters', False)
            save_user_data()
        await show_main_menu(update, context, edit=True)
        return

    if data == 'back_menu':
        await show_main_menu(update, context, edit=True)
        return

    if data == 'next_char':
        await generate_character(update, context)
        return

    if data == 'show_card':
        await show_card(update, context)
        return

    if data == 'admin_panel':
        await show_admin_panel(update, context)
        return

    if data.startswith('admintool_') or data in ('admin_balance', 'admin_fc_settings'):
        await admin_button(update, context)
        return

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Nektome Bot — Помощь*\n\n"
        "Этот бот — случайный чат с AI-персонажами. "
        "Каждый персонаж уникален: у него есть имя, внешность, характер, биография и стиль общения.\n\n"
        "*Команды:*\n"
        "/start — Главное меню\n"
        "/next — Новый собеседник\n"
        "/settings — Настройки\n\n"
        "*Настройки:*\n"
        "• Пол собеседника — кого искать (М/Ж/Любой)\n"
        "• Мой пол — чтобы AI обращался к тебе в правильном роде\n"
        "• Возраст — возрастная группа (можно выбрать несколько)\n"
        "• Режим — Обычный чат, Флирт 18+ или Ролевая игра\n\n"
        "*В чате:*\n"
        "Просто пиши сообщения — собеседник будет отвечать. "
        "Когда надоест, нажми «Поиск собеседника» или отправь /next.\n\n"
        "*Важно:* без API-ключа (OpenAI) ответы генерируются по шаблонам. "
        "С API-ключом — полноценный AI."
    )
    buttons = [[InlineKeyboardButton("🔙 В меню", callback_data='back_menu')]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')

async def show_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data or not user_data[uid].get('char'):
        text = "Сейчас нет активного персонажа. Найди нового! /next"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    char = user_data[uid]['char']
    card = format_character_card(char)
    buttons = [[InlineKeyboardButton("🔙 В меню", callback_data='back_menu')]]

    if update.callback_query:
        await update.callback_query.edit_message_text(card, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')
    else:
        await update.message.reply_text(card, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')

async def generate_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    if uid not in user_data:
        await start(update, context)
        return

    settings = user_data[uid]['settings']
    partner_gender = settings.get('partner_gender', 'any')
    partner_age = settings.get('partner_age', [])
    topic = settings.get('topic', 'chat')

    old_allowed = ENABLE_OLD_ENCOUNTERS and (uid in CHAT_SAVE_IDS or settings.get('old_encounters', False))

    # Save old chat before overwriting
    if user_data[uid].get('char') and user_data[uid].get('messages'):
        old_char = user_data[uid]['char']
        old_msgs = user_data[uid]['messages']
        if len(old_msgs) > 1:
            save_chat_log(uid, old_char, old_msgs)

    # Try old encounter
    old_encounter = None
    if old_allowed:
        old_encounter = _pick_old_encounter(uid)

    if old_encounter:
        char_data, old_context = old_encounter
        # Rebuild opener from the old character's data
        opener = char_data.get('chat_opener', '')
        logger.info(f'User {uid} | OLD ENCOUNTER: {char_data.get("name","?")} {char_data.get("surname","?")}')
    else:
        gender = None
        if partner_gender == 'male':
            gender = 'male'
        elif partner_gender == 'female':
            gender = 'female'

        age_group = partner_age_groups(partner_age) if partner_age else None

        seed = random.randint(0, 2**31)
        char_obj = gen_char(seed=seed, gender=gender, age_group=age_group, topic=topic)
        char_data = make_char_json(char_obj)
        opener = char_data.get('chat_opener', '')
        old_context = None
        logger.info(f'User {uid} | Generated {char_data.get("name","?")} {char_data.get("surname","?")} '
                    f'({char_data.get("age","?")} {char_data.get("gender","?")}) | '
                    f'topic={topic} seed={seed}')

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

    user_data[uid]['char'] = char_data
    user_data[uid]['messages'] = initial_msgs
    user_data[uid]['memory'] = {'facts': [], 'next_id': 0}
    user_data[uid]['char_count'] = user_data[uid].get('char_count', 0) + 1
    user_data[uid]['old_context'] = old_context

    name = char_data.get('name', '?')
    surname = char_data.get('surname', '')
    msg_text = opener if opener else f"{name} {surname}"

    send_opener_now = random.random() < 0.75
    user_data[uid]['opener_sent'] = send_opener_now
    user_data[uid]['last_msg_time'] = time.time()

    save_user_data()

    if update.callback_query:
        await update.callback_query.delete_message()

    try:
        await update.effective_user.send_message('👤 Собеседник найден')
    except Exception as e:
        logger.error(f'User {uid} | Failed to send "Собеседник найден": {e}')
        return

    if send_opener_now:
        opener_parts = [p.strip() for p in msg_text.split('[NEXT]') if p.strip()]
        if not opener_parts:
            opener_parts = [msg_text]
        if char_data.get('writing_style') == 'пишет короткими фразами':
            fragmented = []
            for p in opener_parts:
                fragmented.extend(_split_sentences(p))
            opener_parts = fragmented
        for i, part in enumerate(opener_parts):
            if i > 0:
                await asyncio.sleep(random.uniform(0.8, 1.5))
            try:
                await update.effective_user.send_chat_action(action='typing')
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.8, 2.0))
            try:
                await update.effective_user.send_message(part)
            except Exception as e:
                logger.error(f'User {uid} | Failed to send opener part {i+1}: {e}')
        user_data[uid]['inject_first_msg'] = opener
        user_data[uid]['inject_depth'] = 0

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    t_start = time.time()
    if not is_allowed(uid):
        return
    user_msg = update.message.text.strip()
    logger.info(f'User {uid} | Message received')

    if uid not in user_data or not user_data[uid].get('char'):
        await update.message.reply_text("Сначала найди собеседника! /next")
        return

    char = user_data[uid]['char']
    msgs = user_data[uid]['messages']
    settings = user_data[uid]['settings']
    topic = settings.get('topic', 'chat')

    opener_sent = user_data[uid].get('opener_sent', False)
    if not opener_sent:
        user_data[uid]['opener_sent'] = True
        user_data[uid]['inject_first_msg'] = char.get('chat_opener', '')
        user_data[uid]['inject_depth'] = 1
        save_user_data()

    # detect long gaps (>=15 min) that break roleplay continuity
    now = time.time()
    last_time = user_data[uid].get('last_msg_time', 0)
    gap_minutes = (now - last_time) / 60
    if last_time > 0 and gap_minutes >= 15:
        gap_msg = f'[Прошло {int(gap_minutes)} минут тишины]'
        msgs.append({'role': 'system', 'content': gap_msg})
        logger.info(f'User {uid} | Time gap detected: {int(gap_minutes)} min')
    user_data[uid]['last_msg_time'] = now

    msgs.append({'role': 'user', 'content': user_msg})
    user_data[uid]['msg_count'] = user_data[uid].get('msg_count', 0) + 1

    if user_data[uid].get('memory'):
        user_data[uid]['memory']['lock'] = False

    try:
        await update.message.chat.send_action(action='typing')
    except Exception:
        pass

    user_gender = settings.get('own_gender', 'any')
    system_prompt = build_system_prompt(char, mode=topic, user_gender=user_gender)
    ai_messages = [{'role': 'system', 'content': system_prompt}]

    # Inject old encounter context if present (new chat with familiar person)
    if user_data[uid].get('old_context'):
        ctx = user_data[uid].pop('old_context')
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
        for m in ctx:
            ctx_block.append({'role': m['role'], 'content': m['content']})
        ctx_block.append({'role': 'system', 'content': (
            '[КОНЕЦ ПРОШЛОГО РАЗГОВОРА. Теперь начинается новый чат. '
            'Ты чувствуешь лёгкое узнавание, но не помнишь деталей. Продолжай общение естественно.]'
        )})
        ai_messages[1:1] = ctx_block

    for m in msgs:
        ai_messages.append({'role': m['role'], 'content': m['content']})

    inject = user_data[uid].get('inject_first_msg')
    if inject:
        depth = user_data[uid].get('inject_depth', 0)
        if depth < 3:
            ai_messages.insert(-1, {'role': 'system', 'content':
                f'ВАЖНО: Ты уже поприветствовала собеседника своим первым сообщением: «{inject}». '
                'Не здоровайся снова и не представляйся заново. Просто продолжай общение.'})
            user_data[uid]['inject_depth'] = depth + 1
            save_user_data()
        else:
            del user_data[uid]['inject_first_msg']
            del user_data[uid]['inject_depth']
            save_user_data()

    oversharing = char.get('oversharing_level', 5)
    instruction = build_instruction(mode=topic, oversharing=oversharing, chat_duration=char.get('chat_duration', 'пока не надоест'))
    ai_messages.append({'role': 'system', 'content': instruction})

    memory_block = _build_memory_block(user_data[uid].get('memory'))
    if memory_block:
        insert_pos = max(1, len(ai_messages) - 3)
        ai_messages.insert(insert_pos, {'role': 'system', 'content': memory_block})

    reply = None
    ai_time = 0.0
    if AI_ENABLED:
        global _current_tool_store
        _current_tool_store = user_data[uid]
        user_data[uid]['prompt_count'] = user_data[uid].get('prompt_count', 0) + 1
        t0 = time.time()
        active_tools = get_tools()
        text, tool_calls = call_ai(ai_messages, tools=active_tools)
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
                fn = get_tool_functions().get(func_name)
                if fn:
                    result = fn(args)
                else:
                    result = f'Unknown tool: {func_name}'
                logger.info(f'User {uid} | Tool call [{tool_round}/{max_tool_rounds}]: {func_name}({json.dumps(args, ensure_ascii=False)}) = {result}')
                ai_messages.append({
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': [tc],
                })
                ai_messages.append({
                    'role': 'tool',
                    'tool_call_id': tc['id'],
                    'content': str(result),
                })
            text, tool_calls = call_ai(ai_messages, tools=active_tools)
        _current_tool_store = None
        elapsed = time.time() - t0
        reply = text
        if reply:
            ai_time = elapsed
        else:
            logger.warning(f'User {uid} | AI returned None ({elapsed:.1f}s), using fallback')

    if reply is None:
        logger.info(f'User {uid} | Fallback reply')
        reply = fallback_reply(char, msgs, user_msg)

    disconnected = '[DISCONNECT]' in reply
    reply = reply.replace('[DISCONNECT]', '').strip()

    style = char.get('writing_style', '')
    msgs.append({'role': 'assistant', 'content': reply})
    reply = apply_writing_style(reply, style)

    parts = [p.strip() for p in reply.split('[NEXT]') if p.strip()]
    if not parts:
        parts = [reply]

    if style == 'пишет короткими фразами':
        fragmented = []
        for p in parts:
            fragmented.extend(_split_sentences(p))
        parts = fragmented

    for i, part in enumerate(parts):
        if i > 0:
            await asyncio.sleep(random.uniform(0.8, 1.8))
            try:
                await update.message.chat.send_action(action='typing')
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.5, 1.2))
        try:
            await update.message.reply_text(part)
        except Exception as e:
            logger.warning(f'Failed to send reply part: {e}')

    real_time = time.time() - t_start
    logger.info(f'User {uid} | AI: {ai_time:.1f}s / Real: {real_time:.1f}s')
    save_user_data()

    if disconnected:
        logger.info(f'User {uid} | Character disconnected via [DISCONNECT]')
        save_chat_log(uid, char, msgs)
        user_data[uid]['char'] = None
        user_data[uid]['messages'] = []
        save_user_data()
        await asyncio.sleep(0.5)
        try:
            await update.message.reply_text(
                "Собеседник завершил разговор.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Поиск собеседника", callback_data='next_char'),
                ]]),
            )
        except Exception as e:
            logger.warning(f'Failed to send disconnect message: {e}')

async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await generate_character(update, context)

async def card_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await show_card(update, context)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await show_main_menu(update, context, edit=False)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    data = user_data.get(uid, {})
    msg_count = data.get('msg_count', 0)
    prompt_count = data.get('prompt_count', 0)
    char_count = data.get('char_count', 0)
    text = (
        f'*Статистика*\n'
        f'👤 Сообщений отправлено: {msg_count}\n'
        f'🤖 AI запросов: {prompt_count}\n'
        f'🎭 Персонажей встречено: {char_count}'
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    if PROVIDER_TYPE != 'deepseek':
        await update.message.reply_text('Баланс доступен только для Deepseek провайдера.')
        return
    await update.message.reply_text('🔍 Запрашиваю баланс Deepseek...')
    try:
        await update.message.chat.send_action(action='typing')
    except Exception:
        pass
    data = check_deepseek_balance()
    if data is None:
        await update.message.reply_text('❌ Не удалось получить баланс. Проверь API ключ.')
        return
    await update.message.reply_text(format_balance(data), parse_mode='Markdown')

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    await show_admin_panel(update, context, edit=True if update.callback_query else False)

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=True):
    buttons = []
    if PROVIDER_TYPE == 'deepseek':
        buttons.append([InlineKeyboardButton("💰 Баланс Deepseek", callback_data='admin_balance')])
    buttons.append([InlineKeyboardButton("🔧 Настройка Function Calling", callback_data='admin_fc_settings')])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data='back_menu')])
    text = '*⚙️ Админ-панель*'
    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')

async def show_fc_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_config = load_admin_config()
    disabled = admin_config.get('disabled_tools', [])
    all_tools = [t['function']['name'] for t in _BUILTIN_TOOLS]
    buttons = []
    for name in all_tools:
        label = f"{'✅' if name not in disabled else '❌'} {name}"
        buttons.append([InlineKeyboardButton(label, callback_data=f'admintool_{name}')])
    buttons.append([InlineKeyboardButton("🔙 Админ-панель", callback_data='admin_panel')])
    text = '*🔧 Настройка Function Calling*\n\nОтметь какие инструменты доступны AI:'
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')

async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'admin_balance':
        if PROVIDER_TYPE != 'deepseek':
            await query.edit_message_text('Баланс доступен только для Deepseek провайдера.')
            return
        await query.edit_message_text('🔍 Запрашиваю баланс Deepseek...')
        resp = check_deepseek_balance()
        if resp is None:
            await query.edit_message_text(
                '❌ Не удалось получить баланс. Проверь API ключ.',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Админ-панель", callback_data='admin_panel')]]),
            )
            return
        await query.edit_message_text(
            format_balance(resp),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Админ-панель", callback_data='admin_panel')]]),
            parse_mode='Markdown',
        )
        return
    if data == 'admin_fc_settings':
        await show_fc_settings(update, context)
        return
    if data.startswith('admintool_'):
        tool_name = data.replace('admintool_', '')
        admin_config = load_admin_config()
        disabled = admin_config.get('disabled_tools', [])
        if tool_name in disabled:
            disabled.remove(tool_name)
        else:
            disabled.append(tool_name)
        admin_config['disabled_tools'] = disabled
        save_admin_config(admin_config)
        await show_fc_settings(update, context)
        return
    if data == 'admin_panel':
        await show_admin_panel(update, context, edit=True)
        return

async def _set_commands(app):
    commands = [
        ('start', 'Главное меню'),
        ('next', 'Новый собеседник'),
        ('settings', 'Настройки'),
        ('stats', 'Моя статистика'),
    ]
    if ALLOWED_IDS:
        commands.append(('admin', 'Админ-панель'))
    await app.bot.set_my_commands(commands)

def main():
    if not BOT_TOKEN:
        logger.error('BOT_TOKEN not configured in .env')
        return

    builder = Application.builder().token(BOT_TOKEN).post_init(_set_commands) \
        .read_timeout(30).write_timeout(30).connect_timeout(30)
    if BOT_USE_PROXY and BOT_PROXY_URL:
        builder = builder.proxy(BOT_PROXY_URL)
    app = builder.build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('next', next_command))
    app.add_handler(CommandHandler('card', card_command))
    app.add_handler(CommandHandler('settings', settings_command))
    app.add_handler(CommandHandler('stats', stats_command))
    if ALLOWED_IDS:
        app.add_handler(CommandHandler('admin', admin_start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    for attempt in range(5):
        try:
            logger.info(f'Starting Nektome Telegram Bot... (attempt {attempt+1})')
            app.run_polling(allowed_updates=Update.ALL_TYPES, bootstrap_retries=3)
            return
        except Exception as e:
            logger.error(f'Failed to start bot: {e}')
            if attempt < 4:
                logger.info('Retrying in 5 seconds...')
                time.sleep(5)

if __name__ == '__main__':
    main()
