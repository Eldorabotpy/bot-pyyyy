"""Companheiros: estado isolado dos saves integrais do personagem.
As ações usam revisão otimista; o cliente nunca informa XP, distância ou bônus.
"""
import copy
import math
from datetime import datetime, timedelta, timezone
from bson import ObjectId

FAMILIES = {
    "slime": {"name": "Slime", "icon": "🟢", "stat": "defense", "label": "Defesa", "specialties": {"guardiao": ["Guardião", "defense"], "vital": ["Vital", "max_hp"]}},
    "lobo": {"name": "Lobo", "icon": "🐺", "stat": "initiative", "label": "Iniciativa", "specialties": {"veloz": ["Veloz", "initiative"], "guardiao": ["Guardião", "defense"]}},
    "morcego": {"name": "Morcego", "icon": "🦇", "stat": "max_mana", "label": "Mana máxima", "specialties": {"arcano": ["Arcano", "max_mana"], "veloz": ["Veloz", "initiative"]}},
}
HATCH_DISTANCE = 96000  # 3000 blocos de 32px; cerca de 11min de caminhada a 150px/s.
PREMIUM_HUNT_GOALS = (100, 500, 1500)
FORMS = ["Filhote", "Adulto", "Ancestral"]


# Aumentar somente quando as missões e artes do próximo capítulo estiverem prontas.
RELEASED_PET_CHAPTER = 1
ASSET_ROOT = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/'
PET_JOURNEYS = {
    'slime': [('Pequeno Slime', 'pequeno_slime', 'pradaria', 1), ('Slime Verde', 'slime_verde', 'pradaria', 2), ('Rei Slime', 'rei_slime', 'pradaria', 4)],
    'lobo': [('Lobo Magro', 'lobo_magro', 'floresta', 1), ('Lobo Alfa', 'lobo_alfa', 'floresta', 2), ('Lobisomem', 'lobisomem_campones', 'campos_linho', 4)],
    'morcego': [('Morcego das Minas', 'morcego_das_minas', 'mina_ferro', 5)],
}


def journey(family):
    return [{'name': name, 'species': species, 'chapter': chapter,
             'released': chapter <= RELEASED_PET_CHAPTER,
             'image': f'{ASSET_ROOT}mob/combate/{region}/{species}.png',
             'sheet': f'{ASSET_ROOT}mob/pet/{species}.png'}
            for name, species, region, chapter in PET_JOURNEYS[family]]


def family_of(monster_id):
    key = str(monster_id or "")
    if key.startswith(('ond', 'onda')):
        return None
    return next((f for f in FAMILIES if f in key), None)


def initial():
    return {"version": 0, "incubator_schema": 2, "incubators": 0, "incubator_claimed": False, "premium_incubators": [], "supply_receipts": [], "claimed": [], "eggs": [], "incubation": None, "pets": {}, "active": None, "essences": {}}


def normalize(state):
    state = copy.deepcopy(state)
    if state.get('incubator_schema') != 2:
        owned = bool(state.get('incubator'))
        state['incubators'] = 1 if owned and not state.get('incubation') else 0
        state['incubator_claimed'] = owned
        state['incubator_schema'] = 2
    state.pop('incubator', None)
    state.setdefault('premium_incubators', [])
    state.setdefault('supply_receipts', [])
    state.setdefault('premium_cycles', {})
    return state


def collection():
    from modules.player.core import users_collection
    return users_collection.database['companions']


def load(user_id):
    return normalize(collection().find_one({'_id': ObjectId(str(user_id))}) or initial())


def mutate(user_id, change):
    from pymongo.errors import DuplicateKeyError
    col = collection()
    oid = ObjectId(str(user_id))
    try:
        col.update_one({'_id': oid}, {'$setOnInsert': initial()}, upsert=True)
    except DuplicateKeyError:
        pass
    for _ in range(5):
        old = col.find_one({'_id': oid})
        state = normalize(old)
        result = change(state)
        state['version'] = old['version'] + 1
        state.pop('_id', None)
        if col.update_one({'_id': oid, 'version': old['version']}, {'$set': state}).modified_count:
            return result
    raise ValueError('O companheiro foi atualizado. Tente novamente.')


def knowledge(player):
    counts = {f: 0 for f in FAMILIES}
    for mid, qty in (player.get('bestiario') or {}).items():
        f = family_of(mid)
        if f:
            counts[f] += max(0, int(qty))
    return counts


def level(pet):
    xp = pet.get('xp', 0)
    value = 1
    while value < 25 and xp >= 50 * value:
        xp -= 50 * value
        value += 1
    return value, xp, 50 * value


def bonus(state):
    key = state.get('active')
    pet = state.get('pets', {}).get(key)
    if not pet or key not in FAMILIES:
        return {}
    lvl = level(pet)[0]
    stage = pet.get('stage', 0)
    stat = FAMILIES[key]['stat']
    if stage == 2:
        stat = FAMILIES[key]['specialties'].get(pet.get('specialty'), ['', stat])[1]
    amount = 1 + lvl // 5 + stage * 2
    return {stat: amount * (3 if stat in ('max_hp', 'max_mana') else 1)}


