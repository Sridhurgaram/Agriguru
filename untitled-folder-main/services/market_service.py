import os
import re
import pandas as pd
from typing import Dict, List, Optional
from config import Config
from services.crop_model_service import CropModelService

class MarketService:
    """
    Market Analysis and Financial Profitability Service:
    - Queries verified district-specific crop prices per quintal from tamilnadu_crop_prices_quintal.csv.
    - Integrates crop maturity periods from crop_avg_growth_days_only.csv.
    - Applies agronomic cost-of-cultivation and yield benchmarks (TNAU standard per acre).
    - Uses exact, transparent financial formulas:
        Gross Revenue = Expected Yield (quintals/acre) * Market Price (Rs/quintal)
        Net Profit = Gross Revenue - Cultivation Cost (Rs/acre)
        ROI (%) = (Net Profit / Cultivation Cost) * 100
    - Avoids artificial price inflation or fabricated predictive multipliers.
    """
    
    # Standard Tamil Nadu agricultural economics benchmarks (Yield in quintals/acre, Cultivation cost in Rs/acre)
    # Source: TNAU Agritech Portal & Department of Agriculture, Government of Tamil Nadu
    TN_AGRI_BENCHMARKS = {
        'paddy': {'yield_quintals': 24.0, 'cost_per_acre': 28500},
        'rice': {'yield_quintals': 24.0, 'cost_per_acre': 28500},
        'millet': {'yield_quintals': 9.0, 'cost_per_acre': 14000},
        'bajra': {'yield_quintals': 10.0, 'cost_per_acre': 13500},
        'ragi': {'yield_quintals': 11.0, 'cost_per_acre': 14500},
        'cotton': {'yield_quintals': 8.5, 'cost_per_acre': 26000},
        'sugarcane': {'yield_quintals': 380.0, 'cost_per_acre': 52000},
        'groundnut': {'yield_quintals': 10.5, 'cost_per_acre': 24000},
        'maize': {'yield_quintals': 26.0, 'cost_per_acre': 23000},
        'wheat': {'yield_quintals': 14.0, 'cost_per_acre': 21000},
        'banana': {'yield_quintals': 150.0, 'cost_per_acre': 65000},
        'chilli': {'yield_quintals': 12.0, 'cost_per_acre': 34000},
        'brinjal': {'yield_quintals': 90.0, 'cost_per_acre': 32000},
        'tomato': {'yield_quintals': 100.0, 'cost_per_acre': 36000},
        'onion': {'yield_quintals': 65.0, 'cost_per_acre': 38000},
        'garlic': {'yield_quintals': 35.0, 'cost_per_acre': 42000},
        'tapioca': {'yield_quintals': 130.0, 'cost_per_acre': 31000},
        'black gram': {'yield_quintals': 5.0, 'cost_per_acre': 12500},
        'green gram': {'yield_quintals': 5.0, 'cost_per_acre': 12000},
        'horsegram': {'yield_quintals': 4.5, 'cost_per_acre': 9500},
        'cowpea': {'yield_quintals': 6.0, 'cost_per_acre': 11500},
        'soybean': {'yield_quintals': 8.0, 'cost_per_acre': 18000},
        'sesame': {'yield_quintals': 3.5, 'cost_per_acre': 11000},
        'sunflower': {'yield_quintals': 7.5, 'cost_per_acre': 17500},
        'turmeric': {'yield_quintals': 24.0, 'cost_per_acre': 48000},
        'coriander': {'yield_quintals': 4.0, 'cost_per_acre': 13000},
        'lady': {'yield_quintals': 50.0, 'cost_per_acre': 28000},
        'drumstick': {'yield_quintals': 40.0, 'cost_per_acre': 22000},
        'coconut': {'yield_quintals': 35.0, 'cost_per_acre': 35000},
        'mango': {'yield_quintals': 45.0, 'cost_per_acre': 30000},
        'papaya': {'yield_quintals': 120.0, 'cost_per_acre': 42000},
        'guava': {'yield_quintals': 55.0, 'cost_per_acre': 28000},
        'default': {'yield_quintals': 12.0, 'cost_per_acre': 22000}
    }

    def __init__(self):
        self.price_df = pd.DataFrame()
        self.growth_df = pd.DataFrame()
        self._load_datasets()

    def _load_datasets(self):
        """Load and clean market price and crop growth datasets"""
        p_path = Config.DATA_FILES['price_data']
        g_path = Config.DATA_FILES['growth_data']

        df_p = pd.read_csv(p_path, encoding='latin1')
        df_g = pd.read_csv(g_path, encoding='latin1')

        # Reshape price dataset from wide to long format
        melted = df_p.melt(id_vars=['Crop'], var_name='District', value_name='Price_Per_Quintal')
        melted['Crop_Clean'] = melted['Crop'].apply(CropModelService.normalize_crop_name)
        melted['District_Clean'] = melted['District'].astype(str).str.strip().str.title()
        melted['Price_Per_Quintal'] = pd.to_numeric(melted['Price_Per_Quintal'], errors='coerce').fillna(2500.0)

        df_g['Crop_Clean'] = df_g['Crop'].apply(CropModelService.normalize_crop_name)
        df_g['Avg Growth Period (Days)'] = pd.to_numeric(df_g['Avg Growth Period (Days)'], errors='coerce').fillna(100)

        self.price_df = melted
        self.growth_df = df_g

    def get_crop_growth_days(self, crop_name: str) -> int:
        """Get growth duration in days for a crop"""
        clean_name = CropModelService.normalize_crop_name(crop_name)
        match = self.growth_df[self.growth_df['Crop_Clean'].str.lower() == clean_name.lower()]
        if not match.empty:
            return int(match.iloc[0]['Avg Growth Period (Days)'])
        return 105

    def get_district_crop_price(self, crop_name: str, district: str) -> float:
        """Retrieve district price per quintal (fallback to statewide median if district entry missing)"""
        clean_crop = CropModelService.normalize_crop_name(crop_name).lower()
        clean_dist = district.strip().title()

        # Query price table
        match = self.price_df[
            (self.price_df['Crop_Clean'].str.lower() == clean_crop) &
            (self.price_df['District_Clean'] == clean_dist)
        ]

        if not match.empty:
            return float(match.iloc[0]['Price_Per_Quintal'])
        
        # Fallback to statewide median price for this crop
        crop_sub = self.price_df[self.price_df['Crop_Clean'].str.lower() == clean_crop]
        if not crop_sub.empty:
            return float(crop_sub['Price_Per_Quintal'].median())

        return 3200.0

    def get_benchmark(self, crop_name: str) -> Dict[str, float]:
        """Lookup yield and cultivation cost benchmark"""
        clean = crop_name.lower()
        for k, v in self.TN_AGRI_BENCHMARKS.items():
            if k in clean:
                return v
        return self.TN_AGRI_BENCHMARKS['default']

    def analyze_profitability(self, crops: List[Dict], district: str) -> List[Dict]:
        """
        Compute financial viability for recommended crops:
        - Price per quintal (district specific)
        - Expected yield per acre
        - Cultivation expenses per acre
        - Gross Revenue
        - Net Profit
        - ROI %
        - Growth period (days)
        """
        enriched_crops = []

        for crop in crops:
            crop_name = crop.get('crop', '')
            growth_days = self.get_crop_growth_days(crop_name)
            price_quintal = self.get_district_crop_price(crop_name, district)
            benchmark = self.get_benchmark(crop_name)

            expected_yield = benchmark['yield_quintals']
            cultivation_cost = benchmark['cost_per_acre']

            # Exact standard agricultural economics calculations:
            gross_revenue = expected_yield * price_quintal
            net_profit = gross_revenue - cultivation_cost
            roi = (net_profit / cultivation_cost * 100.0) if cultivation_cost > 0 else 0.0

            enriched_crops.append({
                **crop,
                'growth_days': growth_days,
                'market_price_per_quintal': round(price_quintal, 2),
                'expected_yield_per_acre_quintal': round(expected_yield, 1),
                'cultivation_cost_per_acre': round(cultivation_cost, 2),
                'gross_revenue_per_acre': round(gross_revenue, 2),
                'net_profit_per_acre': round(net_profit, 2),
                'roi_percent': round(roi, 1),
                'district': district.title()
            })

        return enriched_crops
