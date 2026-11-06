import json
from datetime import datetime
from typing import Dict, List, Optional
from config import Config
from services.weather_service import WeatherService
from services.soil_service import SoilService
from services.crop_model_service import CropModelService
from services.irrigation_service import IrrigationService
from services.market_service import MarketService
from utils.db import save_recommendation_history

class RecommendationService:
    """
    Unified Orchestrator:
    Brings together Weather, Soil, Machine Learning, Irrigation, and Market Services.
    Generates data-driven agricultural advisories and persists history.
    """
    def __init__(self):
        self.weather_service = WeatherService()
        self.soil_service = SoilService()
        self.crop_model_service = CropModelService(self.soil_service)
        self.irrigation_service = IrrigationService()
        self.market_service = MarketService()

    def get_full_recommendation(
        self,
        lat: float,
        lon: float,
        district: str,
        planting_date: str = None,
        custom_soil: Optional[Dict] = None,
        phone: Optional[str] = None
    ) -> Dict:
        """
        Execute end-to-end crop recommendation and advisory workflow:
        1. Fetch Weather (Tomorrow.io live / Open-Meteo fallback)
        2. Retrieve NASA POWER 5-Year Historical Climate Analysis
        3. Perform Soil Analysis (District norm or Farmer Lab Test)
        4. Infer Top 5 Crops via ML & Agronomic Suitability
        5. Calculate District Market Profitability & ROI
        6. Generate Smart Irrigation Advisory
        7. Synthesize Historical vs Forecast Climate Insights
        """
        if not planting_date:
            planting_date = datetime.now().strftime("%Y-%m-%d")

        # 1. Weather
        weather = self.weather_service.get_weather_forecast(lat, lon, planting_date)

        # 2. Historical Climate (NASA POWER)
        historical_climate = self.weather_service.get_nasa_historical_climate(lat, lon, planting_date)

        # 3. Soil Analysis
        soil = self.soil_service.get_soil_data(district, custom_soil=custom_soil)

        # 4. Crop Prediction (Top 5)
        top_crops = self.crop_model_service.predict_crops(weather, soil)

        # 5. Market Financial Viability Analysis
        enriched_crops = self.market_service.analyze_profitability(top_crops, soil.get('district_matched', district))

        # 6. Irrigation Advisory for Top Crops
        for crop in enriched_crops:
            crop['irrigation_advisory'] = self.irrigation_service.generate_irrigation_advisory(
                crop['crop'], weather, soil, crop.get('growth_days', 100)
            )

        # 7. Synthesize Climate & Seasonal Insights
        climate_insights = self._generate_climate_insights(weather, historical_climate, planting_date)

        response = {
            'status': 'success',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'coordinates': {'latitude': lat, 'longitude': lon},
            'district': district.title(),
            'planting_date': planting_date,
            'season': weather.get('season', 'Unknown'),
            'weather': weather,
            'historical_climate': historical_climate,
            'climate_insights': climate_insights,
            'soil': soil,
            'recommendations': enriched_crops,
            'model_evaluation': self.crop_model_service.evaluation_results
        }

        # Persist recommendation event
        try:
            save_recommendation_history(
                phone=phone,
                district=district,
                lat=lat,
                lon=lon,
                date=planting_date,
                weather_summary={
                    'temperature': weather.get('temperature (°C)'),
                    'rainfall': weather.get('rainfall (mm)'),
                    'source': weather.get('source')
                },
                top_crops=[c['crop'] for c in enriched_crops[:3]]
            )
        except Exception as e:
            print(f"[RecommendationService] History log notice: {e}")

        return response

    def _generate_climate_insights(self, live_weather: Dict, hist_climate: Dict, planting_date: str) -> List[Dict]:
        """
        Compare upcoming forecast against 5-year historical climate patterns.
        Generates actionable agricultural insights (water deficit warnings, heavy rainfall advisories, heat stress).
        """
        insights = []
        try:
            p_month = datetime.strptime(planting_date, "%Y-%m-%d").month
        except Exception:
            p_month = datetime.now().month

        forecast_rain = float(live_weather.get('rainfall (mm)', 0.0))
        forecast_temp = float(live_weather.get('temperature (°C)', 28.0))

        # Look up historical monthly stats
        hist_month = next((m for m in hist_climate.get('monthly_climate', []) if m.get('month_num') == p_month), None)
        if hist_month:
            hist_avg_rain = float(hist_month.get('avg_accumulated_rainfall_mm', 60.0))
            hist_avg_temp = float(hist_month.get('avg_temperature_c', 28.5))

            # Rainfall comparison
            rain_diff = forecast_rain - hist_avg_rain
            if forecast_rain > (hist_avg_rain * 1.5) and forecast_rain > 40.0:
                insights.append({
                    'type': 'warning',
                    'title': 'High Precipitation Advisory',
                    'message': f"Upcoming forecast rainfall ({forecast_rain:.1f} mm) is substantially above the 5-year historical seasonal monthly average ({hist_avg_rain:.1f} mm). Ensure adequate field drainage to prevent waterlogging."
                })
            elif forecast_rain < (hist_avg_rain * 0.4) and hist_avg_rain > 30.0:
                insights.append({
                    'type': 'alert',
                    'title': 'Water Availability Deficit Warning',
                    'message': f"Upcoming forecast rainfall ({forecast_rain:.1f} mm) indicates a moisture deficit compared to the 5-year historical seasonal pattern ({hist_avg_rain:.1f} mm). Arrange supplementary canal/borewell irrigation."
                })
            else:
                insights.append({
                    'type': 'info',
                    'title': 'Seasonal Rainfall Alignment',
                    'message': f"Expected precipitation ({forecast_rain:.1f} mm) is within normal historical parameters for this month (5-year average: {hist_avg_rain:.1f} mm)."
                })

            # Temperature comparison
            if forecast_temp > (hist_avg_temp + 3.0):
                insights.append({
                    'type': 'warning',
                    'title': 'Elevated Thermal Stress Alert',
                    'message': f"Current temperature ({forecast_temp:.1f}°C) is warmer than the historical seasonal average ({hist_avg_temp:.1f}°C). Monitor crop canopy water stress."
                })
            elif forecast_temp < (hist_avg_temp - 3.0):
                insights.append({
                    'type': 'info',
                    'title': 'Cooler Weather Notice',
                    'message': f"Temperature ({forecast_temp:.1f}°C) is currently cooler than typical historical norms ({hist_avg_temp:.1f}°C)."
                })
        else:
            insights.append({
                'type': 'info',
                'title': 'Historical Baseline Comparison',
                'message': 'Historical climate data loaded. Review seasonal charts for multi-year trends.'
            })

        return insights
