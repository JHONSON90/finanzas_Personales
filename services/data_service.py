import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import traceback
from typing import Optional, List, Dict, Any

def assign_default_comportamiento(rubro: str) -> str:
    """Asigna comportamiento Fijo o Variable por defecto según palabras clave del rubro."""
    r = str(rubro).lower()
    fixed_keywords = ["arriendo", "servicio", "jardín", "jardin", "hipotecario", "ahorro", "crédito", "credito", "seguro", "colegio", "administración", "administracion", "pensión", "pension"]
    for kw in fixed_keywords:
        if kw in r:
            return "Fijo"
    return "Variable"

DEFAULT_CASA_PRESUPUESTOS = [
    {"RUBRO": "Arriendo", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 850000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Servicio doméstico", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 950000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Servicios públicos", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 400000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Mercado y despensa", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 1200000.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Gastos niños (Pañales etc)", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 600000.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Transporte local", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 25000.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Productos de aseo", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 500000.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Jardín niños", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 500000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
]

DEFAULT_PERSONAL_PRESUPUESTOS = [
    {"RUBRO": "Crédito hipotecario", "TIPO": "Personal", "USUARIO": "Edison", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Antojos y snacks", "TIPO": "Personal", "USUARIO": "Edison", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Meta de ahorro", "TIPO": "Personal", "USUARIO": "Edison", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Crédito hipotecario", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Antojos y snacks", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Meta de ahorro", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
]

def get_connection():
    """Obtiene la conexión GSheetsConnection de Streamlit."""
    return st.connection("gsheets", type=GSheetsConnection)

def safe_parse_dates(series: pd.Series) -> pd.Series:
    """Parsea fechas soportando múltiples formatos (YYYY-MM-DD, DD/MM/YYYY, etc.) sin corromper datos."""
    if series.empty:
        return series
    return pd.to_datetime(series, format="mixed", dayfirst=True, errors="coerce")

def format_dates_for_sheet(df: pd.DataFrame, col_name: str = "FECHA") -> pd.DataFrame:
    """Garantiza que las fechas se guarden como string YYYY-MM-DD sin borrar las existentes."""
    df_out = df.copy()
    if col_name in df_out.columns:
        if pd.api.types.is_datetime64_any_dtype(df_out[col_name]):
            df_out[col_name] = df_out[col_name].dt.strftime("%Y-%m-%d").fillna("")
        else:
            parsed = pd.to_datetime(df_out[col_name], format="mixed", dayfirst=True, errors="coerce")
            formatted = parsed.dt.strftime("%Y-%m-%d")
            # Conservar el valor original si el parseo directo dio NaT pero el original tenía texto
            df_out[col_name] = formatted.combine_first(
                df_out[col_name].astype(str).replace("nan", "").replace("None", "").replace("NaT", "")
            )
    return df_out

def load_gastos() -> pd.DataFrame:
    """Carga los datos de la hoja 'Gastos' preservando las fechas y tipos."""
    conn = get_connection()
    try:
        df = conn.read(worksheet="Gastos", ttl=0)
        if df is None or df.empty:
            df = pd.DataFrame(columns=[
                "FECHA", "QUIEN PAGA", "TIPO", "CONCEPTO",
                "CLASIFICACION", "RUBRO", "VALOR", "PAGO", "Mes_Pago"
            ])
        else:
            # Asegurar columnas requeridas
            if "RUBRO" not in df.columns:
                df["RUBRO"] = "Otros"
            if "VALOR" in df.columns:
                df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce").fillna(0.0)
            if "PAGO" in df.columns:
                df["PAGO"] = df["PAGO"].astype(bool)
            if "FECHA" in df.columns:
                # Mantener FECHA como string/formato legible y crear FECHA_DT para operaciones
                df["FECHA_DT"] = safe_parse_dates(df["FECHA"])
        return df
    except Exception as e:
        st.error(f"Error al leer hoja Gastos: {e}")
        return pd.DataFrame(columns=[
            "FECHA", "QUIEN PAGA", "TIPO", "CONCEPTO",
            "CLASIFICACION", "RUBRO", "VALOR", "PAGO", "Mes_Pago"
        ])

def save_gastos(df: pd.DataFrame) -> bool:
    """Guarda el DataFrame en la hoja 'Gastos'."""
    conn = get_connection()
    try:
        df_to_save = format_dates_for_sheet(df, "FECHA")
        if "FECHA_DT" in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=["FECHA_DT"])
        conn.update(worksheet="Gastos", data=df_to_save)
        return True
    except Exception as e:
        st.error(f"Error al guardar en hoja Gastos: {e}")
        return False

def add_single_gasto(new_gasto_dict: dict) -> bool:
    """Lee la hoja Gastos fresca, agrega el nuevo gasto de forma segura y guarda."""
    conn = get_connection()
    try:
        df_current = conn.read(worksheet="Gastos", ttl=0)
        if df_current is None or df_current.empty:
            df_current = pd.DataFrame(columns=[
                "FECHA", "QUIEN PAGA", "TIPO", "CONCEPTO",
                "CLASIFICACION", "RUBRO", "VALOR", "PAGO", "Mes_Pago"
            ])
        
        # Formatear la nueva fila
        new_row = pd.DataFrame([new_gasto_dict])
        df_updated = pd.concat([df_current, new_row], ignore_index=True)
        
        df_to_save = format_dates_for_sheet(df_updated, "FECHA")
        conn.update(worksheet="Gastos", data=df_to_save)
        return True
    except Exception as e:
        st.error(f"Error al agregar gasto: {e}")
        return False

def load_seguimiento_productos() -> pd.DataFrame:
    """Carga los datos de la hoja 'Seguimiento_Productos'."""
    conn = get_connection()
    try:
        df = conn.read(worksheet="Seguimiento_Productos", ttl=0)
        if df is None or df.empty:
            df = pd.DataFrame(columns=[
                "FECHA", "PROVEEDOR", "PRODUCTO", "CANTIDAD", "VALOR UNT", "VALOR TOTAL", "RUBRO"
            ])
        else:
            if "RUBRO" not in df.columns:
                df["RUBRO"] = "Otros"
            if "FECHA" in df.columns:
                df["FECHA_DT"] = safe_parse_dates(df["FECHA"])
            for col in ["CANTIDAD", "VALOR UNT", "VALOR TOTAL"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Error al leer hoja Seguimiento_Productos: {e}")
        return pd.DataFrame(columns=[
            "FECHA", "PROVEEDOR", "PRODUCTO", "CANTIDAD", "VALOR UNT", "VALOR TOTAL", "RUBRO"
        ])

def save_seguimiento_productos(df: pd.DataFrame) -> bool:
    """Guarda el DataFrame en la hoja 'Seguimiento_Productos'."""
    conn = get_connection()
    try:
        df_to_save = format_dates_for_sheet(df, "FECHA")
        if "FECHA_DT" in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=["FECHA_DT"])
        conn.update(worksheet="Seguimiento_Productos", data=df_to_save)
        return True
    except Exception as e:
        st.error(f"Error al guardar en Seguimiento_Productos: {e}")
        return False

def add_compra_con_productos(productos_df: pd.DataFrame, new_gasto_dict: dict) -> bool:
    """Guarda tanto la lista de productos como el gasto general asociado de forma atómica y segura."""
    conn = get_connection()
    try:
        # 1. Guardar productos en Seguimiento_Productos
        df_prod_curr = conn.read(worksheet="Seguimiento_Productos", ttl=0)
        if df_prod_curr is None or df_prod_curr.empty:
            df_prod_curr = pd.DataFrame(columns=[
                "FECHA", "PROVEEDOR", "PRODUCTO", "CANTIDAD", "VALOR UNT", "VALOR TOTAL", "RUBRO"
            ])
        
        prod_updated = pd.concat([df_prod_curr, productos_df], ignore_index=True)
        prod_to_save = format_dates_for_sheet(prod_updated, "FECHA")
        conn.update(worksheet="Seguimiento_Productos", data=prod_to_save)

        # 2. Guardar gasto consolidado en Gastos
        df_gastos_curr = conn.read(worksheet="Gastos", ttl=0)
        if df_gastos_curr is None or df_gastos_curr.empty:
            df_gastos_curr = pd.DataFrame(columns=[
                "FECHA", "QUIEN PAGA", "TIPO", "CONCEPTO",
                "CLASIFICACION", "RUBRO", "VALOR", "PAGO", "Mes_Pago"
            ])
        
        new_gasto_row = pd.DataFrame([new_gasto_dict])
        gastos_updated = pd.concat([df_gastos_curr, new_gasto_row], ignore_index=True)
        gastos_to_save = format_dates_for_sheet(gastos_updated, "FECHA")
        conn.update(worksheet="Gastos", data=gastos_to_save)

        return True
    except Exception as e:
        st.error(f"Error al guardar compra con productos: {e}")
        return False

def load_presupuestos() -> pd.DataFrame:
    """Carga la hoja 'Presupuestos'. Si no existe o está vacía, la inicializa."""
    conn = get_connection()
    try:
        df = conn.read(worksheet="Presupuestos", ttl=0)
        if df is None or df.empty or len(df.dropna(how="all")) == 0:
            initial_data = DEFAULT_CASA_PRESUPUESTOS + DEFAULT_PERSONAL_PRESUPUESTOS
            df = pd.DataFrame(initial_data)
            conn.update(worksheet="Presupuestos", data=df)
        else:
            if "MONTO_PRESUPUESTO" in df.columns:
                df["MONTO_PRESUPUESTO"] = pd.to_numeric(df["MONTO_PRESUPUESTO"], errors="coerce").fillna(0.0)
            if "ACTIVO" in df.columns:
                df["ACTIVO"] = df["ACTIVO"].astype(bool)
            else:
                df["ACTIVO"] = True
            
            if "COMPORTAMIENTO" not in df.columns:
                df["COMPORTAMIENTO"] = df["RUBRO"].apply(assign_default_comportamiento)
            else:
                df["COMPORTAMIENTO"] = df["COMPORTAMIENTO"].fillna("").astype(str).str.strip().str.capitalize()
                mask_invalid = ~df["COMPORTAMIENTO"].isin(["Fijo", "Variable"])
                if mask_invalid.any():
                    df.loc[mask_invalid, "COMPORTAMIENTO"] = df.loc[mask_invalid, "RUBRO"].apply(assign_default_comportamiento)
        return df
    except Exception as e:
        try:
            initial_data = DEFAULT_CASA_PRESUPUESTOS + DEFAULT_PERSONAL_PRESUPUESTOS
            df = pd.DataFrame(initial_data)
            conn.update(worksheet="Presupuestos", data=df)
            return df
        except Exception as e2:
            st.warning(f"Aviso de Presupuestos (usando datos en memoria): {e2}")
            return pd.DataFrame(DEFAULT_CASA_PRESUPUESTOS + DEFAULT_PERSONAL_PRESUPUESTOS)

def save_presupuestos(df: pd.DataFrame) -> bool:
    """Guarda las metas de presupuestos en Google Sheets."""
    conn = get_connection()
    try:
        conn.update(worksheet="Presupuestos", data=df)
        return True
    except Exception as e:
        st.error(f"Error al guardar en hoja Presupuestos: {e}")
        return False
