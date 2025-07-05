import pandas as pd
import networkx as nx
from datetime import datetime, timedelta
import os
from backend.utils import log_info, log_warning, log_error


'''
Charger les fichiers pickle du GTFS métro
'''

'''
Faire jointure avec Trips utilisant route_id, Trips join stop_times en utilisant trip_id et stop_times join stops en utilisant stop_id
(voir cleaning.py)
On peut ainsi extraire tous les arrêts d'une ligne ainsi que leur coordonnés (lat, lon) et d'autres informations utiles.
'''

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
feed_path = os.path.join(BASE_DIR, "IDFM-gtfs_metro_pkl")


# pickle routes
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

        ligne = self.route[
            (self.route["route_short_name"] == route_short_name) & (self.route["route_type"] == route_type)]

        self.route_id = ligne.iloc[0]["route_id"]
        self.trips_ligne = self.trips[self.trips["route_id"] == self.route_id]

    def get_best_trip_id(self):
        counts = self.stop_times[
            self.stop_times["trip_id"].isin(self.trips_ligne["trip_id"])
        ].groupby("trip_id").size()
        return counts.idxmax()

    def get_stops(self):
        trip_id = self.get_best_trip_id()
        trip_stops = self.stop_times[self.stop_times["trip_id"] == trip_id]
        trip_stops = trip_stops.sort_values("stop_sequence", ascending=False)
        final = trip_stops.merge(self.stops, on="stop_id")
        return final[["stop_sequence", "stop_name", "stop_lat", "stop_lon"]].drop_duplicates(
            "stop_sequence").reset_index(drop=True)


class GrapheGTFS:
    def __init__(self, data_path: str, lignes: list = None):
        """
        Build a GTFS routing graph with stop coordinates and real durations.
        Args:
            data_path (str): Folder containing pickled GTFS data.
            lignes (list): Optional list of LigneGTFS instances to restrict graph to certain lines.
        """
        self.graph = nx.DiGraph()
        self.stops = stops
        self.trips = trips
        self.stop_times = stop_times
        self.routes = routes
        self.transfers = self._safe_read_pickle(f"{data_path}/transfers.pkl")
        self._build_graph(lignes)

    def _safe_read_pickle(self, path):
        try:
            return pd.read_pickle(path)
        except FileNotFoundError:
            return pd.DataFrame()

    def _build_graph(self, lignes=None):
        if lignes:
            route_ids = [l.route_id for l in lignes]
            trips = self.trips[self.trips["route_id"].isin(route_ids)]
        else:
            trips = self.trips

        stop_times = self.stop_times[self.stop_times["trip_id"].isin(trips["trip_id"])]
        stop_lookup = self.stops.set_index("stop_id").to_dict(orient="index")

        for trip_id, group in stop_times.groupby("trip_id"):
            sorted = group.sort_values("stop_sequence")
            prev_row = None
            for _, row in sorted.iterrows():
                stop_id = row["stop_id"]
                stop_info = stop_lookup.get(stop_id)
                if stop_info is None:
                    log_warning(f"Pas d'arret trouve avec l'ID : {stop_id}")
                    continue

                self.graph.add_node(
                    stop_id,
                    stop_name=stop_info["stop_name"],
                    lat=stop_info["stop_lat"],
                    lon=stop_info["stop_lon"],
                    accessibility=stop_info.get("wheelchair_accessible", None),
                )
                if prev_row is not None:
                    dep_time = self._parse_time(prev_row["departure_time"])
                    arr_time = self._parse_time(row["arrival_time"])
                    duration = (arr_time - dep_time).total_seconds()
                    
                    self.graph.add_edge(
                        prev_row["stop_id"],
                        stop_id,
                        weight=duration,
                        trip_id=trip_id
                    )
                    
                prev_row = row

        self._add_transfer_edges()

    def _add_transfer_edges(self):
        if self.transfers.empty:
            return

        for _, row in self.transfers.iterrows():
            from_stop = row["from_stop_id"]
            to_stop = row["to_stop_id"]
            weight = row.get("min_transfer_time", 120)
            self.graph.add_edge(from_stop, to_stop, weight=weight)

    def _parse_time(self, t_str):
        try:
            hours, minutes, seconds = map(int, t_str.split(":"))
            if hours >= 24:
                hours -= 24
                return datetime.strptime(f"{hours}:{minutes}:{seconds}", "%H:%M:%S") + timedelta(days=1)
            return datetime.strptime(t_str, "%H:%M:%S")
        except Exception:
            return datetime.strptime("00:00:00", "%H:%M:%S")

    def get_graph(self):
        return self.graph

    def get_coordinates(self, stop_id):
        node = self.graph.nodes.get(stop_id)
        if node:
            return node["lat"], node["lon"]
        return None, None

    def get_duration(self, from_stop, to_stop):
        return self.graph.edges[from_stop, to_stop]["weight"]
