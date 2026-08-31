import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime

from services.auth_service import get_current_user
from services.data_service import (
    load_gastos,
    load_presupuestos,
    load_seguimiento_productos,
    add_single_gasto,
    add_compra_con_productos,
    safe_parse_dates
)
from services.budget_service import (
    filter_gastos_by_user,
    get_available_rubros,
    compute_budget_summary,
    compute_monthly_evolution,
    MESES_NOMBRE
)

st.set_page_config(
    page_title="Dashboard y Gastos | Finanzas",
    page_icon="📊",
    layout="wide"
)

# 1. Identificar usuario activo automáticamente por defecto
current_user = get_current_user()

# 2. Cargar datos centralizados
df_gastos_raw = load_gastos()
df_presupuestos = load_presupuestos()

# Filtrar gastos con regla de privacidad: Casa (ambos) + Personal (solo el usuario activo)
df_gastos = filter_gastos_by_user(df_gastos_raw, current_user)

if "FECHA_DT" not in df_gastos.columns:
    df_gastos["FECHA_DT"] = safe_parse_dates(df_gastos["FECHA"])

df_gastos["MES_NUM"] = df_gastos["FECHA_DT"].dt.month

CATEGORIAS_DEFAULT = [
    "Alimentos", "Alimentacion (Snacks)", "Arriendo", "Aseo", "Casa",
    "Compras", "Educación", "Entretenimiento", "Salud", "Servicios", "Transporte", "Otros"
]

# --- DIALOGS PARA REGISTRO ---

@st.dialog("🛒 Registrar Nuevo Gasto", width="large")
def modal_agregar_gasto():
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("🗓️ Fecha de la Compra")
        pago_realizado = st.radio(
            "👤 ¿Quién pagó?",
            ["Edison", "Diana"],
            index=0 if current_user == "Edison" else 1
        )
    with col2:
        tipo = st.radio("🏠 Tipo de Gasto", ["Casa", "Personal"])
        concepto = st.text_input("📜 Concepto / Detalle", placeholder="Ej. Pago servicios")

    rubros_disponibles = get_available_rubros(df_presupuestos, tipo, current_user)
    
    col3, col4 = st.columns(2)
    with col3:
        clasificacion = st.selectbox("🏷️ Categoría / Clasificación", CATEGORIAS_DEFAULT)
        rubro = st.selectbox("🎯 Rubro Presupuestal", rubros_disponibles)
    with col4:
        monto = st.number_input("💰 Monto ($)", min_value=0.0, step=1000.0, format="%.2f")
        pago_tc = st.toggle("💳 ¿Pago con Tarjeta de Crédito?", value=False)
        mes_pago = st.selectbox(
            "📅 Mes de Pago (TC)",
            [""] + MESES_NOMBRE,
            disabled=not pago_tc
        )

    st.markdown("---")
    if st.button("💾 Guardar Gasto", type="primary", width="stretch"):
        if monto <= 0:
            st.error("El monto debe ser mayor a 0.")
            return
        if not concepto.strip():
            concepto = f"Gasto en {rubro}"

        fecha_str = fecha.strftime("%Y-%m-%d")
        new_gasto = {
            "FECHA": fecha_str,
            "QUIEN PAGA": pago_realizado,
            "TIPO": tipo,
            "CONCEPTO": concepto.strip(),
            "CLASIFICACION": clasificacion,
            "RUBRO": rubro,
            "VALOR": float(monto),
            "PAGO": pago_tc,
            "Mes_Pago": mes_pago if pago_tc else ""
        }

        with st.spinner("Guardando en Google Sheets..."):
            if add_single_gasto(new_gasto):
                st.success("✅ ¡Gasto registrado exitosamente!")
                time.sleep(1.2)
                st.rerun()

def inicializar_productos_df(rubros_list):
    return pd.DataFrame({
        "PRODUCTO": pd.Series(dtype="str"),
        "CANTIDAD": pd.Series(dtype="int"),
        "VALOR UNT": pd.Series(dtype="float"),
        "VALOR TOTAL": pd.Series(dtype="float"),
        "RUBRO": pd.Series(dtype="str")
    })

