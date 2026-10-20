"""Routing helpers for the in-game social chat channels."""


def classificar_destino_mensagem(texto):
    """Return the private channel and body for a chat input.

    Ordinary text is global. Slash-prefixed commands that are not recognized
    are rejected instead of accidentally falling through into the global chat.
    Private whispers are parsed separately by the existing handler.
    """
    texto = str(texto or "").strip()
    texto_lower = texto.lower()

    if texto_lower.startswith("/g "):
        return "grupo", texto[3:].strip()

    for prefixo in ("/c ", "/cla ", "/clã ", "/guilda "):
        if texto_lower.startswith(prefixo):
            return "cla", texto[len(prefixo):].strip()

    if texto.startswith("/"):
        return "comando_invalido", ""

    return "global", texto


def sids_online_do_cla(cla, jogadores_online):
    """List only online sockets whose character is a member of this clan."""
    membros = {
        str(membro.get("user_id"))
        for membro in (cla or {}).get("membros", [])
        if isinstance(membro, dict) and membro.get("user_id") is not None
    }
    return [
        sid
        for sid, info in (jogadores_online or {}).items()
        if str((info or {}).get("char_id")) in membros
    ]


def mensagem_global_nao_lida(id_mensagem, ultimo_id_lido):
    """Compare Mongo ObjectId values represented as ObjectIds or hex strings."""
    if id_mensagem is None or ultimo_id_lido is None:
        return False
    return str(id_mensagem) > str(ultimo_id_lido)
