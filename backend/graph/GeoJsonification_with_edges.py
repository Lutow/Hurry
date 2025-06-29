import pandas as pd
import networkx as nx
from typing import Dict, List, Tuple, Optional
import json

def graph_to_geojson_with_edges(graph: nx.DiGraph, include_edges: bool = True) -> Dict:
    """
    Convertit un graphe NetworkX en GeoJSON avec les stations et optionnellement les connexions.
    
    Args:
        graph: Graphe NetworkX avec les stations et leurs connexions
        include_edges: Si True, inclut les arêtes comme LineString dans le GeoJSON
        
    Returns:
        Dict: GeoJSON avec stations (points) et connexions (lignes)
    """
    
    features = []
    
    # Ajouter les stations comme points
    for node_id, node_data in graph.nodes(data=True):
        # Vérifier que les coordonnées existent
        lat = node_data.get('lat') or node_data.get('stop_lat')
        lon = node_data.get('lon') or node_data.get('stop_lon')
        
        if lat is None or lon is None:
            continue
            
        # Créer le feature pour la station
        station_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lon), float(lat)]
            },
            "properties": {
                "type": "station",
                "stop_id": node_id,
                "stop_name": node_data.get('stop_name', 'Station inconnue'),
                "accessibility": node_data.get('accessibility', 0),
                "wheelchair_boarding": node_data.get('wheelchair_boarding', 0)
            }
        }
        features.append(station_feature)
    
    # Ajouter les connexions comme lignes si demandé
    if include_edges and len(graph.edges) > 0:
        
        # Compter les types de connexions
        metro_edges = 0
        transfer_edges = 0
        
        for from_node, to_node, edge_data in graph.edges(data=True):
            # Obtenir les coordonnées des stations
            from_coords = _get_node_coordinates(graph, from_node)
            to_coords = _get_node_coordinates(graph, to_node)
            
            if not from_coords or not to_coords:
                continue
            
            # Déterminer le type de connexion et la couleur
            if edge_data.get('transfer_type') == 'correspondence':
                connection_type = "correspondance"
                color = "#FF6B6B"  # Rouge pour les correspondances
                weight = 3
                transfer_edges += 1
            else:
                connection_type = "metro"
                # Couleur selon la ligne de métro si disponible
                route_name = edge_data.get('route_name', '')
                color = _get_metro_line_color(route_name)
                weight = 2
                metro_edges += 1
            
            # Créer le feature pour la connexion
            connection_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [from_coords, to_coords]
                },
                "properties": {
                    "type": "connection",
                    "connection_type": connection_type,
                    "from_stop": from_node,
                    "to_stop": to_node,
                    "travel_time": edge_data.get('weight', 0),
                    "route_name": edge_data.get('route_name', ''),
                    "route_id": edge_data.get('route_id', ''),
                    "color": color,
                    "weight": weight
                }
            }
            features.append(connection_feature)
        
        print(f"📊 Connexions ajoutées au GeoJSON:")
        print(f"  🚇 Arêtes de métro: {metro_edges}")
        print(f"  🔄 Correspondances: {transfer_edges}")
        print(f"  📍 Total connexions: {metro_edges + transfer_edges}")
    
    # Créer le GeoJSON final
    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_stations": len([f for f in features if f["properties"]["type"] == "station"]),
            "total_connections": len([f for f in features if f["properties"]["type"] == "connection"]),
            "metro_edges": len([f for f in features if f["properties"].get("connection_type") == "metro"]),
            "correspondences": len([f for f in features if f["properties"].get("connection_type") == "correspondance"])
        }
    }
    
    return geojson

def _get_node_coordinates(graph: nx.DiGraph, node_id: str) -> Optional[List[float]]:
    """Obtient les coordonnées d'un nœud"""
    if node_id not in graph.nodes:
        return None
        
    node_data = graph.nodes[node_id]
    lat = node_data.get('lat') or node_data.get('stop_lat')
    lon = node_data.get('lon') or node_data.get('stop_lon')
    
    if lat is None or lon is None:
        return None
        
    return [float(lon), float(lat)]

