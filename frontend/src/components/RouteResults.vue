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
                <span class="route-label">{{ getOptionLabel(index) }}</span>
                
                <!-- Horaires si disponibles -->
                <div v-if="route.departure_time && route.arrival_time" class="route-schedule">
                  <div class="schedule-time">
                    <span class="material-icons">schedule</span>
                    <span>{{ route.departure_time }} → {{ route.arrival_time }}</span>
                  </div>
                  <div v-if="route.total_waiting_time > 0" class="waiting-time">
                    <span class="material-icons">hourglass_top</span>
                    <span>{{ route.total_waiting_time }} min d'attente</span>
                  </div>
                </div>
                
                <div class="route-metrics">
                  <div class="primary-metrics">
                    <span class="emission">
                      <span class="material-icons">co2</span>
                      {{ route.co2 }} g
                    </span>
                    <span class="duration">
                      <span class="material-icons">schedule</span>
                      {{ route.duration || route.total_travel_time }} min
                    </span>
                  </div>
                  <div class="secondary-metrics">
                    <span class="transfers">
                      <span class="material-icons">transfer_within_a_station</span>
                      {{ route.transfers }} correspondance{{ route.transfers !== 1 ? 's' : '' }}
                    </span>
                  </div>
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
                  <div class="segment-main">
                    <div class="line-indicator">
                      <!-- Badge spécial pour les correspondances -->
                      <div v-if="segment.type === 'transfer'" class="line-badge transfer-badge">
                        <span class="material-icons">transfer_within_a_station</span>
                      </div>
                      <!-- Badge normal pour les lignes de métro -->
                      <div v-else class="line-badge" :style="{ backgroundColor: getLineColor(segment.line) }">
                        {{ segment.line }}
                      </div>
                    </div>
                    <div class="segment-info">
                      <!-- Métadonnées du segment (avant le trajet) -->
                      <div class="segment-meta">
                        <!-- Ne pas afficher le nombre de stations pour les correspondances -->
                        <div v-if="segment.type !== 'transfer'" class="station-count">
                          <span class="material-icons">directions_subway</span>
                          {{ segment.stops || 1 }} station{{ (segment.stops || 1) !== 1 ? 's' : '' }}
                        </div>
                        <span v-if="segment.waiting_time > 0" class="waiting-info">
                          <span class="material-icons">hourglass_top</span>
                          {{ segment.waiting_time }} min d'attente
                        </span>
                      </div>
                      <!-- Trajet (après les métadonnées) -->
                      <div class="segment-path">
                        <div class="station-row">
                          <span class="material-icons station-icon">trip_origin</span>
                          <span class="station-name">{{ segment.from_station || segment.from }}</span>
                          <span v-if="segment.departure_time" class="departure-time">{{ segment.departure_time }}</span>
                        </div>
                        <div class="journey-line"></div>
                        <div class="station-row">
                          <span class="material-icons station-icon">place</span>
                          <span class="station-name">{{ segment.to_station || segment.to }}</span>
                          <span v-if="segment.arrival_time" class="arrival-time">{{ segment.arrival_time }}</span>
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

const fastestIndex = computed(() => {
  if (props.routes.length <= 1) return -1
  return props.routes.reduce((minIdx, route, idx, arr) =>
    route.duration < arr[minIdx].duration ? idx : minIdx, 0)
})

const greenestIndex = computed(() => {
  if (props.routes.length <= 1) return -1
  return props.routes.reduce((minIdx, route, idx, arr) =>
    route.co2 < arr[minIdx].co2 ? idx : minIdx, 0)
})

function getOptionLabel(index) {
  const route = props.routes[index]
  
  // Si le backend a fourni un label personnalisé, l'utiliser
  if (route && route.option_label) {
    return route.option_label
  }
  
  // Si on a des horaires, utiliser une numérotation simple avec indication du créneau
  if (route && route.departure_time && route.arrival_time) {
    if (route.is_requested_time) {
      return "À l'heure demandée"
    } else {
      return `Départ ${route.departure_time}`
    }
  }
  
  // Fallback vers l'ancien système optimisé
  if (props.routes.length === 1) return "Option unique"
  if (index === fastestIndex.value && index === greenestIndex.value) return "Option optimale"
  if (index === fastestIndex.value) return "Option la plus rapide"
  if (index === greenestIndex.value) return "Option la plus écologique"
  return `Option ${index + 1}`
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
  flex-direction: column;
  gap: 8px;
}

.primary-metrics {
  display: flex;
  gap: 16px;
  align-items: center;
}

.secondary-metrics {
  display: flex;
  justify-content: flex-start;
}

/* Harmoniser tous les blocs d'infos (CO2, durée, correspondances) */
.emission, .duration, .transfers {
  display: flex;
  align-items: center;
  gap: 4px;
}

.duration, .transfers {
  color: #2c3e50;
}

.emission .material-icons,
.duration .material-icons,
.transfers .material-icons {
  line-height: 1;
}

.emission {
  color: #2c3e50;
}

.emission .material-icons {
  font-size: 25px;
  color: #2ecc71;
}

.duration .material-icons,
.transfers .material-icons {
  font-size: 16px;
  color: #2c3e50;
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

.transfer-badge {
  background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
  border: 2px solid #ffffff;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.3);
}

.transfer-badge .material-icons {
  font-size: 16px;
  font-weight: 500;
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
  margin-bottom: 8px;
  margin-top: 2px;
}

.segment-meta .material-icons {
  font-size: 14px;
}

.station-count {
  display: flex;
  align-items: center;
  gap: 4px;
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

/* Styles pour les horaires */
.route-schedule {
  margin: 8px 0;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #3498db;
}

.schedule-time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #2c3e50;
  font-size: 14px;
}

.schedule-time .material-icons {
  font-size: 16px;
  color: #3498db;
}

.waiting-time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #e67e22;
  margin-top: 4px;
}

.waiting-time .material-icons {
  font-size: 14px;
}

.departure-time, .arrival-time {
  font-size: 11px;
  color: #3498db;
  font-weight: 600;
  margin-left: auto;
}

.waiting-info {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  color: #e67e22;
}

.waiting-info .material-icons {
  font-size: 12px;
}

.requested-badge {
  background: #e74c3c;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  margin-left: 8px;
  font-weight: 600;
}

.time-slot-badge {
  background: #3498db;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  margin-left: 8px;
  font-weight: 600;
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
