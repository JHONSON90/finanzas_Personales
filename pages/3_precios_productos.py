import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from services.auth_service import get_current_user
from services.data_service import load_seguimiento_productos

st.set_page_config(
    page_title="Precios y Productos | Finanzas",
    page_icon="🛒",
    layout="wide"
)

current_user = get_current_user()

st.title("🛒 Comparador Inteligente de Precios y Productos")
st.caption("Identifica dónde comprar más barato, monitorea variaciones de precio y analiza el gasto por proveedor.")

df_prod = load_seguimiento_productos()

if df_prod.empty:
    st.info("No hay registros de seguimiento a productos todavía. Puedes registrarlos desde el Dashboard.")
else:
    df_prod["FECHA"] = pd.to_datetime(df_prod["FECHA"], errors="coerce")
    if "RUBRO" not in df_prod.columns:
        df_prod["RUBRO"] = "Otros"

    # --- FILTROS ---
    st.subheader("🔍 Filtros")
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        prods_list = sorted(list(df_prod["PRODUCTO"].dropna().unique()))
        sel_prods = st.multiselect("Filtrar por Producto", options=prods_list)
    with f_col2:
        provs_list = sorted(list(df_prod["PROVEEDOR"].dropna().unique()))
        sel_provs = st.multiselect("Filtrar por Proveedor / Tienda", options=provs_list)
    with f_col3:
        rubros_list = sorted(list(df_prod["RUBRO"].dropna().unique()))
        sel_rubros = st.multiselect("Filtrar por Rubro", options=rubros_list)

    df_filtered = df_prod.copy()
    if sel_prods:
        df_filtered = df_filtered[df_filtered["PRODUCTO"].isin(sel_prods)]
    if sel_provs:
        df_filtered = df_filtered[df_filtered["PROVEEDOR"].isin(sel_provs)]
    if sel_rubros:
        df_filtered = df_filtered[df_filtered["RUBRO"].isin(sel_rubros)]

    # --- COMPARADOR DE PRECIO MÁS BARATO ---
    st.markdown("---")
    st.subheader("🏆 ¿Dónde comprar más barato cada producto?")
    
    # Calcular precio mínimo y proveedor por producto
    df_analisis = df_filtered.groupby(["PRODUCTO", "PROVEEDOR"])["VALOR UNT"].agg(["min", "mean", "max", "count"]).reset_index()
    df_analisis.columns = ["PRODUCTO", "PROVEEDOR", "PRECIO_MIN", "PRECIO_PROM", "PRECIO_MAX", "NUM_COMPRAS"]

    # Encontrar mejor opción por producto
    idx_min = df_analisis.groupby("PRODUCTO")["PRECIO_MIN"].idxmin()
    mejores_precios = df_analisis.loc[idx_min].sort_values(by="PRODUCTO")

    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.markdown("##### 💡 Proveedor Recomendado por Menor Precio:")
        st.dataframe(
            mejores_precios[["PRODUCTO", "PROVEEDOR", "PRECIO_MIN", "PRECIO_PROM", "NUM_COMPRAS"]],
            width="stretch",
            column_config={
                "PRECIO_MIN": st.column_config.NumberColumn("Mejor Precio ($)", format="$%.2f"),
                "PRECIO_PROM": st.column_config.NumberColumn("Precio Promedio ($)", format="$%.2f"),
                "NUM_COMPRAS": st.column_config.NumberColumn("Veces Comprado")
            }
        )
    with c2:
        st.markdown("##### 📊 Gasto Total por Proveedor:")
        gasto_prov = df_filtered.groupby("PROVEEDOR")["VALOR TOTAL"].sum().reset_index()
        fig_prov = px.pie(
            gasto_prov,
            names="PROVEEDOR",
            values="VALOR TOTAL",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_prov.update_traces(textposition='inside', textinfo='percent+label')
        fig_prov.update_layout(margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_prov, use_container_width=True)

    # --- HISTORIAL DETALLADO ---
    st.markdown("---")
    st.subheader("📋 Historial Completo de Precios por Producto")
    cols_prod = ["FECHA", "PRODUCTO", "PROVEEDOR", "RUBRO", "CANTIDAD", "VALOR UNT", "VALOR TOTAL"]
    df_show = df_filtered[[c for c in cols_prod if c in df_filtered.columns]].copy()
    if "FECHA" in df_show.columns:
        df_show["FECHA"] = df_show["FECHA"].dt.strftime("%Y-%m-%d")
    
    st.dataframe(
        df_show.sort_values(by="FECHA", ascending=False),
        width="stretch",
        column_config={
            "VALOR UNT": st.column_config.NumberColumn("Precio Unitario ($)", format="$%.2f"),
            "VALOR TOTAL": st.column_config.NumberColumn("Total ($)", format="$%.2f")
        }
    )
