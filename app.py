import random
import json
import uuid
from flask import Flask, render_template, request, jsonify, session
from generators.char_generator import generate as gen_char

app = Flask(__name__)
app.secret_key = 'nektome-ai-chat-secret-2026'

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

    char_data = make_char_json(char)
    token = str(uuid.uuid4())
    char_store[token] = {'character': char_data, 'messages': []}
    char_data['_token'] = token
    return jsonify(char_data)


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
    msgs.append({'role': 'user', 'text': user_msg})
    msg_count = len([m for m in msgs if m['role'] == 'user'])

    attitude = char.get('default_attitude', 'нейтральная и вежливая')
    attitude_replies = STOCK_ANSWERS.get(attitude, STOCK_ANSWERS['нейтральная и вежливая'])
    oversharing = char.get('oversharing_level', 5)
    style = char.get('writing_style', '')
    lying = char.get('lying_tendency', 'честная')
    humor = char.get('humor_style', '')
    rp = char.get('rp_ability', False)
    opener = char.get('chat_opener', '')

    lower = user_msg.lower()

    is_greeting = any(w in lower for w in ['привет', 'здравствуй', 'хай', 'хелло', 'салют', 'даров', 'ку', 'здарова'])
    is_bye = any(w in lower for w in ['пока', 'до свидания', 'прощай', 'удачи', 'бывай'])
    is_how = any(w in lower for w in ['как дела', 'как ты', 'чё как', 'how are', 'как жизнь'])
    is_question = '?' in user_msg or any(w in lower for w in ['что', 'как', 'почему', 'зачем', 'кто', 'где', 'когда'])
    is_compliment = any(w in lower for w in ['красив', 'мил', 'симпатич', 'хорош', 'клёв', 'прикольн', 'классн'])
    is_insult = any(w in lower for w in ['дурак', 'туп', 'идиот', 'отстань', 'заткнись', 'пошёл', 'бесишь'])

    name = char.get('name', '')
    archetype = char.get('archetype', '')
    trauma = char.get('trauma_name', '')
    taboos = char.get('taboo_topics', [])

    STOPWORDS = {'и', 'в', 'на', 'с', 'у', 'о', 'не', 'а', 'но', 'да', 'к', 'по', 'из', 'от', 'для', 'без', 'над', 'под', 'об', 'про', 'до', 'за', 'при', 'или', 'ни', 'то', 'же', 'бы', 'ли', 'если', 'что', 'как', '—', '-'}
    lower_words = set(w.strip('.,!?()[]{}«»""'':;') for w in lower.split())
    taboo_hit = False
    for t in taboos:
        for w in t.lower().split():
            wc = w.strip('.,!?()[]{}«»""'':;')
            if len(wc) > 2 and wc not in STOPWORDS and wc in lower_words:
                taboo_hit = True
                break
        if taboo_hit:
            break
    if taboo_hit:
        reply = 'Давай не будем об этом, хорошо?'
        msgs.append({'role': 'assistant', 'text': reply})
        store['messages'] = msgs
        return jsonify({'reply': reply})

    if msg_count == 1 and opener:
        reply = opener
    elif is_greeting:
        base = attitude_replies.get('greeting', 'Привет!')
        if humor:
            base = f'{random.choice(["Ха!", "Кста!", "О!"] )} {base}'
        reply = base
    elif is_insult:
        r = char.get('harassment_reaction', '')
        if not r:
            r = 'Молча нажимает «Next».'
        reply = f'{r}'
    elif is_compliment:
        base = attitude_replies.get('agree', 'Спасибо!')
        if oversharing >= 7:
            base += ' Ты тоже ничего так!'
        reply = base
    elif is_how:
        mood = char.get('current_mood', 'нормальное')
        intro = oversharing_intro(oversharing)
        if oversharing >= 6:
            reply = f'{intro} Настроение {mood}. Могу рассказать подробнее.'
        elif oversharing >= 3:
            reply = f'{intro} Да нормально всё, {mood}.'
        else:
            reply = f'{intro} Нормально.'
    elif is_bye:
        reply = f'Пока! Было приятно пообщаться.'
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

    reply = apply_writing_style(reply, style)

    msgs.append({'role': 'assistant', 'text': reply})
    store['messages'] = msgs
    return jsonify({'reply': reply})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
