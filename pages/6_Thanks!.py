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

# Custom styling
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

    div.stButton > button {{
        background: rgba(255,255,255,0.85);
        color: black;
        padding: 12px 28px;
        border-radius: 14px;
        font-weight: 600;
        border: none;
        transition: 0.25s;
    }}

    div.stButton > button:hover {{
        background: white;
        cursor: pointer;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Content ---
st.markdown("<div class='title'>🎉 Thank You!</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='body'>Your registration has been successfully submitted. We appreciate your participation!</div>",
    unsafe_allow_html=True,
)

# --- PERFECTLY CENTERED BUTTON ---
col1, col2, col3 = st.columns([3, 2, 3])   # Middle column is centered on page

with col2:
    if st.button("Return Home"):
        st.switch_page("Home.py")






