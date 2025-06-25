from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.graph.GeoJsonification import graph_nodes_to_geojson
from backend.graph.graph import GrapheGTFS
from backend.graph.optimized_graph import OptimizedGraphGTFS
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/hello")
def read_root():
    return {"message": "Hello from FastAPI!"}


# Cache simple pour éviter de refaire les mêmes calculs trop souvent
# Format: {'lat_min,lat_max,lon_min,lon_max': {'timestamp': ..., 'data': ...}}
zone_cache = {}
MAX_CACHE_SIZE = 10  # Nombre maximum d'entrées dans le cache
CACHE_TTL = 60  # Durée de vie du cache en secondes

def clean_old_cache_entries():
    """Nettoie les entrées trop anciennes ou si le cache est trop grand"""
    global zone_cache
    now = time.time()
    
    # Supprimer les entrées trop anciennes
    keys_to_remove = [
        key for key, value in zone_cache.items() 
        if now - value['timestamp'] > CACHE_TTL
    ]
    
    for key in keys_to_remove:
        del zone_cache[key]
        
    # Si le cache est encore trop grand, supprimer les entrées les plus anciennes
    if len(zone_cache) > MAX_CACHE_SIZE:
        sorted_keys = sorted(
            zone_cache.keys(), 
            key=lambda k: zone_cache[k]['timestamp']
        )
        for key in sorted_keys[:len(zone_cache) - MAX_CACHE_SIZE]:
            del zone_cache[key]

@app.get("/geo/stops")
def get_stops_geojson():
    import time
    from typing import Optional
    from fastapi import Query
    
    start_time = time.time()
    
    try:
        print("Début du chargement des stations de métro...")
        g = GrapheGTFS("backend/graph/IDFM-gtfs_metro_pkl")  # double check this relative path!
        print(f"GrapheGTFS chargé en {time.time() - start_time:.2f} secondes")
        
        graph_start_time = time.time()
        graph = g.get_graph()
        print(f"get_graph() exécuté en {time.time() - graph_start_time:.2f} secondes")
        
        geojson_start_time = time.time()
        geojson_data = graph_nodes_to_geojson(graph)
        print(f"Conversion GeoJSON exécutée en {time.time() - geojson_start_time:.2f} secondes")
        
        total_time = time.time() - start_time
        print(f"Temps total de traitement: {total_time:.2f} secondes")
        
        # Ajouter des métadonnées au GeoJSON
        if isinstance(geojson_data, dict):
            geojson_data["metadata"] = {
                "processing_time": round(total_time, 2),
                "number_of_stations": len(geojson_data.get("features", []))
            }
        
        return JSONResponse(content=geojson_data)
    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        print("🔥 ERROR in /geo/stops:", error_message)
        raise HTTPException(status_code=500, detail=error_message)

@app.get("/geo/stops_by_zone")
def get_stops_by_zone(
    lat_min: float = Query(..., description="Latitude minimale de la zone"),
    lat_max: float = Query(..., description="Latitude maximale de la zone"),
    lon_min: float = Query(..., description="Longitude minimale de la zone"), 
    lon_max: float = Query(..., description="Longitude maximale de la zone")
):
    import time
    start_time = time.time()
    
    try:
        # Clé unique pour la zone actuelle
        zone_key = f"{lat_min},{lat_max},{lon_min},{lon_max}"
        
        # Vérifier si les données sont déjà dans le cache
        if zone_key in zone_cache:
            cached_data = zone_cache[zone_key]
            print(f"Utilisation des données en cache pour la zone: {zone_key}")
            
            # Vérifier si le cache est encore valide
            if time.time() - cached_data['timestamp'] <= CACHE_TTL:
                print("Données trouvées dans le cache, envoi des résultats...")
                return JSONResponse(content=cached_data['data'])
            else:
                print("Les données en cache sont périmées, recalcul en cours...")
        
        print(f"Chargement optimisé des stations dans la zone: [{lat_min},{lon_min}] - [{lat_max},{lon_max}]")
        
        # Utiliser la version optimisée qui filtre dès le départ
        g = OptimizedGraphGTFS("backend/graph/IDFM-gtfs_metro_pkl")
        
        # Charger seulement les stations dans la zone demandée
        graph_load_time = time.time()
        graph = g.load_graph_for_zone(lat_min, lat_max, lon_min, lon_max)
        print(f"Graphe optimisé chargé en {time.time() - graph_load_time:.2f} secondes")
        
        # Convertir en GeoJSON
        geojson_start_time = time.time()
        geojson_data = graph_nodes_to_geojson(graph)
        print(f"Conversion GeoJSON exécutée en {time.time() - geojson_start_time:.2f} secondes")
        
        total_time = time.time() - start_time
        print(f"Temps total de traitement optimisé: {total_time:.2f} secondes")
        
        # Ajouter des métadonnées au GeoJSON
        if isinstance(geojson_data, dict):
            geojson_data["metadata"] = {
                "processing_time": round(total_time, 2),
                "number_of_stations": len(geojson_data.get("features", [])),
                "zone": {
                    "lat_min": lat_min,
                    "lat_max": lat_max,
                    "lon_min": lon_min,
                    "lon_max": lon_max
                }
            }
        
        # Mettre en cache les résultats
        zone_cache[zone_key] = {
            "timestamp": time.time(),
            "data": geojson_data
        }
        
        # Nettoyer les anciennes entrées du cache si nécessaire
        clean_old_cache_entries()
        
        return JSONResponse(content=geojson_data)
    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        print("🔥 ERROR in /geo/stops_by_zone:", error_message)
        raise HTTPException(status_code=500, detail=error_message)
