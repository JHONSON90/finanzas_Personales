import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from services.auth_service import get_current_user
from services.data_service import (
    load_gastos,
    load_presupuestos,
    load_seguimiento_productos,
    safe_parse_dates
)
from services.budget_service import (
    filter_gastos_by_user,
    filter_productos_by_user,
    compute_annual_summary,
    compute_annual_rankings,
    compute_monthly_evolution,
    MESES_NOMBRE
)

st.set_page_config(
    page_title="Seguimiento Anual | Finanzas",
    page_icon="📈",
    layout="wide"
)

current_user = get_current_user()

# --- CARGA DE DATOS CENTRALIZADA ---
df_gastos_raw = load_gastos()
df_presupuestos = load_presupuestos()
df_prod_raw = load_seguimiento_productos()

# Filtrar con regla estricta de privacidad: Casa (ambos) + Personal (solo usuario activo)
df_gastos = filter_gastos_by_user(df_gastos_raw, current_user)
df_prod = filter_productos_by_user(df_prod_raw, df_presupuestos, current_user)

if not df_gastos.empty:
    if "FECHA_DT" not in df_gastos.columns:
        df_gastos["FECHA_DT"] = safe_parse_dates(df_gastos["FECHA"])
    df_gastos["ANIO"] = df_gastos["FECHA_DT"].dt.year
    df_gastos["MES_NUM"] = df_gastos["FECHA_DT"].dt.month
    anios_gastos = df_gastos["ANIO"].dropna().astype(int).unique().tolist()
else:
    anios_gastos = []

if not df_prod.empty:
    if "FECHA_DT" not in df_prod.columns:
        df_prod["FECHA_DT"] = safe_parse_dates(df_prod["FECHA"])
    df_prod["ANIO"] = df_prod["FECHA_DT"].dt.year
    anios_prod = df_prod["ANIO"].dropna().astype(int).unique().tolist()
else:
    anios_prod = []

anios_todos = sorted(list(set([a for a in (anios_gastos + anios_prod) if a > 2000])), reverse=True)
if not anios_todos:
    anios_todos = [datetime.now().year]

# --- HEADER Y FILTRO PRINCIPAL ---
st.title("📅 Seguimiento Global Anual de Gastos")
st.caption(
    f"Usuario: **{current_user}** | Análisis consolidado de metas presupuestales anualizadas "
    f"(**Meta Mensual × 12**) vs. gasto real acumulado y rankings anuales de compra."
)

f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 2])
with f_col1:
    sel_anio = st.selectbox("📅 Seleccionar Año", options=anios_todos, index=0)
with f_col2:
    sel_tipo = st.selectbox("🏠 Tipo de Gasto", options=["Todos", "Casa", "Personal"], index=0)
with f_col3:
    top_n = st.slider("🏆 Cantidad en Rankings (Top N)", min_value=5, max_value=25, value=10, step=5)

st.markdown("---")

# --- CÁLCULO DE RESUMEN ANUAL ---
summary_anual, metrics = compute_annual_summary(
    df_gastos,
    df_presupuestos,
    current_user,
    selected_year=sel_anio,
    tipo_filtro=sel_tipo
)

# --- KPIS PRINCIPALES ANUALES ---
presup_anual = metrics["presupuesto_anual"]
real_anual = metrics["real_anual"]
variacion = metrics["variacion"]
pct_ejecucion = metrics["pct_ejecucion"]

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    f"🎯 Presupuesto Anual ({sel_anio})",
    f"${presup_anual:,.0f}",
    help="Presupuesto Mensual Base multiplicado por 12 meses.",
    border=True
)

k2.metric(
    f"💰 Gasto Real Anual ({sel_anio})",
    f"${real_anual:,.0f}",
    help=f"Gasto real acumulado en todo el año {sel_anio} ({metrics['total_registros']} registros).",
    border=True
)

# Variación: Real - Presupuesto (Si gastó menos, es ahorro y número negativo)
if variacion <= 0:
    lbl_var = f"🟢 Margen de ahorro: -${abs(variacion):,.0f}"
    delta_col_var = "normal"
else:
    lbl_var = f"🔴 Exceso anual: +${abs(variacion):,.0f}"
    delta_col_var = "inverse"

