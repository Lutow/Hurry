<template>
  <div id="map">
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <div class="loading-text">Chargement des stations de métro en cours... {{ elapsedTime }}s</div>
    </div>
    <div v-if="error" class="error-message">
      <div class="error-icon">⚠️</div>
      <div>{{ error }}</div>
      <button @click="retryLoading" class="retry-button">Réessayer</button>
    </div>
    <div v-if="loadingCompleted" class="loading-completed">
      Chargement terminé en {{ finalTime }} secondes
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const loading = ref(false)
const loadingCompleted = ref(false)
const error = ref(null)
const elapsedTime = ref(0)
const finalTime = ref(0)
const timerInterval = ref(null)

const startTimer = () => {
  elapsedTime.value = 0
  timerInterval.value = setInterval(() => {
    elapsedTime.value++
  }, 1000)
}

const stopTimer = () => {
  clearInterval(timerInterval.value)
  finalTime.value = elapsedTime.value
}

// Variables réactives pour la gestion des couches sur la carte
const stationsLayer = ref(null)
const edgesLayer = ref(null)  // Nouvelle couche pour les arêtes
const moveEndListener = ref(null)
const zoomStartListener = ref(null)  // Nouvel écouteur pour le début de zoom
const moveStartListener = ref(null)  // Nouvel écouteur pour le début de déplacement
const currentRequest = ref(null)
const currentEdgesRequest = ref(null)  // Requête pour les arêtes
const loadingIndicator = ref(null)
const updatingStations = ref(false)  // Nouvelle variable pour suivre l'état de mise à jour des stations
const showEdges = ref(true)  // Contrôler l'affichage des arêtes

const hideStationsLayer = () => {
  if (stationsLayer.value && !updatingStations.value) {
    updatingStations.value = true
    if (stationsLayer.value.options) {
      // Si la couche a des options d'opacité, on peut la rendre invisible
      stationsLayer.value.setStyle({ opacity: 0, fillOpacity: 0 })
    } else {
      // Sinon, on peut essayer de la masquer directement
      stationsLayer.value.getContainer()?.style.setProperty('display', 'none')
    }
    console.log('Stations masquées pendant la mise à jour')
  }
}

