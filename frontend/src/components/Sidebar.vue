<template>
  <div class="sidebar">
    <h2>Menu</h2>
    <ul>
      <li><a href="#">Infos</a></li>
      <li><a href="#">Connexion</a></li>
      <li><a href="#">Aide</a></li>
    </ul>
  </div>
</template>

<script setup></script>

<style scoped>
.sidebar {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 200px;
  background: #2c3e50;
  color: white;
  padding: 20px;
  z-index: 999;
}
.sidebar h2 {
  margin-bottom: 20px;
}
.sidebar ul {
  list-style: none;
  padding: 0;
}
.sidebar li {
  margin: 10px 0;
}
.sidebar a {
  color: white;
  text-decoration: none;
}
.sidebar a:hover {
  text-decoration: underline;
}
</style>
