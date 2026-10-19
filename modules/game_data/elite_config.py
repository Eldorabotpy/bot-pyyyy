"""Balanceamento dos monstros de elite do mundo aberto."""

# Chance por instância de spawn. Elites definidos diretamente no catálogo
# continuam sendo elites sem rolagem aleatória.
ELITE_CHANCE = 0.12

# Multiplicadores usados somente em elites sorteados. Os elites que já foram
# balanceados individualmente no catálogo mantêm seus atributos próprios.
ELITE_MULTIPLIERS = {
    "hp": 2.0,
    "attack": 1.4,
    "defense": 1.3,
    "xp": 1.5,
    "gold": 1.5,
    "initiative_add": 2,
    "luck_add": 5,
    "loot_bonus_pct": 10,
}
