import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from generators.char_generator import generate

line = '=' * 48 if sys.stdout.encoding.lower() not in ('utf-8', 'utf8') else chr(0x2550) * 48

import random
random.seed()
for age_group in ['teen', 'teen', 'young']:
    char = generate(gender='female', age_group=age_group)

    print(line)
    print(f'  {char.name} {char.surname}')
    print(f'  {char.gender}, {char.age} лет, {char.zodiac}')
    print(f'  Возрастная группа: {age_group}')
    print(line)

    print(f'\n  --- ТЕМПЕРАМЕНТ ---')
    print(f'     Тип:            {char.temperament}')
    print(f'     Архетип:        {char.archetype}')
    print(f'       Желание:     {char.archetype_desire}')
    print(f'       Цель:        {char.archetype_goal}')
    print(f'       Страх:       {char.archetype_fear}')
    print(f'       Талант:      {char.archetype_talent}')
    print(f'     Социальность:   {char.social_style}')
    print(f'     Тип личности:   {char.mbti_name} ({char.mbti_code})')

    print(f'\n  --- ОСНОВНАЯ ИНФОРМАЦИЯ ---')
    print(f'     Дата рождения:  {char.birth_date}')
    print(f'     Город:          {char.city}')
    print(f'     Профессия:      {char.profession}')
    print(f'     Достаток:       {char.wealth_level} — {char.wealth_label}')
    print(f'     Астрология:     {char.astrology_belief}')
    print(f'     Пошлость:       {char.sexual_openness}')
    print(f'     Цель в чате:    {char.chat_motivation}')
    print(f'     Образование:    {char.education}')
    print(f'     Сем. положение: {char.relationship_status}')
    print(f'     Языки:          {", ".join(char.languages)}')

    print(f'\n  --- ВНЕШНОСТЬ ---')
    print(f'     Рост:           {char.height}')
    print(f'     Вес/тело:       {char.body_size}')
    print(f'     Красота:        {char.beauty}')
    print(f'     Цвет глаз:      {char.eye_color}')
    print(f'     Волосы:         {char.hair_color}, {char.hair_length}')
    print(f'     Телосложение:   {char.body_type}')
    if char.gym_habit:
        print(f'     Физ. активность:{char.gym_habit}')
    print(f'     Тип кожи:       {char.skin_tone}')
    print(f'     Стиль одежды:   {char.clothing_style}')
    if char.distinctive_features:
        print(f'     Ос. приметы:    {", ".join(char.distinctive_features)}')

    print(f'\n  --- ХАРАКТЕР ---')
    print(f'     + {", ".join(char.positive_traits)}')
    print(f'     - {", ".join(char.negative_traits)}')
    print(f'     Привычки:       {", ".join(char.habits)}')
    print(f'     Страхи:         {", ".join(char.fears)}')
    print(f'     Мечты:          {", ".join(char.dreams)}')
    print(f'     Ценности:       {", ".join(char.relationship_values)}')

    print(f'\n  --- ПСИХОЛОГИЯ ---')
    print(f'     Травма:         {char.trauma_name}')
    print(f'     Последствие:    {char.trauma_consequence}')
    print(f'     Защита:         {char.trauma_defense}')
    print(f'     Убеждение:      {char.trauma_belief}')

    print(f'\n  --- ПРЕДПОЧТЕНИЯ ---')
    print(f'     Любимые цвета:  {", ".join(char.favorite_colors)}')
    print(f'     Любимая еда:    {", ".join(char.favorite_foods)}')
    print(f'     Любимые напитки:{", ".join(char.favorite_drinks)}')
    print(f'     Любимые жанры музыки: {", ".join(char.favorite_music_genres)}')
    if char.favorite_music_artists:
        print(f'     Любимые исполнители: {", ".join(char.favorite_music_artists[:3])}')
    print(f'     Любимые жанры фильмов: {", ".join(char.favorite_movie_genres)}')
    if char.favorite_movie_titles:
        print(f'     Любимые фильмы: {", ".join(char.favorite_movie_titles[:3])}')
    print(f'     Любимые жанры книг: {", ".join(char.favorite_book_genres)}')
    if char.favorite_book_titles:
        print(f'     Любимые книги:  {", ".join(char.favorite_book_titles[:3])}')
    print(f'     Время года:     {", ".join(char.favorite_seasons)}')
    if char.fetishes:
        print(f'     Фетиши:         {", ".join(char.fetishes)}')

    print(f'\n  --- ОПИСАНИЕ ВНЕШНОСТИ ---')
    print(f'     {char.appearance_description}')

    print(f'\n  --- УВЛЕЧЕНИЯ: {", ".join(char.hobbies)}')

    # Dynamic spice details
    spice_lines = []
    if char.housing:
        spice_lines.append(('Жилище', char.housing))
    if char.financial_habit:
        spice_lines.append(('Финансы', char.financial_habit))
    if char.eating_habit:
        spice_lines.append(('Еда', char.eating_habit))
    if char.pet:
        spice_lines.append(('Питомец', char.pet))
    if char.red_flags:
        spice_lines.append(('Бесят', '; '.join(char.red_flags)))
    if char.green_flags:
        spice_lines.append(('Ценят', '; '.join(char.green_flags)))
    if char.cryptonite:
        spice_lines.append(('Криптонит', char.cryptonite))
    if char.useless_talent:
        spice_lines.append(('Бесполезный талант', char.useless_talent))
    if char.body_language_tell:
        spice_lines.append(('Язык тела', char.body_language_tell))
    if char.humor_style:
        spice_lines.append(('Юмор', char.humor_style))
    if char.biggest_lie:
        spice_lines.append(('Самая большая ложь', char.biggest_lie))
    if char.anger_trigger:
        spice_lines.append(('Триггер гнева', char.anger_trigger))
    if char.enemy:
        spice_lines.append(('Главный враг', char.enemy))
    if char.sleep_type:
        spice_lines.append(('Сон', char.sleep_type))
    if char.personal_scent:
        spice_lines.append(('Запах', char.personal_scent))
    if char.health_issue:
        spice_lines.append(('Здоровье', char.health_issue))
    if char.supernatural_belief:
        spice_lines.append(('Верования', char.supernatural_belief))
    if spice_lines:
        print(f'\n  --- ДЕТАЛИ ---')
        for label, val in spice_lines:
            print(f'     {label:<18} {val}')

    print(f'\n  --- СТИЛЬ ОБЩЕНИЯ ---')
    print(f'     Грамотность:    {char.writing_style}')
    print(f'     RP:             {"Да (*действия*)" if char.rp_ability else "Нет (только текст)"}')
    print(f'     Первое сообщ.:  {char.chat_opener}')
    print(f'     Юмор:           {char.humor_style if hasattr(char, "humor_style") and char.humor_style else "без выраженного стиля"}')
    print(f'     Любимые темы:   {", ".join(char.fav_topics)}')
    print(f'     Табу:           {", ".join(char.taboo_topics)}')
    print(f'     Скип-факторы:   {"; ".join(char.skip_factors)}')
    print(f'     На хамство:     {char.harassment_reaction}')
    print(f'     Ложь:           {char.lying_tendency}')
    desc = {
        1:'почти не говорит о себе', 2:'крайне редко делится личным',
        3:'делится только базой', 4:'расскажет в общих чертах',
        5:'средняя открытость', 6:'достаточно открыта',
        7:'любит говорить о себе', 8:'слабо держит границы',
        9:'овершер на 5й минуте', 10:'выложит всё незнакомцу',
    }.get(char.oversharing_level, '')
    print(f'     Овершеринг:     {char.oversharing_level}/10 — {desc}')

    print(f'\n  --- УСТАНОВКИ ---')
    print(f'     Отношение:      {char.default_attitude}')
    print(f'     Парадокс:       {char.weakness}')

    print(f'\n  --- КОНТЕКСТ ВХОДА ---')
    print(f'     Мотив:          {char.entry_context}')
    print(f'     Ситуация:       {char.current_situation}')
    print(f'     Настроение:     {char.current_mood}')
    print(f'     Скрытый мотив:  {char.hidden_motive}')

    print(f'\n  --- ПРЕДЫСТОРИЯ ---')
    print(f'     {char.backstory}')

    print(f'\n  --- SYSTEM PROMPT (для LLM) ---')
    print(f'     {char.system_prompt}')
    print()
