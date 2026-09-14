import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

MESES_NOMBRE = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

def filter_gastos_by_user(df_gastos: pd.DataFrame, current_user: str) -> pd.DataFrame:
    """
    Filtra los gastos según las reglas de visibilidad:
    - Gastos de Casa (TIPO == 'Casa'): Visibles para Edison y Diana.
    - Gastos Personales (TIPO == 'Personal'): Visibles únicamente si QUIEN PAGA == current_user.
    """
    if df_gastos.empty:
        return df_gastos

    cond_casa = df_gastos["TIPO"].str.lower() == "casa"
    cond_personal = (df_gastos["TIPO"].str.lower() == "personal") & (df_gastos["QUIEN PAGA"].str.strip().str.lower() == current_user.lower())
    cond_otro = ~df_gastos["TIPO"].str.lower().isin(["casa", "personal"])
    
    return df_gastos[cond_casa | cond_personal | cond_otro].copy()

def get_available_rubros(df_presupuestos: pd.DataFrame, tipo: str, current_user: str) -> List[str]:
    """Retorna la lista de rubros disponibles según el tipo de gasto y el usuario activo."""
    if df_presupuestos.empty:
        return ["Otros"]

    df_active = df_presupuestos.copy()
    if "ACTIVO" in df_active.columns:
        df_active = df_active[df_active["ACTIVO"] == True]

    if tipo.lower() == "casa":
        rubros = df_active[df_active["TIPO"].str.lower() == "casa"]["RUBRO"].dropna().unique().tolist()
    else:
        rubros = df_active[
            (df_active["TIPO"].str.lower() == "personal") & 
            (df_active["USUARIO"].str.lower() == current_user.lower())
        ]["RUBRO"].dropna().unique().tolist()

    if not rubros:
        rubros = ["General", "Otros"]
    return sorted(list(set(rubros)))

import calendar
from datetime import datetime

