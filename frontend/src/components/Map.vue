<template>
  <div id="map" style="height: 100vh"></div>
</template>

<script setup>
import { onMounted } from 'vue';
import L from 'leaflet';

onMounted(async () => {
  const map = L.map('map').setView([48.8566, 2.3522], 12); // Paris coords

    setTimeout(() => {
    map.invalidateSize();
  }, 100)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const res = await fetch('http://localhost:8000/geo/stops');
  const geojson = await res.json();

  L.geoJSON(geojson, {
    onEachFeature: (feature, layer) => {
      layer.bindPopup(feature.properties.name || feature.properties.id);
    }
  }).addTo(map);
});
</script>
