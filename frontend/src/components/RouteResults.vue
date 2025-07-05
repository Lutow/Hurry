<template>
  <div v-if="show" class="route-results-overlay" @click="closeIfClickedOutside">
    <div class="route-results" @click.stop @wheel.stop @mousedown.stop @mousemove.stop @touchstart.stop @touchmove.stop>
      <!-- Header avec bouton de fermeture -->
      <div class="results-header">
        <div class="header-content">
          <span class="material-icons">route</span>
          <h2>Itinéraires trouvés</h2>
        </div>
        <button class="close-btn" @click="closeResults">
          <span class="material-icons">close</span>
        </button>
      </div>

      <!-- État de chargement -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Calcul des itinéraires en cours...</p>
      </div>

      <!-- État d'erreur -->
      <div v-else-if="error" class="error-state">
        <span class="material-icons error-icon">error_outline</span>
        <p>{{ error }}</p>
        <button class="retry-btn" @click="$emit('close')">Fermer</button>
      </div>

      <!-- Résultats -->
      <div v-else class="results-content">
        <!-- Résumé du trajet -->
        <div class="journey-summary">
          <div class="journey-points">
            <div class="point start-point">
              <span class="material-icons">trip_origin</span>
              <span class="station-name">{{ from }}</span>
            </div>
            <div class="arrow">
              <span class="material-icons">arrow_downward</span>
            </div>
            <div class="point end-point">
              <span class="material-icons">place</span>
              <span class="station-name">{{ to }}</span>
            </div>
          </div>
        </div>

        <!-- Liste des options d'itinéraires -->
        <div class="routes-container">
          <div v-for="(route, index) in routes" :key="index" class="route-option" @click="selectRoute(route)">
            <div class="route-summary">
              <div class="route-info">
                <span class="route-label">Option {{ index + 1 }}</span>
                <div class="route-metrics">
                  <span class="duration">
                    <span class="material-icons">schedule</span>
                    {{ route.duration }} min
                  </span>
                  <span class="transfers">
                    <span class="material-icons">transfer_within_a_station</span>
                    {{ route.transfers }} correspondance{{ route.transfers !== 1 ? 's' : '' }}
                  </span>
                </div>
              </div>
              
              <!-- Bouton pour afficher/masquer le trajet sur la carte -->
              <div class="route-actions">
                <button 
                  class="show-route-btn"
                  :class="{ active: selectedRouteIndex === index }"
                  @click.stop="toggleRouteDisplay(route, index)"
                >
                  <span class="material-icons">
                    {{ selectedRouteIndex === index ? 'visibility_off' : 'visibility' }}
                  </span>
                  {{ selectedRouteIndex === index ? 'Masquer le trajet' : 'Afficher le trajet' }}
                </button>
              </div>
            </div>

            <div class="route-details">
              <div class="segments">
                <div v-for="(segment, segmentIndex) in route.segments" :key="segmentIndex" class="segment">
                  <!-- Correspondance entre segments -->
                  <div v-if="segmentIndex > 0" class="transfer-indicator">
                    <div class="transfer-dot">
                      <span class="material-icons">sync_alt</span>
                    </div>
                    <div class="transfer-label">Correspondance</div>
                  </div>
                  
                  <div class="segment-main">
                    <div class="line-indicator">
                      <div class="line-badge" :style="{ backgroundColor: getLineColor(segment.line) }">
                        {{ segment.line }}
                      </div>
                    </div>
                    <div class="segment-info">
                      <div class="segment-path">
                        <div class="station-row">
                          <span class="material-icons station-icon">trip_origin</span>
                          <span class="station-name">{{ segment.from }}</span>
                        </div>
                        <div class="journey-line"></div>
                        <div class="station-row">
                          <span class="material-icons station-icon">place</span>
                          <span class="station-name">{{ segment.to }}</span>
                        </div>
                      </div>
                      <div class="segment-meta">
                        <span class="material-icons">directions_subway</span>
                        {{ segment.stops }} station{{ segment.stops !== 1 ? 's' : '' }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, computed, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  from: {
    type: String,
    default: ''
  },
  to: {
    type: String,
    default: ''
  },
  routes: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'routeSelected', 'showRoute', 'hideRoute'])

// État pour suivre quelle route est affichée
const selectedRouteIndex = ref(-1)

// Couleurs des lignes de métro
const lineColors = {
  '1': '#FFCE00',
  '2': '#0064B0',
  '3': '#9F9825',
  '3bis': '#98D4E2',
  '4': '#C04191',
  '5': '#F28E42',
  '6': '#83C491',
  '7': '#F3A4BA',
  '7bis': '#83C491',
  '8': '#CEADD2',
  '9': '#D5C900',
  '10': '#E3B32A',
  '11': '#8D5E2A',
  '12': '#00814F',
  '13': '#98D4E2',
  '14': '#662483',
  'A': '#E2231A',
  'B': '#427DBD',
  'C': '#FFCE00',
  'D': '#00B161',
  'E': '#A0006E',
  'default': '#888888'
}

function getLineColor(line) {
  return lineColors[line] || lineColors.default
}

function selectRoute(route) {
  emit('routeSelected', route)
}

