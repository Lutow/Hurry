import networkx as nx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import traceback
from backend.utils import log_info, log_warning, log_error

class OptimizedGraphGTFS:
    """
    Version optimisée de GrapheGTFS qui permet le chargement rapide et filtré des stations.
    """
    
    def __init__(self, data_path: str):
        """
        Initialise le graphe avec le chemin des données GTFS.
        
        Args:
            data_path (str): Chemin vers les fichiers pickles GTFS
        """
        self.data_path = data_path
        try:
            self.stops = pd.read_pickle(f"{data_path}/stops.pkl")
            log_info(f"Charge {len(self.stops)} arrets depuis {data_path}/stops.pkl")
            print(f"Colonnes disponibles: {self.stops.columns.tolist()}")
        except Exception as e:
            log_error(f"Erreur lors du chargement de stops.pkl: {str(e)}")
            print(traceback.format_exc())
            self.stops = pd.DataFrame()
            
        # On ne charge les autres dataframes que lorsque nécessaire
        self._graph = None
    
    def load_graph_for_zone(self, lat_min, lat_max, lon_min, lon_max):
        """
        Charge uniquement les stations dans une zone géographique donnée.
        
        Args:
            lat_min (float): Latitude minimum
            lat_max (float): Latitude maximum
            lon_min (float): Longitude minimum
            lon_max (float): Longitude maximum
            
        Returns:
            nx.DiGraph: Graphe contenant uniquement les stations dans la zone
        """
        # Créer un graphe vide
        graph = nx.DiGraph()
        
        try:
            # Vérifier que les stops ont bien été chargés
            if self.stops.empty:
                log_error("self.stops est vide, impossible de filtrer")
                return graph
                
            # Vérifier si les colonnes requises existent
            required_cols = ['stop_lat', 'stop_lon', 'stop_id']
            for col in required_cols:
                if col not in self.stops.columns:
                    log_error(f"Colonne {col} manquante dans stops.pkl")
                    return graph
                    
            log_info(f"Filtrage des arrets entre [{lat_min},{lat_max}] lat et [{lon_min},{lon_max}] lon")
            
            # Filtrer les stops par zone géographique (filtrage précoce)
            zone_stops = self.stops[
                (self.stops['stop_lat'] >= lat_min) & 
                (self.stops['stop_lat'] <= lat_max) & 
                (self.stops['stop_lon'] >= lon_min) & 
                (self.stops['stop_lon'] <= lon_max)
            ]
            
            log_info(f"Trouve {len(zone_stops)} arrets dans la zone")
            
            # Si pas de stations dans la zone, renvoyer un graphe vide
            if zone_stops.empty:
                log_warning("Aucune station trouvee dans la zone demandee")
                return graph
                
            # Charger uniquement les données nécessaires
            try:
                transfers = pd.read_pickle(f"{self.data_path}/transfers.pkl")
                log_info(f"Charge {len(transfers)} transferts")
            except Exception as e:
                log_error(f"Erreur lors du chargement des transferts: {str(e)}")
                transfers = pd.DataFrame()
                
            return self._build_graph_from_stops(zone_stops, transfers)
                
        except Exception as e:
            log_error(f"Erreur lors du filtrage des arrets: {str(e)}")
            print(traceback.format_exc())
            return graph
        
    def _build_graph_from_stops(self, zone_stops, transfers):
        """
        Construit un graphe à partir des stations filtrées et des transferts.
        
        Args:
            zone_stops (pd.DataFrame): DataFrame contenant les stations dans la zone
            transfers (pd.DataFrame): DataFrame contenant les transferts
            
        Returns:
            nx.DiGraph: Graphe contenant les stations et les transferts
        """
        try:
            # Créer un graphe vide
            graph = nx.DiGraph()
            
            # Ajouter les stations comme nœuds avec toutes leurs métadonnées
            for _, stop in zone_stops.iterrows():
                try:
                    # Collecter toutes les colonnes disponibles
                    node_attrs = {}
                    for col in stop.index:
                        if pd.notna(stop[col]):  # Ignorer les valeurs NaN/NaT/None
                            node_attrs[col] = stop[col]
                    
                    # Renommer certains attributs pour la compatibilité avec le frontend
                    if 'stop_lat' in node_attrs:
                        node_attrs['lat'] = node_attrs['stop_lat']
                    if 'stop_lon' in node_attrs:
                        node_attrs['lon'] = node_attrs['stop_lon']
                    if 'stop_name' in node_attrs:
                        node_attrs['stop_name'] = node_attrs['stop_name']
                    if 'wheelchair_boarding' in node_attrs:
                        node_attrs['accessibility'] = node_attrs['wheelchair_boarding']
                    
                    graph.add_node(stop['stop_id'], **node_attrs)
                except Exception as e:
                    log_error(f"Erreur lors de l'ajout du noeud {stop.get('stop_id', 'inconnu')}: {str(e)}")
            
            # Ajouter les transferts si disponibles
            if not transfers.empty:
                try:
                    # Obtenir la liste des IDs de stations dans le graphe
                    zone_stop_ids = set(zone_stops['stop_id'])
                    
                    # Filtrer les transferts pour n'inclure que ceux entre stations de la zone
                    try:
                        filtered_transfers = transfers[
                            transfers['from_stop_id'].isin(zone_stop_ids) & 
                            transfers['to_stop_id'].isin(zone_stop_ids)
                        ]
                        log_info(f"Filtre {len(filtered_transfers)} transferts dans la zone")
                    except Exception as e:
                        log_error(f"Erreur lors du filtrage des transferts: {str(e)}")
                        filtered_transfers = pd.DataFrame()
                    
                    # Ajouter les transferts comme arêtes
                    for _, transfer in filtered_transfers.iterrows():
                        try:
                            from_stop = transfer['from_stop_id']
                            to_stop = transfer['to_stop_id']
                            
                            if from_stop in graph.nodes and to_stop in graph.nodes:
                                weight = transfer.get('min_transfer_time', 120)
                                graph.add_edge(from_stop, to_stop, weight=weight)
                        except Exception as e:
                            log_error(f"Erreur lors de l'ajout de l'arete: {str(e)}")
                except Exception as e:
                    log_error(f"Erreur lors du traitement des transferts: {str(e)}")
            
            print(f"Graphe final : {len(graph.nodes)} noeuds et {len(graph.edges)} aretes")
            return graph
            
        except Exception as e:
            log_error(f"Erreur lors de la construction du graphe: {str(e)}")
            print(traceback.format_exc())
            return nx.DiGraph()
    
    def get_all_stops_as_graph(self):
        """
        Renvoie un graphe avec toutes les stations mais sans les connexions entre elles.
        Beaucoup plus rapide que la construction complète du graphe.
        
        Returns:
            nx.DiGraph: Graphe avec toutes les stations
        """
        try:
            if self._graph is None:
                # Utiliser notre méthode _build_graph_from_stops avec toutes les stations
                # mais sans les transferts pour être plus rapide
                self._graph = self._build_graph_from_stops(self.stops, pd.DataFrame())
                print(f"Graphe complet construit avec {len(self._graph.nodes)} stations")
                
            return self._graph
            
        except Exception as e:
            log_error(f"Erreur lors de la construction du graphe complet: {str(e)}")
            print(traceback.format_exc())
            return nx.DiGraph()
                
        return self._graph
    
    def build_connectivity_graph(self):
        """
        Construit un graphe optimisé pour l'analyse de connectivité.
        Filtre les doublons de stations et crée un graphe non orienté.
        
        Returns:
            nx.Graph: Un graphe non orienté avec des stations uniques.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Construction d'un graphe non orienté optimisé pour la connectivité...")
        
        # Créer un graphe non orienté
        G = nx.Graph()
        
        # Charger les stations et filtrer les doublons
        stops_df = self.stops.copy()
        
        # Créer un dictionnaire pour éliminer les doublons par nom
        unique_stops = {}
        stop_id_to_unique = {}  # Pour mapper les IDs de tous les arrêts vers les IDs uniques
        
        for _, stop in stops_df.iterrows():
            # Vérifier que location_type existe avant de l'utiliser
            location_type = stop.get('location_type', 0)
            if location_type == 0 or pd.isna(location_type):  # Seulement les arrêts, pas les stations ou valeurs NA
                stop_name = stop['stop_name']
                stop_id = stop['stop_id']
                
                if stop_name not in unique_stops:
                    # C'est la première station avec ce nom
                    unique_stops[stop_name] = {
                        'stop_id': stop_id,
                        'stop_name': stop_name,
                        'stop_lat': stop['stop_lat'],
                        'stop_lon': stop['stop_lon']
                    }
                    stop_id_to_unique[stop_id] = stop_id  # Le même ID
                else:
                    # C'est un doublon, on le mappe vers l'ID unique
                    stop_id_to_unique[stop_id] = unique_stops[stop_name]['stop_id']
        
        # Ajouter les nœuds au graphe
        logger.info(f"Ajout de {len(unique_stops)} stations uniques au graphe...")
        for stop_name, stop_data in unique_stops.items():
            G.add_node(
                stop_data['stop_id'],
                stop_name=stop_data['stop_name'],
                lat=stop_data['stop_lat'],
                lon=stop_data['stop_lon']
            )
        
        # Charger et ajouter les transferts - on utilise maintenant toutes les connexions disponibles
        try:
            transfers_df = pd.read_pickle(f"{self.data_path}/transfers.pkl")
            logger.info(f"Chargé {len(transfers_df)} transferts")
            
            # On garde les connexions entre stations uniques
            added_edges = set()
            edge_count = 0
            
            for _, transfer in transfers_df.iterrows():
                from_id = transfer['from_stop_id']
                to_id = transfer['to_stop_id']
                
                # Convertir vers les IDs uniques si nécessaire
                from_unique = stop_id_to_unique.get(from_id)
                to_unique = stop_id_to_unique.get(to_id)
                
                # Si ces stations ont été mappées à des stations uniques
                if from_unique and to_unique and from_unique != to_unique:  # Éviter les auto-boucles
                    # Identifiant unique pour cette connexion
                    edge_id = tuple(sorted([from_unique, to_unique]))
                    
                    # Si cette connexion n'existe pas encore
                    if edge_id not in added_edges:
                        G.add_edge(from_unique, to_unique, weight=1)
                        added_edges.add(edge_id)
                        edge_count += 1
            
            logger.info(f"Ajouté {edge_count} connexions uniques au graphe")
            
            # Si on n'a pas assez de connexions, essayons avec les trips/stop_times
            if edge_count < 300:  # Seuil arbitraire qui indique un problème
                logger.warning(f"Seulement {edge_count} connexions trouvées, tentative d'enrichissement...")
                try:
                    # Ajoutons aussi les connexions implicites des trajets
                    try:
                        # Essayer de charger les arêtes uniques si disponibles
                        unique_edges = pd.read_pickle(f"{self.data_path}/unique_edges.pkl")
                        logger.info(f"Chargé {len(unique_edges)} arêtes uniques de trajets")
                        
                        edge_enrichment_count = 0
                        # Vérifier le type des données chargées
                        if isinstance(unique_edges, set):
                            logger.info("Les arêtes uniques sont au format set, conversion...")
                            for edge in unique_edges:
                                # Vérifier le format des arêtes
                                if isinstance(edge, tuple) and len(edge) == 2:
                                    from_id, to_id = edge
                                    
                                    # Convertir vers les IDs uniques si nécessaire
                                    from_unique = stop_id_to_unique.get(from_id)
                                    to_unique = stop_id_to_unique.get(to_id)
                                    
                                    if from_unique and to_unique and from_unique != to_unique:
                                        edge_id = tuple(sorted([from_unique, to_unique]))
                                        
                                        if edge_id not in added_edges:
                                            G.add_edge(from_unique, to_unique, weight=1)
                                            added_edges.add(edge_id)
                                            edge_enrichment_count += 1
                        elif hasattr(unique_edges, 'iterrows'):
                            # C'est un DataFrame, on peut utiliser iterrows
                            for _, edge in unique_edges.iterrows():
                                from_id = edge['from_stop_id']
                                to_id = edge['to_stop_id']
                                
                                # Convertir vers les IDs uniques si nécessaire
                                from_unique = stop_id_to_unique.get(from_id)
                                to_unique = stop_id_to_unique.get(to_id)
                                
                                if from_unique and to_unique and from_unique != to_unique:
                                    edge_id = tuple(sorted([from_unique, to_unique]))
                                    
                                    if edge_id not in added_edges:
                                        G.add_edge(from_unique, to_unique, weight=1)
                                        added_edges.add(edge_id)
                                        edge_enrichment_count += 1
                        
                        logger.info(f"Enrichissement: ajouté {edge_enrichment_count} connexions supplémentaires")
                        edge_count += edge_enrichment_count
                    except Exception as e:
                        logger.warning(f"Impossible de charger les arêtes uniques: {e}")
                        
                    # Essayer d'ajouter des connexions basées sur les lignes de métro
                    try:
                        routes_df = pd.read_pickle(f"{self.data_path}/routes.pkl")
                        trips_df = pd.read_pickle(f"{self.data_path}/trips.pkl")
                        stop_times_df = pd.read_pickle(f"{self.data_path}/stop_times.pkl")
                        
                        logger.info("Ajout de connexions basées sur les lignes et trajets...")
                        
                        # Obtenir les trajets par ligne
                        route_trips = {}
                        for _, trip in trips_df.iterrows():
                            route_id = trip['route_id']
                            trip_id = trip['trip_id']
                            
                            if route_id not in route_trips:
                                route_trips[route_id] = []
                            route_trips[route_id].append(trip_id)
                        
                        # Pour chaque ligne, créer des connexions entre stations consécutives
                        line_edge_count = 0
                        for route_id, trips in route_trips.items():
                            # Prendre juste le premier trajet de la ligne comme représentatif
                            if trips:
                                trip_id = trips[0]
                                # Obtenir les arrêts de ce trajet en ordre de séquence
                                trip_stops = stop_times_df[stop_times_df['trip_id'] == trip_id].sort_values('stop_sequence')
                                
                                # Créer des connexions entre arrêts consécutifs
                                prev_stop_id = None
                                for _, stop_time in trip_stops.iterrows():
                                    current_stop_id = stop_time['stop_id']
                                    
                                    if prev_stop_id is not None:
                                        # Convertir vers les IDs uniques
                                        from_unique = stop_id_to_unique.get(prev_stop_id)
                                        to_unique = stop_id_to_unique.get(current_stop_id)
                                        
                                        if from_unique and to_unique and from_unique != to_unique:
                                            edge_id = tuple(sorted([from_unique, to_unique]))
                                            
                                            if edge_id not in added_edges:
                                                G.add_edge(from_unique, to_unique, weight=1, route_id=route_id)
                                                added_edges.add(edge_id)
                                                line_edge_count += 1
                                                
                                    prev_stop_id = current_stop_id
                        
                        logger.info(f"Ajouté {line_edge_count} connexions basées sur les lignes")
                        edge_count += line_edge_count
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'ajout des connexions par ligne: {e}")
                    
                    # Dernier recours: ajouter des connexions basées sur la proximité géographique
                    if edge_count < 300:
                        logger.warning("Ajout de connexions par proximité géographique...")
                        
                        # Créer des connexions pour les stations proches géographiquement
                        proximity_count = 0
                        
                        # Définir une distance maximale plus agressive pour assurer la connectivité
                        max_distance = 800  # 800 mètres
                        
                        for name1, data1 in unique_stops.items():
                            for name2, data2 in unique_stops.items():
                                if name1 != name2:
                                    # Distance approximative en mètres (formule simplifiée)
                                    dx = 111000 * (data1['stop_lon'] - data2['stop_lon']) * \
                                        np.cos(np.radians((data1['stop_lat'] + data2['stop_lat']) / 2))
                                    dy = 111000 * (data1['stop_lat'] - data2['stop_lat'])
                                    distance = np.sqrt(dx**2 + dy**2)
                                    
                                    # Distance adaptative selon le nombre d'arêtes déjà ajoutées
                                    threshold = max_distance if edge_count < 100 else 500
                                    
                                    # Si distance suffisamment faible, ajouter une connexion
                                    if distance < threshold:
                                        edge_id = tuple(sorted([data1['stop_id'], data2['stop_id']]))
                                        if edge_id not in added_edges:
                                            G.add_edge(data1['stop_id'], data2['stop_id'], weight=distance/100)
                                            added_edges.add(edge_id)
                                            proximity_count += 1
                        
                        logger.info(f"Ajouté {proximity_count} connexions par proximité")
                        edge_count += proximity_count
                        
                except Exception as e:
                    logger.error(f"Erreur lors de l'enrichissement des connexions: {e}")
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement des transferts: {e}")
        
        # Forcer la connexité du réseau si nécessaire
        if not nx.is_connected(G) and len(G.nodes) > 0:
            logger.warning("Le graphe n'est toujours pas connexe, connexion des composantes...")
            
            # Identifier les composantes connexes
            components = list(nx.connected_components(G))
            components.sort(key=len, reverse=True)
            
            logger.info(f"Le graphe a {len(components)} composantes connexes")
            largest_component = components[0]
            
            # Pour chaque composante isolée, la connecter à la plus grande
            component_links = 0
            for i in range(1, len(components)):
                component = components[i]
                
                if len(component) > 0:
                    # Prendre un nœud de cette composante
                    node_from_component = list(component)[0]
                    
                    # Trouver le nœud le plus proche dans la plus grande composante
                    min_distance = float('inf')
                    closest_node = None
                    
                    for node_from_largest in largest_component:
                        # Récupérer les coordonnées
                        lat1, lon1 = G.nodes[node_from_component].get('lat', 0), G.nodes[node_from_component].get('lon', 0)
                        lat2, lon2 = G.nodes[node_from_largest].get('lat', 0), G.nodes[node_from_largest].get('lon', 0)
                        
                        # Calculer la distance
                        dx = 111000 * (lon1 - lon2) * np.cos(np.radians((lat1 + lat2) / 2))
                        dy = 111000 * (lat1 - lat2)
                        distance = np.sqrt(dx**2 + dy**2)
                        
                        if distance < min_distance:
                            min_distance = distance
                            closest_node = node_from_largest
                    
                    if closest_node:
                        # Créer une connexion entre les deux composantes
                        edge_id = tuple(sorted([node_from_component, closest_node]))
                        if edge_id not in added_edges:
                            G.add_edge(node_from_component, closest_node, weight=min_distance/100, artificial=True)
                            added_edges.add(edge_id)
                            component_links += 1
            
            logger.info(f"Ajouté {component_links} connexions pour lier les composantes")
        
        logger.info(f"Graphe final : {len(G.nodes)} noeuds et {len(G.edges)} aretes")
        
        # Vérification finale
        is_connected = nx.is_connected(G)
        logger.info(f"Vérification finale - Réseau connexe: {'OUI' if is_connected else 'NON'}")
        
        return G
    
    def connected(self) -> bool:
        """
        Vérifie si le réseau de transport est connexe.
        
        Returns:
            bool: True si le réseau est connexe, False sinon.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Construire un graphe non orienté optimisé
        G = self.build_connectivity_graph()
        
        # Pour un graphe non orienté, on utilise is_connected
        is_connected = nx.is_connected(G)
        
        logger.info(f"[STATISTIQUES] Réseau connexe: {'OUI' if is_connected else 'NON'}")
        return is_connected
    
    def get_connectivity_details(self) -> dict:
        """
        Retourne des détails sur la connexité du réseau.
        
        Returns:
            dict: Un dictionnaire avec les informations de connexité.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("🔍 Analyse détaillée de la connexité...")
        
        # Utiliser le graphe non orienté optimisé
        G = self.build_connectivity_graph()
        
        details = {
            'is_connected': nx.is_connected(G),
            'total_nodes': len(G.nodes),
            'total_edges': len(G.edges),
            'number_of_components': nx.number_connected_components(G),
            'largest_component_size': 0,
            'isolated_nodes': [],
            'components_info': []
        }
        
        # Analyser les composantes connexes
        components = list(nx.connected_components(G))
        components.sort(key=len, reverse=True)
        
        details['largest_component_size'] = len(components[0]) if components else 0
        
        # Identifier les nœuds isolés (composantes de taille 1)
        for component in components:
            if len(component) == 1:
                node_id = list(component)[0]
                node_data = G.nodes[node_id]
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
        
        return details
    
    def build_graph(self):
        """
        Construit un graphe NetworkX à partir des données GTFS.
        
        Returns:
            nx.DiGraph: Le graphe dirigé représentant le réseau de transport.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Construction du graphe optimisé...")
        
        G = nx.DiGraph()
        
        # Ajouter tous les arrêts comme nœuds
        for _, stop in self.stops.iterrows():
            try:
                G.add_node(stop.stop_id, 
                          stop_name=stop.stop_name,
                          lat=stop.stop_lat, 
                          lon=stop.stop_lon)
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout d'un nœud: {e}")
        
        # Charger les correspondances
        try:
            transfers = pd.read_pickle(f"{self.data_path}/transfers.pkl")
            # Ajouter les correspondances comme arêtes
            for _, transfer in transfers.iterrows():
                if transfer.from_stop_id in G and transfer.to_stop_id in G:
                    # Conversion du temps de correspondance en minutes (initialement en secondes)
                    min_transfer_time = transfer.min_transfer_time / 60 if hasattr(transfer, 'min_transfer_time') and transfer.min_transfer_time > 0 else 3
                    
                    G.add_edge(transfer.from_stop_id, 
                              transfer.to_stop_id, 
                              type="transfer", 
                              time=min_transfer_time)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des correspondances: {e}")
        
        self._graph = G
        logger.info(f"Graphe construit: {len(G.nodes)} nœuds, {len(G.edges)} arêtes")
        return G
