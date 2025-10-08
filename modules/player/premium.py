# Em modules/player/premium.py
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from modules import game_data

class PremiumManager:
    """
    Gerencia o status premium, vantagens e expiração para um jogador.

    Esta classe atua como uma interface segura e centralizada para toda a
    lógica de assinatura, evitando a manipulação direta do dicionário
    `player_data` em outras partes do código.

    Uso:
        pdata = get_player_data(user_id)
        premium = PremiumManager(pdata)
        if premium.is_premium():
            dias_restantes = premium.get_remaining_days()
            print(f"Você tem {dias_restantes} dias de premium.")
        
        premium.grant_days(tier="gold", days=30)
        save_player_data(user_id, premium.player_data)
    """

    def __init__(self, player_data: Dict[str, Any]):
        """Inicializa o gerenciador com os dados de um jogador."""
        from .actions import utcnow # Importação local para evitar dependência circular
        
        self.player_data = player_data or {}
        self._now = utcnow()

    @property
    def tier(self) -> Optional[str]:
        """Retorna o tier premium atual (ex: 'gold') ou None se não for premium."""
        return self.player_data.get("premium_tier") if self.is_premium() else None

    @property
    def expiration_date(self) -> Optional[datetime]:
        """Retorna a data de expiração como um objeto datetime, ou None se não houver."""
        from .actions import _parse_iso
        
        iso_date = self.player_data.get("premium_expires_at")
        return _parse_iso(iso_date) if iso_date else None

    def is_premium(self) -> bool:
        """Verifica se o jogador tem um status premium ativo."""
        tier = self.player_data.get("premium_tier")
        if not tier or tier == "free" or tier not in game_data.PREMIUM_TIERS:
            return False

        # Se a data de expiração for 'None', consideramos como premium permanente.
        exp_date = self.expiration_date
        return exp_date is None or exp_date > self._now

    def get_remaining_days(self) -> int:
        """Calcula o número de dias restantes do plano premium."""
        if not self.is_premium():
            return 0
        
        exp_date = self.expiration_date
        if exp_date is None:
            return 999 # Um número alto para representar "permanente"
        
        remaining = exp_date - self._now
        return remaining.days + 1 # Adiciona 1 para incluir o dia atual

    def grant_days(self, tier: str, days: int) -> None:
        """
        Concede ou atualiza o status premium de um jogador, acumulando os dias.
        Também preenche a energia do jogador como bônus.
        """
        from .actions import get_player_max_energy
        
        tier = str(tier).lower()
        days = max(0, int(days))

        if tier == "free" or tier not in game_data.PREMIUM_TIERS or days <= 0:
            return # Não faz nada se o tier for inválido ou os dias forem zero

        self.player_data['premium_tier'] = tier
        
        # A sua lógica original de acumular dias, agora mais limpa
        base_date = self._now
        current_expiry = self.expiration_date
        
        if current_expiry and current_expiry > base_date:
            base_date = current_expiry
        
        new_expiry = base_date + timedelta(days=days)
        self.player_data['premium_expires_at'] = new_expiry.isoformat()

        # Bônus: Recarrega a energia ao receber premium
        max_energy = get_player_max_energy(self.player_data)
        self.player_data["energy"] = max_energy
        self.player_data['energy_last_ts'] = self._now.isoformat()

    def revoke(self) -> None:
        """Remove o status premium do jogador."""
        self.player_data['premium_tier'] = None
        self.player_data['premium_expires_at'] = None

    def get_perks(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com todas as vantagens (perks) do jogador,
        mesclando as vantagens base com as do seu tier.
        """
        # Define um dicionário base seguro para as vantagens
        base_perks = (game_data.PREMIUM_TIERS.get("free") or {}).get("perks", {})

        if not self.is_premium():
            return dict(base_perks)

        # Obtém as vantagens do tier do jogador
        tier_info = game_data.PREMIUM_TIERS.get(self.tier, {})
        tier_perks = tier_info.get("perks", {})

        # Mescla, onde as vantagens do tier têm prioridade
        merged_perks = {**base_perks, **tier_perks}
        return merged_perks

    def get_perk_value(self, perk_name: str, default: Any = 1) -> Any:
        """Obtém o valor de uma vantagem específica para o jogador."""
        return self.get_perks().get(perk_name, default)
    
    # Em modules/player/premium.py, dentro da classe PremiumManager

    def set_tier(self, tier: str) -> None:
        """
        Define ou altera o tier premium do jogador, sem alterar a data de expiração.
        Se o jogador não for premium, ele se torna premium permanente no novo tier.
        Também preenche a energia como bônus.
        """
        from .actions import get_player_max_energy

        tier = str(tier).lower()
        # Se o tier for "free" ou inválido, simplesmente revoga o premium
        if tier == "free" or tier not in game_data.PREMIUM_TIERS:
            self.revoke()
            return

        self.player_data['premium_tier'] = tier
        
        # Se o jogador não tinha uma data de expiração, ele se torna permanente no novo tier
        if self.player_data.get("premium_expires_at") is None:
            self.player_data['premium_expires_at'] = None

        # Bônus: Recarrega a energia
        max_energy = get_player_max_energy(self.player_data)
        self.player_data["energy"] = max_energy
        self.player_data['energy_last_ts'] = self._now.isoformat()