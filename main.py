from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware
from engine import analyze_custom_region

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Define the Data Format (Expects a GeoJSON)
class AnalysisRequest(BaseModel):
    geojson: Dict[str, Any]

@app.get("/")
def home():
    return {"message": "SkyShadow Analysis Engine Online 🛰️"}

@app.post("/analyze")
def analyze_region(request: AnalysisRequest):
    """
    Receives a Polygon -> Returns Heatmap URL + Stats
    """
    result = analyze_custom_region(request.geojson)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result