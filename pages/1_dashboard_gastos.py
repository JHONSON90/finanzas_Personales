import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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
    get_unique_providers,
    add_single_gasto,
    add_compra_con_productos,
    safe_parse_dates
)
from services.budget_service import (
    filter_gastos_by_user,
    get_available_rubros,
    compute_budget_summary,
    compute_projection_summary,
    compute_trajectory_data,
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
df_gastos["ANIO"] = df_gastos["FECHA_DT"].dt.year

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
    if st.button("💾 Guardar Gasto", type="primary", width='stretch'):
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
        proveedores_disponibles = get_unique_providers()
        opciones_proveedor = proveedores_disponibles + ["➕ Agregar nuevo proveedor..."]
        idx_default = opciones_proveedor.index("D1") if "D1" in opciones_proveedor else 0
        proveedor_sel = st.selectbox("🏭 Proveedor / Tienda", opciones_proveedor, index=idx_default)

        if proveedor_sel == "➕ Agregar nuevo proveedor...":
            nuevo_proveedor = st.text_input("✍️ Nombre del Nuevo Proveedor", placeholder="Ej. Frutería El Vergel")
            proveedor_final = nuevo_proveedor.strip()
        else:
            proveedor_final = proveedor_sel

        pago_tc = st.toggle("💳 ¿Pago con Tarjeta de Crédito?", value=False)
        mes_pago = st.selectbox("📅 Mes de Pago TC", [""] + MESES_NOMBRE, disabled=not pago_tc)

    st.markdown("---")
    st.subheader("📝 Lista de Productos Comprados")
    df_base = inicializar_productos_df(rubros_disponibles)
    
    productos_ingresados = st.data_editor(
        df_base,
        num_rows="dynamic",
        width="stretch",
        key="editor_detalle_compra",
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
    productos_validos["PROVEEDOR"] = proveedor_final if proveedor_final else "Varios"
    productos_validos["RUBRO"] = productos_validos["RUBRO"].fillna(rubro_principal)

    valor_total_compra = productos_validos["VALOR TOTAL"].sum()
    st.metric("Total de la Compra", f"${valor_total_compra:,.2f}", border=True)

    st.markdown("---")
    if st.button("💾 Guardar Compra Completa", type="primary", width='stretch'):
        if not proveedor_final:
            st.error("Por favor ingresa o selecciona un proveedor válido.")
            return

        if valor_total_compra <= 0 or productos_validos.empty:
            st.error("Debes ingresar al menos un producto con precio y cantidad válidos.")
            return

        if proveedor_sel == "➕ Agregar nuevo proveedor..." and proveedor_final:
            if "custom_providers" not in st.session_state:
                st.session_state["custom_providers"] = []
            if proveedor_final not in st.session_state["custom_providers"]:
                st.session_state["custom_providers"].append(proveedor_final)

        new_gasto = {
            "FECHA": fecha_str,
            "QUIEN PAGA": pago_realizado,
            "TIPO": tipo,
            "CONCEPTO": f"Compra {proveedor_final} ({len(productos_validos)} productos)".strip(),
            "CLASIFICACION": clasificacion,
            "RUBRO": rubro_principal,
            "VALOR": float(valor_total_compra),
            "PAGO": pago_tc,
            "Mes_Pago": mes_pago if pago_tc else ""
        }

        with st.spinner("Guardando en Google Sheets..."):
            if add_compra_con_productos(productos_validos, new_gasto):
                if "editor_detalle_compra" in st.session_state:
                    del st.session_state["editor_detalle_compra"]
                st.success("✅ ¡Compra y productos guardados con éxito!")
                time.sleep(1.2)
                st.rerun()


# --- HEADER Y BOTONES DE REGISTRO ---
st.title("📊 Dashboard de Control Financiero y Gastos")
st.caption(f"Usuario: **{current_user}** | Visualizando gastos de **Casa** y gastos **Personales de {current_user}**.")

btn_col1, btn_col2, _ = st.columns([1, 1.2, 2])
with btn_col1:
    if st.button("➕ Registrar Gasto", type="primary", width='stretch'):
        modal_agregar_gasto()
with btn_col2:
    if st.button("🛒 Registrar Compra Detallada", width='stretch'):
        modal_seguimiento_productos()

st.markdown("---")

# --- FILTROS GLOBALES ---
st.subheader("🔍 Filtros de Visualización")
f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)

anios_raw = df_gastos["ANIO"].dropna().astype(int).unique() if "ANIO" in df_gastos.columns else []
anios_disponibles = sorted([int(a) for a in anios_raw if a > 2000], reverse=True)
if not anios_disponibles:
    anios_disponibles = [datetime.now().year]

with f_col1:
    sel_anio = st.selectbox("📅 Año", ["Todos"] + [str(a) for a in anios_disponibles], index=0)

with f_col2:
    meses_disponibles = sorted([int(m) for m in df_gastos["MES_NUM"].dropna().unique() if 1 <= m <= 12])
    meses_labels = {m: MESES_NOMBRE[m-1] for m in meses_disponibles}
    sel_meses = st.multiselect("🗓️ Filtrar por Mes", options=meses_disponibles, format_func=lambda x: meses_labels.get(x, str(x)))

with f_col3:
    opciones_tipo = ["Todos"] + sorted(list(df_gastos["TIPO"].dropna().unique()))
    sel_tipo = st.selectbox("🏠 Tipo de Gasto", opciones_tipo)

with f_col4:
    opciones_paga = ["Todos"] + sorted(list(df_gastos["QUIEN PAGA"].dropna().unique()))
    sel_paga = st.selectbox("👤 Quién Pagó", opciones_paga)

with f_col5:
    rubros_unicos = sorted(list(df_gastos["RUBRO"].dropna().unique()))
    sel_rubros = st.multiselect("🎯 Filtrar por Rubro", options=rubros_unicos)

# Aplicar filtros
df_filtered = df_gastos.copy()
if sel_anio != "Todos":
    df_filtered = df_filtered[df_filtered["ANIO"] == int(sel_anio)]
if sel_tipo != "Todos":
    df_filtered = df_filtered[df_filtered["TIPO"] == sel_tipo]
if sel_paga != "Todos":
    df_filtered = df_filtered[df_filtered["QUIEN PAGA"] == sel_paga]
if sel_meses:
    df_filtered = df_filtered[df_filtered["MES_NUM"].isin(sel_meses)]
if sel_rubros:
    df_filtered = df_filtered[df_filtered["RUBRO"].isin(sel_rubros)]

# --- CONTEXTO PREDICTIVO ---
now = datetime.now()
target_year_proj = int(sel_anio) if sel_anio != "Todos" else now.year

# Selección del mes a proyectar:
# 1. Si el usuario seleccionó exactamente un mes en los filtros, evaluar ese mes específico.
# 2. Si no seleccionó un mes y estamos en el año actual (o "Todos"), proyectar SIEMPRE el mes en curso (now.month).
# 3. Si seleccionó un año pasado cerrado, evaluar el último mes con actividad de dicho año.
if len(sel_meses) == 1:
    target_month_proj = sel_meses[0]
elif target_year_proj == now.year:
    target_month_proj = now.month
else:
    df_anio_gastos = df_gastos[df_gastos["ANIO"] == target_year_proj] if "ANIO" in df_gastos.columns else pd.DataFrame()
    if not df_anio_gastos.empty and "MES_NUM" in df_anio_gastos.columns:
        target_month_proj = int(df_anio_gastos["MES_NUM"].max())
    else:
        target_month_proj = 12

df_proj, proj_metrics = compute_projection_summary(
    df_gastos,
    df_presupuestos,
    current_user,
    selected_year=target_year_proj,
    selected_month=target_month_proj,
    tipo_filtro=sel_tipo,
    rubros_filtro=sel_rubros
)

# --- EVALUACIÓN DE CONTROL PRESUPUESTAL Y SEMÁFORO ---
# Si el usuario seleccionó meses específicos en el filtro (sel_meses), se evalúan dichos meses.
# Si NO seleccionó meses (sel_meses está vacío), se evalúa estrictamente el mes en curso/activo (target_month_proj y target_year_proj),
# evitando comparar el gasto acumulado de todo el año contra un único mes de presupuesto mensual.
if sel_meses:
    df_gastos_budget = df_filtered.copy()
    num_meses_budget = len(sel_meses)
    if num_meses_budget == 1:
        mes_nombre_budget = meses_labels.get(sel_meses[0], f"Mes {sel_meses[0]}")
        label_periodo_budget = f"{mes_nombre_budget} {target_year_proj}"
    else:
        label_periodo_budget = f"{num_meses_budget} meses seleccionados"
else:
    df_gastos_budget = df_gastos[
        (df_gastos["ANIO"] == target_year_proj) &
        (df_gastos["MES_NUM"] == target_month_proj)
    ].copy()
    if sel_tipo != "Todos":
        df_gastos_budget = df_gastos_budget[df_gastos_budget["TIPO"] == sel_tipo]
    if sel_paga != "Todos":
        df_gastos_budget = df_gastos_budget[df_gastos_budget["QUIEN PAGA"] == sel_paga]
    if sel_rubros:
        df_gastos_budget = df_gastos_budget[df_gastos_budget["RUBRO"].isin(sel_rubros)]
        
    num_meses_budget = 1
    mes_nombre_budget = MESES_NOMBRE[target_month_proj - 1]
    label_periodo_budget = f"{mes_nombre_budget} {target_year_proj}"

try:
    summary_budget = compute_budget_summary(
        df_gastos_budget,
        df_presupuestos,
        current_user,
        tipo_filtro=sel_tipo,
        rubros_filtro=sel_rubros,
        num_meses=num_meses_budget
    )
except TypeError:
    summary_budget = compute_budget_summary(
        df_gastos_budget,
        df_presupuestos,
        current_user
    )

total_gastado_budget = float(df_gastos_budget["VALOR"].sum()) if not df_gastos_budget.empty and "VALOR" in df_gastos_budget.columns else 0.0
total_presupuestado = float(summary_budget["MONTO_PRESUPUESTO"].sum()) if not summary_budget.empty and "MONTO_PRESUPUESTO" in summary_budget.columns else 0.0
pct_global = (total_gastado_budget / total_presupuestado * 100.0) if total_presupuestado > 0 else 0.0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric(f"💰 Gastado ({label_periodo_budget})", f"${total_gastado_budget:,.0f}", border=True)
kpi2.metric(f"🎯 Presupuesto ({label_periodo_budget})", f"${total_presupuestado:,.0f}", border=True)

delta_color = "normal" if pct_global <= 80 else ("off" if pct_global <= 100 else "inverse")
kpi3.metric(
    "📈 % Ejecución",
    f"{pct_global:.1f}%",
    delta=f"{'🟢 En meta' if pct_global <= 80 else ('🟡 Cerca al límite' if pct_global <= 100 else '🔴 Excedido')}",
    delta_color=delta_color,
    border=True
)

# KPIs Predictivos
proy_total = proj_metrics["total_proyectado"]
desvio = proj_metrics["desvio_proyectado"]
if desvio >= 0:
    lbl_desvio = f"🟢 Margen est: -${abs(desvio):,.0f}"
    color_desvio = "normal"
else:
    lbl_desvio = f"🔴 Exceso est: +${abs(desvio):,.0f}"
    color_desvio = "inverse"

kpi4.metric(
    f"🔮 Cierre Est. ({proj_metrics['mes_nombre']})",
    f"${proy_total:,.0f}",
    delta=lbl_desvio,
    delta_color=color_desvio,
    border=True
)

ritmo = proj_metrics["ritmo_diario_global"]
sub_ritmo = f"Día {proj_metrics['days_elapsed']} de {proj_metrics['total_days']}" if proj_metrics["is_current_month"] else "Mes cerrado (100%)"
kpi5.metric(
    "⚡ Ritmo Diario",
    f"${ritmo:,.0f}/día",
    delta=sub_ritmo,
    delta_color="off",
    border=True
)

# Alerta preventiva de run-rate
if proj_metrics["is_current_month"]:
    if desvio < 0:
        st.warning(
            f"⚠️ **Alerta Preventiva de Run-Rate ({proj_metrics['mes_nombre']} {proj_metrics['target_year']}):** "
            f"Al ritmo diario actual de **${ritmo:,.0f}/día** (con **{proj_metrics['days_remaining']} días restantes**), "
            f"se estima un cierre de **${proy_total:,.0f}**, lo que generaría un sobregiro proyectado de **+${abs(desvio):,.0f}** sobre el presupuesto (**${proj_metrics['total_presupuestado']:,.0f}**)."
        )
    else:
        st.success(
            f"🟢 **Ritmo de Gasto en Meta ({proj_metrics['mes_nombre']} {proj_metrics['target_year']}):** "
            f"Al ritmo actual de **${ritmo:,.0f}/día**, se proyecta un cierre de **${proy_total:,.0f}**, "
            f"dejando un margen de ahorro estimado de **${abs(desvio):,.0f}**."
        )
else:
    st.info(
        f"ℹ️ **Resumen Histórico ({proj_metrics['mes_nombre']} {proj_metrics['target_year']}):** "
        f"Mes cerrado. Ejecución final: **${proj_metrics['total_gastado']:,.0f}** vs Presupuesto: **${proj_metrics['total_presupuestado']:,.0f}**."
    )

st.markdown("---")

# --- 1. GRÁFICO HISTÓRICO: PRESUPUESTADO VS GASTADO MENSUAL (DIVIDIDO POR AÑO) ---
st.subheader("📈 Comparativo Mensual de Gastos (Dividido por Año)")
st.caption("Comparación visual de gastos reales mes a mes agrupados y divididos por cada año registrado.")

df_mensual_anio = compute_monthly_evolution(
    df_gastos,
    df_presupuestos,
    current_user,
    selected_year=int(sel_anio) if sel_anio != "Todos" else None
)

if not df_mensual_anio.empty:
    fig_mensual = px.bar(
        df_mensual_anio,
        x="MES",
        y="GASTO_REAL",
        color="ANIO",
        barmode="group",
        labels={"GASTO_REAL": "Gasto Real ($)", "MES": "Mes", "ANIO": "Año"},
        color_discrete_sequence=["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899"],
        text=df_mensual_anio["GASTO_REAL"].apply(lambda v: f"${v/1e6:.1f}M" if v >= 1e6 else (f"${v:,.0f}" if v > 0 else ""))
    )
    
    meta_ref = df_mensual_anio["PRESUPUESTO"].iloc[0] if not df_mensual_anio.empty else 0.0
    if meta_ref > 0:
        fig_mensual.add_hline(
            y=meta_ref,
            line_dash="dash",
            line_color="#EF4444",
            annotation_text=f"Meta Presupuesto: ${meta_ref:,.0f}",
            annotation_position="top right"
        )

    fig_mensual.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Gasto Real ($)")
    )
    st.plotly_chart(fig_mensual, width='stretch')
