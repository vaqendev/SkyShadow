from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool # Import this tool
import engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    geojson: Dict[str, Any]
    tree_increase: float = 0.0 

class GrowthRequest(BaseModel):
    geojson: Dict[str, Any]
    temp_drop: float = 0.0

@app.post("/analyze")
async def analyze_region(request: AnalysisRequest):
    # We wrap the blocking engine call in a threadpool
    result = await run_in_threadpool(
        engine.analyze_custom_region, 
        request.geojson, 
        request.tree_increase
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/simulate_growth")
async def simulate_growth(request: GrowthRequest):
    # Doing the same for the growth simulation
    # Note: I noticed generate_tree_locations wasn't in the engine.py file you uploaded, 
    # but assuming it exists in your local version:
    result = await run_in_threadpool(
        engine.generate_tree_locations, 
        request.geojson, 
        request.temp_drop
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result