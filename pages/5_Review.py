# pages/5_Review.py
import streamlit as st
from helpers import init_page, get_authenticated_supabase, prepare_member_record, hide_sidebar, back_button, remove_st_branding

init_page("Step 5: Review & Submit")

import time

# ---------------------------------------------------------
# Rate limiting config
# ---------------------------------------------------------
SUBMISSION_COOLDOWN = 30  # seconds

# State holders
if "last_submit_time" not in st.session_state:
    st.session_state["last_submit_time"] = 0

if "submission_in_progress" not in st.session_state:
    st.session_state["submission_in_progress"] = False


def can_submit() -> bool:
    """Returns True if enough time passed since last submission."""
    now = time.time()
    last = st.session_state["last_submit_time"]
    return (now - last) >= SUBMISSION_COOLDOWN


# Must have a draft
draft = st.session_state.get("draft")

if draft is None:
    st.switch_page("pages/1_Personal.py")

client = get_authenticated_supabase()

user_email = st.session_state.get("user_email", "")
user_name  = st.session_state.get("user_name", "")
remove_st_branding()
hide_sidebar()

# ------------------------------------------------------------
# Review UI - all values shown from draft, not database
# ------------------------------------------------------------
st.subheader("Review Your Registration")
st.caption("Check your details below. Use the buttons to edit on the original pages.")

# --- Section 1: Personal Details ---
with st.expander("Personal Details", expanded=True):
    st.write(f"**Name:** {draft.get('full_name')}")
    st.write(f"**Email:** {draft.get('employee_email')}")
    st.write(f"**Employee ID:** {draft.get('employee_id')}")
    st.write(f"**Organisation:** {draft.get('organisation')}")
    st.write(f"**Mobile:** {draft.get('mobile_number')}")
    st.write(f"**Forces Veteran:** {'Yes' if draft.get('forces_vet') else 'No'}")
    if st.button("Edit Personal Details"):
        st.switch_page("pages/1_Personal.py")

# --- Section 2: Team Details ---
with st.expander("Team Details", expanded=True):
    st.write(f"**Team Name:** {draft.get('team_name') or 'Independent'}")
    st.write(f"**Team Route:** {draft.get('team_route') or 'Not set'}")
    st.write(f"**Role:** {draft.get('role') or 'N/A'}")
    if st.button("Edit Team Details"):
        st.switch_page("pages/2_Team.py")

# --- Section 3: Route Preference ---
with st.expander("Route Preference", expanded=True):
    st.write(f"**Preferred Route:** {draft.get('preferred_route') or 'Not set'}")
    if st.button("Edit Route"):
        st.switch_page("pages/3_Route.py")

# --- Section 4: Logistics ---
with st.expander("Logistics", expanded=True):
    st.write(f"**Shirt Size:** {draft.get('shirt_size')}")
    st.write(f"**Camping Friday:** {'Yes' if draft.get('camping_fri') else 'No'}")
    st.write(f"**Camping Saturday:** {'Yes' if draft.get('camping_sat') else 'No'}")
    st.write(f"**Taking Car:** {'Yes' if draft.get('taking_car') else 'No'}")
    st.write(f"**Travelling From:** {draft.get('travelling_from')}")
    st.write(f"**Notes:** {draft.get('notes')}")
    st.write(f"**Experience:** {draft.get('hiking_experience')}")
    if st.button("Edit Logistics"):
        st.switch_page("pages/4_Logistics.py")


# ---------------------------------------------------------
# SAFE SUBMIT BUTTON (double-submit + rate limit protected)
# ---------------------------------------------------------

submit_disabled = (
    st.session_state["submission_in_progress"]   # actively saving
    or not can_submit()                          # rate-limited
)

cooldown_remaining = max(
    0, SUBMISSION_COOLDOWN - (time.time() - st.session_state["last_submit_time"])
)

if submit_disabled and cooldown_remaining > 0:
    st.info(f"Please wait {cooldown_remaining:.0f} seconds before submitting again.")

submit = st.button("✔ Confirm & Submit", disabled=submit_disabled)

if submit:
    try:
        # Lock submission so they cannot click twice
        st.session_state["submission_in_progress"] = True

        # Record this attempt timestamp
        st.session_state["last_submit_time"] = time.time()

        # Prepare and sanitize final record
        final_record = prepare_member_record(draft, False, client)

        # Check existing user
        employee_email = draft.get("employee_email", "").lower()
        existing = (
            client.table("members")
            .select("id")
            .eq("employee_email", employee_email)
            .execute()
        )
        existing_member = existing.data[0] if existing.data else None

        # Insert or update
        if existing_member is None:
            res = client.table("members").insert(final_record).execute()
            new_id = res.data[0]["id"]
            st.session_state["member_id"] = new_id
        else:
            member_id = existing_member["id"]
            client.table("members").update(final_record).eq("id", member_id).execute()
            st.session_state["member_id"] = member_id

        st.success("Registration confirmed!")
        st.switch_page("pages/6_Thanks!.py")

    except Exception as e:
        st.error("Could not complete your registration.")
        st.exception(e)

    finally:
        # Unlock submission button
        st.session_state["submission_in_progress"] = False

back_button("pages/4_Logistics.py")