const loadMapData = async (map) => {
  loading.value = true
  error.value = null
  startTimer()
  
  try {
    // Récupérer les limites de la carte
    const bounds = map.getBounds()
    const latMin = bounds.getSouth()
    const latMax = bounds.getNorth()
    const lonMin = bounds.getWest()
    const lonMax = bounds.getEast()
    
    // Utiliser la nouvelle API pour ne charger que les stations dans la zone visible
    const url = `http://localhost:8000/geo/stops_by_zone?lat_min=${latMin}&lat_max=${latMax}&lon_min=${lonMin}&lon_max=${lonMax}`
    
    // Annuler la requête précédente si elle existe
    if (currentRequest.value) {
      console.log("Annulation de la requête précédente")
      currentRequest.value.abort()
    }
    
    // Créer un contrôleur d'annulation pour cette requête
    const controller = new AbortController()
    currentRequest.value = controller
    
    const res = await fetch(url, { signal: controller.signal }).catch(err => {
      if (err.name === 'AbortError') {
        console.log('Requête annulée')
        return null
      }
      throw err
    })
    
    // Si la requête a été annulée, arrêter le traitement
    if (!res) return
    
    if (!res.ok) {
      throw new Error(`Erreur HTTP: ${res.status}`)
    }
    const geojson = await res.json()
    
    // Si le backend a renvoyé des métadonnées sur le temps de traitement, les utiliser
    if (geojson.metadata && geojson.metadata.processing_time) {
      finalTime.value = geojson.metadata.processing_time;
      console.log(`Traitement côté serveur: ${finalTime.value}s pour ${geojson.metadata.number_of_stations} stations`);
    }
    
    // Nettoyer la couche précédente si elle existe
    if (stationsLayer.value) {
      map.removeLayer(stationsLayer.value)
    }
    
    // Ajouter les stations à la carte avec leurs informations d'accessibilité
    stationsLayer.value = L.geoJSON(geojson, {
      onEachFeature: (feature, layer) => {
        // Construire le contenu du popup avec les informations d'accessibilité
        let popupContent = `<strong>${feature.properties.name || feature.properties.id}</strong>`;
        
        // Ajouter les informations d'accessibilité si disponibles
        if (feature.properties.wheelchair_boarding !== undefined) {
          const accessibilityStatus = {
            '0': 'Information non disponible',
            '1': 'Accessible aux fauteuils roulants',
            '2': 'Non accessible aux fauteuils roulants'
          }[feature.properties.wheelchair_boarding] || 'Statut inconnu';
          
          popupContent += `<br><span class="accessibility-info">
            <i class="accessibility-icon">♿</i> ${accessibilityStatus}
          </span>`;
        }
        
        // Ajouter d'autres informations utiles si disponibles
        if (feature.properties.platform_code) {
          popupContent += `<br>Plateforme: ${feature.properties.platform_code}`;
        }
        
        if (feature.properties.zone_id) {
          popupContent += `<br>Zone : ${feature.properties.zone_id}`;
        }
        
        layer.bindPopup(popupContent);
      }
    })
    
    // Ajouter la couche à la carte et réinitialiser l'état
    stationsLayer.value.addTo(map)
    updatingStations.value = false
    
    // Nettoyer les anciens écouteurs d'événement s'ils existent
    if (moveEndListener.value) {
      map.off('moveend', moveEndListener.value)
    }
    if (zoomStartListener.value) {
      map.off('zoomstart', zoomStartListener.value)
    }
    if (moveStartListener.value) {
      map.off('movestart', moveStartListener.value)
    }
    
    // Créer de nouveaux écouteurs d'événement pour le début de zoom et de déplacement
    const onZoomStart = () => {
      hideStationsLayer()
    }
    
    const onMoveStart = () => {
      hideStationsLayer()
    }
    
    // Créer un nouvel écouteur d'événement pour la fin du déplacement de la carte
    const onMoveEnd = async () => {
      const newBounds = map.getBounds()
      const newLatMin = newBounds.getSouth()
      const newLatMax = newBounds.getNorth()
      const newLonMin = newBounds.getWest()
      const newLonMax = newBounds.getEast()
      
      // Vérifier si la nouvelle zone est très différente de la précédente pour éviter trop de requêtes
      const latDiff = Math.abs(newLatMax - latMax) + Math.abs(newLatMin - latMin)
      const lonDiff = Math.abs(newLonMax - lonMax) + Math.abs(newLonMin - lonMin)
      
      if (latDiff > 0.01 || lonDiff > 0.01) {  // Seuil arbitraire pour éviter les requêtes inutiles
        try {
          // Annuler la requête précédente si elle existe
          if (currentRequest.value) {
            currentRequest.value.abort()
          }
          
          // Supprimer l'indicateur de chargement précédent s'il existe
          if (loadingIndicator.value && loadingIndicator.value.parentNode) {
            document.body.removeChild(loadingIndicator.value)
          }
          
          // Afficher une petite notification de chargement
          const loadingDiv = document.createElement('div')
          loadingDiv.className = 'mini-loading'
          loadingDiv.innerHTML = 'Chargement des stations...'
          document.body.appendChild(loadingDiv)
          loadingIndicator.value = loadingDiv
          
          // Créer un nouveau contrôleur d'annulation
          const controller = new AbortController()
          currentRequest.value = controller
          
          // Charger les nouvelles stations
          const newUrl = `http://localhost:8000/geo/stops_by_zone?lat_min=${newLatMin}&lat_max=${newLatMax}&lon_min=${newLonMin}&lon_max=${newLonMax}`
          const newRes = await fetch(newUrl, { signal: controller.signal }).catch(err => {
            if (err.name === 'AbortError') {
              console.log('Requête annulée')
              return null
            }
            throw err
          })
          
          // Si la requête a été annulée, arrêter le traitement
          if (!newRes) {
            // Nettoyer l'indicateur de chargement
            if (loadingIndicator.value && loadingIndicator.value.parentNode) {
              document.body.removeChild(loadingIndicator.value)
              loadingIndicator.value = null
            }
            return
          }
          
          if (!newRes.ok) throw new Error(`Erreur HTTP: ${newRes.status}`)
          const newGeojson = await newRes.json()
          
          // Supprimer la couche précédente
          if (stationsLayer.value) {
            map.removeLayer(stationsLayer.value)
          }
          
          // Ajouter les nouvelles stations avec leurs informations d'accessibilité
          stationsLayer.value = L.geoJSON(newGeojson, {
            onEachFeature: (feature, layer) => {
              // Construire le contenu du popup avec les informations d'accessibilité
              let popupContent = `<strong>${feature.properties.name || feature.properties.id}</strong>`;
              
              // Ajouter les informations d'accessibilité si disponibles
              if (feature.properties.wheelchair_boarding !== undefined) {
                const accessibilityStatus = {
                  '0': 'Information non disponible',
                  '1': 'Accessible aux fauteuils roulants',
                  '2': 'Non accessible aux fauteuils roulants'
                }[feature.properties.wheelchair_boarding] || 'Statut inconnu';
                
                popupContent += `<br><span class="accessibility-info">
                  <i class="accessibility-icon">♿</i> ${accessibilityStatus}
                </span>`;
              }
              
              // Ajouter d'autres informations utiles si disponibles
              if (feature.properties.platform_code) {
                popupContent += `<br>Plateforme: ${feature.properties.platform_code}`;
              }
              
              if (feature.properties.zone_id) {
                popupContent += `<br>Zone: ${feature.properties.zone_id}`;
              }
              
              layer.bindPopup(popupContent);
            }
          })
          
          // Ajouter la couche à la carte et réinitialiser l'état
          stationsLayer.value.addTo(map)
          updatingStations.value = false
          
          // Supprimer l'indicateur de chargement
          if (loadingIndicator.value && loadingIndicator.value.parentNode) {
            document.body.removeChild(loadingIndicator.value)
            loadingIndicator.value = null
          }
          
          console.log(`Chargées ${newGeojson.metadata?.number_of_stations || 0} stations dans la nouvelle zone`)
        } catch (err) {
          console.error("Erreur lors du chargement des nouvelles stations:", err)
          
          // S'assurer que l'indicateur de chargement est supprimé en cas d'erreur
          if (loadingIndicator.value && loadingIndicator.value.parentNode) {
            document.body.removeChild(loadingIndicator.value)
            loadingIndicator.value = null
          }
        }
      }
    }
    
    // Stocker les écouteurs d'événement pour pouvoir les supprimer plus tard
    moveEndListener.value = onMoveEnd
    zoomStartListener.value = onZoomStart
    moveStartListener.value = onMoveStart
    
    // Attacher les écouteurs d'événement à la carte
    map.on('moveend', onMoveEnd)
    map.on('zoomstart', onZoomStart)
    map.on('movestart', onMoveStart)
    
    // Charger les arêtes uniques après avoir chargé les stations
    await loadUniqueEdges(map)
    
    loading.value = false
    loadingCompleted.value = true
    stopTimer()
    
    // Cache la notification de succès après 5 secondes
    setTimeout(() => {
      loadingCompleted.value = false
    }, 5000)
  } catch (err) {
    error.value = `Erreur lors du chargement des données: ${err.message}`
    loading.value = false
    stopTimer()
  }
}

