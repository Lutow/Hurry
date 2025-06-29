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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        """Construit le graphe avec des arêtes uniques."""
        logger.info("=== Construction du graphe avec arêtes uniques ===")
        start_time = time.time()
        
        # 1. Charger les données de base
        routes_df = self._load_routes()
        stops_df = self._load_stops()
        transfers_df = self._load_transfers()
        
        # 2. Construire le dictionnaire des stations
        logger.info("Construction du dictionnaire des stations...")
        for _, stop in stops_df.iterrows():
            self.stations[stop['stop_id']] = {
                'name': stop['stop_name'],
                'lat': stop['stop_lat'],
                'lon': stop['stop_lon'],
                'zone_id': stop.get('zone_id', ''),
                'parent_station': stop.get('parent_station', '')
            }
        logger.info(f"Stations chargées: {len(self.stations)}")
        
        # 3. Construire le dictionnaire des routes pour les couleurs
        route_colors = {}
        for _, route in routes_df.iterrows():
            route_colors[route['route_id']] = {
                'short_name': route['route_short_name'],
                'long_name': route['route_long_name'],
                'color': route.get('route_color', 'CCCCCC'),
                'text_color': route.get('route_text_color', '000000')
            }
        
        # 4. Extraire les arêtes uniques
        unique_edges_set = self._get_unique_edges_from_stop_times()
        
        # 5. Construire le graphe avec les arêtes uniques
        logger.info("Construction des arêtes uniques...")
        for stop1, stop2, route_id in unique_edges_set:
            # Vérifier que les stations existent
            if stop1 in self.stations and stop2 in self.stations:
                edge_key = (stop1, stop2, route_id)
                
                # Calculer la distance approximative (pour l'exemple)
                lat1, lon1 = self.stations[stop1]['lat'], self.stations[stop1]['lon']
                lat2, lon2 = self.stations[stop2]['lat'], self.stations[stop2]['lon']
                distance = ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5 * 111000  # Approximation
                
                self.unique_edges[edge_key] = {
                    'from_stop': stop1,
                    'to_stop': stop2,
                    'route_id': route_id,
                    'route_info': route_colors.get(route_id, {}),
                    'distance': distance,
                    'travel_time': max(60, distance / 1000 * 2)  # Temps estimé en secondes
                }
        
        logger.info(f"Arêtes uniques construites: {len(self.unique_edges)}")
        
        # 6. Construire les transferts
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
        
        total_time = time.time() - start_time
        logger.info(f"=== Graphe construit en {total_time:.2f}s ===")
        logger.info(f"Stations: {len(self.stations)}")
        logger.info(f"Arêtes uniques: {len(self.unique_edges)}")
        logger.info(f"Stations avec transferts: {len(self.transfers)}")

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

if __name__ == "__main__":
    main()
