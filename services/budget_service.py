import pandas as pd
from typing import List, Dict, Any, Tuple

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

def compute_budget_summary(df_gastos_visibles: pd.DataFrame, df_presupuestos: pd.DataFrame, current_user: str) -> pd.DataFrame:
    """
    Calcula el comparativo de gasto real vs presupuesto mensual por cada rubro (Casa y Personales del usuario).
    """
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
        df_metas = pd.DataFrame(columns=["RUBRO", "TIPO", "USUARIO", "MONTO_PRESUPUESTO"])

    # Agrupar gastos reales por RUBRO
    if not df_gastos_visibles.empty and "RUBRO" in df_gastos_visibles.columns:
        gastos_por_rubro = df_gastos_visibles.groupby("RUBRO")["VALOR"].sum().reset_index()
        gastos_por_rubro.rename(columns={"VALOR": "GASTO_REAL"}, inplace=True)
    else:
        gastos_por_rubro = pd.DataFrame(columns=["RUBRO", "GASTO_REAL"])

    merged = pd.merge(df_metas, gastos_por_rubro, on="RUBRO", how="outer")
    merged["MONTO_PRESUPUESTO"] = merged["MONTO_PRESUPUESTO"].fillna(0.0)
    merged["GASTO_REAL"] = merged["GASTO_REAL"].fillna(0.0)
    merged["TIPO"] = merged["TIPO"].fillna("Casa")
    merged["USUARIO"] = merged["USUARIO"].fillna("Todos")

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

def compute_monthly_evolution(df_gastos_visibles: pd.DataFrame, df_presupuestos: pd.DataFrame, current_user: str) -> pd.DataFrame:
    """
    Calcula el histórico mes a mes de Gasto Real vs Meta Presupuestal Total.
    """
    # 1. Presupuesto mensual total del usuario (Casa + Personal activo)
    df_presup = df_presupuestos.copy()
    if "ACTIVO" in df_presup.columns:
        df_presup = df_presup[df_presup["ACTIVO"] == True]

    presup_casa = df_presup[df_presup["TIPO"].str.lower() == "casa"]["MONTO_PRESUPUESTO"].sum()
    presup_user = df_presup[
        (df_presup["TIPO"].str.lower() == "personal") & 
        (df_presup["USUARIO"].str.lower() == current_user.lower())
    ]["MONTO_PRESUPUESTO"].sum()
    meta_mensual_total = float(presup_casa + presup_user)

    # 2. Agrupar gastos por mes numérico (1..12)
    df_gastos_copy = df_gastos_visibles.copy()
    if "FECHA_DT" in df_gastos_copy.columns:
        df_gastos_copy["MES_NUM"] = df_gastos_copy["FECHA_DT"].dt.month
    else:
        df_gastos_copy["MES_NUM"] = pd.to_datetime(df_gastos_copy["FECHA"], errors="coerce").dt.month

    # Filtrar meses válidos
    df_valid = df_gastos_copy.dropna(subset=["MES_NUM"])
    
    # Construir tabla de 12 meses
    filas = []
    meses_presentes = sorted(df_valid["MES_NUM"].unique().astype(int).tolist()) if not df_valid.empty else [1]
    
    # Si hay pocos meses, mostrar al menos los meses con datos o el año completo transcurrido
    for mes_idx in range(1, 13):
        gasto_mes = df_valid[df_valid["MES_NUM"] == mes_idx]["VALOR"].sum() if not df_valid.empty else 0.0
        # Solo incluir el mes si tiene gasto o si está entre los meses con actividad
        if gasto_mes > 0 or (meses_presentes and min(meses_presentes) <= mes_idx <= max(meses_presentes)):
            filas.append({
                "MES_NUM": mes_idx,
                "MES": MESES_NOMBRE[mes_idx - 1],
                "PRESUPUESTO": meta_mensual_total,
                "GASTO_REAL": float(gasto_mes),
                "DIFERENCIA": meta_mensual_total - float(gasto_mes)
            })

    if not filas:
        filas = [{"MES_NUM": 1, "MES": "Enero", "PRESUPUESTO": meta_mensual_total, "GASTO_REAL": 0.0, "DIFERENCIA": meta_mensual_total}]

    return pd.DataFrame(filas)
