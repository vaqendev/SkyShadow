from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    geojson: Dict[str, Any]
    tree_increase: float = 0.0 
    hotspot_count: int = 5

class GrowthRequest(BaseModel):
    geojson: Dict[str, Any]
    temp_drop: float = 0.0

@app.post("/analyze")
async def analyze_region(request: AnalysisRequest):
    result = await run_in_threadpool(
        engine.analyze_custom_region, 
        request.geojson, 
        request.tree_increase,
        request.hotspot_count
    )
    
    # Graceful Error Handling (Prevents 500 Crash)
    if "error" in result:
        return {
            "status": "error", 
            "message": result["error"]
        }
    return result

@app.post("/simulate_growth")
async def simulate_growth(request: GrowthRequest):
    result = await run_in_threadpool(
        engine.generate_tree_locations, 
        request.geojson, 
        request.temp_drop
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result