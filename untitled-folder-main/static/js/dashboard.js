/**
 * AgriGuru Agricultural Advisory Dashboard JavaScript
 * Handles: Bilingual toggling (EN/TA), Geolocation, Cascading District Selector,
 * API requests to /api/recommend, Chart.js interactive visualizations.
 */

// =============================================================================
// 1. BILINGUAL TRANSLATION DICTIONARY (English & Tamil)
// =============================================================================
const translations = {
  en: {
    appTitle: "AgriGuru Advisory",
    appSubtitle: "Intelligent Crop Recommendation & Climate Advisory",
    chooseLocation: "Farm Location & Parameters",
    useGps: "Detect GPS Location",
    manualSelect: "Manual District Selection",
    districtLabel: "District:",
    selectDistrict: "-- Select District --",
    plantingDateLabel: "Planting Date:",
    customSoilToggle: "Farmer Laboratory Soil Test (Optional)",
    soilTypeLabel: "Soil Type:",
    phLabel: "Soil pH:",
    nLabel: "Nitrogen (N kg/ha):",
    pLabel: "Phosphorus (P kg/ha):",
    kLabel: "Potassium (K kg/ha):",
    getAdvisoryBtn: "Generate Intelligent Advisory",
    weatherTitle: "Live Agro-Meteorological Weather",
    climateTitle: "NASA POWER 5-Year Climate Analysis",
    soilTitle: "Soil Health & Nutrients",
    recsTitle: "Top 5 Recommended Crops",
    profitTitle: "Financial Profitability & ROI Analysis",
    irrigationTitle: "Smart Irrigation Advisory",
    suitability: "Suitability",
    growthDays: "Growth Days",
    marketPrice: "Market Price",
    netProfit: "Net Profit / Acre",
    roi: "Estimated ROI",
    loadingText: "Consulting satellite weather, soil analysis, and ML recommendation models...",
    langSwitch: "தமிழ் (Tamil)"
  },
  ta: {
    appTitle: "அக்ரிகுரு வேளாண் ஆலோசகர்",
    appSubtitle: "நுண்ணறிவு பயிர் பரிந்துரை மற்றும் காலநிலை வழிகாட்டி",
    chooseLocation: "பண்ணை அமைவிடம் மற்றும் விவரங்கள்",
    useGps: "ஜிபிஎஸ் அமைவிடம் கண்டறி",
    manualSelect: "மாவட்டத்தை தேர்வு செய்க",
    districtLabel: "மாவட்டம்:",
    selectDistrict: "-- மாவட்டத்தைத் தேர்ந்தெடுக்கவும் --",
    plantingDateLabel: "விதைப்பு தேதி:",
    customSoilToggle: "மண் பரிசோதனை ஆய்வக முடிவுகள் (விருப்பத்தேர்வு)",
    soilTypeLabel: "மண் வகை:",
    phLabel: "மண் கார அமிலத்தன்மை (pH):",
    nLabel: "தழைச்சத்து (N கிலோ/ஹெக்):",
    pLabel: "மணிச்சத்து (P கிலோ/ஹெக்):",
    kLabel: "சாம்பல்ச்சத்து (K கிலோ/ஹெக்):",
    getAdvisoryBtn: "பயிர் பரிந்துரை பெறுக",
    weatherTitle: "தற்போதைய வானிலை நிலவரம்",
    climateTitle: "நாசா 5 ஆண்டு வரலாற்று காலநிலை",
    soilTitle: "மண் வளம் & ஊட்டச்சத்துக்கள்",
    recsTitle: "சிறந்த 5 பரிந்துரைக்கப்பட்ட பயிர்கள்",
    profitTitle: "சந்தை விலை மற்றும் லாப பகுப்பாய்வு",
    irrigationTitle: "நுண்ணறிவு பாசன ஆலோசனை",
    suitability: "பொருத்தம்",
    growthDays: "வளரும் நாட்கள்",
    marketPrice: "சந்தை விலை",
    netProfit: "ஏக்கருக்கு நிகர லாபம்",
    roi: "வருவாய் விகிதம் (ROI)",
    loadingText: "வானிலை, மண் தரம் மற்றும் செயற்கை நுண்ணறிவு மாதிரிகள் கணக்கிடப்படுகின்றன...",
    langSwitch: "English"
  }
};

