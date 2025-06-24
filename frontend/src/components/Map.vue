<template>
  <div id="map"></div>
</template>

<script setup>
import { onMounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

onMounted(async () => {
  const map = L.map('map').setView([48.8566, 2.3522], 12)

  // Vérification DOM
  setTimeout(() => {
    map.invalidateSize()
  }, 300)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)

  try {
    const res = await fetch('http://localhost:8000/geo/stops')
    const geojson = await res.json()

    L.geoJSON(geojson, {
      onEachFeature: (feature, layer) => {
        layer.bindPopup(feature.properties.name || feature.properties.id)
      }
    }).addTo(map)
  } catch (error) {
    console.error("Erreur lors du chargement des données GeoJSON:", error)
  }
})
</script>

<style scoped>
#map {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}
</style>
