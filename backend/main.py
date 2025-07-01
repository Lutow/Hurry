from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.graph.GeoJsonification import graph_nodes_to_geojson
from backend.graph.GeoJsonification_with_edges import (
    graph_to_geojson_with_edges,
    create_connection_test_geojson,
    find_connected_stations
)
from backend.idfm_line_reports_router import router as line_reports_router
from backend.graph.graph import GrapheGTFS
from backend.graph.optimized_graph import OptimizedGraphGTFS
from backend.graph.ultra_optimized_graph import UltraOptimizedGraphGTFS
from backend.graph.unique_edges_graph import UniqueEdgesMetroGraph
import time
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()
app.include_router(line_reports_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instance globale du graphe avec arêtes uniques (nouvelle version optimisée)
unique_graph = None
ultra_graph = None


def get_unique_graph():
    """Lazy loading du graphe avec arêtes uniques"""
    global unique_graph
    if unique_graph is None:
        logger.info("Initialisation du graphe avec arêtes uniques...")
        try:
            unique_graph = UniqueEdgesMetroGraph("backend/graph")
            unique_graph.build_graph()
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du graphe avec arêtes uniques: {e}")
            # Fallback vers la version ultra-optimisée si erreur
            unique_graph = None
    return unique_graph


def get_ultra_graph():
    """Lazy loading du graphe ultra-optimisé"""
    global ultra_graph
    if ultra_graph is None:
        logger.info("Initialisation du graphe ultra-optimise...")
        try:
            ultra_graph = UltraOptimizedGraphGTFS("backend/graph/IDFM-gtfs_metro_pkl")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du graphe ultra-optimise: {e}")
            # Fallback vers la version standard si erreur
            ultra_graph = OptimizedGraphGTFS("backend/graph/IDFM-gtfs_metro_pkl")
    return ultra_graph


@app.get("/api/hello")
def read_root():
    return {"message": "Hello from FastAPI ultra-optimisé pour le métro parisien!"}


@app.get("/geo/stations_only")
def get_stations_only():
    """
    Endpoint ultra-rapide pour obtenir toutes les stations sans les connexions.
    """
    start_time = time.time()

    try:
        logger.info("Récupération des stations uniquement...")

        g = get_ultra_graph()
        graph = g.build_stations_only_graph()

        geojson_data = graph_nodes_to_geojson(graph)

        total_time = time.time() - start_time
        logger.info(f"Stations chargées en {total_time:.2f} secondes")

        if isinstance(geojson_data, dict):
            geojson_data["metadata"] = {
                "processing_time": round(total_time, 2),
                "number_of_stations": len(geojson_data.get("features", [])),
                "type": "stations_only"
            }

        return JSONResponse(content=geojson_data)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/geo/graph_zone")
def get_graph_zone(
        lat_min: float = Query(..., description="Latitude minimale de la zone"),
        lat_max: float = Query(..., description="Latitude maximale de la zone"),
        lon_min: float = Query(..., description="Longitude minimale de la zone"),
        lon_max: float = Query(..., description="Longitude maximale de la zone")
):
    """
    Endpoint ultra-optimisé pour obtenir le graphe complet avec arêtes dans une zone.
    """
    start_time = time.time()

    try:
        logger.info(f"Construction du graphe complet pour zone: [{lat_min},{lat_max}] x [{lon_min},{lon_max}]")

        g = get_ultra_graph()

        # Utiliser la méthode SQL si disponible, sinon fallback
        if hasattr(g, 'build_graph_for_zone_sql'):
            graph = g.build_graph_for_zone_sql(lat_min, lat_max, lon_min, lon_max)
        else:
            graph = g.load_graph_for_zone(lat_min, lat_max, lon_min, lon_max)

        geojson_data = graph_nodes_to_geojson(graph)

        total_time = time.time() - start_time
        logger.info(f"Graphe complet construit en {total_time:.2f} secondes")

        if isinstance(geojson_data, dict):
            geojson_data["metadata"] = {
                "processing_time": round(total_time, 2),
                "number_of_stations": len(graph.nodes),
                "number_of_edges": len(graph.edges),
                "zone": {
                    "lat_min": lat_min,
                    "lat_max": lat_max,
                    "lon_min": lon_min,
                    "lon_max": lon_max
                },
                "type": "full_graph_with_edges"
            }

        return JSONResponse(content=geojson_data)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


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


@app.get("/api/stats")
def get_system_stats():
    """
    Obtient des statistiques détaillées sur le système de transport.
    """
    try:
        g = get_ultra_graph()

        if hasattr(g, 'get_statistics'):
            stats = g.get_statistics()
        else:
            # Fallback pour les versions non-ultra
            stats = {
                "total_stations": len(g.stops) if hasattr(g, 'stops') else 0,
                "total_routes": len(g.routes) if hasattr(g, 'routes') else 0,
                "total_transfers": len(g.transfers) if hasattr(g, 'transfers') else 0
            }

        return JSONResponse(content=stats)

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear_cache")
def clear_cache():
    """
    Supprime le cache/base de données pour forcer une reconstruction.
    """
    try:
        g = get_ultra_graph()

        if hasattr(g, 'clear_database'):
            g.clear_database()
            message = "Base de données supprimée avec succès"
        elif hasattr(g, 'clear_cache'):
            g.clear_cache()
            message = "Cache supprimé avec succès"
        else:
            message = "Aucun cache à supprimer"

        return {"message": message}

    except Exception as e:
        logger.error(f"Erreur lors de la suppression du cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ANCIENS ENDPOINTS (compatibilité)
@app.get("/geo/stops")
def get_stops_geojson():
    """Ancien endpoint - utilise maintenant la version ultra-optimisée"""
    return get_stations_only()


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
        print(f"Graphe optimise charge en {time.time() - graph_load_time:.2f} secondes")

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


@app.get("/geo/graph_with_edges")
def get_graph_with_edges(
        lat_min: float = Query(..., description="Latitude minimale de la zone"),
        lat_max: float = Query(..., description="Latitude maximale de la zone"),
        lon_min: float = Query(..., description="Longitude minimale de la zone"),
        lon_max: float = Query(..., description="Longitude maximale de la zone"),
        include_edges: bool = Query(True, description="Inclure les connexions (arêtes) dans le résultat")
):
    """
    Endpoint pour obtenir le graphe avec visualisation des connexions (arêtes colorées).
    """
    start_time = time.time()

    try:
        logger.info(f"Construction du graphe avec arêtes pour zone: [{lat_min},{lat_max}] x [{lon_min},{lon_max}]")

        g = get_ultra_graph()

        # Construire le graphe pour la zone
        if hasattr(g, 'build_graph_for_zone_sql'):
            graph = g.build_graph_for_zone_sql(lat_min, lat_max, lon_min, lon_max)
        else:
            graph = g.load_graph_for_zone(lat_min, lat_max, lon_min, lon_max)

        # Convertir en GeoJSON avec les arêtes
        geojson_data = graph_to_geojson_with_edges(graph, include_edges=include_edges)

        total_time = time.time() - start_time
        logger.info(f"Graphe avec arêtes construit en {total_time:.2f} secondes")

        # Ajouter des métadonnées
        if isinstance(geojson_data, dict):
            geojson_data.setdefault("metadata", {}).update({
                "processing_time": round(total_time, 2),
                "zone": {
                    "lat_min": lat_min,
                    "lat_max": lat_max,
                    "lon_min": lon_min,
                    "lon_max": lon_max
                },
                "include_edges": include_edges,
                "type": "graph_with_edges"
            })

        return JSONResponse(content=geojson_data)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/geo/test_connection")
def test_connection_between_stations(
        station1: str = Query(..., description="ID de la première station"),
        station2: str = Query(..., description="ID de la deuxième station")
):
    """
    Teste et visualise la connexion entre deux stations spécifiques.
    """
    start_time = time.time()

    try:
        logger.info(f"Test de connexion entre {station1} et {station2}")

        g = get_ultra_graph()

        # Construire un graphe large pour inclure les deux stations
        # (on prend toute la région parisienne pour être sûr)
        if hasattr(g, 'build_graph_for_zone_sql'):
            graph = g.build_graph_for_zone_sql(48.7, 49.0, 2.0, 2.7)
        else:
            # Fallback vers stations uniquement si pas de version SQL
            graph = g.build_stations_only_graph()

        # Créer le GeoJSON de test de connexion
        geojson_data = create_connection_test_geojson(graph, station1, station2)

        total_time = time.time() - start_time
        logger.info(f"Test de connexion terminé en {total_time:.2f} secondes")

        # Ajouter des métadonnées
        if isinstance(geojson_data, dict):
            geojson_data.setdefault("metadata", {}).update({
                "processing_time": round(total_time, 2),
                "type": "connection_test"
            })

        return JSONResponse(content=geojson_data)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/geo/station_connections/{station_id}")
def get_station_connections(
        station_id: str,
        max_connections: int = Query(20, description="Nombre maximum de connexions à afficher")
):
    """
    Affiche toutes les connexions directes d'une station donnée.
    """
    start_time = time.time()

    try:
        logger.info(f"Recherche des connexions pour la station {station_id}")

        g = get_ultra_graph()

        # Construire un graphe large
        if hasattr(g, 'build_graph_for_zone_sql'):
            graph = g.build_graph_for_zone_sql(48.7, 49.0, 2.0, 2.7)
        else:
            graph = g.build_stations_only_graph()

        # Trouver les stations connectées
        geojson_data = find_connected_stations(graph, station_id, max_connections)

        total_time = time.time() - start_time
        logger.info(f"Connexions trouvées en {total_time:.2f} secondes")

        # Ajouter des métadonnées
        if isinstance(geojson_data, dict):
            geojson_data.setdefault("metadata", {}).update({
                "processing_time": round(total_time, 2),
                "type": "station_connections"
            })

        return JSONResponse(content=geojson_data)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


# ========================
# NOUVEAUX ENDPOINTS POUR ARÊTES UNIQUES
# ========================

@app.get("/api/unique/edges")
def get_unique_edges():
    """
    Endpoint pour obtenir toutes les arêtes uniques du graphe.
    Chaque couple de stations consécutives n'a qu'une seule arête par ligne.
    """
    start_time = time.time()

    try:
        logger.info("Récupération des arêtes uniques...")

        g = get_unique_graph()
        if g is None:
            raise HTTPException(status_code=500, detail="Graphe avec arêtes uniques non disponible")

        # Obtenir toutes les arêtes pour GeoJSON
        edges = g.get_all_edges_for_geojson()

        # Construire le GeoJSON
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }

        for edge in edges:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [edge['from_coords'], edge['to_coords']]
                },
                "properties": {
                    "from_stop": edge['from_stop'],
                    "to_stop": edge['to_stop'],
                    "from_name": edge['from_name'],
                    "to_name": edge['to_name'],
                    "type": edge['type'],
                    "color": edge['color']
                }
            }

            # Ajouter les infos spécifiques selon le type
            if edge['type'] == 'direct':
                feature['properties'].update({
                    "route_id": edge['route_id'],
                    "route_short_name": edge['route_info'].get('short_name', 'N/A')
                })
            elif edge['type'] == 'transfer':
                feature['properties']['transfer_time'] = edge.get('transfer_time', 180)

            geojson_data['features'].append(feature)

        total_time = time.time() - start_time
        logger.info(f"Aretes uniques recuperees en {total_time:.2f} secondes")

        # Ajouter des métadonnées
        geojson_data["metadata"] = {
            "total_edges": len(edges),
            "direct_edges": len([e for e in edges if e['type'] == 'direct']),
            "transfer_edges": len([e for e in edges if e['type'] == 'transfer']),
            "processing_time": round(total_time, 2),
            "type": "unique_edges"
        }

        return JSONResponse(content=geojson_data)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/api/unique/station/{station_id}/connections")
