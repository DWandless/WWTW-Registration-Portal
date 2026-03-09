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
init_page("Volunteer details")
remove_st_branding()
hide_sidebar()

# -------------------------------------------------------------------
# Participation Agreement
# -------------------------------------------------------------------
st.write("---")
st.subheader("Volunteers Agreement")
st.markdown("""
By volunteering you must agree to: 

- You can sign up as both a walker and a volunteer. Some volunteer roles may not be compatible with taking part as a walker.
- You will be representing DXC whilst volunteering at the event
- DXC will fund your travel, camping and food and in return we ask you commit to the volunteering
- Attend any DXC briefing sessions prior to attendance.
- Mandatory attendance at safety briefings at the campsite.
- DXC cannot be held responsible for any lost or damaged personal items.
- There is no expectation of fundraising for WWTW as your volunteer time is appreciated, however we do encourage you to support the fundraising of our walkers! 
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

AREA_OPTIONS = ["Communications and Marketing (including Getting our Walkers Challenge Ready!)", 
                "Pre-Event Organisation", 
                "Merchandise Support (Source, Design, and Order)", 
                "Setting up the DXC tent and Merch distrubition",
                "Participant support on the day"]

LIMITED_AREA = "Participant support on the day"
LIMITED_AREA_LIMIT = 20

client = get_authenticated_supabase()

limit_area_count = 0

try:
    res = (
        client.table("volunteers")
        .select("id", count="exact")
        .ilike("area", f"%{LIMITED_AREA}%")
        .execute()
    )
    limit_area_count = res.count or 0
except Exception:
    pass




defaults = {
    "full_name": draft.get("full_name") or user_name,
    "employee_email": draft.get("employee_email") or user_email,
    "employee_id": draft.get("employee_id") or "",
    "area": draft.get("area") or [],
    "mobile_number": draft.get("mobile_number") or "",
}

if not isinstance(defaults["area"], list):
    defaults["area"] = []

available_area_options = AREA_OPTIONS.copy()

participant_support_is_full = limit_area_count >= LIMITED_AREA_LIMIT

if (
    participant_support_is_full
    and LIMITED_AREA not in defaults["area"]
):
    available_area_options.remove(LIMITED_AREA)

if participant_support_is_full:
    st.info("Availability for 'Participant support on the day' is currently full.")


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


# -------------------------------------------------------------------
# Form UI
# -------------------------------------------------------------------


with st.form("personal_form"):
    full_name = st.text_input("Full Name *", value=defaults["full_name"])
    employee_email = st.text_input("DXC Email *", value=defaults["employee_email"])
    employee_id = st.text_input("Employee ID *", value=defaults["employee_id"])
    mobile_number = st.text_input("Mobile (optional)", value=defaults["mobile_number"])

    area = st.multiselect(
        "Volunteer Area *",
        available_area_options,
        default = defaults["area"],
    )



    submitted = st.form_submit_button("Submit")

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
    area_clean = ", ".join([sanitize_text(a) for a in area])

    draft.update({
        "full_name": full_name_clean,
        "employee_email": email_clean,
        "employee_id": employee_id_clean,
        "mobile_number": mobile_clean or None,
        "area": area_clean,
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

        # Event not full OR active user
    final_record = prepare_member_record(draft, False, client)
    try:
        res = client.table("volunteers").insert(final_record).execute()
        new_id = res.data[0]["id"]
        st.session_state["member_id"] = new_id
        st.success("Thank you for volunteering to help out!")
        st.switch_page("pages/6_Thanks!.py")
    except Exception as e:
        st.error("Could not register your details.")
        st.exception(e)


back_button("Home.py")
