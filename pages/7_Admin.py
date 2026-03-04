import streamlit as st
import pandas as pd

from helpers import (
    init_page,
    require_access,
    get_authenticated_supabase,
    verify_microsoft_id_token,
    members_to_dataframe,
    apply_member_updates,
    export_excel,
    delete_team,
    delete_member,
    hide_sidebar,
    back_button,
    remove_st_branding,
    export_volunteers_excel
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
    st.error("✖ You must be logged in to access the Admin Panel.")
    back_button("Home.py")
    st.write("---")
    st.stop()

token = st.session_state["token"]

# If somehow token exists but no id_token → treat as not logged in
if "id_token" not in token:
    st.error("✖ Invalid login session. Please sign in again.")
    back_button("Home.py")
    st.write("---")
    st.stop()

# -----------------------------------------------------
# 2) Decode Microsoft Token (same as home.py)
# -----------------------------------------------------
try:
    decoded = verify_microsoft_id_token(token["id_token"])
except Exception:
    st.error("✖ Invalid login session. Please sign in again.")
    back_button("Home.py")
    st.write("---")
    st.stop()

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
    .select("id, team_name, route, on_waiting_list, members(*)")
    .eq("on_waiting_list", False)
    .execute()
    .data
    or []
)

team_id_to_name = {t["id"]: t["team_name"] for t in teams_data}

volunteer_dropdowns = {
    "Full Name": st.column_config.TextColumn("Full Name"),
    "Employee Email": st.column_config.TextColumn("Employee Email"),
    "Employee ID": st.column_config.TextColumn("Employee ID"),
    "Mobile Number": st.column_config.TextColumn("Mobile Number"),
    "Area": st.column_config.TextColumn("Area"),
    "On Waiting List": st.column_config.CheckboxColumn("On Waiting List"),
}
team_name_to_id = {v: k for k, v in team_id_to_name.items()}
team_options = list(team_name_to_id.keys())
team_options_with_unassigned = team_options + ["Unassigned"]

all_members = client.table("members").select("*").execute().data or []
valid_team_ids = set(team_id_to_name.keys())

unassigned_members = [
    m
    for m in all_members
    if not bool(m.get("on_waiting_list"))
    and (m.get("team_id") is None or m.get("team_id") not in valid_team_ids)
]

# -----------------------------------------------------
# Utility: Member Editor Function
# -----------------------------------------------------
def render_member_editor(df_members, team_id_to_name, team_name_to_id, client, title, dropdowns):
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

    # Build dynamic Team Name options: include teams that have space (less than 5 active members)
    # and always include any team present in this dataframe (so current members keep their team).
    try:
        active_members = client.table("members").select("team_id").eq("on_waiting_list", False).execute().data or []
    except Exception:
        active_members = []

    counts = {}
    for m in active_members:
        tid = m.get("team_id")
        if tid is None:
            continue
        counts[tid] = counts.get(tid, 0) + 1

    current_team_names = set(df_members["Team Name"].tolist())

    available_team_names = []
    for tid, name in team_id_to_name.items():
        c = counts.get(tid, 0)
        if c < 5 or name in current_team_names:
            available_team_names.append(name)

    # Ensure Unassigned is always present and no null/None option appears
    if "Unassigned" not in available_team_names:
        available_team_names.append("Unassigned")

    # Make a local copy of dropdowns and override Team Name options
    local_dropdowns = dropdowns.copy()
    local_dropdowns["Team Name"] = st.column_config.SelectboxColumn("Team Name", options=available_team_names)

    # ---- Show editable table (no delete column) ----
    edited = st.data_editor(
        df_members.drop(columns=["id"]),
        width="stretch",
        num_rows="fixed",
        hide_index=True,
        column_config=local_dropdowns,
        key=f"editor_{title}"
    )

    # Restore IDs
    edited["id"] = df_ids["id"]

    # ---- Apply updates ----
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
        if st.button("⌦ Delete", key=f"delete_btn_{title}", use_container_width=True):
            st.session_state[pending_key] = member_options[selected]
    
    # Confirmation dialog
    if st.session_state.get(pending_key):
        # Safely get member name from dataframe
        member_id_str = str(st.session_state[pending_key])
        matching_rows = df_members[df_members["id"] == member_id_str]
        member_name = matching_rows["Full Name"].values[0] if not matching_rows.empty else "Member"
        
        st.error(f"⚠︎ Delete '{member_name}'?")
        
        confirm_cols = st.columns([1, 1, 2])
        
        with confirm_cols[0]:
            if st.button("✔ Confirm", key=f"confirm_delete_yes_{title}", use_container_width=True):
                delete_member(st.session_state[pending_key], client)
                st.session_state[pending_key] = None
                st.session_state.pop(f"delete_select_{title}", None)  # Clear selectbox state
                st.rerun()
        
        with confirm_cols[1]:
            if st.button("✖ Cancel", key=f"confirm_delete_no_{title}", use_container_width=True):
                st.session_state[pending_key] = None
                st.session_state.pop(f"delete_select_{title}", None)  # Clear selectbox state
                st.rerun()
    
    st.markdown("---")


