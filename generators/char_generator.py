import random
import json
from generators.char_model import (
    Character, weighted_choice, weighted_sample, pick_from_pool,
    random_date, zodiac_sign,
)
from generators.char_data import (
    male_names, female_names, male_surnames, female_surnames, cities,
    eye_colors, hair_colors, hair_lengths, body_types, skin_tones,
    positive_traits, negative_traits, hobbies_male, hobbies_female,
    profession_groups, profession_education_map, favorite_colors_pool,
    favorite_foods_pool, favorite_drinks_pool, favorite_music_pool,
    movie_genres_pool, book_genres_pool, fetish_categories, fetishes_pool,
    clothing_styles_pool, habits_pool, fears_pool, dreams_pool,
    relationship_values_pool, education_levels, languages_pool,
    relationship_statuses,
    hair_styles, movie_examples, book_examples, music_examples, trauma_data,
)
from generators.char_profiles import (
    temperaments, archetypes, mbti_profiles, archetype_mbti_compat,
    archetype_profession_groups, age_groups, age_group_profiles,
    age_group_hobbies_boost, age_group_professions, age_group_fetishes,
    age_group_relationship, age_group_education, age_group_music_boost,
    social_alignments, body_sizes, beauty_levels,
    archetype_fetish_mods, beauty_fetish_mods, body_size_fetish_mods,
    wealth_levels, kinkiness_levels, chat_motivations,
)
from generators.char_appearance import generate_appearance, fashion_items
from generators.char_bio import generate_backstory, generate_bio


