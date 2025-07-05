<template>
  <div class="journey-planner" @wheel.stop @mousedown.stop @mousemove.stop @touchstart.stop @touchmove.stop>
    <form @submit.prevent="handleSearch">
      <div class="journey-header">
        <div class="journey-title">
          <span class="material-icons">directions</span>
          <span>Planifier un trajet</span>
        </div>
      </div>
      
      <div class="journey-form">
        <div class="input-group">
          <span class="material-icons location-icon start">trip_origin</span>
          <input
            list="stations"
            type="text" 
            v-model="depart" 
            placeholder="Station de départ" 
            class="journey-input"
            @focus="activeInput = 'depart'; showStationsList = true"
            @input="handleInputChange('depart')"
            @blur="setTimeout(() => { showStationsList = false; }, 200)"
          />
        </div>
        
        <div class="input-group">
          <span class="material-icons location-icon end">place</span>
          <input
            list="stations"
            type="text" 
            v-model="arrivee" 
            placeholder="Station d'arrivée" 
            class="journey-input"
            @focus="activeInput = 'arrivee'; showStationsList = true"
            @input="handleInputChange('arrivee')"
            @blur="setTimeout(() => { showStationsList = false; }, 200)"
          />
        </div>
        
        <div class="form-footer">
          <div class="time-selector">
            <span class="material-icons">schedule</span>
            <input type="time" v-model="heure" class="time-input" />
          </div>
          
          <button type="submit" class="search-button" :disabled="loading">
            <span v-if="loading" class="mini-spinner"></span>
            <span v-else class="material-icons">search</span>
            <span>{{ loading ? 'Recherche...' : 'Rechercher' }}</span>
          </button>
        </div>
      </div>
    </form>

    <div v-if="errorMessage" class="error-message">
      <span class="material-icons error-icon">error_outline</span>
      <span>{{ errorMessage }}</span>
    </div>
    <!-- Datalist pour l'autocomplétion des stations -->
    <datalist id="stations">
      <option
        v-for="stop in stops"
        :key="stop.stop_id"
        :value="stop.stop_name"
      />
    </datalist>
    
    <!-- Liste des stations filtrées - UI unique et bien positionnée -->
    <div v-if="showStationsList && (activeInput === 'depart' || activeInput === 'arrivee')" class="station-dropdown">
      <div v-for="stop in (activeInput === 'depart' ? filteredDepartStops : filteredArriveeStops)" 
           :key="stop.stop_id" 
           class="station-option" 
           @mousedown.prevent="selectStation(stop, activeInput)"
           @touchstart.prevent="selectStation(stop, activeInput)">
        {{ stop.stop_name }}
      </div>
    </div>
  </div>
  
  <RouteResults
    :show="showResults"
    :from="routeResults.from"
    :to="routeResults.to"
    :routes="routeResults.routes"
    :loading="loading"
    :error="errorMessage"
    @close="closeResults"
    @routeSelected="selectRoute"
    @showRoute="showRouteOnMap"
    @hideRoute="hideRouteOnMap"
  />
</template>

<script setup>
import {ref, inject, onMounted, watch} from 'vue'
import RouteResults from './RouteResults.vue'

const depart = ref('')
const arrivee = ref('')
const heure = ref('')
const loading = ref(false)
const stops = ref([])
const errorMessage = ref('')
const showResults = ref(false)
const routeResults = ref({
  from: '',
  to: '',
  routes: []
})

// Variables pour la recherche avancée
const filteredDepartStops = ref([])
const filteredArriveeStops = ref([])
const showStationsList = ref(false)
const activeInput = ref(null)

// Injecter l'instance de la carte et la fonction d'affichage d'itinéraire
const mapInstance = inject('mapInstance', null)
const displayRouteOnMap = inject('displayRouteOnMap', null)

