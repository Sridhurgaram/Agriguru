import os
import pandas as pd
from fuzzywuzzy import fuzz
from typing import Dict, Optional, Tuple
from config import Config

class SoilService:
    """
    Soil Analysis Service:
    - Loads and manages Tamil Nadu district soil database.
    - Handles district normalization, aliases, and fuzzy matching.
    - Distinguishes District Averages from Farm Laboratory Soil Tests.
    - Provides agronomic pH and NPK compatibility ratings and amendment advisories.
    """
    SOIL_TYPE_MAPPING = {
        'Red Sandy': 'Red Sandy Loam',
        'Red Loam': 'Red Loamy Soil',
        'Laterite': 'Lateritic Soil',
        'Alluvial': 'Alluvial Soil',
        'Black Soil': 'Black Cotton Soil',
        'Sandy Coastal': 'Sandy Coastal',
        'Sandy Loam': 'Sandy Loam',
        'Clay Loam': 'Clay Loam',
        'Loamy Sand': 'Loamy Sand',
        'Well-Drained Loam': 'Well-Drained Loam',
        'Forest Loam': 'Forest Loam',
        'Volcanic Red Loam': 'Volcanic Red Loam'
    }

    # Canonical Tamil Nadu district aliases mapping (handles new & partitioned districts)
    DISTRICT_ALIASES = {
        'chengalpattu': 'Kanchipuram',
        'kancheepuram': 'Kanchipuram',
        'ranipet': 'Vellore',
        'tirupathur': 'Vellore',
        'tirupattur': 'Vellore',
        'kallakurichi': 'Villupuram',
        'viluppuram': 'Villupuram',
        'tenkasi': 'Tirunelveli',
        'mayiladuthurai': 'Thanjavur',
        'madurai': 'Madurai',
        'trichy': 'Trichy',
        'tiruchirappalli': 'Trichy',
        'thoothukudi': 'Thoothukudi',
        'tuticorin': 'Thoothukudi',
        'tirunelveli': 'Tirunelveli',
        'tiruppur': 'Tiruppur',
        'tiruvallur': 'Tiruvallur',
        'tiruvannamalai': 'Tiruvannamalai',
        'tiruvarur': 'Tiruvarur',
        'sivaganga': 'Sivagangai',
        'sivagangai': 'Sivagangai',
        'nilgiris': 'Nilgiris',
        'the nilgiris': 'Nilgiris',
        'ooty': 'Nilgiris',
        'kanyakumari': 'Kanyakumari',
        'pudukkottai': 'Trichy',
        'theni': 'Dindigul'
    }

    # Representative quantitative NPK benchmarks in kg/ha based on TNAU soil testing norms
    NPK_NUMERICAL_BENCHMARKS = {
        'N': {'Low': 140.0, 'Medium': 350.0, 'High': 560.0},
        'P': {'Low': 12.0, 'Medium': 22.0, 'High': 40.0},
        'K': {'Low': 110.0, 'Medium': 210.0, 'High': 350.0}
    }

    def __init__(self):
        self.district_soil_df = self._load_district_soil_data()

    def _load_district_soil_data(self) -> pd.DataFrame:
        """Load and clean district soil dataset"""
        path = Config.DATA_FILES['district_soil']
        if not os.path.exists(path):
            raise FileNotFoundError(f"District soil dataset not found at {path}")
        
        df = pd.read_csv(path)
        df['District'] = df['District'].astype(str).str.strip().str.title()
        df['Soil_Type'] = df['Soil_Type'].replace(self.SOIL_TYPE_MAPPING)
        return df

    def match_district(self, query: str) -> Optional[str]:
        """Match district using exact, canonical aliases, and fuzzy ratio"""
        if not query:
            return None
        
        cleaned = query.strip().lower()
        
        # Check alias dictionary first
        if cleaned in self.DISTRICT_ALIASES:
            target_name = self.DISTRICT_ALIASES[cleaned]
            exact_match = self.district_soil_df[self.district_soil_df['District'].str.lower() == target_name.lower()]
            if not exact_match.empty:
                return exact_match.iloc[0]['District']

        # Exact match
        exact = self.district_soil_df[self.district_soil_df['District'].str.lower() == cleaned]
        if not exact.empty:
            return exact.iloc[0]['District']

        # Fuzzy match
        best_match = None
        best_score = 0
        for dist in self.district_soil_df['District'].unique():
            score = fuzz.token_sort_ratio(cleaned, dist.lower())
            if score > best_score and score >= 70:
                best_score = score
                best_match = dist

        return best_match

    def get_soil_data(self, district_name: str, custom_soil: Optional[Dict] = None) -> Dict:
        """
        Get soil data for recommendation.
        If custom_soil is provided with valid farmer laboratory measurements, use it and label as 'Laboratory Soil Test'.
        Otherwise retrieve district default and clearly label as 'District Average (Estimate)'.
        """
        if custom_soil and custom_soil.get('is_lab_test'):
            # Farmer provided exact lab test
            s_type = custom_soil.get('type') or 'Red Loamy Soil'
            s_type = self.SOIL_TYPE_MAPPING.get(s_type, s_type)
            ph = float(custom_soil.get('pH', 6.5))
            n = float(custom_soil.get('N', 280.0))
            p = float(custom_soil.get('P', 20.0))
            k = float(custom_soil.get('K', 180.0))
            
            return {
                'type': s_type,
                'pH': ph,
                'N': n,
                'P': p,
                'K': k,
                'N_rating': self.categorize_nutrient('N', n),
                'P_rating': self.categorize_nutrient('P', p),
                'K_rating': self.categorize_nutrient('K', k),
                'source': 'Farmer Laboratory Soil Test (Precise)',
                'is_lab_test': True,
                'warning': None,
                'amendments': self.generate_soil_amendments(ph, n, p, k)
            }

        matched_district = self.match_district(district_name)
        if not matched_district:
            # Fallback to Chennai or TN average if district completely unknown
            matched_district = "Chennai"
            warning_msg = f"District '{district_name}' could not be verified. Applied default Tamil Nadu soil profile. Soil testing strongly advised."
        else:
            warning_msg = f"Soil measurements are regional district averages for {matched_district}. For precise nutrient management, laboratory soil testing is recommended."

        soil_row = self.district_soil_df[self.district_soil_df['District'] == matched_district].iloc[0]
        s_type = self.SOIL_TYPE_MAPPING.get(soil_row['Soil_Type'], soil_row['Soil_Type'])
        ph = float(soil_row['pH'])
        n_cat = str(soil_row['N']).strip().capitalize()
        p_cat = str(soil_row['P']).strip().capitalize()
        k_cat = str(soil_row['K']).strip().capitalize()

        n_num = self.NPK_NUMERICAL_BENCHMARKS['N'].get(n_cat, 350.0)
        p_num = self.NPK_NUMERICAL_BENCHMARKS['P'].get(p_cat, 22.0)
        k_num = self.NPK_NUMERICAL_BENCHMARKS['K'].get(k_cat, 210.0)

        return {
            'type': s_type,
            'pH': ph,
            'N': n_num,
            'P': p_num,
            'K': k_num,
            'N_rating': n_cat,
            'P_rating': p_cat,
            'K_rating': k_cat,
            'district_matched': matched_district,
            'source': f'District-Level Estimate ({matched_district})',
            'is_lab_test': False,
            'warning': warning_msg,
            'amendments': self.generate_soil_amendments(ph, n_num, p_num, k_num)
        }

    def categorize_nutrient(self, nutrient: str, value: float) -> str:
        """Categorize continuous nutrient value (kg/ha) into Low, Medium, High"""
        if nutrient == 'N':
            return 'Low' if value < 280 else ('High' if value > 560 else 'Medium')
        elif nutrient == 'P':
            return 'Low' if value < 11 else ('High' if value > 25 else 'Medium')
        elif nutrient == 'K':
            return 'Low' if value < 140 else ('High' if value > 280 else 'Medium')
        return 'Medium'

    def check_ph_compatibility(self, soil_ph: float, ph_min: float, ph_max: float) -> Tuple[float, str]:
        """
        Calculate agronomic pH compatibility score (0.0 to 1.0) and description
        """
        if ph_min <= soil_ph <= ph_max:
            return 1.0, f"Optimal pH ({soil_ph:.1f} within ideal range {ph_min}-{ph_max})"
        elif (ph_min - 0.5) <= soil_ph <= (ph_max + 0.5):
            return 0.75, f"Tolerable pH ({soil_ph:.1f} close to ideal range {ph_min}-{ph_max})"
        elif (ph_min - 1.0) <= soil_ph <= (ph_max + 1.0):
            return 0.45, f"Moderate pH Stress ({soil_ph:.1f} deviates from {ph_min}-{ph_max})"
        else:
            return 0.20, f"Severe pH Stress ({soil_ph:.1f} unsuitable for crop requirement {ph_min}-{ph_max})"

    def check_soil_type_match(self, crop_soil_type: str, soil_type: str) -> Tuple[float, str]:
        """
        Check soil mechanical compatibility (exact match vs acceptable soil group)
        """
        crop_s = self.SOIL_TYPE_MAPPING.get(crop_soil_type, crop_soil_type).lower()
        actual_s = self.SOIL_TYPE_MAPPING.get(soil_type, soil_type).lower()

        if crop_s == actual_s:
            return 1.0, f"Exact match for {soil_type}"
        
        # Loam and alluvial groups
        loam_group = ['alluvial soil', 'red loamy soil', 'red sandy loam', 'well-drained loam', 'sandy loam']
        if crop_s in loam_group and actual_s in loam_group:
            return 0.85, f"High compatibility: {soil_type} supports {crop_soil_type} growth"
        
        # Black soil (vertisol) vs clay
        if 'black' in crop_s and 'black' in actual_s:
            return 1.0, "High compatibility for black cotton soil"

        # Moderate general tolerance
        return 0.55, f"Moderate compatibility: {soil_type} can support with organic amendment"

    def generate_soil_amendments(self, ph: float, n: float, p: float, k: float) -> list:
        """Generate agronomically sound soil amendment advice"""
        advisories = []
        if ph < 6.0:
            advisories.append("Soil is acidic (pH < 6.0). Apply agricultural lime or dolomite at 1-2 tonnes/ha to neutralize acidity.")
        elif ph > 8.0:
            advisories.append("Soil is alkaline (pH > 8.0). Apply gypsum (calcium sulfate) or well-decomposed organic compost to improve permeability.")
        else:
            advisories.append("Soil pH is well-balanced for most crops in Tamil Nadu.")

        if n < 200:
            advisories.append("Nitrogen status is Low. Incorporate green manures (e.g. Dhaincha / Sunnhemp) or farmyard manure (FYM).")
        if p < 15:
            advisories.append("Phosphorus status is Low. Apply rock phosphate or single superphosphate (SSP) with biofertilizer (PSB).")
        if k < 140:
            advisories.append("Potassium status is Low. Supplement with Muriate of Potash (MOP) during critical vegetative stages.")
            
        return advisories
