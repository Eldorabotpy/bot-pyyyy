"""Balanceamento dos monstros de elite do mundo aberto."""

# Chance por instância de spawn. Elites definidos diretamente no catálogo
# continuam sendo elites sem rolagem aleatória.
ELITE_CHANCE = 0.12

# Multiplicadores de combate aplicados a toda instância elite no mundo aberto.
# A origem continua indicada por elite_generated para missões e drops especiais.
ELITE_MULTIPLIERS = {
    "hp": 4.0,
    "attack": 4.0,
    "defense": 4.0,
    "xp": 1.5,
    "gold": 1.5,
    "initiative_add": 2,
    "luck_add": 5,
    "loot_bonus_pct": 10,
}