def generate(seed=None, gender=None, age_group=None):
    if seed is not None:
        state = random.getstate()
        random.seed(seed)
    else:
        state = None

    if gender is None:
        gender = random.choice(['male', 'female'])

    # --- Age groups & age ---
    age_group_names = list(age_groups.keys())
    if age_group is None:
        age_group = weighted_choice(
            age_group_names,
            [30, 25, 30, 15]
        )

    age_group_info = age_groups[age_group]
    min_age, max_age = age_group_info['min'], age_group_info['max']
    age = random.randint(min_age, max_age)
    age_profile = age_group_profiles[age_group]

    birth_date = random_date(2026 - max_age - 1, 2026 - min_age)
    zodiac = zodiac_sign(birth_date.day, birth_date.month)

    # --- Name (weighted) ---
    if gender == 'male':
        name = weighted_choice([n for n, _ in male_names], [w for _, w in male_names])
        surname = weighted_choice([s for s, _ in male_surnames], [w for _, w in male_surnames])
    else:
        name = weighted_choice([n for n, _ in female_names], [w for _, w in female_names])
        surname = weighted_choice([s for s, _ in female_surnames], [w for _, w in female_surnames])
    city = random.choice(cities)

    # --- Temperament ---
    temp_name = weighted_choice(
        list(temperaments.keys()),
        [25, 25, 25, 25],
    )
    temp_traits = temperaments[temp_name]

    # --- Archetype ---
    archetype_name = weighted_choice(
        list(archetypes.keys()),
        [1] * 12,
    )
    archetype_data = archetypes[archetype_name]
    archetype_desire = archetype_data['desire']
    archetype_goal = archetype_data['goal']
    archetype_fear = archetype_data['fear']
    archetype_talent = archetype_data['talent']

    # --- Social alignment ---
    social = weighted_choice(
        social_alignments,
        [35, 40, 25],
    )
    social_traits = social['traits']

    # --- Personality profile (9 dims) ---
    personality_dims = [
        'analytical', 'creative', 'sociability', 'emotionality',
        'assertiveness', 'calm', 'fun', 'deep', 'energy',
        'empathy', 'discipline', 'confidence', 'sensuality',
        'adventurousness', 'ambition', 'rebel', 'gentle',
        'romance', 'trust', 'optimism', 'anxious',
        'sophisticated', 'intense', 'practical', 'independence',
        'passion', 'warmth', 'kindness', 'patience',
    ]

    profile = {}
    for dim in personality_dims:
        base = 0
        # from temperament
        if dim in temp_traits:
            base += temp_traits[dim]
        # from age
        if dim in age_profile:
            base += age_profile[dim]
        # from social
        if dim in social_traits:
            base += social_traits[dim]
        profile[dim] = base

    # --- MBTI (weighted by archetype compatibility) ---
    archetype_role_compat = archetype_mbti_compat[archetype_name]
    mbti_weights = {}
    for mbti_key, mbti_data in mbti_profiles.items():
        # which role group
        role_group = None
        if mbti_key in ('INTJ', 'INTP', 'ENTJ', 'ENTP'):
            role_group = 'analyst'
        elif mbti_key in ('INFJ', 'INFP', 'ENFJ', 'ENFP'):
            role_group = 'diplomat'
        elif mbti_key in ('ISTJ', 'ISFJ', 'ESTJ', 'ESFJ'):
            role_group = 'sentinel'
        elif mbti_key in ('ISTP', 'ISFP', 'ESTP', 'ESFP'):
            role_group = 'explorer'

        compat_weight = archetype_role_compat.get(role_group, 1) if role_group else 1
        mbti_weights[mbti_key] = compat_weight * 3

    mbti_code = weighted_choice(list(mbti_weights.keys()), list(mbti_weights.values()))
    mbti_name = mbti_profiles[mbti_code]['name']
    mbti_traits = mbti_profiles[mbti_code]['traits']
    for dim, val in mbti_traits.items():
        if dim in profile:
            profile[dim] += val

    # ensure no negative
    for k in profile:
        profile[k] = max(-1.0, min(1.0, profile[k]))

    # Normalized profile for weighted picks
    profile_normalized = {k: max(0.01, v + 1.0) for k, v in profile.items()}

    # --- Appearance ---
    eye_color = random.choice(eye_colors)
    hair_color = random.choice(hair_colors)
    hair_length = random.choice(hair_lengths)
    body_type = weighted_choice([b[0] for b in body_types], [b[1] for b in body_types])
    if body_type in ('мускулистое', 'атлетичное'):
        gym_freqs = ['три раза в неделю', 'через день', 'каждый день', 'по утрам']
        gym_habit = f'Регулярно ходит в спортзал ({random.choice(gym_freqs)})'
    elif body_type == 'коренастое':
        gym_habit = 'Занимается тяжёлой физической работой'
    elif body_type in ('стройное', 'изящное'):
        gym_habit = random.choice(['Занимается йогой или пилатесом', 'Много гуляет пешком, не любит спортзалы'])
    else:
        gym_habit = random.choice(['Не интересуется фитнесом', 'Иногда гуляет в парке', 'Ведёт малоподвижный образ жизни'])
    skin_tone = random.choice(skin_tones)
    distinctive_features = random.sample([
        'родинка над губой', 'веснушки', 'шрам на брови', 'родинка на щеке',
        'асимметричная улыбка', 'ямочки на щеках', 'пирсинг в носу',
        'шрам на подбородке', 'родинка на шее', 'веснушки на носу',
        'татуировка на запястье', 'седые пряди', 'шрам на руке',
        'родимое пятно', 'пухлые губы', 'густые брови', 'веснушки',
    ], random.randint(0, 2))

    # --- Body size & beauty (affect personality + backstory) ---
    body_size_key = weighted_choice(
        list(body_sizes.keys()),
        [body_sizes[k]['prob'] for k in body_sizes],
    )
    body_size_data = body_sizes[body_size_key]
    weight_range = body_size_data.get('weight_range', '')
    body_size_display = f'{body_size_key} ({weight_range} кг)' if weight_range else body_size_key
    for dim, val in body_size_data['profile'].items():
        if dim in profile:
            profile[dim] += val

    beauty = weighted_choice(
        list(beauty_levels.keys()),
        [beauty_levels[k]['prob'] for k in beauty_levels],
    )
    beauty_data = beauty_levels[beauty]
    for dim, val in beauty_data['profile'].items():
        if dim in profile:
            profile[dim] += val

    # Re-normalize profile after body/beauty mods
    for k in profile:
        profile[k] = max(-1.0, min(1.0, profile[k]))
    profile_normalized = {k: max(0.01, v + 1.0) for k, v in profile.items()}

    clothing_style = pick_from_pool(clothing_styles_pool, profile_normalized, 1, 1)[0]

    extra_backstory = []
    extra_backstory.extend(body_size_data['backstory'])
    extra_backstory.extend(beauty_data['backstory'])

    hair_style_data = hair_styles.get(hair_length)
    if hair_style_data:
        hair_style = random.choices([s for s, w in hair_style_data], weights=[w for s, w in hair_style_data], k=1)[0]
    else:
        hair_style = ''

    appearance_data = {
        'eye_color': eye_color,
        'hair_color': hair_color,
        'hair_length': hair_length,
        'hair_style': hair_style,
        'body_type': body_type,
        'body_size': body_size_key,
        'beauty': beauty,
        'clothing_style': clothing_style,
        'distinctive_features': distinctive_features,
    }
    appearance_description = generate_appearance(appearance_data, gender)

    # --- Positive / Negative traits ---
    pos_weights = []
    for t in positive_traits:
        dim_match = 0
        for dim, val in profile.items():
            if dim[:3] in t[:3]:
                dim_match += max(0, val)
        pos_weights.append(max(0.1, 1 + dim_match))
    negative_traits_selected = []
    neg_traits_list = list(negative_traits)
    neg_weights = [max(0.1, 2 - (profile.get(t[:3], 0) if any(1 for k in profile if k[:3] == t[:3]) else 0)) for t in neg_traits_list]
    positive_traits_selected = random.sample(
        weighted_sample(positive_traits, pos_weights, 6), min(4, 6)
    )
    negative_traits_selected = random.sample(
        weighted_sample(neg_traits_list, neg_weights, 4), min(3, 4)
    )

    # --- Profession ---
    if age_group == 'teen':
        profession = random.choice(age_group_professions['teen'])
        profession_group_key = 'коммуникатор' if profession == 'курьер' else 'творец'
    elif age_group == 'young':
        young_profs = age_group_professions['young']
        if random.random() < 0.4:
            profession = random.choice(young_profs)
            profession_group_key = 'помощник'
        else:
            profession = _pick_profession(archetype_name, profile_normalized, age_group)
            profession_group_key = _get_profession_group(profession)
    else:
        profession = _pick_profession(archetype_name, profile_normalized, age_group)
        profession_group_key = _get_profession_group(profession)

    # --- Wealth ---
    wealth_pool = list(wealth_levels.keys())
    wealth_weights = [wealth_levels[w]['prob'] for w in wealth_pool]
    for pw in wealth_pool:
        data = wealth_levels[pw]
        if 'profession_boost' in data and profession in data['profession_boost']:
            idx = wealth_pool.index(pw)
            wealth_weights[idx] *= 2
            if pw in ('высокий', 'очень высокий'):
                wealth_weights[idx] *= 0.5
    wealth_level = weighted_choice(wealth_pool, wealth_weights)
    wealth_label = wealth_levels[wealth_level]['label']

    # --- Hobbies ---
    hobbies_pool = hobbies_female if gender == 'female' else hobbies_male
    hobby_weights = []
    age_boost = age_group_hobbies_boost[age_group]
    for h_name, h_cost in hobbies_pool:
        w = 1
        for boost_key, boost_val in age_boost.items():
            if boost_key in h_name.lower():
                w *= boost_val
        for dim, val in profile.items():
            if dim[:3] in h_name.lower()[:3]:
                w *= max(0.5, 1 + val * 0.3)
        required = h_cost
        wealth_rank = wealth_pool.index(wealth_level)
        if wealth_rank < required:
            w *= 0.15
        elif wealth_rank > required + 1:
            w *= 1.2
        hobby_weights.append(max(0.1, w))
    chosen = weighted_sample(hobbies_pool, hobby_weights, min(random.randint(2, 5), len(hobbies_pool)))
    hobbies = [h[0] for h in chosen]
    hobbies = list(set(hobbies))

    # --- Education ---
    educ_pool = age_group_education.get(age_group) or education_levels
    if age_group in ('teen', 'young') and profession not in ('студент', 'школьник'):
        education = random.choice(educ_pool)
        if education in ('высшее (бакалавриат)', 'высшее (магистратура)'):
            education = 'среднее'
    else:
        education = random.choice(educ_pool)
    if 'студент' in profession:
        education = 'неоконченное высшее'

    # --- Languages (начинаем с русского, остальные редко) ---
    languages = ['русский']
    if random.random() < 0.35:
        lang_pool_extra = [(l[0], l[1]) if isinstance(l, tuple) else (l, {}) for l in languages_pool]
        lang_weights = []
        for l in lang_pool_extra:
            w = l[1].get('pop', 1)
            for k, v in l[1].items():
                if k in profile_normalized:
                    w *= max(0.5, 1 + profile_normalized[k] * v / 100)
            lang_weights.append(max(0.5, w))
        second = weighted_choice([l[0] for l in lang_pool_extra], lang_weights)
        languages.append(second)
        if random.random() < 0.08:
            remaining = [(l[0], l[1]) for l in lang_pool_extra if l[0] != second]
            r_weights = []
            for l in remaining:
                w = l[1].get('pop', 1)
                for k, v in l[1].items():
                    if k in profile_normalized:
                        w *= max(0.5, 1 + profile_normalized[k] * v / 100)
                r_weights.append(max(0.5, w))
            third = weighted_choice([l[0] for l in remaining], r_weights)
            languages.append(third)

    # --- Favorites ---
    favorite_colors = pick_from_pool(favorite_colors_pool, profile_normalized, 2, 3)
    favorite_foods = random.sample(favorite_foods_pool, min(random.randint(3, 5), len(favorite_foods_pool)))
    favorite_drinks = random.sample(favorite_drinks_pool, min(random.randint(2, 3), len(favorite_drinks_pool)))

    # Music with age boost
    age_music_boost = age_group_music_boost[age_group]
    music_weights = []
    for m in favorite_music_pool:
        m_name = m[0] if isinstance(m, tuple) else m
        m_data = m[1] if isinstance(m, tuple) else {}
        w = 1
        if m_name in age_music_boost:
            w *= 3
        for k, v in m_data.items():
            if k in profile_normalized:
                w *= max(0.1, 1 + profile_normalized[k] * v / 100)
        music_weights.append(max(0.1, w))
    favorite_music = weighted_sample(
        [m[0] if isinstance(m, tuple) else m for m in favorite_music_pool],
        music_weights,
        random.randint(2, 4),
    )

    favorite_seasons = random.sample(['весна', 'лето', 'осень', 'зима'], random.randint(1, 3))

    movie_weights = []
    for m in movie_genres_pool:
        m_name = m[0]
        m_data = m[1] if isinstance(m, tuple) else {}
        w = 1
        for k, v in m_data.items():
            if k in profile_normalized:
                w *= max(0.1, 1 + profile_normalized[k] * v / 100)
        movie_weights.append(max(0.1, w))
    favorite_movies = weighted_sample(
        [m[0] if isinstance(m, tuple) else m for m in movie_genres_pool],
        movie_weights,
        random.randint(2, 4),
    )

    book_weights = []
    for b in book_genres_pool:
        b_name = b[0]
        b_data = b[1] if isinstance(b, tuple) else {}
        w = 1
        for k, v in b_data.items():
            if k in profile_normalized:
                w *= max(0.1, 1 + profile_normalized[k] * v / 100)
        book_weights.append(max(0.1, w))
    favorite_books = weighted_sample(
        [b[0] if isinstance(b, tuple) else b for b in book_genres_pool],
        book_weights,
        random.randint(2, 3),
    )

    # --- Favorite examples ---
    def pick_examples(genre, pool, count=1):
        examples = pool.get(genre, [])
        if examples:
            return random.choice(examples)
        return ''

    favorite_movie_titles = [pick_examples(g, movie_examples) for g in favorite_movies if random.random() < 0.6]
    favorite_movie_titles = list(set(filter(None, favorite_movie_titles)))
    random.shuffle(favorite_movie_titles)
    favorite_book_titles = [pick_examples(g, book_examples) for g in favorite_books if random.random() < 0.6]
    favorite_book_titles = list(set(filter(None, favorite_book_titles)))
    random.shuffle(favorite_book_titles)
    favorite_music_artists = [pick_examples(g, music_examples, 1) for g in favorite_music if random.random() < 0.5]
    favorite_music_artists = list(set(filter(None, favorite_music_artists)))
    random.shuffle(favorite_music_artists)

    # --- Fetishes (cascading: archetype + beauty + body_size → categories → items) ---
    fetish_config = age_group_fetishes[age_group]
    if fetish_config['allowed']:
        # Build fetish boost from archetype + beauty + body_size
        fetish_boosts = {}
        for k, v in archetype_fetish_mods.get(archetype_name, {}).items():
            fetish_boosts[k] = fetish_boosts.get(k, 1) + v
        for k, v in beauty_fetish_mods.get(beauty, {}).items():
            fetish_boosts[k] = fetish_boosts.get(k, 1) + v
        for k, v in body_size_fetish_mods.get(body_size_key, {}).items():
            fetish_boosts[k] = fetish_boosts.get(k, 1) + v

        # Build weights for all fetishes
        all_fetish_items = []
        all_fetish_weights = []
        for cat_name, cat_items in fetish_categories.items():
            for item in cat_items:
                f_name = item[0]
                f_data = item[1] if len(item) > 1 else {}
                w = 1
                # Pop (base popularity)
                if 'pop' in f_data:
                    w += max(0, f_data['pop'])
                # Personality profile
                for dim, val in f_data.items():
                    if dim in profile_normalized:
                        w *= max(0.1, 1 + profile_normalized[dim] * val / 100)
                # Archetype/beauty/body boosts
                for boost_dim, boost_val in fetish_boosts.items():
                    if boost_dim in f_data:
                        w *= boost_val
                all_fetish_items.append((cat_name, f_name))
                all_fetish_weights.append(max(0.1, w))

        fetish_count = random.randint(fetish_config.get('count_min', 1), fetish_config.get('count_max', 3))
        chosen = set()
        fetishes = []
        attempts = 0
        while len(fetishes) < fetish_count and attempts < 50:
            attempts += 1
            available = [i for i in range(len(all_fetish_items)) if i not in chosen]
            if not available:
                break
            avail_weights = [all_fetish_weights[i] for i in available]
            idx = weighted_choice(available, avail_weights)
            chosen.add(idx)
            cat, f_name = all_fetish_items[idx]
            fetishes.append(f_name)
            # Boost same-category items for next picks (cascading)
            for i in range(len(all_fetish_items)):
                if i not in chosen and all_fetish_items[i][0] == cat:
                    all_fetish_weights[i] *= 1.5

        if len(fetishes) > 4:
            fetishes = random.sample(fetishes, 4)
    else:
        fetishes = []

    # --- Habits ---
    habit_weights = []
    for h in habits_pool:
        h_name = h[0] if isinstance(h, tuple) else h
        h_data = h[1] if isinstance(h, tuple) else {}
        w = 1
        for k, v in h_data.items():
            if k in profile_normalized:
                w *= max(0.1, 1 + profile_normalized[k] * v / 100)
        habit_weights.append(max(0.1, w))
    habits = weighted_sample(
        [h[0] if isinstance(h, tuple) else h for h in habits_pool],
        habit_weights,
        random.randint(2, 4),
    )

    # --- Fears ---
    num_fears = random.randint(1, 3) if age > 13 else 2
    fear_weights = []
    for f in fears_pool:
        f_name = f[0] if isinstance(f, tuple) else f
        f_data = f[1] if isinstance(f, tuple) else {}
        w = 1
        for k, v in f_data.items():
            if k in profile_normalized:
                w *= max(0.1, 1 + profile_normalized[k] * v / 100)
        fear_weights.append(max(0.1, w))
    fears = weighted_sample(
        [f[0] if isinstance(f, tuple) else f for f in fears_pool],
        fear_weights,
        num_fears,
    )

    # --- Dreams ---
    num_dreams = random.randint(1, 3)
    dreams = random.sample(dreams_pool, min(num_dreams, len(dreams_pool)))

    # --- Relationship values ---
    rel_weights = []
    for rv in relationship_values_pool:
        w = 1.0
        if rv in profile:
            w *= max(0.5, 1 + profile[rv] * 0.5)
        rel_weights.append(w)
    relationship_values = weighted_sample(relationship_values_pool, rel_weights, random.randint(3, 4))
    relationship_values = list(set(relationship_values))

    # --- Relationship status ---
    rel_pool = age_group_relationship.get(age_group) or relationship_statuses
    relationship_status = random.choice(rel_pool)

    # --- Kinkiness ---
    num_fetishes = len(fetishes)
    sensuality = profile_normalized.get('sensuality', 0)
    romance = profile_normalized.get('romance', 0)
    kink_score = num_fetishes * 0.15 + sensuality * 0.4 + romance * 0.1
    if archetype_name in kinkiness_levels['консервативный']['archetype_block']:
        kink_score *= 0.3
    kink_level = 'консервативный'
    for kl, kdata in kinkiness_levels.items():
        if kink_score >= kdata['threshold']:
            kink_level = kl

    # --- Chat motivation ---
    motives = []
    motive_weights = []
    for mv, mdata in chat_motivations.items():
        mw = 1
        if mv == 'поиск пошлостей' and kink_level in ('консервативный', 'обычный'):
            mw *= 0.15
        elif mv == 'поиск пошлостей' and kink_level == 'похотливый':
            mw *= 3
        elif mv == 'поиск пошлостей' and kink_level == 'раскрепощённый':
            mw *= 1.5
        if archetype_name in mdata.get('archetype_boost', []):
            mw *= 3
        if mv == 'поиск отношений' and relationship_status in ('в отношениях', 'замужем'):
            mw *= 0.3
        if mv == 'поиск пошлостей' and age_group == 'teen':
            mw *= 0.05
        if mv == 'поиск друзей' and age_group == 'teen':
            mw *= 2
        if mv == 'просто скучно' and age_group == 'mature':
            mw *= 0.3
        motives.append(mv)
        motive_weights.append(max(0.1, mw))
    chat_motivation = weighted_choice(motives, motive_weights)

    # --- Astrology / esoteric beliefs ---
    mystic_score = profile_normalized.get('mystic', 0.5) * 2
    analytical_score = profile_normalized.get('analytical', 0.5)
    dreaminess = profile_normalized.get('dreaminess', 0.5)
    astrology_chance = max(0.05, mystic_score * 0.3 + dreaminess * 0.15 - analytical_score * 0.05)
    if random.random() < astrology_chance:
        astrology_belief = 'верит в астрологию'
    else:
        astrology_belief = 'не верит в астрологию'

    # --- Backstory ---
    backstory = generate_backstory(archetype_data, age_group, age, gender, extra_backstory)

    # --- Psychological trauma ---
    trauma = random.choice(trauma_data)
    trauma_name = trauma['name']
    trauma_consequence = random.choice(trauma['consequence'])
    trauma_defense = random.choice(trauma['defense'])
    trauma_belief = trauma['belief']

    # --- Bio ---
    character_for_bio = Character(
        name=name, surname=surname, gender=('Женский' if gender == 'female' else 'Мужской'),
        birth_date=birth_date.strftime('%d.%m.%Y'), age=age, zodiac=zodiac,
        height=f"{random.randint(155, 180)} см" if gender == 'female' else f"{random.randint(170, 195)} см",
        eye_color=eye_color, hair_color=hair_color, hair_length=hair_length,
        body_type=body_type, skin_tone=skin_tone,
        distinctive_features=distinctive_features,
        clothing_style=clothing_style,
        body_size=body_size_display, beauty=beauty,
        appearance_description=appearance_description,
        temperament=temp_name,
        archetype=archetype_name,
        archetype_desire=archetype_desire,
        archetype_goal=archetype_goal,
        archetype_fear=archetype_fear,
        archetype_talent=archetype_talent,
        mbti_code=mbti_code,
        mbti_name=mbti_name,
        social_style=social['name'],
        positive_traits=positive_traits_selected,
        negative_traits=negative_traits_selected,
        wealth_level=wealth_level,
        wealth_label=wealth_label,
        hobbies=hobbies,
        profession=profession,
        profession_group=profession_group_key,
        education=education,
        languages=languages,
        relationship_status=relationship_status,
        city=city,
        astrology_belief=astrology_belief,
        sexual_openness=kink_level,
        chat_motivation=chat_motivation,
        gym_habit=gym_habit,
        hair_style=hair_style,
        favorite_movie_titles=favorite_movie_titles,
        favorite_book_titles=favorite_book_titles,
        favorite_music_artists=favorite_music_artists,
        trauma_name=trauma_name,
        trauma_consequence=trauma_consequence,
        trauma_defense=trauma_defense,
        trauma_belief=trauma_belief,
        favorite_colors=favorite_colors,
        favorite_foods=favorite_foods,
        favorite_drinks=favorite_drinks,
        favorite_music_genres=favorite_music,
        favorite_seasons=favorite_seasons,
        favorite_movie_genres=favorite_movies,
        favorite_book_genres=favorite_books,
        fetishes=fetishes,
        habits=habits,
        fears=fears,
        dreams=dreams,
        relationship_values=relationship_values,
        backstory=backstory,
        bio='',
    )

    bio = generate_bio(character_for_bio, age_group)
    character_for_bio.bio = bio

    if state is not None:
        random.setstate(state)

    return character_for_bio


