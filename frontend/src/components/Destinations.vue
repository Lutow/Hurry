<template>
  <div class="explore-paris">
    <div class="explore-header">
      <h3>🏛️ Explorer Paris</h3>
      <p>Découvrez les monuments emblématiques de la capitale</p>
    </div>
    <div class="landmark-grid">
      <div
        v-for="place in landmarks"
        :key="place.name"
        class="landmark-card"
        @click="selectLandmark(place)"
      >
        <img :src="place.image" :alt="place.name" loading="lazy"/>
        <div class="landmark-info">
          <div class="landmark-name">{{ place.name }}</div>
          <div class="landmark-station">📍 {{ place.nearestStation }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineEmits } from 'vue'
import tourEiffel from '../assets/tour-eiffel-paris.webp'
import louvre from '../assets/cour-napoleon-et-pyramide.webp'
import notreDame from '../assets/Notre-Dame.webp'
import arcTriomphe from '../assets/arc-de-triomphe-france-jb24.webp'
import sacreCoeur from '../assets/sacre-coeur.webp'
import pantheon from '../assets/Pantheon-Paris.webp'

const emit = defineEmits(['selectDestination'])

const landmarks = [
  {
    name: "Tour Eiffel",
    image: tourEiffel,
    nearestStation: "Bir-Hakeim"
  },
  {
    name: "Louvre",
    image: louvre,
    nearestStation: "Palais Royal - Musée du Louvre"
  },
  {
    name: "Notre-Dame",
    image: notreDame,
    nearestStation: "Cité"
  },
  {
    name: "Arc de Triomphe",
    image: arcTriomphe,
    nearestStation: "Charles de Gaulle - Étoile"
  },
  {
    name: "Sacré-Cœur",
    image: sacreCoeur,
    nearestStation: "Pigalle"
  },
  {
    name: "Panthéon",
    image: pantheon,
    nearestStation: "Cardinal Lemoine"
  }
]

function selectLandmark(place) {
  emit('selectDestination', place.nearestStation)
}
</script>

<style scoped>
.explore-paris {
  padding: 1rem;
  color: white;
}

.explore-header {
  text-align: center;
  margin-bottom: 2rem;
}

.explore-header h3 {
  color: #2ecc71;
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.explore-header p {
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
  font-size: 0.9rem;
}

.landmark-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1.5rem;
  justify-items: center;
}

.landmark-card {
  width: 140px;
  cursor: pointer;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.landmark-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

.landmark-card img {
  width: 100%;
  height: 100px;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.landmark-card:hover img {
  transform: scale(1.05);
}

.landmark-info {
  padding: 0.75rem;
}

.landmark-name {
  text-align: center;
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.landmark-station {
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.75rem;
  font-style: italic;
}

@media (max-width: 480px) {
  .landmark-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }
  
  .landmark-card {
    width: 120px;
  }
}
</style>