else:
    st.info("Sin datos para generar el comparativo mensual.")

st.markdown("---")

# --- 2. TRAYECTORIA Y CURVA DE PROYECCIÓN A FIN DE MES ---
st.subheader(f"🔮 Trayectoria y Curva de Proyección a Fin de Mes ({proj_metrics['mes_nombre']} {proj_metrics['target_year']})")
st.caption("Evolución del gasto acumulado día a día y proyección estimada hacia el cierre del mes.")

df_traj = compute_trajectory_data(
    df_gastos,
    total_presupuesto=proj_metrics["total_presupuestado"],
    total_proyectado=proj_metrics["total_proyectado"],
    target_year=proj_metrics["target_year"],
    target_month=proj_metrics["target_month"],
    days_elapsed=proj_metrics["days_elapsed"],
    total_days=proj_metrics["total_days"]
)

fig_traj = go.Figure()
# Gasto real acumulado
fig_traj.add_trace(go.Scatter(
    x=df_traj["FECHA_ETIQUETA"],
    y=df_traj["GASTO_REAL_ACUM"],
    mode="lines+markers",
    name="Gasto Real Acumulado",
    line=dict(color="#3B82F6", width=3),
    marker=dict(size=5)
))

# Proyección Run-Rate
if proj_metrics["is_current_month"]:
    fig_traj.add_trace(go.Scatter(
        x=df_traj["FECHA_ETIQUETA"],
        y=df_traj["GASTO_PROYECTADO_ACUM"],
        mode="lines",
        name="Trayectoria Proyectada (Run-Rate)",
        line=dict(color="#F59E0B", width=3, dash="dash")
    ))

