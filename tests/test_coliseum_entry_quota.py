import copy
import threading
import unittest

from bson import ObjectId

from pvp.entry_quota import (
    DAILY_DATE_FIELD,
    DAILY_USED_FIELD,
    TICKETS_FIELD,
    consume_daily_entries,
    get_daily_entry_quota,
)


class _UpdateResult:
    def __init__(self, modified_count):
        self.modified_count = modified_count


class _MemoryUsers:
    def __init__(self, players):
        self.players = {player["_id"]: copy.deepcopy(player) for player in players}
        self.lock = threading.Lock()

    def find_one(self, query):
        with self.lock:
            player = self.players.get(query["_id"])
            return copy.deepcopy(player) if player else None

    def update_one(self, query, update):
        with self.lock:
            player = self.players.get(query["_id"])
            if not player:
                return _UpdateResult(0)
            for field, expected in query.items():
                if field == "_id":
                    continue
                present = field in player
                if isinstance(expected, dict):
                    if "$exists" in expected and present != expected["$exists"]:
                        return _UpdateResult(0)
                    if "$gt" in expected and (not present or player[field] <= expected["$gt"]):
                        return _UpdateResult(0)
                elif not present or player[field] != expected:
                    return _UpdateResult(0)
            before = copy.deepcopy(player)
            for field, value in update.get("$set", {}).items():
                player[field] = value
            for field in update.get("$unset", {}):
                player.pop(field, None)
            for field, amount in update.get("$inc", {}).items():
                player[field] = player.get(field, 0) + amount
            return _UpdateResult(int(player != before))


class ColiseumEntryQuotaTests(unittest.TestCase):
    def setUp(self):
        self.char_id = ObjectId()
        self.users = _MemoryUsers([{"_id": self.char_id, "gems": 50}])

    def test_ten_free_entries_then_denies_without_ticket(self):
        for _ in range(10):
            result = consume_daily_entries(self.users, [str(self.char_id)], today="2026-10-18")
            self.assertTrue(result["sucesso"])

        denied = consume_daily_entries(self.users, [str(self.char_id)], today="2026-10-18")
        quota = get_daily_entry_quota(self.users, str(self.char_id), today="2026-10-18")
        self.assertFalse(denied["sucesso"])
        self.assertEqual(quota["restantes"], 0)
        self.assertEqual(self.users.find_one({"_id": self.char_id})[DAILY_USED_FIELD], 10)

    def test_tickets_are_used_after_free_entries_and_quota_resets_next_day(self):
        self.users.players[self.char_id][TICKETS_FIELD] = 2
        for _ in range(10):
            self.assertTrue(consume_daily_entries(self.users, [str(self.char_id)], today="2026-10-18")["sucesso"])

        self.assertTrue(consume_daily_entries(self.users, [str(self.char_id)], today="2026-10-18")["sucesso"])
        after_ticket = get_daily_entry_quota(self.users, str(self.char_id), today="2026-10-18")
        self.assertEqual(after_ticket["tickets"], 1)
        self.assertEqual(after_ticket["usadas"], 11)

        next_day = get_daily_entry_quota(self.users, str(self.char_id), today="2026-10-19")
        self.assertEqual(next_day["restantes"], 10)
        self.assertEqual(next_day["tickets"], 1)

    def test_duel_preflight_does_not_charge_either_player_if_one_is_out(self):
        rival_id = ObjectId()
        self.users.players[rival_id] = {
            "_id": rival_id,
            DAILY_DATE_FIELD: "2026-10-18",
            DAILY_USED_FIELD: 10,
            TICKETS_FIELD: 0,
        }
        result = consume_daily_entries(
            self.users,
            [str(self.char_id), str(rival_id)],
            today="2026-10-18",
        )
        self.assertFalse(result["sucesso"])
        self.assertNotIn(DAILY_USED_FIELD, self.users.find_one({"_id": self.char_id}))

    def test_concurrent_requests_cannot_exceed_daily_limit(self):
        results = []
        result_lock = threading.Lock()

        def enter():
            result = consume_daily_entries(self.users, [str(self.char_id)], today="2026-10-18")
            with result_lock:
                results.append(result["sucesso"])

        threads = [threading.Thread(target=enter) for _ in range(24)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sum(results), 10)
        self.assertEqual(self.users.find_one({"_id": self.char_id})[DAILY_USED_FIELD], 10)


if __name__ == "__main__":
    unittest.main()
