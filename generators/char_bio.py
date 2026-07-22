import random
import re


MALE_REPLACE_FULL = [
    (r'\bпро неё\b', 'про него'), (r'\bдля неё\b', 'для него'),
    (r'\bот неё\b', 'от него'), (r'\bу неё\b', 'у него'),
    (r'\bнад ней\b', 'над ним'), (r'\bна неё\b', 'на него'),
    (r'\bк ней\b', 'к нему'), (r'\bс ней\b', 'с ним'),
    (r'\bо ней\b', 'о нём'),
    (r'\bнеё\b', 'него'), (r'\bней\b', 'нем'),
    (r'\bОна\b', 'Он'), (r'\bона\b', 'он'),
    (r'\bЕё\b', 'Его'), (r'\bеё\b', 'его'),
    (r'\bЕй\b', 'Ему'), (r'\bей\b', 'ему'),
    (r'\bбыла\b', 'был'), (r'\bродилась\b', 'родился'),
    (r'\bросла\b', 'рос'), (r'\bстала\b', 'стал'),
    (r'\bосталась\b', 'остался'), (r'\bпережила\b', 'пережил'),
    (r'\bуслышала\b', 'услышал'), (r'\bвидела\b', 'видел'),
    (r'\bузнала\b', 'узнал'), (r'\bпоняла\b', 'понял'),
    (r'\bнаучилась\b', 'научился'), (r'\bоказалась\b', 'оказался'),
    (r'\bполучила\b', 'получил'), (r'\bработала\b', 'работал'),
    (r'\bуспела\b', 'успел'),
    (r'\bдевушкой\b', 'человеком'), (r'\bдевушку\b', 'человека'),
    (r'\bдевушка\b', 'человек'),
    (r'\bдевочкой\b', 'мальчиком'), (r'\bдевочка\b', 'мальчик'),
    (r'\bсестра\b', 'брат'), (r'\bсестрой\b', 'братом'),
    (r'\bсестру\b', 'брата'), (r'\bсестре\b', 'брату'),
    (r'\bподруга\b', 'друг'), (r'\bподруги\b', 'друзья'),
    (r'\bподругу\b', 'друга'), (r'\bподругой\b', 'другом'),
    (r'\bподруге\b', 'другу'),
]

MALE_REPLACE_SAFE = [
    # Only subject pronouns and verb forms — NOT object pronouns (её/ей/неё)
    # because those may refer to feminine nouns in archetype strings
    (r'\bОна\b', 'Он'), (r'\bона\b', 'он'),
    (r'\bбыла\b', 'был'), (r'\bродилась\b', 'родился'),
    (r'\bросла\b', 'рос'), (r'\bстала\b', 'стал'),
    (r'\bосталась\b', 'остался'), (r'\bпережила\b', 'пережил'),
    (r'\bуслышала\b', 'услышал'), (r'\bвидела\b', 'видел'),
    (r'\bузнала\b', 'узнал'), (r'\bпоняла\b', 'понял'),
    (r'\bнаучилась\b', 'научился'), (r'\bоказалась\b', 'оказался'),
    (r'\bполучила\b', 'получил'), (r'\bработала\b', 'работал'),
    (r'\bуспела\b', 'успел'),
    (r'\bдевушкой\b', 'человеком'), (r'\bдевушку\b', 'человека'),
    (r'\bдевочкой\b', 'мальчиком'),
    (r'\bсестра\b', 'брат'), (r'\bсестрой\b', 'братом'),
    (r'\bподруга\b', 'друг'), (r'\bподруги\b', 'друзья'),
]


def _male_replace(text, safe=True):
    replacements = MALE_REPLACE_SAFE if safe else MALE_REPLACE_FULL
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text


def _connector_for_gender(gender):
    if gender == 'male':
        return [
            'В детстве', 'Когда он был маленьким', 'С ранних лет',
            'В школьные годы', 'Будучи ребёнком', 'Ещё в детстве',
        ]
    return [
        'В детстве', 'Когда она была маленькой', 'С ранних лет',
        'В школьные годы', 'Будучи ребёнком', 'Ещё в детстве',
    ]


