from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

class Database:
    def __init__(self):
        self.db_path = Path('user_data/database.sqlite')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.timeout = 30.0
        self._init_db()

    def _get_connection(self):
        """Get database connection with proper settings"""
        conn = sqlite3.connect(str(self.db_path), timeout=self.timeout)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS simulations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    blocks INTEGER,
                    tao_supply REAL,
                    current_block INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS account_states (
                    simulation_id TEXT,
                    block INTEGER,
                    account_id INTEGER,
                    free_balance REAL,
                    market_value REAL,
                    alpha_stakes JSON,
                    FOREIGN KEY (simulation_id) REFERENCES simulations(id),
                    PRIMARY KEY (simulation_id, block, account_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subnet_states (
                    simulation_id TEXT,
                    block INTEGER,
                    subnet_id INTEGER,
                    tao_in REAL,
                    alpha_in REAL,
                    alpha_out REAL,
                    k REAL,
                    exchange_rate REAL,
                    emission_rate REAL,
                    dividends JSON,
                    FOREIGN KEY (simulation_id) REFERENCES simulations(id),
                    PRIMARY KEY (simulation_id, block, subnet_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS network_states (
                    simulation_id TEXT,
                    block INTEGER,
                    tao_supply REAL,
                    sum_prices REAL,
                    FOREIGN KEY (simulation_id) REFERENCES simulations(id),
                    PRIMARY KEY (simulation_id, block)
                )
            """)

    def create_simulation(self, name: str) -> str:
        simulation_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO simulations 
                (id, name, created_at, status)
                VALUES (?, ?, ?, ?)
                """,
                (simulation_id, name, datetime.utcnow(), 'created')
            )
        return simulation_id

    def update_simulation_status(self, simulation_id: str, status: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE simulations SET status = ? WHERE id = ?",
                (status, simulation_id)
            )

    def update_simulation_progress(self, simulation_id: str, current_block: int) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE simulations SET current_block = ? WHERE id = ?",
                (current_block + 1, simulation_id)
            )

    def update_simulation_config(self, simulation_id: str, blocks: int, tao_supply: float) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE simulations 
                SET blocks = ?, tao_supply = ? 
                WHERE id = ?
                """,
                (blocks, tao_supply, simulation_id)
            )

    def store_simulation_state(self, simulation_id: str, block: int, 
                             accounts: List[Dict], subnets: List[Dict], 
                             network: Dict) -> None:
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO account_states 
                (simulation_id, block, account_id, free_balance, 
                 market_value, alpha_stakes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [(
                    simulation_id,
                    block,
                    account['account_id'],
                    account['free_balance'],
                    account['market_value'],
                    json.dumps(account['alpha_stakes'])
                ) for account in accounts]
            )
            
            conn.executemany(
                """
                INSERT INTO subnet_states 
                (simulation_id, block, subnet_id, tao_in, alpha_in, 
                 alpha_out, k, exchange_rate, emission_rate, dividends)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(
                    simulation_id,
                    block,
                    subnet['subnet_id'],
                    subnet['tao_in'],
                    subnet['alpha_in'],
                    subnet['alpha_out'],
                    subnet['k'],
                    subnet['exchange_rate'],
                    subnet['emission_rate'],
                    json.dumps(subnet['dividends'])
                ) for subnet in subnets]
            )
            
            conn.execute(
                """
                INSERT INTO network_states 
                (simulation_id, block, tao_supply, sum_prices)
                VALUES (?, ?, ?, ?)
                """,
                (simulation_id, block, network['tao_supply'], network['sum_prices'])
            )

    def get_simulation_progress(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            sim = conn.execute(
                """
                SELECT id, status, blocks, current_block
                FROM simulations 
                WHERE id = ?
                """,
                (simulation_id,)
            ).fetchone()
            
            if not sim:
                return None
            
            current_block = min(sim['current_block'], sim['blocks']) if sim['blocks'] else 0
            total_blocks = sim['blocks'] if sim['blocks'] else 0
            
            return {
                'id': sim['id'],
                'status': sim['status'],
                'blocks': sim['blocks'],
                'current_block': current_block,
                'progress': f"{current_block}/{total_blocks}",
                'progress_percentage': (current_block / total_blocks * 100) if total_blocks else 0
            }

    def get_simulation(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            sim = conn.execute(
                "SELECT * FROM simulations WHERE id = ?",
                (simulation_id,)
            ).fetchone()
            
            if not sim:
                return None
            
            blocks_with_data = self._get_blocks_with_data(conn, simulation_id)
            
            blocks = {}
            for block in blocks_with_data:
                blocks[block['block']] = self._get_block_state(conn, simulation_id, block['block'])
            
            return {
                'id': sim['id'],
                'name': sim['name'],
                'created_at': sim['created_at'],
                'status': sim['status'],
                'blocks': blocks,
                'metadata': {
                    'total_blocks': sim['blocks'],
                    'logged_blocks': len(blocks),
                    'log_interval': sim['blocks'] // len(blocks) if blocks else None
                }
            }

    def _get_blocks_with_data(self, conn: sqlite3.Connection, 
                             simulation_id: str) -> List[sqlite3.Row]:
        return conn.execute("""
            SELECT DISTINCT block 
            FROM (
                SELECT block FROM account_states WHERE simulation_id = ?
                UNION
                SELECT block FROM subnet_states WHERE simulation_id = ?
                UNION
                SELECT block FROM network_states WHERE simulation_id = ?
            )
            ORDER BY block
        """, (simulation_id, simulation_id, simulation_id)).fetchall()

    def _get_block_state(self, conn: sqlite3.Connection, 
                        simulation_id: str, block: int) -> Dict[str, Any]:
        accounts = [
            {
                'account_id': state['account_id'],
                'free_balance': state['free_balance'],
                'market_value': state['market_value'],
                'alpha_stakes': json.loads(state['alpha_stakes'])
            }
            for state in conn.execute(
                "SELECT * FROM account_states WHERE simulation_id = ? AND block = ?",
                (simulation_id, block)
            ).fetchall()
        ]
        
        subnets = [
            {
                'subnet_id': state['subnet_id'],
                'tao_in': state['tao_in'],
                'alpha_in': state['alpha_in'],
                'alpha_out': state['alpha_out'],
                'k': state['k'],
                'exchange_rate': state['exchange_rate'],
                'emission_rate': state['emission_rate'],
                'dividends': json.loads(state['dividends'])
            }
            for state in conn.execute(
                "SELECT * FROM subnet_states WHERE simulation_id = ? AND block = ?",
                (simulation_id, block)
            ).fetchall()
        ]
        
        network = conn.execute(
            "SELECT * FROM network_states WHERE simulation_id = ? AND block = ?",
            (simulation_id, block)
        ).fetchone()
        
        return {
            'accounts': accounts,
            'subnets': subnets,
            'network': {
                'tao_supply': network['tao_supply'],
                'sum_prices': network['sum_prices']
            } if network else None
        }

    def get_simulations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of simulations with their complete data"""
        with self._get_connection() as conn:
            sims = conn.execute(
                "SELECT * FROM simulations ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            
            if not sims:
                return []
            
            results = []
            for sim in sims:
                blocks_with_data = self._get_blocks_with_data(conn, sim['id'])
                
                blocks = {}
                for block in blocks_with_data:
                    blocks[block['block']] = self._get_block_state(conn, sim['id'], block['block'])
                
                simulation = {
                    'id': sim['id'],
                    'name': sim['name'],
                    'created_at': sim['created_at'],
                    'status': sim['status'],
                    'blocks': blocks,
                    'metadata': {
                        'total_blocks': sim['blocks'],
                        'logged_blocks': len(blocks),
                        'log_interval': sim['blocks'] // len(blocks) if blocks else None
                    }
                }
                results.append(simulation)
            
            return results

    def get_simulations_without_blocks(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            sims = conn.execute(
                """
                SELECT id, name, created_at, status, blocks, current_block
                FROM simulations 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (limit,)
            ).fetchall()
            
            if not sims:
                return []
            
            return [{
                'id': sim['id'],
                'name': sim['name'],
                'created_at': sim['created_at'],
                'status': sim['status'],
                'metadata': {
                    'total_blocks': sim['blocks'],
                    'progression': f"{sim['current_block']}/{sim['blocks']}" if sim['blocks'] else "0/0",
                }
            } for sim in sims]