onMounted(async () => {
  try {
    // Ajouter un timeout pour éviter les attentes infinies
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // Timeout après 5s
    
    console.log("Tentative de récupération des stations...")
    let res;
    
    try {
      // Essayer d'abord la nouvelle API complète
      res = await fetch("http://localhost:8000/api/stops/all", {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        console.warn(`API complète en erreur (${res.status}), tentative avec l'API principale...`);
        throw new Error("API complète en erreur");
      }
    } catch (completeApiError) {
      console.warn("Échec de l'API complète, tentative avec l'API principale");
      
      try {
        // Essayer ensuite l'API principale
        const mainController = new AbortController();
        const mainTimeoutId = setTimeout(() => mainController.abort(), 5000);
        
        res = await fetch("http://localhost:8000/api/stops/list", {
          signal: mainController.signal
        });
        
        clearTimeout(mainTimeoutId);
        
        if (!res.ok) {
          console.warn(`API principale en erreur (${res.status}), tentative avec l'API simplifiée...`);
          throw new Error("API principale en erreur");
        }
      } catch (mainApiError) {
        console.warn("Échec de l'API principale, tentative avec l'API simplifiée");
        
        // En dernier recours, utiliser l'API simplifiée
        try {
          const backupController = new AbortController();
          const backupTimeoutId = setTimeout(() => backupController.abort(), 5000);
          
          res = await fetch("http://localhost:8000/api/stops/basic", {
            signal: backupController.signal
          });
          
          clearTimeout(backupTimeoutId);
          
          if (!res.ok) {
            throw new Error(`API simplifiée également en erreur: ${res.status}`);
          }
        } catch (backupError) {
          console.error("Toutes les tentatives ont échoué:", backupError);
          // Utiliser une liste de stations hardcodée en dernier recours
          stops.value = [
            { stop_id: "local_1", stop_name: "Châtelet" },
            { stop_id: "local_2", stop_name: "Nation" },
            { stop_id: "local_3", stop_name: "Bastille" },
            { stop_id: "local_4", stop_name: "République" },
            { stop_id: "local_5", stop_name: "Montparnasse" },
            { stop_id: "local_6", stop_name: "Gare du Nord" },
            { stop_id: "local_7", stop_name: "Gare de Lyon" },
            { stop_id: "local_8", stop_name: "Saint-Lazare" },
            { stop_id: "local_9", stop_name: "Montmartre" },
            { stop_id: "local_10", stop_name: "Opéra" }
          ];
          console.log("Utilisation de stations hardcodées:", stops.value.length);
          return;
        }
      }
    }
    
    const data = await res.json();
    console.log("Données reçues:", data);
    
    if (data && data.stops) {
      stops.value = data.stops;
      console.log("Stations chargées:", stops.value.length);
    } else {
      console.error("Format de données incorrect:", data);
      stops.value = [];
      errorMessage.value = "Format de données incorrect";
    }
  } catch (error) {
    console.error("Erreur lors du chargement des stations:", error);
    stops.value = [];
    errorMessage.value = `Impossible de charger les stations: ${error.message}`;
  }
})

function fetchConnectivity() {
  fetch('graph/connectivity').then(res => res.json()).then(data => {console.log(data)})
}

async function handleSearch() {
  if (!depart.value || !arrivee.value) {
    errorMessage.value = 'Veuillez renseigner une station de départ et d\'arrivée'
    return
  }
  
  loading.value = true
  errorMessage.value = ''
  showResults.value = true
  
  try {
    const response = await fetch(`/api/routes?depart=${encodeURIComponent(depart.value)}&arrivee=${encodeURIComponent(arrivee.value)}`)
    const data = await response.json()
    
    if (data.error) {
      errorMessage.value = data.error
      routeResults.value = { from: '', to: '', routes: [] }
    } else {
      routeResults.value = data
      errorMessage.value = ''
    }
  } catch (error) {
    console.error('Erreur lors de la recherche de trajet:', error)
    errorMessage.value = 'Une erreur est survenue lors de la recherche'
    routeResults.value = { from: '', to: '', routes: [] }
  } finally {
    loading.value = false
  }
}

function closeResults() {
  showResults.value = false
}

const selectRoute = function(route) {
  if (!displayRouteOnMap) {
    console.error('Fonction d\'affichage d\'itinéraire non disponible')
    return
  }
  
  // Afficher le trajet sur la carte
  displayRouteOnMap(route)
  
  // Fermer les résultats
  closeResults()
}

// Fonctions pour afficher/masquer le trajet sur la carte
function showRouteOnMap(route) {
  // Injecter une fonction pour afficher uniquement ce trajet
  if (mapInstance.value && mapInstance.value.showOnlyRoute) {
    mapInstance.value.showOnlyRoute(route)
  }
}

function hideRouteOnMap() {
  // Injecter une fonction pour réafficher tous les éléments
  if (mapInstance.value && mapInstance.value.showAllElements) {
    mapInstance.value.showAllElements()
  }
}

// Fonction pour gérer l'affichage de la liste des stations
function toggleStations(field) {
  // Utiliser notre propre UI pour afficher les stations
  activeInput.value = field;
  
  // Si on clique sur le même champ, on bascule l'affichage
  if (showStationsList.value && activeInput.value === field) {
    showStationsList.value = false;
  } else {
    showStationsList.value = true;
  }
  
  // Mettre à jour les listes filtrées
  if (field === 'depart') {
    filteredDepartStops.value = filterStations(depart.value, 'depart');
    
    // Focus sur l'input
    const inputElement = document.querySelector('.input-group:first-child input');
    if (inputElement) inputElement.focus();
  } else {
    filteredArriveeStops.value = filterStations(arrivee.value, 'arrivee');
    
    // Focus sur l'input
    const inputElement = document.querySelector('.input-group:nth-child(2) input');
    if (inputElement) inputElement.focus();
  }
  
  console.log(`Affichage de ${field === 'depart' ? filteredDepartStops.value.length : filteredArriveeStops.value.length} stations pour ${field}`);
}

// Fonction pour sélectionner une station dans la liste déroulante
function selectStation(station, field) {
  if (typeof station === 'string') {
    // Si station est directement une chaîne de caractères
    if (field === 'depart') {
      depart.value = station;
      filteredDepartStops.value = [];
    } else {
      arrivee.value = station;
      filteredArriveeStops.value = [];
    }
  } else if (station && station.stop_name) {
    // Si station est un objet avec une propriété stop_name
    if (field === 'depart') {
      depart.value = station.stop_name;
      filteredDepartStops.value = [];
    } else {
      arrivee.value = station.stop_name;
      filteredArriveeStops.value = [];
    }
  }
  
  showStationsList.value = false;
  
  // Notifier l'utilisateur
  const stationName = typeof station === 'string' ? station : station.stop_name;
  console.log(`Station ${stationName} sélectionnée pour ${field}`);
}

// Fonction pour fermer la liste déroulante quand on clique ailleurs
function setupClickOutside() {
  document.addEventListener('click', (event) => {
    const isClickInsideForm = event.target.closest('.journey-form');
    if (!isClickInsideForm && showStationsList.value) {
      showStationsList.value = false;
    }
  });
}

// Ajouter l'event listener pour fermer la liste quand on clique ailleurs
onMounted(() => {
  setupClickOutside();
});

// Fonction pour filtrer les stations selon l'entrée utilisateur
function filterStations(input, targetField) {
  const query = input.toLowerCase().trim();
  
  if (!query || query.length < 2) {
    return stops.value.slice(0, 20); // Retourner les 20 premières stations si la requête est trop courte
  }
  
  const filtered = stops.value.filter(station => 
    station.stop_name.toLowerCase().includes(query)
  );
  
  // Trier les résultats pour que ceux qui commencent par la requête apparaissent en premier
  return filtered.sort((a, b) => {
    const aStartsWith = a.stop_name.toLowerCase().startsWith(query);
    const bStartsWith = b.stop_name.toLowerCase().startsWith(query);
    
    if (aStartsWith && !bStartsWith) return -1;
    if (!aStartsWith && bStartsWith) return 1;
    return 0;
  }).slice(0, 50); // Limiter à 50 résultats pour les performances
}

// Observer les changements d'entrée pour mettre à jour les filtres
watch(depart, (newVal) => {
  filteredDepartStops.value = filterStations(newVal, 'depart');
});

watch(arrivee, (newVal) => {
  filteredArriveeStops.value = filterStations(newVal, 'arrivee');
});

// Fonction pour gérer le changement de saisie dans les champs
function handleInputChange(field) {
  // Mettre à jour l'input actif
  activeInput.value = field;
  
  // Filtrer les stations en fonction de la saisie
  if (field === 'depart') {
    filteredDepartStops.value = filterStations(depart.value, 'depart');
    if (depart.value && depart.value.length > 0) {
      showStationsList.value = true;
    }
  } else if (field === 'arrivee') {
    filteredArriveeStops.value = filterStations(arrivee.value, 'arrivee');
    if (arrivee.value && arrivee.value.length > 0) {
      showStationsList.value = true;
    }
  }
}
</script>

<style scoped>
.journey-planner {
  width: 100%;
  color: var(--sidebar-text);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.journey-header {
  display: flex;
  align-items: center;
  padding: 0 0 15px 0;
  border-bottom: 2px solid var(--sidebar-accent-hover);
  margin-bottom: 15px;
}

.journey-title {
  display: flex;
  align-items: center;
}

.journey-title .material-icons {
  margin-right: 12px;
  font-size: 24px;
  color: var(--sidebar-accent);
}

.journey-title span:not(.material-icons) {
  font-size: 18px;
  font-weight: 600;
}

.journey-form {
  padding: 0;
}

.input-group {
  position: relative;
  margin-bottom: 16px;
}

.location-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--sidebar-text-secondary);
  font-size: 18px;
}

