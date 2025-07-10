<template>
  <div class="sidebar" :style="cssVars" :class="{ 'light-mode': isLight}" @wheel.stop @mousedown.stop @mousemove.stop @touchstart.stop @touchmove.stop @dblclick.stop.prevent>
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
              <input type="checkbox" class="checkbox" v-model="isLight">
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
import {computed, onMounted, ref, provide, watch} from 'vue';

const showSettings = ref(false);
const trafficComponent = ref(null);
const isLight = ref(false);

const cssVars = computed(() => ({
  '--sidebar-bg': isLight.value ? '#f8f9fa' : '#2c3e50',
  '--sidebar-text': isLight.value ? '#2c3e50' : '#ffffff',
  '--sidebar-text-secondary': isLight.value ? 'rgba(44, 62, 80, 0.7)' : 'rgba(255, 255, 255, 0.7)',
  '--sidebar-border': isLight.value ? 'rgba(52, 58, 64, 0.1)' : 'rgba(255, 255, 255, 0.1)',
  '--sidebar-bg-secondary': isLight.value ? 'rgba(255, 255, 255, 0.9)' : 'rgba(0, 0, 0, 0.15)',
  '--sidebar-accent': '#3498db',
  '--sidebar-accent-hover': '#2980b9',
  '--sidebar-danger': isLight.value ? '#c0392b' : '#e74c3c',
  '--sidebar-success': '#2ecc71',
  '--sidebar-shadow': isLight.value ? 'rgba(0, 0, 0, 0.1)' : 'rgba(0, 0, 0, 0.15)',
  '--sidebar-error-bg': isLight.value ? 'rgba(192, 57, 43, 0.1)' : 'rgba(231, 76, 60, 0.1)',
  '--sidebar-button-text': isLight.value ? '#ffffff' : '#ffffff'
}));
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

.sidebar.light-mode {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  color: #2c3e50;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
}

.sidebar-header {
  padding: 24px 20px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
  display: flex;
  flex-direction: column;
}

.sidebar.light-mode .sidebar-header {
  background: rgba(255, 255, 255, 0.8);
  border-bottom: 1px solid rgba(52, 58, 64, 0.1);
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

.sidebar.light-mode .logo-icon {
  color: #2c3e50;
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

.sidebar.light-mode .settings-icon {
  color: rgba(44, 62, 80, 0.7);
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

.menu-category h3 {
  font-size: 14px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 8px 24px;
  font-weight: 500;
  letter-spacing: 1px;
}

.sidebar.light-mode .menu-category h3 {
  color: rgba(44, 62, 80, 0.6);
}

.menu-item .material-icons {
  margin-right: 16px;
  font-size: 20px;
  color: rgba(255, 255, 255, 0.85);
}

.sidebar.light-mode .menu-item .material-icons {
  color: rgba(44, 62, 80, 0.85);
}

.menu-item span:not(.material-icons):not(.menu-badge) {
  font-size: 16px;
  font-weight: 400;
}

.traffic-section {
  background: rgba(0, 0, 0, 0.15);
  margin-top: auto;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar.light-mode .traffic-section {
  background: rgba(255, 255, 255, 0.9);
  border-top: 1px solid rgba(52, 149, 219, 0.2);
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

.sidebar.light-mode .section-title .material-icons {
  color: #c0392b;
}

.section-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.sidebar.light-mode .section-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: rgba(44, 62, 80, 0.9);
}

.refresh-icon {
  cursor: pointer;
  color: rgba(255, 255, 255, 0.6);
  font-size: 18px;
  transition: transform 0.5s ease, color 0.3s ease;
}

.sidebar.light-mode .refresh-icon {
  color: rgba(44, 62, 80, 0.6);
}

.refresh-icon:hover {
  transform: rotate(180deg);
  color: rgba(255, 255, 255, 0.9);
}

.sidebar.light-mode .refresh-icon:hover {
  color: rgba(44, 62, 80, 0.9);
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

.sidebar.light-mode .settings-panel {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
}

.sidebar.light-mode .settings-header {
  border-bottom: 1px solid rgba(52, 58, 64, 0.1);
  background: rgba(255, 255, 255, 0.8);
}

.settings-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: white;
}

.sidebar.light-mode .settings-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
}

.close-settings {
  cursor: pointer;
  color: rgba(255, 255, 255, 0.7);
  transition: color 0.2s ease;
}

.sidebar.light-mode .close-settings {
  color: rgba(44, 62, 80, 0.7);
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

.sidebar.light-mode .settings-group h4 {
  color: rgba(44, 62, 80, 0.7);
  border-bottom: 1px solid rgba(52, 58, 64, 0.1);
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.sidebar.light-mode .setting-item {
  border-bottom: 1px solid rgba(52, 58, 64, 0.05);
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

.sidebar.light-mode .setting-label .material-icons {
  color: rgba(44, 62, 80, 0.8);
}

.setting-label span:not(.material-icons) {
  color: rgba(255, 255, 255, 0.9);
}

.sidebar.light-mode .setting-label span:not(.material-icons) {
  color: rgba(44, 62, 80, 0.9);
}

.setting-select {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  padding: 8px 12px;
  margin-right: 13px;
  border-radius: 4px;
  outline: none;
}

.sidebar.light-mode .setting-select {
  background: rgba(52, 58, 64, 0.1);
  color: #2c3e50;
  border: 1px solid rgba(52, 149, 219, 0.3);
}

.setting-select option {
  background: #34495e;
  color: white;
}

.sidebar.light-mode .setting-select option {
  background: #f8f9fa;
  color: #2c3e50;
}

.about-info {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  line-height: 1.5;
}

.sidebar.light-mode .about-info {
  color: rgba(44, 62, 80, 0.7);
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

.sidebar.light-mode .planner-section {
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(52, 149, 219, 0.2);
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

/* Toggle Switch - Made by Madflows */
.toggle-switch {
  display: block;
  position: relative;
  width: 100px;
  height: 30px;
  --light: #d8dbe0;
  --dark: #000000;   /* soit #2c3e50 */
  --link: rgb(27, 129, 112);
  --link-hover: rgb(24, 94, 82);
}

.switch-label {
  display: block;
  position: relative;
  width: 70%;
  height: 30px;
  background-color: var(--dark);
  border-radius: 25px;
  cursor: pointer;
}

.checkbox {
  position: relative;
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
  box-shadow: inset 12px -4px 0px 0px var(--light);
  -webkit-box-shadow: inset 12px -4px 0px 0px var(--light);
  background-color: var(--dark);
  -webkit-transition: 0.3s;
  transition: 0.3s;
}

.checkbox:checked ~ .slider::before {
  -webkit-transform: translateX(40px);
  -ms-transform: translateX(40px);
  transform: translateX(40px);
  background-color: var(--dark);
  -webkit-box-shadow: none;
  box-shadow: none;
}

/* Styles spécifiques pour le mode clair du toggle switch */
.sidebar.light-mode .toggle-switch {
  --light: #2c3e50;
  --dark: #ecf0f1;
}

.sidebar.light-mode .switch-label {
  background-color: var(--dark);
  border: 1px solid rgb(0, 0, 0);
}

.sidebar.light-mode .checkbox:checked ~ .slider {
  background-color: var(--light);
}

.sidebar.light-mode .slider::before {
  background-color: #2c3e50;
  box-shadow: inset 12px -4px 0px 0px #2c3e50;
  -webkit-box-shadow: inset 12px -4px 0px 0px #2c3e50;
}

.sidebar.light-mode .checkbox:checked ~ .slider::before {
  background-color: white;
  -webkit-box-shadow: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}
</style>