let currentLang = 'en';
let weatherChartInstance = null;
let climateChartInstance = null;
let suitabilityChartInstance = null;
let profitChartInstance = null;

// =============================================================================
// 2. LANGUAGE SWITCHER
// =============================================================================
function toggleLanguage() {
  currentLang = currentLang === 'en' ? 'ta' : 'en';
  const t = translations[currentLang];

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (t[key]) {
      el.innerText = t[key];
    }
  });

  const langBtn = document.getElementById('langToggleBtn');
  if (langBtn) {
    langBtn.innerText = t.langSwitch;
  }
}

// =============================================================================
// 3. GEOLOCATION & DISTRICT HANDLING
// =============================================================================
function detectGpsLocation() {
  const statusBox = document.getElementById('gpsStatusText');
  if (!navigator.geolocation) {
    alert("Geolocation is not supported by your browser.");
    return;
  }

  statusBox.innerText = "Accessing device GPS coordinates...";
  navigator.geolocation.getCurrentPosition(
    async position => {
      const lat = position.coords.latitude.toFixed(4);
      const lon = position.coords.longitude.toFixed(4);
      document.getElementById('inputLat').value = lat;
      document.getElementById('inputLon').value = lon;
      statusBox.innerText = `Detected GPS: ${lat}, ${lon}`;

      // Reverse geocode to find Tamil Nadu district
      try {
        const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
        const data = await resp.json();
        const address = data.address || {};
        const districtName = address.state_district || address.county || address.city || "Chennai";
        
        // Auto-select in district dropdown
        const select = document.getElementById('inputDistrict');
        for (let i = 0; i < select.options.length; i++) {
          if (select.options[i].text.toLowerCase().includes(districtName.toLowerCase().replace("district", "").trim())) {
            select.selectedIndex = i;
            break;
          }
        }
      } catch (err) {
        console.warn("Reverse geocode failed:", err);
      }
    },
    err => {
      statusBox.innerText = "GPS access denied or unavailable. Please select district manually.";
    },
    { timeout: 10000, enableHighAccuracy: true }
  );
}

function onDistrictChange() {
  const districtSelect = document.getElementById('inputDistrict');
  const dist = districtSelect.value;
  if (!dist) return;

  // Approximate center coordinates for standard Tamil Nadu districts
  const districtCoords = {
    "Chennai": [13.0827, 80.2707],
    "Coimbatore": [11.0168, 76.9558],
    "Madurai": [9.9252, 78.1198],
    "Tiruchirappalli": [10.7905, 78.7047],
    "Trichy": [10.7905, 78.7047],
    "Salem": [11.6643, 78.1460],
    "Erode": [11.3410, 77.7172],
    "Thanjavur": [10.7870, 79.1378],
    "Dindigul": [10.3673, 77.9803],
    "Tirunelveli": [8.7139, 77.7567],
    "Vellore": [12.9165, 79.1325],
    "Kanchipuram": [12.8342, 79.7036],
    "Cuddalore": [11.7480, 79.7714],
    "Tiruvallur": [13.1432, 79.9083],
    "Tiruvannamalai": [12.2253, 79.0747],
    "Villupuram": [11.9401, 79.4861],
    "Thoothukudi": [8.7642, 78.1348],
    "Nilgiris": [11.4102, 76.6950],
    "Kanyakumari": [8.0883, 77.5385],
    "Dharmapuri": [12.1211, 78.1582],
    "Krishnagiri": [12.5186, 78.2137],
    "Nagapattinam": [10.7672, 79.8449],
    "Namakkal": [11.2189, 78.1674],
    "Pudukkottai": [10.3797, 78.8208],
    "Ramanathapuram": [9.3639, 78.8395],
    "Sivagangai": [9.8433, 78.4809],
    "Tiruppur": [11.1085, 77.3411],
    "Tiruvarur": [10.7661, 79.6344],
    "Virudhunagar": [9.5680, 77.9624],
    "Ariyalur": [11.1401, 79.0786],
    "Perambalur": [11.2342, 78.8820],
    "Karur": [10.9601, 78.0766],
    "Mayiladuthurai": [11.1018, 79.6522]
  };

  const coords = districtCoords[dist] || [13.0827, 80.2707];
  document.getElementById('inputLat').value = coords[0];
  document.getElementById('inputLon').value = coords[1];
}

