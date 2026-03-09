import streamlit as st
from helpers import hide_sidebar, remove_st_branding, apply_header_font
from pathlib import Path
import base64

hide_sidebar()
remove_st_branding()
apply_header_font()

BASE_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "WWTW_2025.jpg"
ICON_PATH = ASSETS_DIR / "page_icon.png"

st.set_page_config(page_icon= ICON_PATH, layout="wide")

    # Convert image to base64
with open(LOGO_PATH, "rb") as img_file:
    encoded = base64.b64encode(img_file.read()).decode()

st.markdown(
        f"""
        <style>
        html, body {{
            height: 100%;
            overflow: hidden;
        }}

        .stApp {{
            background-image:
                linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)),
                url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            height: 100vh;
            overflow: hidden;
        }}

        .login-wrap {{
            min-height: 80vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem 1rem;
        }}

        .glass-card {{
            width: min(560px, 92vw);
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 18px;
            padding: 2.25rem 2rem;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 16px 40px rgba(0,0,0,0.35);
        }}

        .title {{
            color: white;
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
            text-align: center;
        }}

        .body {{
            color: rgba(255, 255, 255, 0.88);
            font-size: 1.05rem;
            line-height: 1.55;
            text-align: center;
            margin: 0 0 1.75rem 0;
        }}

        .home-btn {{
            display: inline-block;
            width: 100%;
            text-align: center;
            padding: 14px 18px;
            background: rgba(255, 255, 255, 0.85);
            color: black;
            border-radius: 14px;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.05rem;
            transition: all 0.25s ease;
        }}

        .home-btn:visited,
        .home-btn:active,
        .home-btn:focus {{
            color: black;
            text-decoration: none;
        }}

        .home-btn:hover {{
            background: rgba(0, 123, 255, 1);
            color: white;
            text-decoration: none;
            transform: scale(1.05);
        }}

        </style>
        """,
        unsafe_allow_html=True
    )

st.markdown(
    """
    <div class="login-wrap">
      <div class="glass-card">
        <div class="title">Thank You!</div>
        <div class="body">Your registration has been successfully submitted. We appreciate your participation!</div>
        <a href="/?page=Home" class="home-btn">Return Home</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
