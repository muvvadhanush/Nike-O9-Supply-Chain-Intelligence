from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from . import orchestration
from schema.models import InitialState, ExecutionResult, RefineRequest
from agents.constants import APP_PORT
import os

app = FastAPI(title="Nike Supply Chain Control Tower API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for the UI
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CORE_DIR)
UI_DIR = os.path.join(_PROJECT_ROOT, "ui")
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@app.get("/")
async def get_index():
    """Returns the primary Nike POC dashboard."""
    html_file = "Nike POC with O9 Synthetic Data .html"
    return FileResponse(os.path.join(UI_DIR, html_file))


@app.get("/api/initial-state", response_model=InitialState)
async def get_initial_state():
    """
    Returns the starting Signals and Inventory Risk data.
    """
    data = orchestration.get_initial_state()
    return data

@app.post("/api/refine-recommendation")
async def refine_recommendation(request: RefineRequest):
    """
    Refines a recommendation based on a selected option.
    """
    result = orchestration.refine_recommendation(
        scenario_id=request.scenario_id,
        option_idx=request.option_idx,
        use_case=request.use_case
    )
    return result

@app.post("/api/run-pipeline", response_model=ExecutionResult)
async def run_pipeline(scenario_id: int = None):
    """
    Triggers the orchestration for a specific scenario and returns the result object.
    """
    result = orchestration.run_orchestration(scenario_id=scenario_id)
    return result

@app.post("/api/save-activity")
async def save_activity(request: dict):
    """
    Saves a scenario run to the persistent activity log.
    """
    activity_id = orchestration.save_activity(request)
    return {"status": "success", "id": activity_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=APP_PORT)