// Fonction pour charger les arêtes uniques du métro
const loadUniqueEdges = async (map) => {
  if (!showEdges.value) return

  console.log("Chargement des arêtes uniques...")

  try {
    // Annuler la requête d'arêtes précédente si elle existe
    if (currentEdgesRequest.value) {
      console.log("Annulation de la requête d'arêtes précédente")
      currentEdgesRequest.value.abort()
    }

    // Créer un contrôleur d'annulation pour cette requête
    const controller = new AbortController()
    currentEdgesRequest.value = controller

    const url = `http://localhost:8000/api/unique/edges`
    const res = await fetch(url, { signal: controller.signal }).catch(err => {
      if (err.name === 'AbortError') {
        console.log('Requête d\'arêtes annulée')
        return null
      }
      throw err
    })

    // Si la requête a été annulée, arrêter le traitement
    if (!res) return

    if (!res.ok) {
      throw new Error(`Erreur HTTP pour les arêtes: ${res.status}`)
    }

    const edgesGeojson = await res.json()
    console.log(`Chargées ${edgesGeojson.features?.length || 0} arêtes depuis l'API`)

    // Nettoyer la couche d'arêtes précédente si elle existe
    if (edgesLayer.value) {
      map.removeLayer(edgesLayer.value)
    }

    // Créer la couche d'arêtes avec styles différents selon le type
    edgesLayer.value = L.geoJSON(edgesGeojson, {
      style: (feature) => {
        const edgeType = feature.properties.type
        const color = feature.properties.color || '#CCCCCC'

        if (edgeType === 'direct') {
          // Arêtes directes (lignes de métro) - plus épaisses et colorées
          return {
            color: color,
            weight: 3,
            opacity: 0.8,
            smoothFactor: 1
          }
        } else if (edgeType === 'transfer') {
          // Transferts - plus fins et en rouge
          return {
            color: '#FF0000',
            weight: 2,
            opacity: 0.6,
            dashArray: '5, 5', // Ligne pointillée pour les transferts
            smoothFactor: 1
          }
        } else {
          // Style par défaut
          return {
            color: '#CCCCCC',
            weight: 2,
            opacity: 0.5
          }
        }
      },
      onEachFeature: (feature, layer) => {
        // Popup avec informations sur l'arête
        let popupContent = `<div class="edge-popup">`
        
        if (feature.properties.type === 'direct') {
          const routeName = feature.properties.route_short_name || 'N/A'
          popupContent += `
            <h4>🚇 Ligne ${routeName}</h4>
            <p><strong>De :</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers :</strong> ${feature.properties.to_name}</p>
            <p><strong>Type :</strong> Connexion directe</p>
          `
        } else if (feature.properties.type === 'transfer') {
          const transferTime = feature.properties.transfer_time || 'N/A'
          popupContent += `
            <h4>🔄 Correspondance</h4>
            <p><strong>De :</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers :</strong> ${feature.properties.to_name}</p>
            <p><strong>Temps :</strong> ${transferTime}s</p>
            <p><strong>Type :</strong> Transfert</p>
          `
        }
        
        popupContent += `</div>`
        layer.bindPopup(popupContent)
      }
    })

    // Ajouter la couche d'arêtes à la carte (en dessous des stations)
    edgesLayer.value.addTo(map)
    
    // Déplacer les stations au-dessus des arêtes
    if (stationsLayer.value) {
      stationsLayer.value.bringToFront()
    }

    console.log(`Arêtes chargées avec succès: ${edgesGeojson.metadata?.total_edges || 'N/A'} arêtes`)

  } catch (err) {
    console.error("Erreur lors du chargement des arêtes:", err)
  }
}

