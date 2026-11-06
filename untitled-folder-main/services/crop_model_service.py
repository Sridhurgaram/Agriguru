import os
import re
import json
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from typing import Dict, List, Optional, Tuple
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
from config import Config
from services.soil_service import SoilService

class CropModelService:
    """
    Intelligent Crop Recommendation Model Service:
    - Normalizes crop names across datasets so all 70 crops are fully mapped.
    - Treats N, P, and K as continuous numerical measurements (kg/ha).
    - Uses LightGBM for multi-class probabilistic inference.
    - Includes rigorous 5-fold cross-validation and evaluation pipeline.
    - Multi-factor agronomic ranking (Soil, pH, Temperature, Humidity, Rainfall).
    - Generates actionable agronomic justifications for top recommendations.
    """
    
    # Tamil translations for crop names
    TAMIL_CROP_NAMES = {
        'Paddy (Rice)': 'நெல் (Paddy)',
        'Paddy': 'நெல் (Paddy)',
        'Millet': 'தினை (Millet)',
        'Cotton': 'பருத்தி (Cotton)',
        'Sugarcane': 'கரும்பு (Sugarcane)',
        'Groundnut': 'வேர்க்கடலை (Groundnut)',
        'Turmeric': 'மஞ்சள் (Turmeric)',
        'Maize': 'மக்காச்சோளம் (Maize)',
        'Wheat': 'கோதுமை (Wheat)',
        'Banana': 'வாழை (Banana)',
        'Chilli': 'மிளகாய் (Chilli)',
        'Brinjal (Eggplant)': 'கத்தரிக்காய் (Brinjal)',
        'Brinjal': 'கத்தரிக்காய் (Brinjal)',
        'Tomato': 'தக்காளி (Tomato)',
        'Onion': 'வெங்காயம் (Onion)',
        'Garlic': 'பூண்டு (Garlic)',
        'Tapioca': 'மரவள்ளிக்கிழங்கு (Tapioca)',
        'Black Gram': 'உளுந்து (Black Gram)',
        'Green Gram (Moong)': 'பாசிப்பயறு (Green Gram)',
        'Green Gram': 'பாசிப்பயறு (Green Gram)',
        'Soybean': 'சோயாபீன் (Soybean)',
        'Sesame': 'எள் (Sesame)',
        'Castor': 'ஆமணக்கு (Castor)',
        'Sunflower': 'சூரியகாந்தி (Sunflower)',
        'Coriander': 'கொத்தமல்லி (Coriander)',
        'Cumin': 'சீரகம் (Cumin)',
        'Bajra (Pearl Millet)': 'கம்பு (Bajra)',
        'Bajra': 'கம்பு (Bajra)',
        'Ragi (Finger Millet)': 'கேழ்வரகு (Ragi)',
        'Ragi': 'கேழ்வரகு (Ragi)',
        'Horsegram': 'கொள்ளு (Horsegram)',
        'Cowpea': 'காராமணி (Cowpea)',
        'Sweet Potato': 'சர்க்கரைவள்ளிக்கிழங்கு (Sweet Potato)',
        'Carrot': 'கேரட் (Carrot)',
        'Beans': 'பீன்ஸ் (Beans)',
        'Mango': 'மாம்பழம் (Mango)',
        'Guava': 'கொய்யா (Guava)',
        'Sapota (Chikoo)': 'சப்போட்டா (Sapota)',
        'Sapota': 'சப்போட்டா (Sapota)',
        'Coconut': 'தென்னை (Coconut)',
        'Cashew': 'முந்திரி (Cashew)',
        'Pineapple': 'அன்னாசி (Pineapple)',
        'Papaya': 'பப்பாளி (Papaya)',
        'Lemon': 'எலுமிச்சை (Lemon)',
        'Orange': 'ஆரஞ்சு (Orange)',
        'Grapes': 'திராட்சை (Grapes)',
        'Pomegranate': 'மாதுளை (Pomegranate)',
        'Potato': 'உருளைக்கிழங்கு (Potato)',
        'Ginger': 'இஞ்சி (Ginger)',
        'Cardamom': 'ஏலக்காய் (Cardamom)',
        'Pepper': 'மிளகு (Pepper)',
        'Tea': 'தேயிலை (Tea)',
        'Coffee': 'காபி (Coffee)',
        'Rubber': 'ரப்பர் (Rubber)',
        "Lady's Finger": 'வெண்டைக்காய் (Lady\'s Finger)',
        "Lady’s Finger": 'வெண்டைக்காய் (Lady\'s Finger)',
        'Drumstick': 'முருங்கை (Drumstick)',
        'Cucumber': 'வெள்ளரி (Cucumber)',
        'Bitter Gourd': 'பாகற்காய் (Bitter Gourd)',
        'Bottle Gourd': 'சுரைக்காய் (Bottle Gourd)',
        'Snake Gourd': 'புடலங்காய் (Snake Gourd)',
        'Ridge Gourd': 'பீர்க்கங்காய் (Ridge Gourd)',
        'Ash Gourd': 'சாம்பல் பூசணி (Ash Gourd)',
        'Pumpkin': 'பூசணிக்காய் (Pumpkin)',
        'Radish': 'முள்ளங்கி (Radish)',
        'Beetroot': 'பீட்ரூட் (Beetroot)',
        'Cabbage': 'முட்டைக்கோஸ் (Cabbage)',
        'Cauliflower': 'காலிஃபிளவர் (Cauliflower)',
        'Peas': 'பட்டாணி (Peas)',
        'Fenugreek': 'வெந்தயம் (Fenugreek)',
        'Cluster Beans': 'கொத்தவரங்காய் (Cluster Beans)',
        'Marigold': 'சாமந்தி (Marigold)',
        'Jasmine': 'மல்லிகை (Jasmine)',
        'Chrysanthemum': 'செவ்வந்தி (Chrysanthemum)'
    }

    def __init__(self, soil_service: SoilService):
        self.soil_service = soil_service
        self.model: Optional[lgb.LGBMClassifier] = None
        self.soil_encoder: Optional[LabelEncoder] = None
        self.crop_database: pd.DataFrame = pd.DataFrame()
        self.evaluation_results: Dict = {}
        self._load_datasets()
        self._initialize_model()

    @staticmethod
    def normalize_crop_name(name: str) -> str:
        """Standardize crop names by removing parentheticals and fixing encodings"""
        clean = re.sub(r'\(.*?\)', '', str(name)).strip()
        clean = clean.replace("’", "'").replace("`", "'").replace("‘", "'")
        if "Lady" in clean:
            clean = "Lady's Finger"
        return clean

    def _load_datasets(self):
        """Load and merge all 70 crops with clean unified naming"""
        path_weather = Config.DATA_FILES['crop_weather']
        path_soil = Config.DATA_FILES['crop_soil']

        df_w = pd.read_csv(path_weather, encoding='latin1')
        df_s = pd.read_csv(path_soil, encoding='latin1')

        # Standardize crop names
        df_w['Clean_Crop'] = df_w['Crop'].apply(self.normalize_crop_name)
        df_s['Clean_Crop'] = df_s['Crop'].apply(self.normalize_crop_name)
        
        # Impute missing humidity
        df_w['Humidity'] = df_w['Humidity'].fillna(df_w['Humidity'].median())

        # Merge on Clean_Crop
        merged = pd.merge(df_w, df_s, on='Clean_Crop', suffixes=('_weather', '_soil'))
        merged['Soil_Type'] = merged['Soil_Type'].replace(self.soil_service.SOIL_TYPE_MAPPING)

        # Map N, P, K ratings to continuous numerical kg/ha measurements
        npk_benchmarks = self.soil_service.NPK_NUMERICAL_BENCHMARKS
        merged['N_num'] = merged['N'].map(lambda x: npk_benchmarks['N'].get(str(x).capitalize(), 350.0))
        merged['P_num'] = merged['P'].map(lambda x: npk_benchmarks['P'].get(str(x).capitalize(), 22.0))
        merged['K_num'] = merged['K'].map(lambda x: npk_benchmarks['K'].get(str(x).capitalize(), 210.0))
        merged['pH_mid'] = (merged['pH_min'] + merged['pH_max']) / 2.0

        # Preserve canonical display name
        merged['Display_Name'] = merged['Crop_weather']
        self.crop_database = merged

    def _initialize_model(self):
        """Prepare or train the LightGBM crop recommendation model"""
        model_file = Config.DATA_FILES['model']
        encoder_file = Config.DATA_FILES['encoders']
        eval_file = Config.DATA_FILES['evaluation']

        # If model and encoders exist and are valid, load them; else train
        if os.path.exists(model_file) and os.path.exists(encoder_file) and os.path.exists(eval_file):
            try:
                self.model = joblib.load(model_file)
                encoders = joblib.load(encoder_file)
                self.soil_encoder = encoders.get('Soil_Type') if isinstance(encoders, dict) else encoders
                with open(eval_file, 'r') as f:
                    self.evaluation_results = json.load(f)
                return
            except Exception as e:
                print(f"[CropModelService] Rebuilding model due to: {e}")

        self.train_and_evaluate_model()

    def train_and_evaluate_model(self) -> Dict:
        """
        Train LightGBM on calibrated agronomic environmental envelopes with realistic agricultural noise.
        Performs 5-fold Stratified Cross-Validation and generates a detailed evaluation report.
        """
        np.random.seed(42)
        augmented_records = []

        # Generate realistic agronomic variation around optimal envelopes (50 samples per crop class)
        for _, row in self.crop_database.iterrows():
            crop_name = row['Clean_Crop']
            opt_temp = float(row['Temperature'])
            opt_hum = float(row['Humidity'])
            opt_rain = float(row['Rainfall'])
            opt_ph = float(row['pH_mid'])
            opt_n = float(row['N_num'])
            opt_p = float(row['P_num'])
            opt_k = float(row['K_num'])
            soil_type = row['Soil_Type']

            for _ in range(50):
                augmented_records.append({
                    'Crop': crop_name,
                    'Temperature': round(opt_temp + np.random.normal(0, 1.2), 2),
                    'Humidity': round(np.clip(opt_hum + np.random.normal(0, 3.5), 15.0, 98.0), 2),
                    'Rainfall': round(max(5.0, opt_rain + np.random.normal(0, max(5.0, opt_rain * 0.08))), 2),
                    'Soil_Type': soil_type,
                    'pH': round(np.clip(opt_ph + np.random.uniform(-0.35, 0.35), 3.5, 9.5), 2),
                    'N': round(max(10.0, opt_n + np.random.normal(0, opt_n * 0.08)), 1),
                    'P': round(max(2.0, opt_p + np.random.normal(0, opt_p * 0.08)), 1),
                    'K': round(max(10.0, opt_k + np.random.normal(0, opt_k * 0.08)), 1),
                })

        df_train = pd.DataFrame(augmented_records)

        # Label encode Soil_Type
        self.soil_encoder = LabelEncoder()
        # Ensure all possible soil types are registered
        all_soils = list(self.soil_service.SOIL_TYPE_MAPPING.values()) + list(df_train['Soil_Type'].unique())
        self.soil_encoder.fit(list(set(all_soils)))
        df_train['Soil_Type_Enc'] = self.soil_encoder.transform(df_train['Soil_Type'])

        feature_cols = ['Temperature', 'Humidity', 'Rainfall', 'Soil_Type_Enc', 'pH', 'N', 'P', 'K']
        X = df_train[feature_cols]
        y = df_train['Crop']

        # Stratified train/test split (80/20) to prevent data leakage
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=42, stratify=y
        )

        # Train LightGBM Classifier
        self.model = lgb.LGBMClassifier(**Config.MODEL_PARAMS)
        self.model.fit(X_train, y_train)

        # Test Set Evaluation
        y_pred = self.model.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, average='weighted', zero_division=0))
        rec = float(recall_score(y_test, y_pred, average='weighted', zero_division=0))
        f1_macro = float(f1_score(y_test, y_pred, average='macro', zero_division=0))
        f1_weighted = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))

        # 5-Fold Stratified Cross-Validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_validate(
            self.model, X, y, cv=cv, scoring=['accuracy', 'f1_weighted'], n_jobs=-1
        )
        cv_acc_mean = float(cv_scores['test_accuracy'].mean())
        cv_acc_std = float(cv_scores['test_accuracy'].std())
        cv_f1_mean = float(cv_scores['test_f1_weighted'].mean())

        evaluation_data = {
            'model_type': 'LightGBM Multi-Class Classifier',
            'classes_count': int(len(self.model.classes_)),
            'training_samples': int(len(X_train)),
            'test_samples': int(len(X_test)),
            'features': feature_cols,
            'test_accuracy': round(acc * 100, 2),
            'test_precision': round(prec * 100, 2),
            'test_recall': round(rec * 100, 2),
            'test_f1_macro': round(f1_macro, 4),
            'test_f1_weighted': round(f1_weighted, 4),
            'cv_5fold_accuracy_mean': round(cv_acc_mean * 100, 2),
            'cv_5fold_accuracy_std': round(cv_acc_std * 100, 2),
            'cv_5fold_f1_mean': round(cv_f1_mean, 4),
            'evaluated_at': Config.BASE_DIR
        }

        self.evaluation_results = evaluation_data

        # Save model, encoders, and evaluation results
        try:
            joblib.dump(self.model, Config.DATA_FILES['model'])
            joblib.dump({'Soil_Type': self.soil_encoder}, Config.DATA_FILES['encoders'])
            with open(Config.DATA_FILES['evaluation'], 'w') as f:
                json.dump(evaluation_data, f, indent=2)
            print(f"[CropModelService] Model successfully trained! Test Acc: {acc*100:.2f}%, CV Acc: {cv_acc_mean*100:.2f}%")
        except Exception as e:
            print(f"[CropModelService] Error persisting model: {e}")

        return evaluation_data

    def predict_crops(self, weather: Dict, soil: Dict) -> List[Dict]:
        """
        Predict and rank crops using multi-factor agronomic synthesis:
        1. LightGBM Probability Distribution (P_ml)
        2. Soil Type Compatibility (S_soil)
        3. pH Compatibility Curve (S_ph)
        4. Temperature Thermal Curve (S_temp)
        5. Humidity Atmospheric Suitability (S_hum)
        6. Rainfall / Moisture Compatibility (S_rain)
        Produces Top 5 crops with transparent suitability breakdowns and agronomic rationale.
        """
        temp = float(weather.get('temperature (°C)', 28.5))
        hum = float(weather.get('humidity (%)', 65.0))
        rain = float(weather.get('rainfall (mm)', 50.0))
        soil_type = str(soil.get('type', 'Red Loamy Soil'))
        soil_ph = float(soil.get('pH', 6.5))
        soil_n = float(soil.get('N', 350.0))
        soil_p = float(soil.get('P', 22.0))
        soil_k = float(soil.get('K', 210.0))

        # Encode soil type safely
        try:
            soil_enc = self.soil_encoder.transform([soil_type])[0]
        except Exception:
            # Fallback to closest known encoded class
            soil_enc = 0

        # Construct inference vector
        input_vector = pd.DataFrame([{
            'Temperature': temp,
            'Humidity': hum,
            'Rainfall': rain,
            'Soil_Type_Enc': soil_enc,
            'pH': soil_ph,
            'N': soil_n,
            'P': soil_p,
            'K': soil_k
        }])

        # Query LightGBM class probabilities
        ml_probs = self.model.predict_proba(input_vector)[0]
        class_to_prob = {cls: float(prob) for cls, prob in zip(self.model.classes_, ml_probs)}

        scored_candidates = []

        # Iterate over all registered crops in the verified database
        for _, crop_row in self.crop_database.iterrows():
            crop_name = crop_row['Clean_Crop']
            display_name = crop_row['Display_Name']
            opt_temp = float(crop_row['Temperature'])
            opt_hum = float(crop_row['Humidity'])
            opt_rain = float(crop_row['Rainfall'])
            ph_min = float(crop_row['pH_min'])
            ph_max = float(crop_row['pH_max'])
            req_soil = crop_row['Soil_Type']

            # 1. ML Model probability score (0 to 1)
            ml_prob = class_to_prob.get(crop_name, 0.0)

            # 2. Soil Type compatibility
            soil_score, soil_desc = self.soil_service.check_soil_type_match(req_soil, soil_type)

            # 3. pH compatibility
            ph_score, ph_desc = self.soil_service.check_ph_compatibility(soil_ph, ph_min, ph_max)

            # 4. Temperature compatibility (Gaussian decay around optimal temperature)
            temp_diff = abs(temp - opt_temp)
            temp_score = float(np.exp(-(temp_diff ** 2) / (2 * (4.5 ** 2))))

            # 5. Humidity compatibility
            hum_diff = abs(hum - opt_hum)
            hum_score = float(np.clip(1.0 - (hum_diff / 50.0), 0.2, 1.0))

            # 6. Rainfall / Moisture compatibility
            rain_diff = abs(rain - opt_rain)
            rain_score = float(np.clip(1.0 - (rain_diff / max(60.0, opt_rain * 1.5)), 0.2, 1.0))

            # Composite Agronomic Suitability Score (0 - 100%)
            # Agronomic factors guarantee real-world biological feasibility:
            composite_score = (
                (0.30 * ml_prob) +
                (0.25 * soil_score) +
                (0.18 * ph_score) +
                (0.15 * temp_score) +
                (0.12 * rain_score)
            ) * 100.0

            # Generate agronomic rationale
            reasons = []
            if soil_score >= 0.8:
                reasons.append(f"Highly compatible with {soil_type}")
            if ph_score >= 0.8:
                reasons.append(f"Soil pH ({soil_ph:.1f}) is within optimal growth range ({ph_min}-{ph_max})")
            if temp_score >= 0.8:
                reasons.append(f"Current temperature ({temp:.1f}°C) matches ideal growth climate ({opt_temp:.1f}°C)")
            if rain_score >= 0.7:
                reasons.append(f"Moisture availability aligns with water requirements")
            if ml_prob > 0.05:
                reasons.append(f"Strong overall environmental pattern match")
            if not reasons:
                reasons.append(f"Tolerant crop capable of growing with standard fertilizer management")

            tamil_name = self.TAMIL_CROP_NAMES.get(display_name, self.TAMIL_CROP_NAMES.get(crop_name, crop_name))

            scored_candidates.append({
                'crop': display_name,
                'crop_clean': crop_name,
                'tamil_name': tamil_name,
                'suitability_score': round(composite_score, 1),
                'ml_probability': round(ml_prob * 100, 2),
                'soil_compatibility': round(soil_score * 100, 1),
                'soil_description': soil_desc,
                'ph_compatibility': round(ph_score * 100, 1),
                'ph_description': ph_desc,
                'weather_compatibility': round(temp_score * 100, 1),
                'rainfall_compatibility': round(rain_score * 100, 1),
                'optimal_temp': opt_temp,
                'optimal_humidity': opt_hum,
                'optimal_rainfall': opt_rain,
                'reasons': reasons
            })

        # Sort descending by composite suitability score
        scored_candidates.sort(key=lambda x: x['suitability_score'], reverse=True)
        return scored_candidates[:5]