@st.dialog("🛒 Registro Detallado de Compra y Productos", width="large")
def modal_seguimiento_productos():
    col1, col2, col3 = st.columns(3)
    with col1:
        fecha = st.date_input("🗓️ Fecha de Compra")
    with col2:
        pago_realizado = st.radio(
            "👤 ¿Quién pagó?",
            ["Edison", "Diana"],
            index=0 if current_user == "Edison" else 1
        )
    with col3:
        tipo = st.radio("🏠 Tipo de Gasto", ["Casa", "Personal"])

    col4, col5 = st.columns(2)
    with col4:
        clasificacion = st.selectbox("🏷️ Categoría General", CATEGORIAS_DEFAULT)
        rubros_disponibles = get_available_rubros(df_presupuestos, tipo, current_user)
        rubro_principal = st.selectbox("🎯 Rubro Principal", rubros_disponibles)
    with col5:
        proveedor = st.text_input("🏭 Proveedor / Tienda", placeholder="Ej. Éxito, D1, Olímpica")
        pago_tc = st.toggle("💳 ¿Pago con Tarjeta de Crédito?", value=False)
        mes_pago = st.selectbox("📅 Mes de Pago TC", [""] + MESES_NOMBRE, disabled=not pago_tc)

    st.markdown("---")
    st.subheader("📝 Lista de Productos Comprados")
    df_base = inicializar_productos_df(rubros_disponibles)
    
    productos_ingresados = st.data_editor(
        df_base,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "PRODUCTO": st.column_config.TextColumn("Producto", width="medium", required=True),
            "CANTIDAD": st.column_config.NumberColumn("Cantidad", min_value=1, default=1, required=True),
            "VALOR UNT": st.column_config.NumberColumn("Valor Unitario ($)", min_value=0.0, format="%.2f", required=True),
            "VALOR TOTAL": st.column_config.NumberColumn("Valor Total ($)", format="%.2f", disabled=True),
            "RUBRO": st.column_config.SelectboxColumn(
                "Rubro",
                options=rubros_disponibles,
                required=True,
                default=rubro_principal,
                width="medium"
            )
        }
    )

    productos_ingresados["CANTIDAD"] = pd.to_numeric(productos_ingresados["CANTIDAD"], errors='coerce').fillna(0)
    productos_ingresados["VALOR UNT"] = pd.to_numeric(productos_ingresados["VALOR UNT"], errors='coerce').fillna(0)
    productos_ingresados["VALOR TOTAL"] = productos_ingresados["CANTIDAD"] * productos_ingresados["VALOR UNT"]
    
    productos_validos = productos_ingresados.dropna(subset=['PRODUCTO']).copy()
    productos_validos = productos_validos[productos_validos["PRODUCTO"].astype(str).str.strip() != ""]
    fecha_str = fecha.strftime("%Y-%m-%d")
    productos_validos["FECHA"] = fecha_str
    productos_validos["PROVEEDOR"] = proveedor.strip() if proveedor.strip() else "Varios"
    productos_validos["RUBRO"] = productos_validos["RUBRO"].fillna(rubro_principal)

    valor_total_compra = productos_validos["VALOR TOTAL"].sum()
    st.metric("Total de la Compra", f"${valor_total_compra:,.2f}", border=True)

    st.markdown("---")
    if st.button("💾 Guardar Compra Completa", type="primary", width="stretch"):
        if valor_total_compra <= 0 or productos_validos.empty:
            st.error("Debes ingresar al menos un producto con precio y cantidad válidos.")
            return

        new_gasto = {
            "FECHA": fecha_str,
            "QUIEN PAGA": pago_realizado,
            "TIPO": tipo,
            "CONCEPTO": f"Compra {proveedor} ({len(productos_validos)} productos)".strip(),
            "CLASIFICACION": clasificacion,
            "RUBRO": rubro_principal,
            "VALOR": float(valor_total_compra),
            "PAGO": pago_tc,
            "Mes_Pago": mes_pago if pago_tc else ""
        }

        with st.spinner("Guardando en Google Sheets..."):
            if add_compra_con_productos(productos_validos, new_gasto):
                st.success("✅ ¡Compra y productos guardados con éxito!")
                time.sleep(1.2)
                st.rerun()


