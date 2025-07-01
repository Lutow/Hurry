<template>
  <div class="search-overlay">
    <h2>Planifier un trajet</h2>
    <form @submit.prevent="handleSearch">
      <label>Départ</label>
      <input type="text" v-model="depart" placeholder="Station de départ" />

      <label>Arrivée</label>
      <input type="text" v-model="arrivee" placeholder="Station d’arrivée" />

      <label>Heure</label>
      <input type="time" v-model="heure" />

      <button type="submit">Rechercher</button>
      <button @click=fetchConnectivity>Verifier la connexité du réseau</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const depart = ref('')
const arrivee = ref('')
const heure = ref('')

function fetchConnectivity() {
  fetch('graph/connectivity').then(res => res.json()).then(data => {console.log(data)})
}
function handleSearch() {
  console.log('Recherche trajet:', depart.value, arrivee.value, heure.value)
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
.search-overlay input, .search-overlay button {
  margin-top: 8px;
  padding: 8px;
}

button {
  padding: 12.5px 30px;
  border: 0;
  border-radius: 100px;
  background-color: #2ba8fb;
  color: #ffffff;
  font-weight: Bold;
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

