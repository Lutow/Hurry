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
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const depart = ref('')
const arrivee = ref('')
const heure = ref('')

function handleSearch() {
  console.log('Recherche trajet:', depart.value, arrivee.value, heure.value)
  // Envoie vers une API ou traitement du trajet ici
}
</script>

<style scoped>
.search-overlay {
  position: absolute;
  top: 20px;
  left: 50%;
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
</style>
