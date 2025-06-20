import pandas as pd

# 📁 Charger les fichiers pickle du GTFS métro
feed_path = "IDFM-gtfs_metro_pkl"

routes = pd.read_pickle(f"{feed_path}/routes.pkl")
trips = pd.read_pickle(f"{feed_path}/trips.pkl")
stop_times = pd.read_pickle(f"{feed_path}/stop_times.pkl")
stops = pd.read_pickle(f"{feed_path}/stops.pkl")

# 📌 Étape 1 : Trouver la ligne 3 du métro
ligne3 = routes[(routes["route_short_name"] == "3") & (routes["route_type"] == 1)]

print(ligne3)
if ligne3.empty:
    raise Exception("❌ Ligne 3 (métro) non trouvée dans les données.")

route_id = ligne3.iloc[0]["route_id"]
print(f"✅ Ligne 3 trouvée avec route_id = {route_id}")

# 📌 Étape 2 : Récupérer les trips de cette ligne
trips_ligne3 = trips[trips["route_id"] == route_id]
if trips_ligne3.empty:
    raise Exception("❌ Aucun trip trouvé pour la ligne 3.")

# 📌 Étape 3 : Identifier le trip ayant le plus d'arrêts
stops_ligne3 = stop_times[stop_times["trip_id"].isin(trips_ligne3["trip_id"])]
trip_counts = stops_ligne3.groupby("trip_id").size()
best_trip_id = trip_counts.idxmax()
print(f"🚀 Trip le plus complet : {best_trip_id} avec {trip_counts.max()} arrêts")

# 📌 Étape 4 : Extraire les arrêts de ce trip
trip_stops = stops_ligne3[stops_ligne3["trip_id"] == best_trip_id].sort_values("stop_sequence")

# 📌 Étape 5 : Fusion avec les coordonnées des arrêts
merged = trip_stops.merge(stops, on="stop_id")[["stop_sequence", "stop_name", "stop_lat", "stop_lon"]]
merged = merged.drop_duplicates("stop_sequence").reset_index(drop=True)

# 📌 Résultat final
print("\n🚇 Liste complète des arrêts de la ligne 3 :")
print(merged.to_string(index=False))