def _get_metro_line_color(route_name: str) -> str:
    """
    Retourne la couleur officielle des lignes de métro parisien.
    """
    metro_colors = {
        "1": "#FFBE00",   # Jaune
        "2": "#0055C8",   # Bleu
        "3": "#6E6E00",   # Olive
        "3B": "#6EC4E8",  # Bleu clair
        "4": "#A0006E",   # Violet
        "5": "#F28E42",   # Orange
        "6": "#78C695",   # Vert clair
        "7": "#FA9ABA",   # Rose
        "7B": "#6ECA97", # Vert
        "8": "#CEADD2",   # Mauve
        "9": "#D5C900",   # Jaune-vert
        "10": "#8D5524",  # Marron
        "11": "#8D5524",  # Marron
        "12": "#65AC57",  # Vert
        "13": "#6EC4E8",  # Bleu clair
        "14": "#62259D"   # Violet foncé
    }
    
    # Retourner la couleur de la ligne ou une couleur par défaut
    return metro_colors.get(str(route_name), "#4A90E2")  # Bleu par défaut

def create_connection_test_geojson(graph: nx.DiGraph, station1_id: str, station2_id: str) -> Dict:
    """
    Crée un GeoJSON spécifique pour tester la connexion entre deux stations.
    
    Args:
        graph: Graphe NetworkX
        station1_id: ID de la première station
        station2_id: ID de la deuxième station
        
    Returns:
        Dict: GeoJSON avec les deux stations et leur(s) connexion(s) éventuelle(s)
    """
    
    features = []
    connections_found = []
    
    # Vérifier que les stations existent
    if station1_id not in graph.nodes or station2_id not in graph.nodes:
        return {
            "type": "FeatureCollection", 
            "features": [],
            "error": f"Station(s) non trouvée(s): {station1_id}, {station2_id}"
        }
    
    # Ajouter les deux stations
    for station_id in [station1_id, station2_id]:
        node_data = graph.nodes[station_id]
        coords = _get_node_coordinates(graph, station_id)
        
        if coords:
            station_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": coords
                },
                "properties": {
                    "type": "station",
                    "stop_id": station_id,
                    "stop_name": node_data.get('stop_name', 'Station inconnue'),
                    "highlight": True
                }
            }
            features.append(station_feature)
    
    # Chercher les connexions dans les deux sens
    connections_info = []
    
    # Connexion directe station1 -> station2
    if graph.has_edge(station1_id, station2_id):
        edge_data = graph.edges[station1_id, station2_id]
        connections_info.append({
            "from": station1_id,
            "to": station2_id,
            "data": edge_data,
            "direction": "direct"
        })
    
    # Connexion inverse station2 -> station1
    if graph.has_edge(station2_id, station1_id):
        edge_data = graph.edges[station2_id, station1_id]
        connections_info.append({
            "from": station2_id,
            "to": station1_id,
            "data": edge_data,
            "direction": "inverse"
        })
    
    # Créer les features pour les connexions
    for i, conn_info in enumerate(connections_info):
        from_coords = _get_node_coordinates(graph, conn_info["from"])
        to_coords = _get_node_coordinates(graph, conn_info["to"])
        
        if from_coords and to_coords:
            edge_data = conn_info["data"]
            
            # Déterminer le type et la couleur
            if edge_data.get('transfer_type') == 'correspondence':
                connection_type = "correspondance"
                color = "#FF6B6B"  # Rouge
                weight = 4
            else:
                connection_type = "metro"
                route_name = edge_data.get('route_name', '')
                color = _get_metro_line_color(route_name)
                weight = 3
            
            connection_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [from_coords, to_coords]
                },
                "properties": {
                    "type": "connection",
                    "connection_type": connection_type,
                    "direction": conn_info["direction"],
                    "from_stop": conn_info["from"],
                    "to_stop": conn_info["to"],
                    "travel_time": edge_data.get('weight', 0),
                    "route_name": edge_data.get('route_name', ''),
                    "color": color,
                    "weight": weight,
                    "highlight": True
                }
            }
            features.append(connection_feature)
            connections_found.append(connection_type)
    
    # Métadonnées sur la connexion
    station1_name = graph.nodes[station1_id].get('stop_name', station1_id)
    station2_name = graph.nodes[station2_id].get('stop_name', station2_id)
    
    metadata = {
        "station1": {"id": station1_id, "name": station1_name},
        "station2": {"id": station2_id, "name": station2_name},
        "connections_found": len(connections_found),
        "connection_types": list(set(connections_found)),
        "bidirectional": len(connections_found) == 2,
        "connected": len(connections_found) > 0
    }
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": metadata
    }

