
import streamlit as st
import pandas as pd
import os
from uuid import uuid4
from authlib.integrations.requests_client import OAuth2Session
import jwt
import base64
from pathlib import Path
from helpers import hide_sidebar, remove_st_branding

# ---------------------------------------------
# Icon loading
# ---------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ICON_PATH = ASSETS_DIR / "page_icon.png"

# ---------------------------------------------
# Page Setup
# ---------------------------------------------

st.set_page_config(page_icon= ICON_PATH, layout="wide")
remove_st_branding()
hide_sidebar()

# Azure Credentials
azure = st.secrets["azure"]
CLIENT_ID = azure["client_id"]
CLIENT_SECRET = azure["client_secret"]
TENANT_ID = azure.get("tenant_id", "common")

# Azure OAuth Config
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
AUTHORIZE_URL = f"{AUTHORITY}/oauth2/authorize"
TOKEN_URL = f"{AUTHORITY}/oauth2/token"
REDIRECT_URI = "https://wwtw-registration.streamlit.app/"

oauth = OAuth2Session(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scope=["openid", "profile", "email"],
    redirect_uri=REDIRECT_URI,
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

    # Decode Microsoft ID Token
    decoded = jwt.decode(token["id_token"], options={"verify_signature": False})

    # Extract name + email from v1 token
    user_name_raw = decoded.get("name", "Unknown User")
    user_email = (
        decoded.get("preferred_username")
        or decoded.get("email")
        or decoded.get("upn")
        or decoded.get("unique_name")
        or ""
    )

    # Format full name
    if "," in user_name_raw:
        last, first = [x.strip() for x in user_name_raw.split(",", 1)]
        user_name = f"{first} {last}"
    else:
        user_name = user_name_raw.strip()

    st.session_state["user_name"] = user_name
    st.session_state["user_email"] = user_email

    st.set_page_config(page_title="Home", page_icon= ICON_PATH, layout="wide")

    # ---- Session bootstrap ----
    st.session_state.setdefault("SessionID", str(uuid4()))

    st.image(ICON_PATH, width=100)

    st.title("Register for the Cumbrian Challenge with DXC Technology")
    st.write("---")

    # ---- Intro Section ----
    st.markdown("""
    ### Join DXC Technology in Supporting Walking With The Wounded

    Welcome to DXC Technology’s official registration portal for the **Cumbrian Challenge**, the flagship fundraising event by Walking With The Wounded.  
    This inspiring challenge takes place in the stunning Lake District, where teams of 3–5 tackle one of three scenic routes to raise vital funds for veterans in need of mental health support, employment opportunities, and housing stability.

    By signing up through DXC, you’re helping transform lives and make a real difference.  
    **Thank you for being part of this incredible cause!**
    """)

    st.link_button("Learn more about Walking With The Wounded", "https://walkingwiththewounded.org.uk/", type="primary")

    st.divider()

    # ---- Helpers ----
    def get_next_page():
        csv_file = "registrations.csv"
        sid = st.session_state.get("SessionID")
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                if "SessionID" in df.columns and sid in df["SessionID"].values:
                    row = df[df["SessionID"] == sid].iloc[0]
                    def _val(key): return row[key] if key in row.index else None
                    personal_complete = all(_val(k) not in [None, "", float('nan')] for k in ["Name", "Email", "Employee ID", "Organisation"]) if any(k in row.index for k in ["Name", "Email", "Employee ID", "Organisation"]) else False
                    team_complete = all(_val(k) not in [None, "", float('nan')] for k in ["Team", "Captain", "Registered Team"]) if any(k in row.index for k in ["Team", "Captain", "Registered Team"]) else False
                    route_complete = (_val("Route") not in [None, "", float('nan')]) if ("Route" in row.index) else False
                    logistics_complete = any(_val(k) not in [None, "", float('nan')] for k in ["T-shirt", "Travelling From", "Notes", "Experience"]) if any(k in row.index for k in ["T-shirt", "Travelling From", "Notes", "Experience"]) else False
                    if not personal_complete: return "pages/1_Personal.py"
                    if not team_complete: return "pages/2_Team.py"
                    if not route_complete: return "pages/3_Route.py"
                    if not logistics_complete: return "pages/4_Logistics.py"
                    return "pages/5_Review.py"
            except Exception:
                pass
        return "pages/1_Form.py"

    # ---- Split Layout: New vs Existing ----
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("#### ➜ Register Here")
        st.write("Start your registration to join a team and prepare for the event.")
        if st.button("Start New Registration"):
            st.session_state["SessionID"] = str(uuid4())
            st.switch_page("pages/1_Personal.py")

    with col2:
        st.markdown("#### ↪ Already Registered")
        st.write("View your current team and registration details.")
        if st.button("View Registration Details"):
            st.session_state["SessionID"] = str(uuid4())
            st.switch_page("pages/8_Registration_Details.py")
    
    with col3:
        st.markdown("#### 🛠 Admin Panel")
        st.write("Access administrative functions and manage registrations.")
        if st.button("Admin Panel"):
            st.session_state["SessionID"] = str(uuid4())
            st.switch_page("pages/7_Admin.py")


    with col4:
        st.markdown("#### ➜] Logout")
        st.write("Click below to securely log out of the portal.")
        if st.button("Logout"):
            # 1) Clear app-side state & caches
            st.session_state.clear()
            try:
                st.cache_data.clear()
                st.cache_resource.clear()
            except Exception:
                pass
            # 2) Clear any query parameters that might re-trigger auth flow
            try:
                st.query_params.clear()
            except Exception:
                pass
            # 3) Redirect the browser to Microsoft logout to end IdP session
            st.markdown(
                f"""
                <script>
                window.location.href = "{LOGOUT_URL}";
                </script>
                """,
                unsafe_allow_html=True,
            )

# ---------------------------------------------
# Login button (not logged in)
# ---------------------------------------------
else:
    auth_url, _ = oauth.create_authorization_url(
        AUTHORIZE_URL,
        prompt="select_account",
        resource=CLIENT_ID,
    )

    # Get image
    BASE_DIR = Path(__file__).resolve().parent
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

        .glass-title {{
            color: white;
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-align: center;
        }}

        .login-btn {{
            display: inline-block;
            margin-top: 1.5rem;
            padding: 12px 28px;
            background: rgba(255, 255, 255, 0.85);
            color: black;
            border-radius: 14px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.25s ease;
        }}

        .login-btn:hover {{
            background: rgba(0, 123, 255, 1);
            transform: scale(1.05);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # ✅ Vertical center wrapper
    st.markdown(
        "<div style='display:flex; justify-content:center;'>",
        unsafe_allow_html=True
    )

    # ✅ Title
    st.markdown(
        "<div class='glass-title'>Welcome to the Walking With The Wounded Registration Portal</div>",
        unsafe_allow_html=True
    )

    # ✅ Warning message
    # st.markdown(
    #     "<p style='color: white; font-size: 1rem; text-align: center;'>Please log in to continue</p>",
    #     unsafe_allow_html=True
    # )

    # ✅ Login Button (Styled)
    st.markdown(
        f"""
        <div style="display:flex; justify-content:center;">
        <a href="{auth_url}" class="login-btn">
            Login 
        </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ✅ Frosted Glass Card End
st.markdown("</div></div>", unsafe_allow_html=True)
    