.location-icon.start {
  color: var(--sidebar-success);
}

.location-icon.end {
  color: var(--sidebar-danger);
}

.journey-input {
  width: 100%;
  padding: 10px 10px 10px 40px;
  border: none;
  border-radius: 6px;
  background: var(--sidebar-bg-secondary);
  color: var(--sidebar-text);
  font-size: 14px;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.journey-input::placeholder {
  color: var(--sidebar-text-secondary);
}

.journey-input:focus {
  outline: none;
  background: var(--sidebar-bg-secondary);
  box-shadow: 0 0 0 2px var(--sidebar-accent);
}

.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.time-selector {
  display: flex;
  align-items: center;
  background: var(--sidebar-bg-secondary);
  border-radius: 6px;
  padding: 6px 10px;
}

.time-selector .material-icons {
  margin-right: 8px;
  font-size: 16px;
  color: var(--sidebar-text-secondary);
}

.time-input {
  background: transparent;
  border: none;
  color: var(--sidebar-text);
  font-size: 14px;
  width: 80px;
}

.time-input:focus {
  outline: none;
}

.search-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, var(--sidebar-accent), var(--sidebar-success));
  color: var(--sidebar-button-text);
  border: none;
  border-radius: 20px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 120px;
}

.search-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.search-button:not(:disabled):hover {
  background: linear-gradient(90deg, var(--sidebar-accent-hover), var(--sidebar-success));
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--sidebar-shadow);
}

.search-button:not(:disabled):active {
  transform: translateY(0);
  box-shadow: 0 2px 6px var(--sidebar-shadow);
}

.search-button .material-icons {
  font-size: 18px;
  margin-right: 6px;
}

.mini-spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  margin-right: 6px;
  border: 2px solid var(--sidebar-text-secondary);
  border-top-color: var(--sidebar-accent);
  border-radius: 50%;
  animation: spin 1s infinite linear;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  display: flex;
  align-items: center;
  padding: 10px;
  margin-top: 16px;
  background-color: var(--sidebar-error-bg);
  border-radius: 6px;
  font-size: 14px;
}

.error-icon {
  color: var(--sidebar-danger);
  margin-right: 8px;
  font-size: 20px;
}

.input-group:first-child {
  animation: fadeIn 0.5s ease;
}

.input-group:nth-child(2) {
  animation: fadeIn 0.5s ease 0.1s forwards;
}

.form-footer {
  animation: fadeIn 0.5s ease 0.2s forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