def find_connected_stations(graph: nx.DiGraph, station_id: str, max_connections: int = 10) -> Dict:
    """
    Trouve toutes les stations directement connectées à une station donnée.
    
    Args:
        graph: Graphe NetworkX
        station_id: ID de la station de référence
        max_connections: Nombre maximum de connexions à retourner
        
    Returns:
        Dict: GeoJSON avec la station et ses connexions directes
    """
    
    if station_id not in graph.nodes:
        return {
            "type": "FeatureCollection",
            "features": [],
            "error": f"Station non trouvée: {station_id}"
        }
    
    features = []
    station_data = graph.nodes[station_id]
    
    # Ajouter la station centrale (en évidence)
    center_coords = _get_node_coordinates(graph, station_id)
    if center_coords:
        center_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": center_coords
            },
            "properties": {
                "type": "station",
                "stop_id": station_id,
                "stop_name": station_data.get('stop_name', 'Station inconnue'),
                "highlight": True,
                "center": True
            }
        }
        features.append(center_feature)
    
    # Trouver toutes les connexions sortantes
    connected_stations = []
    connections_data = []
    
    for neighbor in graph.neighbors(station_id):
        if len(connected_stations) >= max_connections:
            break
            
        edge_data = graph.edges[station_id, neighbor]
        connected_stations.append(neighbor)
        connections_data.append({
            "to": neighbor,
            "edge_data": edge_data
        })
    
    # Ajouter les stations connectées
    for neighbor in connected_stations:
        neighbor_coords = _get_node_coordinates(graph, neighbor)
        if neighbor_coords:
            neighbor_data = graph.nodes[neighbor]
            neighbor_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": neighbor_coords
                },
                "properties": {
                    "type": "station",
                    "stop_id": neighbor,
                    "stop_name": neighbor_data.get('stop_name', 'Station inconnue'),
                    "connected": True
                }
            }
            features.append(neighbor_feature)
    
    # Ajouter les connexions
    metro_count = 0
    transfer_count = 0
    
    for conn_data in connections_data:
        to_coords = _get_node_coordinates(graph, conn_data["to"])
        if center_coords and to_coords:
            edge_data = conn_data["edge_data"]
            
            if edge_data.get('transfer_type') == 'correspondence':
                connection_type = "correspondance"
                color = "#FF6B6B"
                transfer_count += 1
            else:
                connection_type = "metro"
                route_name = edge_data.get('route_name', '')
                color = _get_metro_line_color(route_name)
                metro_count += 1
            
            connection_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [center_coords, to_coords]
                },
                "properties": {
                    "type": "connection",
                    "connection_type": connection_type,
                    "from_stop": station_id,
                    "to_stop": conn_data["to"],
                    "travel_time": edge_data.get('weight', 0),
                    "route_name": edge_data.get('route_name', ''),
                    "color": color,
                    "weight": 3
                }
            }
            features.append(connection_feature)
    
    metadata = {
        "center_station": {
            "id": station_id,
            "name": station_data.get('stop_name', station_id)
        },
        "total_connections": len(connected_stations),
        "metro_connections": metro_count,
        "transfer_connections": transfer_count,
        "connected_stations": [
            {
                "id": neighbor,
                "name": graph.nodes[neighbor].get('stop_name', neighbor)
            }
            for neighbor in connected_stations
        ]
    }
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": metadata
    }
