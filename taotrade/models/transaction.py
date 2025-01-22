from dataclasses import dataclass


@dataclass
class Transaction:
    """
    Class representing a transaction in the simulation.

    Attributes:
        block (int): Block number when the transaction occurred
        account_id (int): ID of the account executing the transcation
        subnet_id (int): ID of the subnet where transaction occurred
        action (str): Type of transaction action performed (stake/unstake)
        amount (str): Amount of tokens involved in the transaction
    """
    block: int
    account_id: int
    subnet_id: int
    action: str
    amount: str
