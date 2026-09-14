import sys
import importlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Recargar servicios dinámicamente para evitar caché desactualizado en memoria en Streamlit Cloud
for mod_name in ["services.budget_service", "services.data_service", "services.auth_service"]:
    if mod_name in sys.modules:
        try:
            importlib.reload(sys.modules[mod_name])
        except Exception:
            pass

import streamlit as st
from services.auth_service import get_current_user, ADMIN_EMAILS

st.set_page_config(
    page_title="Seguimiento de Gastos y Presupuestos",
    page_icon="💰",
    layout="wide"
)

def login_screen():
    st.header("💰 Seguimiento a Gastos y Presupuestos")
    st.subheader("Por favor, inicia sesión con tu cuenta de Google.")
    st.write("Debes identificarte con un correo autorizado para acceder a tus presupuestos y gastos.")
    st.button("🔑 Iniciar sesión con Google", on_click=st.login, type="primary")

def logout_screen():
    st.header("Cerrar Sesión")
    st.button("👋 Cerrar sesión", on_click=st.logout, type="secondary")

def unauthorized_screen():
    st.error("⛔ Acceso no autorizado")
    email = getattr(st.user, "email", "desconocido")
    st.write(f"La cuenta **{email}** no se encuentra registrada en el sistema de usuarios autorizados.")
    st.button("Cerrar sesión e intentar con otra cuenta", on_click=st.logout)

# Definir páginas con st.Page
p_dashboard = st.Page("pages/1_dashboard_gastos.py", title="Dashboard y Gastos", icon="📊", default=True)
p_presupuesto = st.Page("pages/2_presupuestos_metas.py", title="Presupuestos y Metas", icon="🎯")
p_productos = st.Page("pages/3_precios_productos.py", title="Precios y Productos", icon="🛒")
p_anual = st.Page("pages/4_seguimiento_anual.py", title="Seguimiento Anual", icon="📈")

login_page = st.Page(login_screen, title="Iniciar Sesión", icon="🔐")
logout_page = st.Page(logout_screen, title="Cerrar Sesión", icon="🚪")
unauth_page = st.Page(unauthorized_screen, title="No Autorizado", icon="⛔")

# Manejo de navegación
if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
    email = getattr(st.user, "email", "").lower().strip()
    if email in ADMIN_EMAILS:
        current_user = get_current_user()
        st.sidebar.markdown(f"### 👋 Bienvenido, **{st.user.name or current_user}**")
        st.sidebar.caption(f"Usuario: `{current_user}` | Email: `{email}`")
        st.sidebar.button("Cerrar sesión", on_click=st.logout, key="btn_logout_sidebar")
        
        pages = [p_dashboard, p_presupuesto, p_productos, p_anual, logout_page]
        pg = st.navigation(pages)
    else:
        pg = st.navigation([unauth_page, logout_page])
else:
    # No hay sesión iniciada -> Exclusivamente mostrar pantalla de login
    pg = st.navigation([login_page])

pg.run()
