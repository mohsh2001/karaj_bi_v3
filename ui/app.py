import streamlit as st
import pandas as pd
import joblib
# ---- Load model + feature metadata ----
model = joblib.load("../models/lgbm_car_price.pkl")
opts = joblib.load("../models/feature_options.pkl")
cat_cols      = opts["cat_cols"]
feature_order = opts["feature_order"]
categories    = opts["categorical"]
bmt           = opts["brand_model_trim"]
bmb           = opts["brand_model_body"]
MAE = 1800  # typical error in JOD
st.set_page_config(page_title="Karaj Bi — Car Price Predictor", page_icon="🚗")
st.title("Karaj Bi — Used Car Price Predictor")
st.caption("Enter the car details and get an estimated market price (JOD).")
# ---- Input form ----
col1, col2 = st.columns(2)
with col1:
   brand     = st.selectbox("Brand", sorted(bmt.keys()))
   model_in  = st.selectbox("Model", sorted(bmt[brand].keys()))
   trim      = st.selectbox("Trim", bmt[brand][model_in])
   body_type = st.selectbox("Body type", bmb[brand][model_in])
   fuel      = st.selectbox("Fuel", categories["fuel"])
   condition = st.selectbox("Condition", categories["condition"])
   city      = st.selectbox("City", categories["city"])
with col2:
   year            = st.number_input("Year", min_value=1970, max_value=2027, value=2018, step=1)
   mileage         = st.number_input("Mileage (km)", min_value=0, max_value=1_000_000, value=120_000, step=1000)
   engine_size_cc  = st.number_input("Engine size (cc)", min_value=0, max_value=8000, value=1600, step=100)
   body_condition  = st.selectbox("Body condition", categories["body_condition"])
   paint           = st.selectbox("Paint", categories["paint"])
   exterior_color  = st.selectbox("Exterior color", categories["exterior_color"])
   interior_color  = st.selectbox("Interior color", categories["interior_color"])
# ---- Predict ----
if st.button("Predict price", type="primary"):
   # Build a single-row dataframe in the exact training column order
   row = {
       "brand": brand, "model": model_in, "trim": trim, "year": year,
       "body_type": body_type, "mileage": mileage, "engine_size_cc": engine_size_cc,
       "fuel": fuel, "condition": condition, "body_condition": body_condition,
       "paint": paint, "exterior_color": exterior_color, "interior_color": interior_color,
       "city": city,
   }
   X_new = pd.DataFrame([row])[feature_order]
   # Cast categoricals with the SAME categories used in training
   for col in cat_cols:
       X_new[col] = pd.Categorical(X_new[col], categories=categories[col])
   pred = model.predict(X_new)[0]
   low = max(0, pred - MAE)
   st.success(f"Estimated price: **{pred:,.0f} JOD**")
   st.info(f"Expected range: **{low:,.0f} – {pred:,.0f} JOD**")
   st.caption("Range = estimate − typical error (MAE ≈ 1,800 JOD) up to estimate.")