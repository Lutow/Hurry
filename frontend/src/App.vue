<script setup>
import Map from './components/Map.vue'
import Sidebar from './components/Sidebar.vue'
import SearchOverlay from './components/SearchOverlay.vue'
</script>

<template>
  <div class="app-container">
    <Map />
    <Sidebar />
    <SearchOverlay />
  </div>
</template>

<style scoped>
.app-container {
  position: relative;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
</style>
