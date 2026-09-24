
import streamlit as st

from db.models import register_user, verify_user

st.set_page_config(page_title="Profilo",  layout="wide")

st.markdown(
    "<style>[data-testid='stStatusWidget'] {visibility: hidden;}</style>",
    unsafe_allow_html=True,
)
st.title("Profile")

user = st.session_state.get("user")

if user:
    st.success(f"Hi **{user['username']}**.")
    if st.button("Log out"):
        st.session_state.user = None
        st.rerun()
else:
    tab_login, tab_register = st.tabs(["Login in", "Sign in"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                logged_user = verify_user(username, password)
                if logged_user:
                    st.session_state.user = logged_user
                    st.success("You are logged in!")
                    st.rerun()
                else:
                    st.error("Wrong username or password.")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("Insert username")
            new_password = st.text_input("Insert password", type="password")
            if st.form_submit_button("Sign in"):
                ok, message = register_user(new_username, new_password)
                if ok:
                    st.success(message)
                else:
                    st.error(message)
