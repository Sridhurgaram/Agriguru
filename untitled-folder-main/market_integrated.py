import sys
import os

try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from config import Config
from services.recommendation_service import RecommendationService

class IntegratedRecommendationSystem:
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

    print("\n=== Final Recommendation Report ===")
    print(f"Location: {results['coordinates']['latitude']}, {results['coordinates']['longitude']}")
    print(f"District: {results['district']}")
    print(f"Season: {results['season']}")
    
    w = results['weather']
    print("\nWeather Conditions:")
    print(f"- Temperature: {w.get('temperature (°C)')}°C")
    print(f"- Humidity: {w.get('humidity (%)')}%")
    print(f"- Rainfall: {w.get('rainfall (mm)')} mm")
    print(f"- Source: {w.get('source', 'Unknown')}")
    
    s = results['soil']
    print("\nSoil Conditions:")
    print(f"- Type: {s.get('type')}")
    print(f"- pH: {s.get('pH')}")
    print(f"- Nutrients (N-P-K): {s.get('N')}-{s.get('P')}-{s.get('K')} ({s.get('source')})")
    
    print("\nTop Most Profitable Recommended Crops:")
    print("=" * 125)
    print(f"{'Rank':<5}{'Crop':<28}{'Suitability':<14}{'Price/Qtl':<14}{'Gross Rev/Acre':<18}{'Net Profit/Acre':<18}{'ROI (%)':<12}{'Days':<8}")
    print("-" * 125)
    for rank, crop in enumerate(results['recommendations'], 1):
        roi_str = f"{crop['roi_percent']:.1f}%"
        print(f"{rank:<5}{crop['crop']:<28}{crop['suitability_score']:<14.1f}Rs {crop['market_price_per_quintal']:<11.1f}Rs {crop['gross_revenue_per_acre']:<15.1f}Rs {crop['net_profit_per_acre']:<15.1f}{roi_str:<12}{crop['growth_days']:<8}")
    print("=" * 125)

if __name__ == "__main__":
    if len(sys.argv) >= 5:
        lat, lon, district, date = sys.argv[1:5]
        print(f"Input Details:\nLatitude: {lat}\nLongitude: {lon}\nDistrict: {district}\nDate: {date}\n")
        run_recommendation(lat, lon, district, date)
    else:
        # Default test run
        run_recommendation(13.0827, 80.2707, "Chennai", "2026-11-05")
