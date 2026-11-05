import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import traceback
from typing import Optional, List, Dict, Any, Tuple

def assign_default_comportamiento(rubro: str) -> str:
    """Asigna comportamiento Fijo o Variable por defecto según palabras clave del rubro."""
    r = str(rubro).lower().strip()
    fixed_keywords = [
        "arriendo", "servicio", "jardín", "jardin", "hipotecario", "ahorro",
        "crédito", "credito", "seguro", "colegio", "administración", "administracion",
        "pensión", "pension", "vigilancia", "internet", "gas", "luz", "agua",
        "coacremat", "parqueadero", "viajes", "despensa", "aseo", "ipiales"
    ]
    for kw in fixed_keywords:
        if kw in r:
            return "Fijo"
    return "Variable"

# Catálogo centralizado y tipado de gastos estipulados por usuario
CATALOGO_PAGOS_ESTIPULADOS: List[Dict[str, Any]] = [
    # --- Edison ---
    {
        "id": "edison_servicio_domestico",
        "responsable": "Edison",
        "tipo": "Casa",
        "rubro": "Servicio doméstico",
        "clasificacion": "Servicios",
        "monto_base": 900000.0,
        "concepto_base": "Pago de servicio doméstico"
    },
    {
        "id": "edison_arriendo",
        "responsable": "Edison",
        "tipo": "Casa",
        "rubro": "Arriendo",
        "clasificacion": "Arriendo",
        "monto_base": 850000.0,
        "concepto_base": "Pago de arriendo mensual"
    },
    {
        "id": "edison_productos_aseo",
        "responsable": "Edison",
        "tipo": "Casa",
        "rubro": "Productos de aseo",
        "clasificacion": "Aseo",
        "monto_base": 500000.0,
        "concepto_base": "Compra de productos de aseo"
    },
    {
        "id": "edison_mercado_despensa",
        "responsable": "Edison",
        "tipo": "Casa",
        "rubro": "Mercado y despensa",
        "clasificacion": "Alimentos",
        "monto_base": 400000.0,
        "concepto_base": "Mercado y despensa mensual"
    },
    {
        "id": "edison_vigilancia_casa",
        "responsable": "Edison",
        "tipo": "Casa",
        "rubro": "Vigilancia casa",
        "clasificacion": "Servicios",
        "monto_base": 50000.0,
        "concepto_base": "Pago vigilancia casa"
    },
    {
        "id": "edison_creditos_casa_ipiales",
        "responsable": "Edison",
        "tipo": "Personal",
        "rubro": "Créditos de la casa Ipiales",
        "clasificacion": "Casa",
        "monto_base": 1480000.0,
        "concepto_base": "Pago crédito casa Ipiales"
    },

    # --- Diana ---
    {
        "id": "diana_coacremat_alejo",
        "responsable": "Diana",
        "tipo": "Personal",
        "rubro": "Coacremat Alejo",
        "clasificacion": "Educación",
        "monto_base": 135000.0,
        "concepto_base": "Pago Coacremat Alejo"
    },
    {
        "id": "diana_coacremat_mathi",
        "responsable": "Diana",
        "tipo": "Personal",
        "rubro": "Coacremat Mathi",
        "clasificacion": "Educación",
        "monto_base": 130000.0,
        "concepto_base": "Pago Coacremat Mathi"
    },
    {
        "id": "diana_coacremat_diana",
        "responsable": "Diana",
        "tipo": "Personal",
        "rubro": "Coacremat Diana",
        "clasificacion": "Otros",
        "monto_base": 100000.0,
        "concepto_base": "Aporte Coacremat Diana"
    },
    {
        "id": "diana_credito_banco_agrario",
        "responsable": "Diana",
        "tipo": "Personal",
        "rubro": "Crédito Banco Agrario",
        "clasificacion": "Crédito",
        "monto_base": 500000.0,
        "concepto_base": "Cuota Crédito Banco Agrario"
    },
    {
        "id": "diana_admin_apto",
        "responsable": "Diana",
        "tipo": "Personal",
        "rubro": "Administración apartamento Diana",
        "clasificacion": "Casa",
        "monto_base": 153000.0,
        "concepto_base": "Pago administración apartamento Diana"
    },
    {
        "id": "diana_circulo_viajes",
        "responsable": "Diana",
        "tipo": "Personal",
        "rubro": "Círculo de Viajes",
        "clasificacion": "Otros",
        "monto_base": 371000.0,
        "concepto_base": "Cuota Círculo de Viajes"
    },
    {
        "id": "diana_jardin_ninos",
        "responsable": "Diana",
        "tipo": "Casa",
        "rubro": "Jardín niños",
        "clasificacion": "Educación",
        "monto_base": 500000.0,
        "concepto_base": "Mensualidad Jardín niños"
    },
    {
        "id": "diana_servicios_luz",
        "responsable": "Diana",
        "tipo": "Casa",
        "rubro": "Servicios Luz",
        "clasificacion": "Servicios",
        "monto_base": 135000.0,
        "concepto_base": "Factura Servicios Luz"
    },
    {
        "id": "diana_servicio_agua",
        "responsable": "Diana",
        "tipo": "Casa",
        "rubro": "Servicio Agua",
        "clasificacion": "Servicios",
        "monto_base": 160000.0,
        "concepto_base": "Factura Servicio Agua"
    },
    {
        "id": "diana_internet",
        "responsable": "Diana",
        "tipo": "Casa",
        "rubro": "Internet",
        "clasificacion": "Servicios",
        "monto_base": 110000.0,
        "concepto_base": "Factura Internet"
    },
    {
        "id": "diana_gas",
        "responsable": "Diana",
        "tipo": "Casa",
        "rubro": "Gas",
        "clasificacion": "Servicios",
        "monto_base": 80000.0,
        "concepto_base": "Factura Gas"
    },
    {
        "id": "diana_credito_carro",
        "responsable": "Diana",
        "tipo": "Personal",
        "rubro": "Crédito Carro",
        "clasificacion": "Transporte",
        "monto_base": 1036000.0,
        "concepto_base": "Cuota Crédito Carro"
    },
    {
        "id": "diana_parqueadero",
        "responsable": "Diana",
        "tipo": "Personal",
        "rubro": "Parqueadero",
        "clasificacion": "Transporte",
        "monto_base": 150000.0,
        "concepto_base": "Pago Parqueadero mensual"
    }
]