k3.metric(
    "⚖️ Variación vs Meta",
    f"${variacion:+,.0f}",
    delta=lbl_var,
    delta_color=delta_col_var,
    help="Diferencia entre Gasto Real Anual y Presupuesto Anual.",
    border=True
)

if pct_ejecucion <= 80.0:
    lbl_pct = "🟢 En rango (<80%)"
    delta_col_pct = "normal"
elif pct_ejecucion <= 100.0:
    lbl_pct = "🟡 Cerca al límite (80-100%)"
    delta_col_pct = "off"
else:
    lbl_pct = "🔴 Meta excedida (>100%)"
    delta_col_pct = "inverse"

k4.metric(
    "📈 % Ejecución Global Anual",
    f"{pct_ejecucion:.1f}%" if presup_anual > 0 else "N/A",
    delta=lbl_pct,
    delta_color=delta_col_pct,
    border=True
)

st.markdown("---")

# --- SECCIONES DETALLADAS EN TABS ---
tab_rubros, tab_meses, tab_rankings = st.tabs([
    f"📊 Presupuesto vs Real por Rubro ({sel_anio})",
    f"📈 Evolución Mensual ({sel_anio})",
    f"🏆 Rankings Top {top_n}: Productos y Proveedores ({sel_anio})"
])

# ---------------------------------------------------------------------------------
# TAB 1: PRESUPUESTO VS REAL POR RUBRO
# ---------------------------------------------------------------------------------
with tab_rubros:
    st.subheader(f"🎯 Control Presupuestal Anualizado por Rubro ({sel_anio})")
    st.caption("Comparación de la meta anualizada (Presupuesto Mensual × 12) vs el gasto real consolidado.")

    if summary_anual.empty or presup_anual == 0:
        st.info(f"No se encontraron datos ni metas de presupuesto para el año {sel_anio}.")
    else:
        # Gráfico comparativo de barras
        fig_rubros = go.Figure()
        fig_rubros.add_trace(go.Bar(
            x=summary_anual["RUBRO"],
            y=summary_anual["MONTO_PRESUPUESTO"],
            name="Presupuesto Anual (x12)",
            marker_color="#94A3B8"
        ))
        fig_rubros.add_trace(go.Bar(
            x=summary_anual["RUBRO"],
            y=summary_anual["GASTO_REAL"],
            name="Gasto Real Anual",
            marker_color=summary_anual["COLOR"]
        ))
        fig_rubros.update_layout(
            barmode="group",
            height=340,
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=20, b=80),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(title="Monto ($)")
        )
        st.plotly_chart(fig_rubros, use_container_width=True)

        # Tabla interactiva detallada
        df_view = summary_anual.copy()
        df_view["PROGRESO_RATIO"] = (df_view["PORCENTAJE_EJECUCION"] / 100.0).clip(lower=0.0)

        st.dataframe(
            df_view[["RUBRO", "COMPORTAMIENTO", "TIPO", "MONTO_PRESUPUESTO", "GASTO_REAL", "VARIACION", "PROGRESO_RATIO", "ESTADO"]],
            width="stretch",
            height=300,
            column_config={
                "RUBRO": st.column_config.TextColumn("Rubro Presupuestal", width="medium"),
                "COMPORTAMIENTO": st.column_config.TextColumn("Naturaleza", width="small"),
                "TIPO": st.column_config.TextColumn("Tipo", width="small"),
                "MONTO_PRESUPUESTO": st.column_config.NumberColumn("Presupuesto Anual ($)", format="$%d"),
                "GASTO_REAL": st.column_config.NumberColumn("Real Anual ($)", format="$%d"),
                "VARIACION": st.column_config.NumberColumn("Variación ($)", format="$%d"),
                "PROGRESO_RATIO": st.column_config.ProgressColumn(
                    "% Ejecución",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.0f%%"
                ),
                "ESTADO": st.column_config.TextColumn("Diagnóstico", width="medium")
            }
        )

