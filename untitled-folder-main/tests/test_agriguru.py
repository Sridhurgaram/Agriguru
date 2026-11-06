import os
import sys
import unittest
import json

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from app import app
from services.weather_service import WeatherService
from services.soil_service import SoilService
from services.crop_model_service import CropModelService
from services.irrigation_service import IrrigationService
from services.market_service import MarketService
from services.recommendation_service import RecommendationService
from utils.db import init_db, get_user_by_phone
from utils.security import hash_password, verify_password, mask_aadhaar, sanitize_phone

class AgriGuruSystemTests(unittest.TestCase):
    """
    Comprehensive Test Suite for AgriGuru Platform:
    - Weather API (Tomorrow.io, Open-Meteo, NASA POWER 5-Year Aggregation)
    - Soil Service (District matching, NPK benchmarks, Lab vs District tagging)
    - Crop Model Service (LightGBM multi-class inference, Agronomic ranking)
    - Irrigation Service (Water need tiers, weather rules)
    - Market Service (Revenue, Net Profit, ROI formulas)
    - Flask Endpoints (Recommendation, Weather, Soil, Auth)
    - Coordinates in Tamil Nadu (Chennai, Coimbatore, Madurai, Thanjavur)
    """

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = app.test_client()
        cls.weather_service = WeatherService()
        cls.soil_service = SoilService()
        cls.crop_model_service = CropModelService(cls.soil_service)
        cls.irrigation_service = IrrigationService()
        cls.market_service = MarketService()
        cls.rec_service = RecommendationService()

    # =========================================================================
    # 1. WEATHER & CLIMATE TESTS
    # =========================================================================
    def test_weather_forecast_chennai(self):
        """Test weather service for Chennai coordinates"""
        w = self.weather_service.get_weather_forecast(13.0827, 80.2707, "2026-11-05")
        self.assertIn('temperature (°C)', w)
        self.assertIn('humidity (%)', w)
        self.assertIn('rainfall (mm)', w)
        self.assertIn('source', w)
        self.assertTrue(w['temperature (°C)'] > 10.0)
        self.assertTrue(w['humidity (%)'] > 0.0)

    def test_nasa_historical_climate_aggregation(self):
        """Test NASA POWER 5-year historical climate analysis and aggregation"""
        hist = self.weather_service.get_nasa_historical_climate(13.0827, 80.2707, "2026-11-05")
        self.assertIn('monthly_climate', hist)
        self.assertEqual(len(hist['monthly_climate']), 12)
        self.assertIn('seasonal_comparison', hist)
        self.assertIn('overall_annual_rainfall_mm', hist)
        
        # Verify that accumulated rainfall is non-negative and realistic (>100 mm annually)
        self.assertTrue(hist['overall_annual_rainfall_mm'] > 100.0)
        oct_data = next((m for m in hist['monthly_climate'] if m['month_num'] == 10), None)
        self.assertIsNotNone(oct_data)
        self.assertTrue(oct_data['avg_accumulated_rainfall_mm'] >= 0.0)

    # =========================================================================
    # 2. SOIL SERVICE TESTS
    # =========================================================================
    def test_district_matching(self):
        """Test district matching and canonical aliases"""
        self.assertEqual(self.soil_service.match_district("chennai"), "Chennai")
        self.assertEqual(self.soil_service.match_district("Kanchipuram"), "Kanchipuram")
        self.assertEqual(self.soil_service.match_district("chengalpattu"), "Kanchipuram")
        self.assertEqual(self.soil_service.match_district("Trichy"), "Trichy")
        self.assertEqual(self.soil_service.match_district("tiruchirappalli"), "Trichy")

    def test_soil_data_district_estimate(self):
        """Verify district soil profile is properly tagged as estimate"""
        soil = self.soil_service.get_soil_data("Thanjavur")
        self.assertEqual(soil['type'], "Alluvial Soil")
        self.assertFalse(soil['is_lab_test'])
        self.assertIn("District-Level Estimate", soil['source'])
        self.assertIn('amendments', soil)

    def test_soil_data_farmer_lab_test(self):
        """Verify custom farmer lab test is respected and tagged as precise"""
        custom = {
            'is_lab_test': True,
            'type': 'Black Cotton Soil',
            'pH': 7.5,
            'N': 320,
            'P': 28,
            'K': 240
        }
        soil = self.soil_service.get_soil_data("Chennai", custom_soil=custom)
        self.assertTrue(soil['is_lab_test'])
        self.assertEqual(soil['type'], "Black Cotton Soil")
        self.assertEqual(soil['pH'], 7.5)
        self.assertEqual(soil['N'], 320.0)
        self.assertIn("Farmer Laboratory", soil['source'])

    # =========================================================================
    # 3. CROP MODEL & ML EVALUATION TESTS
    # =========================================================================
    def test_model_evaluation_metrics(self):
        """Verify that model evaluation report contains valid accuracy and CV scores"""
        eval_report = self.crop_model_service.evaluation_results
        self.assertIn('test_accuracy', eval_report)
        self.assertIn('cv_5fold_accuracy_mean', eval_report)
        self.assertIn('test_f1_macro', eval_report)
        # Verify evaluation accuracy is statistically meaningful (>75%)
        self.assertGreater(eval_report['test_accuracy'], 75.0)
        self.assertGreater(eval_report['cv_5fold_accuracy_mean'], 75.0)

    def test_crop_prediction_top5(self):
        """Verify Top 5 crop recommendations are generated with all required fields"""
        weather = {'temperature (°C)': 29.0, 'humidity (%)': 75.0, 'rainfall (mm)': 60.0}
        soil = {'type': 'Alluvial Soil', 'pH': 6.8, 'N': 350.0, 'P': 22.0, 'K': 210.0}
        top5 = self.crop_model_service.predict_crops(weather, soil)
        
        self.assertEqual(len(top5), 5)
        for crop in top5:
            self.assertIn('crop', crop)
            self.assertIn('suitability_score', crop)
            self.assertIn('soil_compatibility', crop)
            self.assertIn('ph_compatibility', crop)
            self.assertIn('weather_compatibility', crop)
            self.assertIn('reasons', crop)
            self.assertTrue(len(crop['reasons']) > 0)
            self.assertTrue(0.0 <= crop['suitability_score'] <= 100.0)

    # =========================================================================
    # 4. IRRIGATION ADVISORY TESTS
    # =========================================================================
    def test_irrigation_advisory_rain_postpone(self):
        """Verify irrigation postponement rule when rainfall is forecast"""
        weather = {'temperature (°C)': 28.0, 'rainfall (mm)': 35.0, 'precipitation_prob (%)': 80.0}
        soil = {'type': 'Alluvial Soil'}
        adv = self.irrigation_service.generate_irrigation_advisory("Paddy (Rice)", weather, soil)
        self.assertEqual(adv['action_status'], "POSTPONE")
        self.assertIn("Postpone", adv['headline'])

    def test_irrigation_advisory_dry_heat(self):
        """Verify critical irrigation recommendation under heat and low rain"""
        weather = {'temperature (°C)': 36.0, 'rainfall (mm)': 0.0, 'precipitation_prob (%)': 10.0}
        soil = {'type': 'Red Sandy Loam'}
        adv = self.irrigation_service.generate_irrigation_advisory("Maize", weather, soil)
        self.assertEqual(adv['action_status'], "CRITICAL_IRRIGATE")

    # =========================================================================
    # 5. MARKET & FINANCIAL PROFITABILITY TESTS
    # =========================================================================
    def test_market_profitability_calculation(self):
        """Verify exact financial formulas: Gross Rev = Yield * Price, Net = Gross - Cost, ROI"""
        crops = [{'crop': 'Paddy (Rice)'}]
        enriched = self.market_service.analyze_profitability(crops, "Thanjavur")
        self.assertEqual(len(enriched), 1)
        p = enriched[0]
        
        expected_gross = p['expected_yield_per_acre_quintal'] * p['market_price_per_quintal']
        expected_net = expected_gross - p['cultivation_cost_per_acre']
        expected_roi = (expected_net / p['cultivation_cost_per_acre']) * 100.0

        self.assertAlmostEqual(p['gross_revenue_per_acre'], expected_gross, delta=0.5)
        self.assertAlmostEqual(p['net_profit_per_acre'], expected_net, delta=0.5)
        self.assertAlmostEqual(p['roi_percent'], expected_roi, delta=0.5)

    # =========================================================================
    # 6. END-TO-END RECOMMENDATION FOR MULTIPLE TAMIL NADU REGIONS
    # =========================================================================
    def test_e2e_tamil_nadu_regions(self):
        """Test full pipeline across representative Tamil Nadu agro-climatic zones"""
        tn_test_points = [
            ("Chennai", 13.0827, 80.2707),
            ("Coimbatore", 11.0168, 76.9558),
            ("Madurai", 9.9252, 78.1198),
            ("Thanjavur", 10.7870, 79.1378)
        ]

        for dist, lat, lon in tn_test_points:
            rec = self.rec_service.get_full_recommendation(lat, lon, dist, "2026-11-05")
            self.assertEqual(rec['status'], 'success')
            self.assertEqual(len(rec['recommendations']), 5)
            self.assertIn('weather', rec)
            self.assertIn('historical_climate', rec)
            self.assertIn('climate_insights', rec)
            self.assertIn('soil', rec)

    # =========================================================================
    # 7. FLASK HTTP ENDPOINTS TESTS
    # =========================================================================
    def test_flask_index_and_chatbot(self):
        """Test standard web routes"""
        res_idx = self.client.get('/')
        self.assertEqual(res_idx.status_code, 200)
        res_chat = self.client.get('/chatbot')
        self.assertEqual(res_chat.status_code, 200)

    def test_flask_api_recommend(self):
        """Test POST /api/recommend REST endpoint"""
        res = self.client.post('/api/recommend', json={
            'latitude': 10.7870,
            'longitude': 79.1378,
            'district': 'Thanjavur',
            'planting_date': '2026-11-05'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(len(data.get('recommendations', [])), 5)

    def test_flask_auth_workflow(self):
        """Test secure registration, password hashing, and login"""
        test_phone = "9876543210"
        
        # Test OTP generation
        res_otp = self.client.post('/api/auth/send_otp', json={'phone': test_phone})
        self.assertEqual(res_otp.status_code, 200)
        
        # Test farmer registration
        res_reg = self.client.post('/api/auth/register_farmer', json={
            'name': 'Ramasamy',
            'phone': test_phone,
            'password': 'secretpassword123',
            'location': 'Kumbakonam',
            'district': 'Thanjavur',
            'aadhaar': '123456789012'
        })
        # Should be 201 Created or 409 Conflict if already in DB
        self.assertIn(res_reg.status_code, [201, 409])

        # Test farmer login
        res_login = self.client.post('/api/auth/login_farmer', json={
            'phone': test_phone,
            'password': 'secretpassword123'
        })
        self.assertEqual(res_login.status_code, 200)
        self.assertTrue(res_login.get_json()['success'])

        # Verify password is not plaintext in DB and Aadhaar is masked
        user = get_user_by_phone(test_phone)
        self.assertIsNotNone(user)
        self.assertNotEqual(user['password_hash'], 'secretpassword123')
        self.assertTrue(user['password_hash'].startswith('pbkdf2:sha256'))
        self.assertTrue(user['aadhaar_masked'].startswith('XXXX-XXXX-'))

if __name__ == '__main__':
    unittest.main()
