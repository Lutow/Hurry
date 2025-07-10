<script setup>
import Map from './components/Map.vue'
import ConnectivityChecker from './components/ConnectivityChecker.vue'
import Destinations from './components/Destinations.vue'
import News from './components/News.vue'
import {ref} from "vue";
import { provideDestination } from './composables/useDestination.js'

const showConnectivity = ref(false)
const showDestinations = ref(false)
const showNews = ref(false)

// Utiliser le composable pour la destination
const { selectedDestination, setDestination } = provideDestination()

const toggleConnectivity = () => {
  showConnectivity.value = !showConnectivity.value
}

const toggleDestinations = () => {
  showDestinations.value = !showDestinations.value
}

const toggleNews = () => {
  showNews.value = !showNews.value
}

const handleSelectDestination = async (station) => {
  // Fermer l'overlay et transmettre la station sélectionnée
  showDestinations.value = false
  
  // Utiliser le composable pour définir la destination
  setDestination(station)
}
</script>

<template>
  <div class="app-container">
    <!-- Composant carte principal (contient déjà Sidebar et SearchOverlay) -->
    <Map />
    
    <!-- Boutons de contrôle -->
    <div class="control-buttons">
      <!-- Bouton de basculement connexité -->
      <button
        class="connectivity-toggle"
        @click="toggleConnectivity"
        :title="showConnectivity ? 'Fermer la vérification de connexité' : 'Vérifier la connexité du réseau'"
      >
        <span class="toggle-icon">{{ showConnectivity ? '✕' : '🔗' }}</span>
        <span class="toggle-text">{{ showConnectivity ? 'Fermer' : 'Connexité' }}</span>
      </button>

      <!-- Bouton Explorer Paris -->
      <button
        class="destinations-toggle"
        @click="toggleDestinations"
        :title="showDestinations ? 'Fermer Explorer Paris' : 'Explorer les monuments de Paris'"
      >
        <span class="toggle-icon">{{ showDestinations ? '✕' : '🏛️' }}</span>
        <span class="toggle-text">{{ showDestinations ? 'Fermer' : 'Explorer' }}</span>
      </button>

      <!-- Bouton Actualités -->
      <button
        class="news-toggle"
        @click="toggleNews"
        :title="showNews ? 'Fermer les actualités' : 'Consulter les actualités internationales'"
      >
        <span class="toggle-icon">{{ showNews ? '✕' : '📰' }}</span>
        <span class="toggle-text">{{ showNews ? 'Fermer' : 'Actualités' }}</span>
      </button>
    </div>

    <!-- Overlay pour le vérificateur de connexité -->
    <div v-if="showConnectivity" class="connectivity-overlay">
      <div class="connectivity-container">
        <ConnectivityChecker />
      </div>
    </div>

    <!-- Overlay pour Explorer Paris -->
    <div v-if="showDestinations" class="destinations-overlay">
      <div class="destinations-container">
        <Destinations @selectDestination="handleSelectDestination" />
      </div>
    </div>

    <!-- Overlay pour les actualités -->
    <div v-if="showNews" class="news-overlay">
      <div class="news-container">
        <News />
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  position: relative;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.control-buttons {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1001;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.connectivity-toggle,
.destinations-toggle,
.news-toggle {
  background: linear-gradient(90deg, #3498db, #2ecc71);
  color: white;
  border: none;
  border-radius: 50px;
  padding: 12px 20px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
  justify-content: center;
}

.destinations-toggle {
  background: linear-gradient(90deg, #e74c3c, #f39c12);
}

.news-toggle {
  background: linear-gradient(90deg, #9b59b6, #3498db);
}

.connectivity-toggle:hover,
.destinations-toggle:hover,
.news-toggle:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}

.toggle-icon {
  font-size: 1.2rem;
}

.toggle-text {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Overlay pour le vérificateur de connexité */
.connectivity-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(5px);
}

.connectivity-container {
  max-width: 100%;
  max-height: 100%;
  overflow-y: auto;
  background: transparent;
  border-radius: 12px;
}

/* Overlay pour Explorer Paris */
.destinations-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(5px);
}

.destinations-container {
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
}

/* Overlay pour les actualités */
.news-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(5px);
}

.news-container {
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  max-width: 800px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .control-buttons {
    top: 10px;
    right: 10px;
  }

  .connectivity-toggle,
  .destinations-toggle,
  .news-toggle {
    padding: 10px 16px;
    font-size: 0.8rem;
    min-width: 100px;
  }

  .connectivity-overlay,
  .destinations-overlay,
  .news-overlay {
    padding: 10px;
  }

  .connectivity-container,
  .destinations-container,
  .news-container {
    width: 100%;
  }

  .destinations-container {
    max-height: 90vh;
    padding: 16px;
  }

  .news-container {
    max-height: 95vh;
    padding: 16px;
  }
}
</style>