# ---------------------------------------------------------------------------------
# TAB 2: EVOLUCIÓN MENSUAL DEL AÑO
# ---------------------------------------------------------------------------------
with tab_meses:
    st.subheader(f"📈 Comportamiento Mensual en el Año {sel_anio}")
    st.caption("Gasto real ejecutado mes a mes a lo largo del año frente a la cuota presupuestal mensual media.")

    df_mensual = compute_monthly_evolution(
        df_gastos,
        df_presupuestos,
        current_user,
        selected_year=int(sel_anio)
    )

    if not df_mensual.empty:
        fig_meses = px.bar(
            df_mensual,
            x="MES",
            y="GASTO_REAL",
            text_auto="$,.0f",
            labels={"GASTO_REAL": "Gasto Real ($)", "MES": "Mes"},
            color_discrete_sequence=["#3B82F6"]
        )

        meta_ref_mensual = df_mensual["PRESUPUESTO"].iloc[0] if not df_mensual.empty else (presup_anual / 12.0)
        if meta_ref_mensual > 0:
            fig_meses.add_hline(
                y=meta_ref_mensual,
                line_dash="dash",
                line_color="#EF4444",
                annotation_text=f"Meta Mensual Media: ${meta_ref_mensual:,.0f}",
                annotation_position="top right"
            )

        fig_meses.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=30, b=30),
            yaxis=dict(title="Gasto Real ($)")
        )
        st.plotly_chart(fig_meses, use_container_width=True)
    else:
        st.info(f"Sin registros de gastos mensuales para el año {sel_anio}.")

# ---------------------------------------------------------------------------------
# TAB 3: RANKINGS TOP N PRODUCTOS Y PROVEEDORES
# ---------------------------------------------------------------------------------
with tab_rankings:
    st.subheader(f"🏆 Rankings de Compras en {sel_anio} (Top {top_n})")
    st.caption("Productos con mayor impacto en el bolsillo y comercios donde más se concentró la facturación.")

    top_prods, top_provs = compute_annual_rankings(df_prod, selected_year=int(sel_anio), top_n=top_n)

    r_col1, r_col2 = st.columns(2)

    with r_col1:
        st.markdown(f"##### 🛒 Top {top_n} Productos Más Costosos")
        if not top_prods.empty:
            fig_prod = px.bar(
                top_prods.sort_values(by="VALOR TOTAL", ascending=True),
                x="VALOR TOTAL",
                y="PRODUCTO",
                orientation="h",
                text_auto="$,.0f",
                labels={"VALOR TOTAL": "Gasto Total ($)", "PRODUCTO": "Producto"},
                color_discrete_sequence=["#8B5CF6"]
            )
            fig_prod.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=10, b=30),
                xaxis=dict(title="Gasto Total Acumulado ($)"),
                yaxis=dict(title="")
            )
            st.plotly_chart(fig_prod, use_container_width=True)

            st.dataframe(
                top_prods,
                width="stretch",
                height=220,
                column_config={
                    "PRODUCTO": st.column_config.TextColumn("Producto"),
                    "VALOR TOTAL": st.column_config.NumberColumn("Gasto Total ($)", format="$%d"),
                    "CANTIDAD": st.column_config.NumberColumn("Unidades Compradas", format="%d"),
                    "PRECIO_PROM": st.column_config.NumberColumn("Precio Promedio ($)", format="$%d")
                }
            )
        else:
            st.info(f"No hay compras detalladas de productos registradas en el año {sel_anio}.")

    with r_col2:
        st.markdown(f"##### 🏭 Top {top_n} Proveedores por Facturación")
        if not top_provs.empty:
            fig_prov = px.bar(
                top_provs.sort_values(by="VALOR TOTAL", ascending=True),
                x="VALOR TOTAL",
                y="PROVEEDOR",
                orientation="h",
                text_auto="$,.0f",
                labels={"VALOR TOTAL": "Gasto Facturado ($)", "PROVEEDOR": "Proveedor / Tienda"},
                color_discrete_sequence=["#10B981"]
            )
            fig_prov.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=10, b=30),
                xaxis=dict(title="Facturación Total ($)"),
                yaxis=dict(title="")
            )
            st.plotly_chart(fig_prov, use_container_width=True)

            st.dataframe(
                top_provs,
                width="stretch",
                height=220,
                column_config={
                    "PROVEEDOR": st.column_config.TextColumn("Proveedor / Tienda"),
                    "VALOR TOTAL": st.column_config.NumberColumn("Total Facturado ($)", format="$%d"),
                    "NUM_COMPRAS": st.column_config.NumberColumn("Ítems Adquiridos", format="%d")
                }
            )
        else:
            st.info(f"No hay registros de compras por proveedor en el año {sel_anio}.")