def teams_to_dataframe(teams):
    df = pd.DataFrame([
        {
            "id": str(t.get("id")),
            "Team Name": t.get("team_name"),
            "Route": t.get("route"),
            "On Waiting List": bool(t.get("on_waiting_list")),
        }
        for t in (teams or [])
    ])
    return df


TEAM_COLUMN_MAP = {
    "Team Name": "team_name",
    "Route": "route",
    "On Waiting List": "on_waiting_list",
}


def apply_team_updates(edited_df, original_df, client):
    if edited_df is None or edited_df.empty:
        return 0

    updates = 0

    original_df = original_df.copy()
    edited_df = edited_df.copy()
    original_df["id"] = original_df["id"].astype(str)
    edited_df["id"] = edited_df["id"].astype(str)

    for _, row in edited_df.iterrows():
        team_id = row["id"]
        orig_rows = original_df[original_df["id"] == team_id]
        if orig_rows.empty:
            continue
        orig = orig_rows.iloc[0]

        changes = {}
        for col, new_val in row.items():
            if col == "id":
                continue

            old_val = orig[col]
            db_col = TEAM_COLUMN_MAP.get(col)
            if not db_col:
                continue

            if db_col == "on_waiting_list":
                new_val = bool(new_val)
                old_val = bool(old_val)

            if new_val != old_val:
                changes[db_col] = new_val

        if changes:
            try:
                client.table("teams").update(changes).eq("id", team_id).execute()
                updates += 1
            except Exception as e:
                st.error(f"Failed to update team {team_id}.")
                st.exception(e)

    return updates


def render_team_editor(df_teams, client, title, dropdowns):
    if df_teams.empty:
        st.info(f"No teams to display for {title}.")
        return

    pending_key = f"pending_delete_{title}"
    if pending_key in st.session_state and st.session_state[pending_key] is not None:
        team_id_str = str(st.session_state[pending_key])
        if not any(df_teams["id"] == team_id_str):
            st.session_state[pending_key] = None
            st.session_state.pop(f"delete_select_{title}", None)

    df_ids = df_teams.copy()

    edited = st.data_editor(
        df_teams.drop(columns=["id"]),
        width="stretch",
        num_rows="fixed",
        hide_index=True,
        column_config=dropdowns,
        key=f"editor_{title}",
    )

    edited["id"] = df_ids["id"]

    applied = apply_team_updates(edited, df_ids, client)
    if applied > 0:
        st.success(f"Applied {applied} update(s).")
        st.rerun()

    team_options = {
        f"{row['Team Name']} — {row['Route']}": row["id"]
        for _, row in df_teams.iterrows()
    }

    st.markdown("**Delete Team:**")
    cols = st.columns([3, 1])

    with cols[0]:
        selected = st.selectbox(
            "Select team to delete",
            list(team_options.keys()),
            key=f"delete_select_{title}",
            label_visibility="collapsed",
        )

    with cols[1]:
        if st.button("⌦ Delete", key=f"delete_btn_{title}", use_container_width=True):
            st.session_state[pending_key] = team_options[selected]

    if st.session_state.get(pending_key):
        team_id_str = str(st.session_state[pending_key])
        matching_rows = df_teams[df_teams["id"] == team_id_str]
        team_name = matching_rows["Team Name"].values[0] if not matching_rows.empty else "Team"

        st.error(f"⚠︎ Delete '{team_name}'? Members will be unassigned.")
        confirm_cols = st.columns([1, 1, 2])

        with confirm_cols[0]:
            if st.button("✔ Confirm", key=f"confirm_delete_yes_{title}", use_container_width=True):
                delete_team(st.session_state[pending_key], client)
                st.session_state[pending_key] = None
                st.session_state.pop(f"delete_select_{title}", None)
                st.rerun()

        with confirm_cols[1]:
            if st.button("✖ Cancel", key=f"confirm_delete_no_{title}", use_container_width=True):
                st.session_state[pending_key] = None
                st.session_state.pop(f"delete_select_{title}", None)
                st.rerun()

    st.markdown("---")