def get_unique_station_connections(station_id: str):
    """
    Endpoint pour obtenir toutes les connexions uniques d'une station.
    """
    start_time = time.time()

    try:
        logger.info(f"Récupération des connexions uniques pour {station_id}")

        g = get_unique_graph()
        if g is None:
            raise HTTPException(status_code=500, detail="Graphe avec arêtes uniques non disponible")

        # Vérifier que la station existe
        if station_id not in g.stations:
            raise HTTPException(status_code=404, detail=f"Station {station_id} non trouvée")

        # Obtenir les connexions
        connections = g.get_station_connections(station_id)
        station_info = g.stations[station_id]

        result = {
            "station_id": station_id,
            "station_name": station_info['name'],
            "station_coords": [station_info['lon'], station_info['lat']],
            "connections": connections,
            "total_connections": len(connections),
            "direct_connections": len([c for c in connections if c['type'] == 'direct']),
            "transfer_connections": len([c for c in connections if c['type'] == 'transfer'])
        }

        total_time = time.time() - start_time
        logger.info(f"Connexions uniques recuperees en {total_time:.2f} secondes")

        result["metadata"] = {
            "processing_time": round(total_time, 2),
            "type": "unique_station_connections"
        }

        return JSONResponse(content=result)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/api/unique/connection")
