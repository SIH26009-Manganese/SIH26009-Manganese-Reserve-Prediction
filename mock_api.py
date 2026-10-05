import os
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from statsmodels.tsa.arima.model import ARIMA
import warnings
import random
import joblib

warnings.filterwarnings("ignore")

app = FastAPI(
    title="SIH 26009 - Manganese Intelligence API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------- Data Loading & Forecasting ---------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "Sheet 2-DATA OF MANGANESE ORE (2014-24).csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "sih_manganese_model.pkl")

forecast_cache = None
deposits_cache = None
grid_cache = None
ml_model = None

def load_ibm_data(file_path):
    df = pd.read_csv(file_path)
    df['year'] = df['YEAR'].str.split('-').str[0].astype(int)
    df = df[['year', 'Production_kt', 'Consumption_kt']].sort_values('year')
    return df

def train_forecast_model(df, horizon=6):
    df_idx = df.set_index('year').sort_index()
    prod = df_idx['Production_kt']
    cons = df_idx['Consumption_kt']

    prod_model = ARIMA(prod, order=(1,1,1)).fit()
    cons_model = ARIMA(cons, order=(1,1,1)).fit()

    forecast_prod = prod_model.forecast(steps=horizon)
    forecast_cons = cons_model.forecast(steps=horizon)

    years = list(range(2024, 2031))
    prod_vals = [prod.loc[2024]] + list(forecast_prod)
    cons_vals = [cons.loc[2024]] + list(forecast_cons)

    # Production scaled by 0.65 (as per ML lead)
    prod_mt = [round((v / 1000) * 0.65, 2) for v in prod_vals]
    cons_mt = [round(v / 1000, 2) for v in cons_vals]

    yearly_forecast = []
    for y, p, d in zip(years, prod_mt, cons_mt):
        yearly_forecast.append({
            "year": y,
            "domestic_production_mt": p,
            "total_demand_mt": d
        })
    return yearly_forecast

def generate_dummy_deposits():
    names = ["Bharweli Mine", "Malanjkhand", "Tirodi Mine", "Gumgaon Mine", "Kandri Mine",
             "Sitasaongi Mine", "Beldongri", "Dongri Buzurg", "Ukwa Mine", "Balaghat East",
             "Ramrama", "Chandak", "Ghorawari", "Padampur", "Chandrapur"]
    grades = ["High", "Medium", "Low"]
    statuses = ["Active Mine", "Exploring", "Closed", "Reserve"]
    lat_base = 21.8
    lon_base = 80.18
    deposits = []
    for i in range(129):
        lat = lat_base + random.uniform(-0.3, 0.3)
        lon = lon_base + random.uniform(-0.3, 0.3)
        name = random.choice(names) + f" {i+1}" if i >= len(names) else names[i]
        deposits.append({
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "name": name,
            "grade": random.choice(grades),
            "status": random.choice(statuses)
        })
    return deposits

def generate_dummy_grid():
    grid = []
    lat_base = 21.8
    lon_base = 80.18
    for _ in range(100):
        lat = lat_base + random.uniform(-0.3, 0.3)
        lon = lon_base + random.uniform(-0.3, 0.3)
        score = round(random.uniform(0.1, 0.95), 3)
        grid.append({
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "score": score
        })
    return grid

