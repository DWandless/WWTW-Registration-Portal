# pages/1_Personal.py
import streamlit as st
from uuid import uuid4
from helpers import (
    init_page,
    back_button,
    get_authenticated_supabase,
    prepare_member_record,
    hide_sidebar,
    get_active_member_count,
    sanitize_text,
    remove_st_branding,
)

import re
import unicodedata


# -------------------------------------------------------------------
# Sanitization + Validation
# -------------------------------------------------------------------

def sanitize_name(name: str) -> str:
    """Allow letters, spaces, apostrophes, hyphens only."""
    name = sanitize_text(name)
    name = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ' -]", "", name)
    return name

def is_valid_email(email: str) -> bool:
    """Strict DXC email validation."""
    email = sanitize_text(email).lower()
    pattern = r"^[A-Za-z0-9._%+-]+@dxc\.com$"
    return re.match(pattern, email) is not None

def is_valid_employee_id(emp_id: str) -> bool:
    """Alphanumeric 3–20 characters."""
    emp_id = sanitize_text(emp_id)
    return bool(re.match(r"^[A-Za-z0-9]{3,20}$", emp_id))

def is_valid_mobile(mobile: str) -> bool:
    """Digits + common formatting characters; 7–15 digits."""
    mobile = sanitize_text(mobile)
    if not mobile:
        return True
    stripped = re.sub(r"[ +()-]", "", mobile)
    return stripped.isdigit() and 7 <= len(stripped) <= 15

def validate_form(full_name: str, employee_email: str, employee_id: str, mobile_number: str) -> tuple[bool, str]:
    """Validate all form fields."""
    full_name = sanitize_name(full_name)
    employee_email = sanitize_text(employee_email)
    employee_id = sanitize_text(employee_id)
    mobile_number = sanitize_text(mobile_number)

    missing = []
    if not full_name: missing.append("Full Name")
    if not employee_email: missing.append("DXC Email")
    if not employee_id: missing.append("Employee ID")

    if missing:
        return False, "Please complete required fields: " + ", ".join(missing)

    if not is_valid_email(employee_email):
        return False, "Please enter a valid DXC email (must end with @dxc.com)."

    if not is_valid_employee_id(employee_id):
        return False, "Employee ID must be 3–20 alphanumeric characters."

    if not is_valid_mobile(mobile_number):
        return False, "Mobile number contains invalid characters or wrong length."

    return True, ""


# -------------------------------------------------------------------
# Session Initialisation
# -------------------------------------------------------------------

st.session_state.setdefault("SessionID", str(uuid4()))
st.session_state.setdefault("draft", {})
draft = st.session_state["draft"]

user_email = (st.session_state.get("user_email", "") or "").strip().lower()
user_name_raw = (st.session_state.get("user_name", "") or "").strip()

# Normalise “Last, First” → “First Last”
if "," in user_name_raw:
    last, first = [x.strip() for x in user_name_raw.split(",", 1)]
    user_name = f"{first} {last}"
else:
    user_name = user_name_raw

# Page layout
init_page("Step 1: Personal Details")
remove_st_branding()
hide_sidebar()

# -------------------------------------------------------------------
# Participation Agreement
# -------------------------------------------------------------------

st.subheader("Participation Agreement")
st.markdown("""
To participate you must agree to:

- Participation is at your own risk  
- Attendance at DXC briefings prior to event  
- Mandatory safety briefings at campsite  
- DXC is not responsible for loss/damage of items  
- Choose a route within your ability  
- Raise a minimum of **£150** in sponsorship  
""")

agree = st.checkbox("I have read and agree to all the above terms.")
if not agree:
    st.warning("You must agree before continuing.")
    back_button("Home.py")
    st.stop()
st.success("✔ Agreement confirmed — continue below.")

# -------------------------------------------------------------------
# Defaults (from draft, not DB)
# -------------------------------------------------------------------

ORG_OPTIONS = ["L-ES", "L-CSC", "Velonetic"]
client = get_authenticated_supabase()

