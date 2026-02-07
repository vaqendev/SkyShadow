from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS so the frontend can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "SkyShadow API is online and ready."}

@app.post("/analyze")
def analyze_endpoint():
    # TODO: Connect to Engine.py
    return {"status": "pending", "message": "Earth Engine logic not implemented yet"}