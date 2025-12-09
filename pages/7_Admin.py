import streamlit as st
import jwt
import pandas as pd

from helpers import (
    init_page,
    require_access,
    get_authenticated_supabase,
    members_to_dataframe,
    apply_member_updates,
    export_excel,
    delete_team,
    delete_member,
    hide_sidebar,
    back_button,
    remove_st_branding
)

# -----------------------------------------------------
# Page Setup
# -----------------------------------------------------
init_page("Admin Panel", "wide")
remove_st_branding()
hide_sidebar()

# -----------------------------------------------------
# 1) CHECK IF USER IS LOGGED IN (from home.py)
# -----------------------------------------------------
if "token" not in st.session_state or st.session_state["token"] is None:
    st.error("❌ You must be logged in to access the Admin Panel.")
    st.page_link("home.py", label="⬅ Return to Login")
    st.stop()

token = st.session_state["token"]

# If somehow token exists but no id_token → treat as not logged in
if "id_token" not in token:
    st.error("❌ Invalid login session. Please sign in again.")
    st.page_link("home.py", label="⬅ Return to Login")
    st.stop()

# -----------------------------------------------------
# 2) Decode Microsoft Token (same as home.py)
# -----------------------------------------------------
decoded = jwt.decode(token["id_token"], options={"verify_signature": False})

raw_name = decoded.get("name", "Unknown User")
user_email = (
    decoded.get("preferred_username")
    or decoded.get("email")
    or decoded.get("upn")
    or decoded.get("unique_name")
    or ""
)

# Convert “Lastname, Firstname” format if needed
if "," in raw_name:
    last, first = [x.strip() for x in raw_name.split(",", 1)]
    user_name = f"{first} {last}"
else:
    user_name = raw_name.strip()

st.session_state["user_name"] = user_name
st.session_state["user_email"] = user_email

# Access control and sidebar
user_email, user_name, is_admin = require_access()

# Authenticated Supabase Client
client = get_authenticated_supabase()

# Load teams and members
teams_data = (
    client.table("teams")
    .select("id, team_name, route, members(*)")
    .execute()
    .data
    or []
)

team_id_to_name = {t["id"]: t["team_name"] for t in teams_data}
team_name_to_id = {v: k for k, v in team_id_to_name.items()}
team_options = list(team_name_to_id.keys())
team_options_with_unassigned = team_options + ["Unassigned"]

all_members = client.table("members").select("*").execute().data or []
valid_team_ids = set(team_id_to_name.keys())

unassigned_members = [m for m in all_members if m.get("team_id") not in valid_team_ids]

# -----------------------------------------------------
# Utility: Member Editor Function
# -----------------------------------------------------
def render_member_editor(df_members, team_name_to_id, client, title, dropdowns):
    if df_members.empty:
        st.info(f"No members to display for {title}.")
        return

    # Clear any stale pending delete state for this section
    pending_key = f"pending_delete_{title}"
    if pending_key in st.session_state and st.session_state[pending_key] is not None:
        # Check if the member still exists in df_members
        member_id_str = str(st.session_state[pending_key])
        if not any(df_members["id"] == member_id_str):
            # Member no longer exists in this list, clear the state
            st.session_state[pending_key] = None
            st.session_state.pop(f"delete_select_{title}", None)

    df_ids = df_members.copy()

    # ---- 1️⃣ Show editable table (no delete column) ----
    edited = st.data_editor(
        df_members.drop(columns=["id"]),
        width="stretch",
        num_rows="fixed",
        column_config=dropdowns,
        key=f"editor_{title}"
    )

    # Restore IDs
    edited["id"] = df_ids["id"]

    # ---- 2️⃣ Apply updates ----
    applied = apply_member_updates(edited, df_ids, team_name_to_id, client)
    if applied > 0:
        st.success(f"Applied {applied} update(s).")
        st.rerun()

    member_options = {
        f"{row['Full Name']} — {row['Employee Email']}": row["id"]
        for _, row in df_members.iterrows()
    }

    st.markdown("**Delete Member:**")
    
    cols = st.columns([3, 1])
    
    with cols[0]:
        selected = st.selectbox(
            "Select member to delete",
            list(member_options.keys()),
            key=f"delete_select_{title}",
            label_visibility="collapsed"
        )
    
    pending_key = f"pending_delete_{title}"
    
    with cols[1]:
        if st.button("🗑️ Delete", key=f"delete_btn_{title}", use_container_width=True):
            st.session_state[pending_key] = member_options[selected]
    
    # Confirmation dialog
    if st.session_state.get(pending_key):
        # Safely get member name from dataframe
        member_id_str = str(st.session_state[pending_key])
        matching_rows = df_members[df_members["id"] == member_id_str]
        member_name = matching_rows["Full Name"].values[0] if not matching_rows.empty else "Member"
        
        st.error(f"⚠️ Delete '{member_name}'?")
        
        confirm_cols = st.columns([1, 1, 2])
        
        with confirm_cols[0]:
            if st.button("✅ Confirm", key=f"confirm_delete_yes_{title}", use_container_width=True):
                delete_member(st.session_state[pending_key], client)
                st.session_state[pending_key] = None
                st.session_state.pop(f"delete_select_{title}", None)  # Clear selectbox state
                st.rerun()
        
        with confirm_cols[1]:
            if st.button("❌ Cancel", key=f"confirm_delete_no_{title}", use_container_width=True):
                st.session_state[pending_key] = None
                st.session_state.pop(f"delete_select_{title}", None)  # Clear selectbox state
                st.rerun()
    
    st.markdown("---")


