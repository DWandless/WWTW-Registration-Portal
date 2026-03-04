import streamlit as st
import jwt
import pandas as pd
from uuid import uuid4

from helpers import (
    init_page,
    get_authenticated_supabase,
    members_to_dataframe,
    sanitize_text,
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

_current_user_rows = (
    client
    .table("members")
    .select("id, team_id, role")
    .eq("employee_email", user_email)
    .limit(1)
    .execute()
    .data
    or []
)

current_user = _current_user_rows[0] if _current_user_rows else None

if not current_user:
    st.write("---")
    st.warning("No registration was found for your account. Please register first to view your team and member details.")
    st.write("---")
    st.caption("Register using the button below.")
    if st.button("Register Now"):
        st.session_state["SessionID"] = str(uuid4())
        st.switch_page("pages/1_Personal.py")

    back_button("Home.py")
    st.stop()

if not current_user.get("team_id"):
    st.write("---")
    st.warning("You are not currently assigned to a team, update your details and assign yourself to a team or contact an admin.")
    st.write("---")
    st.caption("If you need to update your registration details, please click the button below.")
    if st.button("Update Registration Details"):
            st.session_state["SessionID"] = str(uuid4())
            st.switch_page("pages/1_Personal.py")

    back_button("Home.py")
    st.stop()

team_id = current_user["team_id"]

# -----------------------------------------------------
# 4) Load team + members
# -----------------------------------------------------
_team_rows = (
    client
    .table("teams")
    .select("id, team_name, route")
    .eq("id", team_id)
    .limit(1)
    .execute()
    .data
    or []
)

team = _team_rows[0] if _team_rows else None

if not team:
    st.error("Your team could not be found.")
    back_button("Home.py")
    st.stop()

team_members = (
    client
    .table("members")
    .select(
        "id, team_id, full_name, employee_email, role, "
        "shirt_size, camping_fri, camping_sat, "
        "taking_car, travelling_from, on_waiting_list"
    )
    .eq("team_id", team_id)
    .order("role", desc=False)
    .execute()
    .data
    or []
)

is_team_leader = (current_user.get("role") or "").strip().lower() == "leader"

# -----------------------------------------------------
# 5) Display
# -----------------------------------------------------
st.write("---")

st.markdown("### Team Overview")
st.caption("Below are the current registration details for all team members within your team.")

c1, c2, c3 = st.columns(3)

c1.metric("Team", team["team_name"])
c2.metric("Route", team.get("route", "Not set"))
c3.metric("Members", f"{len(team_members)}/5")

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
    hide_index=True,
    column_config={
        "Camping Friday": st.column_config.CheckboxColumn(),
        "Camping Saturday": st.column_config.CheckboxColumn(),
        "Taking Car": st.column_config.CheckboxColumn(),
        "On Waiting List": st.column_config.CheckboxColumn(),
    }
)

# if the currently logged in user is a team leader then they have access to these functions
if is_team_leader:
    st.write("---")
    st.markdown("### Team Management")
    st.caption("As the team leader, you can rename your team or remove members from it.")

    with st.expander("Rename team", expanded=False):
        new_team_name = st.text_input("Team name", value=team.get("team_name", ""))
        rename_disabled = not sanitize_text(new_team_name)

        if st.button("Update Team Name", disabled=rename_disabled):
            try:
                cleaned = sanitize_text(new_team_name)
                client.table("teams").update({"team_name": cleaned}).eq("id", team_id).execute()
                st.success("Team name updated.")
                st.rerun()
            except Exception as e:
                st.error("Could not update the team name.")
                st.exception(e)

    with st.expander("Remove a member from the team", expanded=False):
        removable_members = [
            m for m in team_members
            if (m.get("id") is not None)
            and (str(m.get("employee_email", "")).lower() != user_email)
            and ((m.get("role") or "").strip().lower() != "leader")
        ]

        if not removable_members:
            st.info("There are no team members available to remove.")
        else:
            member_labels = [
                f"{m.get('full_name') or ''} ({m.get('employee_email') or ''})"
                for m in removable_members
            ]
            selected_idx = st.selectbox(
                "Select a team member to remove",
                options=list(range(len(removable_members))),
                format_func=lambda i: member_labels[i],
            )
            selected_member = removable_members[selected_idx]

            confirm_remove = st.checkbox(
                "I understand this will remove the member from the team (it will not delete their registration).",
                value=False,
            )

            if st.button("Remove Member", disabled=not confirm_remove):
                try:
                    client.table("members").update({"team_id": None}).eq("id", selected_member["id"]).execute()
                    st.success("Member removed from the team.")
                    st.rerun()
                except Exception as e:
                    st.error("Could not remove the selected member.")
                    st.exception(e)

back_button("Home.py")
