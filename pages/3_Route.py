# pages/3_Route_1.py
import streamlit as st
from uuid import uuid4
from streamlit.components.v1 import html
import matplotlib.pyplot as plt
import folium

from helpers import (
    init_page,
    hide_sidebar,
    back_button,
    load_gpx_points,
    compute_track_stats,
    trim_outliers,
    expanded_bounds,
    mid_route_center,
    remove_st_branding,
)

# --------------------------------
# App scaffolding (unchanged flow)
# --------------------------------
st.session_state.setdefault("SessionID", str(uuid4()))
st.session_state.setdefault("draft", {})
draft = st.session_state["draft"]

# Require previous steps
if not draft.get("full_name"):
    st.warning("Please complete Personal Details first.")
    st.switch_page("pages/1_Personal.py")

if "team_id" not in draft:
    st.info("Please confirm Team selection (or choose Independently).")
    st.switch_page("pages/2_Team.py")

user_email = st.session_state.get("user_email", "")
user_name = st.session_state.get("user_name", "")

init_page("Step 3: Route Selection")
st.markdown("---")
remove_st_branding()
hide_sidebar()

# ---------- NEW: Dark-mode compatible CSS ----------
st.markdown("""
<style>
.route-card {
    border: 1px solid var(--secondary-background-color);
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0 10px 0;
}

.route-card h4 {
    margin: 0 0 6px 0;
    color: var(--text-color);
}

.route-card .route-value {
    font-size: 18px;
    font-weight: bold;
    margin: 0;
}

.route-note {
    border-left: 4px solid #f0ad4e;
    background: var(--background-color);
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 10px;
    color: var(--text-color);
}
</style>
""", unsafe_allow_html=True)
# ---------------------------------------------------


team_route = draft.get("team_route")

# -------------------------
# Route metadata + file map
# -------------------------
ROUTE_FILES = {
    "Peak": {
        "difficulty": "Easy",
        "color": "green",
        "default_path": "assets/peak.gpx",
        "ascent_hint_m": 631,
    },
    "Tough": {
        "difficulty": "Moderate",
        "color": "orange",
        "default_path": "assets/tough.gpx",
        "ascent_hint_m": 1140,
    },
    "Tougher": {
        "difficulty": "Hard",
        "color": "red",
        "default_path": "assets/tougher.gpx",
        "note": "Requires prior endurance experience and full team",
        "ascent_hint_m": 1570,
    },
}

if team_route:
    st.info(
        f"Your team's route is **{team_route}**. "
        "If you choose a different route, you will continue independently."
    )

# Default selection logic
existing_route = draft.get("preferred_route")
default_index = 0
if team_route and team_route in ROUTE_FILES:
    default_index = list(ROUTE_FILES.keys()).index(team_route)
elif existing_route and existing_route in ROUTE_FILES:
    default_index = list(ROUTE_FILES.keys()).index(existing_route)

# -------------------------------------------
# LAYOUT: Left controls/cards + big map right
# -------------------------------------------
left, right = st.columns([1, 3], gap="large")

with left:
    selected_route = st.selectbox("Choose Your Route", list(ROUTE_FILES.keys()), index=default_index)
    picked = ROUTE_FILES[selected_route]

    if team_route and selected_route == team_route and st.session_state.get("route_pending_confirmation"):
        st.session_state["route_pending_confirmation"] = False
        st.session_state["route_selection_temp"] = None

    # Difficulty card (UPDATED)
    st.markdown(f"""
    <div class="route-card">
      <h4>Difficulty</h4>
      <p class="route-value" style="color:{picked['color']};">{picked['difficulty']}</p>
    </div>
    """, unsafe_allow_html=True)

# -------------------------
# Load GPX + compute stats
# -------------------------
gpx_path = ROUTE_FILES[selected_route]["default_path"]
points_raw = load_gpx_points(gpx_path)

if not points_raw:
    with left:
        st.error(
            f"GPX for **{selected_route}** not found or unreadable at `{gpx_path}`.\n"
            "Please add the file and reload the page."
        )

        st.download_button(
            "⬇️ Download GPX (unavailable)",
            data=b"",
            file_name=f"{selected_route.lower()}_route.gpx",
            mime="application/gpx+xml",
            disabled=True,
        )

        st.session_state.setdefault("route_pending_confirmation", False)
        st.session_state.setdefault("route_selection_temp", None)

        if st.button("✅ Confirm Route"):
            if team_route and selected_route != team_route:
                st.session_state["route_selection_temp"] = selected_route
                st.session_state["route_pending_confirmation"] = True
                st.rerun()
            else:
                draft.update({"preferred_route": selected_route, "individual_override": False})
                st.session_state["draft"] = draft
                st.success("Route saved!")
                st.switch_page("pages/4_Logistics.py")
