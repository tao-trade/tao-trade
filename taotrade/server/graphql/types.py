from typing import List, Optional, Dict, Any
import strawberry
from datetime import datetime
from taotrade.core.database import Database
from taotrade.core.engine import SimulationEngine

@strawberry.type
class SimulationAttributes:
    name: str
    created_at: str = strawberry.field(name="createdAt")
    status: str
    current_block: Optional[int]
    progress: Optional[str]
    progress_percentage: Optional[float]
    blocks: 'BlocksConnection'
    metadata: 'SimulationMetadata'

@strawberry.type
class SimulationData:
    id: str
    attributes: SimulationAttributes

@strawberry.type
class Simulation:
    data: SimulationData

@strawberry.type
class SimulationResult:
    status: str
    id: Optional[str]
    message: Optional[str]

def convert_to_simulation(data: Dict[str, Any]) -> Simulation:
    blocks_data = data.get('blocks', {})
    blocks = convert_to_blocks_connection(blocks_data)
    metadata = convert_to_simulation_metadata(data.get('metadata', {}))
    
    attributes = SimulationAttributes(
        name=str(data.get('name', '')),
        created_at=str(data.get('created_at', datetime.now().isoformat())),
        status=str(data.get('status', '')),
        current_block=data.get('current_block'),
        progress=data.get('progress'),
        progress_percentage=data.get('progress_percentage'),
        blocks=blocks,
        metadata=metadata
    )
    
    simulation_data = SimulationData(
        id=str(data.get('id', '')),
        attributes=attributes
    )
    
    return Simulation(data=simulation_data)

def convert_to_simulation_metadata(data: Dict[str, Any]) -> 'SimulationMetadata':
    return SimulationMetadata(
        total_blocks=int(data.get('total_blocks', 0)),
        logged_blocks=int(data.get('logged_blocks', 0)),
        log_interval=data.get('log_interval')
    )

def convert_to_blocks_connection(data: Dict[str, Any]) -> 'BlocksConnection':
    blocks = []
    for block_num, block_data in sorted(data.items(), key=lambda x: int(x[0])):
        blocks.append(convert_to_block(int(block_num), block_data))
    
    return BlocksConnection(
        data=blocks,
        page_info=PageInfo(
            has_next_page=bool(blocks),
            has_previous_page=bool(blocks),
            start_block=int(blocks[0].id if blocks else 0),
            end_block=int(blocks[-1].id if blocks else 0),
            total_blocks=len(blocks)
        )
    )

def convert_to_block(block_num: int, data: Dict[str, Any]) -> 'Block':
    return Block(
        id=block_num,
        accounts=convert_to_accounts_connection(data.get('accounts', [])),
        subnets=convert_to_subnets_connection(data.get('subnets', [])),
        network=convert_to_network_state(data.get('network', {}))
    )

def convert_to_network_state(data: Dict[str, Any]) -> 'NetworkState':
    return NetworkState(
        tao_supply=float(data.get('tao_supply', 0.0)),
        sum_prices=float(data.get('sum_prices', 0.0))
    )

def convert_to_accounts_connection(data: List[Dict[str, Any]]) -> 'AccountsConnection':
    return AccountsConnection(
        data=[convert_to_account(acc) for acc in data]
    )

def convert_to_account(data: Dict[str, Any]) -> 'Account':
    return Account(
        id=int(data.get('account_id', 0)),
        free_balance=float(data.get('free_balance', 0.0)),
        market_value=float(data.get('market_value', 0.0)),
        alpha_stakes=convert_to_alpha_stakes_connection(data.get('alpha_stakes', {}))
    )

def convert_to_alpha_stakes_connection(data: Dict[str, Any]) -> 'AlphaStakesConnection':
    stakes = [
        AlphaStake(netuid=int(netuid), amount=float(amount))
        for netuid, amount in data.items()
    ]
    return AlphaStakesConnection(data=stakes)

def convert_to_subnets_connection(data: List[Dict[str, Any]]) -> 'SubnetsConnection':
    return SubnetsConnection(
        data=[convert_to_subnet(subnet) for subnet in data]
    )

def convert_to_subnet(data: Dict[str, Any]) -> 'Subnet':
    return Subnet(
        netuid=int(data.get('subnet_id', 0)),
        tao_in=float(data.get('tao_in', 0.0)),
        alpha_in=float(data.get('alpha_in', 0.0)),
        alpha_out=float(data.get('alpha_out', 0.0)),
        k=float(data.get('k', 0.0)),
        exchange_rate=float(data.get('exchange_rate', 0.0)),
        emission_rate=float(data.get('emission_rate', 0.0)),
        dividends=convert_to_dividends_connection(data.get('dividends', {}))
    )

def convert_to_dividends_connection(data: Dict[str, Any]) -> 'DividendsConnection':
    dividends = [
        Dividend(id=int(id), amount=float(amount))
        for id, amount in data.items()
    ]
    return DividendsConnection(data=dividends)

@strawberry.type
class AlphaStake:
    netuid: int
    amount: float

@strawberry.type
class AlphaStakesConnection:
    data: List[AlphaStake]

@strawberry.type
class Dividend:
    id: int
    amount: float

@strawberry.type
class DividendsConnection:
    data: List[Dividend]

@strawberry.type
class NetworkState:
    tao_supply: float
    sum_prices: float

@strawberry.type
class Account:
    id: int
    free_balance: float
    market_value: float
    alpha_stakes: AlphaStakesConnection

@strawberry.type
class AccountsConnection:
    data: List[Account]

@strawberry.type
class Subnet:
    netuid: int
    tao_in: float
    alpha_in: float
    alpha_out: float
    k: float
    exchange_rate: float
    emission_rate: float
    dividends: DividendsConnection

@strawberry.type
class SubnetsConnection:
    data: List[Subnet]

@strawberry.type
class Block:
    id: int
    accounts: AccountsConnection
    subnets: SubnetsConnection
    network: NetworkState

@strawberry.type
class PageInfo:
    has_next_page: bool
    has_previous_page: bool
    start_block: int
    end_block: int
    total_blocks: int

@strawberry.type
class BlocksConnection:
    data: List[Block]
    page_info: PageInfo

@strawberry.type
class SimulationMetadata:
    total_blocks: int
    logged_blocks: int
    log_interval: Optional[int]

@strawberry.type
class Query:
    @strawberry.field
    def simulations(self) -> List[Simulation]:
        db = Database()
        simulations_data = db.get_simulations()
        return [convert_to_simulation(sim) for sim in simulations_data]

    @strawberry.field
    def simulation(self, id: str) -> Optional[Simulation]:
        db = Database()
        simulation_data = db.get_simulation(id)
        if simulation_data:
            return convert_to_simulation(simulation_data)
        return None


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_simulation(self, name: str) -> SimulationResult:
        try:
            engine = SimulationEngine()
            simulation_id = engine.run_simulation(name)
            return SimulationResult(
                status="success",
                id=simulation_id,
                message=None
            )
        except Exception as e:
            return SimulationResult(
                status="error",
                id=None,
                message=str(e)
            )
