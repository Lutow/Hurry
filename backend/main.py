from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.graph.GeoJsonification import graph_nodes_to_geojson
from backend.graph.graph import GrapheGTFS
from fastapi import HTTPException

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/hello")
def read_root():
    return {"message": "Hello from FastAPI!"}


@app.get("/geo/stops")
def get_stops_geojson():
    try:
        g = GrapheGTFS("backend/graph/IDFM-gtfs_metro_pkl")  # double check this relative path!
        geojson_data = graph_nodes_to_geojson(g.get_graph())
        return JSONResponse(content=geojson_data)
    except Exception as e:
        print("🔥 ERROR in /geo/stops:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
