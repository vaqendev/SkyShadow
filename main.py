from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from engine import analyze_custom_region

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Added 'tree_increase' field
class AnalysisRequest(BaseModel):
    geojson: Dict[str, Any]
    tree_increase: float = 0.0  # Default 0.0 (No simulation)

@app.post("/analyze")
def analyze_region(request: AnalysisRequest):
    """
    Receives Polygon + Tree Slider Value -> Returns Simulated Heatmap
    """
    result = analyze_custom_region(request.geojson, request.tree_increase)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result