// Fonction pour charger manuellement les arêtes (pour debug)
const loadEdgesManually = async () => {
  console.log("🔄 Chargement manuel des arêtes...")
  const mapInstance = document.getElementById('map')._leaflet_map
  if (mapInstance) {
    await loadUniqueEdges(mapInstance)
    console.log("✅ Arêtes chargées manuellement")
  } else {
    console.error("❌ Instance de carte non trouvée")
  }
}

const retryLoading = async () => {
  error.value = null
  await initMap()
}

const initMap = async () => {
  const map = L.map('map').setView([48.8566, 2.3522], 12)

  // Vérification DOM
  setTimeout(() => {
    map.invalidateSize()
  }, 300)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)

  await loadMapData(map)
  await loadUniqueEdges(map)  // Charger les arêtes uniques lors de l'initialisation
}

onMounted(async () => {
  await initMap()
})

// Nettoyage des ressources lorsque le composant est démonté
onUnmounted(() => {
  // Annuler la requête en cours si elle existe
  if (currentRequest.value) {
    currentRequest.value.abort()
  }
  
  // Annuler la requête d'arêtes en cours si elle existe
  if (currentEdgesRequest.value) {
    currentEdgesRequest.value.abort()
  }
  
  // Nettoyer l'indicateur de chargement
  if (loadingIndicator.value && loadingIndicator.value.parentNode) {
    document.body.removeChild(loadingIndicator.value)
  }
  
  // Arrêter le timer
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
  }
  
  // Récupérer l'instance de carte si elle existe
  const mapElement = document.getElementById('map')
  if (mapElement && mapElement._leaflet_id) {
    const map = L.DomUtil.get(mapElement)
    
    // Supprimer les écouteurs d'événements
    if (moveEndListener.value) {
      map.off('moveend', moveEndListener.value)
    }
    if (zoomStartListener.value) {
      map.off('zoomstart', zoomStartListener.value)
    }
    if (moveStartListener.value) {
      map.off('movestart', moveStartListener.value)
    }
  }
})

