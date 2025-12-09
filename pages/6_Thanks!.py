import streamlit as st
from helpers import hide_sidebar, remove_st_branding
from pathlib import Path
import base64

hide_sidebar()
remove_st_branding()

st.set_page_config(page_title="Thank You", page_icon="🎉", layout="wide")

BASE_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "WWTW_2025.jpg"

# Convert image to base64
with open(LOGO_PATH, "rb") as img_file:
    encoded = base64.b64encode(img_file.read()).decode()

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image:
            linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)),
            url("data:image/jpg;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}

    .title {{
        color: white;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1rem;
        text-align: center;
    }}

    .body {{
        color: white;
        font-size: 1rem;
        margin-bottom: 1rem;
        text-align: center;
    }}

    .home-btn {{
        display: inline-block;
        margin-top: 1.5rem;
        padding: 12px 28px;
        background: rgba(255, 255, 255, 0.85);
        color: black;
        border-radius: 14px;
        text-decoration: none;
        font-weight: 600;
        transition: all 0.25s ease;
        cursor: pointer;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ----- Centered layout -----

st.markdown(
    "<div style='display:flex; justify-content:center;'>",
    unsafe_allow_html=True
)

st.markdown("<div class='title'>🎉 Thank You!</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='body'>Your registration has been successfully submitted. We appreciate your participation!</div>",
    unsafe_allow_html=True
)

# --------- Hidden Streamlit button (used for navigation) ----------
nav_id = "go_home_button"
if st.button("Return Home (hidden)", key=nav_id, help="hidden button", type="primary"):
    st.switch_page("Home")

# Hide the Streamlit button using CSS
st.markdown(
    f"""
    <style>
        [data-testid="baseButton-secondary"][data-testid="button-{nav_id}"] {{
            display: none !important;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# --------- HTML button that triggers the hidden Streamlit button ----------
st.markdown(
    f"""
    <div style="display:flex; justify-content:center;">
        <a class="home-btn" onclick="document.querySelector('[data-testid=button-{nav_id}]').click();">
            Return home
        </a>
    </div>
    """,
    unsafe_allow_html=True
)





