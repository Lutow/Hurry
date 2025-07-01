<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const disruptions = ref([])
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/ratp-disruptions')
    console.log("Données reçues :", data)
    disruptions.value = data.disruptions || []
  } catch (err) {
    console.error("Erreur de chargement :", err)
    error.value = 'Erreur de chargement des perturbations'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="disruptions-container">
    <h2>Perturbations</h2>
    <div v-if="loading">Chargement…</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else-if="disruptions.length === 0">Aucune perturbation détectée</div>
    <ul v-else>
      <li v-for="d in disruptions" :key="d.id" class="disruption-item">
        <strong>{{ d.title }}</strong><br />
        <span v-html="d.message"></span>
      </li>
    </ul>
  </div>
</template>


<style scoped>
.disruptions-container {
  max-height: 50vh;
  overflow-y: auto;
  background-color: transparent;
  color: #2c3e50;
  font-size: 0.9rem;
  padding: 0.5rem;
}
.disruptions-container h2, ul, li {
  color: white;
}

.disruption-item {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e0e0e0;
}
</style>