const toggleEdges = async () => {
  showEdges.value = !showEdges.value
  
  if (showEdges.value) {
    // Afficher les arêtes
    const mapInstance = document.getElementById('map')._leaflet_map
    if (mapInstance) {
      await loadUniqueEdges(mapInstance)
    }
  } else {
    // Masquer les arêtes
    if (edgesLayer.value) {
      const mapInstance = document.getElementById('map')._leaflet_map
      if (mapInstance) {
        mapInstance.removeLayer(edgesLayer.value)
      }
      edgesLayer.value = null
    }
  }
}
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

.loading-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  text-align: center;
  max-width: 80%;
}

.loading-spinner {
  border: 5px solid #f3f3f3;
  border-top: 5px solid #3498db;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  animation: spin 2s linear infinite;
  margin: 0 auto 15px;
}

.loading-text {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.error-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
  background-color: rgba(255, 220, 220, 0.95);
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  text-align: center;
  max-width: 80%;
  color: #d32f2f;
}

.error-icon {
  font-size: 32px;
  margin-bottom: 10px;
}

.retry-button {
  margin-top: 15px;
  padding: 8px 16px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.retry-button:hover {
  background-color: #388e3c;
}

.loading-completed {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
  background-color: rgba(76, 175, 80, 0.9);
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  font-weight: bold;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.mini-loading {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 5px 15px;
  border-radius: 15px;
  font-size: 12px;
  z-index: 1000;
}

/* Styles pour les informations d'accessibilité dans le popup */
:deep(.accessibility-info) {
  display: block;
  margin-top: 5px;
  padding: 3px 5px;
  border-radius: 3px;
  background-color: #f5f5f5;
}

:deep(.accessibility-icon) {
  margin-right: 5px;
  font-style: normal;
}

/* Couleurs en fonction de l'accessibilité */
:deep(.accessible) {
  background-color: rgba(76, 175, 80, 0.2);
}

:deep(.not-accessible) {
  background-color: rgba(244, 67, 54, 0.2);
}

:deep(.unknown-accessibility) {
  background-color: rgba(255, 152, 0, 0.2);
}

/* Styles pour les popups des arêtes */
.edge-popup {
  font-size: 14px;
  line-height: 1.4;
}

.edge-popup h4 {
  margin: 0 0 5px 0;
  font-size: 16px;
  color: #333;
}

.edge-popup p {
  margin: 2px 0;
  color: #666;
}

/* Styles pour les contrôles de la carte */
.map-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.edges-toggle-button {
  background-color: white;
  border: 2px solid #ccc;
  padding: 10px 15px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.3s ease;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}

.edges-toggle-button:hover {
  background-color: #f0f0f0;
  border-color: #999;
}

.edges-toggle-button.active {
  background-color: #3498db;
  color: white;
  border-color: #2980b9;
}

.edges-toggle-button.active:hover {
  background-color: #2980b9;
}

.manual-load-button {
  background-color: #27ae60;
  color: white;
  border: 2px solid #229954;
  padding: 8px 12px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}

.manual-load-button:hover {
  background-color: #229954;
}
</style>
