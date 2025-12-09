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

# CSS: background and centering; also position the Streamlit button container absolutely.
st.markdown(
    f"""
    <style>
    /* full-page background */
    .stApp {{
        min-height: 100vh;
        background-image:
            linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)),
            url("data:image/jpg;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}

    /* centered wrapper for title + body (absolute center) */
    .center-viewport {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -55%); /* slightly shift up so button sits nicely */
        text-align: center;
        z-index: 900;
        width: 90%;
        max-width: 900px;
        pointer-events: none; /* allow clicks to pass to the real button below */
    }}

    .center-viewport .title {{
        color: white;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }}

    .center-viewport .body {{
        color: white;
        font-size: 1.05rem;
        margin-bottom: 1.25rem;
    }}

    /* Style the Streamlit button itself */
    div.stButton > button {{
        background: rgba(255,255,255,0.95);
        color: black;
        padding: 12px 28px;
        border-radius: 14px;
        font-weight: 600;
        border: none;
        transition: 0.18s;
    }}

    div.stButton > button:hover {{
        background: white;
        cursor: pointer;
    }}

    /* Move the streamlit button container to be exactly centered in viewport,
       just below the center-viewport text. Adjust top to move vertically. */
    div.stButton {{
        position: absolute !important;
        top: 57% !important;    /* tune this value (57%) if you want the gap bigger/smaller */
        left: 50% !important;
        transform: translateX(-50%) !important;
        z-index: 950 !important;
        pointer-events: auto;   /* ensure button is clickable */
    }}

    /* Prevent Streamlit default padding from pushing content away */
    .main .block-container {{
        padding-top: 0rem;
        padding-bottom: 0rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Put the title + body inside the absolute-centered HTML wrapper (pointer-events none so clicks pass)
st.markdown(
    """
    <div class="center-viewport">
      <div class="title">🎉 Thank You!</div>
      <div class="body">Your registration has been successfully submitted. We appreciate your participation!</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Now render the Streamlit button (it will be repositioned by the CSS above)
if st.button("Return Home"):
    # pass the streamlit page name exactly as in your app pages; try "Home" or "Home.py" depending on your routing
    st.switch_page("Home")




