import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import numpy as np
import os
import io

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="IDEAM PRO MAX", layout="wide")

# =========================
# 🎨 ESTILO (MAR + MORADO LEGIBLE)
# =========================
st.markdown("""
<style>

/* Fondo mar */
[data-testid="stAppViewContainer"] {
    background: url("https://images.unsplash.com/photo-1500375592092-40eb2168fd21");
    background-size: cover;
    background-position: center;
}

/* capa clara */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: absolute;
    inset: 0;
    background: rgba(255,255,255,0.85);
    z-index: 0;
}

/* contenido arriba */
.main, .block-container {
    position: relative;
    z-index: 1;
}

/* 💜 TEXTO MORADO LEGIBLE */
html, body, p, span, label, div {
    color: #4b0082 !important;
}

/* títulos */
h1 {
    color: #4b0082 !important;
    text-align: center;
    font-weight: 900;
}

h2, h3 {
    color: #6a0dad !important;
}

/* botones */
.stButton > button {
    background-color: #6a0dad;
    color: white;
    border-radius: 10px;
    border: none;
}

.stButton > button:hover {
    background-color: #4b0082;
}

/* métricas */
[data-testid="stMetricValue"] {
    color: #4b0082 !important;
    font-size: 22px;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# =========================
# TITULO
# =========================
st.title("🏛️ IDEAM PRO MAX - Sistema de Riesgo Hidrometeorológico")

# =========================
# INPUT
# =========================
municipios_input = st.text_input("Municipios (separados por coma)", "Monteria, Sahagun, Lorica")
municipios = [m.strip() for m in municipios_input.split(",") if m.strip()]

btn = st.button("🔍 Analizar")

# =========================
# API SEGURA
# =========================
def get_json(url):
    try:
        return requests.get(url, timeout=6).json()
    except:
        return None

# =========================
# ALERTA SIMULADA
# =========================
def alerta(m, estado):
    return f"📲 ALERTA ({m}): {estado}"

# =========================
# DATOS
# =========================
datos = []

for m in municipios:

    geo = get_json(f"https://geocoding-api.open-meteo.com/v1/search?name={m}&count=1&country=co")

    if not geo or "results" not in geo:
        continue

    lat = geo["results"][0]["latitude"]
    lon = geo["results"][0]["longitude"]

    weather = get_json(
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current_weather=true"
        f"&hourly=relative_humidity_2m,precipitation"
    )

    temp = weather.get("current_weather", {}).get("temperature", 27) if weather else 27

    lluvia = 0
    humedad = 70

    if weather:
        try:
            lluvia = weather["hourly"]["precipitation"][0]
            humedad = weather["hourly"]["relative_humidity_2m"][0]
        except:
            pass

    # =========================
    # IA SIMPLE DE RIESGO
    # =========================
    riesgo = (lluvia * 2) + (humedad * 0.3)

    if riesgo > 60:
        estado = "🔴 ALTO RIESGO - POSIBLE INUNDACIÓN"
        nivel = "red"
    elif riesgo > 30:
        estado = "🟡 RIESGO MODERADO"
        nivel = "yellow"
    else:
        estado = "🟢 CONDICIONES NORMALES"
        nivel = "green"

    datos.append({
        "municipio": m,
        "lat": lat,
        "lon": lon,
        "temperatura": temp,
        "lluvia": lluvia,
        "humedad": humedad,
        "riesgo": riesgo,
        "estado": estado,
        "nivel": nivel,
        "alerta": alerta(m, estado)
    })

# =========================
# EJECUCIÓN
# =========================
if btn and datos:

    st.subheader("🚨 Alertas")

    for d in datos:
        st.write(d["alerta"])

    # =========================
    # SEMÁFORO
    # =========================
    if any(d["nivel"] == "red" for d in datos):
        st.error("🔴 ALERTA ROJA")
    elif any(d["nivel"] == "yellow" for d in datos):
        st.warning("🟡 ALERTA AMARILLA")
    else:
        st.success("🟢 NORMAL")

    # =========================
    # MAPA
    # =========================
    st.subheader("🌍 Mapa Colombia")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=datos,
        get_position='[lon, lat]',
        get_color='[255 if nivel=="red" else 255 if nivel=="yellow" else 0, 0 if nivel=="green" else 165, 0]',
        get_radius=90000,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=4.5709,
            longitude=-74.2973,
            zoom=5
        )
    ))

    # =========================
    # DETALLE
    # =========================
    st.subheader("📊 Detalle")

    for d in datos:
        st.markdown(f"""
        ### 📍 {d['municipio']}
        🌡️ Temperatura: **{d['temperatura']} °C**  
        🌧️ Lluvia: **{d['lluvia']} mm**  
        💧 Humedad: **{d['humedad']} %**  
        📊 Riesgo: **{d['riesgo']:.2f}**  
        🚨 Estado: **{d['estado']}**
        ---
        """)

# =========================
# HISTORICO (SIN ERRORES)
# =========================
archivo = "historial.csv"

if datos and btn:

    df = pd.DataFrame(datos)

    if os.path.exists(archivo):
        df.to_csv(archivo, mode="a", header=False, index=False)
    else:
        df.to_csv(archivo, index=False)

st.subheader("📈 Histórico")

if os.path.exists(archivo):

    dfh = pd.read_csv(archivo, on_bad_lines="skip")

    # evitar errores de columnas viejas
    if "lluvia" not in dfh.columns:
        dfh["lluvia"] = 0
    if "humedad" not in dfh.columns:
        dfh["humedad"] = 0
    if "riesgo" not in dfh.columns:
        dfh["riesgo"] = (dfh["lluvia"] * 2) + (dfh["humedad"] * 0.3)

    st.dataframe(dfh)

    st.line_chart(dfh[["lluvia", "humedad", "riesgo"]])

    buffer = io.BytesIO()
    dfh.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "📥 Descargar Excel",
        buffer,
        file_name="ideam_pro.xlsx"
    )