# home.py
import streamlit as st
import pandas as pd
import os
from uuid import uuid4
import jwt
import base64
from pathlib import Path

from helpers import (
    hide_sidebar,
    remove_st_branding,
    create_oauth_session,
    build_auth_url
)

# ---------------------------------------------
# Icon loading
# ---------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ICON_PATH = ASSETS_DIR / "page_icon.png"

# ---------------------------------------------
# Page Setup
# ---------------------------------------------
st.set_page_config(page_icon=ICON_PATH, layout="wide")
remove_st_branding()
hide_sidebar()

# Azure Credentials
azure = st.secrets["azure"]
CLIENT_ID = azure["client_id"]
CLIENT_SECRET = azure["client_secret"]
TENANT_ID = azure.get("tenant_id", "common")

# OAuth URLs
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
AUTHORIZE_URL = f"{AUTHORITY}/oauth2/authorize"
TOKEN_URL = f"{AUTHORITY}/oauth2/token"
REDIRECT_URI = "https://wwtw-registration.streamlit.app/"

# Create oauth instance from helper
oauth = create_oauth_session(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=["openid", "profile", "email"]
)

LOGOUT_URL = f"{AUTHORITY}/oauth2/logout?post_logout_redirect_uri={REDIRECT_URI}"

# ---------------------------------------------
# Handle Microsoft redirect
# ---------------------------------------------
if "token" not in st.session_state:
    st.session_state["token"] = None

query_params = st.query_params

if "code" in query_params and st.session_state["token"] is None:
    token = oauth.fetch_token(
        url=TOKEN_URL,
        grant_type="authorization_code",
        code=query_params["code"],
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
    )
    st.session_state["token"] = token
    st.query_params.clear()
    st.rerun()

# ---------------------------------------------
# Logged-in flow
# ---------------------------------------------
token = st.session_state["token"]

if token and "id_token" in token:

    decoded = jwt.decode(token["id_token"], options={"verify_signature": False})

    user_name_raw = decoded.get("name", "Unknown User")
    user_email = (
        decoded.get("preferred_username")
        or decoded.get("email")
        or decoded.get("upn")
        or decoded.get("unique_name")
        or ""
    )

    if "," in user_name_raw:
        last, first = [x.strip() for x in user_name_raw.split(",", 1)]
        user_name = f"{first} {last}"
    else:
        user_name = user_name_raw.strip()

    st.session_state["user_name"] = user_name
    st.session_state["user_email"] = user_email

    st.success(f"Welcome, {user_name}")
    st.caption(f"Signed in as: {user_email}")

    st.title("Walking With The Wounded")

    # Bootstrap session
    st.session_state.setdefault("SessionID", str(uuid4()))

    # ---- Intro Section ----
    st.markdown("""
    ### Welcome to the Walking With The Wounded Registration Portal

    The **Cumbrian Challenge** is Walking With The Wounded's flagship fundraising event...
    """)

    st.link_button(
        "Learn more about Walking With The Wounded",
        "https://walkingwiththewounded.org.uk/",
        type="primary"
    )

    st.divider()

    # ---- Split Layout: New vs Existing ----
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("#### 🆕 Register here!")
        st.write("Start your registration to join a team.")
        if st.button("Start New Registration ▶"):
            st.session_state["SessionID"] = str(uuid4())
            st.switch_page("pages/1_Personal.py")

    with col2:
        st.markdown("#### 🔄 Already registered?")
        st.write("Visit the official website to fundraise.")
        st.link_button(
            "Visit Official Event Page",
            "https://walkingwiththewounded.org.uk/",
            type="secondary"
        )

    with col3:
        st.markdown("#### Admin Panel")
        if st.button("Admin Panel"):
            st.session_state["SessionID"] = str(uuid4())
            st.switch_page("pages/7_Admin.py")

    with col4:
        st.markdown("#### Logout")
        if st.button("Logout"):
            st.session_state.clear()
            try:
                st.cache_data.clear()
                st.cache_resource.clear()
            except Exception:
                pass
            try:
                st.query_params.clear()
            except Exception:
                pass

            st.markdown(
                f"""
                <script>window.location.href = "{LOGOUT_URL}";</script>
                """,
                unsafe_allow_html=True,
            )

# ---------------------------------------------
# Not logged in → Show login page
# ---------------------------------------------
else:
    auth_url = build_auth_url(oauth, AUTHORIZE_URL, CLIENT_ID)

    LOGO_PATH = ASSETS_DIR / "WWTW_2025.jpg"
    encoded = base64.b64encode(open(LOGO_PATH, "rb").read()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image:
                linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)),
                url("data:image/jpg;base64,{encoded}");
            background-size: cover;
        }}
        .glass-title {{
            color: white;
            font-size: 1.8rem;
            text-align: center;
        }}
        .login-btn {{
            padding: 12px 28px;
            background: rgba(255,255,255,0.85);
            color: black;
            border-radius: 14px;
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
    st.markdown("<div class='glass-title'>Welcome to the Walking With The Wounded Registration Portal</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="display:flex; justify-content:center;">
            <a href="{auth_url}" class="login-btn">Login</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
