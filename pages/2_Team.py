# pages/2_Team.py
import streamlit as st
from uuid import uuid4
from helpers import (
    init_page,
    get_authenticated_supabase,
    hide_sidebar,
    back_button,
    sanitize_text,
    remove_st_branding,
)

import re
import unicodedata


# -------------------------------------------------------
# Sanitization + Validation for Team Names
# -------------------------------------------------------

def sanitize_team_name(name: str) -> str:
    """
    Only allow letters, digits, spaces, hyphens, apostrophes.
    Prevents XSS, SQL injection, control chars.
    """
    name = sanitize_text(name)
    name = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ0-9' -]", "", name)
    return name

def is_valid_team_name(name: str) -> bool:
    """
    Team name rules:
    - 2–40 chars after sanitization
    - must contain at least one letter or number
    """
    if not name:
        return False

    if len(name) < 2 or len(name) > 40:
        return False

    # Must contain at least one alphanumeric character
    if not re.search(r"[A-Za-z0-9]", name):
        return False

    return True


# -------------------------------------------------------
# Session initialisation
# -------------------------------------------------------
st.session_state.setdefault("SessionID", str(uuid4()))
st.session_state.setdefault("draft", {})
draft = st.session_state["draft"]

# Require Step 1
if not draft.get("full_name"):
    st.warning("Please complete Personal Details first.")
    st.switch_page("pages/1_Personal.py")

# Load sidebar info
user_email = (st.session_state.get("user_email", "") or "").strip().lower()
user_name = (st.session_state.get("user_name", "") or "").strip()

init_page("Step 2: Team Selection")
remove_st_branding()
hide_sidebar()

# -------------------------------------------------------
# Database utilities
# -------------------------------------------------------

def load_teams(client):
    try:
        team_res = (
            client.table("teams")
            .select("id, team_name, route")
            .order("team_name")
            .execute()
        )
        return team_res.data or []
    except Exception as e:
        st.error("Could not load teams from database.")
        st.exception(e)
        return []

def count_team_members(client, teams):
    team_member_counts = {}
    try:
        mres = client.table("members").select("team_id").execute()
        for m in (mres.data or []):
            tid = m.get("team_id")
            if tid:
                team_member_counts[tid] = team_member_counts.get(tid, 0) + 1
    except Exception:
        pass
    return team_member_counts

def create_team(client, team_name: str, route: str):
    insert_res = client.table("teams").insert({"team_name": team_name, "route": route}).execute()
    created = insert_res.data[0]
    return {"id": created.get("id"), "team_name": team_name, "route": route}


# -------------------------------------------------------
# Load teams
# -------------------------------------------------------
client = get_authenticated_supabase()
teams = load_teams(client)
team_member_counts = count_team_members(client, teams)
st.session_state["teams"] = teams

# -------------------------------------------------------
# Load current draft selection
# -------------------------------------------------------
current_team_id = draft.get("team_id") if "team_id" in draft else None

choice = st.selectbox(
    "Select an option:",
    ["Continue Independently", "Join a Team", "Create a Team"],
    index=(0 if current_team_id is None else 1),
)

st.markdown("---")


# -------------------------------------------------------
# 1. Continue Independently
# -------------------------------------------------------
if choice == "Continue Independently":
    st.info("You will participate without a team.")

    if st.button("Confirm Independent Participation"):
        draft.update({
            "team_id": None,
            "team_name": None,
            "team_route": None,
            "role": "Member",
        })
        st.session_state["draft"] = draft
        st.success("Saved.")
        st.switch_page("pages/3_Route.py")


# -------------------------------------------------------
# 2. Join a Team
# -------------------------------------------------------
elif choice == "Join a Team":
    st.subheader("Available Teams")
    st.info("Select an available team to join")

    if not teams:
        st.warning("No teams exist yet — you can create one below.")
    else:
        cols = st.columns(3)

        for i, t in enumerate(teams):
            with cols[i % 3]:
                tid = t["id"]
                tn = t["team_name"]
                tr = t["route"]
                count = team_member_counts.get(tid, 0)

                is_full = count >= 5

                st.markdown(
                    f"""
### {tn}
Route: **{tr}**  
Members: **{count}**
                    """
                )
                st.progress(min(count / 5, 1.0))

                if is_full:
                    st.button(f"Team Full", key=f"join_{tid}", disabled=True)
                else:
                    if st.button(f"Select {tn}", key=f"join_{tid}"):

                        # Live capacity check
                        try:
                            latest_res = (
                                client.table("members")
                                .select("id", count="exact")
                                .eq("team_id", tid)
                                .execute()
                            )
                            latest_count = latest_res.count or 0
                        except Exception:
                            latest_count = team_member_counts.get(tid, 0)

                        if latest_count >= 5:
                            st.error("This team is now full. Please select another team.")
                            st.stop()

                        draft.update({
                            "team_id": tid,
                            "team_name": tn,
                            "team_route": tr,
                            "role": "Member",
                        })
                        st.session_state["draft"] = draft
                        st.switch_page("pages/3_Route.py")


# -------------------------------------------------------
# 3. Create a Team
# -------------------------------------------------------
elif choice == "Create a Team":
    st.subheader("Create a New Team")
    st.info("If you create a team you will automatically be assigned as the team leader of that team.")

    with st.form("create_team_form"):
        new_name_raw = st.text_input("Team Name *")
        new_route = st.selectbox("Route *", ["Peak", "Tough", "Tougher"])
        submitted = st.form_submit_button("Create Team")

    if submitted:
        # Sanitize input
        new_name = sanitize_team_name(new_name_raw)

        if not is_valid_team_name(new_name):
            st.error("Invalid team name. Use 2–40 letters/numbers, spaces, hyphens, or apostrophes.")
            st.stop()

        # Duplicate check
        if any(sanitize_team_name(t["team_name"]).lower() == new_name.lower() for t in teams):
            st.error("A team with that name already exists.")
            st.stop()

        try:
            new_team = create_team(client, new_name, new_route)
            teams.append(new_team)
            st.session_state["teams"] = teams

            draft.update({
                "team_id": new_team["id"],
                "team_name": new_name,
                "team_route": new_route,
                "role": "Leader",
            })
            st.session_state["draft"] = draft

            st.success("Team created!")
            st.switch_page("pages/3_Route.py")

        except Exception as e:
            st.error("Could not create team in database.")
            st.exception(e)
            st.stop()

back_button("pages/1_Personal.py")
st.write("---")