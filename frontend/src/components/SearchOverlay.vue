<template>
  <div class="journey-planner" @wheel.stop @mousedown.stop @mousemove.stop @touchstart.stop @touchmove.stop @dblclick.stop.prevent>
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
            <div class="time-controls">
              <div class="time-type-selector">
                <label>
                  <input type="radio" v-model="timeType" value="departure" />
                  <span>Départ</span>
                </label>
                <label>
                  <input type="radio" v-model="timeType" value="arrival" />
                  <span>Arrivée</span>
                </label>
                <label>
                  <input type="radio" v-model="timeType" value="now" />
                  <span>Sans horaire</span>
                </label>
              </div>
              <input 
                type="time" 
                v-model="heure" 
                class="time-input" 
                :disabled="timeType === 'now'"
                :class="{ 'disabled': timeType === 'now' }"
              />
            </div>
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
    
    <!-- Section ACPM -->
    <div class="acpm-section">
      <div class="section-title">
        <span class="material-icons">account_tree</span>
        <span>Arbre Couvrant de Poids Minimum</span>
      </div>
      
      <div class="acpm-controls">
        <button 
          type="button" 
          class="acpm-button" 
          @click="calculateMST"
          :disabled="loadingMST"
        >
          <span v-if="loadingMST" class="mini-spinner"></span>
          <span v-else class="material-icons">account_tree</span>
          <span>{{ loadingMST ? 'Calcul...' : 'Calculer ACPM' }}</span>
        </button>
        
        <div v-if="mstResult" class="mst-info">
          <div class="mst-weight">
            <span class="material-icons">scale</span>
            <span>Poids total : {{ mstResult.totalWeight }}s</span>
          </div>
          <div class="mst-edges">
            <span class="material-icons">timeline</span>
            <span>{{ mstResult.edgeCount }} arêtes</span>
          </div>
        </div>
        
        <!-- Contrôles d'animation -->
        <div v-if="mstResult" class="animation-controls">
          <div class="animation-buttons">
            <button 
              type="button" 
              class="animation-button"
              @click="startMSTAnimation"
              :disabled="isAnimating"
            >
              <span class="material-icons">play_arrow</span>
              <span>Animation</span>
            </button>
            
            <button 
              v-if="isAnimating" 
              type="button" 
              class="animation-button stop"
              @click="stopAnimation"
            >
              <span class="material-icons">stop</span>
              <span>Arrêter</span>
            </button>
            
            <button 
              type="button" 
              class="animation-button"
              @click="resetAnimation"
              :disabled="isAnimating"
            >
              <span class="material-icons">refresh</span>
              <span>Réinitialiser</span>
            </button>
          </div>
          
          <div class="manual-controls">
            <button 
              type="button" 
              class="step-button"
              @click="previousStep"
              :disabled="isAnimating || currentStep <= 0"
            >
              <span class="material-icons">skip_previous</span>
            </button>
            
            <div class="step-info">
              <span>Étape {{ currentStep }} / {{ mstResult.steps ? mstResult.steps.length : 0 }}</span>
              <div v-if="mstResult.steps && currentStep > 0 && currentStep <= mstResult.steps.length" class="current-step-info">
                <span>Poids actuel: {{ mstResult.steps[currentStep - 1]?.totalWeight || 0 }}s</span>
              </div>
            </div>
            
            <button 
              type="button" 
              class="step-button"
              @click="nextStep"
              :disabled="isAnimating || currentStep >= (mstResult.steps ? mstResult.steps.length : 0)"
            >
              <span class="material-icons">skip_next</span>
            </button>
          </div>
          
          <div class="speed-control">
            <label for="animation-speed">Vitesse:</label>
            <div class="speed-presets">
              <button 
                type="button" 
                class="speed-preset" 
                :class="{ active: animationSpeed === 20 }"
                @click="animationSpeed = 20"
              >
                Ultra
              </button>
              <button 
                type="button" 
                class="speed-preset" 
                :class="{ active: animationSpeed === 100 }"
                @click="animationSpeed = 100"
              >
                Rapide
              </button>
              <button 
                type="button" 
                class="speed-preset" 
                :class="{ active: animationSpeed === 500 }"
                @click="animationSpeed = 500"
              >
                Normal
              </button>
              <button 
                type="button" 
                class="speed-preset" 
                :class="{ active: animationSpeed === 1000 }"
                @click="animationSpeed = 1000"
              >
                Lent
              </button>
            </div>
            <input 
              id="animation-speed"
              type="range" 
              min="20" 
              max="2000" 
              step="20"
              v-model="animationSpeed"
              class="speed-slider"
            />
            <span class="speed-value">{{ animationSpeed }}ms</span>
          </div>
        </div>
        
        <button 
          v-if="mstResult && !mstDisplayed && !isAnimating" 
          type="button" 
          class="acpm-display-button"
          @click="displayMST"
        >
          <span class="material-icons">visibility</span>
          <span>Afficher Complet</span>
        </button>
        
        <button 
          v-if="mstDisplayed" 
          type="button" 
          class="acpm-hide-button"
          @click="hideMST"
        >
          <span class="material-icons">visibility_off</span>
          <span>Cacher</span>
        </button>
      </div>
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
import { useDestination } from '../composables/useDestination.js'

