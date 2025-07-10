// Composable pour gérer la sélection de destination
import { ref, provide, inject } from 'vue'

// Symboles pour l'injection
const DESTINATION_KEY = Symbol('destination')

// État global pour la destination sélectionnée
const selectedDestination = ref('')

// Fonction pour fournir la destination (à utiliser dans App.vue)
export function provideDestination() {
  provide(DESTINATION_KEY, {
    selectedDestination,
    setDestination: (destination) => {
      selectedDestination.value = destination
    }
  })
  
  return {
    selectedDestination,
    setDestination: (destination) => {
      selectedDestination.value = destination
    }
  }
}

// Fonction pour injecter la destination (à utiliser dans les composants enfants)
export function useDestination() {
  const destinationContext = inject(DESTINATION_KEY)
  
  if (!destinationContext) {
    console.error('useDestination must be used within a component that provides destination')
    return {
      selectedDestination: ref(''),
      setDestination: () => {}
    }
  }
  
  return destinationContext
}
