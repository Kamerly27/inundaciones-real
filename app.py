import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os
import io

# CONFIG
st.set_page_config(page_title="Sistema IDEAM - Inundaciones", layout="wide")

archivo = "historial_clima.csv"

# ESTILO
st.markdown("""
<style>
.stApp {
    background-color: #f4f6f7;
}

.main-box {
    background-color: white;
    padding: 25px;
    border-radius: 10px;
}

h1 { color: #1b5e20 !important; text-align:center; }
h2, h3 { color: #2e7d32 !important; }
label, p, div { color: black !important; }

[data-testid="stMetricValue"] {
    color: #1b5e20 !important;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-box">', unsafe_allow_html=True)

# TITULO
st.title("🌊 Sistema de Monitoreo de Inundaciones")
st.markdown("### 📊 Estilo IDEAM - Córdoba")

# INPUT
municipios_input = st.text_input("Municipios (separados por coma)", "Sahagun, Monteria")

municipios = [m.strip() for m in municipios_input.split(",")]

datos_guardar = []
map_data = []

for municipio in municipios:
    try:
        geo = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={municipio}&count=1&country=co"
        ).json()

        if "results" not in geo:
            continue

        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]

        map_data.append({"lat": lat, "lon": lon})

        weather = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=relative_humidity_2m,precipitation"
        ).json()

        current = weather.get("current_weather", {})
        temp = current.get("temperature", 0)

        hourly = weather.get("hourly", {})
        lluvia = hourly.get("precipitation", [0])[0]
        humedad = hourly.get("relative_humidity_2m", [0])[0]

        # GUARDAR
        datos_guardar.append({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "municipio": municipio,
            "temperatura": temp,
            "lluvia": lluvia,
            "humedad": humedad
        })

        # MOSTRAR
        st.markdown(f"---")
        st.markdown(f"## 📍 {municipio.upper()}")

        col1, col2, col3 = st.columns(3)
        col1.metric("🌧️ Lluvia", f"{lluvia} mm")
        col2.metric("💧 Humedad", f"{humedad}%")
        col3.metric("🌡️ Temp", f"{temp} °C")

        # ALERTA
        if lluvia > 20:
            st.error("🔴 Alto riesgo")
        elif lluvia > 5:
            st.warning("🟡 Riesgo moderado")
        else:
            st.success("🟢 Sin riesgo")

    except:
        st.error(f"Error en {municipio}")

# GUARDAR CSV
if datos_guardar:
    df_nuevo = pd.DataFrame(datos_guardar)

    if os.path.exists(archivo):
        df_nuevo.to_csv(archivo, mode='a', header=False, index=False)
    else:
        df_nuevo.to_csv(archivo, index=False)

# HISTÓRICO
st.markdown("---")
st.markdown("## 📊 Histórico de datos")

if os.path.exists(archivo):
    df_hist = pd.read_csv(archivo)

    st.dataframe(df_hist)

    municipio_sel = st.selectbox("Selecciona municipio", df_hist["municipio"].unique())

    df_filtrado = df_hist[df_hist["municipio"] == municipio_sel]

    st.line_chart(df_filtrado[["lluvia", "humedad"]])

    # ✅ DESCARGA EXCEL CORREGIDA (SIN ERROR EN LA NUBE)
    buffer = io.BytesIO()
    df_hist.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    st.download_button(
        label="📥 Descargar reporte en Excel",
        data=buffer,
        file_name="reporte_inundaciones.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# MAPA
if map_data:
    st.markdown("### 🗺️ Mapa")
    st.map(pd.DataFrame(map_data))

st.markdown('</div>', unsafe_allow_html=True)