// Utiliser le composable pour la destination
const { selectedDestination } = useDestination()

const depart = ref('')
const arrivee = ref('')
const heure = ref('')
const timeType = ref('now') // 'departure', 'arrival', 'now'
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

// Variables pour l'ACPM
const loadingMST = ref(false)
const mstResult = ref(null)
const mstDisplayed = ref(false)
const isAnimating = ref(false)
const currentStep = ref(0)
const animationSpeed = ref(500) // ms par étape

// Injecter l'instance de la carte et la fonction d'affichage d'itinéraire
const mapInstance = inject('mapInstance', null)
const displayRouteOnMap = inject('displayRouteOnMap', null)

// Surveiller les changements de la destination sélectionnée
watch(selectedDestination, (newDestination) => {
  if (newDestination && newDestination.trim() !== '') {
    arrivee.value = newDestination;
  }
}, { immediate: true });

onMounted(async () => {
  // Initialiser l'heure par défaut à l'heure actuelle
  const now = new Date();
  const currentTime = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
  heure.value = currentTime;

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
    let url;
    let params = new URLSearchParams({
      depart: depart.value,
      arrivee: arrivee.value
    });
    
    // Choisir l'endpoint en fonction du type d'horaire
    if (timeType.value === 'now') {
      // Utiliser l'ancien endpoint pour les recherches sans horaire spécifique
      url = `/api/routes?${params.toString()}`;
    } else {
      // Utiliser le nouveau endpoint avec horaires
      url = `/api/routes-with-schedule?${params.toString()}`;
      
      if (timeType.value === 'departure' && heure.value) {
        params.append('departure_time', heure.value);
      } else if (timeType.value === 'arrival' && heure.value) {
        params.append('arrival_time', heure.value);
      }
      
      url = `/api/routes-with-schedule?${params.toString()}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
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
  // Masquer le trajet affiché et restaurer l'affichage complet
  hideRouteOnMap()
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

// ===== FONCTIONS ACPM =====

// Classe Union-Find pour l'algorithme de Kruskal
class UnionFind {
  constructor(vertices) {
    this.parent = new Map()
    this.rank = new Map()
    
    vertices.forEach(vertex => {
      this.parent.set(vertex, vertex)
      this.rank.set(vertex, 0)
    })
  }
  
  find(vertex) {
    if (this.parent.get(vertex) !== vertex) {
      this.parent.set(vertex, this.find(this.parent.get(vertex)))
    }
    return this.parent.get(vertex)
  }
  
  union(vertex1, vertex2) {
    const root1 = this.find(vertex1)
    const root2 = this.find(vertex2)
    
    if (root1 === root2) return false
    
    const rank1 = this.rank.get(root1)
    const rank2 = this.rank.get(root2)
    
    if (rank1 < rank2) {
      this.parent.set(root1, root2)
    } else if (rank1 > rank2) {
      this.parent.set(root2, root1)
    } else {
      this.parent.set(root2, root1)
      this.rank.set(root1, rank1 + 1)
    }
    
    return true
  }
}

// Algorithme de Kruskal pour calculer l'ACPM
function kruskalMST(edges, vertices) {
  console.log(`Calcul ACPM avec ${edges.length} arêtes et ${vertices.size} sommets`)
  
  // Trier les arêtes par poids croissant
  const sortedEdges = edges.sort((a, b) => a.weight - b.weight)
  
  const unionFind = new UnionFind(vertices)
  const mstEdges = []
  const steps = []
  let totalWeight = 0
  
  for (const edge of sortedEdges) {
    if (unionFind.union(edge.from, edge.to)) {
      mstEdges.push(edge)
      totalWeight += edge.weight
      
      // Enregistrer cette étape
      steps.push({
        edge: edge,
        edgesCount: mstEdges.length,
        totalWeight: Math.round(totalWeight),
        mstEdges: [...mstEdges]
      })
      
      // Si on a assez d'arêtes pour couvrir tous les sommets
      if (mstEdges.length === vertices.size - 1) {
        break
      }
    }
  }
  
  console.log(`ACPM calculé: ${mstEdges.length} arêtes, poids total: ${totalWeight}`)
  return {
    edges: mstEdges,
    totalWeight: Math.round(totalWeight),
    edgeCount: mstEdges.length,
    steps: steps
  }
}

// Fonction pour calculer l'ACPM
async function calculateMST() {
  if (loadingMST.value) return
  
  loadingMST.value = true
  mstResult.value = null
  
  try {
    console.log('Récupération des données du graphe pour ACPM...')
    
    // Récupérer les arêtes depuis l'API
    const response = await fetch('http://localhost:8000/api/unique/edges')
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`)
    }
    
    const data = await response.json()
    const edges = []
    const vertices = new Set()
    
    // Convertir les données GeoJSON en format pour l'algorithme
    data.features.forEach(feature => {
      const props = feature.properties
      
      // Utiliser seulement les connexions directes (pas les transferts pour l'ACPM)
      if (props.type === 'direct' && props.from_name && props.to_name) {
        const weight = props.travel_time || 120 // Poids par défaut si non spécifié
        
        edges.push({
          from: props.from_name,
          to: props.to_name,
          weight: weight,
          originalEdge: feature
        })
        
        vertices.add(props.from_name)
        vertices.add(props.to_name)
      }
    })
    
    console.log(`Données préparées: ${edges.length} arêtes, ${vertices.size} sommets`)
    
    if (edges.length === 0) {
      throw new Error('Aucune arête trouvée pour calculer l\'ACPM')
    }
    
    // Calculer l'ACPM avec Kruskal
    mstResult.value = kruskalMST(edges, vertices)
    
    console.log('ACPM calculé avec succès:', mstResult.value)
    
  } catch (error) {
    console.error('Erreur lors du calcul de l\'ACPM:', error)
    errorMessage.value = `Erreur ACPM: ${error.message}`
    
    // Effacer le message d'erreur après 5 secondes
    setTimeout(() => {
      errorMessage.value = ''
    }, 5000)
  } finally {
    loadingMST.value = false
  }
}