def generate_backstory(archetype_data, age_group_name, age, gender, extra_fragments=None, must_include=0):
    is_male = (gender == 'male')

    archetype_frags = list(archetype_data['backstory'])
    extra = list(extra_fragments) if extra_fragments else []
    fragments = extra + archetype_frags

    if is_male:
        fragments = [_male_replace(f, safe=False) for f in fragments]

    must_pick = fragments[:must_include] if must_include > 0 else []
    rest = fragments[must_include:]
    k = random.randint(2, 3)
    if k > len(rest):
        k = len(rest)
    selected = must_pick + random.sample(rest, k) if rest else must_pick

    connectors = _connector_for_gender(gender)
    connector_starts = [c.lower() for c in connectors]

    lines = []
    for i, frag in enumerate(selected):
        intro = random.choice(connectors) if i == 0 else ''
        line = frag.strip()
        if not line.endswith('.'):
            line += '.'
        if intro:
            frag_lower = line.lower()
            skip = False
            for cs in connector_starts:
                if frag_lower.startswith(cs):
                    skip = True
                    break
            if skip:
                lines.append(line.capitalize() if line[0].islower() else line)
            else:
                lines.append(f"{intro} {line[0].lower() + line[1:]}")
        else:
            lines.append(line.capitalize() if line[0].islower() else line)

    backstory_text = ' '.join(lines)
    return backstory_text


def generate_bio(character, age_group_name):
    age = character.age
    archetype = character.archetype
    temperament = character.temperament
    mbti_name = character.mbti_name
    profession = character.profession
    hobbies = ', '.join(character.hobbies[:3])
    bio_personality = ', '.join(character.positive_traits[:3])

    desire = character.archetype_desire
    goal = character.archetype_goal
    fear = character.archetype_fear

    is_male = (character.gender == 'Мужской')
    p_on = 'Он' if is_male else 'Она'
    p_ee = 'Его' if is_male else 'Её'
    p_pro = 'про него' if is_male else 'про неё'
    p_neego = 'него' if is_male else 'неё'
    p_emu = 'Ему' if is_male else 'Ей'

    if is_male:
        desire = _male_replace(desire)
        goal = _male_replace(goal)
        fear = _male_replace(fear)

    templates = [
        f"""{p_on} {temperament.lower()} по темпераменту и {mbti_name.lower()} по типу личности. 
В душе — {archetype.lower()}. {desire}. 
{goal}. {fear}.
Работает {profession.lower()}. В свободное время любит {hobbies}.""",

        f"""В свои {age} {p_on.lower()} {_male_replace('успела')} понять главное: {desire.lower()}. 
Поэтому {goal.lower()}. 
{temperament.lower()} и {mbti_name.lower()} — это {p_pro}. 
{fear}.
Сейчас работает {profession.lower()}. Из увлечений — {hobbies}.""",

        f"""Тип личности — {mbti_name}, темперамент — {temperament}. {p_ee} архетип — {archetype}. 
{desire}. 
{goal}. 
{fear}.
Профессия: {profession.lower()}. Любит {hobbies}.""",

        f"""{p_on} — {archetype.lower()} в душе и {mbti_name.lower()} по складу ума. 
{desire}. 
{goal}. 
{fear}.
Работает {profession.lower()}. В свободное время {hobbies}.""",

        f"""Если кратко: {archetype.lower()}, {temperament.lower()}, {mbti_name.lower()}. 
{desire}. 
{goal}. 
{fear}.
Профессия — {profession.lower()}. Увлекается {hobbies}.""",

        f"""В {age} лет {p_on.lower()} уже точно знает, что {desire.lower()}. 
Поэтому {goal.lower()}. 
{fear}.
{p_on} {temperament.lower()} и {mbti_name.lower()} по типу. 
Работает {profession.lower()}. Любит {hobbies}.""",

        f"""По жизни — {archetype.lower()}. 
{desire}. 
{goal}. 
{fear}.
Темперамент: {temperament.lower()}. Тип личности: {mbti_name}. 
Профессия: {profession.lower()}. Увлечения: {hobbies}.""",

        f"""{p_on} сочетает в себе черты {archetype.lower()} и {mbti_name.lower()}. 
{desire}. 
{goal}. 
{fear}.
Работает {profession.lower()}. Из хобби выделяет {hobbies}.""",

        f"""Темперамент — {temperament.lower()}, тип личности — {mbti_name}. Архетип — {archetype}. 
{desire}. 
{goal}. 
{fear}.
Профессия — {profession.lower()}. В свободное время {hobbies}.""",

        f"""{p_ee} архетип — {archetype.upper()}. 
{desire}. 
{goal}. 
{fear}.
Тип личности: {mbti_name}. Темперамент: {temperament.lower()}.
Работает {profession.lower()}. Увлекается {hobbies}.""",
    ]

    return random.choice(templates)