def volunteers_to_dataframe(volunteers):
    df = pd.DataFrame([
        {
            "id": str(v.get("id")),
            "Full Name": v.get("full_name"),
            "Employee Email": v.get("employee_email"),
            "Employee ID": v.get("employee_id"),
            "Mobile Number": v.get("mobile_number"),
            "Area": v.get("area"),
            "On Waiting List": bool(v.get("on_waiting_list")),
        }
        for v in (volunteers or [])
    ])
    return df


VOLUNTEER_COLUMN_MAP = {
    "Full Name": "full_name",
    "Employee Email": "employee_email",
    "Employee ID": "employee_id",
    "Mobile Number": "mobile_number",
    "Area": "area",
    "On Waiting List": "on_waiting_list",
}


def apply_volunteer_updates(edited_df, original_df, client):
    if edited_df is None or edited_df.empty:
        return 0

    updates = 0

    original_df = original_df.copy()
    edited_df = edited_df.copy()
    original_df["id"] = original_df["id"].astype(str)
    edited_df["id"] = edited_df["id"].astype(str)

    for _, row in edited_df.iterrows():
        volunteer_id = row["id"]
        orig_rows = original_df[original_df["id"] == volunteer_id]
        if orig_rows.empty:
            continue
        orig = orig_rows.iloc[0]

        changes = {}
        for col, new_val in row.items():
            if col == "id":
                continue

            old_val = orig[col]
            db_col = VOLUNTEER_COLUMN_MAP.get(col)
            if not db_col:
                continue

            if db_col == "on_waiting_list":
                new_val = bool(new_val)
                old_val = bool(old_val)

            if new_val != old_val:
                changes[db_col] = new_val

        if changes:
            try:
                client.table("volunteers").update(changes).eq("id", volunteer_id).execute()
                updates += 1
            except Exception as e:
                st.error(f"Failed to update volunteer {volunteer_id}.")
                st.exception(e)

    return updates


def delete_volunteer(volunteer_id: str, client):
    try:
        client.table("volunteers").delete().eq("id", volunteer_id).execute()
        st.success("Volunteer deleted.")
        st.rerun()
    except Exception as e:
        st.error("Failed to delete volunteer.")
        st.exception(e)


