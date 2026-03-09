import streamlit as st
from uuid import uuid4

from helpers import (
    init_page,
    hide_sidebar,
    back_button,
    remove_st_branding,
)


st.session_state.setdefault("SessionID", str(uuid4()))

init_page("Agreement")
remove_st_branding()
hide_sidebar()

st.write("---")
st.subheader("Participation & Volunteering Agreement")
st.markdown("""
To participate you must agree to:

- You can sign up as both a walker and a volunteer. Some volunteer roles may not be compatible with taking part as a walker.
- Participation is at your own risk  
- Attendance at DXC briefings prior to event  
- Mandatory safety briefings at campsite  
- DXC is not responsible for loss/damage of items  
- Choose a route within your ability  
- Raise an individual minimum of **£150**, or a team minimum of **£600** (4 members), or **£750** (5 members) in fundraising

By volunteering you must also agree to:

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

st.session_state["agreement_confirmed"] = True
st.success("✔ Agreement confirmed — continue below.")

if st.button("Continue to Personal Details →", type="primary"):
    st.switch_page("pages/1_Personal.py")