function toggleCustomSoilForm() {
  const checkbox = document.getElementById('chkCustomSoil');
  const soilInputs = document.getElementById('customSoilInputs');
  soilInputs.style.display = checkbox.checked ? 'grid' : 'none';
}

// =============================================================================
// 4. GENERATE RECOMMENDATIONS (FETCH API)
// =============================================================================
async function fetchRecommendations() {
  const lat = parseFloat(document.getElementById('inputLat').value);
  const lon = parseFloat(document.getElementById('inputLon').value);
  const district = document.getElementById('inputDistrict').value;
  const plantingDate = document.getElementById('inputDate').value;

  if (!lat || !lon || !district) {
    alert("Please specify a valid district and geographic coordinates.");
    return;
  }

  // Check custom soil
  let customSoil = null;
  const isCustom = document.getElementById('chkCustomSoil').checked;
  if (isCustom) {
    customSoil = {
      is_lab_test: true,
      type: document.getElementById('customSoilType').value,
      pH: parseFloat(document.getElementById('customSoilPh').value) || 6.5,
      N: parseFloat(document.getElementById('customSoilN').value) || 280,
      P: parseFloat(document.getElementById('customSoilP').value) || 20,
      K: parseFloat(document.getElementById('customSoilK').value) || 180
    };
  }

  // Show loading indicator & scroll
  const loader = document.getElementById('loadingIndicator');
  const resultsContainer = document.getElementById('resultsSection');
  loader.style.display = 'block';
  loader.scrollIntoView({ behavior: 'smooth' });

  try {
    const payload = {
      latitude: lat,
      longitude: lon,
      district: district,
      planting_date: plantingDate,
      custom_soil: customSoil
    };

    const response = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    loader.style.display = 'none';

    if (data.status === 'success') {
      renderResults(data);
      resultsContainer.style.display = 'block';
      resultsContainer.scrollIntoView({ behavior: 'smooth' });
    } else {
      alert("Error: " + (data.message || "Could not retrieve recommendations"));
    }
  } catch (err) {
    loader.style.display = 'none';
    alert("Network error: " + err.message);
  }
}