# -----------------------------------------------------
# Dropdown Config
# -----------------------------------------------------
dropdowns = {
    "Team Name": st.column_config.SelectboxColumn("Team Name", options=team_options_with_unassigned),
    # Use the canonical route keys used elsewhere in the app
    "Preferred Route": st.column_config.SelectboxColumn("Preferred Route", options=["Peak", "Tough", "Tougher"]),
    "Organisation": st.column_config.SelectboxColumn("Organisation", options=["CSC", "L-ES", "Velonetic"]),
    "Role": st.column_config.SelectboxColumn("Role", options=["Member", "Leader"]),
    "Shirt Size": st.column_config.SelectboxColumn("Shirt Size", options=["XS", "S", "M", "L", "XL", "XXL"]),
    "Forces Veteran": st.column_config.CheckboxColumn("Forces Veteran"),
    "Camping Friday": st.column_config.CheckboxColumn("Camping Friday"),
    "Camping Saturday": st.column_config.CheckboxColumn("Camping Saturday"),
    "Taking Car": st.column_config.CheckboxColumn("Taking Car"),
    "On Waiting List": st.column_config.CheckboxColumn("On Waiting List"),
    "Notes": st.column_config.TextColumn("Notes"),
    "Hiking Experience": st.column_config.TextColumn("Hiking Experience"),
    "Travelling From": st.column_config.TextColumn("Travelling From"),
}


# -----------------------------------------------------
# Waiting List
# -----------------------------------------------------
waiting_members = client.table("members").select("*").eq("on_waiting_list", True).execute().data or []
st.markdown("---")
st.subheader("Waiting List")
st.caption("Members added here when the event reaches capacity (200+ active participants). Manage these members below—edit their details or uncheck 'On Waiting List' to move them to active status. Delete members if needed.")

with st.expander(f"Waiting List ({len(waiting_members)})", expanded=False):
    if waiting_members:
        df_wait = members_to_dataframe(waiting_members, team_id_to_name)
        render_member_editor(df_wait, team_name_to_id, client, "Waiting List", dropdowns)
    else:
        st.info("No users are currently on the waiting list.")

# -----------------------------------------------------
# Unassigned Members
# -----------------------------------------------------
st.markdown("---")
st.subheader("Unassigned Members")
st.caption("Participants who registered but are not part of any team. Assign them to teams using the 'Team Name' dropdown in the table, or delete them if needed. Teams accept up to 5 members each.")

with st.expander(f"Unassigned Members ({len(unassigned_members)})"):
    if unassigned_members:
        df_un = members_to_dataframe(unassigned_members, team_id_to_name)
        render_member_editor(df_un, team_name_to_id, client, "Unassigned", dropdowns)
    else:
        st.info("All members are assigned to teams.")


# -----------------------------------------------------
# Teams & Members Section
# -----------------------------------------------------
st.markdown("---")
st.subheader("Teams & Members")
st.caption("View and manage all teams and their members. Edit participant details, reassign members to different teams, or delete entire teams (members will be unassigned). Each team can hold up to 5 members.")

for team in teams_data:
    team_members = team.get("members") or []

    with st.expander(f"{team['team_name']} — Route: {team.get('route','')} ({len(team_members)}/5 Members)"):

        if team_members:
            df_team = members_to_dataframe(team_members, team_id_to_name)
            render_member_editor(df_team, team_name_to_id, client, team["team_name"], dropdowns)
        else:
            st.info("No members assigned to this team.")

        # Delete Team (with confirmation)
        with st.container():
            st.markdown("**Delete Team:**")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(team['team_name'])
            
            with col2:
                if st.button(f"🗑️ Delete", key=f"del_team_btn_{team['id']}", use_container_width=True):
                    st.session_state["confirm_delete_team"] = team["id"]
            
            # Confirmation dialog
            if st.session_state.get("confirm_delete_team") == team["id"]:
                st.error(f"⚠️ Delete team '{team['team_name']}'? Members will be unassigned.")
                
                col_confirm, col_cancel = st.columns([1, 1])
                
                with col_confirm:
                    if st.button("✅ Confirm", key=f"confirm_yes_{team['id']}", use_container_width=True):
                        delete_team(team["id"], client)
                        st.session_state["confirm_delete_team"] = None
                        st.rerun()
                
                with col_cancel:
                    if st.button("❌ Cancel", key=f"confirm_no_{team['id']}", use_container_width=True):
                        st.session_state["confirm_delete_team"] = None
                        st.rerun()

# -----------------------------------------------------
# EXPORT BUTTON
# -----------------------------------------------------
excel_file = export_excel(client)

st.markdown("---")
st.subheader("Export Data")
st.caption("Download a comprehensive Excel file (.xlsx) containing all participants, sorted by team and waiting list status. Use this for reporting, planning, or offline record-keeping.")

st.download_button(
    label="Export & Download Teams.xlsx",
    data=excel_file.getvalue(),
    file_name="teams.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

back_button("Home.py")
