import streamlit as st

# Mapeo de correos electrónicos a nombres de usuario
USER_EMAILS = {
    "edisonportillal@gmail.com": "Edison",
    "edisonportillaluna@gmail.com": "Edison",
    "dianatc0812@gmail.com": "Diana",
    "dianaportilla@gmail.com": "Diana",
    "dianaluna@gmail.com": "Diana",
}

ADMIN_EMAILS = [
    "edisonportillal@gmail.com",
    "edisonportillaluna@gmail.com",
    "dianatc0812@gmail.com",
    "dianaportilla@gmail.com",
    "dianaluna@gmail.com"
]

def get_current_user() -> str:
    """
    Retorna el usuario activo ('Edison' o 'Diana').
    Identifica automáticamente al usuario mediante Google OAuth (st.user).
    Si no hay sesión iniciada, asigna 'Edison' por defecto en desarrollo local.
    """
    if hasattr(st, "user") and st.user and getattr(st.user, "is_logged_in", False):
        email = getattr(st.user, "email", "").lower().strip()
        if email in USER_EMAILS:
            return USER_EMAILS[email]
        name = getattr(st.user, "name", "").lower()
        if "diana" in name:
            return "Diana"
        if "edison" in name:
            return "Edison"

    return "Edison"

def is_admin() -> bool:
    """Verifica si el usuario actual tiene rol de administrador."""
    if hasattr(st, "user") and st.user and getattr(st.user, "is_logged_in", False):
        email = getattr(st.user, "email", "").lower().strip()
        return email in ADMIN_EMAILS
    return True
