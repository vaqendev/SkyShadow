from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from engine import get_tile_url

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "SkyShadow Tile Server Online 🌍"}

@app.get("/map-layer")
def get_map_layer():
    try:
        url = get_tile_url()
        return {"tile_url": url}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}