# --- HEADER Y BOTONES DE REGISTRO ---
st.title("📊 Dashboard de Control Financiero y Gastos")
st.caption(f"Usuario: **{current_user}** | Visualizando gastos de **Casa** y gastos **Personales de {current_user}**.")

btn_col1, btn_col2, _ = st.columns([1, 1.2, 2])
with btn_col1:
    if st.button("➕ Registrar Gasto", type="primary", width="stretch"):
        modal_agregar_gasto()
with btn_col2:
    if st.button("🛒 Registrar Compra Detallada", width="stretch"):
        modal_seguimiento_productos()

st.markdown("---")

# --- FILTROS GLOBALES ---
st.subheader("🔍 Filtros de Visualización")
f_col1, f_col2, f_col3, f_col4 = st.columns(4)

with f_col1:
    opciones_tipo = ["Todos"] + sorted(list(df_gastos["TIPO"].dropna().unique()))
    sel_tipo = st.selectbox("Tipo de Gasto", opciones_tipo)

with f_col2:
    opciones_paga = ["Todos"] + sorted(list(df_gastos["QUIEN PAGA"].dropna().unique()))
    sel_paga = st.selectbox("Quién Pagó", opciones_paga)

with f_col3:
    meses_disponibles = sorted([int(m) for m in df_gastos["MES_NUM"].dropna().unique() if 1 <= m <= 12])
    meses_labels = {m: MESES_NOMBRE[m-1] for m in meses_disponibles}
    sel_meses = st.multiselect("Filtrar por Mes", options=meses_disponibles, format_func=lambda x: meses_labels.get(x, str(x)))

with f_col4:
    rubros_unicos = sorted(list(df_gastos["RUBRO"].dropna().unique()))
    sel_rubros = st.multiselect("Filtrar por Rubro", options=rubros_unicos)

# Aplicar filtros
df_filtered = df_gastos.copy()
if sel_tipo != "Todos":
    df_filtered = df_filtered[df_filtered["TIPO"] == sel_tipo]
if sel_paga != "Todos":
    df_filtered = df_filtered[df_filtered["QUIEN PAGA"] == sel_paga]
if sel_meses:
    df_filtered = df_filtered[df_filtered["MES_NUM"].isin(sel_meses)]
if sel_rubros:
    df_filtered = df_filtered[df_filtered["RUBRO"].isin(sel_rubros)]

# --- KPIS PRINCIPALES ---
summary_budget = compute_budget_summary(df_filtered, df_presupuestos, current_user)

total_gastado = df_filtered["VALOR"].sum() if not df_filtered.empty else 0.0
total_presupuestado = summary_budget["MONTO_PRESUPUESTO"].sum()
pct_global = (total_gastado / total_presupuestado * 100.0) if total_presupuestado > 0 else 0.0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("💰 Total Gastos", f"${total_gastado:,.0f}", border=True)
kpi2.metric("🎯 Presupuesto Total", f"${total_presupuestado:,.0f}", border=True)

delta_color = "normal" if pct_global <= 80 else ("off" if pct_global <= 100 else "inverse")
kpi3.metric(
    "📈 % Ejecución",
    f"{pct_global:.1f}%",
    delta=f"{'🟢 En meta' if pct_global <= 80 else ('🟡 Cerca al límite' if pct_global <= 100 else '🔴 Excedido')}",
    delta_color=delta_color,
    border=True
)

