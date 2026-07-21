from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import random


@dataclass
class Character:
    name: str
    surname: str
    gender: str
    birth_date: str
    age: int
    zodiac: str
    height: str
    eye_color: str
    hair_color: str
    hair_length: str
    body_type: str
    skin_tone: str
    distinctive_features: list
    clothing_style: str
    body_size: str
    beauty: str
    appearance_description: str
    temperament: str
    archetype: str
    archetype_desire: str
    archetype_goal: str
    archetype_fear: str
    archetype_talent: str
    mbti_code: str
    mbti_name: str
    social_style: str
    positive_traits: list
    negative_traits: list
    wealth_level: str
    wealth_label: str
    hobbies: list
    profession: str
    profession_group: str
    education: str
    languages: list
    relationship_status: str
    city: str
    astrology_belief: str
    sexual_openness: str
    chat_motivation: str
    gym_habit: str
    hair_style: str
    favorite_movie_titles: list
    favorite_book_titles: list
    favorite_music_artists: list
    trauma_name: str
    trauma_consequence: str
    trauma_defense: str
    trauma_belief: str
    favorite_colors: list
    favorite_foods: list
    favorite_drinks: list
    favorite_music_genres: list
    favorite_seasons: list
    favorite_movie_genres: list
    favorite_book_genres: list
    fetishes: list
    habits: list
    fears: list
    dreams: list
    relationship_values: list
    backstory: str
    bio: str
    housing: str
    financial_habit: str
    eating_habit: str
    pet: str
    red_flags: list
    green_flags: list
    cryptonite: str
    useless_talent: str
    body_language_tell: str
    humor_style: str
    biggest_lie: str
    anger_trigger: str
    enemy: str
    sleep_type: str
    personal_scent: str
    health_issue: str
    supernatural_belief: str
    writing_style: str
    rp_ability: bool
    entry_context: str
    current_situation: str
    current_mood: str
    hidden_motive: str
    chat_opener: str
    skip_factors: list
    harassment_reaction: str
    fav_topics: list
    taboo_topics: list
    lying_tendency: str
    oversharing_level: int
    default_attitude: str
    weakness: str
    system_prompt: str


def weighted_choice(items, weights):
    total = sum(weights)
    r = random.uniform(0, total)
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def weighted_sample(pool, weights, k):
    if k >= len(pool):
        return list(pool)
    indices = list(range(len(pool)))
    chosen = []
    for _ in range(k):
        if not indices:
            break
        ws = [weights[i] for i in indices]
        idx = weighted_choice(indices, ws)
        indices.remove(idx)
        chosen.append(pool[idx])
    return chosen


def pick_from_pool(pool, profile, count_min=1, count_max=3, sample_count=None, boost_list=None):
    if sample_count is None:
        sample_count = random.randint(count_min, count_max)
    if boost_list is None:
        boost_list = []
    if sample_count >= len(pool):
        return [item[0] if isinstance(item, tuple) else item for item in pool]
    weights = []
    for item in pool:
        item_name = item[0] if isinstance(item, tuple) else item
        if isinstance(item, tuple):
            item_data = item[1] if isinstance(item[1], dict) else {}
            weight = 1
            for key, value in item_data.items():
                if key in profile and isinstance(profile[key], (int, float)):
                    weight += max(0, profile[key] * value / 100)
                elif key == 'pop' and isinstance(value, (int, float)):
                    weight += max(0, value)
            if item_name in boost_list:
                weight *= 3
            weight = max(0.1, weight)
            weights.append(weight)
        else:
            w = 2 if item_name in boost_list else 1
            weights.append(w)
    chosen = set()
    result = []
    for _ in range(sample_count):
        available = [i for i in range(len(pool)) if i not in chosen]
        if not available:
            break
        avail_weights = [weights[i] for i in available]
        idx = weighted_choice(available, avail_weights)
        chosen.add(idx)
        item = pool[idx]
        if isinstance(item, tuple):
            result.append(item[0])
        else:
            result.append(item)
    return result


def random_date(start_year=1980, end_year=2005):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    days = random.randint(0, delta.days)
    return start + timedelta(days=days)


def zodiac_sign(day, month):
    signs = [
        (1, 20, 'Козерог'), (2, 19, 'Водолей'), (3, 21, 'Рыбы'),
        (4, 20, 'Овен'), (5, 21, 'Телец'), (6, 21, 'Близнецы'),
        (7, 22, 'Рак'), (8, 21, 'Лев'), (9, 23, 'Дева'),
        (10, 23, 'Весы'), (11, 23, 'Скорпион'), (12, 22, 'Стрелец'),
    ]
    for m, d, sign in signs:
        if month == m and day <= d:
            return sign
    return 'Козерог'
