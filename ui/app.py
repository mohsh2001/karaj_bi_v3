import streamlit as st
import pandas as pd
import joblib
model = joblib.load("../models/lgbm_car_price.pkl")
opts = joblib.load("../models/feature_options.pkl")
cat_cols      = opts["cat_cols"]
feature_order = opts["feature_order"]
categories    = opts["categorical"]
bmt           = opts["brand_model_trim"]
bmb           = opts["brand_model_body"]
MAE = 1800
st.set_page_config(page_title="Karaj Bi — Car Price Predictor", page_icon="🚗", layout="centered")
st.markdown("""
<style>
.stApp { background-color: #062E2E; color: #E6F2F2; }
section[data-testid="stSidebar"] { background-color: #0A3A3A; }
/* Hide Streamlit's top header bar */
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { background: transparent !important; }
#MainMenu { visibility: hidden; }
h1, h2, h3, h4 { color: #E6F2F2 !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #6E8585 !important; }
p, label, .stMarkdown { color: #A8C0C0; }
/* Inputs */
.stSelectbox div[data-baseweb="select"] > div,
.stNumberInput input,
.stTextInput input {
   background-color: #0A3A3A !important;
   border: 1px solid #1F4D4D !important;
   color: #E6F2F2 !important;
}
.stSelectbox label, .stNumberInput label { color: #7FB8B8 !important; font-size: 0.85rem; }
/* Button — override primary styling */
.stButton > button,
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
   background-color: #5EE3E3 !important;
   color: #062E2E !important;
   border: none !important;
   font-weight: 600 !important;
}
.stButton > button p {
   color: #062E2E !important;
   font-weight: 600 !important;
}
.stButton > button:hover {
   background-color: #7FB8B8 !important;
   color: #062E2E !important;
}
.stButton > button:hover p { color: #062E2E !important; }
/* Alert boxes */
div[data-testid="stAlert"] {
   background-color: #0A3A3A !important;
   border: 1px solid #1F4D4D !important;
   border-radius: 6px;
}
/* Tag pill for title */
.tag-pill {
   display: inline-block;
   padding: 4px 10px;
   background: rgba(94, 227, 227, 0.08);
   border: 1px solid #5EE3E3;
   border-radius: 999px;
   color: #5EE3E3;
   font-size: 0.7rem;
   letter-spacing: 0.1em;
   margin-bottom: 0.5rem;
}
/* Result cards */
.result-card {
   background: #0A3A3A;
   border: 1px solid #1F4D4D;
   border-radius: 8px;
   padding: 1rem 1.25rem;
   margin-top: 0.75rem;
}
.result-label { color: #7FB8B8; font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; }
.result-value { color: #5EE3E3; font-size: 1.75rem; font-weight: 600; margin-top: 4px; }
.result-range { color: #E6F2F2; font-size: 1.1rem; margin-top: 4px; }
.result-note { color: #6E8585; font-size: 0.75rem; margin-top: 8px; }
</style>
""", unsafe_allow_html=True)
st.markdown('<span class="tag-pill">USED CAR PRICING</span>', unsafe_allow_html=True)
st.title("Karaj Bi — Used Car Price Predictor")
st.caption("Enter the car details and get an estimated market price (JOD).")
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
if st.button("Predict price", type="primary"):
   row = {
       "brand": brand, "model": model_in, "trim": trim, "year": year,
       "body_type": body_type, "mileage": mileage, "engine_size_cc": engine_size_cc,
       "fuel": fuel, "condition": condition, "body_condition": body_condition,
       "paint": paint, "exterior_color": exterior_color, "interior_color": interior_color,
       "city": city,
   }
   X_new = pd.DataFrame([row])[feature_order]
   for col in cat_cols:
       X_new[col] = pd.Categorical(X_new[col], categories=categories[col])
   pred = model.predict(X_new)[0]
   low = max(0, pred - MAE)
   st.markdown(f"""
<div class="result-card">
<div class="result-label">Estimated Price</div>
<div class="result-value">{pred:,.0f} JOD</div>
<div class="result-range">Range: {low:,.0f} – {pred:,.0f} JOD</div>
<div class="result-note">Range = estimate − typical error (MAE ≈ 1,800 JOD) up to estimate.</div>
</div>
   """, unsafe_allow_html=True)