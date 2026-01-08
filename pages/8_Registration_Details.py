import streamlit as st
import jwt
import pandas as pd
from uuid import uuid4

from helpers import (
    init_page,
    get_authenticated_supabase,
    members_to_dataframe,
    hide_sidebar,
    back_button,
    remove_st_branding
)

# -----------------------------------------------------
# Page Setup
# -----------------------------------------------------
init_page("Registration Details", "wide")
remove_st_branding()
hide_sidebar()

# -----------------------------------------------------
# 1) CHECK IF USER IS LOGGED IN
# -----------------------------------------------------
if "token" not in st.session_state or not st.session_state["token"]:
    st.error("✖ You must be logged in to access this page.")
    back_button("Home.py")
    st.write("---")
    st.stop()

token = st.session_state["token"]

if "id_token" not in token:
    st.error("✖ Invalid login session. Please sign in again.")
    back_button("Home.py")
    st.write("---")
    st.stop()

# -----------------------------------------------------
# 2) Decode Microsoft Token
# -----------------------------------------------------
decoded = jwt.decode(token["id_token"], options={"verify_signature": False})

raw_name = decoded.get("name", "")
user_email = (
    decoded.get("preferred_username")
    or decoded.get("email")
    or decoded.get("upn")
    or ""
).lower()

if "," in raw_name:
    last, first = [x.strip() for x in raw_name.split(",", 1)]
    user_name = f"{first} {last}"
else:
    user_name = raw_name.strip()

st.session_state["user_email"] = user_email
st.session_state["user_name"] = user_name

# -----------------------------------------------------
# 3) Load current user → team
# -----------------------------------------------------
client = get_authenticated_supabase()

current_user = (
    client
    .table("members")
    .select("id, team_id, role")
    .eq("employee_email", user_email)
    .single()
    .execute()
    .data
)

if not current_user or not current_user.get("team_id"):
    st.write("---")
    st.warning("You are not currently assigned to a team.")
    back_button("Home.py")
    st.stop()

team_id = current_user["team_id"]

# -----------------------------------------------------
# 4) Load team + members
# -----------------------------------------------------
team = (
    client
    .table("teams")
    .select("id, team_name, route")
    .eq("id", team_id)
    .single()
    .execute()
    .data
)

if not team:
    st.error("Your team could not be found.")
    back_button("Home.py")
    st.stop()

team_members = (
    client
    .table("members")
    .select(
        "team_id, full_name, employee_email, role, "
        "shirt_size, camping_fri, camping_sat, "
        "taking_car, travelling_from, on_waiting_list"
    )
    .eq("team_id", team_id)
    .order("role", desc=True)
    .execute()
    .data
    or []
)

# -----------------------------------------------------
# 5) Display
# -----------------------------------------------------
st.write("---")
st.subheader(f"Team: {team['team_name']}")
st.caption(f"Route: {team.get('route', 'Not set')}")
df = members_to_dataframe(team_members, {team_id: team["team_name"]})

# Explicit whitelist of visible columns
visible_columns = [
    "Role",
    "Full Name",
    "Employee Email",
    "Shirt Size",
    "Camping Friday",
    "Camping Saturday",
    "Taking Car",
    "Travelling From",
    "On Waiting List",
]

df_view = df[visible_columns]

st.dataframe(
    df_view,
    use_container_width=True,
    column_config={
        "Camping Friday": st.column_config.CheckboxColumn(),
        "Camping Saturday": st.column_config.CheckboxColumn(),
        "Taking Car": st.column_config.CheckboxColumn(),
        "On Waiting List": st.column_config.CheckboxColumn(),
    }
)

st.write("---")
st.caption("If you need to update your registration details, please click the button below.")
if st.button("Update Registration Details"):
            st.session_state["SessionID"] = str(uuid4())
            st.switch_page("pages/1_Personal.py")

back_button("Home.py")
st.write("---")
