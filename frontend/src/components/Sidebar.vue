<template>
  <div class="sidebar" @wheel.stop @mousedown.stop @mousemove.stop @touchstart.stop @touchmove.stop>
    <div class="sidebar-header">
      <div class="logo-container">
        <span class="material-icons logo-icon">directions_subway</span>
        <h1>Hurry</h1>
      </div>
      <span class="material-icons settings-icon" @click="toggleSettings">settings</span>
      <div class="header-line"></div>
    </div>
    
    <div class="planner-section">
      <SearchOverlay />
    </div>
    
    <div class="traffic-section">
      <div class="section-header">
        <div class="section-title">
          <span class="material-icons">traffic</span>
          <h2>Info Traffic</h2>
        </div>
        <span class="material-icons refresh-icon" @click="refreshTraffic" title="Rafraîchir les informations">refresh</span>
      </div>
      <div class="traffic-content">
        <Traffic ref="trafficComponent" />
      </div>
    </div>

    <div class="settings-panel" v-if="showSettings">
      <div class="settings-header">
        <h3>Paramètres</h3>
        <span class="material-icons close-settings" @click="toggleSettings">close</span>
      </div>
      
      <div class="settings-content">
        <div class="settings-group">
          <h4>Affichage</h4>
          <div class="setting-item">
            <div class="setting-label">
              <span class="material-icons">palette</span>
              <span>Thème</span>
            </div>
          <div class="toggle-switch">
            <label class="switch-label">
              <input type="checkbox" class="checkbox">
              <span class="slider"></span>
            </label>
          </div>
          </div>
          <div class="setting-item">
            <div class="setting-label">
              <span class="material-icons">language</span>
              <span>Langue</span>
            </div>
            <select class="setting-select">
              <option value="fr">Français</option>
              <option value="en">Anglais</option>
              <option value="es">Espagnol</option>
            </select>
          </div>
        </div>
        <div class="settings-group">
          <h4>À propos</h4>
          <div class="about-info">
            <p>Hurry v1.0 - Mastercamp Efrei</p>
            <p>© 2025 - Tous droits réservés</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import Traffic from "./Traffic.vue";
import SearchOverlay from "./SearchOverlay.vue";
import { onMounted, ref } from 'vue';

const showSettings = ref(false);
const trafficComponent = ref(null);

const toggleSettings = () => {
  showSettings.value = !showSettings.value;
};

const refreshTraffic = () => {
  // Animer l'icône de rafraîchissement
  const refreshIcon = document.querySelector('.refresh-icon');
  if (refreshIcon) {
    refreshIcon.classList.add('refreshing');
    setTimeout(() => {
      refreshIcon.classList.remove('refreshing');
    }, 1000);
  }
  
  // Appeler la méthode de rafraîchissement du composant Traffic si elle existe
  if (trafficComponent.value && trafficComponent.value.retryFetch) {
    trafficComponent.value.retryFetch();
  }
};

// Importation dynamique de Material Icons
onMounted(() => {
  const link = document.createElement('link');
  link.href = "https://fonts.googleapis.com/icon?family=Material+Icons";
  link.rel = "stylesheet";
  document.head.appendChild(link);
});


</script>

<style scoped>
.sidebar {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 550px;
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  color: white;
  padding: 0;
  z-index: 999;
  display: flex;
  flex-direction: column;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  animation: slideIn 0.4s ease-out forwards;
}

.sidebar-header {
  padding: 24px 20px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
  display: flex;
  flex-direction: column;
}

.logo-container {
  display: flex;
  align-items: center;
}

.logo-icon {
  font-size: 32px;
  margin-right: 12px;
  color: #3498db;
}

.settings-icon {
  position: absolute;
  top: 24px;
  right: 20px;
  font-size: 24px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
}

.settings-icon:hover {
  color: #3498db;
  transform: rotate(30deg);
}

.sidebar-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #3498db, #2ecc71);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.header-line {
  height: 3px;
  width: 60px;
  background: linear-gradient(90deg, #3498db, #2ecc71);
  border-radius: 2px;
  margin-top: 8px;
}

.menu-section {
  padding: 20px 0;
  overflow-y: auto;
  flex-grow: 1;
}

/* Style personnalisé pour la barre de défilement de la section menu */
.menu-section::-webkit-scrollbar {
  width: 6px;
}

.menu-section::-webkit-scrollbar-track {
  background: transparent;
}

.menu-section::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.menu-section::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.5);
}

/* Firefox */
.menu-section {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
}

.menu-category {
  margin-bottom: 20px;
}

.menu-category h3 {
  font-size: 14px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 8px 24px;
  font-weight: 500;
  letter-spacing: 1px;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 12px 24px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
  position: relative;
  transform: translateX(-10px);
  opacity: 0;
  animation: fadeInRight 0.3s ease forwards;
  animation-delay: calc(0.05s * var(--index, 0));
}

