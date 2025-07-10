<template>
  <div class="news-interface">
    <div class="news-header">
      <h3>🌍 Actualités Internationales</h3>
      <p>Découvrez les journaux du monde entier</p>
    </div>
    
    <!-- Sélecteur de langues avec drapeaux -->
    <div class="language-selector">
      <button 
        v-for="lang in languages" 
        :key="lang.code"
        :class="['language-btn', { active: selectedLanguage === lang.code }]"
        @click="selectedLanguage = lang.code"
      >
        <img :src="lang.flag" :alt="lang.name" class="flag"/>
        <span class="lang-name">{{ lang.name }}</span>
      </button>
    </div>
    
    <!-- Grille des journaux -->
    <div class="news-grid">
      <div
        v-for="journal in filteredJournals"
        :key="journal.name"
        class="news-card"
      >
        <img 
          :src="journal.logo" 
          :alt="journal.name" 
          loading="lazy"
          @error="handleImageError"
          class="journal-logo"
        />
        <div class="news-info">
          <div class="news-name">{{ journal.name }}</div>
          <div class="news-country">{{ journal.country }}</div>
          <button 
            class="access-btn"
            @click="openJournal(journal.url)"
          >
            Accéder au site
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// Import des images des journaux
import lemondeImg from '../assets/lemonde.png'
import lefigaroImg from '../assets/lefigaro.png'
import liberationImg from '../assets/liberation.svg'
import lequipeImg from '../assets/lequipe.png'
import leparisienImg from '../assets/leparisien.png'
import vingtMinutesImg from '../assets/20minutes.webp'

import theguardianImg from '../assets/theguardian.jpg'
import bbcnewsImg from '../assets/bbcnews.png'
import thetimesImg from '../assets/thetimes.png'
import cnnImg from '../assets/CNN.png'
import nytimesImg from '../assets/nytimes.jpg'
import reutersImg from '../assets/reuters.webp'

import elpaisImg from '../assets/elpais.png'
import lavanguardiaImg from '../assets/lavanguardia.png'
import elmundoImg from '../assets/elmundo.png'
import abcImg from '../assets/abc.png'
import larazonImg from '../assets/larazon.png'
import marcaImg from '../assets/marca.gif'

import derspiegelImg from '../assets/derspiegel.jfif'
import diezeitImg from '../assets/diezeit.gif'
import bildImg from '../assets/bild.png'
import sueddeutscheImg from '../assets/sueddeutsche-zeitung.svg'
import frankfurterImg from '../assets/frankfurter.png'
import handelsblattImg from '../assets/handelsblatt.png'

import corriereImg from '../assets/corriere.jfif'
import larepublicaImg from '../assets/larepublica.jfif'
import lagazettaImg from '../assets/lagazzetta.png'
import ilesore24Img from '../assets/ilesore24.png'
import lastampaImg from '../assets/lastampa.png'
import ilgiornaleImg from '../assets/il_giornale_logo.jpg'

// Import des drapeaux
import franceFlag from '../assets/france.avif'
import ukFlag from '../assets/uk.png'
import spainFlag from '../assets/spain.png'
import germanyFlag from '../assets/germany.webp'
import italyFlag from '../assets/italie.png'

const selectedLanguage = ref('fr')

const languages = [
  { code: 'fr', name: 'Français', flag: franceFlag },
  { code: 'en', name: 'English', flag: ukFlag },
  { code: 'es', name: 'Español', flag: spainFlag },
  { code: 'de', name: 'Deutsch', flag: germanyFlag },
  { code: 'it', name: 'Italiano', flag: italyFlag }
]

