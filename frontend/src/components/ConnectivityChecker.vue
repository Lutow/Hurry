<template>
  <div class="connectivity-checker">
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">
          <i class="icon">🔗</i>
          Vérification de la Connexité du Réseau
        </h3>
        <p class="card-description">
          Vérifiez si toutes les stations du réseau de transport sont accessibles entre elles
        </p>
      </div>

      <div class="card-content">
        <!-- Boutons d'action -->
        <div class="action-buttons">
          <button 
            class="btn btn-primary"
            @click="checkConnectivity"
            :disabled="loading"
          >
            <i class="btn-icon">🔍</i>
            {{ loading ? 'Vérification...' : 'Vérifier la Connexité' }}
          </button>

          <button 
            class="btn btn-secondary"
            @click="getDetailedAnalysis"
            :disabled="loading"
          >
            <i class="btn-icon">📊</i>
            Analyse Détaillée
          </button>
        </div>

        <!-- Indicateur de chargement -->
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
          <p>{{ loadingMessage }}</p>
        </div>

        <!-- Résultat de la connexité simple -->
        <div v-if="connectivityResult && !loading" class="result-card">
          <div class="result-header" :class="connectivityResult.is_connected ? 'success' : 'warning'">
            <i class="result-icon">
              {{ connectivityResult.is_connected ? '✅' : '❌' }}
            </i>
            <h4>{{ connectivityResult.message }}</h4>
          </div>
          <div class="result-details">
            <p><strong>Temps de traitement :</strong> {{ connectivityResult.processing_time }}s</p>
            <p v-if="connectivityResult.is_connected" class="success-text">
              🎉 Toutes les stations sont accessibles entre elles !
            </p>
            <p v-else class="warning-text">
              ⚠️ Certaines stations ne sont pas accessibles depuis d'autres stations.
            </p>
          </div>
        </div>

        <!-- Analyse détaillée -->
        <div v-if="detailedAnalysis && !loading" class="detailed-analysis">
          <h4>📊 Analyse Détaillée de la Connexité</h4>
          
          <div class="analysis-grid">
            <div class="stat-card">
              <div class="stat-number">{{ detailedAnalysis.total_nodes }}</div>
              <div class="stat-label">Stations Total</div>
            </div>
            
            <div class="stat-card">
              <div class="stat-number">{{ detailedAnalysis.total_edges }}</div>
              <div class="stat-label">Connexions Total</div>
            </div>
            
            <div class="stat-card">
              <div class="stat-number">{{ detailedAnalysis.number_of_components }}</div>
              <div class="stat-label">Composantes Connexes</div>
            </div>
            
            <div class="stat-card">
              <div class="stat-number">{{ detailedAnalysis.largest_component_size }}</div>
              <div class="stat-label">Plus Grande Composante</div>
            </div>
          </div>

          <!-- Composantes connexes -->
          <div v-if="detailedAnalysis.components_info.length > 1" class="components-section">
            <h5>🔗 Composantes Connexes</h5>
            <div class="components-list">
              <div 
                v-for="component in detailedAnalysis.components_info" 
                :key="component.component_id"
                class="component-item"
                :class="{ 'main-component': component.component_id === 1 }"
              >
                <span class="component-id">Composante {{ component.component_id }}</span>
                <span class="component-size">{{ component.size }} stations</span>
                <span class="component-percentage">({{ component.percentage.toFixed(1) }}%)</span>
              </div>
            </div>
          </div>

          <!-- Nœuds isolés -->
          <div v-if="detailedAnalysis.isolated_nodes.length > 0" class="isolated-nodes">
            <h5>🏝️ Stations Isolées ({{ detailedAnalysis.isolated_nodes.length }})</h5>
            <div class="isolated-list">
              <div 
                v-for="node in detailedAnalysis.isolated_nodes" 
                :key="node.stop_id"
                class="isolated-item"
              >
                <strong>{{ node.stop_name }}</strong>
                <span class="coordinates">({{ node.lat.toFixed(4) }}, {{ node.lon.toFixed(4) }})</span>
              </div>
            </div>
          </div>

          <div class="analysis-footer">
            <p><strong>Temps d'analyse :</strong> {{ detailedAnalysis.processing_time }}s</p>
          </div>
        </div>

        <!-- Messages d'erreur -->
        <div v-if="error" class="error-card">
          <i class="error-icon">❌</i>
          <h4>Erreur</h4>
          <p>{{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConnectivityChecker',
  data() {
    return {
      loading: false,
      loadingMessage: '',
      connectivityResult: null,
      detailedAnalysis: null,
      error: null
    }
  },
  methods: {
    async checkConnectivity() {
      this.resetResults()
      this.loading = true
      this.loadingMessage = 'Vérification de la connexité du réseau...'
      
      try {
        const response = await fetch('http://localhost:8000/api/connectivity/check')
        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`)
        }
        
        this.connectivityResult = await response.json()
      } catch (err) {
        this.error = `Erreur lors de la vérification: ${err.message}`
      } finally {
        this.loading = false
      }
    },

    async getDetailedAnalysis() {
      this.resetResults()
      this.loading = true
      this.loadingMessage = 'Analyse détaillée de la connexité en cours...'
      
      try {
        const response = await fetch('http://localhost:8000/api/connectivity/details')
        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`)
        }
        
        this.detailedAnalysis = await response.json()
      } catch (err) {
        this.error = `Erreur lors de l'analyse: ${err.message}`
      } finally {
        this.loading = false
      }
    },

    resetResults() {
      this.connectivityResult = null
      this.detailedAnalysis = null
      this.error = null
    }
  }
}
</script>

