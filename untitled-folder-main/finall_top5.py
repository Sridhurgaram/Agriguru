import sys
import os

try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from config import Config
from services.recommendation_service import RecommendationService

class CropRecommendationSystem:
    """Backwards-compatible wrapper delegating to RecommendationService"""
    def __init__(self):
        self.service = RecommendationService()

    def get_recommendations(self, lat: float, lon: float, district_name: str, start_date: str):
        return self.service.get_full_recommendation(
            lat=float(lat),
            lon=float(lon),
            district=str(district_name),
            planting_date=str(start_date)
        )

def run_recommendation(lat, lon, district, date):
    service = RecommendationService()
    results = service.get_full_recommendation(
        lat=float(lat),
        lon=float(lon),
        district=str(district),
        planting_date=str(date)
    )
    
    if results.get('status') == 'error':
        print(f"\n❌ Error: {results.get('message')}")
        return

    print("\n=== Recommendation Report ===")
    print(f"📍 Location: {results['coordinates']['latitude']}, {results['coordinates']['longitude']}")
    print(f"🗺️ District: {results['district']}")
    print(f"📅 Season: {results['season']}")
    
    w = results['weather']
    print("\n🌦️ Weather Conditions:")
    print(f"- Temperature: {w.get('temperature (°C)')}°C")
    print(f"- Humidity: {w.get('humidity (%)')}%")
    print(f"- Rainfall: {w.get('rainfall (mm)')} mm")
    print(f"- Source: {w.get('source', 'Unknown')}")
    
    s = results['soil']
    print("\n🌱 Soil Conditions:")
    print(f"- Type: {s.get('type')}")
    print(f"- pH: {s.get('pH')}")
    print(f"- Nutrients (N-P-K): {s.get('N')}-{s.get('P')}-{s.get('K')} ({s.get('source')})")
    
    print("\n🏆 Top Recommended Crops:")
    for i, crop in enumerate(results['recommendations'], 1):
        print(f"{i}. {crop['crop']} ({crop.get('tamil_name', '')}) - Suitability: {crop['suitability_score']}%")

if __name__ == "__main__":
    if len(sys.argv) >= 5:
        lat, lon, district, date = sys.argv[1:5]
        run_recommendation(lat, lon, district, date)
    else:
        run_recommendation(13.0827, 80.2707, "Chennai", "2026-11-05")