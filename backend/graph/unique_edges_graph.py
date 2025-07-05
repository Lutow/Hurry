"""
Génération d'un graphe avec des arêtes UNIQUES entre stations consécutives.
Cette version ne crée qu'UNE SEULE arête par couple de stations consécutives sur chaque ligne,
contrairement aux versions précédentes qui créaient une arête par passage de métro.
"""

import pickle
import sqlite3
import pandas as pd
from typing import Dict, List, Tuple, Set
import logging
from pathlib import Path
import os
import time

# Configuration du logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UniqueEdgesMetroGraph:
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.cache_dir = self.data_path / "IDFM-gtfs_metro_pkl"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Graphe avec arêtes uniques
        self.stations = {}  # stop_id -> {name, lat, lon, ...}
        self.unique_edges = {}  # (stop_id1, stop_id2, route_id) -> edge_data
        self.transfers = {}  # stop_id -> [connected_stop_ids]
        
        # Pour l'algorithme de recherche d'itinéraire
        self.nodes = set()  # Ensemble des identifiants de stations
        self.adjacency = {}  # Dictionnaire d'adjacence: stop_id -> {voisin: (route_id, coût)}
        self.temp_edges_backup = {}  # Sauvegarde des arêtes temporairement supprimées
        
        # Cache des données
        self._routes_cache = None
        self._stops_cache = None
        
        logger.info(f"Initialisation du graphe avec arêtes uniques - Cache: {self.cache_dir}")

    def _load_routes(self) -> pd.DataFrame:
        """Charge les données des routes avec cache."""
        cache_file = self.cache_dir / "routes.pkl"
        
        if cache_file.exists():
            logger.info("Chargement des routes depuis le cache")
            return pickle.load(open(cache_file, 'rb'))
        
        logger.info("Chargement des routes depuis CSV")
        routes_df = pd.read_csv(self.data_path / "IDFM-gtfs" / "routes.txt")
        
        # Sauvegarde en cache
        pickle.dump(routes_df, open(cache_file, 'wb'))
        return routes_df

    def _load_stops(self) -> pd.DataFrame:
        """Charge les données des stations avec cache."""
        cache_file = self.cache_dir / "stops.pkl"
        
        if cache_file.exists():
            logger.info("Chargement des stations depuis le cache")
            return pickle.load(open(cache_file, 'rb'))
        
        logger.info("Chargement des stations depuis CSV")
        stops_df = pd.read_csv(self.data_path / "IDFM-gtfs" / "stops.txt")
        
        # Sauvegarde en cache
        pickle.dump(stops_df, open(cache_file, 'wb'))
        return stops_df

    def _get_unique_edges_from_stop_times(self) -> Set[Tuple[str, str, str]]:
        """
        Extrait les arêtes UNIQUES depuis stop_times.
        Retourne un set de tuples (stop_id1, stop_id2, route_id) pour chaque couple
        de stations consécutives sur chaque ligne.
        """
        cache_file = self.cache_dir / "unique_edges.pkl"
        
        if cache_file.exists():
            logger.info("Chargement des arêtes uniques depuis le cache")
            return pickle.load(open(cache_file, 'rb'))
        
        logger.info("Extraction des arêtes uniques depuis stop_times...")
        start_time = time.time()
        
        # Utiliser les fichiers en cache
        stop_times_cache = self.cache_dir / "stop_times.pkl"
        trips_cache = self.cache_dir / "trips.pkl"
        
        if not stop_times_cache.exists() or not trips_cache.exists():
            logger.error("Fichiers cache manquants pour stop_times ou trips")
            return set()
        
        # Charger trips pour avoir route_id par trip_id
        logger.info("Chargement des trips depuis le cache...")
        trips_df = pickle.load(open(trips_cache, 'rb'))
        trip_to_route = dict(zip(trips_df['trip_id'], trips_df['route_id']))
        
        # Charger stop_times depuis le cache
        logger.info("Chargement des stop_times depuis le cache...")
        stop_times_df = pickle.load(open(stop_times_cache, 'rb'))
        
        logger.info(f"Loaded {len(stop_times_df)} stop_times entries")
        
        unique_edges = set()
        
        # Ajouter route_id depuis trips
        logger.info("Ajout des route_id...")
        stop_times_df['route_id'] = stop_times_df['trip_id'].map(trip_to_route)
        
        # Grouper par trip_id et trier par stop_sequence
        logger.info("Extraction des arêtes par trip...")
        for trip_id, trip_data in stop_times_df.groupby('trip_id'):
            trip_data = trip_data.sort_values('stop_sequence')
            stops = trip_data['stop_id'].tolist()
            route_id = trip_data['route_id'].iloc[0] if len(trip_data) > 0 else None
            
            if route_id is None:
                continue
            
            # Créer les arêtes entre stations consécutives
            for j in range(len(stops) - 1):
                stop1, stop2 = stops[j], stops[j+1]
                # Créer une arête unique (ordonnée pour éviter doublons)
                edge = tuple(sorted([stop1, stop2]) + [route_id])
                unique_edges.add(edge)
        
        logger.info(f"Extraction terminée en {time.time() - start_time:.2f}s")
        logger.info(f"Nombre d'arêtes uniques trouvées: {len(unique_edges)}")
        
        # Sauvegarde en cache
        pickle.dump(unique_edges, open(cache_file, 'wb'))
        return unique_edges

    def _load_transfers(self) -> pd.DataFrame:
        """Charge les données des transferts avec cache."""
        cache_file = self.cache_dir / "transfers.pkl"
        
        if cache_file.exists():
            logger.info("Chargement des transferts depuis le cache")
            return pickle.load(open(cache_file, 'rb'))
        
        logger.info("Chargement des transferts depuis CSV")
        transfers_df = pd.read_csv(self.data_path / "IDFM-gtfs" / "transfers.txt")
        
        # Sauvegarde en cache
        pickle.dump(transfers_df, open(cache_file, 'wb'))
        return transfers_df

    def build_graph(self):
        """Construit le graphe complet avec arêtes uniques."""
        # 1. Charger les données nécessaires
        logger.info("Chargement des données...")
        start_time = time.time()
        
        # Charger les fichiers stop_times.txt et trips.txt si non présents dans le cache
        self._prepare_cache_data()
        
        # Charger les arêtes uniques (depuis le cache ou les calculer)
        unique_edges_set = self._get_unique_edges_from_stop_times()
        
        if not unique_edges_set:
            logger.error("Aucune arête unique trouvée")
            return
            
        logger.info(f"Arêtes uniques extraites: {len(unique_edges_set)}")
        
        # 2. Charger les informations des stations
        stops_df = self._load_stops()
        
        # 3. Charger les informations sur les lignes (pour les couleurs)
        routes_df = self._load_routes()
        route_colors = {}
        for _, route in routes_df.iterrows():
            route_colors[route['route_id']] = {
                'route_id': route['route_id'],
                'short_name': route['route_short_name'],
                'color': route.get('route_color', 'FFFFFF'),
                'text_color': route.get('route_text_color', '000000')
            }
        
        # 4. Construire le dictionnaire des stations
        logger.info("Construction du dictionnaire des stations...")
        for _, stop in stops_df.iterrows():
            if stop['location_type'] == 0:  # 0 = station régulière
                self.stations[stop['stop_id']] = {
                    'stop_id': stop['stop_id'],
                    'name': stop['stop_name'],
                    'lat': stop['stop_lat'],
                    'lon': stop['stop_lon'],
                    'location_type': stop['location_type'],
                }
                
                # Créer un nœud dans le graphe pour cette station
                self.nodes.add(stop['stop_id'])
        
        logger.info(f"Stations extraites: {len(self.stations)}")
        
        # 5. Chargement des transferts
        transfers_cache = self.cache_dir / "transfers.pkl"
        if transfers_cache.exists():
            logger.info("Chargement des transferts depuis le cache...")
            transfers_df = pickle.load(open(transfers_cache, 'rb'))
        else:
            logger.info("Chargement des transferts depuis CSV...")
            transfers_path = self.data_path / "IDFM-gtfs" / "transfers.txt"
            if transfers_path.exists():
                transfers_df = pd.read_csv(transfers_path)
                pickle.dump(transfers_df, open(transfers_cache, 'wb'))
            else:
                logger.warning("Fichier transfers.txt non trouvé!")
                transfers_df = pd.DataFrame(columns=['from_stop_id', 'to_stop_id', 'transfer_type', 'min_transfer_time'])
        
        # 6. Construire les arêtes uniques
        logger.info("Construction des arêtes uniques...")
        for stop1, stop2, route_id in unique_edges_set:
            if stop1 not in self.stations or stop2 not in self.stations:
                continue
                
            # Calculer la distance approximative entre les stations (en mètres)
            lat1, lon1 = self.stations[stop1]['lat'], self.stations[stop1]['lon']
            lat2, lon2 = self.stations[stop2]['lat'], self.stations[stop2]['lon']
            
            # Formule de Haversine simplifiée pour courtes distances
            distance = self._haversine_distance(lat1, lon1, lat2, lon2)
            
            # Ajouter l'arête
            self.unique_edges[(stop1, stop2, route_id)] = {
                'from_stop': stop1,
                'to_stop': stop2,
                'route_id': route_id,
                'route_info': route_colors.get(route_id, {}),
                'distance': distance,
                'travel_time': max(60, distance / 1000 * 2)  # Temps estimé en secondes
            }
        
        logger.info(f"Arêtes uniques construites: {len(self.unique_edges)}")
        
        # 7. Construire les transferts
        logger.info("Construction des transferts...")
        for _, transfer in transfers_df.iterrows():
            from_stop = transfer['from_stop_id']
            to_stop = transfer['to_stop_id']
            
            if from_stop not in self.transfers:
                self.transfers[from_stop] = []
            if to_stop not in self.transfers:
                self.transfers[to_stop] = []
                
            self.transfers[from_stop].append({
                'to_stop': to_stop,
                'transfer_time': transfer.get('min_transfer_time', 180),
                'transfer_type': transfer.get('transfer_type', 2)
            })
        
        logger.info(f"Transferts construits: {len(self.transfers)} stations avec transferts")
        
        # 8. Construire les structures pour la recherche d'itinéraire
        logger.info("Construction des structures pour la recherche d'itinéraire...")
        self.adjacency = {}  # Réinitialiser la structure d'adjacence
        
        for (stop1, stop2, route_id), edge_data in self.unique_edges.items():
            if stop1 not in self.adjacency:
                self.adjacency[stop1] = {}
            if stop2 not in self.adjacency:
                self.adjacency[stop2] = {}
            
            # Pour la recherche d'itinéraire, on utilise un coût de 1 pour chaque arête
            # On stocke aussi la ligne (route_id) pour pouvoir déterminer les correspondances
            self.adjacency[stop1][stop2] = (route_id, 1)
            self.adjacency[stop2][stop1] = (route_id, 1)  # Graphe bidirectionnel
        
        # 9. Ajouter les transferts dans la structure d'adjacence
        for from_stop, transfer_list in self.transfers.items():
            if from_stop not in self.adjacency:
                self.adjacency[from_stop] = {}
                
            for transfer in transfer_list:
                to_stop = transfer['to_stop']
                if to_stop not in self.adjacency:
                    self.adjacency[to_stop] = {}
                
                # Les transferts sont considérés comme une arête spéciale
                # avec un coût de 1 (comme les arêtes normales)
                transfer_route_id = "transfer"  # Identifiant spécial pour les transferts
                self.adjacency[from_stop][to_stop] = (transfer_route_id, 1)
        
        # Sauvegarde des noeuds
        self.nodes = set(self.adjacency.keys())
        
        # Effectuer un nettoyage pour s'assurer que tous les nœuds sont accessibles
        nodes_to_remove = set()
        for node in self.nodes:
            if node not in self.adjacency or not self.adjacency[node]:
                nodes_to_remove.add(node)
        
        # Supprimer les nœuds isolés
        for node in nodes_to_remove:
            self.nodes.remove(node)
            if node in self.adjacency:
                del self.adjacency[node]
        
        if nodes_to_remove:
            logger.info(f"Nœuds isolés supprimés: {len(nodes_to_remove)}")
        
        total_time = time.time() - start_time
        logger.info(f"=== Graphe construit en {total_time:.2f}s ===")
        logger.info(f"Stations: {len(self.stations)}")
        logger.info(f"Arêtes uniques: {len(self.unique_edges)}")
        logger.info(f"Stations avec transferts: {len(self.transfers)}")
        logger.info(f"Nœuds dans le graphe de recherche: {len(self.nodes)}")
        logger.info(f"Nombre moyen de voisins par nœud: {sum(len(adj) for adj in self.adjacency.values()) / len(self.adjacency) if self.adjacency else 0:.2f}")

    def get_station_connections(self, stop_id: str) -> List[Dict]:
        """Retourne toutes les connexions d'une station (arêtes + transferts)."""
        connections = []
        
        # Connexions directes (arêtes)
        for (stop1, stop2, route_id), edge_data in self.unique_edges.items():
            if stop1 == stop_id:
                connections.append({
                    'to_stop': stop2,
                    'type': 'direct',
                    'route_id': route_id,
                    'route_info': edge_data['route_info'],
                    'travel_time': edge_data['travel_time']
                })
            elif stop2 == stop_id:
                connections.append({
                    'to_stop': stop1,
                    'type': 'direct',
                    'route_id': route_id,
                    'route_info': edge_data['route_info'],
                    'travel_time': edge_data['travel_time']
                })
        
        # Transferts
        if stop_id in self.transfers:
            for transfer in self.transfers[stop_id]:
                connections.append({
                    'to_stop': transfer['to_stop'],
                    'type': 'transfer',
                    'transfer_time': transfer['transfer_time'],
                    'transfer_type': transfer['transfer_type']
                })
        
        return connections

    def find_direct_connection(self, from_stop: str, to_stop: str) -> List[Dict]:
        """Trouve les connexions directes entre deux stations."""
        connections = []
        
        # Rechercher dans les arêtes uniques
        for (stop1, stop2, route_id), edge_data in self.unique_edges.items():
            if (stop1 == from_stop and stop2 == to_stop) or (stop1 == to_stop and stop2 == from_stop):
                connections.append({
                    'route_id': route_id,
                    'route_info': edge_data['route_info'],
                    'travel_time': edge_data['travel_time'],
                    'distance': edge_data['distance']
                })
        
        return connections

    def get_all_edges_for_geojson(self) -> List[Dict]:
        """Retourne toutes les arêtes pour la génération de GeoJSON."""
        edges = []
        
        # Arêtes directes
        for (stop1, stop2, route_id), edge_data in self.unique_edges.items():
            if stop1 in self.stations and stop2 in self.stations:
                edges.append({
                    'from_stop': stop1,
                    'to_stop': stop2,
                    'from_name': self.stations[stop1]['name'],
                    'to_name': self.stations[stop2]['name'],
                    'from_coords': [self.stations[stop1]['lon'], self.stations[stop1]['lat']],
                    'to_coords': [self.stations[stop2]['lon'], self.stations[stop2]['lat']],
                    'route_id': route_id,
                    'route_info': edge_data['route_info'],
                    'travel_time': edge_data['travel_time'],  # Ajout du temps de trajet
                    'type': 'direct',
                    'color': f"#{edge_data['route_info'].get('color', 'CCCCCC')}"
                })
        
        # Transferts
        for from_stop, transfers in self.transfers.items():
            if from_stop in self.stations:
                for transfer in transfers:
                    to_stop = transfer['to_stop']
                    if to_stop in self.stations:
                        edges.append({
                            'from_stop': from_stop,
                            'to_stop': to_stop,
                            'from_name': self.stations[from_stop]['name'],
                            'to_name': self.stations[to_stop]['name'],
                            'from_coords': [self.stations[from_stop]['lon'], self.stations[from_stop]['lat']],
                            'to_coords': [self.stations[to_stop]['lon'], self.stations[to_stop]['lat']],
                            'type': 'transfer',
                            'color': '#FF0000',  # Rouge pour les transferts
                            'transfer_time': transfer['transfer_time']
                        })
        
        return edges

    def find_shortest_path(self, start: str, end: str) -> Tuple[List[str], float]:
        """
        Trouve le chemin le plus court entre deux stations.
        Utilise une variante de l'algorithme de Dijkstra.
        """
        logger.info(f"Recherche du chemin le plus court de {start} à {end}...")
        
        if start == end:
            return [start], 0
        
        # Initialiser les structures
        visited = set()
        distances = {node: float('inf') for node in self.nodes}
        previous_nodes = {node: None for node in self.nodes}
        distances[start] = 0
        
        # File de priorité (min-heap)
        from heapq import heappop, heappush
        priority_queue = [(0, start)]  # (coût, stop_id)
        
        while priority_queue:
            current_distance, current_node = heappop(priority_queue)
            
            if current_node in visited:
                continue
            
            visited.add(current_node)
            
            # Explorer les voisins
            for neighbor, (route_id, travel_time) in self.adjacency.get(current_node, {}).items():
                if neighbor in visited:
                    continue
                
                new_distance = current_distance + travel_time
                
                # Relaxation
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous_nodes[neighbor] = current_node
                    heappush(priority_queue, (new_distance, neighbor))
        
        # Reconstruire le chemin
        path = []
        current_node = end
        while current_node is not None:
            path.append(current_node)
            current_node = previous_nodes[current_node]
        
        path = path[::-1]  # Inverser le chemin
        
        if distances[end] == float('inf'):
            logger.info("Aucun chemin trouvé")
            return [], float('inf')
        
        logger.info(f"Chemin trouvé: {' -> '.join(path)} avec un coût de {distances[end]}")
        return path, distances[end]

    # --- Méthodes pour la recherche d'itinéraires ---

    def get_neighbors(self, node_id: str) -> List[str]:
        """Retourne la liste des voisins d'un nœud."""
        if node_id in self.adjacency:
            return list(self.adjacency[node_id].keys())
        return []
        
    def get_line_between_stations(self, from_id: str, to_id: str) -> str:
        """Retourne l'identifiant de ligne entre deux stations."""
        if from_id in self.adjacency and to_id in self.adjacency[from_id]:
            route_id, _ = self.adjacency[from_id][to_id]
            logger.debug(f"Connexion {from_id} -> {to_id}: route_id = {route_id}")
            # Extraire le numéro/lettre de ligne à partir du route_id
            route_short_name = self._get_route_short_name(route_id)
            return route_short_name
        else:
            logger.warning(f"Aucune connexion trouvée entre {from_id} et {to_id}")
            return "?"  # Ligne inconnue
    
    def _get_route_short_name(self, route_id: str) -> str:
        """Récupère le nom court de la ligne à partir du route_id."""
        if route_id == "transfer":
            return "Correspondance"
            
        if self._routes_cache is None:
            self._routes_cache = self._load_routes()
            logger.info(f"Cache des routes chargé: {len(self._routes_cache)} routes")
            
        route_info = self._routes_cache[self._routes_cache['route_id'] == route_id]
        if not route_info.empty:
            short_name = route_info.iloc[0]['route_short_name']
            logger.debug(f"Route {route_id} -> {short_name}")
            return short_name
        else:
            logger.warning(f"Route {route_id} non trouvée dans le cache des routes")
            return "?"

    def get_station_name(self, stop_id: str) -> str:
        """Récupère le nom d'une station à partir de son identifiant."""
        if stop_id in self.stations:
            return self.stations[stop_id]['name']
        return stop_id  # Retourne l'ID si nom non trouvé
    
    def find_station_by_name(self, name_query: str) -> List[str]:
        """
        Recherche une station par nom avec correspondance floue améliorée.
        Retourne une liste d'IDs de stations correspondantes, triée par pertinence.
        Version améliorée avec seuil plus strict pour éviter les confusions.
        """
        try:
            from backend.utils.fuzzy_search import find_best_station_matches
            
            # Utiliser la recherche floue améliorée avec seuil plus strict
            matches = find_best_station_matches(self.stations, name_query, max_results=3, min_score=0.7)
            
            if matches:
                best_match = matches[0]
                station_name = self.stations[best_match[0]].get('name', 'Unknown')
                logger.info(f"Station trouvée pour '{name_query}': '{station_name}' (score: {best_match[1]:.2f})")
            else:
                logger.warning(f"Aucune station trouvée pour '{name_query}' avec le seuil strict")
            
            # Retourner uniquement les IDs des stations
            return [match[0] for match in matches]
            
        except ImportError:
            # Fallback vers l'ancienne méthode si le module n'est pas disponible
            logger.warning("Module fuzzy_search non disponible, utilisation de la recherche basique")
            return self._find_station_by_name_basic(name_query)
    
    def _find_station_by_name_basic(self, name_query: str) -> List[str]:
        """
        Méthode de recherche basique (fallback).
        """
        matches = []
        name_query = name_query.lower().strip()
        
        # Premièrement, rechercher les correspondances exactes ou contenues
        for stop_id, station_data in self.stations.items():
            station_name = station_data['name'].lower()
            
            # Correspondance exacte
            if station_name == name_query:
                matches.insert(0, stop_id)  # Priorité maximale
            # Nom de la requête contenu dans le nom de la station
            elif name_query in station_name:
                matches.append(stop_id)
        
        # Si aucune correspondance, rechercher des correspondances partielles
        if not matches:
            query_words = set(name_query.split())
            for stop_id, station_data in self.stations.items():
                station_name = station_data['name'].lower()
                station_words = set(station_name.split())
                
                # Intersection des mots
                common_words = query_words.intersection(station_words)
                if common_words:
                    matches.append(stop_id)
        
        return matches
    
    def remove_edge_temporarily(self, from_id: str, to_id: str):
        """
        Supprime temporairement une arête du graphe pour l'algorithme de Yen.
        """
        if from_id in self.adjacency and to_id in self.adjacency[from_id]:
            if from_id not in self.temp_edges_backup:
                self.temp_edges_backup[from_id] = {}
            
            # Sauvegarder l'arête avant suppression
            self.temp_edges_backup[from_id][to_id] = self.adjacency[from_id][to_id]
            
            # Supprimer l'arête
            del self.adjacency[from_id][to_id]
    
    def restore_edges(self, node_id: str, neighbors: dict):
        """
        Restaure les arêtes temporairement supprimées pour un nœud.
        """
        if node_id in self.temp_edges_backup:
            for neighbor, edge_data in self.temp_edges_backup[node_id].items():
                self.adjacency[node_id][neighbor] = edge_data
            
            # Supprimer la sauvegarde
            del self.temp_edges_backup[node_id]
    
    def _prepare_cache_data(self):
        """Prépare les données de cache pour les fichiers stop_times.txt et trips.txt."""
        stop_times_cache = self.cache_dir / "stop_times.pkl"
        trips_cache = self.cache_dir / "trips.pkl"
        
        # Vérification de l'existence des fichiers
        if not stop_times_cache.exists():
            logger.info("Préparation du cache pour stop_times.txt...")
            stop_times_path = self.data_path / "IDFM-gtfs" / "stop_times.txt"
            if stop_times_path.exists():
                logger.info("Chargement du fichier stop_times.txt...")
                stop_times_df = pd.read_csv(stop_times_path)
                pickle.dump(stop_times_df, open(stop_times_cache, 'wb'))
                logger.info("Cache pour stop_times.txt créé avec succès.")
            else:
                logger.error("Fichier stop_times.txt introuvable!")
        
        if not trips_cache.exists():
            logger.info("Préparation du cache pour trips.txt...")
            trips_path = self.data_path / "IDFM-gtfs" / "trips.txt"
            if trips_path.exists():
                logger.info("Chargement du fichier trips.txt...")
                trips_df = pd.read_csv(trips_path)
                pickle.dump(trips_df, open(trips_cache, 'wb'))
                logger.info("Cache pour trips.txt créé avec succès.")
            else:
                logger.error("Fichier trips.txt introuvable!")

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calcule la distance approximative entre deux points géographiques
        en utilisant la formule de Haversine.
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Rayon de la Terre en mètres
        R = 6371000
        
        # Conversion en radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Différences
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Formule de Haversine
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        return distance
def main():
    """Test de la génération du graphe avec arêtes uniques."""
    data_path = "."
    
    graph = UniqueEdgesMetroGraph(data_path)
    graph.build_graph()
    
    # Test des connexions
    logger.info("\n=== Test des connexions ===")
    
    # Prendre une station au hasard pour tester
    if graph.stations:
        test_station = list(graph.stations.keys())[0]
        connections = graph.get_station_connections(test_station)
        
        logger.info(f"Station de test: {test_station} ({graph.stations[test_station]['name']})")
        logger.info(f"Nombre de connexions: {len(connections)}")
        
        # Afficher quelques connexions
        for i, conn in enumerate(connections[:5]):
            if conn['type'] == 'direct':
                route_name = conn['route_info'].get('short_name', 'N/A')
                logger.info(f"  {i+1}. Ligne {route_name} vers {graph.stations[conn['to_stop']]['name']}")
            else:
                logger.info(f"  {i+1}. Transfert vers {graph.stations[conn['to_stop']]['name']}")
    
    # Test de la recherche de chemin
    logger.info("\n=== Test de la recherche de chemin ===")
    if len(graph.stations) > 1:
        start_station = list(graph.stations.keys())[0]
        end_station = list(graph.stations.keys())[-1]
        path, cost = graph.find_shortest_path(start_station, end_station)
        
        logger.info(f"Chemin le plus court de {start_station} à {end_station}: {' -> '.join(path)}")
        logger.info(f"Coût du chemin: {cost}")

if __name__ == "__main__":
    main()
