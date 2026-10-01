"""Companheiros: estado isolado dos saves integrais do personagem.
As ações usam revisão otimista; o cliente nunca informa XP, distância ou bônus.
"""
import copy
import math
from bson import ObjectId

FAMILIES = {
    "slime": {"name": "Slime", "icon": "🟢", "stat": "defense", "label": "Defesa", "specialties": {"guardiao": ["Guardião", "defense"], "vital": ["Vital", "max_hp"]}},
    "lobo": {"name": "Lobo", "icon": "🐺", "stat": "initiative", "label": "Iniciativa", "specialties": {"veloz": ["Veloz", "initiative"], "guardiao": ["Guardião", "defense"]}},
    "morcego": {"name": "Morcego", "icon": "🦇", "stat": "max_mana", "label": "Mana máxima", "specialties": {"arcano": ["Arcano", "max_mana"], "veloz": ["Veloz", "initiative"]}},
}
HATCH_DISTANCE = 96000  # 3000 blocos de 32px; cerca de 11min de caminhada a 150px/s.
FORMS = ["Filhote", "Adulto", "Ancestral"]


def family_of(monster_id):
    key = str(monster_id or "")
    if key.startswith(('ond', 'onda')):
        return None
    return next((f for f in FAMILIES if f in key), None)


def initial():
    return {"version": 0, "incubator": False, "claimed": [], "eggs": [], "incubation": None, "pets": {}, "active": None, "essences": {}}


def collection():
    from modules.player.core import users_collection
    return users_collection.database['companions']


def load(user_id):
    return collection().find_one({'_id': ObjectId(str(user_id))}) or initial()


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
        state = copy.deepcopy(old)
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


def view(player, state):
    result = copy.deepcopy(state)
    result.pop('_id', None)
    result['families'] = FAMILIES
    result['knowledge'] = knowledge(player)
    result['incubator_progress'] = sum(max(0, int(n)) for n in (player.get('bestiario') or {}).values())
    result['hatch_distance'] = HATCH_DISTANCE
    result['bonus'] = bonus(state)
    for key, pet in result['pets'].items():
        pet['level'], pet['level_xp'], pet['next_xp'] = level(pet)
        pet['form'] = FORMS[pet.get('stage', 0)]
    return result


def action(player, state, action, family=None, specialty=None):
    if not isinstance(action, str) or (family is not None and not isinstance(family, str)) or (specialty is not None and not isinstance(specialty, str)):
        raise ValueError('Pedido inválido.')
    counts = knowledge(player)
    if action == 'incubator':
        if state['incubator']:
            raise ValueError('Você já possui uma chocadeira.')
        if sum(int(n) for n in (player.get('bestiario') or {}).values()) < 10:
            raise ValueError('Registre 10 abates no Bestiário para receber a chocadeira.')
        state['incubator'] = True
        return 'Chocadeira permanente recebida!'
    if action == 'unequip':
        state['active'] = None
        return 'Companheiro guardado.'
    if family not in FAMILIES:
        raise ValueError('Escolha uma família válida.')
    if action == 'claim':
        if counts[family] < 50 or family in state['claimed']:
            raise ValueError('Conquista indisponível ou já resgatada.')
        state['claimed'].append(family)
        state['eggs'].append(family)
        return 'Ovo recebido! Coloque-o na chocadeira.'
    if action == 'incubate':
        if not state['incubator'] or state['incubation'] or family not in state['eggs']:
            raise ValueError('Você precisa de uma chocadeira livre e desse ovo.')
        state['eggs'].remove(family)
        state['incubation'] = {'family': family, 'distance': 0}
        return 'Incubação iniciada. Explore o mundo para chocar!'
    if action == 'hatch':
        egg = state['incubation']
        if not egg or egg['family'] != family or egg['distance'] < HATCH_DISTANCE or family in state['pets']:
            raise ValueError('O ovo ainda não está pronto.')
        state['pets'][family] = {'xp': 0, 'bond': 0, 'stage': 0, 'specialty': None}
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
    if not state.get('active'):
        return
    def reward(s):
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