.menu-item:hover {
  background: rgba(52, 152, 219, 0.1);
  border-left-color: rgba(52, 152, 219, 0.7);
}

.menu-item.active {
  background: rgba(52, 152, 219, 0.2);
  border-left-color: #3498db;
}

.menu-item .material-icons {
  margin-right: 16px;
  font-size: 20px;
  color: rgba(255, 255, 255, 0.85);
}

.menu-item span:not(.material-icons):not(.menu-badge) {
  font-size: 16px;
  font-weight: 400;
}

.menu-badge {
  position: absolute;
  right: 24px;
  background: #e74c3c;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: bold;
}

.traffic-section {
  background: rgba(0, 0, 0, 0.15);
  margin-top: auto;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px 10px 24px;
}

.section-title {
  display: flex;
  align-items: center;
}

.section-title .material-icons {
  margin-right: 12px;
  font-size: 22px;
  color: #e74c3c;
}

.section-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.refresh-icon {
  cursor: pointer;
  color: rgba(255, 255, 255, 0.6);
  font-size: 18px;
  transition: transform 0.5s ease, color 0.3s ease;
}

.refresh-icon:hover {
  transform: rotate(180deg);
  color: rgba(255, 255, 255, 0.9);
}

.refresh-icon.refreshing {
  animation: spin 1s linear infinite;
  color: #3498db;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.settings-panel {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.3s ease;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
}

.settings-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: white;
}

.close-settings {
  cursor: pointer;
  color: rgba(255, 255, 255, 0.7);
  transition: color 0.2s ease;
}

.close-settings:hover {
  color: #e74c3c;
}

.settings-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.settings-group {
  margin-bottom: 25px;
}

.settings-group h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
  padding-bottom: 5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.setting-label {
  display: flex;
  align-items: center;
}

.setting-label .material-icons {
  margin-right: 10px;
  font-size: 20px;
  color: rgba(255, 255, 255, 0.8);
}

.setting-select {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  outline: none;
}

.setting-select option {
  background: #34495e;
  color: white;
}

.about-info {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  line-height: 1.5;
}

.about-info p {
  margin: 5px 0;
}

@keyframes slideIn {
  from { transform: translateX(-100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInRight {
  from {
    transform: translateX(-10px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.menu-category:nth-child(1) .menu-item:nth-child(1) { --index: 0; }
.menu-category:nth-child(1) .menu-item:nth-child(2) { --index: 1; }
.menu-category:nth-child(2) .menu-item:nth-child(1) { --index: 2; }
.menu-category:nth-child(2) .menu-item:nth-child(2) { --index: 3; }

.planner-section {
  padding: 24px 20px;
  background: rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-grow: 0;
}

.traffic-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 0 5px;
}

/* S'assurer que SearchOverlay est masqué quand les paramètres sont affichés */
.settings-panel {
  z-index: 10;
}

/* Amélioration des interactions de défilement */
.sidebar * {
  touch-action: pan-y; /* Autorise uniquement le défilement vertical sur les appareils tactiles */
  -ms-touch-action: pan-y;
}

.sidebar input, 
.sidebar button,
.sidebar select {
  touch-action: manipulation; /* Optimise l'interaction tactile pour les contrôles */
  -ms-touch-action: manipulation;
}

/* Empêche les éventuels soucis de pointeurs avec les événements arrêtés */
.sidebar {
  pointer-events: auto;
  overscroll-behavior: contain; /* Empêche le défilement de se propager */
}

/* Made by Madflows */
.toggle-switch {
  position: relative;
  width: 100px;
  height: 30px;
  --light: #d8dbe0;
  --dark: black;
  --link: rgb(27, 129, 112);
  --link-hover: rgb(24, 94, 82);
}

.switch-label {
  display: block;
  position: absolute;
  width: 70%;
  height: 30px;
  background-color: var(--dark);
  border-radius: 25px;
  cursor: pointer;
}

.checkbox {
  position: absolute;
  display: none;
}

.slider {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 25px;
  -webkit-transition: 0.3s;
  transition: 0.3s;
}

.checkbox:checked ~ .slider {
  background-color: var(--light);
}

.slider::before {
  content: "";
  position: absolute;
  top: 5px;
  left: 5px;
  width: 21px;
  height: 20px;
  border-radius: 50%;
  -webkit-box-shadow: inset 12px -4px 0px 0px var(--light);
  background-color: var(--dark);
  -webkit-transition: 0.3s;
  transition: 0.3s;
}

.checkbox:checked ~ .slider::before {
  -webkit-transform: translateX(50px);
  -ms-transform: translateX(50px);
  transform: translateX(40px);
  background-color: black;
  -webkit-box-shadow: none;
  box-shadow: none;
}
</style>
