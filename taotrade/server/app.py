from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from strawberry.fastapi import GraphQLRouter
import strawberry
from typing import List, Dict, Any
from taotrade.core.database import Database
from taotrade.core.engine import SimulationEngine
from taotrade.server.graphql.types import Query, Mutation

class Server:
    def __init__(self, port: int = 8000):
        self.app = FastAPI(title="TaoTrade Server")
        self.port = port
        self.db = Database()
        self.engine = SimulationEngine()
        self._setup_routes()
        self._setup_graphql()

    def _setup_graphql(self):
        schema = strawberry.Schema(query=Query, mutation=Mutation)
        graphql_app = GraphQLRouter(
            schema,
            graphql_ide="apollo-sandbox",
            allow_queries_via_get=True
        )
        self.app.include_router(graphql_app, prefix="/graphql")

    def _get_root_response(self) -> Dict[str, Any]:
        return {
            'status': 'running',
            'mode': 'api-only',
            'endpoints': [
                {'path': '/api/simulate', 'method': 'POST'}
            ]
        }

    def _get_simulations(self) -> List[Dict[str, Any]]:
        return self.db.get_simulations_without_blocks()

    async def _create_simulation(self, request: Request) -> JSONResponse:
        data = await request.json()
        simulation_name = data.get('simulation')
        
        if not simulation_name:
            raise HTTPException(
                status_code=400,
                detail="No simulation name provided"
            )
        
        try:
            simulation_id = self.engine.run_simulation(simulation_name)
            return JSONResponse(
                status_code=200,
                content={
                    'status': 'success',
                    'simulation_id': simulation_id
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    def _get_simulation(self, simulation_id: str) -> JSONResponse:
        result = self.db.get_simulation(simulation_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Simulation not found"
            )
        
        return JSONResponse(
            status_code=200,
            content=result
        )

    def _setup_routes(self):
        self.app.get("/")(self._get_root_response)
        self.app.get("/api/simulations")(self._get_simulations)
        self.app.post("/api/simulations")(self._create_simulation)
        self.app.get("/api/simulations/{simulation_id}")(self._get_simulation)

    def run(self):
        import uvicorn
        print(f"Starting RAO server on port {self.port}")
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)