def test_unique_connection(
        from_stop: str = Query(..., description="ID de la station de départ"),
        to_stop: str = Query(..., description="ID de la station d'arrivée")
):
    """
    Endpoint pour tester une connexion directe entre deux stations avec arêtes uniques.
    """
    start_time = time.time()

    try:
        logger.info(f"Test de connexion unique entre {from_stop} et {to_stop}")

        g = get_unique_graph()
        if g is None:
            raise HTTPException(status_code=500, detail="Graphe avec arêtes uniques non disponible")

        # Vérifier que les stations existent
        if from_stop not in g.stations:
            raise HTTPException(status_code=404, detail=f"Station de départ {from_stop} non trouvée")
        if to_stop not in g.stations:
            raise HTTPException(status_code=404, detail=f"Station d'arrivée {to_stop} non trouvée")

        # Trouver les connexions directes
        connections = g.find_direct_connection(from_stop, to_stop)

        result = {
            "from_stop": from_stop,
            "to_stop": to_stop,
            "from_name": g.stations[from_stop]['name'],
            "to_name": g.stations[to_stop]['name'],
            "has_direct_connection": len(connections) > 0,
            "connections": connections,
            "total_connections": len(connections)
        }

        total_time = time.time() - start_time
        logger.info(f"Test de connexion unique terminé en {total_time:.2f} secondes")

        result["metadata"] = {
            "processing_time": round(total_time, 2),
            "type": "unique_connection_test"
        }

        return JSONResponse(content=result)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/api/unique/stats")
