from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class AccountConfig:
    id: int
    free_balance: float
    registered_subnets: List[int]
    alpha_stakes: Dict[int, float]
