import geojson


def graph_nodes_to_geojson(graph):
    features = []

    for node_id, data in graph.nodes(data=True):
        lat = data.get("lat")
        lon = data.get("lon")

        if lat is not None and lon is not None:
            point = geojson.Point((lon, lat))
            feature = geojson.Feature(
                geometry=point,
                properties={
                    "id": node_id,
                    "name": data.get("stop_name", ""),
                    "accessibility": data.get("wheelchair_accessible", None)
                }
            )
            features.append(feature)

    return geojson.FeatureCollection(features)
