<template>
  <div class="sidebar">
    <h1>Menu</h1>
    <h2 id="Titre2">Info Traffic</h2>
    <Traffic />
  </div>
</template>

<script setup>
import Traffic from "./Traffic.vue";
</script>

<style scoped>
.sidebar {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 340px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  z-index: 999;
}

.sidebar h1 {
  margin-bottom: 20px;
  margin-top: 0;
}

.sidebar #Titre2 {
  margin-top: 450px;
}

.sidebar a:hover {
  text-decoration: underline;
}
</style>
