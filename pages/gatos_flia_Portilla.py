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

@st.dialog("🛒 Agregar Gasto")
def agregar_gasto():
    Fecha = st.date_input("🗓️ Fecha de la Compra")
    Pago_realizado = st.radio("👤 ¿Quién pagó?", ["Edison", "Diana"])
    Tipo = st.radio("🏠 Tipo de Gasto", ["Casa", "Personal"])
    Concepto = st.text_input("📜 Concepto")
    Categoría = st.selectbox("🏷️ Categoría", ["Alimentos", "Alimentacion (Snacks)", "Arriendo", "Aseo", "Casa",  "Compras", "Educación", "Entretenimiento","Salud", "Servicios", "Transporte", "Otros"])
    Monto = st.number_input("💰 Monto", min_value=0.0, format="%.2f")
    Pago = st.toggle("🔄 ¿Hay que devolver el dinero?", value=False)
    
    if st.button("Agregar Gasto"):
        df = conn.read(worksheet="Gastos", ttl=0)
        new_row = pd.DataFrame({
            "FECHA": [Fecha],
            "QUIEN PAGA": [Pago_realizado],
            "TIPO": [Tipo],
            "CONCEPTO": [Concepto],
            "CLASIFICACION": [Categoría],
            "VALOR": [Monto],
            "PAGO": [Pago]
        })
        df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Gastos", data=df)
        st.success("Gasto agregado exitosamente!!")
        time.sleep(2)
        st.rerun()
        
def inicializar_productos_df():
    return pd.DataFrame({
        "PRODUCTO": pd.Series(dtype="str"),
        "CANTIDAD": pd.Series(dtype="int"),
        "VALOR UNT": pd.Series(dtype="float"),
        "VALOR TOTAL": pd.Series(dtype="float")
    })


@st.dialog("🛒 Seguimiento Detallado de Productos", width="medium")
def seguimiento_productos():
    col1, col2, col3 = st.columns(3)
    with col1:
        Fecha = st.date_input("🗓️ Fecha de la Compra")
    with col2:
        Pago_realizado = st.radio("👤 ¿Quién pagó?", ["Edison", "Diana"])
    with col3:
        Tipo = st.radio("🏠 Tipo de Gasto", ["Casa", "Personal"])
    col4, col5 = st.columns(2)
    with col4:
        Categoría = st.selectbox("🏷️ Categoría de Gasto", ["Alimentos", "Alimentacion (Snacks)", "Arriendo", "Aseo", "Casa",  "Compras", "Educación", "Entretenimiento","Salud", "Servicios", "Transporte", "Otros"])
    with col5:
        Proveedor = st.text_input("🏭 Proveedor")
        Pago = st.toggle("🔄 ¿Hay que devolver el dinero?", value=False)
    st.markdown("---")
    st.subheader("📝 Detalle de Productos (Llene la tabla a continuación)")
    df_productos_base = inicializar_productos_df()
    productos_ingresados = st.data_editor(
        df_productos_base,
        num_rows="dynamic",
        use_container_width="stretch",
        column_config={
            "PRODUCTO": st.column_config.TextColumn("PRODUCTO", width="large", required=True),
            "CANTIDAD": st.column_config.NumberColumn("CANTIDAD", required=True),
            "VALOR UNT": st.column_config.NumberColumn("VALOR UNT", required=True),
            "VALOR TOTAL": st.column_config.NumberColumn("VALOR TOTAL", format="%.2f")
        }
    )

    productos_ingresados["CANTIDAD"] = pd.to_numeric(productos_ingresados["CANTIDAD"], errors='coerce').fillna(0)
    productos_ingresados["VALOR UNT"] = pd.to_numeric(productos_ingresados["VALOR UNT"], errors='coerce').fillna(0)
    productos_ingresados["VALOR TOTAL"] = productos_ingresados["CANTIDAD"] * productos_ingresados["VALOR UNT"]
    productos_validos = productos_ingresados.dropna(subset=['PRODUCTO'])
    productos_validos["FECHA"] = Fecha
    productos_validos["PROVEEDOR"] = Proveedor
    valor_total_compra = productos_validos["VALOR TOTAL"].sum()


    st.metric("Total de la Compra", f"${valor_total_compra:,.2f}", border=True)
    
    st.markdown("---")

    
    if st.button("💾 Agregar Compra y Productos"):
        if valor_total_compra == 0:
            st.error("Debe ingresar al menos un producto con un valor mayor a 0")
            return
        with st.spinner("Guardando..."):
            df2 = conn.read(worksheet="Seguimiento_Productos", ttl=0)
            df2 = pd.concat([df2, productos_validos], ignore_index=True)
            conn.update(worksheet="Seguimiento_Productos", data=df2)

            df = conn.read(worksheet="Gastos", ttl=0)
            new_row2 = pd.DataFrame({
                "FECHA": [Fecha],
                "QUIEN PAGA": [Pago_realizado],
                "TIPO": [Tipo],
                "CONCEPTO": ["Compras con Seguimiento"],
                "CLASIFICACION": [Categoría],
                "VALOR": [valor_total_compra],
                "PAGO": [Pago],
            })
            df = pd.concat([df, new_row2], ignore_index=True)
            conn.update(worksheet="Gastos", data=df)
            st.success("Producto agregado exitosamente!!")
            time.sleep(2)
            st.rerun()

col1, col2 = st.columns(2)
with col1:
    if st.button("Agregar Gasto"):
        agregar_gasto()
with col2:
    if st.button("Seguimiento a productos"):
        seguimiento_productos()

df = df[~((df['TIPO'] == 'Personal') & (df['QUIEN PAGA'] == 'Edison'))]

df["FECHA"] = pd.to_datetime(df["FECHA"], format="%Y-%m-%d")
df["MES"] = df["FECHA"].dt.month

grafico1, grafico2 = st.columns(2)
with grafico1:
    grafico_total = df.groupby(["FECHA", "QUIEN PAGA"])["VALOR"].sum().reset_index()
    fig = px.line(grafico_total, x="FECHA", y="VALOR", color="QUIEN PAGA")
    st.plotly_chart(fig)
with grafico2:
    grafico_total2 = df.groupby("QUIEN PAGA")["VALOR"].sum().reset_index()
    fig2 = px.pie(grafico_total2, names="QUIEN PAGA", values="VALOR")
    st.plotly_chart(fig2)

filtro1, filtro2, filtro3 = st.columns(3, vertical_alignment="center")
with filtro1:
    st.multiselect("Filtrar por Quien Paga", options=df["QUIEN PAGA"].unique(), key="quien_paga")

with filtro2:
    st.multiselect("Filtrar por Mes", options=df["MES"].unique(), key="meses")

with filtro3:
    st.multiselect("Filtrar por Tipo", options=df["TIPO"].unique(), key="tipos")

if st.session_state.quien_paga:
    df = df[df["QUIEN PAGA"].isin(st.session_state.quien_paga)]

if st.session_state.meses:
    df = df[df["MES"].isin(st.session_state.meses)]

if st.session_state.tipos:
    df = df[df["TIPO"].isin(st.session_state.tipos)]

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

st.write(df.groupby(["CLASIFICACION", "CONCEPTO"])["VALOR"].sum().reset_index().sort_values(by="VALOR", ascending=False))


#todo: agregar funcionalidade para analizar el comportamiento de productos y mirar cuanto se debe devolver y mirar si se puede hacer una tabla para devolver y cambiar el estado de pago