def render_volunteer_editor(df_volunteers, client, title, dropdowns):
    if df_volunteers.empty:
        st.info(f"No volunteers to display for {title}.")
        return

    pending_key = f"pending_delete_{title}"
    if pending_key in st.session_state and st.session_state[pending_key] is not None:
        volunteer_id_str = str(st.session_state[pending_key])
        if not any(df_volunteers["id"] == volunteer_id_str):
            st.session_state[pending_key] = None
            st.session_state.pop(f"delete_select_{title}", None)

    df_ids = df_volunteers.copy()

    edited = st.data_editor(
        df_volunteers.drop(columns=["id"]),
        width="stretch",
        num_rows="fixed",
        hide_index=True,
        column_config=dropdowns,
        key=f"editor_{title}",
    )

    edited["id"] = df_ids["id"]

    applied = apply_volunteer_updates(edited, df_ids, client)
    if applied > 0:
        st.success(f"Applied {applied} update(s).")
        st.rerun()

    volunteer_options = {
        f"{row['Full Name']} — {row['Employee Email']}": row["id"]
        for _, row in df_volunteers.iterrows()
    }

    st.markdown("**Delete Volunteer:**")
    cols = st.columns([3, 1])

    with cols[0]:
        selected = st.selectbox(
            "Select volunteer to delete",
            list(volunteer_options.keys()),
            key=f"delete_select_{title}",
            label_visibility="collapsed",
        )

    with cols[1]:
        if st.button("⌦ Delete", key=f"delete_btn_{title}", use_container_width=True):
            st.session_state[pending_key] = volunteer_options[selected]

    if st.session_state.get(pending_key):
        volunteer_id_str = str(st.session_state[pending_key])
        matching_rows = df_volunteers[df_volunteers["id"] == volunteer_id_str]
        volunteer_name = matching_rows["Full Name"].values[0] if not matching_rows.empty else "Volunteer"

        st.error(f"⚠︎ Delete '{volunteer_name}'?")
        confirm_cols = st.columns([1, 1, 2])

        with confirm_cols[0]:
            if st.button("✔ Confirm", key=f"confirm_delete_yes_{title}", use_container_width=True):
                delete_volunteer(st.session_state[pending_key], client)
                st.session_state[pending_key] = None
                st.session_state.pop(f"delete_select_{title}", None)
                st.rerun()

        with confirm_cols[1]:
            if st.button("✖ Cancel", key=f"confirm_delete_no_{title}", use_container_width=True):
                st.session_state[pending_key] = None
                st.session_state.pop(f"delete_select_{title}", None)
                st.rerun()

    st.markdown("---")

# -----------------------------------------------------
# Dropdown Config
# -----------------------------------------------------
dropdowns = {
    "Team Name": st.column_config.SelectboxColumn("Team Name", options=team_options_with_unassigned),
    # Use the canonical route keys used elsewhere in the app
    "Preferred Route": st.column_config.SelectboxColumn("Preferred Route", options=["Peak", "Tough", "Tougher"]),
    "Organisation": st.column_config.SelectboxColumn(
        "Organisation",
        options=["L-ES", "L-CSC", "Velonetic", "CSC"],
    ),
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
    "Dropped Out": st.column_config.CheckboxColumn("Dropped Out"),
    
}

# -----------------------------------------------------
# Volunteers
# -----------------------------------------------------
volunteers = client.table("volunteers").select('*').eq("on_waiting_list", False).execute().data or []
st.markdown("---")
st.subheader("Volunteers")
st.caption("Manage volunteers who have signed up to assist with the event.")

with st.expander(f"Volunteers ({len(volunteers)})", expanded=False):
    if volunteers:
        df_vol = volunteers_to_dataframe(volunteers)
        render_volunteer_editor(df_vol, client, "Volunteers", volunteer_dropdowns)
    else:
        st.info("No volunteers have signed up yet.")




# -----------------------------------------------------
# Particpant Waiting List
# -----------------------------------------------------
waiting_members = client.table("members").select("*").eq("on_waiting_list", True).execute().data or []
st.markdown("---")
st.subheader("Participant Waiting List")
st.caption("Members added here when the event reaches capacity (200+ active participants). Manage these members below—edit their details or uncheck 'On Waiting List' to move them to active status. Delete members if needed.")

with st.expander(f"Waiting List ({len(waiting_members)})", expanded=False):
    if waiting_members:
        df_wait = members_to_dataframe(waiting_members, team_id_to_name)
        render_member_editor(df_wait, team_id_to_name, team_name_to_id, client, "Waiting List", dropdowns)
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
        render_member_editor(df_un, team_id_to_name, team_name_to_id, client, "Unassigned", dropdowns)
    else:
        st.info("All members are assigned to teams.")


