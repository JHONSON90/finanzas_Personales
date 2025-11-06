import streamlit as st
import time


ADMIN_EMAILS = ["edisonportillal@gmail.com", "edisonportillaluna@gmail.com"]

st.set_page_config(
    page_title="Seguimiento Gastos Personales",
    page_icon=":dollar:",
    layout="wide")

def login_screen():
    st.header(" Seguimiento a Gastos Personales.")
    st.subheader("Por favor, inicia sesión.")
    st.button("Log in with Google", on_click=st.login)

def logout():
    st.button("Cerrar sesión", on_click=st.logout)

login_page = st.Page(login_screen, title="Login", icon=":material/login:")
logout_page = st.Page(logout, title="Logout", icon=":material/logout:")

gastos = st.Page("pages/gastos_info.py", title="Gastos Generales")
solo_lectura = st.Page("pages/solo_lectura_info.py", title="Solo Lectura")
gastos_flia = st.Page("pages/gatos_flia_Portilla.py", title="Gastos Familia Portilla")
seguimiento_productos = st.Page("pages/seguimiento_productos.py", title="Seguimiento a Productos")

if st.user.is_logged_in:
    if st.user.email in ADMIN_EMAILS:
        st.sidebar.header(f"Bienvenido, {st.user.name}!")
        st.sidebar.button("Cerrar sesión", on_click=st.logout)

        logout_page = st.Page(logout, title="Logout", icon=":material/logout:")
        pages = [gastos, gastos_flia, seguimiento_productos, logout_page]
    else:
        st.sidebar.header(f"Bienvenido, {st.user.name}!")
        st.sidebar.button("Cerrar sesión", on_click=st.logout)
        logout_page = st.Page(logout, title="Logout", icon=":material/logout:")
        pages = [gastos_flia, seguimiento_productos, logout_page]
    pg = st.navigation(pages)
else:
    pg = st.navigation([login_page])
pg.run()

# if not st.user.is_logged_in:
#     #pg = st.navigation([st.Page(login_screen)])
#     login_screen()
#     st.stop()

# else:
#     if st.user.email in ADMIN_EMAILS:
#         st.session_state.role = "admin"
#     else:
#         st.session_state.role = "user"

#     st.sidebar.header(f"Bienvenido, {st.user.name}!")
#     st.sidebar.button("Cerrar sesión", on_click=st.logout)

#     # admon_pages = [gastos]
#     # user_pages = [solo_lectura]

#     #page_dict = admon_pages if st.session_state.role == "admin" else user_pages

#     if st.session_state.role == "admin":
#         page_dict = [gastos]
#     else:
#         page_dict = [solo_lectura]
#     pg = st.navigation(page_dict)
#     pg.run()


# def login_screen():
#     st.header(" Seguimiento a Gastos Personales.")
#     st.subheader("Por favor, inicia sesión.")
#     st.button("Log in with Google", on_click=st.login)

# def logout():
#     st.button("Cerrar sesión", on_click=st.logout)

# login_page = st.Page(login_screen, title="Login", icon=":material/login:")
# logout_page = st.Page(logout, title="Logout", icon=":material/logout:")

# gastos_page = st.Page("pages/gastos_info.py", title="Gastos Generales", icon=":material/attach_money:")
# solo_lectura_page = st.Page("pages/solo_lectura_info.py", title="Solo Lectura", icon=":material/visibility_off:")


# if st.user.is_logged_in:
#     if st.user.email in ADMIN_EMAILS:
#        pages = [gastos_page, logout_page]
#     else:
#         pages = [solo_lectura_page, logout_page]
#     pg = st.navigation(pages)
# else:
#     pg = st.navigation([login_page])
# pg.run()

