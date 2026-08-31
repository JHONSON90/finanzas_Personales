import streamlit as st
import pandas as pd
import time

from services.auth_service import get_current_user
from services.data_service import load_presupuestos, save_presupuestos

st.set_page_config(
    page_title="Presupuestos y Metas | Finanzas",
    page_icon="🎯",
    layout="wide"
)

# 1. Identificar usuario
current_user = get_current_user()

st.title("🎯 Gestión de Presupuestos y Metas")
st.caption(f"Configura y ajusta los techos presupuestales mensuales para la **Casa** y tus gastos **Personales ({current_user})**.")

# 2. Cargar datos de presupuestos
df_presupuestos = load_presupuestos()

# Separar presupuestos de Casa y Personales del usuario activo
df_casa = df_presupuestos[df_presupuestos["TIPO"].str.lower() == "casa"].copy()
df_personal = df_presupuestos[
    (df_presupuestos["TIPO"].str.lower() == "personal") &
    (df_presupuestos["USUARIO"].str.lower() == current_user.lower())
].copy()

tab1, tab2, tab3 = st.tabs(["🏠 Presupuestos de Casa", f"👤 Mis Presupuestos Personales ({current_user})", "➕ Crear Nuevo Rubro"])

# --- TAB 1: PRESUPUESTOS DE CASA ---
with tab1:
    st.subheader("🏠 Metas Presupuestales del Hogar")
    st.caption("Estos rubros y montos aplican a los gastos compartidos de la casa.")

    if not df_casa.empty:
        total_presup_casa = df_casa[df_casa["ACTIVO"] == True]["MONTO_PRESUPUESTO"].sum()
        st.metric("Total Presupuesto Mensual Casa", f"${total_presup_casa:,.0f}", border=True)

        st.markdown("##### ✏️ Edita los montos directamente en la tabla:")
        casa_edited = st.data_editor(
            df_casa[["RUBRO", "MONTO_PRESUPUESTO", "ACTIVO"]],
            num_rows="dynamic",
            width="stretch",
            key="editor_casa",
            column_config={
                "RUBRO": st.column_config.TextColumn("Rubro", required=True),
                "MONTO_PRESUPUESTO": st.column_config.NumberColumn("Monto Mensual ($)", format="$%d", min_value=0.0, step=10000.0, required=True),
                "ACTIVO": st.column_config.CheckboxColumn("Activo", default=True)
            }
        )

        if st.button("💾 Guardar Cambios en Presupuesto de Casa", type="primary"):
            # Reconstruir dataframe general
            casa_edited["TIPO"] = "Casa"
            casa_edited["USUARIO"] = "Todos"
            
            # Mantener los otros presupuestos (personales de todos)
            df_otros = df_presupuestos[df_presupuestos["TIPO"].str.lower() != "casa"]
            df_nuevo_total = pd.concat([casa_edited, df_otros], ignore_index=True)
            
            if save_presupuestos(df_nuevo_total):
                st.success("✅ ¡Presupuestos de Casa actualizados exitosamente en Google Sheets!")
                time.sleep(1)
                st.rerun()
    else:
        st.info("No hay presupuestos de casa registrados.")

# --- TAB 2: PRESUPUESTOS PERSONALES ---
with tab2:
    st.subheader(f"👤 Metas Personales de {current_user}")
    st.caption(f"Tus rubros y presupuestos individuales. Diana solo puede ver y editar los suyos, y Edison los propios.")

    total_presup_personal = df_personal[df_personal["ACTIVO"] == True]["MONTO_PRESUPUESTO"].sum() if not df_personal.empty else 0.0
    st.metric(f"Total Presupuesto Personal ({current_user})", f"${total_presup_personal:,.0f}", border=True)

    st.markdown("##### ✏️ Edita tus montos personales:")
    personal_edited = st.data_editor(
        df_personal[["RUBRO", "MONTO_PRESUPUESTO", "ACTIVO"]],
        num_rows="dynamic",
        width="stretch",
        key="editor_personal",
        column_config={
            "RUBRO": st.column_config.TextColumn("Rubro Personal", required=True),
            "MONTO_PRESUPUESTO": st.column_config.NumberColumn("Monto Mensual ($)", format="$%d", min_value=0.0, step=10000.0, required=True),
            "ACTIVO": st.column_config.CheckboxColumn("Activo", default=True)
        }
    )

    if st.button("💾 Guardar Mis Presupuestos Personales", type="primary"):
        personal_edited["TIPO"] = "Personal"
        personal_edited["USUARIO"] = current_user
        
        # Mantener todos los demás (Casa y personales del otro usuario)
        df_resto = df_presupuestos[
            ~((df_presupuestos["TIPO"].str.lower() == "personal") & 
              (df_presupuestos["USUARIO"].str.lower() == current_user.lower()))
        ]
        df_nuevo_total = pd.concat([df_resto, personal_edited], ignore_index=True)
        
        if save_presupuestos(df_nuevo_total):
            st.success(f"✅ ¡Presupuestos personales de {current_user} actualizados!")
            time.sleep(1)
            st.rerun()

# --- TAB 3: CREAR NUEVO RUBRO ---
with tab3:
    st.subheader("➕ Agregar Nuevo Rubro Presupuestal")
    col1, col2 = st.columns(2)
    with col1:
        tipo_nuevo = st.radio("¿Para quién es el rubro?", ["Personal", "Casa"])
        nombre_rubro = st.text_input("Nombre del Rubro", placeholder="Ej. Créditos hipotecarios, Meta de ahorro, Gimnasio")
    with col2:
        monto_nuevo = st.number_input("Monto de Presupuesto Inicial ($)", min_value=0.0, step=10000.0, format="%.2f")
        usuario_asignado = current_user if tipo_nuevo == "Personal" else "Todos"
        st.info(f"📌 Asignado a: **{usuario_asignado}** ({tipo_nuevo})")

    if st.button("✨ Crear y Guardar Rubro", type="primary"):
        if not nombre_rubro.strip():
            st.error("Por favor ingresa un nombre para el rubro.")
        else:
            # Validar que no exista duplicado
            nombre_limpio = nombre_rubro.strip()
            df_curr = load_presupuestos()
            existe = df_curr[
                (df_curr["RUBRO"].str.lower() == nombre_limpio.lower()) &
                (df_curr["TIPO"].str.lower() == tipo_nuevo.lower()) &
                (df_curr["USUARIO"].str.lower() == usuario_asignado.lower())
            ]
            if not existe.empty:
                st.warning(f"Ya existe un rubro '{nombre_limpio}' para {usuario_asignado}.")
            else:
                nuevo_registro = pd.DataFrame([{
                    "RUBRO": nombre_limpio,
                    "TIPO": tipo_nuevo,
                    "USUARIO": usuario_asignado,
                    "MONTO_PRESUPUESTO": float(monto_nuevo),
                    "ACTIVO": True
                }])
                df_actualizado = pd.concat([df_curr, nuevo_registro], ignore_index=True)
                if save_presupuestos(df_actualizado):
                    st.success(f"✅ ¡Rubro '{nombre_limpio}' agregado exitosamente!")
                    time.sleep(1.2)
                    st.rerun()