function toggleRouteDisplay(route, index) {
  if (selectedRouteIndex.value === index) {
    // Masquer le trajet actuellement affiché
    selectedRouteIndex.value = -1
    emit('hideRoute')
  } else {
    // Afficher le nouveau trajet
    selectedRouteIndex.value = index
    emit('showRoute', route)
  }
}

function closeResults() {
  // Masquer le trajet affiché avant de fermer
  if (selectedRouteIndex.value !== -1) {
    selectedRouteIndex.value = -1
    emit('hideRoute')
  }
  emit('close')
}

function closeIfClickedOutside(event) {
  if (event.target.classList.contains('route-results-overlay')) {
    // Masquer le trajet affiché avant de fermer
    if (selectedRouteIndex.value !== -1) {
      selectedRouteIndex.value = -1
      emit('hideRoute')
    }
    emit('close')
  }
}

// Réinitialiser l'état quand les routes changent
watch(() => props.routes, () => {
  selectedRouteIndex.value = -1
})
</script>

<style scoped>
.route-results-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: hidden; /* Empêche le scroll de l'overlay */
}

.route-results {
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease-out;
  /* Empêche la propagation du scroll vers les éléments parents */
  overscroll-behavior: contain;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.results-header {
  background: linear-gradient(135deg, #3498db, #2ecc71);
  color: white;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0; /* Empêche le header de se réduire */
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-content .material-icons {
  font-size: 28px;
}

.header-content h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.close-btn .material-icons {
  color: white;
  font-size: 24px;
}

.loading-state, .error-state {
  padding: 40px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  flex: 1;
  overflow-y: auto;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  font-size: 48px;
  color: #e74c3c;
}

.retry-btn {
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 10px 20px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.retry-btn:hover {
  background: #2980b9;
}

.results-content {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
}

.journey-summary {
  background: #f8f9fa;
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
  flex-shrink: 0; /* Empêche la section de se réduire */
}

.journey-points {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.point {
  display: flex;
  align-items: center;
  gap: 12px;
}

.start-point .material-icons {
  color: #2ecc71;
  font-size: 20px;
}

.end-point .material-icons {
  color: #e74c3c;
  font-size: 20px;
}

.station-name {
  font-weight: 500;
  color: #333;
  word-break: break-word; /* Permet la coupure des longs noms */
}

.arrow {
  display: flex;
  justify-content: center;
  margin: 4px 0;
}

.arrow .material-icons {
  color: #666;
  font-size: 20px;
}

.routes-container {
  flex: 1;
  overflow-y: auto; /* Permet le scroll uniquement dans cette section */
  overflow-x: hidden;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  /* Scroll personnalisé */
  scrollbar-width: thin;
  scrollbar-color: #cbd5e0 #f7fafc;
}

.routes-container::-webkit-scrollbar {
  width: 6px;
}

.routes-container::-webkit-scrollbar-track {
  background: #f7fafc;
  border-radius: 3px;
}

.routes-container::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 3px;
}

.routes-container::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}

.route-option {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0; /* Empêche les cartes de se réduire */
}

.route-option:hover {
  border-color: #3498db;
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.2);
  transform: translateY(-1px);
}

.route-summary {
  background: #f8f9fa;
  padding: 16px;
  border-bottom: 1px solid #e9ecef;
}

.route-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.route-label {
  font-weight: 600;
  color: #3498db;
  font-size: 16px;
}

.route-metrics {
  display: flex;
  gap: 16px;
}

.duration, .transfers {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #666;
}

.duration .material-icons, .transfers .material-icons {
  font-size: 16px;
}

.route-details {
  padding: 16px;
}

.segments {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.segment {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.transfer-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
  padding: 8px;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 6px;
  font-size: 12px;
  color: #856404;
}

.transfer-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #ffeaa7;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.transfer-dot .material-icons {
  font-size: 14px;
  color: #856404;
}

.transfer-label {
  font-weight: 500;
}

.segment-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.line-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.line-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: white;
  font-weight: bold;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.segment-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0; /* Permet la compression du texte */
}

.segment-path {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.station-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.station-icon {
  font-size: 16px;
  color: #666;
  flex-shrink: 0;
}

.journey-line {
  width: 2px;
  height: 20px;
  background: #ddd;
  margin-left: 7px;
  margin: 4px 0 4px 7px;
}

.segment-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.segment-meta .material-icons {
  font-size: 14px;
}

.route-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.show-route-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 20px;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(52, 152, 219, 0.3);
}

.show-route-btn:hover {
  background: #2980b9;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(52, 152, 219, 0.4);
}

.show-route-btn.active {
  background: #e74c3c;
}

.show-route-btn.active:hover {
  background: #c0392b;
}

.show-route-btn .material-icons {
  font-size: 16px;
}

/* Responsive */
@media (max-width: 600px) {
  .route-results-overlay {
    padding: 10px;
  }
  
  .route-results {
    max-height: 90vh;
  }
  
  .results-header {
    padding: 16px;
  }
  
  .header-content h2 {
    font-size: 18px;
  }
  
  .routes-container {
    padding: 16px;
  }
  
  .route-metrics {
    flex-direction: column;
    gap: 8px;
    align-items: flex-end;
  }
  
  .journey-summary {
    padding: 16px;
  }
  
  .route-details {
    padding: 12px;
  }
}
</style>