// Fonction pour afficher l'ACPM sur la carte
function displayMST() {
  if (!mstResult.value || !mapInstance.value) {
    console.error('Pas de résultat ACPM ou instance de carte non disponible')
    return
  }
  
  console.log('Affichage de l\'ACPM sur la carte')
  
  if (mapInstance.value.showMST) {
    mapInstance.value.showMST(mstResult.value)
    mstDisplayed.value = true
  } else {
    console.error('Fonction showMST non disponible sur l\'instance de carte')
  }
}

// Fonction pour cacher l'ACPM
function hideMST() {
  if (!mapInstance.value) {
    console.error('Instance de carte non disponible')
    return
  }
  
  console.log('Masquage de l\'ACPM')
  
  if (mapInstance.value.hideMST) {
    mapInstance.value.hideMST()
    mstDisplayed.value = false
  } else if (mapInstance.value.showAllElements) {
    mapInstance.value.showAllElements()
    mstDisplayed.value = false
  } else {
    console.error('Fonction hideMST non disponible sur l\'instance de carte')
  }
}

// ===== FONCTIONS ANIMATION ACPM =====

// Fonction pour démarrer l'animation progressive
function startMSTAnimation() {
  if (!mstResult.value || !mstResult.value.steps || mstResult.value.steps.length === 0) {
    console.error('Pas de données d\'étapes pour l\'animation')
    return
  }
  
  isAnimating.value = true
  currentStep.value = 0
  
  // Masquer l'ACPM complet s'il est affiché
  if (mstDisplayed.value) {
    hideMST()
  }
  
  // Centrer la vue sur l'ensemble de l'ACPM au début de l'animation
  if (mapInstance.value && mapInstance.value.centerOnMST) {
    mapInstance.value.centerOnMST(mstResult.value)
  }
  
  // Démarrer l'animation
  animateNextStep()
}

