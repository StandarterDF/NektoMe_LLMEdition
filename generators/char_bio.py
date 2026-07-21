import random


def generate_backstory(archetype_data, age_group_name, age, gender, extra_fragments=None):
    fragments = list(archetype_data['backstory'])
    if extra_fragments:
        fragments.extend(extra_fragments)

    selected = random.sample(fragments, min(random.randint(2, 3), len(fragments)))

    connectors = [
        'В детстве', 'Когда она была маленькой', 'С ранних лет',
        'В школьные годы', 'Будучи ребёнком', 'Ещё в детстве',
    ]
    connector_starts = [c.lower() for c in connectors]

    lines = []
    for i, frag in enumerate(selected):
        intro = random.choice(connectors) if i == 0 else ''
        line = frag.strip()
        if not line.endswith('.'):
            line += '.'
        if intro:
            frag_lower = line.lower()
            # skip intro if fragment already starts with a connector word
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

    templates = [
        f"""Она {temperament.lower()} по темпераменту и {mbti_name.lower()} по типу личности. 
В душе — {archetype.lower()}. {desire}. 
{goal}. {fear}.
Работает {profession.lower()}. В свободное время любит {hobbies}.""",

        f"""В свои {age} она успела понять главное: {desire.lower()}. 
Поэтому {goal.lower()}. 
{temperament.lower()} и {mbti_name.lower()} — это про неё. 
{fear}.
Сейчас работает {profession.lower()}. Из увлечений — {hobbies}.""",

        f"""Тип личности — {mbti_name}, темперамент — {temperament}. Её архетип — {archetype}. 
{desire}. 
{goal}. 
{fear}.
Профессия: {profession.lower()}. Любит {hobbies}.""",

        f"""Она — {archetype.lower()} в душе и {mbti_name.lower()} по складу ума. 
{desire}. 
{goal}. 
{fear}.
Работает {profession.lower()}. В свободное время {hobbies}.""",

        f"""Если кратко: {archetype.lower()}, {temperament.lower()}, {mbti_name.lower()}. 
{desire}. 
{goal}. 
{fear}.
Профессия — {profession.lower()}. Увлекается {hobbies}.""",

        f"""В {age} лет она уже точно знает, что {desire.lower()}. 
Поэтому {goal.lower()}. 
{fear}.
Она {temperament.lower()} и {mbti_name.lower()} по типу. 
Работает {profession.lower()}. Любит {hobbies}.""",

        f"""По жизни — {archetype.lower()}. 
{desire}. 
{goal}. 
{fear}.
Темперамент: {temperament.lower()}. Тип личности: {mbti_name}. 
Профессия: {profession.lower()}. Увлечения: {hobbies}.""",

        f"""Она сочетает в себе черты {archetype.lower()} и {mbti_name.lower()}. 
{desire}. 
{goal}. 
{fear}.
Работает {profession.lower()}. Из хобби выделяет {hobbies}.""",

        f"""Темперамент — {temperament.lower()}, тип личности — {mbti_name}. Архетип — {archetype}. 
{desire}. 
{goal}. 
{fear}.
Профессия — {profession.lower()}. В свободное время {hobbies}.""",

        f"""Её архетип — {archetype.upper()}. 
{desire}. 
{goal}. 
{fear}.
Тип личности: {mbti_name}. Темперамент: {temperament.lower()}.
Работает {profession.lower()}. Увлекается {hobbies}.""",
    ]

    return random.choice(templates)
