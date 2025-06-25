import geojson
from collections import defaultdict


def graph_nodes_to_geojson(graph):
    """
    Convertit un graphe NetworkX en GeoJSON pour l'affichage sur une carte.
    
    Args:
        graph (nx.DiGraph): Graphe contenant les nœuds à convertir
        
    Returns:
        dict: Objet GeoJSON contenant les stations
    """
    try:
        print(f"Conversion en GeoJSON de {len(graph.nodes)} nœuds")
        grouped = defaultdict(list)
        
        # Vérifier que le graphe n'est pas vide
        if len(graph.nodes) == 0:
            print("⚠️ Le graphe est vide, retour d'un GeoJSON vide")
            return geojson.FeatureCollection([])
        
        # Regroupement par nom de station
        for node_id, data in graph.nodes(data=True):
            try:
                # D'abord chercher stop_name, sinon utiliser l'ID comme nom par défaut
                name = data.get("stop_name", "") or str(node_id)
                grouped[name].append(data)
            except Exception as e:
                print(f"❌ Erreur lors du traitement du nœud {node_id}")
                continue

        features = []
        for name, nodes in grouped.items():
            try:
                # Récupérer les coordonnées lat/lon
                lats = []
                lons = []
                for n in nodes:
                    if "lat" in n:
                        lats.append(n["lat"])
                    elif "stop_lat" in n:
                        lats.append(n["stop_lat"])
                        
                    if "lon" in n:
                        lons.append(n["lon"])
                    elif "stop_lon" in n:
                        lons.append(n["stop_lon"])
                
                if not lats or not lons:
                    continue

                avg_lat = sum(lats) / len(lats)
                avg_lon = sum(lons) / len(lons)
                
                point = geojson.Point((avg_lon, avg_lat))
                
                # Construire un dictionnaire de propriétés pour le GeoJSON
                properties = {"name": name}
                
                # Copier tous les attributs utiles du premier nœud
                if nodes:
                    for attr in [
                        "accessibility", "wheelchair_boarding", "platform_code", 
                        "stop_timezone", "parent_station", "zone_id", "location_type",
                        "stop_id"
                    ]:
                        val = nodes[0].get(attr)
                        if val is not None:
                            properties[attr] = val
                
                # Filtrer les propriétés None
                properties = {k: v for k, v in properties.items() if v is not None}
                
                # Créer la feature GeoJSON
                feature = geojson.Feature(
                    geometry=point,
                    properties=properties
                )
                features.append(feature)
                
            except Exception as e:
                print(f"❌ Erreur lors du traitement de la station '{name}'")
                continue
        
        print(f"Génération de {len(features)} features GeoJSON")
        return geojson.FeatureCollection(features)
        
    except Exception as e:
        print(f"❌ Erreur lors de la conversion en GeoJSON: {e}")
        import traceback
        traceback.print_exc()
        return geojson.FeatureCollection([])