def utc_date(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def premium_cycle(player, now=None):
    """Renovação antecipada estende expires_at, preservando activated_at."""
    now = utc_date(now) or datetime.now(timezone.utc)
    premium = player.get('eldora_premium') or {}
    start, end = utc_date(premium.get('activated_at')), utc_date(premium.get('expires_at'))
    if not start or not end or not start <= now < end:
        return None
    start += timedelta(days=30) * ((now - start) // timedelta(days=30))
    return {'id': str(int(start.timestamp())), 'start': start.isoformat(),
            'end': min(start + timedelta(days=30), end).isoformat(), 'kills': 0, 'claimed': []}


def premium_player(user_id):
    from modules.player.core import users_collection
    return users_collection.find_one({'_id': ObjectId(str(user_id))}, {'eldora_premium': 1}) or {}


def advance_premium(state, cycle):
    if cycle:
        saved = state.setdefault('premium_cycles', {}).setdefault(cycle['id'], copy.deepcopy(cycle))
        saved['kills'] = min(PREMIUM_HUNT_GOALS[-1], saved['kills'] + 1)


def premium_view(player, state, now=None):
    current = premium_cycle(player, now)
    cycles = copy.deepcopy(state.get('premium_cycles', {}))
    if current:
        cycles.setdefault(current['id'], current)
    result = []
    for key, cycle in sorted(cycles.items(), reverse=True):
        active = bool(current and current['id'] == key)
        rewards = [{'goal': goal, 'id': f'{key}:{goal}', 'claimed': goal in cycle['claimed'],
                    'eligible': cycle['kills'] >= goal} for goal in PREMIUM_HUNT_GOALS]
        if active or any(r['eligible'] and not r['claimed'] for r in rewards):
            result.append({**cycle, 'active': active, 'rewards': rewards})
    return {'active': bool(current), 'cycles': result}


def view(player, state):
    result = normalize(state)
    result.pop('_id', None)
    result['families'] = {key: {**value, 'journey': journey(key), 'available': journey(key)[0]['released']} for key, value in FAMILIES.items()}
    result['chapter'] = RELEASED_PET_CHAPTER
    result['knowledge'] = knowledge(player)
    result['incubator_progress'] = sum(max(0, int(n)) for n in (player.get('bestiario') or {}).values())
    result['premium_missions'] = premium_view(player, result)
    result['hatch_distance'] = HATCH_DISTANCE
    result['bonus'] = bonus(state)
    for key, pet in result['pets'].items():
        pet['level'], pet['level_xp'], pet['next_xp'] = level(pet)
        steps = journey(key)
        step = steps[min(pet.get('stage', 0), len(steps)-1)]
        pet['art'] = step
        pet['form'] = step['name'] if pet.get('journey_version') == 1 else FORMS[pet.get('stage', 0)]
        next_stage = pet.get('stage', 0) + 1
        pet['next_released'] = next_stage < len(steps) and steps[next_stage]['released']
    return result


def action(player, state, action, family=None, specialty=None):
    if not isinstance(action, str) or (family is not None and not isinstance(family, str)) or (specialty is not None and not isinstance(specialty, str)):
        raise ValueError('Pedido inválido.')
    counts = knowledge(player)
    if action == 'incubator':
        if state['incubator_claimed']:
            raise ValueError('Esta conquista já foi resgatada.')
        if sum(int(n) for n in (player.get('bestiario') or {}).values()) < 10:
            raise ValueError('Registre 10 abates no Bestiário para receber a chocadeira.')
        state['incubator_claimed'] = True
        state['incubators'] += 1
        return 'Você recebeu 1 incubadora de uso único!'
    if action == 'premium_incubator':
        try:
            cycle_id, goal_text = (family or '').split(':')
            goal = int(goal_text)
        except (ValueError, TypeError):
            raise ValueError('Escolha uma missão Premium válida.')
        cycle = state.get('premium_cycles', {}).get(cycle_id)
        if not cycle or goal not in PREMIUM_HUNT_GOALS or cycle['kills'] < goal:
            raise ValueError('Complete os abates desta missão do Eldora Premium.')
        if goal in cycle['claimed']:
            raise ValueError('Recompensa desta missão já resgatada.')
        cycle['claimed'].append(goal)
        state['incubators'] += 1
        return 'Incubadora da missão do Eldora Premium recebida!'
    if action == 'unequip':
        state['active'] = None
        return 'Companheiro guardado.'
    if family not in FAMILIES:
        raise ValueError('Escolha uma família válida.')
    if action == 'claim':
        if not journey(family)[0]['released']:
            raise ValueError('Esta família será liberada em um próximo capítulo.')
        if counts[family] < 50 or family in state['claimed']:
            raise ValueError('Conquista indisponível ou já resgatada.')
        state['claimed'].append(family)
        state['eggs'].append(family)
        return 'Ovo recebido! Coloque-o na chocadeira.'
    if action == 'incubate':
        if state['incubators'] < 1 or state['incubation'] or family not in state['eggs']:
            raise ValueError('Você precisa de uma chocadeira livre e desse ovo.')
        state['incubators'] -= 1
        state['eggs'].remove(family)
        state['incubation'] = {'family': family, 'distance': 0}
        return 'Incubação iniciada. Explore o mundo para chocar!'
    if action == 'hatch':
        egg = state['incubation']
        if not egg or egg['family'] != family or egg['distance'] < HATCH_DISTANCE or family in state['pets']:
            raise ValueError('O ovo ainda não está pronto.')
        state['pets'][family] = {'xp': 0, 'bond': 0, 'stage': 0, 'specialty': None, 'journey_version': 1}
        state['incubation'] = None
        state['active'] = state['active'] or family
        return 'O ovo chocou! Seu novo companheiro chegou.'
    pet = state['pets'].get(family)
    if not pet:
        raise ValueError('Esse companheiro ainda não nasceu.')
    if action == 'equip':
        state['active'] = family
        return 'Companheiro equipado!'
    if action == 'evolve':
        stage = pet['stage']
        if stage >= 2:
            raise ValueError('Esse companheiro já alcançou a forma final.')
        steps = journey(family)
        if stage + 1 >= len(steps) or not steps[stage + 1]['released']:
            raise ValueError('Esta evolução ainda não foi liberada. Seu progresso está salvo.')
        req_level, req_bond, cost = (10, 50, 25) if stage == 0 else (25, 300, 100)
        if level(pet)[0] < req_level or pet['bond'] < req_bond or state['essences'].get(family, 0) < cost:
            raise ValueError('Complete o nível, o vínculo e as essências da evolução.')
        if stage == 1 and specialty not in FAMILIES[family]['specialties']:
            raise ValueError('Escolha a especialização final.')
        state['essences'][family] -= cost
        pet['stage'] += 1
        pet['specialty'] = specialty if stage == 1 else None
        return 'Evolução concluída!'
    raise ValueError('Ação inválida.')


def record_victory(user_id, monster_id):
    # Chamado apenas no fluxo de abate confirmado; não há endpoint de XP.
    state = load(user_id)
    cycle = premium_cycle(premium_player(user_id))
    if not state.get('active') and not cycle:
        return
    def reward(s):
        advance_premium(s, cycle)
        pet = s['pets'].get(s.get('active'))
        if pet:
            pet['xp'] = min(15000, pet['xp'] + 10)
            pet['bond'] += 1
            f = family_of(monster_id)
            if f:
                s['essences'][f] = s['essences'].get(f, 0) + 1
    mutate(user_id, reward)


def movement_distance(previous, region, x, y, now):
    # Troca de mapa, reconexão, teleporte e pacotes impossíveis não rendem distância.
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (x, y, now)):
        return None, 0
    sample = (region, x, y, now)
    if not previous or previous[0] != region:
        return sample, 0
    elapsed = now - previous[3]
    distance = math.hypot(x - previous[1], y - previous[2])
    if elapsed <= 0 or elapsed > 3 or distance > 180 * elapsed + 8:
        return sample, 0
    return sample, min(distance, 150 * elapsed)


def record_distance(user_id, distance):
    if distance <= 0:
        return
    def advance(s):
        egg = s.get('incubation')
        if egg:
            egg['distance'] = min(HATCH_DISTANCE, egg['distance'] + distance)
    mutate(user_id, advance)


def profile_slot(user_id):
    if not ObjectId.is_valid(str(user_id)):
        return None
    state = load(user_id)
    key = state.get('active')
    pet = state.get('pets', {}).get(key)
    if not pet or key not in FAMILIES:
        return None
    return {'name': FAMILIES[key]['name'], 'icon': FAMILIES[key]['icon'],
            'level': level(pet)[0], 'form': FORMS[pet['stage']]}


def flush_movement(online):
    distance = online.get('_pet_distance', 0)
    if distance and online.get('char_id') and load(online['char_id']).get('incubation'):
        record_distance(online['char_id'], distance)
    online['_pet_distance'] = 0


def deliver_supplies(user_id, player):
    """Créditos pagos duráveis. Repetir a leitura após falha não duplica a entrega."""
    grants = player.get('companion_incubator_grants') or []
    current = load(user_id)
    missing = [g for g in grants if g['id'] not in current['supply_receipts']]
    if not missing:
        return
    def deliver(state):
        for grant in missing:
            if grant['id'] not in state['supply_receipts']:
                state['incubators'] += int(grant['quantity'])
                state['supply_receipts'].append(grant['id'])
    mutate(user_id, deliver)
