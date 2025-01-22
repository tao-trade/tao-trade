from rao.models.base.simulation import BaseSimulation
from rao.models.subtensor import Subtensor
from rao.models.subnet import Subnet
from rao.models.account import Account
from rao.models.transaction import Transaction
#from rao.models.base.strategy import Strategy


class FirstBlock(BaseSimulation):
    def __init__(self):
        super().__init__()
        self.name = "first_block"

    def setup(self):
        subnets = [
            Subnet(id=0, tao_in=0.0, alpha_in=0.0, alpha_out=0.0, is_root=True),
            Subnet(id=1, tao_in=1.0, alpha_in=1.0, alpha_out=0.0)
        ]

        accounts = [
            Account(
                id=1,
                free_balance=100.0,
                registered_subnets=[0, 1],
                alpha_stakes={},
                strategy=None
            ),
            Account(
                id=2,
                free_balance=100.0,
                registered_subnets=[1],
                alpha_stakes={},
                strategy=None
            ),
        ]

        transactions = [
            Transaction(
                block=1,
                account_id=1,
                subnet_id=0,
                action='stake',
                amount='100'
            ),
            Transaction(
                block=1,
                account_id=2,
                subnet_id=1,
                action='stake',
                amount='100'
            )
        ]

        self.subtensor = Subtensor(
            subnets=subnets,
            accounts=accounts,
            transactions=transactions,
            tao_supply=200,
            global_split=1.0,
            balanced=True,
            root_weight=0.5,
            blocks=7200,
            n_steps=7200
        )
