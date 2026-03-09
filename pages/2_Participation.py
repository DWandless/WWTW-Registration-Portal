import streamlit as st
from uuid import uuid4

from helpers import (
    init_page,
    hide_sidebar,
    back_button,
    remove_st_branding,
)


st.session_state.setdefault("SessionID", str(uuid4()))
st.session_state.setdefault("draft", {})
draft = st.session_state["draft"]

init_page("Step 2: Participation Type")
remove_st_branding()
hide_sidebar()

if not st.session_state.get("agreement_confirmed"):
    st.switch_page("pages/1_Agreement.py")

st.write("---")
st.subheader("How are you taking part?")

participation_options = ["Walking", "Volunteering", "Both"]
current_participation = draft.get("participation_type")
if current_participation not in participation_options:
    current_participation = "Walking"

participation_type = st.selectbox(
    "Select an option",
    participation_options,
    index=participation_options.index(current_participation),
)

AREA_OPTIONS = [
    "Communications and Marketing (including Getting our Walkers Challenge Ready!)",
    "Pre-Event Organisation",
    "Merchandise Support (Source, Design, and Order)",
    "Setting up the DXC tent and Merch distrubition",
    "Participant support on the day",
]

selected_areas = []
if participation_type in {"Volunteering", "Both"}:
    prior = draft.get("volunteering_area_selection")
    if not isinstance(prior, list):
        prior = []

    selected_areas = st.multiselect(
        "Volunteer Area",
        AREA_OPTIONS,
        default=prior,
    )

st.write("---")

if st.button("Save & Continue →", type="primary"):
    draft["participation_type"] = participation_type

    if participation_type in {"Volunteering", "Both"}:
        draft["volunteering_area_selection"] = selected_areas
        draft["volunteering_area"] = ", ".join(selected_areas)
    else:
        draft.pop("volunteering_area_selection", None)
        draft.pop("volunteering_area", None)

    st.session_state["draft"] = draft
    st.switch_page("pages/1_Personal.py")

back_button("pages/1_Agreement.py")
