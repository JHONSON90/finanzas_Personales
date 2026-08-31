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
    st.button("🔑 Iniciar sesión con Google", on_click=st.login, type="primary")

def logout_screen():
    st.header("Cerrar Sesión")
    st.button("👋 Cerrar sesión", on_click=st.logout, type="secondary")

# Definir páginas con st.Page
p_dashboard = st.Page("pages/1_dashboard_gastos.py", title="Dashboard y Gastos", icon="📊", default=True)
p_presupuesto = st.Page("pages/2_presupuestos_metas.py", title="Presupuestos y Metas", icon="🎯")
p_productos = st.Page("pages/3_precios_productos.py", title="Precios y Productos", icon="🛒")

login_page = st.Page(login_screen, title="Iniciar Sesión", icon="🔐")
logout_page = st.Page(logout_screen, title="Cerrar Sesión", icon="🚪")

# Manejo de navegación
# Si estamos en entorno autenticado de Streamlit Cloud:
if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
    st.sidebar.markdown(f"### 👋 Bienvenido, **{st.user.name or get_current_user()}**")
    st.sidebar.caption(f"Email: `{st.user.email}`")
    st.sidebar.button("Cerrar sesión", on_click=st.logout, key="btn_logout_sidebar")
    
    pages = [p_dashboard, p_presupuesto, p_productos, logout_page]
    pg = st.navigation(pages)
else:
    # Entorno local / desarrollo o acceso sin autenticación estricta:
    # Mostramos las 3 páginas directamente con el selector de usuario simulado en sidebar
    pages = [p_dashboard, p_presupuesto, p_productos]
    pg = st.navigation(pages)

pg.run()
