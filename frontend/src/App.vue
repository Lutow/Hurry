<script setup>
import Map from './components/Map.vue'
import ConnectivityChecker from './components/ConnectivityChecker.vue'
import {ref} from "vue";

const showConnectivity = ref(false)

const toggleConnectivity = () => {
  showConnectivity.value = !showConnectivity.value
}
</script>

<template>
  <div class="app-container">
    <!-- Composant carte principal (contient déjà Sidebar et SearchOverlay) -->
    <Map />
    
    <!-- Bouton de basculement connexité -->
    <button
      class="connectivity-toggle"
      @click="toggleConnectivity"
      :title="showConnectivity ? 'Fermer la vérification de connexité' : 'Vérifier la connexité du réseau'"
    >
      <span class="toggle-icon">{{ showConnectivity ? '✕' : '🔗' }}</span>
      <span class="toggle-text">{{ showConnectivity ? 'Fermer' : 'Connexité' }}</span>
    </button>

    <!-- Overlay pour le vérificateur de connexité -->
    <div v-if="showConnectivity" class="connectivity-overlay">
      <div class="connectivity-container">
        <ConnectivityChecker />
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

.connectivity-toggle {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1001;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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

.connectivity-toggle:hover {
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

@media (max-width: 768px) {
  .connectivity-toggle {
    top: 10px;
    right: 10px;
    padding: 10px 16px;
    font-size: 0.8rem;
    min-width: 100px;
  }

  .connectivity-overlay {
    padding: 10px;
  }

  .connectivity-container {
    width: 100%;
  }
}
</style>