<style scoped>
.connectivity-checker {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  color: white;
  padding: 30px;
  text-align: center;
}

.card-title {
  margin: 0 0 10px 0;
  font-size: 1.8rem;
  font-weight: 600;
}

.icon {
  margin-right: 10px;
  font-size: 2rem;
}

.card-description {
  margin: 0;
  opacity: 0.9;
  font-size: 1rem;
}

.card-content {
  padding: 30px;
}

.action-buttons {
  display: flex;
  gap: 15px;
  margin-bottom: 30px;
  flex-wrap: wrap;
  justify-content: center;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 180px;
  justify-content: center;
}

.btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(90deg, #3498db, #2ecc71);
  color: white;
}

.btn-secondary {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.btn-icon {
  font-size: 1.2rem;
}

.loading {
  text-align: center;
  padding: 40px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.result-card, .detailed-analysis {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 25px;
  margin-top: 20px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
  padding: 15px;
  border-radius: 8px;
}

.result-header.success {
  background: #d4edda;
  color: #155724;
}

.result-header.warning {
  background: #fff3cd;
  color: #856404;
}

.result-icon {
  font-size: 2rem;
}

.result-header h4 {
  margin: 0;
  font-size: 1.3rem;
}

.result-details {
  padding-left: 60px;
}

.success-text {
  color: #28a745;
  font-weight: 500;
}

.warning-text {
  color: #dc3545;
  font-weight: 500;
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.stat-number {
  font-size: 2.5rem;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 5px;
}

.stat-label {
  color: #666;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.components-section, .isolated-nodes {
  margin-top: 25px;
}

.components-section h5, .isolated-nodes h5 {
  margin-bottom: 15px;
  color: #333;
  font-size: 1.2rem;
}

.components-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.component-item {
  background: white;
  padding: 12px 16px;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.main-component {
  border-left: 4px solid #28a745;
}

.component-percentage {
  color: #666;
  font-size: 0.9rem;
}

.isolated-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 10px;
}

.isolated-item {
  background: white;
  padding: 12px;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.coordinates {
  color: #666;
  font-size: 0.85rem;
  display: block;
  margin-top: 4px;
}

.analysis-footer {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #e9ecef;
  text-align: center;
  color: #666;
}

.error-card {
  background: #f8d7da;
  color: #721c24;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.error-icon {
  font-size: 1.5rem;
}

.error-card h4 {
  margin: 0 0 5px 0;
}

.error-card p {
  margin: 0;
}

@media (max-width: 768px) {
  .connectivity-checker {
    padding: 10px;
  }
  
  .card-header {
    padding: 20px;
  }
  
  .card-content {
    padding: 20px;
  }
  
  .action-buttons {
    flex-direction: column;
    align-items: center;
  }
  
  .btn {
    min-width: 250px;
  }
  
  .analysis-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
  
  .isolated-list {
    grid-template-columns: 1fr;
  }
}
</style>