// Fonction pour animer l'étape suivante
function animateNextStep() {
  if (!isAnimating.value || !mstResult.value || !mstResult.value.steps) {
    return
  }
  
  const steps = mstResult.value.steps
  
  if (currentStep.value < steps.length) {
    const step = steps[currentStep.value]
    
    // Afficher l'étape actuelle sur la carte
    if (mapInstance.value && mapInstance.value.showMSTStep) {
      mapInstance.value.showMSTStep(step)
    }
    
    currentStep.value++
    
    // Programmer la prochaine étape
    if (currentStep.value < steps.length) {
      setTimeout(() => {
        animateNextStep()
      }, animationSpeed.value)
    } else {
      // Animation terminée
      setTimeout(() => {
        isAnimating.value = false
        mstDisplayed.value = true
      }, animationSpeed.value)
    }
  }
}

// Fonction pour passer à l'étape suivante manuellement
function nextStep() {
  if (!mstResult.value || !mstResult.value.steps || currentStep.value >= mstResult.value.steps.length) {
    return
  }
  
  const step = mstResult.value.steps[currentStep.value]
  
  // Afficher l'étape actuelle sur la carte
  if (mapInstance.value && mapInstance.value.showMSTStep) {
    mapInstance.value.showMSTStep(step)
  }
  
  currentStep.value++
  
  // Si c'était la dernière étape
  if (currentStep.value >= mstResult.value.steps.length) {
    mstDisplayed.value = true
  }
}

// Fonction pour revenir à l'étape précédente
function previousStep() {
  if (!mstResult.value || !mstResult.value.steps || currentStep.value <= 0) {
    return
  }
  
  currentStep.value--
  
  const step = mstResult.value.steps[currentStep.value]
  
  // Afficher l'étape actuelle sur la carte
  if (mapInstance.value && mapInstance.value.showMSTStep) {
    mapInstance.value.showMSTStep(step)
  }
  
  mstDisplayed.value = false
}

// Fonction pour arrêter l'animation
function stopAnimation() {
  isAnimating.value = false
}

// Fonction pour réinitialiser l'animation
function resetAnimation() {
  isAnimating.value = false
  currentStep.value = 0
  
  if (mapInstance.value && mapInstance.value.hideMST) {
    mapInstance.value.hideMST()
  }
  
  mstDisplayed.value = false
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
  gap: 8px;
}

.time-selector .material-icons {
  font-size: 16px;
  color: var(--sidebar-text-secondary);
}

.time-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.time-type-selector {
  display: flex;
  gap: 12px;
}

.time-type-selector label {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-size: 11px;
  color: var(--sidebar-text-secondary);
}

.time-type-selector input[type="radio"] {
  margin: 0;
  accent-color: var(--sidebar-accent);
}

.time-type-selector label:has(input:checked) {
  color: var(--sidebar-accent);
  font-weight: 500;
}

.time-input {
  background: transparent;
  border: 1px solid var(--sidebar-border);
  border-radius: 4px;
  color: var(--sidebar-text);
  font-size: 12px;
  padding: 4px 6px;
  width: 100%;
  transition: all 0.3s ease;
}

.time-input:focus {
  outline: none;
  border-color: var(--sidebar-accent);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.time-input.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--sidebar-bg-primary);
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

/* Styles pour la section ACPM */
.acpm-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 2px solid var(--sidebar-accent-hover);
}

.section-title {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  font-size: 16px;
  font-weight: 600;
}

.section-title .material-icons {
  margin-right: 10px;
  font-size: 20px;
  color: var(--sidebar-accent);
}

.acpm-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.acpm-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, #9b59b6, #8e44ad);
  color: var(--sidebar-button-text);
  border: none;
  border-radius: 20px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 140px;
}

.acpm-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.acpm-button:not(:disabled):hover {
  background: linear-gradient(90deg, #8e44ad, #7d3c98);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--sidebar-shadow);
}

.acpm-button .material-icons {
  font-size: 18px;
  margin-right: 6px;
}

.acpm-display-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, #27ae60, #2ecc71);
  color: white;
  border: none;
  border-radius: 15px;
  padding: 8px 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
}