const journals = [
  // Français
  {
    name: "Le Monde",
    country: "France",
    language: "fr",
    logo: lemondeImg,
    url: "https://www.lemonde.fr"
  },
  {
    name: "Le Figaro",
    country: "France", 
    language: "fr",
    logo: lefigaroImg,
    url: "https://www.lefigaro.fr"
  },
  {
    name: "Libération",
    country: "France",
    language: "fr",
    logo: liberationImg,
    url: "https://www.liberation.fr"
  },
  {
    name: "L'Équipe",
    country: "France",
    language: "fr",
    logo: lequipeImg,
    url: "https://www.lequipe.fr"
  },
  {
    name: "Le Parisien",
    country: "France",
    language: "fr",
    logo: leparisienImg,
    url: "https://www.leparisien.fr"
  },
  {
    name: "20 Minutes",
    country: "France",
    language: "fr",
    logo: vingtMinutesImg,
    url: "https://www.20minutes.fr"
  },
  
  // Anglais
  {
    name: "The Guardian",
    country: "United Kingdom",
    language: "en",
    logo: theguardianImg,
    url: "https://www.theguardian.com"
  },
  {
    name: "BBC News",
    country: "United Kingdom",
    language: "en", 
    logo: bbcnewsImg,
    url: "https://www.bbc.com/news"
  },
  {
    name: "The Times",
    country: "United Kingdom",
    language: "en",
    logo: thetimesImg,
    url: "https://www.thetimes.co.uk"
  },
  {
    name: "CNN",
    country: "United States",
    language: "en",
    logo: cnnImg,
    url: "https://www.cnn.com"
  },
  {
    name: "The New York Times",
    country: "United States",
    language: "en",
    logo: nytimesImg,
    url: "https://www.nytimes.com"
  },
  {
    name: "Reuters",
    country: "United Kingdom",
    language: "en",
    logo: reutersImg,
    url: "https://www.reuters.com"
  },
  
  // Espagnol
  {
    name: "El País",
    country: "Spain",
    language: "es",
    logo: elpaisImg,
    url: "https://elpais.com"
  },
  {
    name: "La Vanguardia",
    country: "Spain",
    language: "es",
    logo: lavanguardiaImg,
    url: "https://www.lavanguardia.com"
  },
  {
    name: "El Mundo",
    country: "Spain",
    language: "es",
    logo: elmundoImg,
    url: "https://www.elmundo.es"
  },
  {
    name: "ABC",
    country: "Spain",
    language: "es",
    logo: abcImg,
    url: "https://www.abc.es"
  },
  {
    name: "La Razón",
    country: "Spain",
    language: "es",
    logo: larazonImg,
    url: "https://www.larazon.es"
  },
  {
    name: "Marca",
    country: "Spain",
    language: "es",
    logo: marcaImg,
    url: "https://www.marca.com"
  },
  
  // Allemand
  {
    name: "Der Spiegel",
    country: "Germany",
    language: "de",
    logo: derspiegelImg,
    url: "https://www.spiegel.de"
  },
  {
    name: "Die Zeit",
    country: "Germany",
    language: "de",
    logo: diezeitImg,
    url: "https://www.zeit.de"
  },
  {
    name: "Bild",
    country: "Germany",
    language: "de",
    logo: bildImg,
    url: "https://www.bild.de"
  },
  {
    name: "Süddeutsche Zeitung",
    country: "Germany",
    language: "de",
    logo: sueddeutscheImg,
    url: "https://www.sueddeutsche.de"
  },
  {
    name: "Frankfurter Allgemeine",
    country: "Germany",
    language: "de",
    logo: frankfurterImg,
    url: "https://www.faz.net"
  },
  {
    name: "Handelsblatt",
    country: "Germany",
    language: "de",
    logo: handelsblattImg,
    url: "https://www.handelsblatt.com"
  },
  
  // Italien
  {
    name: "Corriere della Sera",
    country: "Italy",
    language: "it",
    logo: corriereImg,
    url: "https://www.corriere.it"
  },
  {
    name: "La Repubblica",
    country: "Italy",
    language: "it",
    logo: larepublicaImg,
    url: "https://www.repubblica.it"
  },
  {
    name: "La Gazzetta dello Sport",
    country: "Italy",
    language: "it",
    logo: lagazettaImg,
    url: "https://www.gazzetta.it"
  },
  {
    name: "Il Sole 24 Ore",
    country: "Italy",
    language: "it",
    logo: ilesore24Img,
    url: "https://www.ilsole24ore.com"
  },
  {
    name: "La Stampa",
    country: "Italy",
    language: "it",
    logo: lastampaImg,
    url: "https://www.lastampa.it"
  },
  {
    name: "Il Giornale",
    country: "Italy",
    language: "it",
    logo: ilgiornaleImg,
    url: "https://www.ilgiornale.it"
  }
]

const filteredJournals = computed(() => {
  return journals.filter(journal => journal.language === selectedLanguage.value)
})

function openJournal(url) {
  window.open(url, '_blank')
}

function handleImageError(event) {
  // Remplacer l'image par un placeholder en cas d'erreur
  event.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjgwIiB2aWV3Qm94PSIwIDAgMjAwIDgwIiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjgwIiBmaWxsPSIjZjBmMGYwIi8+Cjx0ZXh0IHg9IjEwMCIgeT0iNDAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiM2NjY2NjYiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZHk9IjAuNGVtIj5KT1VSTkFMPC90ZXh0Pgo8L3N2Zz4K'
  event.target.style.objectFit = 'cover'
}
</script>

<style scoped>
.news-interface {
  padding: 1rem;
  color: white;
}

.news-header {
  text-align: center;
  margin-bottom: 2rem;
}

.news-header h3 {
  color: #3498db;
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.news-header p {
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
  font-size: 0.9rem;
}

.language-selector {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.language-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 60px;
}

.language-btn:hover {
  transform: translateY(-2px);
  border-color: #3498db;
  background: rgba(52, 152, 219, 0.2);
}

.language-btn.active {
  border-color: #3498db;
  background: rgba(52, 152, 219, 0.3);
}

.flag {
  width: 24px;
  height: 18px;
  object-fit: cover;
  border-radius: 2px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.lang-name {
  font-size: 0.75rem;
  font-weight: 500;
}

.news-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.2rem;
  justify-items: center;
  max-width: 100%;
}

.news-card {
  width: 180px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.news-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

.journal-logo {
  width: 100%;
  height: 70px;
  object-fit: contain;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 0.8rem;
  transition: transform 0.3s ease;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.news-card:hover .journal-logo {
  transform: scale(1.05);
}

.news-info {
  padding: 0.8rem;
  text-align: center;
}

.news-name {
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.4rem;
  line-height: 1.2;
}

.news-country {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.75rem;
  margin-bottom: 0.8rem;
  font-style: italic;
}

.access-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  transition: all 0.3s ease;
  width: 100%;
}

.access-btn:hover {
  background: #2980b9;
  transform: translateY(-1px);
}

@media (max-width: 768px) {
  .news-grid {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
  }
  
  .news-card {
    width: 140px;
  }
  
  .journal-logo {
    height: 60px;
    padding: 0.6rem;
  }
  
  .language-selector {
    gap: 0.25rem;
  }
  
  .language-btn {
    min-width: 50px;
    padding: 0.4rem 0.6rem;
  }
}
</style>
