import networkx as nx
import pandas as pd
from datetime import datetime, timedelta
import os
import traceback

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
            print(f"Chargé {len(self.stops)} arrêts depuis {data_path}/stops.pkl")
            print(f"Colonnes disponibles: {self.stops.columns.tolist()}")
        except Exception as e:
            print(f"❌ Erreur lors du chargement de stops.pkl: {str(e)}")
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
                print("❌ self.stops est vide, impossible de filtrer")
                return graph
                
            # Vérifier si les colonnes requises existent
            required_cols = ['stop_lat', 'stop_lon', 'stop_id']
            for col in required_cols:
                if col not in self.stops.columns:
                    print(f"❌ Colonne {col} manquante dans stops.pkl")
                    return graph
                    
            print(f"Filtrage des arrêts entre [{lat_min},{lat_max}] lat et [{lon_min},{lon_max}] lon")
            
            # Filtrer les stops par zone géographique (filtrage précoce)
            zone_stops = self.stops[
                (self.stops['stop_lat'] >= lat_min) & 
                (self.stops['stop_lat'] <= lat_max) & 
                (self.stops['stop_lon'] >= lon_min) & 
                (self.stops['stop_lon'] <= lon_max)
            ]
            
            print(f"Trouvé {len(zone_stops)} arrêts dans la zone")
            
            # Si pas de stations dans la zone, renvoyer un graphe vide
            if zone_stops.empty:
                print("⚠️ Aucune station trouvée dans la zone demandée")
                return graph
                
            # Charger uniquement les données nécessaires
            try:
                transfers = pd.read_pickle(f"{self.data_path}/transfers.pkl")
                print(f"Chargé {len(transfers)} transferts")
            except Exception as e:
                print(f"❌ Erreur lors du chargement des transferts: {str(e)}")
                transfers = pd.DataFrame()
                
            return self._build_graph_from_stops(zone_stops, transfers)
                
        except Exception as e:
            print(f"❌ Erreur lors du filtrage des arrêts: {str(e)}")
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
                    print(f"❌ Erreur lors de l'ajout du nœud {stop.get('stop_id', 'inconnu')}: {str(e)}")
            
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
                        print(f"Filtré {len(filtered_transfers)} transferts dans la zone")
                    except Exception as e:
                        print(f"❌ Erreur lors du filtrage des transferts: {str(e)}")
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
                            print(f"❌ Erreur lors de l'ajout de l'arête: {str(e)}")
                except Exception as e:
                    print(f"❌ Erreur lors du traitement des transferts: {str(e)}")
            
            print(f"Graphe final: {len(graph.nodes)} nœuds et {len(graph.edges)} arêtes")
            return graph
            
        except Exception as e:
            print(f"❌ Erreur lors de la construction du graphe: {str(e)}")
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
            print(f"❌ Erreur lors de la construction du graphe complet: {str(e)}")
            print(traceback.format_exc())
            return nx.DiGraph()
                
        return self._graph