# --------------------- Startup ---------------------
@app.on_event("startup")
def startup_event():
    global forecast_cache, deposits_cache, grid_cache, ml_model

    try:
        df = load_ibm_data(DATA_PATH)
        forecast_cache = train_forecast_model(df, horizon=6)
        print("Forecast model trained successfully.")
    except Exception as e:
        print(f"Error loading forecast data: {e}")
        forecast_cache = [
            {"year": 2024, "domestic_production_mt": 2.20, "total_demand_mt": 8.97},
            {"year": 2025, "domestic_production_mt": 2.24, "total_demand_mt": 9.51},
            {"year": 2026, "domestic_production_mt": 2.28, "total_demand_mt": 10.08},
            {"year": 2027, "domestic_production_mt": 2.31, "total_demand_mt": 10.69},
            {"year": 2028, "domestic_production_mt": 2.34, "total_demand_mt": 11.33},
            {"year": 2029, "domestic_production_mt": 2.36, "total_demand_mt": 12.01},
            {"year": 2030, "domestic_production_mt": 2.37, "total_demand_mt": 12.73},
        ]

    deposits_cache = generate_dummy_deposits()
    grid_cache = generate_dummy_grid()
    print("Dummy spatial data generated.")

    try:
        if os.path.exists(MODEL_PATH):
            ml_model = joblib.load(MODEL_PATH)
            print("ML model loaded successfully from", MODEL_PATH)
        else:
            alt_path = os.path.join(os.path.dirname(__file__), "..", "sih_manganese_model.pkl")
            if os.path.exists(alt_path):
                ml_model = joblib.load(alt_path)
                print("ML model loaded successfully from", alt_path)
            else:
                print("WARNING: Model file not found. Predictions will use dummy logic.")
    except Exception as e:
        print(f"WARNING: Could not load ML model: {e}")

# --------------------- Pydantic Models ---------------------
class PointInferenceRequest(BaseModel):
    latitude: float
    longitude: float
    band_8: float
    band_11: float
    band_12: float

# --------------------- Endpoints ---------------------

@app.get("/api/v1/health")
async def health_check():
    return {"status": "online", "pipeline": "SIH-26009"}

@app.get("/api/v1/forecast/summary")
async def get_forecast_summary():
    if forecast_cache is None:
        raise HTTPException(status_code=503, detail="Forecast not ready")
    return {"yearly_forecast": forecast_cache}

@app.get("/api/v1/spatial/deposits")
async def get_deposits():
    if deposits_cache is None:
        raise HTTPException(status_code=503, detail="Deposits not ready")
    return deposits_cache

@app.get("/api/v1/spatial/grid-predictions")
async def get_grid_predictions():
    if grid_cache is None:
        raise HTTPException(status_code=503, detail="Grid not ready")
    return grid_cache

@app.post("/api/v1/spatial/predict-point")
async def predict_point(payload: PointInferenceRequest):
    try:
        # ---- FIXES APPLIED HERE ----
        EPSILON = 0.0001   # matching training epsilon

        # 1. Ratios as before (both with correct epsilon)
        ratio_11_8 = payload.band_11 / (payload.band_8 + EPSILON)
        ratio_11_12 = payload.band_11 / (payload.band_12 + EPSILON)

        # 2. Normalized Difference: (Band 11 - Band 8) / (Band 11 + Band 8 + epsilon)
        norm_diff = (payload.band_11 - payload.band_8) / (payload.band_11 + payload.band_8 + EPSILON)

        # 3. Build feature vector (6 features)
        features = [[
            payload.band_8,
            payload.band_11,
            payload.band_12,
            ratio_11_8,
            ratio_11_12,
            norm_diff
        ]]

        # 4. Run inference
        if ml_model is not None:
            proba = ml_model.predict_proba(features)
            score = float(proba[0][1])   # class 1 probability
        else:
            # Fallback dummy (for testing)
            score = 0.5 + 0.3 * (payload.band_8 / 3000) + 0.2 * (payload.band_11 / 4000) - 0.1 * (payload.band_12 / 4000)
            score = min(max(score, 0.0), 1.0)

        score_pct = round(score * 100, 1)

        # 5. Confidence & recommendation
        if score_pct >= 75:
            confidence = "High"
            risk_level = "Low"
            recommendation = "Targeted drilling recommended."
        elif score_pct >= 50:
            confidence = "Medium"
            risk_level = "Moderate"
            recommendation = "Conduct geochemical survey."
        else:
            confidence = "Low"
            risk_level = "High"
            recommendation = "Low priority, further study needed."

        return {
            "prospectivity_score": score_pct,
            "confidence": confidence,
            "risk_level": risk_level,
            "recommendation": recommendation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
