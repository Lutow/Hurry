#!/usr/bin/env python3
"""
Construction rapide de la base de données avec arêtes optimisées.
"""

import sys
import os
import sqlite3
import pandas as pd
import numpy as np
import logging
from collections import defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_optimized_database():
    """
    Construit la base de données de façon optimisée en évitant les comparaisons lentes.
    """
    
    data_path = "backend/graph/IDFM-gtfs_metro_pkl"
    db_path = f"{data_path}/metro_graph.db"
    
    print("🚀 CONSTRUCTION OPTIMISEE DE LA BASE DE DONNEES")
    print("=" * 60)
    
    try:
        # Supprimer l'ancienne base
        if os.path.exists(db_path):
            os.remove(db_path)
            print("🗑️ Ancienne base supprimee")
        
        # Charger les données
        print("📂 Chargement des donnees...")
        stops = pd.read_pickle(f"{data_path}/stops.pkl")
        transfers = pd.read_pickle(f"{data_path}/transfers.pkl")
        trips = pd.read_pickle(f"{data_path}/trips.pkl")
        stop_times = pd.read_pickle(f"{data_path}/stop_times.pkl")
        routes = pd.read_pickle(f"{data_path}/routes.pkl")
        
        print(f"✅ Données chargees :")
        print(f"   - {len(stops)} stations")
        print(f"   - {len(transfers)} transferts")
        print(f"   - {len(trips)} trips")
        print(f"   - {len(stop_times)} stop_times")
        print(f"   - {len(routes)} routes")
        
        # Créer la base de données
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Créer les tables
        print("🏗️ Création des tables...")
        cursor.execute('''
            CREATE TABLE stops (
                stop_id TEXT PRIMARY KEY,
                stop_name TEXT,
                stop_lat REAL,
                stop_lon REAL,
                wheelchair_boarding INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE edges (
                from_stop_id TEXT,
                to_stop_id TEXT,
                travel_time REAL,
                route_short_name TEXT,
                route_id TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE transfers (
                from_stop_id TEXT,
                to_stop_id TEXT,
                transfer_time REAL
            )
        ''')
        
        # Créer les index
        cursor.execute('CREATE INDEX idx_edges_from ON edges(from_stop_id)')
        cursor.execute('CREATE INDEX idx_edges_to ON edges(to_stop_id)')
        
        # Filtrer pour ne garder qu'une station unique par nom (suppression des doublons)
        stops_unique = stops.drop_duplicates(subset=["stop_name"]).copy()
        print("📍 Insertion des stations uniques...")
        stops_data = [
            (
                row['stop_id'],
                row['stop_name'],
                row['stop_lat'],
                row['stop_lon'],
                row.get('wheelchair_boarding', 0)
            )
            for _, row in stops_unique.iterrows()
        ]
        cursor.executemany('''
            INSERT INTO stops (stop_id, stop_name, stop_lat, stop_lon, wheelchair_boarding)
            VALUES (?, ?, ?, ?, ?)
        ''', stops_data)
        print(f"✅ {len(stops_data)} stations uniques insérées")
        
        # Insérer les transferts
        print("🔄 Insertion des transferts...")
        transfers_data = [
            (
                row['from_stop_id'],
                row['to_stop_id'],
                row.get('min_transfer_time', 120)
            )
            for _, row in transfers.iterrows()
        ]
        
        cursor.executemany('''
            INSERT INTO transfers (from_stop_id, to_stop_id, transfer_time)
            VALUES (?, ?, ?)
        ''', transfers_data)
        
        print(f"✅ {len(transfers_data)} transferts insérés")
        
        # Optimisation pour les arêtes : créer un dictionnaire trip_id -> stop_times
        print("🚇 Préparation des données stop_times...")
        
        # Grouper les stop_times par trip_id pour éviter les filtres répétés
        stop_times_by_trip = defaultdict(list)
        for _, row in stop_times.iterrows():
            stop_times_by_trip[row['trip_id']].append({
                'stop_id': row['stop_id'],
                'stop_sequence': row['stop_sequence'],
                'arrival_time': row['arrival_time'],
                'departure_time': row['departure_time']
            })
        
        # Trier chaque groupe par stop_sequence
        for trip_id in stop_times_by_trip:
            stop_times_by_trip[trip_id].sort(key=lambda x: x['stop_sequence'])
        
        print(f"✅ Stop_times préparés pour {len(stop_times_by_trip)} trips")
        
        # Pré-grouper les stop_times par trip_id pour accélérer la boucle
        stop_times_by_trip = {k: v.sort_values('stop_sequence') for k, v in stop_times.groupby('trip_id')}
        # Création d'un mapping nom de station -> stop_id principal (pour les arêtes)
        stop_name_to_id = {row['stop_name']: row['stop_id'] for _, row in stops_unique.iterrows()}
        # Créer le mapping route_id -> route_short_name
        route_names = {row['route_id']: row['route_short_name'] for _, row in routes.iterrows()}
        print("🚇 Traitement des connexions métro (stations uniques)...")
        edges_set = set()
        processed_count = 0
        for _, trip in trips.iterrows():
            trip_id = trip['trip_id']
            route_id = trip['route_id']
            route_name = route_names.get(route_id, '')
            trip_stops = stop_times_by_trip.get(trip_id, None)
            if trip_stops is None:
                continue
            stop_names_seq = trip_stops['stop_id'].map(lambda sid: stops.loc[stops['stop_id'] == sid, 'stop_name'].values[0] if sid in stops['stop_id'].values else None)
            stop_names_seq = stop_names_seq.dropna().tolist()
            for i in range(len(stop_names_seq) - 1):
                from_name = stop_names_seq[i]
                to_name = stop_names_seq[i + 1]
                if from_name != to_name:
                    from_id = stop_name_to_id[from_name]
                    to_id = stop_name_to_id[to_name]
                    edge_tuple = (from_id, to_id, 120, route_name, route_id)
                    if (from_id, to_id) not in [(e[0], e[1]) for e in edges_set]:
                        edges_set.add(edge_tuple)
            processed_count += 1
            if processed_count % 5000 == 0:
                print(f"📈 Traite {processed_count}/{len(trips)} trips...")
        edges_data = list(edges_set)
        print(f"✅ {len(edges_data)} aretes preparees entre stations uniques")
        
        # Insérer les arêtes par batch
        print("💾 Insertion des arêtes...")
        batch_size = 10000
        for i in range(0, len(edges_data), batch_size):
            batch = edges_data[i:i+batch_size]
            cursor.executemany('''
                INSERT INTO edges (from_stop_id, to_stop_id, travel_time, route_short_name, route_id)
                VALUES (?, ?, ?, ?, ?)
            ''', batch)
            
            if i % (batch_size * 5) == 0:
                print(f"📈 Insere {i + len(batch)}/{len(edges_data)} arêtes...")
        
        # Commit et vérification finale
        conn.commit()
        
        cursor.execute('SELECT COUNT(*) FROM stops')
        stops_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM edges')
        edges_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM transfers')
        transfers_count = cursor.fetchone()[0]
        
        print("=" * 60)
        print("✅ BASE DE DONNÉES CRÉÉE AVEC SUCCÈS !")
        print(f"📊 Contenu final :")
        print(f"   - {stops_count:,} stations")
        print(f"   - {edges_count:,} aretes métro")
        print(f"   - {transfers_count:,} transferts")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_connectivity():
    """
    Test la connexité avec la nouvelle base de données.
    """
    print("\n🔍 TEST DE CONNEXITE AVEC LA NOUVELLE BASE")
    print("=" * 60)
    
    try:
        # S'assurer que le dossier racine est dans le path pour l'import
        import os
        import sys
        # Calcul du chemin racine du projet (dossier contenant backend)
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        print(f"sys.path = {sys.path}")
        from backend.graph.ultra_optimized_graph import UltraOptimizedGraphGTFS
        
        # Initialiser le graphe
        graph_manager = UltraOptimizedGraphGTFS('backend/graph/IDFM-gtfs_metro_pkl')
        
        # Tester la connexité
        print("🔍 Verification de la connexité...")
        is_connected = graph_manager.connected()
        
        print(f"📊 Résultat: {'✅ RESEAU CONNEXE' if is_connected else '❌ RESEAU NON CONNEXE'}")
        
        if is_connected:
            print("🎉 Toutes les stations sont accessibles entre elles !")
        else:
            # Obtenir les détails
            details = graph_manager.get_connectivity_details()
            print(f"📊 {details['number_of_components']} composantes connexes")
            print(f"📊 Plus grande composante: {details['largest_component_size']} stations")
            
            if details['isolated_nodes']:
                print(f"🏝️ {len(details['isolated_nodes'])} stations isolees")
        
        return is_connected
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 1. Construire la base optimisée
    success = build_optimized_database()
    
    if success:
        # 2. Tester la connexité
        test_connectivity()
    else:
        print("❌ Echec de la construction de la base")
