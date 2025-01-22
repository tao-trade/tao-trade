from typing import Dict, Any, Optional, Union
from taotrade.models.subtensor import Subtensor

class BaseSimulation:
    def __init__(self):
        self.id: Optional[str] = None
        self.name: Optional[str] = None
        self.config: Dict[str, Any] = {}
        self.subtensor: Union[Subtensor, None] = None

    def setup(self) -> None:
        """Setup simulation parameters"""
        pass

    def validate_setup(self) -> None:
        """Validate that simulation is properly set up"""
        if not self.subtensor:
            raise ValueError("Subtensor not initialized. Did you call setup()?")

    @classmethod
    def get_template(cls) -> str:
        """Return template code for new simulation"""
        import textwrap
        
        return textwrap.dedent('''
            from rao.models.base.simulation import BaseSimulation
            from rao.models.subtensor import Subtensor
            from rao.models.subnet import Subnet
            from rao.models.account import Account
            from rao.models.transaction import Transaction
            from rao.models.base.strategy import Strategy


            class {class_name}(BaseSimulation):
                def __init__(self):
                    super().__init__()
                    self.name = "{name}"
                    
                def setup(self):
                    # Setup simulation parameters
                    subnets = [
                        Subnet(id=0, tao_in=1000, alpha_in=1000, alpha_out=0, is_root=True),
                        Subnet(id=1, tao_in=500, alpha_in=500, alpha_out=0)
                    ]
                    
                    accounts = [
                        Account(
                            id=0,
                            free_balance=1000,
                            registered_subnets=[0, 1],
                            alpha_stakes={{}},
                            strategy=None
                        )
                    ]
                    
                    transactions = [
                        Transaction(
                            block=1,
                            account_id=0,
                            subnet_id=1,
                            action='buy',
                            amount='100'
                        )
                    ]
                    
                    self.subtensor = Subtensor(
                        subnets=subnets,
                        accounts=accounts,
                        transactions=transactions,
                        tao_supply=10000,
                        global_split=0.5,
                        balanced=True,
                        root_weight=1.0,
                        blocks=100,
                        n_steps=10
                    )
            ''').strip()
