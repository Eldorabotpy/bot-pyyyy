# modules/player/premium.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Type
from modules import game_data

class PremiumManager:
    """
    Gerencia status premium e vantagens para um jogador.
    - self.player_data é mutado in-place (quem chama deve salvar se necessário).
    - Trata 'premium_expires_at' == None como *permanente*.
    """

    def __init__(self, player_data: Dict[str, Any]):
        # Import local para evitar circularidade; esperamos que actions.utcnow exista.
        from .actions import utcnow  # deve retornar datetime (idealmente timezone-aware)

        self.player_data = player_data or {}
        self._now = utcnow()

    @property
    def tier(self) -> Optional[str]:
        """Retorna o tier (ex: 'gold') ou None."""
        tier = self.player_data.get("premium_tier")
        return tier if tier else None

    @property
    def expiration_date(self) -> Optional[datetime]:
        """Retorna datetime de expiração, ou None se permanente / não definido."""
        from .actions import _parse_iso  # função utilitária para parse ISO -> datetime

        iso_date = self.player_data.get("premium_expires_at")
        if not iso_date:
            return None
        dt = _parse_iso(iso_date)
        return dt

    def is_premium(self) -> bool:
        """Indica se jogador está em estado premium ativo (inclui permanente)."""
        tier = self.player_data.get("premium_tier")
        if not tier or tier == "free" or tier not in game_data.PREMIUM_TIERS:
            return False

        # Se expiration_date for None -> tratamos como permanente
        exp_date = self.expiration_date
        return exp_date is None or (exp_date > self._now)

    def get_remaining_days(self) -> int:
        """Dias restantes; 0 = não premium, 999 = permanente."""
        if not self.is_premium():
            return 0

        exp_date = self.expiration_date
        if exp_date is None:
            return 999
        remaining = exp_date - self._now
        # Se já passou, retorna 0
        return max(0, remaining.days + 1)

    def grant_days(self, tier: str, days: int, *, force: bool = False) -> None:
        """
        Concede ou atualiza premium por 'days' dias.
        """
        from .actions import get_player_max_energy

        tier = str(tier).lower()
        days = max(0, int(days))

        if tier == "free" or tier not in game_data.PREMIUM_TIERS or days <= 0:
            return

        self.player_data['premium_tier'] = tier

        # 1. Determinar a data base para adicionar os dias
        current_expiry = self.expiration_date 
        
        # Garante que base_date seja timezone-aware (UTC) para comparação segura
        base_date = self._now.replace(tzinfo=timezone.utc) if self._now.tzinfo is None else self._now

        if current_expiry is None:
            # Se for permanente (None), só muda se forçado
            if self.player_data.get('premium_expires_at') is None:
                if not force:
                    return # Já é permanente, não faz nada
                else:
                    # Força sobrescrever permanente -> começa de agora
                    start_date = base_date
            else:
                # Expiry é None mas não é permanente (ex: nunca teve premium)
                start_date = base_date
        else:
            # Se já tem data, garante UTC
            current_expiry = current_expiry.replace(tzinfo=timezone.utc) if current_expiry.tzinfo is None else current_expiry
            
            # Se a data atual ainda é válida (futuro), soma a partir dela
            if current_expiry > base_date:
                start_date = current_expiry
            else:
                # Se já venceu, começa de agora
                start_date = base_date

        # 2. Calcular nova data
        new_expiry = start_date + timedelta(days=days)
        self.player_data['premium_expires_at'] = new_expiry.isoformat()

        # Bônus: recarrega energia
        try:
            max_energy = get_player_max_energy(self.player_data)
            self.player_data["energy"] = max_energy
            self.player_data['energy_last_ts'] = base_date.isoformat()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Falha ao aplicar bônus de energia em grant_days")

    def revoke(self) -> None:
        """Revoga o premium (remove tier e expiração)."""
        # Preferimos remover as chaves em vez de setar None para evitar ambiguidade
        self.player_data.pop('premium_tier', None)
        self.player_data.pop('premium_expires_at', None)

    def get_perks(self) -> Dict[str, Any]:
        """
        Retorna merge de perks entre 'free' e o tier atual (tier tem prioridade).
        """
        base_perks = (game_data.PREMIUM_TIERS.get("free") or {}).get("perks", {}) or {}

        if not self.is_premium():
            return dict(base_perks)

        tier_name = self.tier
        tier_info = game_data.PREMIUM_TIERS.get(tier_name, {}) if tier_name else {}
        tier_perks = tier_info.get("perks", {}) or {}

        merged_perks = {**base_perks, **tier_perks}
        return merged_perks

    def get_perk_value(self, perk_name: str, default: Any = 1, cast: Type = None) -> Any:
        """
        Retorna o valor do perk; se cast fornecido (ex: float, int), tenta converter com fallback.
        Ex.: get_perk_value('xp_multiplier', 1.0, cast=float)
        """
        value = self.get_perks().get(perk_name, default)
        if cast:
            try:
                return cast(value)
            except Exception:
                try:
                    return cast(default)
                except Exception:
                    return default
        return value

    def set_tier(self, tier: str, *, permanent: bool = False) -> None:
        """
        Define/alterar o tier sem alterar a data de expiração por padrão.
        Se permanent=True, torna o premium permanente (premium_expires_at = None).
        """
        from .actions import get_player_max_energy

        tier = str(tier).lower()
        if tier == "free" or tier not in game_data.PREMIUM_TIERS:
            self.revoke()
            return

        self.player_data['premium_tier'] = tier

        if permanent:
            self.player_data['premium_expires_at'] = None

        # Recarrega energia como bônus
        try:
            max_energy = get_player_max_energy(self.player_data)
            self.player_data["energy"] = max_energy
            self.player_data['energy_last_ts'] = self._now.isoformat()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Falha ao aplicar bônus de energia em set_tier")