def get_unique_graph_stats():
    """
    Endpoint pour obtenir les statistiques du graphe avec arêtes uniques.
    """
    start_time = time.time()

    try:
        logger.info("Récupération des statistiques du graphe avec arêtes uniques")

        g = get_unique_graph()
        if g is None:
            raise HTTPException(status_code=500, detail="Graphe avec arêtes uniques non disponible")

        # Analyser les arêtes par type
        direct_edges = [e for e in g.unique_edges.values()]
        route_counts = {}

        for edge in direct_edges:
            route_info = edge['route_info']
            route_name = route_info.get('short_name', 'Unknown')
            route_counts[route_name] = route_counts.get(route_name, 0) + 1

        result = {
            "total_stations": len(g.stations),
            "total_unique_edges": len(g.unique_edges),
            "total_transfers": len(g.transfers),
            "stations_with_transfers": len([s for s in g.transfers if g.transfers[s]]),
            "edges_by_route": route_counts,
            "total_routes": len(route_counts)
        }

        total_time = time.time() - start_time
        logger.info(f"Statistiques recuperees en {total_time:.2f} secondes")

        result["metadata"] = {
            "processing_time": round(total_time, 2),
            "type": "unique_graph_stats"
        }

        return JSONResponse(content=result)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/connectivity/check")
def check_network_connectivity():
    """
    Vérifie si le réseau de transport est connexe.
    Retourne un booléen indiquant si toutes les stations sont accessibles.
    """
    start_time = time.time()

    try:
        logger.info("🔍 Vérification de la connexité du réseau...")

        g = get_ultra_graph()
        is_connected = g.connected()

        total_time = time.time() - start_time

        result = {
            "is_connected": is_connected,
            "processing_time": round(total_time, 2),
            "message": "Le réseau est connexe" if is_connected else "Le réseau n'est pas connexe",
            "status": "success" if is_connected else "warning"
        }

        logger.info(f"✅ Vérification terminée en {total_time:.2f}s: {'Connexe' if is_connected else 'Non connexe'}")

        return JSONResponse(content=result)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur lors de la vérification de connexité après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/api/connectivity/details")
def get_connectivity_details():
    """
    Retourne des détails complets sur la connexité du réseau.
    Inclut le nombre de composantes connexes, les nœuds isolés, etc.
    """
    start_time = time.time()

    try:
        logger.info("📊 Analyse détaillée de la connexité...")

        g = get_ultra_graph()
        details = g.get_connectivity_details()

        total_time = time.time() - start_time
        details["processing_time"] = round(total_time, 2)

        logger.info(f"📊 Analyse terminée en {total_time:.2f}s")

        return JSONResponse(content=details)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur lors de l'analyse de connexité après {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/api/stats")
def get_network_stats():
    """
    Retourne des statistiques générales sur le réseau.
    """
    start_time = time.time()

    try:
        logger.info("📈 Récupération des statistiques du réseau...")

        g = get_ultra_graph()
        stats = g.get_statistics()

        total_time = time.time() - start_time
        stats["processing_time"] = round(total_time, 2)

        return JSONResponse(content=stats)

    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"Erreur lors de la recuperation des stats apres {total_time:.2f}s: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)
