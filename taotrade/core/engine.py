import importlib.util
import sys
from pathlib import Path
from typing import Type, cast
from taotrade.models.base.simulation import BaseSimulation
from taotrade.models.subtensor import Subtensor
from taotrade.core.database import Database

class SimulationEngine:
    def __init__(self):
        self.db = Database()

    def _load_simulation_class(self, simulation_name: str) -> Type[BaseSimulation]:
        """Load simulation class from file"""
        file_path = Path(f'user_data/simulations/{simulation_name}.py')
        if not file_path.exists():
            raise ValueError(f"Simulation {simulation_name} not found at {file_path}")

        spec = importlib.util.spec_from_file_location(simulation_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load simulation module: {simulation_name}")
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[simulation_name] = module
        spec.loader.exec_module(module)

        class_name = ''.join(word.capitalize() for word in simulation_name.split('_'))
        if not hasattr(module, class_name):
            raise ValueError(f"Simulation class {class_name} not found in {simulation_name}.py")
        
        simulation_class = getattr(module, class_name)
        if not issubclass(simulation_class, BaseSimulation):
            raise ValueError(f"Class {class_name} must inherit from BaseSimulation")
        
        return simulation_class

    def _update_progress(self, simulation_id: str, block: int, total_blocks: int, log_interval: int) -> None:
        """Update simulation progress based on log interval"""
        if block == 0 or block == total_blocks - 1 or block % log_interval == 0:
            self.db.update_simulation_progress(simulation_id, block)

    def _process_block(self, subtensor: Subtensor, block: int, simulation_id: str) -> None:
        """Process a single block in the simulation"""
        
        if block in subtensor.transaction_blocks:
            for tx in subtensor.transaction_blocks[block]:
                subtensor._execute_transaction(tx)

        if block != 0:
            subtensor._process_block_step()
        
        self._update_progress(simulation_id, block, subtensor.blocks, subtensor.log_interval)
        
        if block % subtensor.log_interval == 0 or block == subtensor.blocks - 1:
            state = subtensor.get_state(block)
            self.db.store_simulation_state(
                simulation_id,
                block,
                state['accounts'],
                state['subnets'],
                state['network']
            )

    def run_simulation(self, simulation_name: str, simulation_id: str = None) -> str:
        """Run a simulation"""
        if simulation_id is None:
            simulation_id = self.db.create_simulation(simulation_name)
        
        try:
            simulation = self._load_simulation_class(simulation_name)()
            simulation.id = simulation_id
            simulation.setup()
            simulation.validate_setup()
            
            subtensor = cast(Subtensor, simulation.subtensor)
            
            self.db.update_simulation_config(
                simulation_id,
                subtensor.blocks,
                subtensor.tao_supply
            )
            self.db.update_simulation_status(simulation_id, 'running')
            
            for block in range(subtensor.blocks):
                self._process_block(subtensor, block, simulation_id)

            self.db.update_simulation_progress(simulation_id, subtensor.blocks - 1)
            self.db.update_simulation_status(simulation_id, 'completed')
            return simulation_id
            
        except Exception as e:
            self.db.update_simulation_status(simulation_id, 'failed')
            raise e