def compute_budget_summary(
    df_gastos_visibles: pd.DataFrame,
    df_presupuestos: pd.DataFrame,
    current_user: str,
    *args,
    tipo_filtro: Optional[str] = None,
    rubros_filtro: Optional[List[str]] = None,
    num_meses: int = 1,
    **kwargs
) -> pd.DataFrame:
    """
    Calcula el comparativo de gasto real vs presupuesto mensual por cada rubro (Casa y Personales del usuario).
    Aplica filtros de tipo, rubro y escalamiento por número de meses si aplica.
    Preserva la columna COMPORTAMIENTO (Fijo / Variable).
    """
    try:
        df_presup = df_presupuestos.copy() if df_presupuestos is not None else pd.DataFrame()
        if "ACTIVO" in df_presup.columns:
            df_presup = df_presup[df_presup["ACTIVO"] == True]

        if "TIPO" not in df_presup.columns:
            df_presup["TIPO"] = "Casa"
        if "USUARIO" not in df_presup.columns:
            df_presup["USUARIO"] = "Todos"

        user_clean = str(current_user or "").strip().lower()
        presup_casa = df_presup[df_presup["TIPO"].fillna("").astype(str).str.lower() == "casa"]
        presup_user = df_presup[
            (df_presup["TIPO"].fillna("").astype(str).str.lower() == "personal") & 
            (df_presup["USUARIO"].fillna("").astype(str).str.lower() == user_clean)
        ]
        df_metas = pd.concat([presup_casa, presup_user], ignore_index=True)

        if df_metas.empty:
            df_metas = pd.DataFrame(columns=["RUBRO", "TIPO", "USUARIO", "MONTO_PRESUPUESTO", "COMPORTAMIENTO"])

        if tipo_filtro and str(tipo_filtro).lower() != "todos":
            df_metas = df_metas[df_metas["TIPO"].fillna("").astype(str).str.lower() == str(tipo_filtro).lower()]
        if rubros_filtro:
            df_metas = df_metas[df_metas["RUBRO"].isin(rubros_filtro)]

        # Escalar presupuesto mensual por el número de meses evaluados (por defecto 1 mes)
        try:
            factor_meses = max(1, int(num_meses)) if num_meses else 1
        except Exception:
            factor_meses = 1

        if "MONTO_PRESUPUESTO" in df_metas.columns:
            df_metas["MONTO_PRESUPUESTO"] = pd.to_numeric(df_metas["MONTO_PRESUPUESTO"], errors="coerce").fillna(0.0) * factor_meses

        if "COMPORTAMIENTO" not in df_metas.columns:
            df_metas["COMPORTAMIENTO"] = "Variable"
        else:
            df_metas["COMPORTAMIENTO"] = df_metas["COMPORTAMIENTO"].fillna("Variable")

        # Agrupar gastos reales por RUBRO
        if df_gastos_visibles is not None and not df_gastos_visibles.empty and "RUBRO" in df_gastos_visibles.columns:
            df_g = df_gastos_visibles.copy()
            df_g["VALOR"] = pd.to_numeric(df_g["VALOR"], errors="coerce").fillna(0.0)
            gastos_por_rubro = df_g.groupby("RUBRO")["VALOR"].sum().reset_index()
            gastos_por_rubro.rename(columns={"VALOR": "GASTO_REAL"}, inplace=True)
        else:
            gastos_por_rubro = pd.DataFrame(columns=["RUBRO", "GASTO_REAL"])

        merged = pd.merge(df_metas, gastos_por_rubro, on="RUBRO", how="outer")
        if rubros_filtro:
            merged = merged[merged["RUBRO"].isin(rubros_filtro)]
        if tipo_filtro and str(tipo_filtro).lower() != "todos":
            merged = merged[merged["TIPO"].fillna("").astype(str).str.lower() == str(tipo_filtro).lower()]

        merged["MONTO_PRESUPUESTO"] = pd.to_numeric(merged["MONTO_PRESUPUESTO"], errors="coerce").fillna(0.0)
        merged["GASTO_REAL"] = pd.to_numeric(merged["GASTO_REAL"], errors="coerce").fillna(0.0)
        merged["TIPO"] = merged["TIPO"].fillna("Casa")
        merged["USUARIO"] = merged["USUARIO"].fillna("Todos")
        merged["COMPORTAMIENTO"] = merged["COMPORTAMIENTO"].fillna("Variable")

        merged["DIFERENCIA"] = merged["MONTO_PRESUPUESTO"] - merged["GASTO_REAL"]
        
        def calc_pct(row):
            if row["MONTO_PRESUPUESTO"] > 0:
                return (row["GASTO_REAL"] / row["MONTO_PRESUPUESTO"]) * 100.0
            elif row["GASTO_REAL"] > 0:
                return 100.0
            return 0.0

        merged["PORCENTAJE_EJECUCION"] = merged.apply(calc_pct, axis=1)

        def get_status(row):
            pct = row["PORCENTAJE_EJECUCION"]
            monto_presup = row["MONTO_PRESUPUESTO"]
            if monto_presup > 0 and pct > 100.0:
                exceso = row["GASTO_REAL"] - monto_presup
                return f"🔴 Excedido (+${exceso:,.0f})", "#EF4444"
            elif pct >= 80.0:
                return "🟡 En Alerta (80%-100%)", "#F59E0B"
            else:
                return "🟢 En Rango (<80%)", "#10B981"

        status_data = merged.apply(get_status, axis=1)
        merged["ESTADO"] = [s[0] for s in status_data]
        merged["COLOR"] = [s[1] for s in status_data]

        return merged.sort_values(by=["PORCENTAJE_EJECUCION", "GASTO_REAL"], ascending=False).reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame(columns=[
            "RUBRO", "TIPO", "USUARIO", "MONTO_PRESUPUESTO",
            "COMPORTAMIENTO", "GASTO_REAL", "DIFERENCIA",
            "PORCENTAJE_EJECUCION", "ESTADO", "COLOR"
        ])

