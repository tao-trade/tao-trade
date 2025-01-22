import click
from taotrade.server import Server
from pathlib import Path

@click.group()
def cli():
    """TaoTrade CLI"""
    pass

@cli.group()
def run():
    """Run commands"""
    pass

@run.command()
@click.option('--port', default=8000, help='Port to run the server on')
def server(port: int):
    """Start the server"""
    server = Server(port=port)
    server.run()

@cli.command()
@click.argument('simulation_name')
def simulate(simulation_name):
    """Run a simulation"""
    from taotrade.core.engine import SimulationEngine
    import sys
    import time
    import threading
    
    engine = SimulationEngine()
    simulation_id = None
    simulation_complete = threading.Event()
    
    try:
        simulation_id = engine.db.create_simulation(simulation_name)
        click.echo(f"\nStarting simulation: {simulation_id}")
        
        def monitor_progress():
            last_progress = None
            final_update_received = False
            
            while not simulation_complete.is_set() or not final_update_received:
                sim = engine.db.get_simulation_progress(simulation_id)
                if not sim:
                    break
                
                if sim['status'] == 'completed':
                    progress = f"Progress: {sim['blocks']}/{sim['blocks']} (100.0%) ✅"
                    final_update_received = True
                else:
                    progress = f"Progress: {sim['progress']} ({sim['progress_percentage']:.1f}%)"
                    if sim['status'] == 'running':
                        progress += " ⏳"
                    elif sim['status'] == 'interrupted':
                        progress += " ⏹️"
                    elif sim['status'] == 'failed':
                        progress += " ❌"
                
                if progress != last_progress:
                    sys.stdout.write('\r' + ' ' * 80)
                    sys.stdout.write('\r' + progress)
                    sys.stdout.flush()
                    last_progress = progress
                
                if sim['status'] in ['interrupted', 'failed']:
                    final_update_received = True
                
                time.sleep(0.1)
        
        progress_thread = threading.Thread(target=monitor_progress)
        progress_thread.daemon = True
        progress_thread.start()
        
        engine.run_simulation(simulation_name, simulation_id)
        
        simulation_complete.set()
        progress_thread.join(timeout=1.0)
        
        sys.stdout.write('\n')
        
    except KeyboardInterrupt:
        if simulation_id:
            engine.db.update_simulation_status(simulation_id, 'interrupted')
            simulation_complete.set()
        click.echo("\nSimulation interrupted")
    except Exception as e:
        if simulation_id:
            engine.db.update_simulation_status(simulation_id, 'failed')
            simulation_complete.set()
        click.echo(f"\nSimulation failed: {str(e)}")

@cli.command()
@click.argument('plot_spec')
@click.option('--id', required=True, help='Simulation ID')
def plot(plot_spec, id):
    """Generate a plot"""
    from taotrade.models.base.plot import BasePlot
    plot = BasePlot.create(plot_spec, id)
    plot.generate()

@cli.group()
def create():
    """Create new components"""
    pass

@create.command()
@click.argument('name')
def simulation(name):
    """Create a new simulation"""
    from taotrade.models.base.simulation import BaseSimulation
    
    file_path = Path('user_data/simulations') / f"{name}.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    class_name = ''.join(word.capitalize() for word in name.split('_'))
    
    template = BaseSimulation.get_template().format(
        class_name=class_name,
        name=name
    )
    
    with open(file_path, 'w') as f:
        f.write(template.strip())
    click.echo(f"Created new simulation: {file_path}")

@create.command()
@click.argument('name')
def plot(name):
    """Create a new plot"""
    from taotrade.models.base.plot import BasePlot
    
    file_path = Path('user_data/plots') / f"{name}.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    class_name = ''.join(word.capitalize() for word in name.split('_'))
    template = BasePlot.get_template().format(
        class_name=class_name
    )
    
    with open(file_path, 'w') as f:
        f.write(template)
    
    click.echo(f"Created new plot: {file_path}")

@cli.group()
def list():
    """List available components"""
    pass

@list.command()
def simulations():
    """List available simulations"""
    sim_path = Path('user_data/simulations')
    if sim_path.exists():
        files = [f.stem for f in sim_path.glob('*.py')]
        click.echo("\nAvailable simulations:")
        for f in files:
            click.echo(f"  - {f}")
    else:
        click.echo("No simulations found")

@list.command()
def plots():
    """List available plots"""
    plot_path = Path('user_data/plots')
    if plot_path.exists():
        files = [f.stem for f in plot_path.glob('*.py')]
        click.echo("\nAvailable plots:")
        for f in files:
            click.echo(f"  - {f}")
    else:
        click.echo("No plots found")

def main():
    cli()

if __name__ == "__main__":
    main()