.acpm-display-button:hover {
  background: linear-gradient(90deg, #229954, #27ae60);
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(39, 174, 96, 0.3);
}

.acpm-display-button .material-icons {
  font-size: 16px;
  margin-right: 4px;
}

.acpm-hide-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, #e74c3c, #c0392b);
  color: white;
  border: none;
  border-radius: 15px;
  padding: 8px 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
}

.acpm-hide-button:hover {
  background: linear-gradient(90deg, #c0392b, #a93226);
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(231, 76, 60, 0.3);
}

.acpm-hide-button .material-icons {
  font-size: 16px;
  margin-right: 4px;
}

.mst-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--sidebar-bg-secondary);
  border-radius: 8px;
  border-left: 4px solid #9b59b6;
}

.mst-weight, .mst-edges {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: var(--sidebar-text);
}

.mst-weight .material-icons, .mst-edges .material-icons {
  margin-right: 8px;
  font-size: 16px;
  color: var(--sidebar-accent);
}

.mst-weight {
  font-weight: 600;
  color: var(--sidebar-accent);
}

/* Styles pour les contrôles d'animation ACPM */
.animation-controls {
  margin-top: 15px;
  padding: 15px;
  background: var(--sidebar-bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--sidebar-accent-hover);
}

.animation-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.animation-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--sidebar-accent);
  color: var(--sidebar-button-text);
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
  min-width: 80px;
  justify-content: center;
}

.animation-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.animation-button:not(:disabled):hover {
  background: var(--sidebar-accent-hover);
  transform: translateY(-1px);
}

.animation-button.stop {
  background: var(--sidebar-danger);
}

.animation-button.stop:not(:disabled):hover {
  background: #dc2626;
}

.manual-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 8px;
  background: var(--sidebar-bg);
  border-radius: 6px;
}

.step-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--sidebar-accent);
  color: var(--sidebar-button-text);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
}

.step-button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.step-button:not(:disabled):hover {
  background: var(--sidebar-accent-hover);
  transform: scale(1.1);
}

.step-info {
  text-align: center;
  flex: 1;
  margin: 0 12px;
}

.step-info span {
  display: block;
  font-size: 12px;
  color: var(--sidebar-text);
  font-weight: 500;
}

.current-step-info {
  margin-top: 4px;
}

.current-step-info span {
  font-size: 11px;
  color: var(--sidebar-text-secondary);
  font-style: italic;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--sidebar-text);
}

.speed-control label {
  font-weight: 500;
  min-width: 50px;
}

.speed-slider {
  flex: 1;
  height: 4px;
  background: var(--sidebar-bg);
  border-radius: 2px;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
}

.speed-slider::-webkit-slider-thumb {
  appearance: none;
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: var(--sidebar-accent);
  border-radius: 50%;
  cursor: pointer;
}

.speed-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: var(--sidebar-accent);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.speed-presets {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}

.speed-preset {
  padding: 4px 8px;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  border: 1px solid var(--sidebar-accent-hover);
  border-radius: 4px;
  font-size: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  flex: 1;
}

.speed-preset:hover {
  background: var(--sidebar-accent-hover);
  color: var(--sidebar-button-text);
}

.speed-preset.active {
  background: var(--sidebar-accent);
  color: var(--sidebar-button-text);
  border-color: var(--sidebar-accent);
}

.speed-value {
  font-size: 11px;
  color: var(--sidebar-text-secondary);
  min-width: 45px;
}

/* Styles pour le dropdown personnalisé des stations */
.station-dropdown {
  position: absolute;
  top: calc(100% + 5px); /* Un peu plus d'espace depuis le formulaire */
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(20, 20, 20, 0.98); /* Plus foncé pour un look plus "pop-up" */
  border: 1px solid rgba(52, 152, 219, 0.7);
  border-radius: 8px;
  max-height: 300px;
  overflow-y: auto;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.6); /* Ombre plus prononcée */
  backdrop-filter: blur(10px); /* Effet de flou d'arrière-plan */
}

.station-option {
  padding: 12px 15px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  color: #ffffff;
  font-size: 14px;
}

.station-option:hover {
  background: rgba(52, 152, 219, 0.2);
  color: #3498db;
}

.station-option:last-child {
  border-bottom: none;
}
</style>