def compute_projection_summary(
    df_gastos_visibles: pd.DataFrame,
    df_presupuestos: pd.DataFrame,
    current_user: str,
    selected_year: Optional[int] = None,
    selected_month: Optional[int] = None,
    tipo_filtro: Optional[str] = None,
    rubros_filtro: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Calcula la proyección predictiva a fin de mes (Run-rate inteligente):
    - Rubros Variables: Gasto Real extrapolado por días transcurridos vs días totales del mes.
    - Rubros Fijos: Si ya se pagó = Gasto Real. Si no se ha pagado = Monto presupuestado esperado.
    - Detección adaptativa de mes en curso vs mes cerrado.
    """
    now = datetime.now()
    
    # Determinar año y mes de análisis
    target_year = int(selected_year) if selected_year else now.year
    target_month = int(selected_month) if selected_month else now.month

    # Días totales y días transcurridos
    _, total_days = calendar.monthrange(target_year, target_month)
    
    if target_year == now.year and target_month == now.month:
        days_elapsed = min(now.day, total_days)
        is_current_month = True
    elif (target_year < now.year) or (target_year == now.year and target_month < now.month):
        days_elapsed = total_days
        is_current_month = False
    else:
        days_elapsed = 0
        is_current_month = False

    # Filtrar metas activas del usuario (Casa + Personal)
    df_presup = df_presupuestos.copy()
    if "ACTIVO" in df_presup.columns:
        df_presup = df_presup[df_presup["ACTIVO"] == True]

    presup_casa = df_presup[df_presup["TIPO"].str.lower() == "casa"]
    presup_user = df_presup[
        (df_presup["TIPO"].str.lower() == "personal") & 
        (df_presup["USUARIO"].str.lower() == current_user.lower())
    ]
    df_metas = pd.concat([presup_casa, presup_user], ignore_index=True)

    if df_metas.empty:
        df_metas = pd.DataFrame(columns=["RUBRO", "TIPO", "USUARIO", "MONTO_PRESUPUESTO", "COMPORTAMIENTO"])

    if tipo_filtro and str(tipo_filtro).lower() != "todos":
        df_metas = df_metas[df_metas["TIPO"].str.lower() == str(tipo_filtro).lower()]
    if rubros_filtro:
        df_metas = df_metas[df_metas["RUBRO"].isin(rubros_filtro)]

    if "COMPORTAMIENTO" not in df_metas.columns:
        df_metas["COMPORTAMIENTO"] = "Variable"
    else:
        df_metas["COMPORTAMIENTO"] = df_metas["COMPORTAMIENTO"].fillna("Variable")

    # Filtrar gastos reales del mes y año analizado
    df_g = df_gastos_visibles.copy()
    if not df_g.empty:
        if "FECHA_DT" not in df_g.columns:
            df_g["FECHA_DT"] = pd.to_datetime(df_g["FECHA"], errors="coerce")
        df_month_gastos = df_g[
            (df_g["FECHA_DT"].dt.year == target_year) & 
            (df_g["FECHA_DT"].dt.month == target_month)
        ]
    else:
        df_month_gastos = pd.DataFrame(columns=["RUBRO", "VALOR"])

    if not df_month_gastos.empty and "RUBRO" in df_month_gastos.columns:
        gastos_por_rubro = df_month_gastos.groupby("RUBRO")["VALOR"].sum().reset_index()
        gastos_por_rubro.rename(columns={"VALOR": "GASTO_REAL"}, inplace=True)
    else:
        gastos_por_rubro = pd.DataFrame(columns=["RUBRO", "GASTO_REAL"])

    merged = pd.merge(df_metas, gastos_por_rubro, on="RUBRO", how="outer")
    merged["MONTO_PRESUPUESTO"] = pd.to_numeric(merged["MONTO_PRESUPUESTO"], errors="coerce").fillna(0.0)
    merged["GASTO_REAL"] = pd.to_numeric(merged["GASTO_REAL"], errors="coerce").fillna(0.0)
    merged["TIPO"] = merged["TIPO"].fillna("Casa")
    merged["USUARIO"] = merged["USUARIO"].fillna("Todos")
    merged["COMPORTAMIENTO"] = merged["COMPORTAMIENTO"].fillna("Variable").astype(str).str.capitalize()

    # Cálculo del Run-Rate proyectado
    def project_row(row):
        monto = row["MONTO_PRESUPUESTO"]
        real = row["GASTO_REAL"]
        comp = row["COMPORTAMIENTO"]
        
        if comp == "Variable":
            if days_elapsed > 0:
                ritmo = real / days_elapsed
                proy = ritmo * total_days
            else:
                ritmo = 0.0
                proy = monto
        else: # Fijo
            ritmo = (real / days_elapsed) if days_elapsed > 0 else 0.0
            if real > 0:
                proy = real
            else:
                proy = monto # compromiso fijo pendiente

        return pd.Series([ritmo, proy], index=["RITMO_DIARIO", "GASTO_PROYECTADO"])

    proj_vals = merged.apply(project_row, axis=1)
    merged["RITMO_DIARIO"] = proj_vals["RITMO_DIARIO"]
    merged["GASTO_PROYECTADO"] = proj_vals["GASTO_PROYECTADO"]
    merged["DIFERENCIA_PROYECTADA"] = merged["MONTO_PRESUPUESTO"] - merged["GASTO_PROYECTADO"]

    def calc_proj_pct(row):
        presup = row["MONTO_PRESUPUESTO"]
        proy = row["GASTO_PROYECTADO"]
        if presup > 0:
            return (proy / presup) * 100.0
        elif proy > 0:
            return 100.0
        return 0.0

    merged["PCT_PROYECTADO"] = merged.apply(calc_proj_pct, axis=1)

    def get_early_warning(row):
        pct = row["PCT_PROYECTADO"]
        presup = row["MONTO_PRESUPUESTO"]
        proy = row["GASTO_PROYECTADO"]
        if presup > 0 and proy > presup:
            exceso = proy - presup
            return f"🔴 Exceso Proyectado (+${exceso:,.0f})", "#EF4444"
        elif pct >= 85.0:
            return "🟡 Advertencia (>85%)", "#F59E0B"
        else:
            return "🟢 Ritmo Controlado", "#10B981"

    warn_data = merged.apply(get_early_warning, axis=1)
    merged["ESTADO_PREDICTIVO"] = [w[0] for w in warn_data]
    merged["COLOR_PREDICTIVO"] = [w[1] for w in warn_data]

    # Ordenar por desvío proyectado y monto
    merged = merged.sort_values(by=["PCT_PROYECTADO", "GASTO_PROYECTADO"], ascending=False).reset_index(drop=True)

    # Métricas consolidadas
    tot_presup = float(merged["MONTO_PRESUPUESTO"].sum())
    tot_real = float(merged["GASTO_REAL"].sum())
    tot_proy = float(merged["GASTO_PROYECTADO"].sum())
    desvio = tot_presup - tot_proy
    ritmo_global = (tot_real / days_elapsed) if days_elapsed > 0 else 0.0

    metrics = {
        "target_year": target_year,
        "target_month": target_month,
        "mes_nombre": MESES_NOMBRE[target_month - 1],
        "total_days": total_days,
        "days_elapsed": days_elapsed,
        "days_remaining": max(0, total_days - days_elapsed),
        "is_current_month": is_current_month,
        "total_presupuestado": tot_presup,
        "total_gastado": tot_real,
        "total_proyectado": tot_proy,
        "desvio_proyectado": desvio,
        "pct_proyectado_total": (tot_proy / tot_presup * 100.0) if tot_presup > 0 else 0.0,
        "ritmo_diario_global": ritmo_global
    }

    return merged, metrics

def compute_trajectory_data(
    df_gastos_visibles: pd.DataFrame,
    total_presupuesto: float,
    total_proyectado: float,
    target_year: int,
    target_month: int,
    days_elapsed: int,
    total_days: int
) -> pd.DataFrame:
    """
    Construye la serie día a día (1..total_days) con:
    - Gasto Real acumulado hasta el día transcurrido.
    - Proyección acumulada punteada hasta el fin del mes.
    - Línea de presupuesto de referencia.
    """
    df_g = df_gastos_visibles.copy()
    if not df_g.empty:
        if "FECHA_DT" not in df_g.columns:
            df_g["FECHA_DT"] = pd.to_datetime(df_g["FECHA"], errors="coerce")
        df_month = df_g[
            (df_g["FECHA_DT"].dt.year == target_year) & 
            (df_g["FECHA_DT"].dt.month == target_month)
        ]
    else:
        df_month = pd.DataFrame(columns=["FECHA_DT", "VALOR"])

    # Gastos por día del mes
    daily_spend = {}
    if not df_month.empty:
        df_valid_days = df_month.dropna(subset=["FECHA_DT"])
        for day, val in df_valid_days.groupby(df_valid_days["FECHA_DT"].dt.day)["VALOR"].sum().items():
            daily_spend[int(day)] = float(val)

    rows = []
    acum_real = 0.0
    
    # Calcular pendiente restante para proyección suave
    gasto_al_dia_hoy = 0.0
    for d in range(1, days_elapsed + 1):
        gasto_al_dia_hoy += daily_spend.get(d, 0.0)

    dias_restantes = max(1, total_days - days_elapsed)
    pendiente_restante = max(0.0, (total_proyectado - gasto_al_dia_hoy) / dias_restantes) if days_elapsed < total_days else 0.0

    for d in range(1, total_days + 1):
        gasto_del_dia = daily_spend.get(d, 0.0)
        
        if d <= days_elapsed:
            acum_real += gasto_del_dia
            real_val = acum_real
            # La proyección en días pasados/presente se alinea al gasto real
            proy_val = acum_real
        else:
            real_val = None
            proy_val = gasto_al_dia_hoy + pendiente_restante * (d - days_elapsed)

        rows.append({
            "DIA": d,
            "FECHA_ETIQUETA": f"{d:02d}/{target_month:02d}",
            "GASTO_REAL_ACUM": real_val,
            "GASTO_PROYECTADO_ACUM": proy_val,
            "META_PRESUPUESTO": total_presupuesto
        })

    return pd.DataFrame(rows)

def compute_monthly_evolution(
    df_gastos_visibles: pd.DataFrame,
    df_presupuestos: pd.DataFrame,
    current_user: str,
    selected_year: Optional[int] = None
) -> pd.DataFrame:
    """
    Calcula el comparativo mensual de Gasto Real vs Presupuesto, dividido y agrupado por AÑO.
    Permite comparar el comportamiento interanual y mensual de manera clara.
    """
    # 1. Presupuesto mensual total del usuario
    df_presup = df_presupuestos.copy()
    if "ACTIVO" in df_presup.columns:
        df_presup = df_presup[df_presup["ACTIVO"] == True]

    presup_casa = df_presup[df_presup["TIPO"].str.lower() == "casa"]["MONTO_PRESUPUESTO"].sum()
    presup_user = df_presup[
        (df_presup["TIPO"].str.lower() == "personal") & 
        (df_presup["USUARIO"].str.lower() == current_user.lower())
    ]["MONTO_PRESUPUESTO"].sum()
    meta_mensual_total = float(presup_casa + presup_user)

    # 2. Extraer Año y Mes
    df_gastos_copy = df_gastos_visibles.copy()
    if not df_gastos_copy.empty:
        if "FECHA_DT" not in df_gastos_copy.columns:
            df_gastos_copy["FECHA_DT"] = pd.to_datetime(df_gastos_copy["FECHA"], errors="coerce")
        df_gastos_copy["ANIO"] = df_gastos_copy["FECHA_DT"].dt.year
        df_gastos_copy["MES_NUM"] = df_gastos_copy["FECHA_DT"].dt.month
    else:
        df_gastos_copy["ANIO"] = datetime.now().year
        df_gastos_copy["MES_NUM"] = 1

    df_valid = df_gastos_copy.dropna(subset=["ANIO", "MES_NUM"]).copy()
    if not df_valid.empty:
        df_valid["ANIO"] = df_valid["ANIO"].astype(int)
        df_valid["MES_NUM"] = df_valid["MES_NUM"].astype(int)

    # Determinar años a incluir
    if selected_year is not None:
        anios_presentes = [int(selected_year)]
    elif not df_valid.empty:
        anios_presentes = sorted(df_valid["ANIO"].unique().tolist())
    else:
        anios_presentes = [datetime.now().year]

    filas = []
    for anio in anios_presentes:
        df_anio = df_valid[df_valid["ANIO"] == anio] if not df_valid.empty else pd.DataFrame()
        meses_con_datos = sorted(df_anio["MES_NUM"].unique().tolist()) if not df_anio.empty else [1]
        
        for mes_idx in range(1, 13):
            gasto_mes = df_anio[df_anio["MES_NUM"] == mes_idx]["VALOR"].sum() if not df_anio.empty else 0.0
            # Incluir mes si tiene gastos o si está dentro de la ventana de meses con actividad del año
            if gasto_mes > 0 or (meses_con_datos and min(meses_con_datos) <= mes_idx <= max(meses_con_datos)):
                filas.append({
                    "ANIO": str(anio),
                    "MES_NUM": mes_idx,
                    "MES": MESES_NOMBRE[mes_idx - 1],
                    "MES_ANIO": f"{MESES_NOMBRE[mes_idx - 1][:3]} {anio}",
                    "PRESUPUESTO": meta_mensual_total,
                    "GASTO_REAL": float(gasto_mes),
                    "DIFERENCIA": meta_mensual_total - float(gasto_mes)
                })

    if not filas:
        filas = [{
            "ANIO": str(datetime.now().year),
            "MES_NUM": 1,
            "MES": "Enero",
            "MES_ANIO": f"Ene {datetime.now().year}",
            "PRESUPUESTO": meta_mensual_total,
            "GASTO_REAL": 0.0,
            "DIFERENCIA": meta_mensual_total
        }]

    return pd.DataFrame(filas)

def compute_annual_summary(
    df_gastos_visibles: pd.DataFrame,
    df_presupuestos: pd.DataFrame,
    current_user: str,
    selected_year: int,
    tipo_filtro: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Consolida el seguimiento global anual de gastos:
    - Presupuesto Anual = Presupuesto Mensual Base * 12
    - Real Anual = Suma de gastos ejecutados en el año seleccionado
    - Variación = Real Anual - Presupuesto Anual
    - % Ejecución = (Real Anual / Presupuesto Anual) * 100 con control de nulos y división por cero
    """
    try:
        df_g = df_gastos_visibles.copy() if df_gastos_visibles is not None else pd.DataFrame()
        if not df_g.empty:
            if "FECHA_DT" not in df_g.columns:
                df_g["FECHA_DT"] = pd.to_datetime(df_g["FECHA"], errors="coerce")
            df_g["ANIO"] = df_g["FECHA_DT"].dt.year
            df_anio = df_g[df_g["ANIO"] == int(selected_year)].copy()
        else:
            df_anio = pd.DataFrame()

        if tipo_filtro and str(tipo_filtro).lower() != "todos" and not df_anio.empty:
            df_anio = df_anio[df_anio["TIPO"].fillna("").astype(str).str.lower() == str(tipo_filtro).lower()]

        summary = compute_budget_summary(
            df_anio,
            df_presupuestos,
            current_user,
            tipo_filtro=tipo_filtro,
            num_meses=12
        )

        presup_total = float(summary["MONTO_PRESUPUESTO"].sum()) if not summary.empty else 0.0
        real_total = float(summary["GASTO_REAL"].sum()) if not summary.empty else 0.0
        variacion_total = real_total - presup_total
        pct_total = (real_total / presup_total * 100.0) if presup_total > 0 else 0.0

        if not summary.empty:
            summary["VARIACION"] = summary["GASTO_REAL"] - summary["MONTO_PRESUPUESTO"]
        else:
            summary["VARIACION"] = 0.0

        metrics = {
            "selected_year": int(selected_year),
            "presupuesto_anual": presup_total,
            "real_anual": real_total,
            "variacion": variacion_total,
            "pct_ejecucion": pct_total,
            "total_registros": len(df_anio)
        }
        return summary, metrics
    except Exception as e:
        empty_df = pd.DataFrame(columns=[
            "RUBRO", "TIPO", "USUARIO", "MONTO_PRESUPUESTO",
            "COMPORTAMIENTO", "GASTO_REAL", "DIFERENCIA", "VARIACION",
            "PORCENTAJE_EJECUCION", "ESTADO", "COLOR"
        ])
        metrics = {
            "selected_year": int(selected_year),
            "presupuesto_anual": 0.0,
            "real_anual": 0.0,
            "variacion": 0.0,
            "pct_ejecucion": 0.0,
            "total_registros": 0
        }
        return empty_df, metrics

def compute_annual_rankings(
    df_prod: pd.DataFrame,
    selected_year: int,
    top_n: int = 10
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifica los Top N productos más costosos y Top N proveedores por gasto acumulado en el año.
    """
    top_n = max(1, int(top_n)) if top_n else 10
    if df_prod is None or df_prod.empty:
        empty_prod = pd.DataFrame(columns=["PRODUCTO", "VALOR TOTAL", "CANTIDAD", "PRECIO_PROM"])
        empty_prov = pd.DataFrame(columns=["PROVEEDOR", "VALOR TOTAL", "NUM_COMPRAS"])
        return empty_prod, empty_prov

    df_p = df_prod.copy()
    if "FECHA_DT" not in df_p.columns:
        df_p["FECHA_DT"] = pd.to_datetime(df_p["FECHA"], errors="coerce")
    df_p["ANIO"] = df_p["FECHA_DT"].dt.year

    df_p_anio = df_p[df_p["ANIO"] == int(selected_year)].copy()
    if df_p_anio.empty:
        empty_prod = pd.DataFrame(columns=["PRODUCTO", "VALOR TOTAL", "CANTIDAD", "PRECIO_PROM"])
        empty_prov = pd.DataFrame(columns=["PROVEEDOR", "VALOR TOTAL", "NUM_COMPRAS"])
        return empty_prod, empty_prov

    for col in ["VALOR TOTAL", "CANTIDAD", "VALOR UNT"]:
        if col in df_p_anio.columns:
            df_p_anio[col] = pd.to_numeric(df_p_anio[col], errors="coerce").fillna(0.0)

    # 1. Top Productos
    df_valid_prod = df_p_anio.dropna(subset=["PRODUCTO"]).copy()
    df_valid_prod["PRODUCTO"] = df_valid_prod["PRODUCTO"].astype(str).str.strip()
    df_valid_prod = df_valid_prod[df_valid_prod["PRODUCTO"] != ""]
    
    if not df_valid_prod.empty:
        agg_dict = {"VALOR TOTAL": "sum"}
        if "CANTIDAD" in df_valid_prod.columns:
            agg_dict["CANTIDAD"] = "sum"
        if "VALOR UNT" in df_valid_prod.columns:
            agg_dict["VALOR UNT"] = "mean"
            
        top_productos = (
            df_valid_prod.groupby("PRODUCTO")
            .agg(agg_dict)
            .reset_index()
            .rename(columns={"VALOR UNT": "PRECIO_PROM"})
            .sort_values(by="VALOR TOTAL", ascending=False)
            .head(top_n)
        )
    else:
        top_productos = pd.DataFrame(columns=["PRODUCTO", "VALOR TOTAL", "CANTIDAD", "PRECIO_PROM"])

    # 2. Top Proveedores
    df_valid_prov = df_p_anio.dropna(subset=["PROVEEDOR"]).copy()
    df_valid_prov["PROVEEDOR"] = df_valid_prov["PROVEEDOR"].astype(str).str.strip()
    df_valid_prov = df_valid_prov[~df_valid_prov["PROVEEDOR"].str.lower().isin(["", "none", "nan", "varios", "null"])]

    if not df_valid_prov.empty:
        top_proveedores = (
            df_valid_prov.groupby("PROVEEDOR")
            .agg({"VALOR TOTAL": "sum", "PRODUCTO": "count"})
            .reset_index()
            .rename(columns={"PRODUCTO": "NUM_COMPRAS"})
            .sort_values(by="VALOR TOTAL", ascending=False)
            .head(top_n)
        )
    else:
        top_proveedores = pd.DataFrame(columns=["PROVEEDOR", "VALOR TOTAL", "NUM_COMPRAS"])

    return top_productos, top_proveedores
