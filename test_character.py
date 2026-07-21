import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from char_generator import generate

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

    print(f'\n  --- ПРЕДЫСТОРИЯ ---')
    print(f'     {char.backstory}')

    print(f'\n  --- О СЕБЕ: {char.bio}')
    print()
