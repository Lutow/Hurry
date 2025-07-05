<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const disruptions = ref([])
const loading = ref(true)
const error = ref(null)

const fetchDisruptions = async (retryCount = 0) => {
  try {
    const { data } = await axios.get('/api/ratp-disruptions')
    console.log("Données reçues :", data)
    disruptions.value = data.disruptions || []
    error.value = null // Réinitialiser l'erreur en cas de succès
    loading.value = false
  } catch (err) {
    console.error(`Erreur de chargement (tentative ${retryCount + 1}/3):`, err)
    
    // Toujours tenter un nouveau chargement si on n'a pas encore fait 3 tentatives
    if (retryCount < 2) { // 0, 1, 2 = 3 tentatives au total
      console.log(`Nouvelle tentative dans 3 secondes... (${retryCount + 2}/3)`)
      setTimeout(() => {
        fetchDisruptions(retryCount + 1)
      }, 3000)
    } else {
      console.log("Échec après 3 tentatives")
      error.value = 'Erreur de chargement des perturbations'
      loading.value = false
    }
  }
}

const retryFetch = () => {
  loading.value = true
  error.value = null
  fetchDisruptions()
}

onMounted(() => {
  fetchDisruptions()
})
</script>

<template>
  <div class="disruptions-container" @wheel.stop @mousedown.stop @mousemove.stop @touchstart.stop @touchmove.stop>
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <div class="loading-text">Chargement des informations trafic...</div>
    </div>
    <div v-else-if="error" class="error-container">
      <div class="error-message">{{ error }}</div>
      <button @click="retryFetch" class="retry-button">
        <span class="material-icons">refresh</span>
        Réessayer
      </button>
    </div>
    <div v-else-if="disruptions.length === 0" class="no-disruptions">
      <span class="material-icons check-icon">check_circle</span>
      <div>Aucune perturbation détectée</div>
      <div class="status-message">Tout fonctionne normalement</div>
    </div>
    <ul v-else class="disruption-list">
      <li v-for="d in disruptions" :key="d.id" class="disruption-item">
        <div class="disruption-header">
          <span class="material-icons warning-icon">warning</span>
          <strong>{{ d.title }}</strong>
        </div>
        <div class="disruption-message" v-html="d.message"></div>
      </li>
    </ul>
  </div>
</template>


<style scoped>
.disruptions-container {
  max-height: 40vh;
  overflow-y: auto;
  background-color: transparent;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9rem;
  padding: 0.5rem 1rem;
  /* Pour Firefox */
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.5) transparent;
}

.disruption-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.disruption-item {
  margin-bottom: 1.2rem;
  padding: 12px 15px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  border-left: 4px solid #e74c3c;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.disruption-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.disruption-header {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.disruption-header strong {
  font-weight: 600;
  color: #fff;
  font-size: 14px;
}

.warning-icon {
  color: #e74c3c;
  margin-right: 8px;
  font-size: 18px;
}

.disruption-message {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.5;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.2);
  border-top-color: #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

.loading-text {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.error-container {
  text-align: center;
  padding: 1.5rem;
  background: rgba(231, 76, 60, 0.1);
  border-radius: 8px;
  margin: 0.5rem;
}

.error-message {
  color: #e74c3c;
  margin-bottom: 12px;
  font-size: 14px;
}

.retry-button {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  margin: 0 auto;
}

.retry-button .material-icons {
  margin-right: 6px;
  font-size: 16px;
}

.retry-button:hover {
  background-color: #2980b9;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.no-disruptions {
  text-align: center;
  padding: 1.5rem;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}

.check-icon {
  color: #2ecc71;
  font-size: 32px;
  margin-bottom: 10px;
  display: block;
}

.status-message {
  color: #2ecc71;
  font-size: 12px;
  margin-top: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Style personnalisé pour la barre de défilement (pour Chrome, Safari et les navigateurs basés sur WebKit) */
.disruptions-container::-webkit-scrollbar {
  width: 6px;
}

.disruptions-container::-webkit-scrollbar-track {
  background: transparent;
}

.disruptions-container::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.disruptions-container::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.5);
}
</style>
