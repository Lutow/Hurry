<template>
  <div class="search-overlay">
    <h2>Planifier un trajet</h2>
    <form @submit.prevent="handleSearch">
      <label for="depart">Départ</label>
      <input
        list="stations"
        v-model="depart"
        id="depart"
        placeholder="Station de départ"
      />

      <label for="arrivee">Arrivée</label>
      <input
        list="stations"
        v-model="arrivee"
        id="arrivee"
        placeholder="Station d’arrivée"
      />

      <label for="heure">Heure</label>
      <input type="time" v-model="heure" id="heure" />

      <button type="submit">Rechercher</button>
      <button type="button" @click="fetchConnectivity">Vérifier la connexité (Désactivé temporairement)</button>
    </form>

    <!-- Liste de suggestions -->
    <datalist id="stations">
      <option
        v-for="stop in stops"
        :key="stop.stop_id"
        :value="stop.stop_name"
      />
    </datalist>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const depart = ref('')
const arrivee = ref('')
const heure = ref('')
const stops = ref([])

onMounted(async () => {
  try {
    const res = await fetch("http://localhost:8000/api/stops/list")
    const data = await res.json()
    stops.value = data.stops
  } catch (error) {
    console.error("Erreur lors du chargement des stations:", error)
    alert("Impossible de charger les stations")
  }
})

async function fetchConnectivity() {
  try {
    const res = await fetch('http://localhost:8000/api/connectivity/check')
    const data = await res.json()
    alert(data.message)
  } catch (error) {
    console.error('Erreur de connectivité', error)
    alert("Erreur lors de la vérification.")
  }
}

async function handleSearch() {
  const fromStop = stops.value.find(s => s.stop_name === depart.value)
  const toStop = stops.value.find(s => s.stop_name === arrivee.value)

  if (!fromStop || !toStop) {
    alert("Merci de sélectionner des stations valides depuis la liste.")
    return
  }

  try {
    const response = await fetch(
      `http://localhost:8000/api/shortest_path?from_stop_id=${encodeURIComponent(fromStop.stop_id)}&to_stop_id=${encodeURIComponent(toStop.stop_id)}`
    )
    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Erreur lors de la recherche')
    }

    alert(`Trajet trouvé : ${data.path_names?.join(' ➜ ')}`)
    console.log("Résultat du trajet :", data)

  } catch (err) {
    console.error('Erreur recherche trajet:', err)
    alert("Erreur lors de la recherche du trajet.")
  }
}
</script>

<style scoped>
.search-overlay {
  position: absolute;
  top: 8%;
  left: 8%;
  transform: translateX(-50%);
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  width: 300px;
}
.search-overlay form {
  display: flex;
  flex-direction: column;
}
.search-overlay input,
.search-overlay button {
  margin-top: 8px;
  padding: 8px;
}

button {
  padding: 12.5px 30px;
  border: 0;
  border-radius: 100px;
  background-color: #2ba8fb;
  color: #ffffff;
  font-weight: bold;
  transition: all 0.5s;
  -webkit-transition: all 0.5s;
}

button:hover {
  background-color: #6fc5ff;
  box-shadow: 0 0 20px #6fc5ff50;
  transform: scale(1.1);
}

button:active {
  background-color: #3d94cf;
  transition: all 0.25s;
  -webkit-transition: all 0.25s;
  box-shadow: none;
  transform: scale(0.98);
}
</style>
