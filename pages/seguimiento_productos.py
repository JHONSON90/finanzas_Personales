import streamlit as st
import time
from streamlit_gsheets import GSheetsConnection
import traceback
import pandas as pd
from plotly import express as px
import plotly.graph_objects as go


st.title("🛒 Seguimiento a productos donde se compra mas barato!!!!")

conn  = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(worksheet="Seguimiento_Productos", ttl=0)
    placeholder = st.empty()
    placeholder.success("Conexión exitosa!")
    time.sleep(2)
    placeholder.empty()
except Exception as e:
    placeholder = st.empty()
    placeholder.error(f"Error al conectar con Google Sheets: {str(e)}")
    placeholder.error(f"Traceback: {traceback.format_exc()}")
    placeholder.empty()

filtro1, filtro2 = st.columns(2)
with filtro1:
    st.multiselect("Producto", options=df["PRODUCTO"].unique(), key="producto")
with filtro2:
    st.multiselect("Proveedor", options=df["PROVEEDOR"].unique(), key="proveedor")


if st.session_state.producto:
    df = df[df["PRODUCTO"].isin(st.session_state.producto)]

if st.session_state.proveedor:
    df = df[df["PROVEEDOR"].isin(st.session_state.proveedor)]

st.write(df)

st.subheader("Compra a proveedores")
col1, col2 = st.columns(2)
with col1:
    grafico1 = df.groupby("PROVEEDOR")["VALOR TOTAL"].sum().reset_index()
    fig = px.pie(grafico1, names="PROVEEDOR", values="VALOR TOTAL")
    st.plotly_chart(fig)
with col2:
    st.write(grafico1)
