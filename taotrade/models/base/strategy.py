from typing import Any, Dict

class Strategy:
    def __init__(self):
        pass
    
    def generate_trades(self, chain_state: Dict[str, Any]):
        raise NotImplementedError