if not df_filtered.empty and "RUBRO" in df_filtered.columns and len(df_filtered.dropna(subset=["RUBRO"])) > 0:
    top_rubro_df = df_filtered.groupby("RUBRO")["VALOR"].sum().reset_index().sort_values(by="VALOR", ascending=False)
    if not top_rubro_df.empty:
        top_rubro_row = top_rubro_df.iloc[0]
        kpi4.metric("🔥 Rubro Mayor Gasto", f"{top_rubro_row['RUBRO']}", f"${top_rubro_row['VALOR']:,.0f}", border=True)
    else:
        kpi4.metric("🔥 Rubro Mayor Gasto", "N/A", border=True)
else:
    kpi4.metric("🔥 Rubro Mayor Gasto", "N/A", border=True)

st.markdown("---")

# --- 1. GRÁFICO HISTÓRICO: PRESUPUESTADO VS GASTADO MENSUAL ---
st.subheader("📈 Comparativo Mensual: Presupuesto vs Gasto Real")
df_mensual = compute_monthly_evolution(df_gastos, df_presupuestos, current_user)

fig_mensual = go.Figure()
fig_mensual.add_trace(go.Bar(
    x=df_mensual["MES"],
    y=df_mensual["PRESUPUESTO"],
    name="Meta Presupuesto",
    marker_color="#94A3B8",
    opacity=0.75
))
fig_mensual.add_trace(go.Bar(
    x=df_mensual["MES"],
    y=df_mensual["GASTO_REAL"],
    name="Gasto Real",
    text=df_mensual["GASTO_REAL"].apply(lambda v: f"${v/1e6:.1f}M" if v >= 1e6 else f"${v:,.0f}"),
    textposition="outside",
    marker_color="#3B82F6"
))
fig_mensual.update_layout(
    barmode="group",
    height=320,
    margin=dict(l=10, r=10, t=20, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis=dict(title="Monto ($)")
)
st.plotly_chart(fig_mensual, width="stretch")

st.markdown("---")

# --- 2. SEMÁFORO COMPACTO DE PRESUPUESTO (REINICIADO POR MES/FILTRO) ---
st.subheader("🎯 Semáforo de Presupuestos vs Gasto Real")
st.caption("Monitoreo de metas presupuestales con cálculo de ejecución adaptado al período consultado.")

if summary_budget.empty:
    st.info("No hay metas de presupuesto configuradas.")
else:
    df_semaforo = summary_budget.copy()
    df_semaforo["PROGRESO_RATIO"] = df_semaforo["PORCENTAJE_EJECUCION"] / 100.0
    
    n_meta = len(df_semaforo[df_semaforo["PORCENTAJE_EJECUCION"] < 80])
    n_alerta = len(df_semaforo[(df_semaforo["PORCENTAJE_EJECUCION"] >= 80) & (df_semaforo["PORCENTAJE_EJECUCION"] <= 100)])
    n_exceso = len(df_semaforo[df_semaforo["PORCENTAJE_EJECUCION"] > 100])

    m_c1, m_c2, m_c3 = st.columns(3)
    m_c1.caption(f"🟢 **En Rango (<80%):** {n_meta} rubros")
    m_c2.caption(f"🟡 **En Alerta (80-100%):** {n_alerta} rubros")
    m_c3.caption(f"🔴 **Excedidos (>100%):** {n_exceso} rubros")

    # Tabla compacta estilizada que no ocupa espacio excesivo a lo alto
    st.dataframe(
        df_semaforo[["RUBRO", "TIPO", "GASTO_REAL", "MONTO_PRESUPUESTO", "PROGRESO_RATIO", "ESTADO"]],
        width="stretch",
        height=230,
        column_config={
            "RUBRO": st.column_config.TextColumn("Rubro", width="medium"),
            "TIPO": st.column_config.TextColumn("Tipo", width="small"),
            "GASTO_REAL": st.column_config.NumberColumn("Gastado ($)", format="$%d"),
            "MONTO_PRESUPUESTO": st.column_config.NumberColumn("Presupuesto ($)", format="$%d"),
            "PROGRESO_RATIO": st.column_config.ProgressColumn(
                "% Ejecutado",
                min_value=0.0,
                max_value=1.0,
                format="%.0f%%"
            ),
            "ESTADO": st.column_config.TextColumn("Estado", width="medium")
        }
    )

st.markdown("---")

# --- 3. GRÁFICOS ANALÍTICOS ---
st.subheader("📊 Análisis Detallado de Gastos")
g_col1, g_col2 = st.columns(2)

with g_col1:
    st.markdown("##### 🎯 Comparativo por Rubro (Selección Actual)")
    if not summary_budget.empty:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=summary_budget["RUBRO"],
            y=summary_budget["MONTO_PRESUPUESTO"],
            name="Presupuesto",
            marker_color="#94A3B8"
        ))
        fig_bar.add_trace(go.Bar(
            x=summary_budget["RUBRO"],
            y=summary_budget["GASTO_REAL"],
            name="Gasto Real",
            marker_color=summary_budget["COLOR"]
        ))
        fig_bar.update_layout(
            barmode="group",
            height=300,
            xaxis_tickangle=-45,
            margin=dict(l=10, r=10, t=20, b=80),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, width="stretch")
    else:
        st.info("Sin datos para graficar.")

