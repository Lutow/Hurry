<template>
  <div id="map">
    <Sidebar />
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
import { onMounted, onUnmounted, ref, provide } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Sidebar from "./Sidebar.vue";

// Filtrage des doublons de transferts entre deux noms de stations
function filterUniqueTransfers(features) {
  const seen = new Set()
  return features.filter(f => {
    if (f.properties.type !== 'transfer') return true
    const key1 = `${f.properties.from_name}--${f.properties.to_name}`
    const key2 = `${f.properties.to_name}--${f.properties.from_name}` // bidirectionnel
    if (seen.has(key1) || seen.has(key2)) return false
    seen.add(key1)
    seen.add(key2)
    return true
  })
}

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
const map = ref(null)
const routeLayer = ref(null)  // Couche pour afficher les itinéraires
const allStations = ref([])  // Stocker toutes les stations pour le filtrage
const originalStationsData = ref(null)  // Sauvegarder les données originales des stations
const originalEdgesData = ref(null)  // Sauvegarder les données originales des arêtes
const routeDisplayed = ref(false)  // Indique si un trajet est actuellement affiché
const currentRoute = ref(null)  // Stocke le trajet actuellement affiché

// Fournir l'instance de carte aux composants enfants
provide('mapInstance', map)

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

    // Sauvegarder les données originales pour pouvoir les restaurer plus tard
    originalStationsData.value = geojson

    // Nettoyer la couche précédente si elle existe
    if (stationsLayer.value) {
      map.removeLayer(stationsLayer.value)
    }

    // Ajouter les stations à la carte avec leurs informations d'accessibilité
    stationsLayer.value = L.geoJSON(geojson, {
    pointToLayer: (feature, latlng) => {
    return L.circleMarker(latlng, {
      radius: 6,
      color: '#000000',
      fillColor: '#FFFFFF',
      fillOpacity: 1,
      weight: 3
      })
    },
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
      // Ne pas recharger les stations si un trajet est actuellement affiché
      if (routeDisplayed.value) {
        console.log('Trajet affiché, rechargement des stations ignoré')
        return
      }
      
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
            pointToLayer: (feature, latlng) => {
              return L.circleMarker(latlng, {
                radius: 6,
                color: '#000000',
                fillColor: '#FFFFFF',
                fillOpacity: 1,
                weight: 3
              })
            },
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

    //Filtrage frontend des transferts en double
    edgesGeojson.features = filterUniqueTransfers(edgesGeojson.features)

    // Sauvegarder les données originales pour pouvoir les restaurer plus tard
    originalEdgesData.value = edgesGeojson

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
          const travelTime = feature.properties.travel_time || 'N/A'
          popupContent += `
            <h4>🚇 Ligne ${routeName}</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Temps:</strong> ${travelTime}s</p>
            <p><strong>Type:</strong> Connexion directe</p>
          `
        } else if (feature.properties.type === 'transfer') {
          const transferTime = feature.properties.transfer_time || 'N/A'
          popupContent += `
            <h4>🔄 Correspondance</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Temps:</strong> ${transferTime}s</p>
            <p><strong>Type:</strong> Transfert</p>
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
  console.log("Chargement manuel des arêtes...")
  const mapInstance = document.getElementById('map')._leaflet_map
  if (mapInstance) {
    await loadUniqueEdges(mapInstance)
    console.log("Arêtes chargées manuellement")
  } else {
    console.error("Instance de carte non trouvée")
  }
}

const retryLoading = async () => {
  error.value = null
  await initMap()
}

const initMap = async () => {
  const mapInstance = L.map('map', {
    center: [48.8566, 2.3522],
    zoom: 12,
    zoomControl: false
  })

  L.control.zoom({ position: 'bottomright' }).addTo(mapInstance)

  // Vérification DOM
  setTimeout(() => {
    mapInstance.invalidateSize()
  }, 300)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(mapInstance)

  map.value = mapInstance // Injecter l'instance de carte ici

  await loadMapData(mapInstance)
  await loadUniqueEdges(mapInstance)  // Charger les arêtes uniques lors de l'initialisation
}

onMounted(async () => {
  await initMap()
  // Fournir l'instance de carte correctement après l'initialisation
  provide('mapInstance', map)
  
  // Ajouter les méthodes à l'instance de la carte après l'initialisation
  if (map.value) {
    map.value.showOnlyRoute = showOnlyRoute
    map.value.showAllElements = showAllElements
  }
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

// Fonction pour afficher un itinéraire sur la carte
const displayRouteOnMap = (route) => {
  console.log("Route sélectionnée pour affichage:", route);
  
  // Si une couche d'itinéraire existe déjà, la supprimer
  if (routeLayer.value && map.value) {
    map.value.removeLayer(routeLayer.value);
  }
  
  if (!map.value) {
    console.error("Carte non initialisée");
    return;
  }
  
  // Pour la version 1, on va juste mettre en évidence les stations du trajet
  // Dans une future version, on pourrait récupérer les coordonnées des segments et tracer des lignes
  
  // Créer un tableau de points pour les stations impliquées dans l'itinéraire
  const routeStations = [];
  
  // Pour chaque segment, ajouter les stations de départ et d'arrivée
  route.segments.forEach(segment => {
    routeStations.push({
      name: segment.from,
      type: 'segment-start',
      line: segment.line
    });
    
    routeStations.push({
      name: segment.to,
      type: 'segment-end',
      line: segment.line
    });
  });
  
  // TODO: Dans une future version, nous pourrions rechercher les coordonnées réelles des stations
  // et dessiner une ligne entre elles pour représenter le trajet complet
  
  console.log("Stations du trajet à afficher:", routeStations);
}

// Fonction pour afficher uniquement un trajet spécifique
const showOnlyRoute = (route) => {
  console.log('Affichage du trajet uniquement:', route)
  
  // Stocker le trajet courant et marquer qu'un trajet est affiché
  currentRoute.value = route
  routeDisplayed.value = true
  
  if (!originalStationsData.value || !originalEdgesData.value) {
    console.error('Données originales non disponibles')
    return
  }
  
  // Masquer toutes les couches existantes
  if (stationsLayer.value) {
    map.value.removeLayer(stationsLayer.value)
    stationsLayer.value = null
  }
  if (edgesLayer.value) {
    map.value.removeLayer(edgesLayer.value)
    edgesLayer.value = null
  }
  
  // Créer un ensemble des noms de stations du trajet
  const routeStationNames = new Set()
  // Stocker les segments pour l'affichage organisé
  const routeSegments = []
  
  // Extraire toutes les stations du trajet
  if (route.segments) {
    route.segments.forEach(segment => {
      routeStationNames.add(segment.from)
      routeStationNames.add(segment.to)
      
      // Ajouter les infos du segment pour l'affichage
      routeSegments.push({
        from: segment.from,
        to: segment.to,
        line: segment.line
      })
    })
  }
  
  console.log('Stations du trajet:', Array.from(routeStationNames))
  
  // Filtrer les stations pour ne garder que celles du trajet
  const routeStationsFeatures = originalStationsData.value.features.filter(feature =>
    routeStationNames.has(feature.properties.name)
  )
  
  console.log(`Stations filtrées: ${routeStationsFeatures.length} sur ${originalStationsData.value.features.length}`)
  
  // Créer une nouvelle couche pour les stations du trajet
  if (routeStationsFeatures.length > 0) {
    stationsLayer.value = L.geoJSON({
      type: 'FeatureCollection',
      features: routeStationsFeatures
    }, {
      pointToLayer: (feature, latlng) => {
        // Détermine le rôle de la station dans le trajet pour personnaliser l'affichage
        const stationName = feature.properties.name
        
        // Vérifier si la station est un départ ou une arrivée de trajet
        const isStartOfRoute = route.segments[0].from === stationName
        const isEndOfRoute = route.segments[route.segments.length - 1].to === stationName
        
        // Mise en forme selon le rôle de la station
        if (isStartOfRoute) {
          return L.circleMarker(latlng, {
            radius: 10,
            fillColor: '#2ecc71', // Vert pour le départ
            color: '#27ae60',
            weight: 3,
            opacity: 1,
            fillOpacity: 0.9
          })
        } else if (isEndOfRoute) {
          return L.circleMarker(latlng, {
            radius: 10,
            fillColor: '#e74c3c', // Rouge pour l'arrivée
            color: '#c0392b',
            weight: 3,
            opacity: 1,
            fillOpacity: 0.9
          })
        } else {
          // Station intermédiaire
          return L.circleMarker(latlng, {
            radius: 8,
            fillColor: '#3498db', // Bleu pour intermédiaire
            color: '#2980b9',
            weight: 3,
            opacity: 1,
            fillOpacity: 0.9
          })
        }
      },
      onEachFeature: (feature, layer) => {
        const stationName = feature.properties.name
        
        // Vérifier le type de station dans l'itinéraire
        const isStartOfRoute = route.segments[0].from === stationName
        const isEndOfRoute = route.segments[route.segments.length - 1].to === stationName
        
        let stationType = ''
        if (isStartOfRoute) {
          stationType = '<span class="station-type-start">Station de départ</span>'
        } else if (isEndOfRoute) {
          stationType = '<span class="station-type-end">Station d\'arrivée</span>'
        } else {
          stationType = '<span class="station-type-transfer">Correspondance</span>'
        }
        
        layer.bindPopup(`
          <div class="station-popup highlighted">
            <h4>📍 ${stationName}</h4>
            <p><strong>${stationType}</strong></p>
          </div>
        `)
      }
    })
    
    stationsLayer.value.addTo(map.value)
  }
  
  // Filtrer les arêtes pour ne garder que celles du trajet
  const routeEdgesFeatures = []
  
  if (route.segments) {
    route.segments.forEach(segment => {
      // Trouver les arêtes correspondant à ce segment
      const matchingEdges = originalEdgesData.value.features.filter(feature => {
        const fromName = feature.properties.from_name
        const toName = feature.properties.to_name
        
        return (
          (fromName === segment.from && toName === segment.to) ||
          (fromName === segment.to && toName === segment.from) // Bidirectionnel
        )
      })
      
      routeEdgesFeatures.push(...matchingEdges)
    })
  }
  
  console.log(`Arêtes filtrées: ${routeEdgesFeatures.length} arêtes trouvées`)
  
  // Créer une nouvelle couche pour les arêtes du trajet
  if (routeEdgesFeatures.length > 0) {
    edgesLayer.value = L.geoJSON({
      type: 'FeatureCollection',
      features: routeEdgesFeatures
    }, {
      style: (feature) => {
        const edgeType = feature.properties.type
        // Utiliser la couleur de la ligne pour une meilleure correspondance visuelle
        const color = feature.properties.color || '#e74c3c'
        
        // Rechercher le segment correspondant pour adapter le style
        const fromName = feature.properties.from_name
        const toName = feature.properties.to_name
        const isFirstSegment = route.segments[0].from === fromName && route.segments[0].to === toName
        const isLastSegment = route.segments[route.segments.length-1].from === fromName && route.segments[route.segments.length-1].to === toName

        if (edgeType === 'direct') {
          // Style pour les connexions directes (sections de ligne de métro)
          return {
            color: color,
            weight: 6, // Plus épais pour une meilleure visibilité
            opacity: 1,
            smoothFactor: 1,
            // Effet d'animation pour les premiers/derniers segments
            dashArray: (isFirstSegment || isLastSegment) ? null : null,
            lineCap: 'round'
          }
        } else if (edgeType === 'transfer') {
          // Style pour les correspondances
          return {
            color: '#FF6B35',
            weight: 4,
            opacity: 1,
            dashArray: '10, 5', // Tirets plus visibles
            smoothFactor: 1,
            lineCap: 'round'
          }
        } else {
          // Style par défaut
          return {
            color: '#e74c3c',
            weight: 5,
            opacity: 1
          }
        }
      },
      onEachFeature: (feature, layer) => {
        let popupContent = `<div class="edge-popup highlighted">`

        if (feature.properties.type === 'direct') {
          const routeName = feature.properties.route_short_name || 'N/A'
          const travelTime = feature.properties.travel_time || 'N/A'
          popupContent += `
            <h4>🚇 Ligne ${routeName} - TRAJET SÉLECTIONNÉ</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Temps:</strong> ${travelTime}s</p>
          `
        } else if (feature.properties.type === 'transfer') {
          const transferTime = feature.properties.transfer_time || 'N/A'
          popupContent += `
            <h4>🔄 Correspondance - TRAJET SÉLECTIONNÉ</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Temps:</strong> ${transferTime}s</p>
          `
        }

        popupContent += `</div>`
        layer.bindPopup(popupContent)
      }
    })
    
    edgesLayer.value.addTo(map.value)
    
    // Déplacer les stations au-dessus des arêtes
    if (stationsLayer.value) {
      stationsLayer.value.bringToFront()
    }
  }
}

// Fonction pour réafficher tous les éléments
const showAllElements = () => {
  console.log('Réaffichage de tous les éléments')
  
  // Réinitialiser l'état du trajet affiché
  routeDisplayed.value = false
  currentRoute.value = null
  
  // Supprimer les couches actuelles
  if (stationsLayer.value) {
    map.value.removeLayer(stationsLayer.value)
    stationsLayer.value = null
  }
  if (edgesLayer.value) {
    map.value.removeLayer(edgesLayer.value)
    edgesLayer.value = null
  }
  
  // Restaurer les couches originales si disponibles
  if (originalStationsData.value) {
    stationsLayer.value = L.geoJSON(originalStationsData.value, {
      pointToLayer: (feature, latlng) => {
        return L.circleMarker(latlng, {
          radius: 6,
          color: '#000000',
          fillColor: '#FFFFFF',
          fillOpacity: 1,
          weight: 3
        })
      },
      onEachFeature: (feature, layer) => {
        let popupContent = `<strong>${feature.properties.name || feature.properties.id}</strong>`;

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

        if (feature.properties.platform_code) {
          popupContent += `<br>Plateforme: ${feature.properties.platform_code}`;
        }

        if (feature.properties.zone_id) {
          popupContent += `<br>Zone: ${feature.properties.zone_id}`;
        }

        layer.bindPopup(popupContent);
      }
    })
    
    stationsLayer.value.addTo(map.value)
  }
  
  if (originalEdgesData.value && showEdges.value) {
    edgesLayer.value = L.geoJSON(originalEdgesData.value, {
      style: (feature) => {
        const edgeType = feature.properties.type
        const color = feature.properties.color || '#CCCCCC'

        if (edgeType === 'direct') {
          return {
            color: color,
            weight: 3,
            opacity: 0.8,
            smoothFactor: 1
          }
        } else if (edgeType === 'transfer') {
          return {
            color: '#FF0000',
            weight: 2,
            opacity: 0.6,
            dashArray: '5, 5',
            smoothFactor: 1
          }
        } else {
          return {
            color: '#CCCCCC',
            weight: 2,
            opacity: 0.5
          }
        }
      },
      onEachFeature: (feature, layer) => {
        let popupContent = `<div class="edge-popup">`

        if (feature.properties.type === 'direct') {
          const routeName = feature.properties.route_short_name || 'N/A'
          const travelTime = feature.properties.travel_time || 'N/A'
          popupContent += `
            <h4>🚇 Ligne ${routeName}</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Temps:</strong> ${travelTime}s</p>
            <p><strong>Type:</strong> Connexion directe</p>
          `
        } else if (feature.properties.type === 'transfer') {
          const transferTime = feature.properties.transfer_time || 'N/A'
          popupContent += `
            <h4>🔄 Correspondance</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Temps:</strong> ${transferTime}s</p>
            <p><strong>Type:</strong> Transfert</p>
          `
        }

        popupContent += `</div>`
        layer.bindPopup(popupContent)
      }
    })
    
    edgesLayer.value.addTo(map.value)
    
    // Déplacer les stations au-dessus des arêtes
    if (stationsLayer.value) {
      stationsLayer.value.bringToFront()
    }
  }
}

// Ajouter les nouvelles méthodes à l'instance de la carte
// Cette section a été déplacée vers onMounted() pour s'assurer que map.value existe
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

/* Styles pour les éléments mis en évidence */
:deep(.edge-popup.highlighted) {
  background-color: rgba(231, 76, 60, 0.1);
  border: 2px solid #e74c3c;
  border-radius: 5px;
  padding: 10px;
}

:deep(.edge-popup.highlighted h4) {
  color: #c0392b;
  font-weight: bold;
}

:deep(.station-popup.highlighted) {
  background-color: rgba(231, 76, 60, 0.1);
  border: 2px solid #e74c3c;
  border-radius: 5px;
  padding: 10px;
}

:deep(.station-popup.highlighted h4) {
  color: #c0392b;
  font-weight: bold;
}

:deep(.station-type-start) {
  color: #2ecc71;
  font-weight: bold;
  display: block;
  padding: 5px;
  background-color: rgba(46, 204, 113, 0.1);
  border-radius: 4px;
  margin-top: 5px;
}

:deep(.station-type-end) {
  color: #e74c3c;
  font-weight: bold;
  display: block;
  padding: 5px;
  background-color: rgba(231, 76, 60, 0.1);
  border-radius: 4px;
  margin-top: 5px;
}

:deep(.station-type-transfer) {
  color: #3498db;
  font-weight: bold;
  display: block;
  padding: 5px;
  background-color: rgba(52, 152, 219, 0.1);
  border-radius: 4px;
  margin-top: 5px;
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
