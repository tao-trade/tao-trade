from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Subnet:
    """
    Class representing a subnet in the network.

    Attributes:
        id (int): Unique identifier for the subnet
        tao_in (float): Amount of tao in the subnet pool
        alpha_in (float): Amount of alpha in the subnet pool
        alpha_out (float): Amount of alpha outstanding (staked)
        is_root (bool): Flag indicating if this is a root subnet
        k (float): Constant product k = tao_in * alpha_in
    """
    id: int
    tao_in: float
    alpha_in: float
    alpha_out: float
    is_root: bool = False
    k: float = field(init=False)

    def __post_init__(self):
        """
        Post-initialization processing to calculate the constant product k.
        
        For non-root subnets:
            k = tao_in * alpha_in
        For root subnets:
            k = 0
        """
        self.k = self.tao_in * self.alpha_in if not self.is_root else 0.0

    def alpha_price(self) -> float:
        """
        Calculate the price of alpha in terms of tao.

        Formula:
            Root subnet: 1.0
            Non-root subnet: tao_in / alpha_in or 1.0 if alpha_in = 0

        Returns:
            float: Alpha price in tao
        """
        return 1.0 if self.is_root or self.alpha_in == 0 else self.tao_in / self.alpha_in

    def weight(self, alpha_amount: float) -> float:
        """
        Calculate voting weight for an alpha stake.

        Formula:
            Root subnet: alpha_amount
            Non-root subnet: (alpha_amount / alpha_out) * tao_in
                Returns 0 if alpha_out = 0

        Args:
            alpha_amount: Alpha to calculate weight for

        Returns:
            float: Voting weight
        """
        return alpha_amount if self.is_root else (
            0.0 if self.alpha_out == 0 else (alpha_amount / self.alpha_out) * self.tao_in
        )

    def stake(self, tao_amount: float) -> float:
        """
        Convert tao to alpha via staking.

        Formula:
            Root subnet:
                alpha_received = tao_amount
            Non-root subnet (constant product k = tao_in * alpha_in):
                alpha_received = alpha_in - k/(tao_in + tao_amount)

        Args:
            tao_amount: Tao to stake

        Returns:
            float: Alpha received
        """
        if self.is_root:
            self.alpha_out += tao_amount
            return tao_amount
        new_tao_in = self.tao_in + tao_amount
        new_alpha_in = self.k / new_tao_in
        alpha_bought = self.alpha_in - new_alpha_in
        self.alpha_out += alpha_bought
        self.alpha_in = new_alpha_in
        self.tao_in = new_tao_in
        return alpha_bought

    def unstake(self, alpha_amount: float) -> float:
        """
        Convert alpha back to tao via unstaking.

        Formula:
            Root subnet:
                tao_received = alpha_amount
            Non-root subnet (constant product k = tao_in * alpha_in):
                tao_received = tao_in - k/(alpha_in + alpha_amount)

        Args:
            alpha_amount: Alpha to unstake

        Returns:
            float: Tao received
        """
        if self.is_root:
            self.alpha_out -= alpha_amount
            return alpha_amount
        new_alpha_in = self.alpha_in + alpha_amount
        new_tao_in = self.k / new_alpha_in
        tao_bought = self.tao_in - new_tao_in
        self.alpha_out -= alpha_amount
        self.alpha_in = new_alpha_in
        self.tao_in = new_tao_in
        return tao_bought

    def inject(self, tao_amount: float, alpha_amount: float, alpha_out: float):
        """
        Inject tokens into subnet pools and recalculate constant product.

        Updates:
            tao_in += tao_amount
            alpha_in += alpha_amount
            alpha_out += alpha_out
            k = tao_in * alpha_in

        Args:
            tao_amount: Tao to add to pool
            alpha_amount: Alpha to add to pool
            alpha_out: Alpha to add to outstanding
        """
        self.tao_in += tao_amount
        self.alpha_in += alpha_amount
        self.alpha_out += alpha_out
        self.k = self.tao_in * self.alpha_in

    def get_state(self, emissions: Dict[int, float], dividends: Dict[int, float]) -> Dict[str, Any]:
        """Get subnet state"""
        return {
            'subnet_id': self.id,
            'tao_in': self.tao_in,
            'alpha_in': self.alpha_in,
            'alpha_out': self.alpha_out,
            'k': self.k,
            'exchange_rate': self.alpha_price(),
            'emission_rate': emissions.get(self.id, 0.0),
            'dividends': dividends if not self.is_root else {}
        }
