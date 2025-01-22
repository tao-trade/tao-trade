from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from .subnet import Subnet
from .base.types import AccountConfig
from .base.strategy import Strategy

@dataclass
class Account:
    """
    Class representing a user account with balance and subnet stakes.

    Attributes:
        id (int): Unique identifier for the account
        free_balance (float): Available tao balance in the account
        registered_subnets (List[int]): List of subnet IDs the account is registered with
        alpha_stakes (Dict[int, float]): Mapping of subnet IDs to staked alpha amounts
    """
    id: int
    free_balance: float
    registered_subnets: List[int]
    alpha_stakes: Dict[int, float]
    strategy: Optional[Strategy] = None

    @classmethod
    def from_config(cls, config: AccountConfig, strategy: Optional[Strategy] = None):
        return cls(
            id=config.id,
            free_balance=config.free_balance,
            registered_subnets=config.registered_subnets,
            alpha_stakes=config.alpha_stakes,
            strategy=strategy
        )

    def calculate_market_value(self, subnets: Dict[int, 'Subnet']) -> float:
        """Calculate total market value of account including stakes"""
        return (
            self.free_balance +
            sum(
                self.alpha_stakes.get(subnet.id, 0.0) if subnet.is_root
                else (subnet.tao_in - (subnet.k / (subnet.alpha_in + 
                      self.alpha_stakes.get(subnet.id, 0.0))))
                for subnet in subnets.values()
                if self.alpha_stakes.get(subnet.id, 0.0) > 0
            )
        )

    def get_state(self, subnets: Dict[int, 'Subnet']) -> Dict[str, Any]:
        """Get account state including market value"""
        return {
            'account_id': self.id,
            'free_balance': self.free_balance,
            'market_value': self.calculate_market_value(subnets),
            'alpha_stakes': self.alpha_stakes.copy()
        }
