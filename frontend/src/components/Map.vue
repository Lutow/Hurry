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
import { onMounted, onUnmounted, ref, provide, watch } from 'vue'
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
const mstDisplayed = ref(false)  // Indique si l'ACPM est actuellement affiché
const mstLayer = ref(null)  // Couche pour afficher l'ACPM
const currentMST = ref(null)  // Stocke l'ACPM actuellement affiché

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
    map.value.showMST = showMST
    map.value.showMSTStep = showMSTStep
    map.value.centerOnMST = centerOnMST
    map.value.hideMST = hideMST
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
  
  // DÉSACTIVER LE LAZY LOADING pendant l'affichage du trajet
  if (moveEndListener.value) {
    map.value.off('moveend', moveEndListener.value)
  }
  if (zoomStartListener.value) {
    map.value.off('zoomstart', zoomStartListener.value)
  }
  if (moveStartListener.value) {
    map.value.off('movestart', moveStartListener.value)
  }
  
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
  
  // NOUVELLE LOGIQUE UNIFIÉE : utiliser le detailed_path si disponible (trajets avec horaires)
  // ou construire à partir des segments (trajets sans horaires)
  let segmentsToProcess = []
  
  if (route.detailed_path && route.detailed_path.length > 0) {
    // Trajets avec horaires : utiliser detailed_path
    console.log('Trajet avec horaires - utilisation de detailed_path:', route.detailed_path)
    segmentsToProcess = route.detailed_path
  } else if (route.segments) {
    // Trajets sans horaires : utiliser segments
    console.log('Trajet sans horaires - utilisation de segments:', route.segments)
    segmentsToProcess = route.segments
  }
  
  // Extraire toutes les stations du trajet
  segmentsToProcess.forEach((segment, index) => {
    console.log(`Segment ${index}:`, segment)
    
    // Gérer les deux formats : trajets avec horaires (from_station/to_station) et sans horaires (from/to)
    const fromStation = segment.from_station || segment.from
    const toStation = segment.to_station || segment.to
    const lineInfo = segment.line
    
    console.log(`  fromStation: "${fromStation}", toStation: "${toStation}", line: "${lineInfo}"`)
    
    if (fromStation && toStation) {
      routeStationNames.add(fromStation)
      routeStationNames.add(toStation)
      
      // Ajouter les infos du segment pour l'affichage
      routeSegments.push({
        from: fromStation,
        to: toStation,
        line: lineInfo
      })
    }
  })
  
  console.log('Stations du trajet extraites:', Array.from(routeStationNames))
  console.log('Segments du trajet:', routeSegments)
  
  // Filtrer les arêtes pour ne garder que celles du trajet
  const routeEdgesFeatures = []
  
  // Utiliser les segments traités uniformément
  segmentsToProcess.forEach(segment => {
    const fromStation = segment.from_station || segment.from
    const toStation = segment.to_station || segment.to
    const lineInfo = segment.line
    
    console.log(`Traitement du segment: ${fromStation} -> ${toStation} (ligne: ${lineInfo})`)
    
    // Pour les segments de correspondance (transferts)
    if (segment.type === 'transfer' || lineInfo === 'Correspondance') {
      const transferEdges = originalEdgesData.value.features.filter(feature => {
        return feature.properties.type === 'transfer' &&
               ((feature.properties.from_name === fromStation && feature.properties.to_name === toStation) ||
                (feature.properties.from_name === toStation && feature.properties.to_name === fromStation))
      })
      console.log(`Trouvé ${transferEdges.length} transferts pour ${fromStation} -> ${toStation}`)
      routeEdgesFeatures.push(...transferEdges)
    } else {
      // Pour les segments de métro (connexions directes)
      // Chercher toutes les arêtes directes de cette ligne entre ces deux stations
      const directEdges = originalEdgesData.value.features.filter(feature => {
        const fromName = feature.properties.from_name
        const toName = feature.properties.to_name
        const routeShortName = feature.properties.route_short_name
        
        // Correspondance exacte par nom et ligne
        const exactMatch = (fromName === fromStation && toName === toStation && routeShortName === lineInfo) ||
                          (fromName === toStation && toName === fromStation && routeShortName === lineInfo)
        
        // Si pas de correspondance exacte, essayer juste par nom (moins strict)
        const nameMatch = (fromName === fromStation && toName === toStation) ||
                         (fromName === toStation && toName === fromStation)
        
        return exactMatch || nameMatch
      })
      
      console.log(`Trouvé ${directEdges.length} connexions directes pour ${fromStation} -> ${toStation} (ligne ${lineInfo})`)
      routeEdgesFeatures.push(...directEdges)
      
      // Si on n'a pas trouvé d'arêtes directes exactes, chercher le chemin sur la ligne
      if (directEdges.length === 0 && lineInfo && lineInfo !== 'Correspondance') {
        console.log(`Recherche du chemin sur la ligne ${lineInfo} entre ${fromStation} et ${toStation}`)
        
        // Chercher toutes les arêtes de cette ligne
        const lineEdges = originalEdgesData.value.features.filter(feature => {
          return feature.properties.route_short_name === lineInfo &&
                 feature.properties.type === 'direct'
        })
        
        // Construire un graphe simple pour cette ligne pour trouver le chemin
        const lineGraph = new Map()
        lineEdges.forEach(edge => {
          const from = edge.properties.from_name
          const to = edge.properties.to_name
          
          if (!lineGraph.has(from)) lineGraph.set(from, [])
          if (!lineGraph.has(to)) lineGraph.set(to, [])
          
          lineGraph.get(from).push({ station: to, edge })
          lineGraph.get(to).push({ station: from, edge })
        })
        
        // Fonction pour trouver le chemin le plus court entre deux stations
        const findPath = (start, end, graph) => {
          if (start === end) return []
          
          const visited = new Set()
          const queue = [{ station: start, path: [] }]
          
          while (queue.length > 0) {
            const { station, path } = queue.shift()
            
            if (visited.has(station)) continue
            visited.add(station)
            
            if (station === end) {
              return path
            }
            
            const neighbors = graph.get(station) || []
            for (const neighbor of neighbors) {
              if (!visited.has(neighbor.station)) {
                queue.push({
                  station: neighbor.station,
                  path: [...path, neighbor.edge]
                })
              }
            }
          }
          return []
        }
        
        // Trouver le chemin entre les deux stations
        const pathEdges = findPath(fromStation, toStation, lineGraph)
        console.log(`Trouvé ${pathEdges.length} arêtes pour le chemin ${fromStation} -> ${toStation}`)
        routeEdgesFeatures.push(...pathEdges)
      }
    }
  })
  
  // Ajouter les stations intermédiaires basées sur les arêtes trouvées
  routeEdgesFeatures.forEach(edge => {
    routeStationNames.add(edge.properties.from_name)
    routeStationNames.add(edge.properties.to_name)
  })
  
  // Filtrer les stations pour ne garder que celles du trajet
  const routeStationsFeatures = originalStationsData.value.features.filter(feature =>
    routeStationNames.has(feature.properties.name)
  )
  
  // Créer une nouvelle couche pour les stations du trajet
  if (routeStationsFeatures.length > 0) {
    stationsLayer.value = L.geoJSON({
      type: 'FeatureCollection',
      features: routeStationsFeatures
    }, {
      pointToLayer: (feature, latlng) => {
        // Style simplifié des stations pour l'affichage du trajet
        const stationName = feature.properties.name
        
        // Vérifier si la station est un départ ou une arrivée de trajet
        // Utiliser les segments traités uniformément
        const firstSegment = segmentsToProcess[0]
        const lastSegment = segmentsToProcess[segmentsToProcess.length - 1]
        
        const firstStationName = firstSegment?.from_station || firstSegment?.from
        const lastStationName = lastSegment?.to_station || lastSegment?.to
        
        const isStartOfRoute = firstStationName === stationName
        const isEndOfRoute = lastStationName === stationName
        
        // Style simplifié mais distinctif
        if (isStartOfRoute) {
          return L.circleMarker(latlng, {
            radius: 12,
            fillColor: '#27ae60',  // Vert foncé pour le départ
            color: '#ffffff',      // Contour blanc
            weight: 3,
            opacity: 1,
            fillOpacity: 1
          })
        } else if (isEndOfRoute) {
          return L.circleMarker(latlng, {
            radius: 12,
            fillColor: '#e74c3c',  // Rouge pour l'arrivée
            color: '#ffffff',      // Contour blanc
            weight: 3,
            opacity: 1,
            fillOpacity: 1
          })
        } else {
          // Station intermédiaire
          return L.circleMarker(latlng, {
            radius: 9,
            fillColor: '#3498db',  // Bleu pour intermédiaire
            color: '#ffffff',      // Contour blanc
            weight: 2,
            opacity: 1,
            fillOpacity: 1
          })
        }
      },
      onEachFeature: (feature, layer) => {
        const stationName = feature.properties.name
        
        // Vérifier le type de station dans l'itinéraire
        // Utiliser les segments traités uniformément
        const firstSegment = segmentsToProcess[0]
        const lastSegment = segmentsToProcess[segmentsToProcess.length - 1]
        
        const firstStationName = firstSegment?.from_station || firstSegment?.from
        const lastStationName = lastSegment?.to_station || lastSegment?.to
        
        const isStartOfRoute = firstStationName === stationName
        const isEndOfRoute = lastStationName === stationName
        
        let stationType = ''
        if (isStartOfRoute) {
          stationType = '<span class="station-type-start">🟢 Départ</span>'
        } else if (isEndOfRoute) {
          stationType = '<span class="station-type-end">🔴 Arrivée</span>'
        } else {
          stationType = '<span class="station-type-transfer">🔵 Étape</span>'
        }
        
        layer.bindPopup(`
          <div class="station-popup route-highlighted">
            <h4>📍 ${stationName}</h4>
            <p><strong>${stationType}</strong></p>
          </div>
        `)
      }
    })
    
    stationsLayer.value.addTo(map.value)
  }
  
  // Déduplication des arêtes (éviter les doublons)
  const uniqueEdges = routeEdgesFeatures.filter((edge, index, array) => {
    return array.findIndex(e => 
      e.properties.from_name === edge.properties.from_name &&
      e.properties.to_name === edge.properties.to_name &&
      e.properties.type === edge.properties.type
    ) === index
  })
  
  // Créer une nouvelle couche pour les arêtes du trajet
  if (uniqueEdges.length > 0) {
    edgesLayer.value = L.geoJSON({
      type: 'FeatureCollection',
      features: uniqueEdges
    }, {
      style: (feature) => {
        const edgeType = feature.properties.type
        
        // Style simplifié pour une meilleure visibilité du trajet
        if (edgeType === 'direct') {
          // Connexions directes - style épais et coloré
          return {
            color: '#2c3e50',  // Couleur foncée uniforme
            weight: 8,         // Plus épais pour bien voir le trajet
            opacity: 1,
            smoothFactor: 1,
            lineCap: 'round',
            lineJoin: 'round'
          }
        } else if (edgeType === 'transfer') {
          // Correspondances - style différent mais visible
          return {
            color: '#e74c3c',  // Rouge pour les correspondances
            weight: 6,
            opacity: 1,
            dashArray: '15, 10', // Tirets plus larges
            smoothFactor: 1,
            lineCap: 'round',
            lineJoin: 'round'
          }
        } else {
          // Style par défaut
          return {
            color: '#34495e',
            weight: 6,
            opacity: 1
          }
        }
      },
      onEachFeature: (feature, layer) => {
        // Popup simplifié pour l'affichage du trajet
        let popupContent = `<div class="edge-popup route-highlighted">`

        if (feature.properties.type === 'direct') {
          const routeName = feature.properties.route_short_name || 'N/A'
          const travelTime = feature.properties.travel_time || 'N/A'
          popupContent += `
            <h4>🚇 Ligne ${routeName} - TRAJET</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Temps:</strong> ${travelTime}s</p>
          `
        } else if (feature.properties.type === 'transfer') {
          const transferTime = feature.properties.transfer_time || 'N/A'
          popupContent += `
            <h4>🔄 Correspondance - TRAJET</h4>
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
  
  // Centrer la carte sur le trajet affiché pour une meilleure visibilité
  if (routeStationsFeatures.length > 0) {
    // Créer un groupe avec toutes les features pour calculer les limites
    const allFeatures = [...routeStationsFeatures, ...uniqueEdges]
    if (allFeatures.length > 0) {
      const group = L.featureGroup()
      
      // Ajouter temporairement les features au groupe pour calculer les limites
      L.geoJSON({
        type: 'FeatureCollection', 
        features: allFeatures
      }).addTo(group)
      
      // Ajuster la vue de la carte pour montrer tout le trajet
      map.value.fitBounds(group.getBounds(), {
        padding: [20, 20]  // Ajouter un peu de marge autour du trajet
      })
      
      // Retirer le groupe temporaire
      group.clearLayers()
    }
  }
}

// Fonction pour réafficher tous les éléments
const showAllElements = () => {
  console.log('Réaffichage de tous les éléments')
  
  // Réinitialiser l'état du trajet affiché
  routeDisplayed.value = false
  currentRoute.value = null
  
  // Réinitialiser l'état de l'ACPM affiché
  mstDisplayed.value = false
  currentMST.value = null
  
  // RÉACTIVER LE LAZY LOADING après avoir masqué le trajet
  if (moveEndListener.value) {
    map.value.on('moveend', moveEndListener.value)
  }
  if (zoomStartListener.value) {
    map.value.on('zoomstart', zoomStartListener.value)
  }
  if (moveStartListener.value) {
    map.value.on('movestart', moveStartListener.value)
  }
  
  // Supprimer les couches actuelles
  if (stationsLayer.value) {
    map.value.removeLayer(stationsLayer.value)
    stationsLayer.value = null
  }
  if (edgesLayer.value) {
    map.value.removeLayer(edgesLayer.value)
    edgesLayer.value = null
  }
  if (mstLayer.value) {
    map.value.removeLayer(mstLayer.value)
    mstLayer.value = null
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

// ===== FONCTIONS ACPM =====

// Fonction pour afficher l'ACPM sur la carte
const showMST = (mstResult) => {
  console.log('Affichage de l\'ACPM sur la carte:', mstResult)
  
  // Stocker l'ACPM courant et marquer qu'il est affiché
  currentMST.value = mstResult
  mstDisplayed.value = true
  
  // DÉSACTIVER LE LAZY LOADING pendant l'affichage de l'ACPM
  if (moveEndListener.value) {
    map.value.off('moveend', moveEndListener.value)
  }
  if (zoomStartListener.value) {
    map.value.off('zoomstart', zoomStartListener.value)
  }
  if (moveStartListener.value) {
    map.value.off('movestart', moveStartListener.value)
  }
  
  if (!originalStationsData.value || !originalEdgesData.value) {
    console.error('Données originales non disponibles pour l\'ACPM')
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
  
  // Créer un ensemble des noms de stations de l'ACPM
  const mstStationNames = new Set()
  
  // Extraire toutes les stations de l'ACPM
  mstResult.edges.forEach(edge => {
    mstStationNames.add(edge.from)
    mstStationNames.add(edge.to)
  })
  
  // Filtrer les stations pour ne garder que celles de l'ACPM
  const mstStationsFeatures = originalStationsData.value.features.filter(feature =>
    mstStationNames.has(feature.properties.name)
  )
  
  // Créer une nouvelle couche pour les stations de l'ACPM
  if (mstStationsFeatures.length > 0) {
    stationsLayer.value = L.geoJSON({
      type: 'FeatureCollection',
      features: mstStationsFeatures
    }, {
      pointToLayer: (feature, latlng) => {
        // Style spécial pour les stations de l'ACPM
        return L.circleMarker(latlng, {
          radius: 8,
          fillColor: '#9b59b6',  // Violet pour l'ACPM
          color: '#ffffff',      // Contour blanc
          weight: 3,
          opacity: 1,
          fillOpacity: 0.9
        })
      },
      onEachFeature: (feature, layer) => {
        const stationName = feature.properties.name
        
        layer.bindPopup(`
          <div class="station-popup mst-highlighted">
            <h4>🌐 ${stationName}</h4>
            <p><strong><span class="station-type-mst">Station ACPM</span></strong></p>
          </div>
        `)
      }
    })
    
    stationsLayer.value.addTo(map.value)
  }
  
  // Créer les arêtes de l'ACPM
  const mstGeoJsonFeatures = []
  
  mstResult.edges.forEach((edge, index) => {
    // Trouver l'arête correspondante dans les données originales
    const originalEdge = originalEdgesData.value.features.find(feature => {
      return (feature.properties.from_name === edge.from && 
              feature.properties.to_name === edge.to) ||
             (feature.properties.from_name === edge.to && 
              feature.properties.to_name === edge.from)
    })
    
    if (originalEdge) {
      // Créer une nouvelle feature avec les propriétés de l'ACPM
      const mstFeature = {
        ...originalEdge,
        properties: {
          ...originalEdge.properties,
          mst_order: index + 1,
          mst_weight: edge.weight,
          type: 'mst'
        }
      }
      mstGeoJsonFeatures.push(mstFeature)
    }
  })
  
  // Créer une nouvelle couche pour les arêtes de l'ACPM
  if (mstGeoJsonFeatures.length > 0) {
    mstLayer.value = L.geoJSON({
      type: 'FeatureCollection',
      features: mstGeoJsonFeatures
    }, {
      style: (feature) => {
        // Style spécial pour les arêtes de l'ACPM
        return {
          color: '#9b59b6',      // Violet pour l'ACPM
          weight: 6,             // Plus épais
          opacity: 1,
          smoothFactor: 1,
          lineCap: 'round',
          lineJoin: 'round'
        }
      },
      onEachFeature: (feature, layer) => {
        const order = feature.properties.mst_order
        const weight = feature.properties.mst_weight
        
        layer.bindPopup(`
          <div class="edge-popup mst-highlighted">
            <h4>🌐 Arête ACPM #${order}</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Poids:</strong> ${weight}s</p>
            <p><strong>Ordre:</strong> ${order}/${mstResult.edgeCount}</p>
          </div>
        `)
      }
    })
    
    mstLayer.value.addTo(map.value)
    
    // Déplacer les stations au-dessus des arêtes
    if (stationsLayer.value) {
      stationsLayer.value.bringToFront()
    }
  }
  
  // Centrer la carte sur l'ACPM
  if (mstStationsFeatures.length > 0) {
    const allFeatures = [...mstStationsFeatures, ...mstGeoJsonFeatures]
    if (allFeatures.length > 0) {
      const group = L.featureGroup()
      
      L.geoJSON({
        type: 'FeatureCollection', 
        features: allFeatures
      }).addTo(group)
      
      map.value.fitBounds(group.getBounds(), {
        padding: [20, 20]
      })
      
      group.clearLayers()
    }
  }
}

// Fonction pour afficher une étape de l'ACPM
const showMSTStep = (step) => {
  console.log('Affichage de l\'étape ACPM:', step)
  
  // DÉSACTIVER LE LAZY LOADING pendant l'affichage de l'ACPM
  if (moveEndListener.value) {
    map.value.off('moveend', moveEndListener.value)
  }
  if (zoomStartListener.value) {
    map.value.off('zoomstart', zoomStartListener.value)
  }
  if (moveStartListener.value) {
    map.value.off('movestart', moveStartListener.value)
  }
  
  if (!originalStationsData.value || !originalEdgesData.value) {
    console.error('Données originales non disponibles pour l\'étape ACPM')
    return
  }
  
  // Masquer les couches existantes
  if (stationsLayer.value) {
    map.value.removeLayer(stationsLayer.value)
    stationsLayer.value = null
  }
  if (edgesLayer.value) {
    map.value.removeLayer(edgesLayer.value)
    edgesLayer.value = null
  }
  if (mstLayer.value) {
    map.value.removeLayer(mstLayer.value)
    mstLayer.value = null
  }
  
  // Créer un ensemble des noms de stations pour cette étape
  const stepStationNames = new Set()
  
  // Extraire toutes les stations jusqu'à cette étape
  step.mstEdges.forEach(edge => {
    stepStationNames.add(edge.from)
    stepStationNames.add(edge.to)
  })
  
  // Filtrer les stations pour ne garder que celles de cette étape
  const stepStationsFeatures = originalStationsData.value.features.filter(feature =>
    stepStationNames.has(feature.properties.name)
  )
  
  // Créer une nouvelle couche pour les stations de cette étape
  if (stepStationsFeatures.length > 0) {
    stationsLayer.value = L.geoJSON({
      type: 'FeatureCollection',
      features: stepStationsFeatures
    }, {
      pointToLayer: (feature, latlng) => {
        // Mettre en évidence la nouvelle arête ajoutée
        const isNewEdgeStation = (step.edge.from === feature.properties.name || 
                                 step.edge.to === feature.properties.name)
        
        return L.circleMarker(latlng, {
          radius: isNewEdgeStation ? 10 : 8,
          fillColor: isNewEdgeStation ? '#e74c3c' : '#9b59b6',  // Rouge pour nouvelle, violet pour existante
          color: '#ffffff',
          weight: isNewEdgeStation ? 4 : 3,
          opacity: 1,
          fillOpacity: 0.9
        })
      },
      onEachFeature: (feature, layer) => {
        const stationName = feature.properties.name
        const isNewEdgeStation = (step.edge.from === stationName || step.edge.to === stationName)
        
        layer.bindPopup(`
          <div class="station-popup mst-highlighted">
            <h4>🌐 ${stationName}</h4>
            <p><strong><span class="station-type-mst">
              ${isNewEdgeStation ? 'Nouvelle station ajoutée' : 'Station ACPM'}
            </span></strong></p>
            ${isNewEdgeStation ? '<p><em>Étape ' + step.edgesCount + '</em></p>' : ''}
          </div>
        `)
      }
    })
    
    stationsLayer.value.addTo(map.value)
  }
  
  // Créer les arêtes pour cette étape
  const stepGeoJsonFeatures = []
  
  step.mstEdges.forEach((edge, index) => {
    // Trouver l'arête correspondante dans les données originales
    const originalEdge = originalEdgesData.value.features.find(feature => {
      return (feature.properties.from_name === edge.from && 
              feature.properties.to_name === edge.to) ||
             (feature.properties.from_name === edge.to && 
              feature.properties.to_name === edge.from)
    })
    
    if (originalEdge) {
      // Marquer la dernière arête ajoutée
      const isNewEdge = edge === step.edge
      
      const stepFeature = {
        ...originalEdge,
        properties: {
          ...originalEdge.properties,
          mst_order: index + 1,
          mst_weight: edge.weight,
          type: 'mst',
          is_new_edge: isNewEdge
        }
      }
      stepGeoJsonFeatures.push(stepFeature)
    }
  })
  
  // Créer une nouvelle couche pour les arêtes de cette étape
  if (stepGeoJsonFeatures.length > 0) {
    mstLayer.value = L.geoJSON({
      type: 'FeatureCollection',
      features: stepGeoJsonFeatures
    }, {
      style: (feature) => {
        const isNewEdge = feature.properties.is_new_edge
        
        return {
          color: isNewEdge ? '#e74c3c' : '#9b59b6',  // Rouge pour nouvelle, violet pour existante
          weight: isNewEdge ? 8 : 6,
          opacity: 1,
          smoothFactor: 1,
          lineCap: 'round',
          lineJoin: 'round'
        }
      },
      onEachFeature: (feature, layer) => {
        const order = feature.properties.mst_order
        const weight = feature.properties.mst_weight
        const isNewEdge = feature.properties.is_new_edge
        
        layer.bindPopup(`
          <div class="edge-popup mst-highlighted">
            <h4>🌐 ${isNewEdge ? 'Nouvelle arête' : 'Arête ACPM'} #${order}</h4>
            <p><strong>De:</strong> ${feature.properties.from_name}</p>
            <p><strong>Vers:</strong> ${feature.properties.to_name}</p>
            <p><strong>Poids:</strong> ${weight}s</p>
            ${isNewEdge ? `<p><em>Ajoutée à l'étape ${step.edgesCount}</em></p>` : ''}
            <p class="edge-type-mst">Étape ${step.edgesCount}/${step.mstEdges.length}</p>
          </div>
        `)
      }
    })
    
    mstLayer.value.addTo(map.value)
  }
}

// Fonction pour centrer la vue sur l'ensemble de l'ACPM
const centerOnMST = (mstResult) => {
  console.log('Centrage de la vue sur l\'ACPM')
  
  if (!originalEdgesData.value || !mstResult.edges) {
    console.error('Données non disponibles pour le centrage')
    return
  }
  
  // Créer un groupe de toutes les arêtes de l'ACPM pour calculer les bounds
  const allMSTFeatures = []
  
  mstResult.edges.forEach(edge => {
    const originalEdge = originalEdgesData.value.features.find(feature => {
      return (feature.properties.from_name === edge.from && 
              feature.properties.to_name === edge.to) ||
             (feature.properties.from_name === edge.to && 
              feature.properties.to_name === edge.from)
    })
    
    if (originalEdge) {
      allMSTFeatures.push(originalEdge)
    }
  })
  
  if (allMSTFeatures.length > 0) {
    const mstGeoJSON = {
      type: 'FeatureCollection',
      features: allMSTFeatures
    }
    
    const bounds = L.geoJSON(mstGeoJSON).getBounds()
    
    // Centrer avec un padding généreux pour voir l'animation complète
    map.value.fitBounds(bounds, { 
      padding: [50, 50],
      maxZoom: 12  // Limiter le zoom pour garder une vue d'ensemble
    })
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

/* Styles spécifiques pour l'affichage des trajets */
:deep(.edge-popup.route-highlighted) {
  background-color: rgba(44, 62, 80, 0.1);
  border: 3px solid #2c3e50;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

:deep(.edge-popup.route-highlighted h4) {
  color: #2c3e50;
  font-weight: bold;
  margin: 0 0 8px 0;
  font-size: 16px;
}

:deep(.station-popup.route-highlighted) {
  background-color: rgba(44, 62, 80, 0.1);
  border: 3px solid #2c3e50;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

:deep(.station-popup.route-highlighted h4) {
  color: #2c3e50;
  font-weight: bold;
  margin: 0 0 8px 0;
  font-size: 16px;
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

:deep(.station-type-mst) {
  color: #9b59b6;
  font-weight: bold;
  display: block;
  padding: 5px;
  background-color: rgba(155, 89, 182, 0.1);
  border-radius: 4px;
  margin-top: 5px;
}

/* Styles spécifiques pour l'affichage de l'ACPM */
:deep(.edge-popup.mst-highlighted) {
  background-color: rgba(155, 89, 182, 0.1);
  border: 3px solid #9b59b6;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

:deep(.edge-popup.mst-highlighted h4) {
  color: #9b59b6;
  font-weight: bold;
  margin: 0 0 8px 0;
  font-size: 16px;
}

:deep(.station-popup.mst-highlighted) {
  background-color: rgba(155, 89, 182, 0.1);
  border: 3px solid #9b59b6;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

:deep(.station-popup.mst-highlighted h4) {
  color: #9b59b6;
  font-weight: bold;
  margin: 0 0 8px 0;
  font-size: 16px;
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