DEFAULT_CASA_PRESUPUESTOS = [
    {"RUBRO": "Arriendo", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 850000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Servicio doméstico", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 900000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Productos de aseo", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 500000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Mercado y despensa", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 400000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Vigilancia casa", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 50000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Jardín niños", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 500000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Servicios Luz", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 135000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Servicio Agua", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 160000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Internet", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 110000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Gas", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 80000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Gastos niños (Pañales etc)", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 600000.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Transporte local", "TIPO": "Casa", "USUARIO": "Todos", "MONTO_PRESUPUESTO": 25000.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
]

DEFAULT_PERSONAL_PRESUPUESTOS = [
    # Edison
    {"RUBRO": "Créditos de la casa Ipiales", "TIPO": "Personal", "USUARIO": "Edison", "MONTO_PRESUPUESTO": 1480000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Crédito hipotecario", "TIPO": "Personal", "USUARIO": "Edison", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Antojos y snacks", "TIPO": "Personal", "USUARIO": "Edison", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Meta de ahorro", "TIPO": "Personal", "USUARIO": "Edison", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},

    # Diana
    {"RUBRO": "Coacremat Alejo", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 135000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Coacremat Mathi", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 130000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Coacremat Diana", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 100000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Crédito Banco Agrario", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 500000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Administración apartamento Diana", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 153000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Círculo de Viajes", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 371000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Crédito Carro", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 1036000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Parqueadero", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 150000.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Crédito hipotecario", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
    {"RUBRO": "Antojos y snacks", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Variable"},
    {"RUBRO": "Meta de ahorro", "TIPO": "Personal", "USUARIO": "Diana", "MONTO_PRESUPUESTO": 0.0, "ACTIVO": True, "COMPORTAMIENTO": "Fijo"},
]

def get_connection():
    """Obtiene la conexión GSheetsConnection de Streamlit."""
    return st.connection("gsheets", type=GSheetsConnection)

def safe_parse_dates(series: pd.Series) -> pd.Series:
    """
    Parsea fechas soportando múltiples formatos (YYYY-MM-DD, DD/MM/YYYY, etc.)
    priorizando YYYY-MM-DD e interpretando DD/MM/YYYY si contiene barras.
    """
    if series.empty:
        return series

    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    s_clean = series.astype(str).str.strip().replace(["nan", "None", "NaT", ""], pd.NA)

    # 1. Intentar formato ISO estándar YYYY-MM-DD primero (prioridad máxima)
    parsed_iso = pd.to_datetime(s_clean, format="%Y-%m-%d", errors="coerce")

    # 2. Para las celdas que fallaron (ej. con barras 10/09/2026), intentar DD/MM/YYYY
    mask_na = parsed_iso.isna() & s_clean.notna()
    if mask_na.any():
        parsed_latam = pd.to_datetime(s_clean[mask_na], format="%d/%m/%Y", errors="coerce")
        parsed_iso = parsed_iso.combine_first(parsed_latam)

    # 3. Fallback con format='mixed' y dayfirst=True
    mask_still_na = parsed_iso.isna() & s_clean.notna()
    if mask_still_na.any():
        parsed_mixed = pd.to_datetime(s_clean[mask_still_na], format="mixed", dayfirst=True, errors="coerce")
        parsed_iso = parsed_iso.combine_first(parsed_mixed)

    return parsed_iso

def normalize_date_column(series: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """
    Normaliza una columna de fechas en:
    1. FECHA: string estrictamente formateado como 'YYYY-MM-DD'
    2. FECHA_DT: pd.Series con datetime64 para ordenamiento y filtros numéricos
    """
    dt_series = safe_parse_dates(series)
    str_series = dt_series.dt.strftime("%Y-%m-%d")
    
    # Si alguna fila no pudo ser parseada pero tenía texto original, conservarlo limpio
    str_clean = series.astype(str).str.strip().replace(["nan", "None", "NaT"], "")
    str_series = str_series.fillna(str_clean)
    return str_series, dt_series

def format_dates_for_sheet(df: pd.DataFrame, col_name: str = "FECHA") -> pd.DataFrame:
    """Garantiza que toda la columna de fechas se guarde estrictamente como string YYYY-MM-DD."""
    df_out = df.copy()
    if col_name in df_out.columns:
        str_dates, _ = normalize_date_column(df_out[col_name])
        df_out[col_name] = str_dates
    return df_out

def load_gastos() -> pd.DataFrame:
    """Carga los datos de la hoja 'Gastos' normalizando FECHA siempre a YYYY-MM-DD."""
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
                # Normalizar FECHA estrictamente a formato YYYY-MM-DD y generar FECHA_DT
                df["FECHA"], df["FECHA_DT"] = normalize_date_column(df["FECHA"])
        return df
    except Exception as e:
        st.error(f"Error al leer hoja Gastos: {e}")
        return pd.DataFrame(columns=[
            "FECHA", "QUIEN PAGA", "TIPO", "CONCEPTO",
            "CLASIFICACION", "RUBRO", "VALOR", "PAGO", "Mes_Pago"
        ])

def save_gastos(df: pd.DataFrame) -> bool:
    """Guarda el DataFrame en la hoja 'Gastos' con fechas estandarizadas en YYYY-MM-DD."""
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
    """Lee la hoja Gastos fresca, agrega el nuevo gasto con formato YYYY-MM-DD estricto y guarda."""
    conn = get_connection()
    try:
        df_current = conn.read(worksheet="Gastos", ttl=0)
        if df_current is None or df_current.empty:
            df_current = pd.DataFrame(columns=[
                "FECHA", "QUIEN PAGA", "TIPO", "CONCEPTO",
                "CLASIFICACION", "RUBRO", "VALOR", "PAGO", "Mes_Pago"
            ])
        
        # Forzar formato YYYY-MM-DD estricto en el nuevo gasto
        if "FECHA" in new_gasto_dict:
            parsed_single = safe_parse_dates(pd.Series([new_gasto_dict["FECHA"]]))
            if not parsed_single.empty and pd.notnull(parsed_single.iloc[0]):
                new_gasto_dict["FECHA"] = parsed_single.iloc[0].strftime("%Y-%m-%d")
        
        # Formatear la nueva fila y concatenar
        new_row = pd.DataFrame([new_gasto_dict])
        df_updated = pd.concat([df_current, new_row], ignore_index=True)
        
        # Estandarizar toda la hoja completa antes de guardar para unificar datos viejos y nuevos
        df_to_save = format_dates_for_sheet(df_updated, "FECHA")
        if "FECHA_DT" in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=["FECHA_DT"])
        conn.update(worksheet="Gastos", data=df_to_save)
        return True
    except Exception as e:
        st.error(f"Error al agregar gasto: {e}")
        return False

def add_batch_gastos(new_gastos_list: List[Dict[str, Any]]) -> bool:
    """
    Inserta atómicamente una lista de gastos en una sola llamada a Google Sheets,
    asegurando formato estricto YYYY-MM-DD en fechas y consistencia de tipos.
    """
    if not new_gastos_list:
        return True

    conn = get_connection()
    try:
        df_current = conn.read(worksheet="Gastos", ttl=0)
        expected_cols = [
            "FECHA", "QUIEN PAGA", "TIPO", "CONCEPTO",
            "CLASIFICACION", "RUBRO", "VALOR", "PAGO", "Mes_Pago"
        ]
        if df_current is None or df_current.empty:
            df_current = pd.DataFrame(columns=expected_cols)

        # Preparar y normalizar cada gasto
        processed_gastos = []
        for g in new_gastos_list:
            item = dict(g)
            # Asegurar fecha en YYYY-MM-DD
            if "FECHA" in item and item["FECHA"]:
                parsed_single = safe_parse_dates(pd.Series([item["FECHA"]]))
                if not parsed_single.empty and pd.notnull(parsed_single.iloc[0]):
                    item["FECHA"] = parsed_single.iloc[0].strftime("%Y-%m-%d")
                else:
                    item["FECHA"] = str(item["FECHA"]).strip()
            
            # Asegurar VALOR numérico
            if "VALOR" in item:
                try:
                    item["VALOR"] = float(item["VALOR"])
                except (ValueError, TypeError):
                    item["VALOR"] = 0.0

            # Asegurar PAGO booleano
            if "PAGO" in item:
                item["PAGO"] = bool(item["PAGO"])
            else:
                item["PAGO"] = False

            if "Mes_Pago" not in item:
                item["Mes_Pago"] = ""

            processed_gastos.append(item)

        df_new_rows = pd.DataFrame(processed_gastos)
        df_updated = pd.concat([df_current, df_new_rows], ignore_index=True)

        # Estandarizar toda la hoja completa antes de guardar para asegurar consistencia
        df_to_save = format_dates_for_sheet(df_updated, "FECHA")
        if "FECHA_DT" in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=["FECHA_DT"])

        conn.update(worksheet="Gastos", data=df_to_save)
        return True
    except Exception as e:
        st.error(f"Error al guardar lote de gastos: {e}")
        return False

def load_seguimiento_productos() -> pd.DataFrame:
    """Carga los datos de la hoja 'Seguimiento_Productos' normalizando FECHA a YYYY-MM-DD."""
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
                df["FECHA"], df["FECHA_DT"] = normalize_date_column(df["FECHA"])
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
    """Guarda el DataFrame en la hoja 'Seguimiento_Productos' con fechas en YYYY-MM-DD."""
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
    """Guarda tanto la lista de productos como el gasto general con formato YYYY-MM-DD estricto."""
    conn = get_connection()
    try:
        # Asegurar formato YYYY-MM-DD en new_gasto_dict
        if "FECHA" in new_gasto_dict:
            parsed_single = safe_parse_dates(pd.Series([new_gasto_dict["FECHA"]]))
            if not parsed_single.empty and pd.notnull(parsed_single.iloc[0]):
                new_gasto_dict["FECHA"] = parsed_single.iloc[0].strftime("%Y-%m-%d")

        # 1. Guardar productos en Seguimiento_Productos
        df_prod_curr = conn.read(worksheet="Seguimiento_Productos", ttl=0)
        if df_prod_curr is None or df_prod_curr.empty:
            df_prod_curr = pd.DataFrame(columns=[
                "FECHA", "PROVEEDOR", "PRODUCTO", "CANTIDAD", "VALOR UNT", "VALOR TOTAL", "RUBRO"
            ])
        
        prod_updated = pd.concat([df_prod_curr, productos_df], ignore_index=True)
        prod_to_save = format_dates_for_sheet(prod_updated, "FECHA")
        if "FECHA_DT" in prod_to_save.columns:
            prod_to_save = prod_to_save.drop(columns=["FECHA_DT"])
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
        if "FECHA_DT" in gastos_to_save.columns:
            gastos_to_save = gastos_to_save.drop(columns=["FECHA_DT"])
        conn.update(worksheet="Gastos", data=gastos_to_save)

        return True
    except Exception as e:
        st.error(f"Error al guardar compra con productos: {e}")
        return False

def ensure_stipulated_presupuestos(df_presupuestos: pd.DataFrame) -> pd.DataFrame:
    """
    Asegura que todos los rubros estipulados en CATALOGO_PAGOS_ESTIPULADOS existan
    en el DataFrame de Presupuestos. Si faltan, los inserta con sus valores y formato estipulado
    (RUBRO, TIPO, USUARIO, MONTO_PRESUPUESTO, ACTIVO, COMPORTAMIENTO).
    """
    expected_cols = ["RUBRO", "TIPO", "USUARIO", "MONTO_PRESUPUESTO", "ACTIVO", "COMPORTAMIENTO"]
    
    if df_presupuestos is None or df_presupuestos.empty:
        df = pd.DataFrame(DEFAULT_CASA_PRESUPUESTOS + DEFAULT_PERSONAL_PRESUPUESTOS)
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        return df[expected_cols]

    df = df_presupuestos.copy()
    for col in expected_cols:
        if col not in df.columns:
            if col == "ACTIVO":
                df[col] = True
            elif col == "MONTO_PRESUPUESTO":
                df[col] = 0.0
            elif col == "COMPORTAMIENTO":
                df[col] = "Fijo"
            elif col == "TIPO":
                df[col] = "Casa"
            elif col == "USUARIO":
                df[col] = "Todos"
            else:
                df[col] = ""

    # Normalizar valores para chequeo seguro de existencia
    tipo_series = df["TIPO"].fillna("").astype(str).str.strip().str.lower()
    rubro_series = df["RUBRO"].fillna("").astype(str).str.strip().str.lower()
    user_series = df["USUARIO"].fillna("").astype(str).str.strip().str.lower()

    # Construir un set de claves existentes
    # Para Casa: clave es 'casa|<rubro>'
    # Para Personal: clave es 'personal|<usuario>|<rubro>'
    existing_keys = set()
    for t, r, u in zip(tipo_series, rubro_series, user_series):
        if t == "casa":
            existing_keys.add(f"casa|{r}")
        else:
            existing_keys.add(f"personal|{u}|{r}")

    new_rows = []
    for item in CATALOGO_PAGOS_ESTIPULADOS:
        item_tipo = item["tipo"].strip()
        item_rubro = item["rubro"].strip()
        item_user = "Todos" if item_tipo.lower() == "casa" else item["responsable"].strip()
        
        if item_tipo.lower() == "casa":
            key = f"casa|{item_rubro.lower()}"
        else:
            key = f"personal|{item_user.lower()}|{item_rubro.lower()}"

        if key not in existing_keys:
            new_rows.append({
                "RUBRO": item_rubro,
                "TIPO": item_tipo,
                "USUARIO": item_user,
                "MONTO_PRESUPUESTO": float(item["monto_base"]),
                "ACTIVO": True,
                "COMPORTAMIENTO": "Fijo"
            })
            existing_keys.add(key)

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        df = pd.concat([df, df_new], ignore_index=True)

    # Tipado estricto
    df["MONTO_PRESUPUESTO"] = pd.to_numeric(df["MONTO_PRESUPUESTO"], errors="coerce").fillna(0.0)
    df["ACTIVO"] = df["ACTIVO"].astype(bool)
    df["COMPORTAMIENTO"] = df["COMPORTAMIENTO"].fillna("Fijo").astype(str).str.strip().str.capitalize()
    mask_invalid = ~df["COMPORTAMIENTO"].isin(["Fijo", "Variable"])
    if mask_invalid.any():
        df.loc[mask_invalid, "COMPORTAMIENTO"] = df.loc[mask_invalid, "RUBRO"].apply(assign_default_comportamiento)

    return df

def load_presupuestos() -> pd.DataFrame:
    """Carga la hoja 'Presupuestos'. Si no existe o está vacía, la inicializa."""
    conn = get_connection()
    try:
        df = conn.read(worksheet="Presupuestos", ttl=0)
        if df is None or df.empty or len(df.dropna(how="all")) == 0:
            initial_data = DEFAULT_CASA_PRESUPUESTOS + DEFAULT_PERSONAL_PRESUPUESTOS
            df = pd.DataFrame(initial_data)
            df = ensure_stipulated_presupuestos(df)
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

            # Sincronizar rubros estipulados faltantes
            filas_anteriores = len(df)
            df = ensure_stipulated_presupuestos(df)
            if len(df) > filas_anteriores:
                try:
                    conn.update(worksheet="Presupuestos", data=df)
                except Exception:
                    pass
        return df
    except Exception as e:
        try:
            initial_data = DEFAULT_CASA_PRESUPUESTOS + DEFAULT_PERSONAL_PRESUPUESTOS
            df = pd.DataFrame(initial_data)
            df = ensure_stipulated_presupuestos(df)
            conn.update(worksheet="Presupuestos", data=df)
            return df
        except Exception as e2:
            st.warning(f"Aviso de Presupuestos (usando datos en memoria): {e2}")
            return ensure_stipulated_presupuestos(pd.DataFrame(DEFAULT_CASA_PRESUPUESTOS + DEFAULT_PERSONAL_PRESUPUESTOS))

def save_presupuestos(df: pd.DataFrame) -> bool:
    """Guarda las metas de presupuestos en Google Sheets."""
    conn = get_connection()
    try:
        conn.update(worksheet="Presupuestos", data=df)
        return True
    except Exception as e:
        st.error(f"Error al guardar en hoja Presupuestos: {e}")
        return False

def get_unique_providers() -> list[str]:
    """
    Obtiene la lista consolidada de proveedores conocidos desde la hoja 'Seguimiento_Productos'
    y la combina con comercios habituales y entradas personalizadas en la sesión actual.
    """
    defaults = ["D1", "Éxito", "Alkosto", "Jumbo", "Olímpica", "Ara", "Carulla", "Farmatodo"]
    try:
        df_prod = load_seguimiento_productos()
        if not df_prod.empty and "PROVEEDOR" in df_prod.columns:
            cleaned = [
                str(p).strip()
                for p in df_prod["PROVEEDOR"].dropna().unique()
                if str(p).strip() and str(p).strip().lower() not in ["none", "nan", "varios", "null", "otro"]
            ]
            defaults.extend(cleaned)
    except Exception:
        pass

    if "custom_providers" in st.session_state and isinstance(st.session_state["custom_providers"], list):
        defaults.extend(st.session_state["custom_providers"])

    seen = {}
    for p in defaults:
        p_clean = p.strip()
        if p_clean and p_clean.lower() not in seen:
            seen[p_clean.lower()] = p_clean

    return sorted(list(seen.values()), key=lambda s: s.lower())
