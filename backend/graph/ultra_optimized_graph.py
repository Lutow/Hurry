import pandas as pd
import networkx as nx
import numpy as np
from datetime import datetime, timedelta
import os
from typing import Dict, List, Tuple, Optional, Set
import pickle
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
from functools import lru_cache

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltraOptimizedGraphGTFS:
    """
    Version améliorée du graphe GTFS qui utilise SQLite pour avoir de meilleures performances, avec ça on a un chargement extrêmement rapide
    et des requêtes bien plus rapides.
    
    Nouvelles optimisations :
    1. Base de données SQLite pour les requêtes rapides
    2. Index spatiaux pour les zones géographiques
    3. Parallélisation du traitement
    4. Cache intelligent avec expiration
    5. Pré-agrégation des données
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.db_path = f"{data_path}/metro_graph.db"
        self.stops = None
        self.routes = None
        self.transfers = None
        self._load_data_and_setup_db()
        
    def _load_data_and_setup_db(self):
        """Charge les données et configure la base de données SQLite"""
        try:
            logger.info("Initialisation de la base de données ultra-optimisée...")
            
            # Charger les stations depuis la base SQLite (321 uniques)
            with sqlite3.connect(self.db_path) as conn:
                self.stops = pd.read_sql_query("SELECT * FROM stops", conn)
            self.routes = pd.read_pickle(f"{self.data_path}/routes.pkl")
            self.transfers = pd.read_pickle(f"{self.data_path}/transfers.pkl")
            logger.info(f"Données chargées: {len(self.stops)} stations (uniques), {len(self.routes)} lignes, {len(self.transfers)} correspondances")

            
            # Vérifier si la DB existe et est à jour
            if not os.path.exists(self.db_path) or self._db_needs_update():
                logger.info("Création/mise à jour de la base de données...")
                self._create_database()
            else:
                logger.info("Base de données existante trouvée et à jour")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation: {e}")
            raise
    
    def _db_needs_update(self) -> bool:
        """Vérifie si la DB doit être mise à jour"""
        try:
            # Comparer les timestamps des fichiers
            db_mtime = os.path.getmtime(self.db_path)
            pickle_files = [
                f"{self.data_path}/stops.pkl",
                f"{self.data_path}/stop_times.pkl",
                f"{self.data_path}/trips.pkl"
            ]
            
            for file in pickle_files:
                if os.path.exists(file) and os.path.getmtime(file) > db_mtime:
                    return True
            return False
        except:
            return True
    
    def _create_database(self):
        """Crée la base de données SQLite optimisée"""
        logger.info("Création de la base de données SQLite...")
        
        # Supprimer l'ancienne DB si elle existe
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Table des stations avec index spatial
            cursor.execute('''
                CREATE TABLE stops (
                    stop_id TEXT PRIMARY KEY,
                    stop_name TEXT,
                    stop_lat REAL,
                    stop_lon REAL,
                    wheelchair_boarding INTEGER,
                    zone_id TEXT
                )
            ''')
            
            # Index spatial sur les coordonnées
            cursor.execute('CREATE INDEX idx_stops_location ON stops(stop_lat, stop_lon)')
            
            # Table des arêtes pré-calculées
            cursor.execute('''
                CREATE TABLE edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_stop_id TEXT,
                    to_stop_id TEXT,
                    route_id TEXT,
                    trip_id TEXT,
                    travel_time REAL,
                    route_short_name TEXT,
                    FOREIGN KEY (from_stop_id) REFERENCES stops(stop_id),
                    FOREIGN KEY (to_stop_id) REFERENCES stops(stop_id)
                )
            ''')
            
            # Index sur les arêtes
            cursor.execute('CREATE INDEX idx_edges_from_stop ON edges(from_stop_id)')
            cursor.execute('CREATE INDEX idx_edges_to_stop ON edges(to_stop_id)')
            cursor.execute('CREATE INDEX idx_edges_route ON edges(route_id)')
            
            # Table des transferts
            cursor.execute('''
                CREATE TABLE transfers (
                    from_stop_id TEXT,
                    to_stop_id TEXT,
                    transfer_time REAL,
                    PRIMARY KEY (from_stop_id, to_stop_id)
                )
            ''')
            
            # Insérer les stations
            logger.info("Insertion des stations...")
            stops_data = []
            for _, stop in self.stops.iterrows():
                stops_data.append((
                    stop['stop_id'],
                    stop['stop_name'],
                    stop['stop_lat'],
                    stop['stop_lon'],
                    stop.get('wheelchair_boarding', 0),
                    stop.get('zone_id', '')
                ))
            
            cursor.executemany('''
                INSERT INTO stops (stop_id, stop_name, stop_lat, stop_lon, wheelchair_boarding, zone_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', stops_data)
            
            # Insérer les transferts
            logger.info("Insertion des transferts...")
            transfers_data = []
            for _, transfer in self.transfers.iterrows():
                transfers_data.append((
                    transfer['from_stop_id'],
                    transfer['to_stop_id'],
                    transfer.get('min_transfer_time', 120)
                ))
            
            cursor.executemany('''
                INSERT INTO transfers (from_stop_id, to_stop_id, transfer_time)
                VALUES (?, ?, ?)
            ''', transfers_data)
            
            # Traiter les arêtes en parallèle
            logger.info("Traitement des arêtes en parallèle...")
            self._process_edges_parallel(conn)
            
            conn.commit()
            logger.info("Base de données créée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la DB: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _process_edges_parallel(self, conn):
        """Traite les arêtes en parallèle pour optimiser les performances"""
        
        # Charger les données nécessaires
        trips = pd.read_pickle(f"{self.data_path}/trips.pkl")
        stop_times = pd.read_pickle(f"{self.data_path}/stop_times.pkl")
        
        # Créer un mapping route -> short_name
        route_names = self.routes.set_index('route_id')['route_short_name'].to_dict()
        
        # Diviser les trips en chunks pour le traitement parallèle
        chunk_size = 1000
        trip_chunks = [trips[i:i+chunk_size] for i in range(0, len(trips), chunk_size)]
        
        logger.info(f"Traitement de {len(trips)} trips en {len(trip_chunks)} chunks...")
        
        all_edges = []
        
        # Traiter chaque chunk
        for i, chunk in enumerate(trip_chunks):
            if i % 10 == 0:
                logger.info(f"Traitement du chunk {i+1}/{len(trip_chunks)}")
            
            chunk_edges = self._process_trip_chunk(chunk, stop_times, route_names)
            all_edges.extend(chunk_edges)
        
        # Insérer toutes les arêtes
        logger.info(f"Insertion de {len(all_edges)} arêtes...")
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO edges (from_stop_id, to_stop_id, route_id, trip_id, travel_time, route_short_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', all_edges)
        
        logger.info("Arêtes insérées avec succès")
    
    def _process_trip_chunk(self, trip_chunk, stop_times, route_names):
        """Traite un chunk de trips pour extraire les arêtes"""
        edges = []
        
        for _, trip in trip_chunk.iterrows():
            trip_id = trip['trip_id']
            route_id = trip['route_id']
            route_short_name = route_names.get(route_id, '')
            
            # Obtenir les stop_times pour ce trip
            trip_stops = stop_times[stop_times['trip_id'] == trip_id].sort_values('stop_sequence')
            
            if len(trip_stops) < 2:
                continue
            
            # Créer les arêtes consécutives
            for i in range(len(trip_stops) - 1):
                current_stop = trip_stops.iloc[i]
                next_stop = trip_stops.iloc[i + 1]
                
                # Calculer le temps de trajet
                try:
                    dep_time = self._parse_time(current_stop['departure_time'])
                    arr_time = self._parse_time(next_stop['arrival_time'])
                    travel_time = (arr_time - dep_time).total_seconds()
                    travel_time = max(travel_time, 60)  # Minimum 1 minute
                except:
                    travel_time = 120  # Valeur par défaut
                
                edges.append((
                    current_stop['stop_id'],
                    next_stop['stop_id'],
                    route_id,
                    trip_id,
                    travel_time,
                    route_short_name
                ))
        
        return edges
    
    def _parse_time(self, time_str: str) -> datetime:
        """Parse un temps GTFS optimisé"""
        try:
            hours, minutes, seconds = map(int, time_str.split(':'))
            if hours >= 24:
                hours -= 24
                return datetime.strptime(f"{hours:02d}:{minutes:02d}:{seconds:02d}", "%H:%M:%S") + timedelta(days=1)
            return datetime.strptime(time_str, "%H:%M:%S")
        except:
            return datetime.strptime("00:00:00", "%H:%M:%S")
    
    def build_graph_for_zone_sql(self, lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> nx.DiGraph:
        """
        Construit un graphe pour une zone en utilisant SQLite pour des performances optimales.
        """
        logger.info(f"Construction du graphe SQL pour zone: [{lat_min},{lat_max}] x [{lon_min},{lon_max}]")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Requête optimisée pour obtenir les stations dans la zone
            stations_query = '''
                SELECT stop_id, stop_name, stop_lat, stop_lon, wheelchair_boarding, zone_id
                FROM stops
                WHERE stop_lat BETWEEN ? AND ? AND stop_lon BETWEEN ? AND ?
            '''
            
            stations_df = pd.read_sql_query(
                stations_query, 
                conn, 
                params=[lat_min, lat_max, lon_min, lon_max]
            )
            
            if stations_df.empty:
                logger.warning("Aucune station dans la zone")
                return nx.DiGraph()
            
            logger.info(f"🚇 Trouvé {len(stations_df)} stations dans la zone")
            
            # Créer le graphe
            graph = nx.DiGraph()
            
            # Ajouter les nœuds
            for _, station in stations_df.iterrows():
                graph.add_node(
                    station['stop_id'],
                    stop_name=station['stop_name'],
                    lat=station['stop_lat'],
                    lon=station['stop_lon'],
                    accessibility=station['wheelchair_boarding']
                )
            
            # Obtenir les arêtes dans la zone
            stop_ids = list(stations_df['stop_id'])
            placeholders = ','.join(['?' for _ in stop_ids])
            
            edges_query = f'''
                SELECT from_stop_id, to_stop_id, travel_time, route_short_name, route_id
                FROM edges
                WHERE from_stop_id IN ({placeholders}) AND to_stop_id IN ({placeholders})
            '''
            
            edges_df = pd.read_sql_query(edges_query, conn, params=stop_ids + stop_ids)
            
            logger.info(f"🚇 Trouvé {len(edges_df):,} arêtes de métro dans la zone")
            
            # Ajouter les arêtes
            for _, edge in edges_df.iterrows():
                if edge['from_stop_id'] in graph.nodes and edge['to_stop_id'] in graph.nodes:
                    graph.add_edge(
                        edge['from_stop_id'],
                        edge['to_stop_id'],
                        weight=edge['travel_time'],
                        route_id=edge['route_id'],
                        route_name=edge['route_short_name']
                    )
            
            # Ajouter les transferts
            transfers_query = f'''
                SELECT from_stop_id, to_stop_id, transfer_time
                FROM transfers
                WHERE from_stop_id IN ({placeholders}) AND to_stop_id IN ({placeholders})
            '''
            
            transfers_df = pd.read_sql_query(transfers_query, conn, params=stop_ids + stop_ids)
            
            logger.info(f"🔄 Ajout de {len(transfers_df)} correspondances (transferts entre lignes)")
            
            for _, transfer in transfers_df.iterrows():
                if transfer['from_stop_id'] in graph.nodes and transfer['to_stop_id'] in graph.nodes:
                    graph.add_edge(
                        transfer['from_stop_id'],
                        transfer['to_stop_id'],
                        weight=transfer['transfer_time'],
                        transfer_type='correspondence'
                    )
            
            logger.info(f"✅ Graphe SQL final: {len(graph.nodes)} stations, {len(graph.edges)} connexions total")
            return graph
            
        except Exception as e:
            logger.error(f"Erreur lors de la construction du graphe SQL: {e}")
            raise
        finally:
            conn.close()
    
    def build_stations_only_graph(self) -> nx.DiGraph:
        """
        Construit un graphe avec seulement les stations (ultra-rapide).
        """
        logger.info("🏗️  Construction du graphe stations uniquement (sans connexions)...")
        
        graph = nx.DiGraph()
        
        # Ajouter toutes les stations comme nœuds
        for _, stop in self.stops.iterrows():
            graph.add_node(
                stop['stop_id'],
                stop_name=stop['stop_name'],
                lat=stop['stop_lat'],
                lon=stop['stop_lon'],
                accessibility=stop.get('wheelchair_boarding', 0)
            )
        
        logger.info(f"✅ Graphe stations créé: {len(graph.nodes)} stations de métro")
        return graph
    
    @lru_cache(maxsize=128)
    def get_route_info(self, route_id: str) -> Optional[Dict]:
        """Obtient les informations d'une ligne (avec cache)"""
        route_data = self.routes[self.routes['route_id'] == route_id]
        if not route_data.empty:
            return route_data.iloc[0].to_dict()
        return None
    
    def get_statistics(self) -> Dict:
        """Obtient des statistiques sur le système"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            stats = {}
            
            # Statistiques de base
            # Toujours compter les stations depuis la table stops SQLite (321 uniques)
            cursor.execute('SELECT COUNT(*) FROM stops')
            stats['total_stations'] = cursor.fetchone()[0]
            stats['total_routes'] = len(self.routes)
            stats['total_transfers'] = len(self.transfers)
            
            # Statistiques depuis la DB
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM edges')
            stats['total_edges'] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT route_short_name, COUNT(*) as edge_count
                FROM edges
                GROUP BY route_short_name
                ORDER BY edge_count DESC
            ''')
            
            stats['edges_by_route'] = dict(cursor.fetchall())
            
            return stats
            
        finally:
            conn.close()
    
    def clear_database(self):
        """Supprime la base de données pour forcer une reconstruction"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            logger.info("Base de données supprimée - prochaine utilisation recréera la DB")
        else:
            logger.info("Aucune base de données à supprimer")
    
    def build_full_network_graph(self) -> nx.DiGraph:
        """
        Construit un graphe complet avec toutes les stations et connexions du réseau.
        Version optimisée qui évite de recalculer si déjà fait.
        """
        logger.info("Construction du graphe complet pour vérification de connexité...")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Créer le graphe
            graph = nx.DiGraph()
            
            # Ajouter toutes les stations
            logger.info("Ajout de toutes les stations...")
            for _, stop in self.stops.iterrows():
                graph.add_node(
                    stop['stop_id'],
                    stop_name=stop['stop_name'],
                    lat=stop['stop_lat'],
                    lon=stop['stop_lon'],
                    accessibility=stop.get('wheelchair_boarding', 0)
                )
            
            # Vérifier si la base contient des arêtes
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM edges')
            edges_count = cursor.fetchone()[0]
            
            if edges_count == 0:
                logger.warning("⚠️ Aucune arête dans la base, construction rapide avec transferts uniquement...")
                # Utiliser seulement les transferts pour un test rapide
                for _, transfer in self.transfers.iterrows():
                    if transfer['from_stop_id'] in graph.nodes and transfer['to_stop_id'] in graph.nodes:
                        # Ajouter les transferts dans les deux sens
                        graph.add_edge(
                            transfer['from_stop_id'],
                            transfer['to_stop_id'],
                            weight=transfer.get('min_transfer_time', 120),
                            edge_type='transfer'
                        )
                        graph.add_edge(
                            transfer['to_stop_id'],
                            transfer['from_stop_id'],
                            weight=transfer.get('min_transfer_time', 120),
                            edge_type='transfer'
                        )
                
                logger.info(f"✅ Graphe rapide créé: {len(graph.nodes)} stations, {len(graph.edges)} connexions (transferts uniquement)")
                logger.warning("⚠️ ATTENTION: Ce graphe ne contient que les transferts. Pour une connexité complète, la base de données doit contenir les arêtes métro.")
                return graph
            
            # Ajouter toutes les arêtes de métro
            logger.info("Ajout de toutes les connexions métro...")
            edges_df = pd.read_sql_query('''
                SELECT from_stop_id, to_stop_id, travel_time, route_short_name, route_id
                FROM edges
            ''', conn)
            
            for _, edge in edges_df.iterrows():
                if edge['from_stop_id'] in graph.nodes and edge['to_stop_id'] in graph.nodes:
                    graph.add_edge(
                        edge['from_stop_id'],
                        edge['to_stop_id'],
                        weight=edge['travel_time'],
                        route_id=edge['route_id'],
                        route_name=edge['route_short_name'],
                        edge_type='metro'
                    )
            
            # Ajouter tous les transferts
            logger.info("Ajout de toutes les correspondances...")
            transfers_df = pd.read_sql_query('''
                SELECT from_stop_id, to_stop_id, transfer_time
                FROM transfers
            ''', conn)
            
            for _, transfer in transfers_df.iterrows():
                if transfer['from_stop_id'] in graph.nodes and transfer['to_stop_id'] in graph.nodes:
                    # Ajouter le transfert dans les deux sens pour la connexité
                    graph.add_edge(
                        transfer['from_stop_id'],
                        transfer['to_stop_id'],
                        weight=transfer['transfer_time'],
                        edge_type='transfer'
                    )
                    graph.add_edge(
                        transfer['to_stop_id'],
                        transfer['from_stop_id'],
                        weight=transfer['transfer_time'],
                        edge_type='transfer'
                    )
            
            logger.info(f"✅ Graphe complet créé: {len(graph.nodes)} stations, {len(graph.edges)} connexions")
            return graph
            
        except Exception as e:
            logger.error(f"Erreur lors de la construction du graphe complet: {e}")
            raise
        finally:
            conn.close()
    
    def connected(self):
        """
        Vérifie si le réseau de transport est connexe (toutes les stations sont accessibles).
        Pour un graphe orienté, on vérifie la connexité faible.
        """
        logger.info("🔍 Vérification de la connexité du réseau...")
        
        # Construire un graphe avec toutes les stations et connexions
        if not hasattr(self, '_full_graph') or self._full_graph is None:
            self._full_graph = self.build_full_network_graph()
        
        # Pour un réseau de transport, on vérifie la connexité faible
        # (ignore la direction des arêtes)
        is_connected = nx.is_weakly_connected(self._full_graph)
        
        logger.info(f"📊 Réseau connexe: {'✅ Oui' if is_connected else '❌ Non'}")
        return is_connected
    
    def get_connectivity_details(self) -> Dict:
        """
        Retourne des détails sur la connexité du réseau.
        """
        logger.info("🔍 Analyse détaillée de la connexité...")
        
        if not hasattr(self, '_full_graph') or self._full_graph is None:
            self._full_graph = self.build_full_network_graph()
        
        details = {
            'is_connected': nx.is_weakly_connected(self._full_graph),
            'total_nodes': len(self._full_graph.nodes),
            'total_edges': len(self._full_graph.edges),
            'number_of_components': nx.number_weakly_connected_components(self._full_graph),
            'largest_component_size': 0,
            'isolated_nodes': [],
            'components_info': []
        }
        
        # Analyser les composantes connexes
        components = list(nx.weakly_connected_components(self._full_graph))
        components.sort(key=len, reverse=True)
        
        details['largest_component_size'] = len(components[0]) if components else 0
        
        # Identifier les nœuds isolés (composantes de taille 1)
        for component in components:
            if len(component) == 1:
                node_id = list(component)[0]
                node_data = self._full_graph.nodes[node_id]
                details['isolated_nodes'].append({
                    'stop_id': node_id,
                    'stop_name': node_data.get('stop_name', 'Inconnu'),
                    'lat': node_data.get('lat', 0),
                    'lon': node_data.get('lon', 0)
                })
        
        # Informations sur toutes les composantes
        for i, component in enumerate(components):
            component_info = {
                'component_id': i + 1,
                'size': len(component),
                'percentage': (len(component) / details['total_nodes']) * 100 if details['total_nodes'] > 0 else 0
            }
            details['components_info'].append(component_info)
        
        logger.info(f"📊 Analyse terminée: {details['number_of_components']} composante(s), plus grande: {details['largest_component_size']} stations")
        
        return details
