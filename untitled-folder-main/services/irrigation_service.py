from typing import Dict, List, Optional

class IrrigationService:
    """
    Smart Irrigation Advisory Service:
    - Assesses crop water requirements based on crop taxonomy and phenology.
    - Factors in upcoming forecast rainfall, ambient temperatures, and soil drainage characteristics.
    - Generates actionable, timely scheduling recommendations for farmers.
    - Maintains scientific integrity without fabricating uncalibrated sensor metrics.
    """
    
    # Crop water requirement classification (Total seasonal crop evapotranspiration requirement)
    CROP_WATER_NEEDS = {
        'Paddy (Rice)': 'High',
        'Paddy': 'High',
        'Sugarcane': 'High',
        'Banana': 'High',
        'Papaya': 'High',
        'Wheat': 'Medium',
        'Maize': 'Medium',
        'Cotton': 'Medium',
        'Groundnut': 'Medium',
        'Chilli': 'Medium',
        'Tomato': 'Medium',
        'Brinjal (Eggplant)': 'Medium',
        'Brinjal': 'Medium',
        'Onion': 'Medium',
        'Garlic': 'Medium',
        'Tapioca': 'Medium',
        'Sunflower': 'Medium',
        'Soybean': 'Medium',
        'Turmeric': 'Medium',
        'Carrot': 'Medium',
        'Millet': 'Low',
        'Bajra (Pearl Millet)': 'Low',
        'Bajra': 'Low',
        'Ragi (Finger Millet)': 'Low',
        'Ragi': 'Low',
        'Black Gram': 'Low',
        'Green Gram (Moong)': 'Low',
        'Green Gram': 'Low',
        'Horsegram': 'Low',
        'Cowpea': 'Low',
        'Sesame': 'Low',
        'Castor': 'Low',
        'Coriander': 'Low',
        'Cumin': 'Low'
    }

    @staticmethod
    def get_water_requirement_tier(crop_name: str) -> str:
        """Return water requirement tier: High, Medium, or Low"""
        for k, v in IrrigationService.CROP_WATER_NEEDS.items():
            if k.lower() in crop_name.lower():
                return v
        return 'Medium'

    def generate_irrigation_advisory(self, crop_name: str, weather: Dict, soil: Dict, growth_days: int = 100) -> Dict:
        """
        Generate agronomically sound irrigation advice based on upcoming weather and soil properties.
        """
        temp = float(weather.get('temperature (°C)', 28.0))
        rainfall_forecast = float(weather.get('rainfall (mm)', 0.0))
        soil_type = str(soil.get('type', 'Red Loam'))
        precip_prob = float(weather.get('precipitation_prob (%)', 0.0))
        water_need = self.get_water_requirement_tier(crop_name)

        advisories = []
        action_status = "NORMAL"  # NORMAL, POSTPONE, CRITICAL_IRRIGATE, CAUTION
        urgency_level = "Low"

        # 1. Upcoming Rainfall Forecast Rules
        if rainfall_forecast >= 25.0 or precip_prob >= 70.0:
            action_status = "POSTPONE"
            urgency_level = "High"
            advisories.append(f"Significant rainfall expected ({rainfall_forecast:.1f} mm). Postpone irrigation to avoid waterlogging and nitrogen leaching.")
        elif rainfall_forecast >= 10.0:
            action_status = "POSTPONE"
            urgency_level = "Medium"
            advisories.append(f"Light-to-moderate rain forecast ({rainfall_forecast:.1f} mm). Defer planned irrigation and monitor field moisture after showers.")
        elif rainfall_forecast < 5.0 and temp >= 34.0:
            action_status = "CRITICAL_IRRIGATE"
            urgency_level = "High"
            advisories.append(f"High atmospheric demand ({temp:.1f}°C) with negligible rain forecast. High evapotranspiration risk: schedule irrigation early morning or late evening.")
        else:
            advisories.append("Weather conditions are moderate. Maintain standard soil moisture based on the current crop growth stage.")

        # 2. Crop-specific water need rules
        if water_need == 'High':
            advisories.append(f"{crop_name} is a high-water-demand crop. Ensure standing water or continuous moisture during critical tillering/panicle initiation stages.")
        elif water_need == 'Low':
            advisories.append(f"{crop_name} is drought-hardy and sensitive to excess moisture. Avoid over-irrigation to prevent root rot and wilt diseases.")

        # 3. Soil moisture retention characteristics
        if 'sandy' in soil_type.lower():
            advisories.append(f"{soil_type} has rapid percolation and low moisture retention. Provide lighter, more frequent irrigation cycles.")
        elif 'black' in soil_type.lower():
            advisories.append(f"{soil_type} (Vertisol) has high clay content and water holding capacity. Allow surface drying between waterings to ensure soil aeration.")
        else:
            advisories.append(f"{soil_type} offers balanced drainage and moisture retention.")

        # Summary title
        if action_status == "POSTPONE":
            headline = "Postpone Irrigation – Rain Expected"
            badge_color = "#e65100"  # Orange
        elif action_status == "CRITICAL_IRRIGATE":
            headline = "Irrigation Recommended – Heat & Dry Spell"
            badge_color = "#c62828"  # Red
        else:
            headline = "Routine Irrigation Schedule"
            badge_color = "#2e7d32"  # Green

        return {
            'crop': crop_name,
            'water_requirement_tier': water_need,
            'action_status': action_status,
            'urgency_level': urgency_level,
            'headline': headline,
            'badge_color': badge_color,
            'guidance': advisories,
            'disclaimer': 'Irrigation guidance is derived from regional atmospheric forecast and crop phenology models. For micro-irrigation systems (drip/sprinkler), calibrate with tensiometer or local soil moisture measurements.'
        }