// =============================================================================
// 5. RENDER ADVISORY RESULTS
// =============================================================================
function renderResults(data) {
  const w = data.weather;
  const s = data.soil;
  const hist = data.historical_climate;
  const recs = data.recommendations || [];
  const insights = data.climate_insights || [];

  // 1. Weather Card
  document.getElementById('valTemperature').innerText = `${w['temperature (°C)']}°C`;
  document.getElementById('valHumidity').innerText = `${w['humidity (%)']}%`;
  document.getElementById('valRainfall').innerText = `${w['rainfall (mm)']} mm`;
  document.getElementById('valWind').innerText = `${w['wind_speed (km/h)']} km/h`;
  document.getElementById('valRainProb').innerText = `${w['precipitation_prob (%)']}%`;
  document.getElementById('valCondition').innerText = w['condition'];
  document.getElementById('valSeason').innerText = data.season;

  const weatherBadge = document.getElementById('badgeWeatherSource');
  weatherBadge.innerText = w.source;
  weatherBadge.className = w.is_live ? 'badge badge-live' : 'badge badge-fallback';

  // 2. Climate Insights Alerts
  const insightsContainer = document.getElementById('climateInsightsBox');
  insightsContainer.innerHTML = '';
  insights.forEach(item => {
    const alertDiv = document.createElement('div');
    const alertClass = item.type === 'warning' ? 'insight-warning' : (item.type === 'alert' ? 'insight-alert-danger' : 'insight-info');
    alertDiv.className = `insight-alert ${alertClass}`;
    alertDiv.innerHTML = `<strong>${item.title}:</strong> ${item.message}`;
    insightsContainer.appendChild(alertDiv);
  });

  // 3. Soil Card
  document.getElementById('valSoilType').innerText = s.type;
  document.getElementById('valSoilPh').innerText = s.pH;
  document.getElementById('valSoilN').innerText = `${s.N} kg/ha (${s.N_rating})`;
  document.getElementById('valSoilP').innerText = `${s.P} kg/ha (${s.P_rating})`;
  document.getElementById('valSoilK').innerText = `${s.K} kg/ha (${s.K_rating})`;

  const soilSourceBadge = document.getElementById('badgeSoilSource');
  soilSourceBadge.innerText = s.source;
  soilSourceBadge.className = s.is_lab_test ? 'badge badge-live' : 'badge badge-info';

  const amendmentsList = document.getElementById('soilAmendmentsList');
  amendmentsList.innerHTML = '';
  (s.amendments || []).forEach(adv => {
    const li = document.createElement('li');
    li.innerText = adv;
    amendmentsList.appendChild(li);
  });

  // 4. Top 5 Recommended Crops
  const recsContainer = document.getElementById('cropRecommendationsList');
  recsContainer.innerHTML = '';

  recs.forEach((crop, idx) => {
    const card = document.createElement('div');
    card.className = 'crop-card';

    const reasonsHtml = (crop.reasons || []).map(r => `<li>${r}</li>`).join('');

    card.innerHTML = `
      <div class="crop-rank-badge">
        <span class="crop-rank-number">#${idx + 1}</span>
        <span class="crop-rank-label">Rank</span>
      </div>
      <div class="crop-details">
        <h3>${crop.crop}</h3>
        <div class="crop-tamil-name">${crop.tamil_name || ''}</div>
        <div class="crop-tags-row">
          <span class="tag-compat">Suitability: <strong>${crop.suitability_score}%</strong></span>
          <span class="tag-compat">Soil Match: ${crop.soil_compatibility}%</span>
          <span class="tag-compat">pH Match: ${crop.ph_compatibility}%</span>
          <span class="tag-compat">Climate Match: ${crop.weather_compatibility}%</span>
          <span class="tag-compat">Duration: ${crop.growth_days} Days</span>
        </div>
        <ul class="crop-reasons-list">${reasonsHtml}</ul>
      </div>
      <div class="crop-financials-box">
        <div class="financial-label">Market Price / Qtl</div>
        <div class="financial-value">₹${crop.market_price_per_quintal.toLocaleString()}</div>
        <div class="financial-label" style="margin-top:6px;">Expected Net Profit / Acre</div>
        <div class="financial-value" style="color:#2e7d32;">₹${crop.net_profit_per_acre.toLocaleString()}</div>
        <div class="financial-roi">ROI: ${crop.roi_percent}%</div>
      </div>
    `;
    recsContainer.appendChild(card);
  });

  // 5. Irrigation Advisory (Primary recommended crop)
  if (recs.length > 0 && recs[0].irrigation_advisory) {
    const irr = recs[0].irrigation_advisory;
    const irrBox = document.getElementById('irrigationAdvisoryBox');
    irrBox.style.backgroundColor = irr.action_status === 'POSTPONE' ? '#fff3e0' : (irr.action_status === 'CRITICAL_IRRIGATE' ? '#ffebee' : '#e8f5e9');
    irrBox.style.border = `2px solid ${irr.badge_color}`;
    
    document.getElementById('irrHeadline').innerText = irr.headline;
    document.getElementById('irrHeadline').style.color = irr.badge_color;
    
    const irrList = document.getElementById('irrGuidanceList');
    irrList.innerHTML = (irr.guidance || []).map(g => `<li>${g}</li>`).join('');
    document.getElementById('irrDisclaimer').innerText = irr.disclaimer;
  }

  // 6. Render Charts
  renderCharts(w, hist, recs);
}