def _pick_profession(archetype, profile, age_group):
    archetype_prof = archetype_profession_groups[archetype]
    group_weights = {}
    for g_name, g_weight in archetype_prof.items():
        if g_name in profession_groups:
            group_weights[g_name] = g_weight

    chosen_group = weighted_choice(list(group_weights.keys()), list(group_weights.values()))
    profs = profession_groups[chosen_group]
    return weighted_choice([p for p, _ in profs], [w for _, w in profs])


def _get_profession_group(profession):
    for group, profs in profession_groups.items():
        for p, _ in profs:
            if p == profession:
                return group
    return 'коммуникатор'


def generate_json(seed=None, gender=None, age_group=None):
    character = generate(seed, gender, age_group)
    return character_to_dict(character)


def character_to_dict(character):
    data = {
        'name': f"{character.name} {character.surname}",
        'gender': character.gender,
        'age': character.age,
        'birth_date': character.birth_date,
        'zodiac': character.zodiac,
        'height': character.height,
        'city': character.city,
        'temperament': character.temperament,
        'archetype': character.archetype,
        'archetype_desire': character.archetype_desire,
        'archetype_goal': character.archetype_goal,
        'archetype_fear': character.archetype_fear,
        'archetype_talent': character.archetype_talent,
        'mbti_code': character.mbti_code,
        'mbti_name': character.mbti_name,
        'social_style': character.social_style,
        'profession': character.profession,
        'profession_group': character.profession_group,
        'education': character.education,
        'relationship_status': character.relationship_status,
        'appearance': {
            'eye_color': character.eye_color,
            'hair_color': character.hair_color,
            'hair_length': character.hair_length,
            'body_type': character.body_type,
            'skin_tone': character.skin_tone,
            'distinctive_features': character.distinctive_features,
            'clothing_style': character.clothing_style,
            'description': character.appearance_description,
        },
        'personality': {
            'positive_traits': character.positive_traits,
            'negative_traits': character.negative_traits,
            'hobbies': character.hobbies,
            'habits': character.habits,
            'fears': character.fears,
            'dreams': character.dreams,
            'relationship_values': character.relationship_values,
        },
        'favorites': {
            'colors': character.favorite_colors,
            'foods': character.favorite_foods,
            'drinks': character.favorite_drinks,
            'music': character.favorite_music_genres,
            'seasons': character.favorite_seasons,
            'movies': character.favorite_movie_genres,
            'books': character.favorite_book_genres,
        },
        'fetishes': character.fetishes,
        'languages': character.languages,
        'backstory': character.backstory,
        'bio': character.bio,
    }
    return data


if __name__ == '__main__':
    for i in range(3):
        c = generate()
        print(f"\n{'='*60}")
        print(f"{c.name}, {c.age}")
        print(f"Темперамент: {c.temperament}")
        print(f"Архетип: {c.archetype}")
        print(f"MBTI: {c.mbti_code} ({c.mbti_name})")
        print(f"Профессия: {c.profession}")
        print(f"Био: {c.bio[:200]}...")
        print(f"Предыстория: {c.backstory[:200]}...")
