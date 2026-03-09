import streamlit as st
import pandas as pd
from uuid import uuid4

from helpers import (
    init_page,
    get_authenticated_supabase,
    members_to_dataframe,
    sanitize_text,
    verify_microsoft_id_token,
    apply_member_updates,
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
try:
    decoded = verify_microsoft_id_token(token["id_token"])
except Exception:
    st.error("✖ Invalid login session. Please sign in again.")
    back_button("Home.py")
    st.write("---")
    st.stop()

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
    .select(
        "id, team_id, role, full_name, employee_email, employee_id, mobile_number, organisation, "
        "preferred_route, shirt_size, forces_vet, camping_fri, camping_sat, taking_car, travelling_from, "
        "notes, hiking_experience, on_waiting_list, dropped_out, volunteering_area"
    )
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
        st.switch_page("pages/1_Agreement.py")

    back_button("Home.py")
    st.stop()

# -----------------------------------------------------
# 4) Self-service: edit your own registration details
# -----------------------------------------------------
st.write("---")
st.markdown("### Your Registration")
st.caption("View and update your individual registration details below.")

volunteering_area_text = (current_user.get("volunteering_area") or "").strip()
has_volunteering = bool(volunteering_area_text)

VOLUNTEER_AREA_OPTIONS_ALL = [
    "Communications and Marketing (including Getting our Walkers Challenge Ready!)",
    "Pre-Event Organisation",
    "Merchandise Support (Source, Design, and Order)",
    "Setting up the DXC tent and Merch distrubition",
    "Participant support on the day",
]

VOLUNTEER_AREA_OPTIONS_BOTH = [
    "Communications and Marketing (including Getting our Walkers Challenge Ready!)",
    "Pre-Event Organisation",
    "Merchandise Support (Source, Design, and Order)",
]

walking_fields_present = any(
    (current_user.get(k) not in [None, "", False])
    for k in [
        "preferred_route",
        "shirt_size",
        "camping_fri",
        "camping_sat",
        "taking_car",
        "travelling_from",
        "notes",
        "hiking_experience",
    ]
)

is_volunteer_only = has_volunteering and not walking_fields_present and not current_user.get("team_id")

team_id = current_user.get("team_id")

team_lookup = {}
team_name_to_id = {}
team = None

if team_id:
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
    if team:
        team_lookup = {team_id: team.get("team_name")}
        team_name_to_id = {team.get("team_name"): team_id}

df_self = members_to_dataframe([current_user], team_lookup)

if is_volunteer_only:
    volunteer_only_columns = [
        "Employee ID",
        "Mobile Number",
        "Organisation",
        "Forces Veteran",
    ]

    df_volunteer_view = df_self[volunteer_only_columns].copy()

    volunteer_column_config = {
        "Organisation": st.column_config.SelectboxColumn(
            "Organisation",
            options=["L-ES", "L-CSC", "Velonetic", "CSC"],
        ),
        "Forces Veteran": st.column_config.CheckboxColumn("Forces Veteran"),
    }

    edited_volunteer = st.data_editor(
        df_volunteer_view,
        width="stretch",
        num_rows="fixed",
        hide_index=True,
        column_config=volunteer_column_config,
        disabled=[],
        key="volunteer_only_editor",
    )

    edited_volunteer["id"] = df_self["id"]
    original_volunteer = df_self[["id"] + volunteer_only_columns].copy()

    applied_volunteer = apply_member_updates(edited_volunteer, original_volunteer, team_name_to_id, client)
    if applied_volunteer > 0:
        st.success("Saved.")
        st.rerun()

    current_selected = [a.strip() for a in volunteering_area_text.split(",") if a.strip()]
    current_selected = [a for a in current_selected if a in VOLUNTEER_AREA_OPTIONS_ALL]
    selected_areas = st.multiselect(
        "Volunteer Area",
        VOLUNTEER_AREA_OPTIONS_ALL,
        default=current_selected,
    )

    if st.button("Save Volunteer Areas", key="save_volunteer_areas_volunteer_only"):
        try:
            updated_value = ", ".join(selected_areas) if selected_areas else None
            client.table("members").update({"volunteering_area": updated_value}).eq("id", current_user.get("id")).execute()
            st.success("Saved.")
            st.rerun()
        except Exception as e:
            st.error("Could not save your volunteer areas.")
            st.exception(e)

    back_button("Home.py")
    st.stop()

self_visible_columns = [
    "Team Name",
    "Role",
    "Full Name",
    "Employee Email",
    "Employee ID",
    "Mobile Number",
    "Organisation",
    "Preferred Route",
    "Shirt Size",
    "Forces Veteran",
    "Camping Friday",
    "Camping Saturday",
    "Taking Car",
    "Travelling From",
    "Hiking Experience",
    "Notes",
    "On Waiting List",
    "Dropped Out",
]

df_self_view = df_self[self_visible_columns].copy()
df_self_ids = df_self.copy()

self_dropdowns = {
    "Organisation": st.column_config.SelectboxColumn("Organisation", options=["L-ES", "L-CSC", "Velonetic", "CSC"]),
    "Preferred Route": st.column_config.SelectboxColumn("Preferred Route", options=["Peak", "Tough", "Tougher"]),
    "Shirt Size": st.column_config.SelectboxColumn("Shirt Size", options=["XS", "S", "M", "L", "XL", "XXL"]),
    "Forces Veteran": st.column_config.CheckboxColumn("Forces Veteran"),
    "Camping Friday": st.column_config.CheckboxColumn("Camping Friday"),
    "Camping Saturday": st.column_config.CheckboxColumn("Camping Saturday"),
    "Taking Car": st.column_config.CheckboxColumn("Taking Car"),
    "On Waiting List": st.column_config.CheckboxColumn("On Waiting List"),
    "Dropped Out": st.column_config.CheckboxColumn("Dropped Out"),
    "Notes": st.column_config.TextColumn("Notes"),
    "Hiking Experience": st.column_config.TextColumn("Hiking Experience"),
    "Travelling From": st.column_config.TextColumn("Travelling From"),
}

disabled_columns = [
    "Team Name",
    "Role",
    "Full Name",
    "Employee Email",
    "On Waiting List",
    "Dropped Out",
]

# Hide non-editable columns from the self-service editor
self_editable_columns = [c for c in self_visible_columns if c not in disabled_columns]
df_self_view = df_self[self_editable_columns].copy()

edited_self = st.data_editor(
    df_self_view,
    width="stretch",
    num_rows="fixed",
    hide_index=True,
    column_config=self_dropdowns,
    disabled=[],
    key="self_editor",
)

edited_self["id"] = df_self_ids["id"]
original_self = df_self_ids.copy()

applied_self = apply_member_updates(edited_self, original_self, team_name_to_id, client)
if applied_self > 0:
    st.success("Saved.")
    st.rerun()

if walking_fields_present and not is_volunteer_only:
    st.write("---")
    st.subheader("Volunteer Areas")

    if not has_volunteering:
        st.caption("If you would like update your details to volunteer as well as walk, please select which area's you would be happy to support with:")
    else:
        st.caption("You have signed up as a volunteer, please select & update which area's you would be happy to support with:")

    current_selected = [a.strip() for a in volunteering_area_text.split(",") if a.strip()]
    current_selected = [a for a in current_selected if a in VOLUNTEER_AREA_OPTIONS_BOTH]

    selected_areas = st.multiselect(
        "Volunteer Area",
        VOLUNTEER_AREA_OPTIONS_BOTH,
        default=current_selected,
    )

    if st.button("Save Volunteer Areas", key="save_volunteer_areas_both"):
        try:
            updated_value = ", ".join(selected_areas) if selected_areas else None
            client.table("members").update({"volunteering_area": updated_value}).eq("id", current_user.get("id")).execute()
            st.success("Saved.")
            st.rerun()
        except Exception as e:
            st.error("Could not save your volunteer areas.")
            st.exception(e)

if not team_id:
    st.write("---")
    if current_user.get("on_waiting_list") is True:
        st.info(
            "You are currently on the waiting list. Please return to this page once you have been contacted to assign yourself to a team."
        )
    elif current_user.get("on_waiting_list") is False:
        teams = (
            client
            .table("teams")
            .select("id, team_name, route, on_waiting_list")
            .eq("on_waiting_list", False)
            .order("team_name")
            .execute()
            .data
            or []
        )

        team_member_counts = {}
        try:
            mres = client.table("members").select("team_id").execute()
            for m in (mres.data or []):
                tid = m.get("team_id")
                if tid:
                    team_member_counts[tid] = team_member_counts.get(tid, 0) + 1
        except Exception:
            pass

        eligible_teams = [
            t for t in teams
            if team_member_counts.get(t.get("id"), 0) < 5
        ]

        if eligible_teams:
            team_options = {
                f"{t.get('team_name')} — {t.get('route', 'Not set')} ({team_member_counts.get(t.get('id'), 0)}/5)": t.get("id")
                for t in eligible_teams
            }

            st.markdown("### Join an Available Team")
            st.caption("You're not currently assigned to a team. If you'd like to join one, select a team below. Only teams with available spaces are shown.")
            selected_label = st.selectbox(
                "Select a team to join",
                options=list(team_options.keys()),
            )
            selected_team_id = team_options[selected_label]

            if st.button("Join Team"):
                try:
                    team_row = (
                        client.table("teams")
                        .select("id, on_waiting_list")
                        .eq("id", selected_team_id)
                        .limit(1)
                        .execute()
                        .data
                        or []
                    )
                    if not team_row or team_row[0].get("on_waiting_list") is True:
                        st.error("That team is no longer available.")
                        st.stop()

                    latest_res = (
                        client.table("members")
                        .select("id", count="exact")
                        .eq("team_id", selected_team_id)
                        .execute()
                    )
                    latest_count = latest_res.count or 0

                    if latest_count >= 5:
                        st.error("This team is now full. Please select another team.")
                        st.stop()

                    client.table("members").update({"team_id": selected_team_id, "role": "Member"}).eq("id", current_user.get("id")).execute()
                    st.success("Joined team.")
                    st.rerun()
                except Exception as e:
                    st.error("Could not join the selected team.")
                    st.exception(e)
        else:
            st.info("There are currently no teams available to join (teams may be full or on the waiting list). Please contact an admin.")

    back_button("Home.py")
    st.stop()

# -----------------------------------------------------
# 5) Load team + members
# -----------------------------------------------------
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
# 6) Display team
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

    with st.expander("Update team route", expanded=False):
        route_options = ["Peak", "Tough", "Tougher"]
        current_route = team.get("route") if team.get("route") in route_options else route_options[0]
        new_route = st.selectbox("Route", route_options, index=route_options.index(current_route))

        if st.button("Update Team Route"):
            try:
                client.table("teams").update({"route": new_route}).eq("id", team_id).execute()
                st.success("Team route updated.")
                st.rerun()
            except Exception as e:
                st.error("Could not update the team route.")
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