# -----------------------------------------------------
# Confirmed Teams & Members Section
# -----------------------------------------------------
st.markdown("---")
st.subheader("Confirmed Teams & Members")
st.caption("View and manage all confirmed teams and their members. Edit participant details, reassign members to different teams, or delete entire teams (members will be unassigned). Each team can hold up to 5 members.")

confirmed_team_count = len(teams_data)
confirmed_member_count = sum(len(t.get("members") or []) for t in teams_data)

c1, c2 = st.columns(2)
c1.metric("Confirmed Teams", confirmed_team_count)
c2.metric("Members Assigned to Confirmed Teams", confirmed_member_count)

for team in teams_data:
    team_members = team.get("members") or []

    with st.expander(f"{team['team_name']} — Route: {team.get('route','')} ({len(team_members)}/5 Members)"):

        if team_members:
            df_team = members_to_dataframe(team_members, team_id_to_name)
            render_member_editor(df_team, team_id_to_name, team_name_to_id, client, team["team_name"], dropdowns)
        else:
            st.info("No members assigned to this team.")

        # Delete Team (with confirmation)
        with st.container():
            st.markdown("**Delete Team:**")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(team['team_name'])
            
            with col2:
                if st.button(f"⌦ Delete", key=f"del_team_btn_{team['id']}", use_container_width=True):
                    st.session_state["confirm_delete_team"] = team["id"]
            
            # Confirmation dialog
            if st.session_state.get("confirm_delete_team") == team["id"]:
                st.error(f"⚠︎ Delete team '{team['team_name']}'? Members will be unassigned.")
                
                col_confirm, col_cancel = st.columns([1, 1])
                
                with col_confirm:
                    if st.button("✔ Confirm", key=f"confirm_yes_{team['id']}", use_container_width=True):
                        delete_team(team["id"], client)
                        st.session_state["confirm_delete_team"] = None
                        st.rerun()
                
                with col_cancel:
                    if st.button("✖ Cancel", key=f"confirm_no_{team['id']}", use_container_width=True):
                        st.session_state["confirm_delete_team"] = None
                        st.rerun()


# -----------------------------------------------------
# Confirmed Teams & Members Section
# -----------------------------------------------------
st.markdown("---")
st.subheader("Teams on the Waiting List")
st.caption("View and manage all teams on the waiting list.")

unassigned_teams_data = (
    client.table("teams")
    .select("id, team_name, route, on_waiting_list, members(*)")
    .eq("on_waiting_list", True)
    .execute()
    .data
    or []
)

team_waiting_dropdowns = {
    "Team Name": st.column_config.TextColumn("Team Name"),
    "Route": st.column_config.SelectboxColumn("Route", options=["Peak", "Tough", "Tougher"]),
    "On Waiting List": st.column_config.CheckboxColumn("On Waiting List"),
}

with st.expander(f"Teams on Waiting List ({len(unassigned_teams_data)})", expanded=False):
    if unassigned_teams_data:
        df_waiting_teams = teams_to_dataframe(unassigned_teams_data)
        render_team_editor(df_waiting_teams, client, "WaitingListTeams", team_waiting_dropdowns)
    else:
        st.info("No teams are currently on the waiting list.")

    
# -----------------------------------------------------
# EXPORT BUTTON
# -----------------------------------------------------
excel_file = export_excel(client)
volunteers_excel = export_volunteers_excel(client)

st.markdown("---")
st.subheader("Export Data")
st.caption("Download a comprehensive Excel file (.xlsx) containing all participants, sorted by team and waiting list status. Use this for reporting, planning, or offline record-keeping.")

st.download_button(
    label="Export & Download Teams.xlsx",
    data=excel_file.getvalue(),
    file_name="teams.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.download_button(
    label="Export & Download Volunteers.xlsx",
    data=volunteers_excel.getvalue(),
    file_name="volunteers.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

back_button("Home.py")