else:
    stats_raw = compute_track_stats(points_raw)

    ascent_show = (
        stats_raw["ascent_m"]
        if stats_raw["ascent_m"] and stats_raw["ascent_m"] > 0
        else ROUTE_FILES[selected_route].get("ascent_hint_m")
    )
    ascent_text = f"{int(ascent_show)} m" if ascent_show else "—"

    points_trim = trim_outliers(points_raw, q=0.01)
    stats_trim = compute_track_stats(points_trim)

    with left:
        # Distance card (UPDATED)
        st.markdown(f"""
        <div class="route-card">
          <h4>Distance</h4>
          <p class="route-value">{stats_raw['distance_km']:.2f} km</p>
        </div>
        """, unsafe_allow_html=True)

        # Ascent card (UPDATED)
        st.markdown(f"""
        <div class="route-card">
          <h4>Ascent</h4>
          <p class="route-value">{ascent_text}</p>
        </div>
        """, unsafe_allow_html=True)

        # Note card (UPDATED)
        if ROUTE_FILES[selected_route].get("note"):
            st.markdown(f"""
            <div class="route-note">
              <small>{ROUTE_FILES[selected_route]['note']}</small>
            </div>
            """, unsafe_allow_html=True)

        try:
            with open(gpx_path, "rb") as f:
                gpx_bytes = f.read()
            st.download_button(
                "⬇️ Download Route (GPX)",
                data=gpx_bytes,
                file_name=f"{selected_route.lower()}_route.gpx",
                mime="application/gpx+xml",
            )
        except Exception as e:
            st.error(f"Error loading GPX for download: {e}")
            st.download_button(
                "⬇️ Download GPX (error)",
                data=b"",
                disabled=True
            )

        # Confirm route
        st.session_state.setdefault("route_pending_confirmation", False)
        st.session_state.setdefault("route_selection_temp", None)

        if st.button("✅ Confirm Route"):
            if team_route and selected_route != team_route:
                st.session_state["route_selection_temp"] = selected_route
                st.session_state["route_pending_confirmation"] = True
                st.rerun()
            else:
                draft.update({"preferred_route": selected_route, "individual_override": False})
                st.session_state["draft"] = draft
                st.success("Route saved!")
                st.switch_page("pages/4_Logistics.py")

        if st.session_state.get("route_pending_confirmation"):
            st.warning(
                "You selected a different route than your team. "
                "If you confirm, you will continue as an individual."
            )
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Continue as Individual"):
                    draft.update({
                        "preferred_route": st.session_state["route_selection_temp"],
                        "individual_override": True,
                    })
                    st.session_state["draft"] = draft
                    st.session_state["route_pending_confirmation"] = False
                    st.success("Route saved — proceeding as an individual.")
                    st.switch_page("pages/4_Logistics.py")
            with cc2:
                if st.button("Return to Team Selection"):
                    st.session_state["route_pending_confirmation"] = False
                    st.switch_page("pages/2_Team.py")

    with right:
        MAP_HEIGHT = 800
        coords_raw = [(lat, lon) for (lat, lon, _ele) in points_raw]

        min_lat, min_lon, max_lat, max_lon = expanded_bounds(points_raw, margin_frac=0.08)
        centre_latlon = mid_route_center(points_trim, stats_trim["cum_dist_km"])

        try:
            m = folium.Map(location=centre_latlon, zoom_start=13, tiles="OpenTopoMap")

            folium.PolyLine(
                coords_raw,
                color="#6A307D",
                weight=9,
                opacity=0.95
            ).add_to(m)

            folium.Marker(coords_raw[0], popup="Start", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(coords_raw[-1], popup="End", icon=folium.Icon(color="red")).add_to(m)

            m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

            html(m._repr_html_(), height=MAP_HEIGHT)
        except Exception as e:
            st.error(f"Map render error: {e}")

back_button("pages/2_Team.py")