with g_col2:
    st.markdown("##### 🏷️ Distribución por Clasificación / Categoría")
    if not df_filtered.empty and "CLASIFICACION" in df_filtered.columns:
        df_clasif = df_filtered.groupby("CLASIFICACION")["VALOR"].sum().reset_index()
        fig_pie = px.pie(
            df_clasif,
            names="CLASIFICACION",
            values="VALOR",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_pie, width="stretch")
    else:
        st.info("Sin datos para graficar.")

g_col3, g_col4 = st.columns(2)
with g_col3:
    st.markdown("##### 👤 Gastos por Persona Responsable")
    if not df_filtered.empty and "QUIEN PAGA" in df_filtered.columns:
        df_payer = df_filtered.groupby("QUIEN PAGA")["VALOR"].sum().reset_index()
        fig_payer = px.bar(
            df_payer,
            x="QUIEN PAGA",
            y="VALOR",
            color="QUIEN PAGA",
            text_auto="$,.0f",
            color_discrete_map={"Edison": "#3B82F6", "Diana": "#EC4899"}
        )
        fig_payer.update_layout(height=280, showlegend=False, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_payer, width="stretch")

with g_col4:
    st.markdown("##### 💳 Compromisos Tarjetas de Crédito por Mes")
    if not df_filtered.empty and "Mes_Pago" in df_filtered.columns:
        df_tc = df_filtered[df_filtered["PAGO"] == True]
        if not df_tc.empty:
            df_tc_mes = df_tc.groupby("Mes_Pago")["VALOR"].sum().reset_index()
            fig_tc = px.bar(
                df_tc_mes,
                x="Mes_Pago",
                y="VALOR",
                text_auto="$,.0f",
                color_discrete_sequence=["#F97316"]
            )
            fig_tc.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=20))
            st.plotly_chart(fig_tc, width="stretch")
        else:
            st.info("No hay pagos con tarjeta de crédito registrados en la selección.")

# --- TABLA DETALLADA ---
st.markdown("---")
st.subheader("📋 Registro Detallado de Gastos")
if not df_filtered.empty:
    cols_mostrar = ["FECHA", "QUIEN PAGA", "TIPO", "CONCEPTO", "CLASIFICACION", "RUBRO", "VALOR", "PAGO", "Mes_Pago"]
    df_display = df_filtered[[c for c in cols_mostrar if c in df_filtered.columns]].copy()
    if "FECHA_DT" in df_filtered.columns:
        df_display["_sort_dt"] = df_filtered["FECHA_DT"]
        df_display = df_display.sort_values(by="_sort_dt", ascending=False).drop(columns=["_sort_dt"])
    
    st.dataframe(
        df_display,
        width="stretch",
        column_config={
            "FECHA": st.column_config.TextColumn("Fecha"),
            "VALOR": st.column_config.NumberColumn("Valor ($)", format="$%d"),
            "PAGO": st.column_config.CheckboxColumn("Tarjeta Crédito")
        }
    )
else:
    st.info("No hay gastos para mostrar con los filtros seleccionados.")
