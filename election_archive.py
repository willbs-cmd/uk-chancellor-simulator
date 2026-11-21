"""Combined archive of general-election and local-election results."""
import pandas as pd
import streamlit as st


def render(s=None):
    s = s or st.session_state
    st.markdown("### Election archive")
    st.caption("A permanent record of simulated Westminster general elections and annual local contests.")
    national = list(s.get("election_history", []))
    if national:
        st.markdown("#### General elections")
        rows = [{
            "Term": item.get("term", 0), "Result": item.get("title", "Election result"),
            "Governing party": item.get("governing_party", "—"),
            "Seats won": item.get("player_seats", 0), "Mandate": item.get("mandate_label", "—"),
            "Turnout": f"{float(item.get('turnout', 0)):.1f}%",
            "Sitting MPs defeated": item.get("defeated_incumbents", 0),
        } for item in reversed(national)]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        latest = national[-1]
        st.caption("Latest seat distribution · " + " · ".join(
            f"{p}: {n}" for p, n in sorted(latest.get("seats", {}).items(), key=lambda x: x[1], reverse=True)
        ))
    else:
        st.info("The first general election will be archived after election night.")
    st.divider()
    local = list(s.get("local_election_history", []))
    if local:
        st.markdown("#### Annual local elections")
        rows = [{
            "Term": item.get("term", 0), "Year": item.get("year", 0),
            "Governing party": item.get("governing_party", "—"),
            "Governing wards": f"{item.get('governing_seats', 0)}/{item.get('total_wards', 0)}",
            "National local vote": f"{float(item.get('vote_share', {}).get(item.get('governing_party'), 0)):.1f}%",
            "Winner": item.get("winner", "—"),
            "Approval impact": f"{float(item.get('approval_change', 0)):+.1f}",
            "Regional groups controlled": item.get("controlled_regions", {}).get(item.get("governing_party"), 0),
        } for item in reversed(local)]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("No local contests have yet been held.")
