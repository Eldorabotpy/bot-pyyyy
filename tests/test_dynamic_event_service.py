import unittest
from datetime import datetime, timezone
from flask import Flask

from modules.events.dynamic_event_service import (
    DEFAULT_TIERS,
    EventError,
    ITEMS_DATA,
    monthly_invasion_windows,
    normalize_config,
    points_after_daily_cap,
)


class DynamicEventConfigTests(unittest.TestCase):
    def test_monthly_invasion_runs_first_seven_days_in_sao_paulo(self):
        windows = monthly_invasion_windows(datetime(2026, 11, 5, 12, tzinfo=timezone.utc))
        self.assertEqual(
            [(row["event_key"], row["starts_at"], row["ends_at"]) for row in windows],
            [
                (
                    "invasao-sombria-mensal-202611",
                    datetime(2026, 11, 1, 3, tzinfo=timezone.utc),
                    datetime(2026, 11, 8, 3, tzinfo=timezone.utc),
                ),
                (
                    "invasao-sombria-mensal-202612",
                    datetime(2026, 12, 1, 3, tzinfo=timezone.utc),
                    datetime(2026, 12, 8, 3, tzinfo=timezone.utc),
                ),
            ],
        )

    def test_monthly_invasion_skips_elapsed_window_and_rolls_year(self):
        windows = monthly_invasion_windows(datetime(2026, 12, 20, tzinfo=timezone.utc))
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["event_key"], "invasao-sombria-mensal-202701")
        self.assertEqual(windows[0]["starts_at"], datetime(2027, 1, 1, 3, tzinfo=timezone.utc))
        self.assertEqual(windows[0]["ends_at"], datetime(2027, 1, 8, 3, tzinfo=timezone.utc))

    def test_default_invasion_has_five_progression_milestones(self):
        config = normalize_config({
            "title": "A Invasão Sombria",
            "starts_at": "2026-10-20T00:00:00Z",
            "ends_at": "2026-10-27T00:00:00Z",
        })
        self.assertEqual(config["tiers"], DEFAULT_TIERS)
        self.assertEqual(len(config["rewards"]), 5)
        for reward in config["rewards"]:
            for item in reward["items"]:
                self.assertIn(item["item_id"], ITEMS_DATA)

    def test_config_requires_timezone_and_existing_stackable_items(self):
        with self.assertRaises(EventError):
            normalize_config({"title": "Teste", "starts_at": "2026-10-20T00:00:00", "ends_at": "2026-10-27T00:00:00Z"})
        with self.assertRaises(EventError):
            normalize_config({
                "title": "Teste", "starts_at": "2026-10-20T00:00:00Z", "ends_at": "2026-10-27T00:00:00Z",
                "rewards": [{"gold": 1, "items": [{"item_id": "item_que_nao_existe", "quantity": 1}]}] * 5,
            })

    def test_database_naive_datetime_is_interpreted_as_utc_on_admin_edit(self):
        config = normalize_config({
            "title": "Teste", "starts_at": datetime(2026, 10, 20),
            "ends_at": datetime(2026, 10, 27),
        })
        self.assertEqual(config["starts_at"].tzinfo, timezone.utc)

    def test_corruption_modifiers_and_essence_chance_are_configurable(self):
        config = normalize_config({
            "title": "Invasão",
            "starts_at": "2026-10-20T00:00:00Z",
            "ends_at": "2026-10-27T00:00:00Z",
            "corruption": {
                "enabled": True,
                "chance": 20,
                "portal_enabled": False,
                "modifiers": {"hp": 1.3, "attack": 1.2, "defense": 1.1, "xp": 1.25},
                "essence_drop_chance": 12,
            },
        })
        self.assertEqual(config["corruption"]["modifiers"]["hp"], 1.3)
        self.assertFalse(config["corruption"]["portal_enabled"])
        self.assertEqual(config["corruption"]["essence_drop_chance"], 12)
        self.assertIn("essencia_sombria", ITEMS_DATA)

    def test_corruption_modifiers_reject_excessive_values(self):
        with self.assertRaises(EventError):
            normalize_config({
                "title": "Invasão",
                "starts_at": "2026-10-20T00:00:00Z",
                "ends_at": "2026-10-27T00:00:00Z",
                "corruption": {"enabled": True, "modifiers": {"hp": 4.1}},
            })

    def test_corrupted_defaults_double_combat_stats(self):
        config = normalize_config({
            "title": "Invasão",
            "starts_at": "2026-10-20T00:00:00Z",
            "ends_at": "2026-10-27T00:00:00Z",
            "corruption": {"enabled": True},
        })
        self.assertEqual(config["corruption"]["modifiers"]["hp"], 2.0)
        self.assertEqual(config["corruption"]["modifiers"]["attack"], 2.0)
        self.assertEqual(config["corruption"]["modifiers"]["defense"], 2.0)

    def test_manual_and_premium_points_share_the_same_daily_cap(self):
        awarded_today = 147
        awarded_today += points_after_daily_cap(5, awarded_today, 150)
        awarded_today += points_after_daily_cap(1, awarded_today, 150)
        self.assertEqual(awarded_today, 150)
        self.assertEqual(points_after_daily_cap(20, 150, 150), 0)

    def test_administrative_api_rejects_unauthenticated_users(self):
        from rotas.dynamic_events import dynamic_events_bp
        app = Flask(__name__)
        app.secret_key = "unit-test-secret"
        app.register_blueprint(dynamic_events_bp)
        response = app.test_client().get("/admin/api/eventos")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
