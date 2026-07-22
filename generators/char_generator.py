import random
import json
from generators.char_model import (
    Character, weighted_choice, weighted_sample, pick_from_pool,
    random_date, zodiac_sign,
)
from datetime import datetime, timedelta
from generators.char_data import (
    male_names, female_names, male_surnames, female_surnames, cities,
    eye_colors, hair_colors, hair_lengths, body_types, skin_tones,
    positive_traits, negative_traits, positive_trait_dims, negative_trait_dims,
    hobbies_male, hobbies_female,
    profession_groups, profession_education_map, favorite_colors_pool,
    favorite_drinks_pool, favorite_music_pool,
    movie_genres_pool, book_genres_pool, fetish_categories, fetishes_pool,
    clothing_styles_pool, habits_pool, fears_pool, dreams_pool,
    relationship_values_pool, education_levels, languages_pool,
    relationship_statuses,
    hair_styles, movie_examples, book_examples, music_examples, trauma_data,
    housing_pool, financial_habits_pool, eating_habits_pool,
    pets_pool, red_flags_pool, green_flags_pool,
    cryptonite_pool, useless_talents_pool, body_language_tells_pool,
    humor_styles_pool, biggest_lies_pool, anger_triggers_pool,
    enemies_pool, sleep_types_pool, personal_scents_pool, health_issues_pool,
    supernatural_beliefs_pool,
    writing_styles, rp_ability_profiles,
    entry_contexts, current_situations_pool, current_moods_pool,
    hidden_motives_pool, chat_openers_pool, chat_openers_male_pool,
    chat_openers_female_pool, chat_openers_flirt_pool, chat_openers_rp_pool,
    skip_factors_pool,
    harassment_reactions_pool, fav_topics_pool, taboo_topics_pool,
    lying_tendencies, oversharing_descriptions,
    foods_by_cost, wealth_to_food_cost,
    default_attitudes_pool, paradoxes_pool,
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


def generate(seed=None, gender=None, age_group=None, topic=None):
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
        if topic == 'flirt':
            age_group = weighted_choice(
                age_group_names,
                [0, 55, 35, 10]   # flirt: strictly 18+
            )
        elif topic == 'rp':
            age_group = weighted_choice(
                age_group_names,
                [30, 40, 20, 10]   # rp: slightly older
            )
        else:
            age_group = weighted_choice(
                age_group_names,
                [42, 42, 12, 4]   # default
            )

    age_group_info = age_groups[age_group]
    min_age, max_age = age_group_info['min'], age_group_info['max']
    age_profile = age_group_profiles[age_group]

    age = random.randint(min_age, max_age)
    birth_year = datetime.now().year - age
    birth_date = datetime(birth_year, 1, 1) + timedelta(days=random.randint(0, 364))
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
    if topic == 'flirt':
        temp_name = weighted_choice(
            list(temperaments.keys()),
            [35, 30, 15, 20],
        )
    elif topic == 'rp':
        temp_name = weighted_choice(
            list(temperaments.keys()),
            [20, 20, 30, 30],
        )
    else:
        temp_name = weighted_choice(
            list(temperaments.keys()),
            [25, 25, 25, 25],
        )
    temp_traits = temperaments[temp_name]

    # --- Archetype (weighted by temperament compatibility) ---
    archetype_temp_compat = {
        'Сангвиник': {'Невинный': 3, 'Искатель': 3, 'Любовник': 3, 'Герой': 1, 'Сирота': 1, 'Бунтарь': 2, 'Творец': 3, 'Правитель': 2, 'Мудрец': 1, 'Воин': 2, 'Маг': 2, 'Шут': 3},
        'Холерик':   {'Невинный': 0, 'Искатель': 2, 'Любовник': 2, 'Герой': 3, 'Сирота': 0, 'Бунтарь': 3, 'Творец': 1, 'Правитель': 3, 'Мудрец': 0, 'Воин': 3, 'Маг': 2, 'Шут': 2},
        'Флегматик': {'Невинный': 3, 'Искатель': 2, 'Любовник': 1, 'Герой': 1, 'Сирота': 3, 'Бунтарь': 0, 'Творец': 2, 'Правитель': 1, 'Мудрец': 3, 'Воин': 1, 'Маг': 1, 'Шут': 1},
        'Меланхолик':{'Невинный': 1, 'Искатель': 3, 'Любовник': 2, 'Герой': 1, 'Сирота': 2, 'Бунтарь': 1, 'Творец': 3, 'Правитель': 0, 'Мудрец': 2, 'Воин': 1, 'Маг': 2, 'Шут': 0},
    }
    compat_weights = archetype_temp_compat.get(temp_name, {k: 1 for k in archetypes})
    topic_archetype_boost = {}
    if topic == 'flirt':
        topic_archetype_boost = {'Любовник': 6, 'Бунтарь': 4, 'Шут': 3, 'Маг': 2, 'Искатель': 1, 'Герой': 1}
    elif topic == 'rp':
        topic_archetype_boost = {'Творец': 4, 'Маг': 4, 'Искатель': 4, 'Мудрец': 3, 'Герой': 3, 'Воин': 2, 'Любовник': 1}
    archetype_name = weighted_choice(
        list(archetypes.keys()),
        [compat_weights.get(k, 1) + topic_archetype_boost.get(k, 0) for k in archetypes],
    )
    archetype_data = archetypes[archetype_name]
    archetype_desire = archetype_data['desire']
    archetype_goal = archetype_data['goal']
    archetype_fear = archetype_data['fear']
    archetype_talent = archetype_data['talent']

    # --- Social alignment (weighted by temperament) ---
    temp_to_social = {
        'Сангвиник': {'Экстраверт': 65, 'Интроверт': 0, 'Амбиверт': 35},
        'Холерик':   {'Экстраверт': 60, 'Интроверт': 0, 'Амбиверт': 40},
        'Флегматик': {'Экстраверт': 0, 'Интроверт': 65, 'Амбиверт': 35},
        'Меланхолик':{'Экстраверт': 0, 'Интроверт': 55, 'Амбиверт': 45},
    }
    social_weights_config = temp_to_social.get(temp_name, {'Экстраверт': 35, 'Интроверт': 40, 'Амбиверт': 25})
    social = weighted_choice(
        social_alignments,
        [social_weights_config[s['name']] for s in social_alignments],
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

    if social['name'] == 'Интроверт':
        mbti_weights = {k: v for k, v in mbti_weights.items() if k.startswith('I')}
    elif social['name'] == 'Экстраверт':
        mbti_weights = {k: v for k, v in mbti_weights.items() if k.startswith('E')}

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

    # --- Body size & beauty first (affect personality + backstory) ---
    if topic == 'flirt':
        body_probs = {'очень худая': 10, 'стройная': 35, 'средняя': 25, 'пышная': 20, 'полная': 10}
        body_size_key = weighted_choice(
            list(body_sizes.keys()),
            [body_probs[k] for k in body_sizes],
        )
    else:
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

    if topic == 'flirt':
        beauty_probs = {'обычная': 20, 'симпатичная': 30, 'красивая': 30, 'очень красивая': 20}
        beauty = weighted_choice(
            list(beauty_levels.keys()),
            [beauty_probs[k] for k in beauty_levels],
        )
    else:
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

    # --- Height & Appearance ---
    height_cm = random.randint(155, 180) if gender == 'female' else random.randint(170, 195)
    height_str = f"{height_cm} см"

    # BMI-based body type filtering
    if weight_range:
        w_parts = weight_range.split('-')
        weight_mid = (float(w_parts[0]) + float(w_parts[1])) / 2
    else:
        weight_mid = 60
    bmi = weight_mid / ((height_cm / 100) ** 2)

    body_type = _pick_body_type_by_bmi(bmi)

    eye_color = random.choice(eye_colors)
    hair_color = random.choice(hair_colors)
    hair_length = random.choice(hair_lengths)
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

    if topic == 'flirt':
        style_boost_kwargs = {'boost_list': ['элегантный', 'романтичный', 'готический', 'уличный стиль', 'спорт-шик']}
    else:
        style_boost_kwargs = {}
    clothing_style = pick_from_pool(clothing_styles_pool, profile_normalized, 1, 1, **style_boost_kwargs)[0]

    extra_backstory = []
    extra_backstory.extend(body_size_data['backstory'])
    extra_backstory.extend(beauty_data['backstory'])
    extra_backstory = _resolve_backstory_conflicts(body_size_key, beauty, extra_backstory)

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
        for dim in positive_trait_dims.get(t, []):
            dim_match += max(0, profile.get(dim, 0))
        pos_weights.append(max(0.1, 1 + dim_match))
    neg_traits_list = list(negative_traits)
    neg_weights = []
    for t in neg_traits_list:
        dim_mismatch = 0
        for dim in negative_trait_dims.get(t, []):
            # Lower profile value in relevant dims => higher negative trait weight
            dim_mismatch += max(0, -profile.get(dim, 0))
        neg_weights.append(max(0.1, 1 + dim_mismatch))
    positive_traits_selected = weighted_sample(positive_traits, pos_weights, min(4, 6))
    negative_traits_selected = weighted_sample(neg_traits_list, neg_weights, min(3, 4))

    # --- Profession ---
    if age_group == 'teen':
        if age < 16:
            profession = 'школьник'
            profession_group_key = 'творец'
        else:
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
        if age < 17:
            education = 'среднее'
        else:
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
    food_cost_tier = wealth_to_food_cost.get(wealth_level, 'средняя')
    food_pool_for_wealth = foods_by_cost.get(food_cost_tier, foods_by_cost['средняя'])
    favorite_foods = random.sample(food_pool_for_wealth, min(random.randint(3, 5), len(food_pool_for_wealth)))
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
        # Build fetish boost from archetype + beauty + body_size (multiplicative: 1 + sum of mods)
        fetish_boosts = {}
        for k, v in archetype_fetish_mods.get(archetype_name, {}).items():
            fetish_boosts[k] = fetish_boosts.get(k, 0) + v
        for k, v in beauty_fetish_mods.get(beauty, {}).items():
            fetish_boosts[k] = fetish_boosts.get(k, 0) + v
        for k, v in body_size_fetish_mods.get(body_size_key, {}).items():
            fetish_boosts[k] = fetish_boosts.get(k, 0) + v
        # Convert additive boosts to multiplicative (1 + sum)
        fetish_boosts = {k: max(0.1, 1 + v) for k, v in fetish_boosts.items()}

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
                # Archetype/beauty/body boosts (multiplicative, pre-normalized to 1+sum)
                for boost_dim, boost_val in fetish_boosts.items():
                    if boost_dim in f_data:
                        w *= boost_val
                all_fetish_items.append((cat_name, f_name))
                all_fetish_weights.append(max(0.1, w))

        fetish_count_min = fetish_config.get('count_min', 1)
        fetish_count_max = fetish_config.get('count_max', 3)
        if topic == 'flirt':
            fetish_count_min = min(fetish_count_min + 1, 5)
            fetish_count_max = min(fetish_count_max + 2, 6)
        fetish_count = random.randint(fetish_count_min, fetish_count_max)
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
    if topic == 'flirt':
        kink_score *= 1.5
    if not topic or topic != 'flirt':
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
        if topic == 'flirt' and mv == 'поиск пошлостей':
            mw *= 5
        if topic == 'flirt' and mv in ('поиск друзей', 'просто скучно', 'повысить самооценку'):
            mw *= 0.15
        if topic == 'rp' and mv in ('поиск друзей', 'просто скучно', 'поиск приключений'):
            mw *= 3
        if topic == 'rp' and mv == 'поиск пошлостей':
            mw *= 0.2
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

    # --- Psychological trauma (before backstory, so backstory can reference it) ---
    # Archetype-trauma compatibility: boost weights for matching traumas
    archetype_trauma_compat = {
        'Невинный': {'развод родителей': 4, 'потеря близкого': 3, 'одиночество': 2},
        'Сирота': {'потеря близкого': 4, 'эмоциональное отвержение': 3, 'одиночество': 2, 'предательство близкого': 2},
        'Воин': {'буллинг': 4, 'физическое насилие': 3, 'отвержение внешности': 2},
        'Искатель': {'гиперопека': 4, 'воспитание с установками': 3, 'эмоциональное отвержение': 2},
        'Бунтарь': {'гиперопека': 4, 'физическое насилие': 3, 'воспитание с установками': 2},
        'Любовник': {'эмоциональное отвержение': 4, 'предательство близкого': 3, 'измена': 2, 'одиночество': 2},
        'Творец': {'воспитание с установками': 4, 'эмоциональное отвержение': 2, 'буллинг': 2},
        'Правитель': {'бедность в детстве': 4, 'предательство близкого': 3, 'развод родителей': 2},
        'Маг': {'одиночество': 4, 'потеря близкого': 2, 'воспитание с установками': 2},
        'Мудрец': {'предательство близкого': 4, 'измена': 3, 'воспитание с установками': 2},
        'Шут': {'эмоциональное отвержение': 4, 'одиночество': 3, 'развод родителей': 2},
        'Герой': {'потеря близкого': 4, 'физическое насилие': 3, 'буллинг': 3, 'предательство близкого': 2},
    }
    if topic == 'flirt':
        flirt_safe_traumas = [t for t in trauma_data if t['name'] not in ('сексуальное насилие', 'отвержение внешности')]
        trauma_candidates = flirt_safe_traumas if flirt_safe_traumas else trauma_data
    else:
        trauma_candidates = trauma_data
    compat_map = archetype_trauma_compat.get(archetype_name, {})
    trauma_weights = [compat_map.get(t['name'], 1) for t in trauma_candidates]
    trauma = weighted_choice(trauma_candidates, trauma_weights)
    trauma_name = trauma['name']
    trauma_consequence = random.choice(trauma['consequence'])
    trauma_defense = random.choice(trauma['defense'])
    trauma_belief = trauma['belief']

    # --- Backstory (with trauma-aligned fragment) ---
    trauma_backstory_lines = {
        'предательство близкого': ['когда-то самый близкий человек предал её доверие, и с тех пор она никому не верит до конца'],
        'эмоциональное отвержение': ['родители были холодны и никогда не говорили, что любят её'],
        'физическое насилие': ['в детстве она регулярно сталкивалась с жестокостью дома'],
        'буллинг': ['в школе её травили и дразнили за внешность'],
        'потеря близкого': ['она потеряла самого родного человека и до сих пор не может это принять'],
        'гиперопека': ['родители контролировали каждый её шаг, не давая права на ошибку'],
        'измена': ['она пережила предательство от того, кого любила больше всего'],
        'бедность в детстве': ['семья жила в постоянной нехватке денег — она помнит, как экономили на еде'],
        'воспитание с установками': ['ей с детства внушали, что она должна быть лучше всех, чтобы её любили'],
        'одиночество': ['после переезда она осталась совсем одна и долго не могла найти друзей'],
        'развод родителей': ['когда родители развелись, она оказалась между ними и не знала, на чью сторону встать'],
        'сексуальное насилие': ['в её жизни был эпизод, о котором она старается не вспоминать'],
        'травма красоты': ['с детства её оценивали только по внешности — люди не видели в ней личность'],
        'отвержение внешности': ['близкие высмеивали её фигуру, и с тех пор она ненавидит своё тело'],
    }
    trauma_frags = trauma_backstory_lines.get(trauma_name, [])
    if trauma_frags:
        # Force trauma fragments to always appear by injecting them directly
        extra_backstory = list(trauma_frags) + extra_backstory
    # Use guaranteed count that includes trauma frags
    must_include = len(trauma_frags)
    backstory = generate_backstory(archetype_data, age_group, age, gender, extra_backstory, must_include=must_include)

    # --- Dynamic spice blocks (3-5 случайных деталей на персонажа) ---
    spice_slots = [
        'housing', 'financial_habit', 'eating_habit',
        'pet', 'red_flags', 'green_flags',
        'cryptonite', 'useless_talent', 'body_language_tell',
        'humor_style', 'biggest_lie', 'anger_trigger',
        'enemy', 'sleep_type', 'personal_scent', 'health_issue',
        'supernatural_belief',
    ]
    picked_spices = random.sample(spice_slots, min(random.randint(3, 5), len(spice_slots)))


    poverty_traumas = ['бедность в детстве', 'потеря состояния']
    if trauma_name in poverty_traumas and 'financial_habit' not in picked_spices:
        picked_spices.append('financial_habit')

    spice_values: dict = {k: '' for k in spice_slots}
    spice_values['red_flags'] = []
    spice_values['green_flags'] = []

    poverty_habits = [
        'скрупулёзно вносит все траты в приложение',
        'считает каждую копейку',
        'экономит на всём, даже на еде',
    ]
    low_income_meal_habits = [
        'питается лапшой быстрого приготовления',
        'готовит на неделю вперёд контейнерами',
        'перекусывает на бегу — нормального обеда нет',
        'едет в другой район за самыми дешёвыми продуктами',
    ]

    def pick(flag_pool, n=1):
        if isinstance(flag_pool, list):
            return random.choice(flag_pool) if n == 1 else random.sample(flag_pool, min(n, len(flag_pool)))
        return ''

    for s in picked_spices:
        if s == 'housing':
            spice_values[s] = pick(housing_pool)
        elif s == 'financial_habit':
            if trauma_name in poverty_traumas:
                spice_values[s] = random.choice(poverty_habits)
            else:
                spice_values[s] = pick(financial_habits_pool)
        elif s == 'eating_habit':
            wealth_rank = ['очень низкий', 'низкий', 'средний', 'выше среднего', 'высокий', 'очень высокий'].index(wealth_level)
            if wealth_rank <= 1:
                spice_values[s] = random.choice(low_income_meal_habits)
            else:
                spice_values[s] = pick(eating_habits_pool)
        elif s == 'pet':
            spice_values[s] = pick(pets_pool)
        elif s == 'red_flags':
            spice_values[s] = pick(red_flags_pool, 2)
        elif s == 'green_flags':
            spice_values[s] = pick(green_flags_pool, 2)
        elif s == 'cryptonite':
            spice_values[s] = pick(cryptonite_pool)
        elif s == 'useless_talent':
            spice_values[s] = pick(useless_talents_pool)
        elif s == 'body_language_tell':
            spice_values[s] = pick(body_language_tells_pool)
        elif s == 'humor_style':
            spice_values[s] = pick(humor_styles_pool)
        elif s == 'biggest_lie':
            spice_values[s] = pick(biggest_lies_pool)
        elif s == 'anger_trigger':
            spice_values[s] = pick(anger_triggers_pool)
        elif s == 'enemy':
            spice_values[s] = pick(enemies_pool)
        elif s == 'sleep_type':
            spice_values[s] = pick(sleep_types_pool)
        elif s == 'personal_scent':
            spice_values[s] = pick(personal_scents_pool)
        elif s == 'health_issue':
            spice_values[s] = pick(health_issues_pool)
        elif s == 'supernatural_belief':
            spice_values[s] = pick(supernatural_beliefs_pool)

    # --- Resolve sleep type vs habits conflicts ---
    sleep_type_val = spice_values.get('sleep_type', '')
    is_lark = ('жаворонок' in sleep_type_val or '6 утра' in sleep_type_val)
    if is_lark and 'любит поспать 9' in sleep_type_val:
        pass  # contradicting lark+long sleep is allowed (they just can't also wake at 5)
    if is_lark:
        habits = [h for h in habits if 'говорить во сне' not in h]
    if 'сова' in sleep_type_val or '2 ночи' in sleep_type_val:
        habits = [h for h in habits if h != 'просыпаться в 5 утра']
    if 'любит поспать 9' in sleep_type_val or 'хронически не высыпается' in sleep_type_val:
        habits = [h for h in habits if h != 'просыпаться в 5 утра']

    # --- Chat communication module (стиль письма, RP, мотивация входа) ---
    if topic == 'rp':
        style_weights = {
            'игровой стиль': 30, 'идеальная грамотность': 20,
            '~эстет~': 15, 'смешанный стиль': 10,
            'любитель многоточий': 8, 'скобочки и смайлики': 5,
            'all lowercase': 1, 'куча опечаток': 1,
        }
        writing_style = weighted_choice(
            list(style_weights.keys()), list(style_weights.values())
        )
    elif topic == 'flirt':
        style_weights = {
            'игровой стиль': 25, 'идеальная грамотность': 20,
            'скобочки и смайлики': 15, 'смешанный стиль': 12,
            '~эстет~': 10, 'любитель многоточий': 8,
            'all lowercase': 4, 'куча опечаток': 3,
        }
        writing_style = weighted_choice(
            list(style_weights.keys()), list(style_weights.values())
        )
    else:
        writing_style = random.choice(writing_styles)['name']
    if topic == 'rp':
        rp_weights = [20, 15, 35, 30]
    elif topic == 'flirt':
        rp_weights = [60, 15, 15, 10]
    else:
        rp_weights = [88, 6, 4, 2]
    rp_level = weighted_choice(
        [r['level'] for r in rp_ability_profiles],
        rp_weights,
    )
    rp_ability = rp_level in ('активный рп', 'профи рп')
    entry_context = random.choice(entry_contexts)
    # Age-filter situations
    if age_group == 'teen':
        teen_ok = [s for s in current_situations_pool if not any(
            kw in s[0] for kw in ['за рулём', 'стоит в пробке', 'на работе', 'лейт-шоу', 'деловой ужин', 'бар', 'вино', 'кофе в круглосуточной кофейне']
        )]
        current_situation = weighted_choice(
            [s[0] for s in teen_ok], [s[1] for s in teen_ok]
        ) if teen_ok else weighted_choice(
            [s[0] for s in current_situations_pool], [s[1] for s in current_situations_pool]
        )
    else:
        current_situation = weighted_choice(
            [s[0] for s in current_situations_pool], [s[1] for s in current_situations_pool]
        )
    mood_weights = {
        'игривое': 10, 'философское': 10, 'агрессивное': 5, 'сонное': 12,
        'пьяное': 5, 'грустное': 10, 'тревожное': 8, 'эйфорическое': 4,
        'ноющее («хочется поныть»)': 9, 'влюблённое': 4, 'злое': 5,
        'расслабленное': 8, 'апатичное': 6, 'весёлое': 10,
        'любопытное': 12, 'саркастичное': 7, 'благодарное': 3, 'одинокое': 8,
    }
    if topic == 'flirt':
        mood_weights['игривое'] = 30
        mood_weights['влюблённое'] = 20
        mood_weights['эйфорическое'] = 15
        mood_weights['агрессивное'] = 2
    elif topic == 'rp':
        mood_weights['философское'] = 25
        mood_weights['любопытное'] = 22
        mood_weights['расслабленное'] = 15
        mood_weights['эйфорическое'] = 10
    current_mood = weighted_choice(
        list(mood_weights.keys()),
        list(mood_weights.values()),
    )
    hidden_motive = random.choice(hidden_motives_pool)
    if topic == 'flirt':
        flirt_motive_weights = {
            'найти флирт / вирт': 25,
            'проверить, «а вдруг встречу свою половинку»': 18,
            'выпросить комплименты': 15,
            'повысить самооценку за чужой счёт': 12,
            'разнообразить скучный вечер': 10,
            'реально найти отношения': 8,
            'просто посмеяться': 6,
            'найти друга для переписок': 4,
            'просто убить 15 минут': 2,
            'выговориться про бывшего/бывшую': 2,
            'пожаловаться на жизнь': 2,
            'найти того, кто выслушает': 2,
            'потроллить неадекватов': 1,
            'спор ради спора': 1,
            'получить совет в сложной ситуации': 1,
            'постебаться над странными людьми': 1,
        }
        hidden_motive = weighted_choice(list(flirt_motive_weights.keys()), list(flirt_motive_weights.values()))
    elif topic == 'rp':
        rp_motive_weights = {
            'найти друга для переписок': 18,
            'просто убить 15 минут': 15,
            'разнообразить скучный вечер': 14,
            'просто посмеяться': 12,
            'найти того, кто выслушает': 10,
            'проверить, «а вдруг встречу свою половинку»': 8,
            'спор ради спора': 6,
            'пожаловаться на жизнь': 5,
            'получить совет в сложной ситуации': 4,
            'выговориться про бывшего/бывшую': 3,
            'потроллить неадекватов': 3,
            'постебаться над странными людьми': 2,
            'найти флирт / вирт': 2,
            'выпросить комплименты': 2,
            'повысить самооценку за чужой счёт': 1,
            'реально найти отношения': 1,
        }
        hidden_motive = weighted_choice(list(rp_motive_weights.keys()), list(rp_motive_weights.values()))
    if gender == 'male':
        opener_pool = chat_openers_pool + chat_openers_male_pool
        # Убираем женские варианты из пула
        opener_pool = [o for o in opener_pool if not o[0].lower().startswith('д ')]
    else:
        opener_pool = chat_openers_pool + chat_openers_female_pool
        # Убираем мужские варианты из пула
        opener_pool = [o for o in opener_pool if not o[0].lower().startswith('м ')]
    if topic == 'flirt':
        opener_pool = opener_pool + chat_openers_flirt_pool
    elif topic == 'rp':
        opener_pool = opener_pool + chat_openers_rp_pool
        if random.random() < 0.1:
            opener_pool = opener_pool + chat_openers_flirt_pool
    chat_opener = weighted_choice(
        [o[0] for o in opener_pool],
        [o[1] for o in opener_pool],
    )
    chat_opener = chat_opener.replace('{name}', name).replace('{age}', str(age))
    chat_opener = chat_opener.replace('{city}', city).replace('{profession}', profession)
    chat_opener = chat_opener.replace('{zodiac}', zodiac).replace('{mood}', current_mood)
    if '{hobby}' in chat_opener and hobbies:
        chat_opener = chat_opener.replace('{hobby}', random.choice(hobbies))
    skip_count = random.randint(1, 3)
    skip_factors = random.sample(skip_factors_pool, min(skip_count, len(skip_factors_pool)))
    if hidden_motive in ('найти флирт / вирт',) or chat_motivation == 'поиск пошлостей':
        skip_factors = [sf for sf in skip_factors if 'пошлост' not in sf and 'флиртует' not in sf]
    passive_reactions = ['молча нажимает «Next»', 'игнорирует и просто скипает', 'пишет «окей, было весело, пока» и отключается']
    aggressive_reactions = ['покрывает матом и блокирует', 'жестко троллит перед отключением']
    if trauma_defense in ('избегает конфликтов', 'замалчивает обиды', 'сбегает от ответственности', 'уходит от разговора'):
        harassment_reaction = random.choice(passive_reactions)
    elif trauma_defense in ('высмеивает других первой', 'иронизирует над чувствами', 'носит маску уверенности'):
        harassment_reaction = random.choice(aggressive_reactions)
    else:
        harassment_reaction = random.choice(harassment_reactions_pool)
    fav_topics = random.sample(fav_topics_pool, min(random.randint(2, 4), len(fav_topics_pool)))
    taboo_topics = random.sample(taboo_topics_pool, min(random.randint(2, 3), len(taboo_topics_pool)))
    # Resolve goal/taboo conflicts
    if hidden_motive in ('найти флирт / вирт',) or chat_motivation == 'поиск пошлостей':
        taboo_topics = [t for t in taboo_topics if t != 'секс и интимные подробности']
    if hidden_motive in ('выговориться про бывшего/бывшую', 'пожаловаться на жизнь'):
        taboo_topics = [t for t in taboo_topics if t != 'прошлые отношения']
    lying_tendency = weighted_choice(
        [l['level'] for l in lying_tendencies],
        [30, 25, 20, 10, 15],
    )
    if lying_tendency == 'играет роль':
        lying_tendency = f'играет роль: {_pick_lying_role()}'

    # --- Oversharing level (1-10) ---
    oversharing_base = profile_normalized.get('emotionality', 1.0) * 2.5
    oversharing_base += profile_normalized.get('sociability', 1.0) * 2
    oversharing_base -= profile_normalized.get('discipline', 1.0) * 0.8
    oversharing_base += profile_normalized.get('anxious', 1.0) * 1.5
    oversharing_base = max(1, min(10, round(oversharing_base)))
    oversharing_level = oversharing_base

    # Trauma reduces oversharing (closed traumas are not for strangers)
    closed_traumas = ['предательство близкого', 'страх привязанности', 'измена',
                      'сексуальное насилие', 'потеря близкого']
    if trauma_name in closed_traumas:
        oversharing_level = max(1, oversharing_level - 3)
    open_traumas = ['буллинг', 'эмоциональное отвержение', 'гиперопека',
                    'травма красоты', 'синдром самозванца']
    if trauma_name in open_traumas:
        oversharing_level = min(10, oversharing_level + 1)

    if chat_motivation in ('выговориться', 'выговориться про бывшего'):
        oversharing_level = min(10, oversharing_level + 3)
    if hidden_motive in ('выговориться про бывшего/бывшую', 'пожаловаться на жизнь'):
        oversharing_level = min(10, oversharing_level + 2)
    if lying_tendency.startswith('честная') or lying_tendency.startswith('приукрашивает'):
        oversharing_level = min(10, oversharing_level + 1)
    if lying_tendency.startswith('профессиональный') or lying_tendency.startswith('играет'):
        oversharing_level = max(1, oversharing_level - 2)
    if topic == 'flirt':
        oversharing_level = min(10, oversharing_level + 2)
    oversharing_level = max(1, min(10, oversharing_level))

    # --- Default attitude & weakness ---
    default_attitude = random.choice(default_attitudes_pool)
    weakness = random.choice(paradoxes_pool)
    gender_name = 'Женский' if gender == 'female' else 'Мужской'

    # --- System prompt (replaces generic bio) ---
    system_prompt = (
        f"Ты — {name} {surname}, {age} лет, {gender_name}. "
        f"Архетип: {archetype_name}, темперамент: {temp_name}, тип личности: {mbti_name} ({mbti_code}). "
        f"Стиль письма: {writing_style}. "
        f"Уровень откровенности: {oversharing_level}/10. "
        f"Ложь: {lying_tendency}. "
        f"Парадокс: {weakness}. "
        f"Установка при знакомстве: {default_attitude}."
    )

    # --- Bio ---
    character_for_bio = Character(
        name=name, surname=surname, gender=('Женский' if gender == 'female' else 'Мужской'),
        birth_date=birth_date.strftime('%d.%m.%Y'), age=age, zodiac=zodiac,
        height=height_str,
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
        housing=spice_values.get('housing', ''),
        financial_habit=spice_values.get('financial_habit', ''),
        eating_habit=spice_values.get('eating_habit', ''),
        pet=spice_values.get('pet', ''),
        red_flags=spice_values.get('red_flags', []),
        green_flags=spice_values.get('green_flags', []),
        cryptonite=spice_values.get('cryptonite', ''),
        useless_talent=spice_values.get('useless_talent', ''),
        body_language_tell=spice_values.get('body_language_tell', ''),
        humor_style=spice_values.get('humor_style', ''),
        biggest_lie=spice_values.get('biggest_lie', ''),
        anger_trigger=spice_values.get('anger_trigger', ''),
        enemy=spice_values.get('enemy', ''),
        sleep_type=spice_values.get('sleep_type', ''),
        personal_scent=spice_values.get('personal_scent', ''),
        health_issue=spice_values.get('health_issue', ''),
        supernatural_belief=spice_values.get('supernatural_belief', ''),
        writing_style=writing_style,
        rp_ability=rp_ability,
        entry_context=entry_context,
        current_situation=current_situation,
        current_mood=current_mood,
        hidden_motive=hidden_motive,
        chat_opener=chat_opener,
        skip_factors=skip_factors,
        harassment_reaction=harassment_reaction,
        fav_topics=fav_topics,
        taboo_topics=taboo_topics,
        lying_tendency=lying_tendency,
        oversharing_level=oversharing_level,
        default_attitude=default_attitude,
        weakness=weakness,
        system_prompt=system_prompt,
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


def _pick_body_type_by_bmi(bmi):
    if bmi < 17:
        eligible = [(b, w) for b, w in body_types if b in ('субтильное', 'худощавое', 'изящное')]
    elif bmi < 19:
        eligible = [(b, w) for b, w in body_types if b in ('стройное', 'худощавое', 'изящное')]
    elif bmi < 24:
        eligible = [(b, w) for b, w in body_types if b in ('среднее', 'стройное', 'атлетичное')]
    elif bmi < 28:
        eligible = [(b, w) for b, w in body_types if b in ('плотное', 'среднее', 'коренастое')]
    else:
        eligible = [(b, w) for b, w in body_types if b in ('пышное', 'полное', 'плотное')]
    if not eligible:
        eligible = body_types
    return weighted_choice([b[0] for b in eligible], [b[1] for b in eligible])


def _resolve_backstory_conflicts(body_size_key, beauty_key, backstory_fragments):
    """Resolve conflicts between body_size and beauty backstory fragments.
    If body_size has negative body image backstory (нейтральный/отрицательный),
    exclude beauty fragments about 'привыкла к комплиментам' and 'ценят за внешность'."""
    negative_body = body_size_key in ('очень худая', 'пышная', 'полная')
    if negative_body and beauty_key in ('красивая', 'очень красивая'):
        filtered = []
        for f in backstory_fragments:
            if 'привыкла к комплиментам' in f or 'ценят её только за внешность' in f:
                continue
            filtered.append(f)
        return filtered
    return backstory_fragments


_lying_roles = [
    'богатую наследницу нефтяной компании',
    'агента под прикрытием',
    'ведьму из старинного рода',
    'путешественницу во времени',
    'космического рейнджера',
    'пришельца с Марса',
    'тайного агента ФСБ',
    'стриптизёршу из элитного клуба',
    'беглую принцессу',
    'хакера из Anonymous',
    'жену олигарха (который «всё контролирует»)',
    'модель Plus Size',
    'участницу шоу «Голос»',
    'профессиональную гадалку',
    'владелицу частного музея',
]


def _pick_lying_role():
    return random.choice(_lying_roles)


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