defaults = {
    "full_name": draft.get("full_name") or user_name,
    "employee_email": draft.get("employee_email") or user_email,
    "employee_id": draft.get("employee_id") or "",
    "organisation": draft.get("organisation") or None,
    "mobile_number": draft.get("mobile_number") or "",
    "forces_vet": bool(draft.get("forces_vet")),
}

if defaults["organisation"] not in ORG_OPTIONS:
    defaults["organisation"] = None

# Check if user already exists
employee_email_lower = (defaults["employee_email"] or "").lower()
existing_user = None
user_on_waiting_list = False
try:
    if employee_email_lower:
        existing_res = (
            client.table("members")
            .select("id, on_waiting_list")
            .eq("employee_email", employee_email_lower)
            .execute()
        )
        existing_user = existing_res.data[0] if existing_res.data else None
        if existing_user:
            user_on_waiting_list = existing_user.get("on_waiting_list", False)
except Exception:
    pass

# Check if event is full
current_count = get_active_member_count(client)
event_is_full = current_count >= 200

if event_is_full:
    st.warning("⚠︎ The event is currently full. If you aren't updating your information, your details will be added to the waiting list instead.")

# -------------------------------------------------------------------
# Form UI
# -------------------------------------------------------------------

with st.form("personal_form"):
    full_name = st.text_input("Full Name *", value=defaults["full_name"])
    employee_email = st.text_input("DXC Email *", value=defaults["employee_email"])
    employee_id = st.text_input("Employee ID *", value=defaults["employee_id"])

    organisation = st.selectbox(
        "Organisation *",
        ORG_OPTIONS,
        index=ORG_OPTIONS.index(defaults["organisation"]) if defaults["organisation"] else 0,
    )

    mobile_number = st.text_input("Mobile (optional)", value=defaults["mobile_number"])
    forces_vet = st.checkbox(
        "Please tick this box if you are a Forces Veteran",
        value=defaults["forces_vet"],
    )

    submitted = st.form_submit_button("Save & Next →")

# -------------------------------------------------------------------
# On Submit
# -------------------------------------------------------------------

if submitted:
    is_valid, error_msg = validate_form(full_name, employee_email, employee_id, mobile_number)
    if not is_valid:
        st.error(error_msg)
        st.stop()

    # Sanitized values
    full_name_clean = sanitize_name(full_name)
    email_clean = sanitize_text(employee_email).lower()
    employee_id_clean = sanitize_text(employee_id)
    mobile_clean = sanitize_text(mobile_number)

    draft.update({
        "full_name": full_name_clean,
        "employee_email": email_clean,
        "employee_id": employee_id_clean,
        "organisation": organisation,
        "mobile_number": mobile_clean or None,
        "forces_vet": forces_vet,
    })
    st.session_state["draft"] = draft

    # Re-check for existing user with updated email
    submitted_email = draft.get("employee_email", "").lower()
    user_exists = False
    existing_member_at_submit = None

    try:
        if submitted_email:
            existing_check = (
                client.table("members")
                .select("id, on_waiting_list")
                .eq("employee_email", submitted_email)
                .execute()
            )
            existing_member_at_submit = (
                existing_check.data[0] if existing_check.data else None
            )
            user_exists = bool(existing_member_at_submit)
    except Exception:
        pass

    # Logic
    if event_is_full and not user_exists:
        # NEW + FULL ⇒ waiting list
        final_record = prepare_member_record(draft, True, client)
        try:
            res = client.table("members").insert(final_record).execute()
            new_id = res.data[0]["id"]
            st.session_state["member_id"] = new_id
            st.success("Thank you for registering!")
            st.switch_page("pages/6_Thanks!.py")
        except Exception as e:
            st.error("Could not add you to the waiting list.")
            st.exception(e)

    elif event_is_full and user_exists and existing_member_at_submit.get("on_waiting_list", False):
        # WAITING LIST + STILL FULL ⇒ cannot proceed
        st.info("You are currently on the waiting list. You cannot edit your details while the event is full.")
        st.stop()

    else:
        # Event not full OR active user
        st.success("Personal details saved!")
        st.switch_page("pages/2_Team.py")

back_button("Home.py")
