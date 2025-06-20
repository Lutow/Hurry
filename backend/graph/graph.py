import pandas as pd
import networkx as nx

'''
Charger les fichiers pickle du GTFS métro
'''
feed_path = "IDFM-gtfs_metro_pkl"


routes = pd.read_pickle(f"{feed_path}/routes.pkl")
trips = pd.read_pickle(f"{feed_path}/trips.pkl")
stop_times = pd.read_pickle(f"{feed_path}/stop_times.pkl")
stops = pd.read_pickle(f"{feed_path}/stops.pkl")
transfers = pd.read_pickle(f"{feed_path}/transfers.pkl")


class Ligne:
    def __init__(self, route_short_name, route_type=1):
        self.route_short_name = route_short_name
        self.route = routes
        self.route_type = route_type
        self.trips = trips
        self.stops = stops
        self.stop_times = stop_times

'''
Faire jointure avec Trips utilisant route_id, Trips join stop_times en utilisant trip_id et stop_times join stops en utilisant stop_id
(voir cleaning.py)
On peut ainsi extraire tous les arrêts d'une ligne ainsi que leur coordonnés (lat, lon) et d'autres informations utiles.
'''



