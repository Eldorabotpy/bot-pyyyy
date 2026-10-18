import unittest

from pvp.season_ranking import (
    build_elo_standings,
    build_player_season_rank,
    current_season_points,
    find_player_season_position,
)
from pvp.season_history import build_player_match_history


class PvpSeasonRankingTests(unittest.TestCase):
    def test_groups_players_at_each_elo_threshold(self):
        points = [0, 1499, 1500, 3999, 4000, 7999, 8000, 9999, 10000]
        players = [
            {"nome": f"Herói {index}", "pontos": value, "vitorias": index}
            for index, value in enumerate(points)
        ]

        tiers, ranking, total = build_elo_standings(players)

        self.assertEqual(
            [(tier["nome"], tier["quantidade"]) for tier in tiers],
            [("Bronze", 2), ("Prata", 2), ("Ouro", 2), ("Diamante", 2), ("Mestre", 1)],
        )
        self.assertEqual(total, len(points))
        self.assertEqual([player["pontos"] for player in ranking], [10000, 9999, 8000, 7999, 4000])

    def test_emblems_and_display_names_are_returned_for_every_tier(self):
        players = [
            {"nome": "Bronzeiro", "pontos": 0},
            {"nome": "Prateada", "pontos": 1500},
            {"nome": "Dourado", "pontos": 4000},
            {"nome": "Cristal", "pontos": 8000},
            {"nome": "Campeão", "pontos": 10000},
        ]

        tiers, _, _ = build_elo_standings(players)

        self.assertEqual([tier["id"] for tier in tiers], ["bronze", "prata", "ouro", "diamante", "mestre"])
        self.assertTrue(all(tier["icone"].endswith(f"/{tier['id']}.svg") for tier in tiers))
        self.assertEqual(tiers[-1]["jogadores"][0]["elo"], "Mestre")

    def test_each_tier_has_five_divisions_with_i_as_the_entry_division(self):
        points = [0, 300, 600, 900, 1200, 1500, 2000, 2500, 3000, 3500,
                  4000, 4800, 5600, 6400, 7200, 8000, 8400, 8800, 9200,
                  9600, 10000, 11000, 12000, 13000, 14000]
        tiers, ranking, _ = build_elo_standings([
            {"nome": f"Herói {index}", "pontos": value}
            for index, value in enumerate(points)
        ])

        self.assertTrue(all(len(tier["divisoes"]) == 5 for tier in tiers))
        self.assertEqual(
            [division["romano"] for division in tiers[0]["divisoes"]],
            ["I", "II", "III", "IV", "V"],
        )
        self.assertEqual(
            [division["quantidade"] for division in tiers[0]["divisoes"]],
            [1, 1, 1, 1, 1],
        )
        self.assertTrue(all(
            [division["quantidade"] for division in tier["divisoes"]] == [1, 1, 1, 1, 1]
            for tier in tiers
        ))
        self.assertEqual(
            [tier["divisoes"][0]["jogadores"][0]["divisao_nome"] for tier in tiers],
            ["Bronze I", "Prata I", "Ouro I", "Diamante I", "Mestre I"],
        )
        self.assertEqual(
            [(division["minimo"], division["maximo"]) for division in tiers[0]["divisoes"]],
            [(0, 299), (300, 599), (600, 899), (900, 1199), (1200, 1499)],
        )
        self.assertEqual(
            [(division["minimo"], division["maximo"]) for division in tiers[-1]["divisoes"]],
            [(10000, 10999), (11000, 11999), (12000, 12999), (13000, 13999), (14000, None)],
        )
        self.assertEqual(
            [division["icone"].rsplit("/", 1)[-1] for tier in tiers for division in tier["divisoes"]],
            [
                f"{tier['nome'].replace(' ', '_')}_{roman}.png"
                for tier in tiers
                for roman in ("I", "II", "III", "IV", "V")
            ],
        )
        self.assertEqual(ranking[0]["elo_completo"], "Mestre V")
        self.assertIsNone(tiers[-1]["divisoes"][-1]["maximo"])

    def test_player_rank_includes_progress_to_next_division(self):
        rank = build_player_season_rank({"nome": "Herói", "pontos": 299, "vitorias": 4, "derrotas": 2})

        self.assertEqual(rank["elo_completo"], "Bronze I")
        self.assertTrue(rank["icone"].endswith("/Bronze_I.png"))
        self.assertEqual(rank["proxima_divisao"], "Bronze II")
        self.assertEqual(rank["pontos_para_proxima"], 1)
        self.assertEqual(rank["progresso_percentual"], 99)

    def test_last_master_division_has_no_next_rank(self):
        rank = build_player_season_rank({"nome": "Campeão", "pontos": 14000})

        self.assertEqual(rank["elo_completo"], "Mestre V")
        self.assertIsNone(rank["proxima_divisao"])
        self.assertIsNone(rank["progresso_percentual"])

    def test_match_history_uses_the_selected_player_position(self):
        matches = [
            {
                "jogadores": ["hero", "rival"],
                "nomes": ["Herói", "Rival"],
                "vencedor": "rival",
                "alteracoes": [{"delta": -28, "pontos": 472}, {"delta": 28, "pontos": 528}],
                "temporada": 3,
            },
            {
                "jogadores": ["rival", "hero"],
                "nomes": ["Rival", "Herói"],
                "vencedor": "hero",
                "alteracoes": [{"delta": -31, "pontos": 497}, {"delta": 31, "pontos": 503}],
                "temporada": 3,
            },
        ]

        history = build_player_match_history("hero", matches)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["adversario"], "Rival")
        self.assertFalse(history[0]["vitoria"])
        self.assertEqual((history[0]["variacao"], history[0]["pontos"]), (-28, 472))
        self.assertTrue(history[1]["vitoria"])
        self.assertEqual((history[1]["variacao"], history[1]["pontos"]), (31, 503))

    def test_match_history_respects_limit(self):
        matches = [
            {"jogadores": ["hero", str(index)], "nomes": ["Herói", f"Rival {index}"]}
            for index in range(5)
        ]

        self.assertEqual(len(build_player_match_history("hero", matches, limit=3)), 3)
        self.assertEqual(build_player_match_history("hero", matches, limit=0), [])

    def test_old_season_points_do_not_affect_current_rival_selection(self):
        self.assertEqual(current_season_points({"pvp_season_number": 2, "pvp_points": 6400}, 3), 0)
        self.assertEqual(current_season_points({"pvp_season_number": 3, "pvp_points": 6400}, 3), 6400)

    def test_player_season_position_uses_points_and_tiebreakers(self):
        players = [
            {"id": "hero", "nome": "Herói", "pontos": 900, "vitorias": 7, "derrotas": 2},
            {"id": "leader", "nome": "Líder", "pontos": 1000, "vitorias": 2, "derrotas": 1},
            {"id": "rival", "nome": "Rival", "pontos": 900, "vitorias": 8, "derrotas": 2},
        ]

        self.assertEqual(
            find_player_season_position(players, "hero"),
            {"posicao_temporada": 3, "participantes_temporada": 3},
        )
        self.assertIsNone(find_player_season_position(players, "missing"))


if __name__ == "__main__":
    unittest.main()
