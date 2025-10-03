import streamlit as st

ADMIN_EMAILS = ["edisonportillal@gmail.com", "edisonportillaluna@gmail.com"]

st.set_page_config(
    page_title="Seguimiento Gastos Personales",
    page_icon=":dollar:",
    layout="wide")

def login_screen():
    st.header(" Seguimiento a Gastos Personales.")
    st.subheader("Por favor, inicia sesión.")
    st.button("Log in with Google", on_click=st.login)

if not st.user.is_logged_in:
    #pg = st.navigation([st.Page(login_screen)])
    login_screen()
    st.stop()

else:
    if st.user.email in ADMIN_EMAILS:
        st.session_state.role = "admin"
    else:
        st.session_state.role = "user"

    st.sidebar.header(f"Bienvenido, {st.user.name}!")
    st.sidebar.button("Cerrar sesión", on_click=st.logout)

    gastos = st.Page("pages/gastos_info.py", title="Gastos Generales")
    solo_lectura = st.Page("pages/solo_lectura_info.py", title="Solo Lectura")

    admon_pages = [gastos, solo_lectura]
    user_pages = [solo_lectura]

    page_dict = admon_pages if st.session_state.role == "admin" else user_pages
    pg = st.navigation(page_dict)

pg.run()