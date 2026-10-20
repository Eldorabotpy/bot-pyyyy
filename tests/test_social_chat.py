import unittest

from modules.social_chat import (
    classificar_destino_mensagem,
    mensagem_global_nao_lida,
    sids_online_do_cla,
)


class SocialChatRoutingTests(unittest.TestCase):
    def test_plain_text_is_global(self):
        self.assertEqual(classificar_destino_mensagem("Olá reino"), ("global", "Olá reino"))

    def test_party_command_stays_in_group(self):
        self.assertEqual(classificar_destino_mensagem("/g vamos"), ("grupo", "vamos"))

    def test_clan_commands_stay_in_clan(self):
        for command in ("/c Olá", "/cla Olá", "/clã Olá", "/guilda Olá"):
            with self.subTest(command=command):
                self.assertEqual(classificar_destino_mensagem(command), ("cla", "Olá"))

    def test_unknown_slash_command_is_not_global(self):
        self.assertEqual(classificar_destino_mensagem("/outro teste"), ("comando_invalido", ""))

    def test_clan_delivery_targets_only_online_members(self):
        clan = {"membros": [{"user_id": "char-a"}, {"user_id": "char-b"}]}
        online = {
            "sid-a": {"char_id": "char-a"},
            "sid-b": {"char_id": "char-b"},
            "sid-c": {"char_id": "char-c"},
        }
        self.assertEqual(set(sids_online_do_cla(clan, online)), {"sid-a", "sid-b"})

    def test_global_message_after_read_cursor_is_unread(self):
        self.assertTrue(mensagem_global_nao_lida("66aa00000000000000000002", "66aa00000000000000000001"))

    def test_global_message_at_or_before_read_cursor_is_read(self):
        cursor = "66aa00000000000000000002"
        self.assertFalse(mensagem_global_nao_lida(cursor, cursor))
        self.assertFalse(mensagem_global_nao_lida("66aa00000000000000000001", cursor))


if __name__ == "__main__":
    unittest.main()
