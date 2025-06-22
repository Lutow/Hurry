<script setup>
import { ref, onMounted } from 'vue'
import Map from './components/Map.vue'


const msg = ref('Loading...')

onMounted(async () => {
  const res = await fetch('http://localhost:8000/api/hello')
  const data = await res.json()
  msg.value = data.message
})
</script>

<template>
  <div>
    <h1>{{ msg }}</h1>
    <Map />
  </div>
</template>


