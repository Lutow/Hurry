#!/usr/bin/env python3
"""
Script pour mettre à jour les temps de trajet dans metro_graph.db
Calcule des temps réalistes basés sur la distance géographique et les spécificités du métro parisien


Fichier à garder pour montrer à la démo technique comment on a fait
"""

import sqlite3
import math
import logging
from typing import Dict, List, Tuple, Optional

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TravelTimeCalculator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        
        # Paramètres du métro parisien
        self.MIN_TRAVEL_TIME = 60    # Temps minimum entre deux stations (1 minute)
        self.MAX_TRAVEL_TIME = 300   # Temps maximum entre deux stations (5 minutes)
        self.STATION_STOP_TIME = 30  # Temps d'arrêt en station (30 secondes)
        
        # Vitesses moyennes réelles par ligne en km/h (données officielles RATP)
        self.line_speeds_kmh = {
            '1': 35.57,   # Ligne 1 (automatique)
            '2': 32.35,   # Ligne 2
            '3': 35.25,   # Ligne 3
            '3bis': 15.60, # Ligne 3bis (courte et lente)
            '4': 29.04,   # Ligne 4 (automatique mais plus lente que prévu)
            '5': 35.04,   # Ligne 5
            '6': 30.22,   # Ligne 6 (partiellement aérienne)
            '7': 31.89,   # Ligne 7
            '7bis': 25.71, # Ligne 7bis (embranchement)
            '8': 32.64,   # Ligne 8
            '9': 33.60,   # Ligne 9
            '10': 30.52,  # Ligne 10
            '11': 29.08,  # Ligne 11
            '12': 30.21,  # Ligne 12
            '13': 32.40,  # Ligne 13
            '14': 49.41,  # Ligne 14 (la plus rapide, automatique)
        }
        
        # Vitesse par défaut pour les lignes non reconnues
        self.DEFAULT_SPEED_KMH = 32.0  # Moyenne approximative
    
    def connect(self):
        """Établit la connexion à la base de données"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
            logger.info(f"Connexion établie à {self.db_path}")
        except Exception as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            raise
    
    def close(self):
        """Ferme la connexion à la base de données"""
        if self.conn:
            self.conn.close()
            logger.info("Connexion fermée")
    
    def examine_database_structure(self):
        """Examine la structure de la base de données"""
        cursor = self.conn.cursor()
        
        # Lister toutes les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"Tables trouvées: {[table[0] for table in tables]}")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            logger.info(f"Colonnes de {table_name}: {[col[1] for col in columns]}")
            
            # Compter les lignes
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"Nombre de lignes dans {table_name}: {count}")
            
            # Afficher quelques exemples
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            examples = cursor.fetchall()
            if examples:
                logger.info(f"Exemples de {table_name}:")
                for example in examples:
                    logger.info(f"  {dict(example)}")
        
        return [table[0] for table in tables]
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcule la distance géodésique entre deux points en kilomètres
        """
        R = 6371.0  # Rayon de la Terre en km
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def calculate_travel_time(self, distance_km: float, route_short_name: str = None) -> int:
        """
        Calcule le temps de trajet en secondes basé sur la distance et la vitesse spécifique de la ligne
        """
        if distance_km <= 0:
            return self.MIN_TRAVEL_TIME
        
        # Déterminer la vitesse selon la ligne
        if route_short_name and route_short_name in self.line_speeds_kmh:
            speed_kmh = self.line_speeds_kmh[route_short_name]
            logger.debug(f"Ligne {route_short_name}: vitesse {speed_kmh} km/h")
        else:
            speed_kmh = self.DEFAULT_SPEED_KMH
            if route_short_name:
                logger.debug(f"Ligne {route_short_name} inconnue, vitesse par défaut {speed_kmh} km/h")
        
        # Calcul du temps de trajet (sans arrêt)
        travel_time_hours = distance_km / speed_kmh
        travel_time_seconds = travel_time_hours * 3600
        
        # Ajouter le temps d'arrêt en station
        total_time = travel_time_seconds + self.STATION_STOP_TIME
        
        # Appliquer les limites min/max
        total_time = max(self.MIN_TRAVEL_TIME, min(self.MAX_TRAVEL_TIME, total_time))
        
        return int(total_time)
    
    def get_stops_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """Récupère les coordonnées de toutes les stations"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT stop_id, stop_lat, stop_lon FROM stops")
        stops = cursor.fetchall()
        
        coordinates = {}
        for stop in stops:
            stop_id, lat, lon = stop
            if lat is not None and lon is not None:
                coordinates[stop_id] = (float(lat), float(lon))
        
        logger.info(f"Coordonnées récupérées pour {len(coordinates)} stations")
        return coordinates
    
    def update_travel_times(self, dry_run: bool = True):
        """
        Met à jour les temps de trajet dans la base de données
        """
        cursor = self.conn.cursor()
        
        # Vérifier d'abord quelle table contient les arêtes
        tables = self.examine_database_structure()
        
        # Chercher la table qui contient travel_time
        edge_table = None
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            if 'travel_time' in columns:
                edge_table = table
                logger.info(f"Table des arêtes trouvée: {edge_table}")
                break
        
        if not edge_table:
            logger.error("Aucune table avec un champ 'travel_time' trouvée")
            return
        
        # Récupérer les coordonnées des stations
        coordinates = self.get_stops_coordinates()
        
        # Récupérer toutes les arêtes
        cursor.execute(f"SELECT * FROM {edge_table}")
        edges = cursor.fetchall()
        
        logger.info(f"Traitement de {len(edges)} arêtes...")
        
        updates = []
        statistics = {
            'updated': 0,
            'no_coordinates': 0,
            'total': len(edges)
        }
        
        for edge in edges:
            edge_dict = dict(edge)
            
            # Identifier les colonnes source et destination
            from_stop = None
            to_stop = None
            route_info = None
            
            # Chercher les colonnes qui correspondent aux stations
            for key, value in edge_dict.items():
                if key.lower() in ['from_stop', 'from_stop_id', 'stop_id', 'source']:
                    from_stop = value
                elif key.lower() in ['to_stop', 'to_stop_id', 'destination', 'dest']:
                    to_stop = value
                elif key.lower() in ['route_short_name', 'route_id', 'line']:
                    route_info = value
            
            if not from_stop or not to_stop:
                # Essayer d'autres approches pour identifier les stations
                logger.warning(f"Impossible d'identifier les stations pour l'arête: {edge_dict}")
                continue
            
            # Vérifier que nous avons les coordonnées
            if from_stop not in coordinates or to_stop not in coordinates:
                statistics['no_coordinates'] += 1
                continue
            
            # Calculer la distance
            lat1, lon1 = coordinates[from_stop]
            lat2, lon2 = coordinates[to_stop]
            distance_km = self.haversine_distance(lat1, lon1, lat2, lon2)
            
            # Calculer le nouveau temps de trajet
            new_travel_time = self.calculate_travel_time(distance_km, route_info)
            
            # Identifier la clé primaire pour la mise à jour
            primary_key_conditions = []
            for key, value in edge_dict.items():
                if key.lower() in ['id', 'edge_id', 'rowid']:
                    primary_key_conditions.append(f"{key} = ?")
                    break
            
            if not primary_key_conditions:
                # Utiliser toutes les colonnes pour identifier l'arête
                primary_key_conditions = [f"{key} = ?" for key in edge_dict.keys() if key != 'travel_time']
                condition_values = [value for key, value in edge_dict.items() if key != 'travel_time']
            else:
                condition_values = [edge_dict[key] for key in edge_dict.keys() if key.lower() in ['id', 'edge_id', 'rowid']]
            
            updates.append((new_travel_time, condition_values, primary_key_conditions))
            statistics['updated'] += 1
            
            if statistics['updated'] % 100 == 0:
                logger.info(f"Traité {statistics['updated']}/{statistics['total']} arêtes...")
        
        logger.info(f"Statistiques: {statistics}")
        
        if dry_run:
            logger.info("Mode DRY RUN - Aucune modification effectuée")
            logger.info(f"Exemples de mises à jour qui seraient effectuées:")
            for i, (new_time, conditions, _) in enumerate(updates[:5]):
                logger.info(f"  Arête {i+1}: nouveau temps = {new_time}s")
        else:
            # Effectuer les mises à jour
            logger.info("Application des mises à jour...")
            for new_time, condition_values, primary_key_conditions in updates:
                condition_str = " AND ".join(primary_key_conditions)
                query = f"UPDATE {edge_table} SET travel_time = ? WHERE {condition_str}"
                cursor.execute(query, [new_time] + condition_values)
            
            self.conn.commit()
            logger.info(f"✅ {len(updates)} arêtes mises à jour avec succès!")

def main():
    """Fonction principale"""
    import os
    
    # Chemin vers la base de données
    db_path = os.path.join("backend", "graph", "IDFM-gtfs_metro_pkl", "metro_graph.db")
    
    if not os.path.exists(db_path):
        logger.error(f"Base de données non trouvée: {db_path}")
        return
    
    calculator = TravelTimeCalculator(db_path)
    
    try:
        calculator.connect()
        
        # D'abord examiner la structure
        logger.info("=== EXAMEN DE LA STRUCTURE DE LA BASE ===")
        calculator.examine_database_structure()
        
        # Ensuite faire une simulation
        logger.info("\n=== SIMULATION DES MISES À JOUR ===")
        calculator.update_travel_times(dry_run=True)
        
        # Demander confirmation pour appliquer les changements
        print("\nVoulez-vous appliquer ces changements à la base de données? (oui/non): ", end="")
        response = input().strip().lower()
        
        if response in ['oui', 'o', 'yes', 'y']:
            logger.info("\n=== APPLICATION DES MISES À JOUR ===")
            calculator.update_travel_times(dry_run=False)
            logger.info("✅ Mise à jour terminée avec succès!")
        else:
            logger.info("❌ Mise à jour annulée par l'utilisateur.")
        
    except Exception as e:
        logger.error(f"Erreur: {e}")
    finally:
        calculator.close()

if __name__ == "__main__":
    main()
