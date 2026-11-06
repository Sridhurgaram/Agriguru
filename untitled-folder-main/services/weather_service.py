import os
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config import Config

class WeatherService:
    """
    Dedicated Weather Service managing:
    1. Tomorrow.io API: Live conditions, short-term and daily forecasts.
    2. Open-Meteo API: High-reliability live forecast fallback when Tomorrow.io quota/key unavailable.
    3. NASA POWER API: 5-year historical agricultural climate analysis (T2M, RH2M, PRECTOTCORR, ALLSKY_SFC_SW_DWN).
    4. Mathematically verified aggregation and persistent multi-tier caching.
    """
    def __init__(self):
        self.cache_dir = Config.CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        self.memory_cache = {}

    # =========================================================================
    # 1. TOMORROW.IO API INTEGRATION
    # =========================================================================
    def _fetch_tomorrow_realtime(self, lat: float, lon: float) -> Optional[Dict]:
        """Fetch current weather from Tomorrow.io realtime endpoint"""
        api_key = Config.TOMORROW_API_KEY
        if not api_key:
            return None

        url = f"https://api.tomorrow.io/v4/weather/realtime?location={lat},{lon}&apikey={api_key}"
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get('data', {}).get('values', {})
                return {
                    'temperature': round(float(data.get('temperature', 28.0)), 1),
                    'humidity': round(float(data.get('humidity', 65.0)), 1),
                    'precipitation_rate': round(float(data.get('precipitationIntensity', 0.0)), 2),
                    'precipitation_probability': round(float(data.get('precipitationProbability', 0.0)), 1),
                    'wind_speed': round(float(data.get('windSpeed', 10.0)) * 3.6, 1), # m/s to km/h
                    'weather_code': data.get('weatherCode', 1000)
                }
        except Exception as e:
            print(f"[WeatherService] Tomorrow.io realtime error: {e}")
        return None

    def _fetch_tomorrow_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """Fetch daily forecast timeline from Tomorrow.io"""
        api_key = Config.TOMORROW_API_KEY
        if not api_key:
            return None

        url = f"https://api.tomorrow.io/v4/weather/forecast?location={lat},{lon}&timesteps=1d&apikey={api_key}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                timelines = resp.json().get('timelines', {}).get('daily', [])
                if timelines:
                    forecast_days = []
                    for day in timelines[:7]:
                        vals = day.get('values', {})
                        t_avg = vals.get('temperatureAvg') or vals.get('temperatureApparentAvg') or 28.0
                        rain_sum = vals.get('rainAccumulationSum') or vals.get('precipitationAccumulationSum') or 0.0
                        hum_avg = vals.get('humidityAvg') or 65.0
                        wind_avg = vals.get('windSpeedAvg') or 3.0
                        rain_prob = vals.get('precipitationProbabilityAvg') or vals.get('precipitationProbabilityMax') or 0.0
                        
                        forecast_days.append({
                            'date': day.get('time', '').split('T')[0],
                            'temp_avg': round(float(t_avg), 1),
                            'temp_min': round(float(vals.get('temperatureMin', t_avg - 3)), 1),
                            'temp_max': round(float(vals.get('temperatureMax', t_avg + 3)), 1),
                            'humidity': round(float(hum_avg), 1),
                            'rainfall_mm': round(float(rain_sum), 2),
                            'wind_speed_kmh': round(float(wind_avg) * 3.6, 1),
                            'rain_prob': round(float(rain_prob), 1)
                        })

                    # Calculate multi-day forecast averages
                    df_fc = pd.DataFrame(forecast_days)
                    return {
                        'forecast_days': forecast_days,
                        'avg_temp': round(df_fc['temp_avg'].mean(), 1),
                        'avg_humidity': round(df_fc['humidity'].mean(), 1),
                        'total_rainfall': round(df_fc['rainfall_mm'].sum(), 2),
                        'avg_rain_prob': round(df_fc['rain_prob'].mean(), 1),
                        'avg_wind': round(df_fc['wind_speed_kmh'].mean(), 1)
                    }
        except Exception as e:
            print(f"[WeatherService] Tomorrow.io forecast error: {e}")
        return None

    # =========================================================================
    # 2. OPEN-METEO FALLBACK API (HIGH ACCURACY LIVE SATELLITE/NWP FORECAST)
    # =========================================================================
    def _fetch_open_meteo_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """Fetch 7-day live weather forecast using Open-Meteo"""
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,relative_humidity_2m_mean,wind_speed_10m_max"
            f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
            f"&timezone=auto"
        )
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get('current', {})
                daily = data.get('daily', {})
                
                days_count = len(daily.get('time', []))
                forecast_days = []
                for i in range(min(7, days_count)):
                    t_min = daily['temperature_2m_min'][i]
                    t_max = daily['temperature_2m_max'][i]
                    t_avg = (t_min + t_max) / 2.0
                    rain_sum = daily['precipitation_sum'][i] or 0.0
                    hum = daily['relative_humidity_2m_mean'][i] or 65.0
                    wind = daily['wind_speed_10m_max'][i] or 12.0
                    prob = daily['precipitation_probability_max'][i] or 0.0
                    
                    forecast_days.append({
                        'date': daily['time'][i],
                        'temp_avg': round(t_avg, 1),
                        'temp_min': round(t_min, 1),
                        'temp_max': round(t_max, 1),
                        'humidity': round(hum, 1),
                        'rainfall_mm': round(rain_sum, 2),
                        'wind_speed_kmh': round(wind, 1),
                        'rain_prob': round(prob, 1)
                    })
                
                df_fc = pd.DataFrame(forecast_days)
                return {
                    'current': {
                        'temperature': round(float(current.get('temperature_2m', df_fc['temp_avg'].iloc[0])), 1),
                        'humidity': round(float(current.get('relative_humidity_2m', df_fc['humidity'].iloc[0])), 1),
                        'precipitation_rate': round(float(current.get('precipitation', 0.0)), 2),
                        'precipitation_probability': round(float(df_fc['rain_prob'].iloc[0]), 1),
                        'wind_speed': round(float(current.get('wind_speed_10m', df_fc['wind_speed_kmh'].iloc[0])), 1),
                        'weather_code': 1000
                    },
                    'forecast_days': forecast_days,
                    'avg_temp': round(df_fc['temp_avg'].mean(), 1),
                    'avg_humidity': round(df_fc['humidity'].mean(), 1),
                    'total_rainfall': round(df_fc['rainfall_mm'].sum(), 2),
                    'avg_rain_prob': round(df_fc['rain_prob'].mean(), 1),
                    'avg_wind': round(df_fc['wind_speed_kmh'].mean(), 1)
                }
        except Exception as e:
            print(f"[WeatherService] Open-Meteo fallback error: {e}")
        return None

    # =========================================================================
    # 3. NASA POWER HISTORICAL CLIMATE ANALYSIS
    # =========================================================================
    def get_nasa_historical_climate(self, lat: float, lon: float, reference_date: str = None) -> Dict:
        """
        5-Year Historical Agricultural Climate Analysis via NASA POWER API.
        Retrieves T2M, RH2M, PRECTOTCORR, ALLSKY_SFC_SW_DWN.
        Calculates:
        - Monthly accumulated rainfall (correctly summed across days in each month per year)
        - 5-year average monthly rainfall
        - 5-year average temperature by month
        - 5-year average humidity by month
        - Seasonal comparison (Summer, SW Monsoon, NE Monsoon, Winter)
        - Historical rainfall trends
        """
        ref_dt = datetime.strptime(reference_date, "%Y-%m-%d") if reference_date else datetime.now()
        end_year = ref_dt.year - 1  # Full preceding completed years
        start_year = end_year - 4   # 5-year period (e.g. 2020-2024 or 2019-2023)
        
        cache_key = f"nasa_power_{round(lat, 3)}_{round(lon, 3)}_{start_year}_{end_year}.json"
        cache_file = os.path.join(self.cache_dir, cache_key)
        
        # Check disk cache
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    return cached_data
            except Exception as e:
                print(f"[WeatherService] Cache read error: {e}")

        # Query NASA POWER API
        start_str = f"{start_year}0101"
        end_str = f"{end_year}1231"
        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        params = {
            "parameters": "T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": start_str,
            "end": end_str,
            "format": "JSON"
        }

        try:
            resp = requests.get(url, params=params, timeout=25)
            if resp.status_code == 200:
                p = resp.json().get('properties', {}).get('parameter', {})
                dates = list(p.get('T2M', {}).keys())
                
                records = []
                for d in dates:
                    t2m = p['T2M'].get(d, -999)
                    rh2m = p['RH2M'].get(d, -999)
                    rain = p['PRECTOTCORR'].get(d, -999)
                    solar = p.get('ALLSKY_SFC_SW_DWN', {}).get(d, -999)
                    
                    if t2m > -50 and rh2m >= 0 and rain >= 0:
                        records.append({
                            'date': pd.to_datetime(d, format='%Y%m%d'),
                            'year': int(d[:4]),
                            'month': int(d[4:6]),
                            't2m': t2m,
                            'rh2m': rh2m,
                            'precip': rain,
                            'solar': solar if solar >= 0 else None
                        })
                
                df = pd.DataFrame(records)
                if not df.empty:
                    analysis = self._compute_historical_climate_metrics(df, start_year, end_year, lat, lon)
                    # Cache to disk
                    try:
                        with open(cache_file, 'w') as f:
                            json.dump(
                                analysis, f, indent=2,
                                default=lambda o: int(o) if isinstance(o, (np.integer, int)) else float(o) if isinstance(o, (np.floating, float)) else str(o)
                            )
                    except Exception as e:
                        print(f"[WeatherService] Cache write error: {e}")
                    return analysis
        except Exception as e:
            print(f"[WeatherService] NASA POWER query error: {e}")

        # Fallback historical statistics if NASA POWER offline
        return self._generate_regional_historical_baseline(lat, lon, start_year, end_year)

    def _compute_historical_climate_metrics(self, df: pd.DataFrame, start_year: int, end_year: int, lat: float, lon: float) -> Dict:
        """Mathematically correct climate aggregation"""
        # 1. Monthly Accumulated Rainfall per year
        # In each year and month, sum the daily rainfall mm
        monthly_yearly = df.groupby(['year', 'month']).agg({
            'precip': 'sum',      # Monthly accumulated rainfall in mm
            't2m': 'mean',        # Monthly average temperature
            'rh2m': 'mean',       # Monthly average relative humidity
            'solar': 'mean'       # Monthly average solar radiation
        }).reset_index()

        # 2. 5-Year Average Monthly Accumulation & Means
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_summary = []
        for m in range(1, 13):
            sub = monthly_yearly[monthly_yearly['month'] == m]
            monthly_summary.append({
                'month_num': int(m),
                'month_name': month_names[m - 1],
                'avg_accumulated_rainfall_mm': round(float(sub['precip'].mean()), 1),
                'avg_temperature_c': round(float(sub['t2m'].mean()), 1),
                'avg_humidity_pct': round(float(sub['rh2m'].mean()), 1),
                'avg_solar_radiation_mj': round(float(sub['solar'].mean()), 2) if 'solar' in sub else 18.5,
                'rainfall_std_dev': round(float(sub['precip'].std()), 1) if len(sub) > 1 else 0.0
            })

        # 3. Annual Totals and Trends
        yearly_summary = []
        for yr in sorted(df['year'].unique()):
            sub_yr = monthly_yearly[monthly_yearly['year'] == yr]
            yearly_summary.append({
                'year': int(yr),
                'annual_rainfall_mm': round(float(sub_yr['precip'].sum()), 1),
                'annual_avg_temp_c': round(float(sub_yr['t2m'].mean()), 1),
                'annual_avg_humidity_pct': round(float(sub_yr['rh2m'].mean()), 1)
            })

        # 4. Seasonal Aggregations for Tamil Nadu Agriculture
        # Winter: Jan-Feb
        # Summer: Mar-May
        # SW Monsoon: Jun-Sep
        # NE Monsoon: Oct-Dec (crucial for Tamil Nadu!)
        seasons = {
            'Winter (Jan-Feb)': [1, 2],
            'Summer (Mar-May)': [3, 4, 5],
            'Southwest Monsoon (Jun-Sep)': [6, 7, 8, 9],
            'Northeast Monsoon (Oct-Dec)': [10, 11, 12]
        }
        seasonal_summary = {}
        for s_name, m_list in seasons.items():
            s_data = [m for m in monthly_summary if m['month_num'] in m_list]
            tot_rain = sum(m['avg_accumulated_rainfall_mm'] for m in s_data)
            avg_t = np.mean([m['avg_temperature_c'] for m in s_data])
            avg_h = np.mean([m['avg_humidity_pct'] for m in s_data])
            seasonal_summary[s_name] = {
                'accumulated_rainfall_mm': round(float(tot_rain), 1),
                'avg_temp_c': round(float(avg_t), 1),
                'avg_humidity_pct': round(float(avg_h), 1)
            }

        return {
            'source': 'NASA POWER Agroclimatology (5-Year Historical)',
            'coordinates': {'latitude': lat, 'longitude': lon},
            'period': f"{start_year} - {end_year}",
            'monthly_climate': monthly_summary,
            'annual_trends': yearly_summary,
            'seasonal_comparison': seasonal_summary,
            'overall_annual_rainfall_mm': round(float(np.mean([y['annual_rainfall_mm'] for y in yearly_summary])), 1),
            'overall_annual_avg_temp_c': round(float(np.mean([y['annual_avg_temp_c'] for y in yearly_summary])), 1),
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def _generate_regional_historical_baseline(self, lat: float, lon: float, start_year: int, end_year: int) -> Dict:
        """Statistically grounded regional climate fallback for Tamil Nadu agro-climatic zones"""
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        # Typical TN seasonal rainfall profile (peaking in NE Monsoon Oct-Nov)
        tn_base_rain = [25.0, 15.0, 18.0, 35.0, 55.0, 50.0, 75.0, 110.0, 125.0, 240.0, 290.0, 140.0]
        tn_base_temp = [25.5, 27.0, 29.5, 32.0, 33.5, 31.5, 30.5, 29.8, 29.5, 28.0, 26.5, 25.0]
        tn_base_hum = [68.0, 65.0, 62.0, 65.0, 68.0, 64.0, 66.0, 68.0, 72.0, 80.0, 82.0, 74.0]

        monthly_summary = []
        for i in range(12):
            monthly_summary.append({
                'month_num': i + 1,
                'month_name': month_names[i],
                'avg_accumulated_rainfall_mm': tn_base_rain[i],
                'avg_temperature_c': tn_base_temp[i],
                'avg_humidity_pct': tn_base_hum[i],
                'avg_solar_radiation_mj': 19.0,
                'rainfall_std_dev': round(tn_base_rain[i] * 0.25, 1)
            })

        return {
            'source': 'Tamil Nadu Agro-Climatic Regional Benchmark (Fallback)',
            'coordinates': {'latitude': lat, 'longitude': lon},
            'period': f"{start_year} - {end_year}",
            'monthly_climate': monthly_summary,
            'annual_trends': [],
            'seasonal_comparison': {
                'Winter (Jan-Feb)': {'accumulated_rainfall_mm': 40.0, 'avg_temp_c': 26.2, 'avg_humidity_pct': 66.5},
                'Summer (Mar-May)': {'accumulated_rainfall_mm': 108.0, 'avg_temp_c': 31.7, 'avg_humidity_pct': 65.0},
                'Southwest Monsoon (Jun-Sep)': {'accumulated_rainfall_mm': 360.0, 'avg_temp_c': 30.3, 'avg_humidity_pct': 67.5},
                'Northeast Monsoon (Oct-Dec)': {'accumulated_rainfall_mm': 670.0, 'avg_temp_c': 26.5, 'avg_humidity_pct': 78.7}
            },
            'overall_annual_rainfall_mm': 1178.0,
            'overall_annual_avg_temp_c': 28.7,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # =========================================================================
    # 4. UNIFIED WEATHER INTEGRATION & AGGREGATION
    # =========================================================================
    def get_weather_forecast(self, lat: float, lon: float, start_date: str) -> Dict:
        """
        Unified Weather Forecast Orchestration:
        - Primary: Tomorrow.io API (realtime + daily forecast)
        - Secondary Fallback: Open-Meteo live API
        - Tertiary Fallback: NASA POWER historical climate for that calendar month
        - Quaternary Fallback: Regional baseline
        Ensures clear data source indicators and proper field mapping.
        """
        cache_key = f"live_{round(lat, 3)}_{round(lon, 3)}"
        now_ts = time.time()
        
        # Check memory cache for live forecast (30 mins TTL)
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if now_ts - entry['timestamp'] < Config.WEATHER_CACHE_TTL_SECONDS:
                return entry['data']

        source = "Unknown"
        is_live = False
        weather_payload = None

        # 1. Try Tomorrow.io
        t_realtime = self._fetch_tomorrow_realtime(lat, lon)
        t_forecast = self._fetch_tomorrow_forecast(lat, lon)
        
        if t_realtime and t_forecast:
            source = "Tomorrow.io (Live API)"
            is_live = True
            weather_payload = {
                'temperature (°C)': t_realtime['temperature'],
                'humidity (%)': t_realtime['humidity'],
                'rainfall (mm)': t_forecast['total_rainfall'],
                'wind_speed (km/h)': t_realtime['wind_speed'],
                'precipitation_prob (%)': t_realtime['precipitation_probability'],
                'condition': self._map_tomorrow_weather_code(t_realtime.get('weather_code', 1000)),
                'forecast_daily': t_forecast['forecast_days'],
                'source': source,
                'is_live': is_live,
                'is_fallback': False
            }

        # 2. Try Open-Meteo if Tomorrow.io not available
        if not weather_payload:
            om_data = self._fetch_open_meteo_forecast(lat, lon)
            if om_data:
                source = "Open-Meteo (Live NWP Forecast)"
                is_live = True
                weather_payload = {
                    'temperature (°C)': om_data['current']['temperature'],
                    'humidity (%)': om_data['current']['humidity'],
                    'rainfall (mm)': om_data['total_rainfall'],
                    'wind_speed (km/h)': om_data['current']['wind_speed'],
                    'precipitation_prob (%)': om_data['current']['precipitation_probability'],
                    'condition': 'Partly Cloudy' if om_data['total_rainfall'] < 10 else 'Rain Showers',
                    'forecast_daily': om_data['forecast_days'],
                    'source': source,
                    'is_live': is_live,
                    'is_fallback': False
                }

        # 3. Fallback to NASA POWER historical climate for the start_date month
        if not weather_payload:
            start_month = datetime.strptime(start_date, "%Y-%m-%d").month if start_date else datetime.now().month
            nasa_hist = self.get_nasa_historical_climate(lat, lon, start_date)
            month_stats = next((m for m in nasa_hist['monthly_climate'] if m['month_num'] == start_month), None)
            
            if month_stats:
                source = "NASA POWER (Historical Climate Average)"
                weather_payload = {
                    'temperature (°C)': month_stats['avg_temperature_c'],
                    'humidity (%)': month_stats['avg_humidity_pct'],
                    'rainfall (mm)': month_stats['avg_accumulated_rainfall_mm'],
                    'wind_speed (km/h)': 12.0,
                    'precipitation_prob (%)': 35.0,
                    'condition': 'Historical Seasonal Climate Pattern',
                    'forecast_daily': [],
                    'source': source,
                    'is_live': False,
                    'is_fallback': True
                }

        # 4. Final safety fallback
        if not weather_payload:
            weather_payload = Config.FALLBACK_WEATHER.copy()

        # Add timestamps and metadata
        weather_payload['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        weather_payload['season'] = self.get_season(start_date)

        # Cache in memory
        self.memory_cache[cache_key] = {
            'timestamp': now_ts,
            'data': weather_payload
        }
        return weather_payload

    def get_season(self, date_str: str) -> str:
        """Identify agricultural season in Tamil Nadu based on date"""
        try:
            month = datetime.strptime(date_str, "%Y-%m-%d").month
        except Exception:
            month = datetime.now().month

        if month in [1, 2]:
            return "Winter (Navarai / நவரை)"
        elif month in [3, 4, 5]:
            return "Summer (Chithirai / கோடை)"
        elif month in [6, 7, 8, 9]:
            return "Southwest Monsoon (Kuruvai / குறுவை)"
        else:
            return "Northeast Monsoon (Samba / Thaladi / சம்பா)"

    def _map_tomorrow_weather_code(self, code: int) -> str:
        """Map Tomorrow.io weather codes to readable descriptions"""
        mapping = {
            1000: "Clear / Sunny",
            1100: "Mostly Clear",
            1101: "Partly Cloudy",
            1102: "Mostly Cloudy",
            1001: "Cloudy",
            2000: "Fog",
            4000: "Drizzle",
            4001: "Rain",
            4200: "Light Rain",
            4201: "Heavy Rain",
            8000: "Thunderstorm"
        }
        return mapping.get(code, "Clear Sky")
