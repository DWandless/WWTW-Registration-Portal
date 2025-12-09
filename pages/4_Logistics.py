# pages/4_Logistics.py
import streamlit as st
from uuid import uuid4
from helpers import init_page, hide_sidebar, back_button, sanitize_text, remove_st_branding

import re
import unicodedata


# -------------------------------------------------------
# Sanitization + Validation Utilities
# -------------------------------------------------------

def sanitize_free_text(value: str, max_len: int = 500) -> str:
    """
    Sanitize long free-text fields such as notes and experience.
    - Normalizes unicode
    - Removes control characters
    - Removes angle brackets entirely (< >) to prevent script injection
    - Limits length
    """
    value = sanitize_text(value)
    value = re.sub(r"[<>]", "", value)  # Remove HTML/script brackets
    return value[:max_len]

def validate_logistics(travelling_from: str, notes: str, experience: str, required_experience: bool):
    """Validate and sanitize all logistics fields."""
    travelling_from_clean = sanitize_free_text(travelling_from, 120)
    notes_clean = sanitize_free_text(notes, 500)
    experience_clean = sanitize_free_text(experience, 500)

    # Required when route is Tougher
    if required_experience and not experience_clean:
        return False, "Hiking experience is required for the Tougher route.", None

    return True, "", {
        "travelling_from": travelling_from_clean or None,
        "notes": notes_clean or None,
        "experience": experience_clean or None,
    }


# -------------------------------------------------------
# Session Initialisation
# -------------------------------------------------------

st.session_state.setdefault("SessionID", str(uuid4()))
draft = st.session_state.setdefault("draft", {})

user_email = (st.session_state.get("user_email", "") or "").lower()
user_name = (st.session_state.get("user_name", "") or "").strip()

# Page
init_page("Step 4: Logistics")
remove_st_branding()
hide_sidebar()


# -------------------------------------------------------
# Form Defaults
# -------------------------------------------------------

preferred_route = draft.get("preferred_route")
shirt_sizes = ["XS", "S", "M", "L", "XL", "XXL"]

defaults = {
    "shirt_size": draft.get("shirt_size", "M"),
    "camping_fri": draft.get("camping_fri", False),
    "camping_sat": draft.get("camping_sat", False),
    "taking_car": draft.get("taking_car", False),
    "travelling_from": draft.get("travelling_from", ""),
    "notes": draft.get("notes", ""),
    "experience": draft.get("hiking_experience", ""),
}


# -------------------------------------------------------
# UI
# -------------------------------------------------------

with st.form("logistics_form", clear_on_submit=False):

    st.selectbox(
        "T-shirt Size *",
        shirt_sizes,
        key="tshirt",
        index=shirt_sizes.index(defaults["shirt_size"]),
    )

    st.text_input(
        "Travelling from",
        key="travelling_from",
        value=defaults["travelling_from"],
        help="Enter the city or area you will travel from."
    )

    st.markdown("**Select all that apply to you:**")
    col1, col2 = st.columns(2)
    with col1:
        st.checkbox("Camping Friday night", key="camping_fri", value=defaults["camping_fri"])
        st.checkbox("Taking a car", key="taking_car", value=defaults["taking_car"])
    with col2:
        st.checkbox("Camping Saturday night", key="camping_sat", value=defaults["camping_sat"])

    # Conditional experience field
    if preferred_route == "Tougher":
        st.text_area(
            "Hiking Experience *",
            key="experience",
            value=defaults["experience"],
            help="Required for participants taking the Tougher route."
        )
    else:
        with st.expander("Additional Info (optional)"):
            st.text_area("Notes", key="notes", value=defaults["notes"])
            st.text_area("Experience", key="experience", value=defaults["experience"])

    submitted = st.form_submit_button("Save & Next →")


# -------------------------------------------------------
# Submit Logic
# -------------------------------------------------------

if submitted:

    # Extract raw values
    travelling_from_raw = st.session_state.get("travelling_from", "")
    notes_raw = st.session_state.get("notes", "")
    experience_raw = st.session_state.get("experience", "")

    # Validate & sanitize
    is_valid, error_msg, cleaned = validate_logistics(
        travelling_from_raw,
        notes_raw,
        experience_raw,
        required_experience=(preferred_route == "Tougher")
    )

    if not is_valid:
        st.error(error_msg)
        st.stop()

    # Save sanitized content
    draft.update({
        "shirt_size": st.session_state["tshirt"],
        "camping_fri": st.session_state["camping_fri"],
        "camping_sat": st.session_state["camping_sat"],
        "taking_car": st.session_state["taking_car"],
        "travelling_from": cleaned["travelling_from"],
        "notes": cleaned["notes"],
        "hiking_experience": cleaned["experience"],
    })

    st.session_state["draft"] = draft
    st.success("Logistics saved!")
    st.switch_page("pages/5_Review.py")


back_button("pages/3_Route.py")