# Techo Presupuestal
fig_traj.add_trace(go.Scatter(
    x=df_traj["FECHA_ETIQUETA"],
    y=df_traj["META_PRESUPUESTO"],
    mode="lines",
    name="Meta Presupuesto",
    line=dict(color="#EF4444", width=2, dash="dot")
))

fig_traj.update_layout(
    height=320,
    margin=dict(l=10, r=10, t=20, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis=dict(title="Monto Acumulado ($)"),
    xaxis=dict(title="Día del Mes")
)
st.plotly_chart(fig_traj, width='stretch')

st.markdown("---")

# --- 3. SEMÁFORO Y CONTROL PRESUPUESTAL POR RUBRO ---
st.subheader("🎯 Semáforo y Control Presupuestal por Rubro")
tab_pred, tab_real = st.tabs([
    f"🔮 Proyección Predictiva ({proj_metrics['mes_nombre']} {proj_metrics['target_year']})",
    f"📊 Ejecución Real ({label_periodo_budget})"
])

with tab_pred:
    st.caption("Proyección inteligente de cierre según naturaleza del gasto (Fijo vs Variable) y ritmo diario.")
    if df_proj.empty:
        st.info("No hay metas configuradas.")
    else:
        df_proj_view = df_proj.copy()
        df_proj_view["PROY_RATIO"] = (df_proj_view["PCT_PROYECTADO"] / 100.0).clip(lower=0.0)

        n_meta_p = len(df_proj_view[df_proj_view["PCT_PROYECTADO"] < 85])
        n_alerta_p = len(df_proj_view[(df_proj_view["PCT_PROYECTADO"] >= 85) & (df_proj_view["PCT_PROYECTADO"] <= 100)])
        n_exceso_p = len(df_proj_view[df_proj_view["PCT_PROYECTADO"] > 100])

        cp1, cp2, cp3 = st.columns(3)
        cp1.caption(f"🟢 **Ritmo Controlado (<85%):** {n_meta_p} rubros")
        cp2.caption(f"🟡 **En Advertencia (85-100%):** {n_alerta_p} rubros")
        cp3.caption(f"🔴 **Exceso Proyectado (>100%):** {n_exceso_p} rubros")

        st.dataframe(
            df_proj_view[["RUBRO", "COMPORTAMIENTO", "TIPO", "GASTO_REAL", "RITMO_DIARIO", "GASTO_PROYECTADO", "MONTO_PRESUPUESTO", "PROY_RATIO", "ESTADO_PREDICTIVO"]],
            width="stretch",
            height=260,
            column_config={
                "RUBRO": st.column_config.TextColumn("Rubro", width="medium"),
                "COMPORTAMIENTO": st.column_config.TextColumn("Naturaleza", width="small"),
                "TIPO": st.column_config.TextColumn("Tipo", width="small"),
                "GASTO_REAL": st.column_config.NumberColumn("Gastado Hoy ($)", format="$%d"),
                "RITMO_DIARIO": st.column_config.NumberColumn("Ritmo ($/día)", format="$%d"),
                "GASTO_PROYECTADO": st.column_config.NumberColumn("Cierre Est. ($)", format="$%d"),
                "MONTO_PRESUPUESTO": st.column_config.NumberColumn("Presupuesto ($)", format="$%d"),
                "PROY_RATIO": st.column_config.ProgressColumn(
                    "% Proyectado",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.0f%%"
                ),
                "ESTADO_PREDICTIVO": st.column_config.TextColumn("Diagnóstico", width="medium")
            }
        )

with tab_real:
    st.caption(f"Monitoreo de metas presupuestales para **{label_periodo_budget}** vs Presupuesto {'Mensual' if num_meses_budget == 1 else f'de {num_meses_budget} meses'}.")
    if summary_budget.empty:
        st.info("No hay metas de presupuesto configuradas.")
    else:
        df_semaforo = summary_budget.copy()
        df_semaforo["PROGRESO_RATIO"] = (df_semaforo["PORCENTAJE_EJECUCION"] / 100.0).clip(lower=0.0)
        
        n_meta = len(df_semaforo[df_semaforo["PORCENTAJE_EJECUCION"] < 80])
        n_alerta = len(df_semaforo[(df_semaforo["PORCENTAJE_EJECUCION"] >= 80) & (df_semaforo["PORCENTAJE_EJECUCION"] <= 100)])
        n_exceso = len(df_semaforo[df_semaforo["PORCENTAJE_EJECUCION"] > 100])

        m_c1, m_c2, m_c3 = st.columns(3)
        m_c1.caption(f"🟢 **En Rango (<80%):** {n_meta} rubros")
        m_c2.caption(f"🟡 **En Alerta (80-100%):** {n_alerta} rubros")
        m_c3.caption(f"🔴 **Excedidos (>100%):** {n_exceso} rubros")

        st.dataframe(
            df_semaforo[["RUBRO", "COMPORTAMIENTO", "TIPO", "GASTO_REAL", "MONTO_PRESUPUESTO", "PROGRESO_RATIO", "ESTADO"]],
            width="stretch",
            height=240,
            column_config={
                "RUBRO": st.column_config.TextColumn("Rubro", width="medium"),
                "COMPORTAMIENTO": st.column_config.TextColumn("Naturaleza", width="small"),
                "TIPO": st.column_config.TextColumn("Tipo", width="small"),
                "GASTO_REAL": st.column_config.NumberColumn(f"Gastado {label_periodo_budget} ($)", format="$%d"),
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

# --- 3. GRÁFICOS ANALÍTICOS ---
st.subheader("📊 Análisis Detallado de Gastos")
g_col1, g_col2 = st.columns(2)

with g_col1:
    st.markdown(f"##### 🎯 Comparativo por Rubro ({label_periodo_budget})")
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
        st.plotly_chart(fig_bar, width='stretch')
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
        st.plotly_chart(fig_pie, width='stretch')
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
        st.plotly_chart(fig_payer, width='stretch')

with g_col4:
    st.markdown("##### 💳 Compromisos Tarjetas de Crédito por Mes (Apilado por Rubro)")
    if not df_filtered.empty and "Mes_Pago" in df_filtered.columns:
        df_tc = df_filtered[
            (df_filtered["PAGO"] == True) &
            (df_filtered["Mes_Pago"].fillna("").astype(str).str.strip() != "")
        ].copy()
        if not df_tc.empty:
            df_tc["RUBRO"] = df_tc["RUBRO"].fillna("Otros").astype(str).str.strip()
            df_tc["RUBRO"] = df_tc["RUBRO"].replace({"": "Otros"})

            df_tc_mes = df_tc.groupby(["Mes_Pago", "RUBRO"])["VALOR"].sum().reset_index()

            # Ordenar los meses cronológicamente
            meses_en_datos = [m for m in MESES_NOMBRE if m in df_tc_mes["Mes_Pago"].unique()]
            meses_extra = [m for m in df_tc_mes["Mes_Pago"].unique() if m not in MESES_NOMBRE]
            orden_meses = meses_en_datos + meses_extra

            fig_tc = px.bar(
                df_tc_mes,
                x="Mes_Pago",
                y="VALOR",
                color="RUBRO",
                barmode="stack",
                labels={"Mes_Pago": "Mes de Pago", "VALOR": "Monto ($)", "RUBRO": "Rubro Presupuestal"},
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_tc.update_layout(
                xaxis=dict(title="Mes de Pago", categoryorder="array", categoryarray=orden_meses),
                yaxis=dict(title="Compromiso ($)"),
                height=300,
                margin=dict(l=10, r=10, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_tc, width='stretch')
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