// =============================================================================
// 6. CHART.JS INTERACTIVE VISUALIZATIONS
// =============================================================================
function renderCharts(weather, histClimate, recs) {
  if (typeof Chart === 'undefined') {
    console.warn("Chart.js not loaded");
    return;
  }

  // --- Chart 1: 7-Day Live Weather Forecast ---
  const forecastDays = weather.forecast_daily || [];
  if (forecastDays.length > 0) {
    const ctxWeather = document.getElementById('chartWeatherForecast').getContext('2d');
    if (weatherChartInstance) weatherChartInstance.destroy();

    const labels = forecastDays.map(d => d.date.slice(5)); // MM-DD
    const temps = forecastDays.map(d => d.temp_avg);
    const rain = forecastDays.map(d => d.rainfall_mm);

    weatherChartInstance = new Chart(ctxWeather, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            type: 'line',
            label: 'Avg Temp (°C)',
            data: temps,
            borderColor: '#e65100',
            backgroundColor: 'rgba(230, 81, 0, 0.15)',
            yAxisID: 'yTemp',
            tension: 0.3,
            fill: true
          },
          {
            type: 'bar',
            label: 'Rainfall (mm)',
            data: rain,
            backgroundColor: '#0288d1',
            yAxisID: 'yRain',
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          yTemp: {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'Temperature (°C)' }
          },
          yRain: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            title: { display: true, text: 'Rainfall (mm)' }
          }
        }
      }
    });
  }

  // --- Chart 2: NASA POWER 5-Year Monthly Historical Rainfall ---
  const monthsData = histClimate.monthly_climate || [];
  if (monthsData.length > 0) {
    const ctxClimate = document.getElementById('chartHistoricalClimate').getContext('2d');
    if (climateChartInstance) climateChartInstance.destroy();

    const monthLabels = monthsData.map(m => m.month_name);
    const histRain = monthsData.map(m => m.avg_accumulated_rainfall_mm);
    const histTemp = monthsData.map(m => m.avg_temperature_c);

    climateChartInstance = new Chart(ctxClimate, {
      type: 'bar',
      data: {
        labels: monthLabels,
        datasets: [
          {
            label: '5-Yr Avg Rainfall (mm)',
            data: histRain,
            backgroundColor: '#43a047',
            borderRadius: 4
          },
          {
            type: 'line',
            label: '5-Yr Avg Temp (°C)',
            data: histTemp,
            borderColor: '#f57f17',
            borderWidth: 2,
            tension: 0.2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: { display: true, text: 'NASA POWER 5-Year Climate Profile (Monthly Accumulation)' }
        }
      }
    });
  }

  // --- Chart 3: Top 5 Crops Suitability Breakdown ---
  if (recs.length > 0) {
    const ctxSuit = document.getElementById('chartCropSuitability').getContext('2d');
    if (suitabilityChartInstance) suitabilityChartInstance.destroy();

    suitabilityChartInstance = new Chart(ctxSuit, {
      type: 'bar',
      data: {
        labels: recs.map(c => c.crop.split(' ')[0]),
        datasets: [{
          label: 'Overall Suitability Score (%)',
          data: recs.map(c => c.suitability_score),
          backgroundColor: ['#2e7d32', '#388e3c', '#43a047', '#66bb6a', '#81c784'],
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 100, title: { display: true, text: 'Suitability (%)' } }
        }
      }
    });

    // --- Chart 4: Financial Profitability & ROI Comparison ---
    const ctxProf = document.getElementById('chartCropProfitability').getContext('2d');
    if (profitChartInstance) profitChartInstance.destroy();

    profitChartInstance = new Chart(ctxProf, {
      type: 'bar',
      data: {
        labels: recs.map(c => c.crop.split(' ')[0]),
        datasets: [
          {
            label: 'Net Profit (₹/Acre)',
            data: recs.map(c => c.net_profit_per_acre),
            backgroundColor: '#1b5e20',
            borderRadius: 6,
            yAxisID: 'yProfit'
          },
          {
            type: 'line',
            label: 'ROI (%)',
            data: recs.map(c => c.roi_percent),
            borderColor: '#e65100',
            borderWidth: 3,
            yAxisID: 'yRoi'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          yProfit: {
            type: 'linear',
            position: 'left',
            title: { display: true, text: 'Net Profit (₹/Acre)' }
          },
          yRoi: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            title: { display: true, text: 'ROI (%)' }
          }
        }
      }
    });
  }
}

// Initial setup on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const dateInput = document.getElementById('inputDate');
  if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().split('T')[0];
  }
});
