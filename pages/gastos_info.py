import streamlit as st
import time
from streamlit_gsheets import GSheetsConnection
import traceback
import pandas as pd
from plotly import express as px
import plotly.graph_objects as go


st.title("Gastos Generales")

conn  = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(worksheet="Gastos", ttl=0)
    placeholder = st.empty()
    placeholder.success("Conexión exitosa!")
    time.sleep(2)
    placeholder.empty()
except Exception as e:
    placeholder = st.empty()
    placeholder.error(f"Error al conectar con Google Sheets: {str(e)}")
    placeholder.error(f"Traceback: {traceback.format_exc()}")
    placeholder.empty()

@st.dialog("Agregar Gasto")
def agregar_gasto():
    Fecha = st.date_input("Fecha")
    Pago_realizado = st.radio("Quien paga", ["Edison", "Diana"])
    Concepto = st.text_input("Concepto")
    Categoría = st.selectbox("Categoría", ["Alimentos", "Alimentacion (Snacks)", "Arriendo", "Casa",  "Compras", "Educación", "Entretenimiento","Salud", "Transporte", "Otros"])
    Monto = st.number_input("Monto", min_value=0.0, format="%.2f")

    
    if st.button("Agregar Gasto"):
        df = conn.read(worksheet="Gastos", ttl=0)
        new_row = pd.DataFrame({
            "FECHA": [Fecha],
            "QUIEN PAGA": [Pago_realizado],
            "CONCEPTO": [Concepto],
            "CLASIFICACION": [Categoría],
            "VALOR": [Monto]
        })
        df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Gastos", data=df)
        st.success("Gasto agregado exitosamente!!")
        time.sleep(2)
        st.rerun()

if st.button("Agregar Gasto"):
    agregar_gasto()

df["FECHA"] = pd.to_datetime(df["FECHA"], format="%Y-%m-%d")
df["MES"] = df["FECHA"].dt.month

grafico_total = df.groupby("FECHA")["VALOR"].sum().reset_index()
fig = px.line(grafico_total, x="FECHA", y="VALOR")
st.plotly_chart(fig)

filtro1, filtro2 = st.columns(2, vertical_alignment="center")
with filtro1:
    st.multiselect("Filtrar por Quien Paga", options=df["QUIEN PAGA"].unique(), key="quien_paga")

with filtro2:
    st.multiselect("Filtrar por Mes", options=df["MES"].unique(), key="meses")

if st.session_state.quien_paga:
    df = df[df["QUIEN PAGA"].isin(st.session_state.quien_paga)]

if st.session_state.meses:
    df = df[df["MES"].isin(st.session_state.meses)]

col1, col2 = st.columns(2)

with col1:
    grafico_1 = df.groupby("CLASIFICACION")["VALOR"].sum().reset_index()
    fig = px.pie(grafico_1, names="CLASIFICACION", values="VALOR")
    st.plotly_chart(fig)
with col2:
    st.write(grafico_1)


data1, data2, data3 =st.columns(3, vertical_alignment="center")

para_metrica3 = df.groupby("CLASIFICACION")["VALOR"].sum().reset_index().sort_values(by="VALOR", ascending=False).iloc[0]

data1.metric("Total Gastos", f"{df["VALOR"].sum():,.0f}",border=True)
data2.metric("Promedio Gastos", f"{df["VALOR"].mean():,.0f}",border=True)
data3.metric(f"Clasificación mas alta,  {para_metrica3["CLASIFICACION"]}", f"{para_metrica3["VALOR"]:,.0f}", border=True )

st.write(df.groupby("CONCEPTO")["VALOR"].sum().reset_index().sort_values(by="VALOR", ascending=False))






