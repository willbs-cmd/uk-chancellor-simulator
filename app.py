"""UK Chancellor Simulator (Hardcore Mode): the Streamlit UI.
All game rules live in engine.py.

IMF economic outlook is included directly in this file.
"""

import pandas as pd
import streamlit as st

import achievements
import budget
import country
import engine
import scenarios as scen
import state

from state import CARDS_ECON, CARDS_POLITICAL, CARDS_TOP

from theme import (
    apply_theme,
    crisis_card,
    event_card,
    header,
    humphrey_message,
    news_box,
    render_cards,
    render_newspapers,
    render_polls,
    render_scorecard,
    render_timeline,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="UK Chancellor Simulator - Hardcore",
    layout="wide",
    page_icon="🏛️",
    initial_sidebar_state="collapsed",
)

apply_theme()
state.ensure_init()
s = st.session_state


# ============================================================
# IMF THREE-YEAR ECONOMIC OUTLOOK
# ============================================================
#
# Source:
# IMF United Kingdom 2026 Article IV Consultation
# July 16, 2026.
#
# These are IMF staff projections, not guaranteed outcomes.
#
# Debt figure is PSNFL (Public Sector Net Financial Liabilities),
# which is NOT the same measure as the simulator's debt variable.
#
# IMF projections:
#
# 2026:
# GDP growth       1.0%
# CPI average      3.2%
# Unemployment     5.6%
# Public balance  -4.0% GDP
# PSNFL            83.9% GDP
#
# 2027:
# GDP growth       1.3%
# CPI average      2.4%
# Unemployment     5.3%
# Public balance  -3.3% GDP
# PSNFL            84.4% GDP
#
# 2028:
# GDP growth       1.7%
# CPI average      2.0%
# Unemployment     4.8%
# Public balance  -2.8% GDP
# PSNFL            84.7% GDP
# ============================================================

IMF_OUTLOOK = {
    2026: {
        "growth": 1.0,
        "inflation": 3.2,
        "unemployment": 5.6,
        "balance": -4.0,
        "psnfl": 83.9,
    },
    2027: {
        "growth": 1.3,
        "inflation": 2.4,
        "unemployment": 5.3,
        "balance": -3.3,
        "psnfl": 84.4,
    },
    2028: {
        "growth": 1.7,
        "inflation": 2.0,
        "unemployment": 4.8,
        "balance": -2.8,
        "psnfl": 84.7,
    },
}


IMF_SOURCE = (
    "IMF United Kingdom 2026 Article IV Consultation "
    "(July 16, 2026)"
)


def get_imf_projection(year):
    """Return the IMF projection for a calendar year."""
    return IMF_OUTLOOK.get(year)


def get_current_imf_projection():
    """Return the IMF projection for the current simulator year."""
    return IMF_OUTLOOK.get(int(s.year) + 2025)


def imf_outlook_screen():
    """
    Render the three-year IMF economic outlook and compare it
    with the player's simulated economy.
    """

    st.subheader("🌐 IMF Three-Year Economic Outlook")

    st.caption(
        "Baseline projections from the IMF's July 2026 UK Article IV. "
        "Your policy choices can move the simulated economy above or below "
        "this baseline."
    )

    # --------------------------------------------------------
    # OUTLOOK TABLE
    # --------------------------------------------------------

    outlook_rows = []

    for year, data in IMF_OUTLOOK.items():
        outlook_rows.append(
            {
                "Year": year,
                "Real GDP growth": f"{data['growth']:.1f}%",
                "CPI inflation": f"{data['inflation']:.1f}%",
                "Unemployment": f"{data['unemployment']:.1f}%",
                "Public balance": f"{data['balance']:.1f}% GDP",
                "PSNFL": f"{data['psnfl']:.1f}% GDP",
            }
        )

    outlook_df = pd.DataFrame(outlook_rows)

    st.dataframe(
        outlook_df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # CURRENT YEAR COMPARISON
    # --------------------------------------------------------

    current_year = int(s.year) + 2025
    imf = get_imf_projection(current_year)

    if imf is not None:

        st.markdown(f"### 📍 Your Economy vs IMF — {current_year}")

        # The simulator's unemployment figure lives in country state.
        try:
            current_unemployment = float(
                s.country["unemployment"]
            )
        except Exception:
            try:
                current_unemployment = float(
                    s.unemployment
                )
            except Exception:
                current_unemployment = None

        c1, c2, c3, c4 = st.columns(4)

        # GDP
        growth_gap = float(s.growth) - imf["growth"]

        c1.metric(
            "Real GDP growth",
            f"{float(s.growth):.1f}%",
            f"{growth_gap:+.1f}pp vs IMF",
            delta_color="normal",
        )

        # Inflation
        inflation_gap = float(s.inflation) - imf["inflation"]

        c2.metric(
            "Inflation",
            f"{float(s.inflation):.1f}%",
            f"{inflation_gap:+.1f}pp vs IMF",
            delta_color="inverse",
        )

        # Unemployment
        if current_unemployment is not None:

            unemployment_gap = (
                current_unemployment
                - imf["unemployment"]
            )

            c3.metric(
                "Unemployment",
                f"{current_unemployment:.1f}%",
                f"{unemployment_gap:+.1f}pp vs IMF",
                delta_color="inverse",
            )

        else:
            c3.metric(
                "Unemployment",
                "N/A",
            )

        # Public balance
        try:
            current_deficit = float(s.deficit)

            # The simulator's deficit is positive for a deficit.
            # IMF balance is negative for a deficit.
            game_balance = -current_deficit

            balance_gap = game_balance - imf["balance"]

            c4.metric(
                "Public balance",
                f"{game_balance:.1f}% GDP",
                f"{balance_gap:+.1f}pp vs IMF",
                delta_color="normal",
            )

        except Exception:
            c4.metric(
                "Public balance",
                "N/A",
            )

        # ----------------------------------------------------
        # GDP CHART
        # ----------------------------------------------------

        st.markdown("### 📈 Real GDP Growth")

        growth_chart = pd.DataFrame(
            {
                "IMF baseline": {
                    year: data["growth"]
                    for year, data in IMF_OUTLOOK.items()
                }
            }
        )

        try:
            current_growth = float(s.growth)

            # Add the current simulated value where it overlaps
            # with the IMF forecast.
            growth_chart.loc[current_year, "Your economy"] = (
                current_growth
            )

        except Exception:
            pass

        growth_chart = growth_chart.sort_index()

        st.line_chart(
            growth_chart,
            use_container_width=True,
        )

        # ----------------------------------------------------
        # INFLATION CHART
        # ----------------------------------------------------

        st.markdown("### 📉 Inflation")

        inflation_chart = pd.DataFrame(
            {
                "IMF baseline": {
                    year: data["inflation"]
                    for year, data in IMF_OUTLOOK.items()
                }
            }
        )

        try:
            current_inflation = float(s.inflation)

            inflation_chart.loc[
                current_year,
                "Your economy"
            ] = current_inflation

        except Exception:
            pass

        inflation_chart = inflation_chart.sort_index()

        st.line_chart(
            inflation_chart,
            use_container_width=True,
        )

        # ----------------------------------------------------
        # IMF COMMENTARY
        # ----------------------------------------------------

        st.markdown("### 🧾 What the IMF expects")

        st.info(
            f"""
**{current_year} IMF baseline**

- **GDP growth:** {imf['growth']:.1f}%
- **Average CPI inflation:** {imf['inflation']:.1f}%
- **Unemployment:** {imf['unemployment']:.1f}%
- **Public-sector balance:** {imf['balance']:.1f}% of GDP
- **PSNFL:** {imf['psnfl']:.1f}% of GDP

The IMF expects the UK economy to slow in 2026 before recovering as
the energy shock fades. Growth is projected to rise from **1.0% in
2026** to **1.3% in 2027** and **1.7% in 2028**.
"""
        )

        # ----------------------------------------------------
        # PERFORMANCE JUDGEMENT
        # ----------------------------------------------------

        if growth_gap >= 0.5:
            st.success(
                "🚀 Your economy is performing substantially better "
                "than the IMF growth baseline."
            )

        elif growth_gap >= 0:
            st.success(
                "📈 Your economy is growing at least as quickly "
                "as the IMF baseline."
            )

        elif growth_gap > -0.5:
            st.warning(
                "⚠️ Your economy is slightly weaker than the "
                "IMF baseline."
            )

        else:
            st.error(
                "📉 Your economy is substantially weaker than the "
                "IMF baseline."
            )

    else:
        # ----------------------------------------------------
        # AFTER THREE-YEAR FORECAST
        # ----------------------------------------------------

        st.warning(
            "The IMF's three-year baseline ends here. "
            "Your economic performance is now determined primarily "
            "by your policy choices and the simulator's internal model."
        )

    # --------------------------------------------------------
    # FORECAST SOURCE
    # --------------------------------------------------------

    st.divider()

    st.caption(
        f"Source: {IMF_SOURCE}. "
        "IMF projections are a reference scenario rather than a "
        "guarantee of future economic outcomes."
    )

    st.caption(
        "Note: PSNFL (Public Sector Net Financial Liabilities) is "
        "the IMF's selected fiscal-liabilities measure and should "
        "not be directly compared with the simulator's debt percentage."
    )


# ============================================================
# RESTART
# ============================================================

def restart():
    s.clear()
    st.rerun()


# ============================================================
# SIDEBAR: SAVE / NEW GAME
# ============================================================

with st.sidebar:

    st.markdown("### 💾 Game")

    if s.step == "game":

        st.download_button(
            "Download save file",
            state.export_save(),
            file_name=(
                f"chancellor_{s.party.replace(' ', '')}"
                f"_T{s.term}Y{s.year}.json"
            ),
            mime="application/json",
            help=(
                "Save your progress and load it again "
                "from the start screen."
            ),
        )

        st.caption(
            f"{s.party} · {s.difficulty} · seed {s.seed}"
        )

        if st.button("Abandon run & start over"):
            restart()

    else:
        st.caption("Start a game to enable saving.")


# ============================================================
# SETUP SCREEN
# ============================================================

def setup_screen():

    st.title(
        "🏛️ The UK Chancellor Simulator "
        "(Hardcore Mode)"
    )

    st.markdown(
        "### Step 1: Choose Your Government"
    )

    party = st.selectbox(
        "Select Governing Party:",
        state.PARTIES,
    )

    c1, c2 = st.columns([2, 1])

    with c1:

        difficulty = st.radio(
            "Difficulty",
            list(state.DIFFICULTY),
            index=2,
            horizontal=True,
            captions=[
                d["blurb"]
                for d in state.DIFFICULTY.values()
            ],
        )

    with c2:

        seed = st.number_input(
            "Seed (same seed, same crises)",
            min_value=1,
            max_value=999999,
            value=int(s.seed),
            step=1,
        )

    tags = st.checkbox(
        "Show ideology tags on policy options",
        value=(difficulty == "Easy"),
        key=f"tags_{difficulty}",
        help=(
            "Off by default: read the policy, not the label. "
            "Your MPs still know what is and is not in "
            "your party's tradition."
        ),
    )

    if st.button(
        "Enter Number 11",
        type="primary",
    ):

        state.new_game(
            party,
            difficulty,
            seed,
            tags,
        )

        st.rerun()

    with st.expander("Load a saved game"):

        up = st.file_uploader(
            "Save file (.json)",
            type="json",
        )

        if up is not None and st.button("Load game"):

            err = state.import_save(
                up.getvalue().decode(
                    "utf-8",
                    errors="replace",
                )
            )

            if err:
                st.error(err)
            else:
                st.rerun()


if s.step == "setup":

    setup_screen()
    st.stop()


# ============================================================
# MAIN HEADER & DASHBOARD
# ============================================================

header(
    s.party,
    s.term,
    s.year,
    s.block,
)

render_cards(CARDS_TOP)

st.markdown("#### 🏛️ Political Capital")

render_cards(CARDS_POLITICAL)

st.divider()


# ============================================================
# SCORECARD
# ============================================================

def scorecard_block(show_share=True):

    data = engine.scorecard()

    render_scorecard(data)

    if show_share:

        st.caption("Share your result:")

        st.code(
            data["share"],
            language=None,
        )


# ============================================================
# GAME OVER
# ============================================================

if s.get("game_over"):

    over = s.game_over

    if over["kind"] == "sacked":

        humphrey_message(
            "I am so sorry, Chancellor. The Prime Minister "
            "feels that your continued presence at the Treasury "
            "is... politically sub-optimal. The removal van is "
            "waiting at the back door of Number 11."
        )

        st.error(
            s.get("sacked_reason")
            or "You have been sacked."
        )

    elif over["kind"] == "lost":

        humphrey_message(
            "The electorate has spoken, Chancellor. Or rather, "
            "they have shouted. We have been thoroughly evicted. "
            "I shall miss our little chats."
        )

    scorecard_block()

    if st.button(
        "Start a New Career",
        type="primary",
    ):
        restart()

    st.stop()


# ============================================================
# ELECTION NIGHT
# ============================================================

if s.year > 5:

    r = engine.compute_election()

    if s.get("game_over"):
        st.rerun()

    st.subheader(
        "🗳️ GENERAL ELECTION NIGHT: RESULTS"
    )

    box = (
        "#2b5440"
        if r["win"]
        else "#111111"
    )

    st.markdown(
        f"""
        <div style='
            background-color: {box};
            padding: 20px;
            border-radius: 10px;
            color: white;
            text-align: center;
            border: 2px solid #c9a45c;
        '>
            <h2>{r['title']}</h2>
            <h4 style='color: #c9a45c;'>
                {r['gov_type']}
            </h4>
            <p style='font-size: 18px;'>
                Your Seats: <b>{r['player_seats']}</b>
                |
                Target for UK Majority:
                {engine.WIN_MAJORITY}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 🏛️ The New Parliament"
    )

    labels = {
        "Labour": "LAB",
        "Conservative": "CON",
        "Liberal Democrats": "LDEM",
        "Reform UK": "REF",
        "Green Party": "GRN",
        "SNP": "SNP",
        "Plaid Cymru": "PC",
    }

    for col, party in zip(
        st.columns(7),
        state.PARTIES,
    ):

        col.metric(
            labels[party],
            r["seats"][party],
        )

    st.divider()

    extra = (
        "Managing a coalition partner will be tedious"
        if r["coalition"]
        else
        "A minority government will be a legislative nightmare"
        if r["kind"] == "minority"
        else
        "The numbers are in your favour"
    )

    humphrey_message(
        "Congratulations, Chancellor. We have survived "
        "the electorate. "
        f"{extra}, but you remain at the Treasury."
    )

    boost = round(
        min(
            15.0,
            max(
                5.0,
                r["margin"] / 10.0,
            ),
        ),
        1,
    )

    st.success(
        f"""
**YOU SURVIVED!** You retained power.

🎉 **HONEYMOON PERIOD:** +**{boost}%**
to Public Approval and all Political Capital if you continue.
"""
    )

    scorecard_block()

    if st.button(
        "Continue as Chancellor",
        type="primary",
    ):

        engine.continue_term()
        st.rerun()

    st.stop()


# ============================================================
# BUDGET
# ============================================================

def budget_screen():

    if s.get("budget_passed"):

        st.subheader(
            "🏛️ Parliamentary Vote Results"
        )

        bb = s.backbench_opinion

        base_ayes = (
            326
            if s.party not in state.REGIONAL
            else 300
        )

        ayes = min(
            650,
            max(
                0,
                int(
                    base_ayes
                    + (bb / 1.5)
                    - 20
                    + (s.year * 2)
                ),
            ),
        )

        noes = 650 - ayes

        txt = (
            f"**Ayes:** {ayes} | "
            f"**Noes:** {noes}"
        )

        if bb > 70:

            st.success(
                "**House of Commons:** The Budget passed "
                "the Commons with a thumping majority! "
                "Your backbenchers cheered you to the rafters.\n\n"
                + txt
            )

        elif bb > 40:

            st.info(
                "**House of Commons:** The Budget passed "
                "the Commons. There was some grumbling "
                "from the backbenches, but the whips kept "
                "them in line.\n\n"
                + txt
            )

        else:

            st.warning(
                "**House of Commons:** The Budget barely "
                "scraped through the Commons! A massive "
                "backbench rebellion nearly brought the "
                "government down.\n\n"
                + txt
            )

        lords_ayes = min(
            750,
            max(
                0,
                int(
                    200
                    + s.approval * 2.5
                ),
            ),
        )

        lords_noes = 750 - lords_ayes

        if s.approval < 40:

            humphrey_message(
                f"As for the House of Lords, Chancellor, "
                f"they actually voted against us "
                f"(**{lords_noes} Not-Contents** to "
                f"{lords_ayes} Contents). I reminded them "
                "of the Parliament Act of 1911. They cannot "
                "reject a Money Bill. However, seeing your "
                "dismal poll numbers, they decided to delay "
                "it for a month just to be difficult. The "
                "markets were briefly irritated."
            )

        else:

            humphrey_message(
                f"As for the House of Lords, Chancellor, "
                f"they supported the bill "
                f"(**{lords_ayes} Contents** to "
                f"{lords_noes} Not-Contents). Though even "
                "if they hadn't, the Parliament Act of 1911 "
                "means they cannot vote down a Money Bill. "
                "The constitution is a wonderful thing."
            )

        for ev in s.event_cards:

            event_card(
                ev["title"],
                ev["text"],
                ev["summary"],
            )

        if s.get("headlines"):

            render_newspapers(
                *s.headlines
            )

        st.divider()

        if st.button(
            "Proceed to Spring",
            type="primary",
        ):

            engine.proceed_to_spring()
            st.rerun()

    else:

        st.subheader(
            f"Year {s.year} - "
            "Block 3: The Chancellor's Budget"
        )

        humphrey_message(
            "A budget, Chancellor, is merely a collection "
            "of numbers we present to the House to obscure "
            "our true intentions. Shall we proceed to the "
            "dispatch box?"
        )

        budget.render()

        st.divider()

        st.caption(
            "Any slider changes you have not applied "
            "are applied automatically when you submit."
        )

        if st.button(
            "Submit Budget to the Commons & Lords",
            type="primary",
        ):

            engine.submit_budget()
            st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

def dashboard():

    tab_econ, tab_imf, tab_nation, tab_hist = st.tabs(
        [
            "📊 Economy & Polls",
            "🌐 IMF Outlook",
            "🇬🇧 State of the Nation",
            "📜 History",
        ]
    )

    # --------------------------------------------------------
    # ECONOMY
    # --------------------------------------------------------

    with tab_econ:

        render_cards(
            CARDS_ECON,
            per_row=2,
        )

        st.markdown(
            "### 📈 Voting Intention"
        )

        df = pd.DataFrame(
            s.poll_history
        ).set_index("Period")

        render_polls(df)

    # --------------------------------------------------------
    # IMF
    # --------------------------------------------------------

    with tab_imf:

        imf_outlook_screen()

    # --------------------------------------------------------
    # STATE OF THE NATION
    # --------------------------------------------------------

    with tab_nation:

        country.render()

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    with tab_hist:

        pending = sorted(
            s.pending,
            key=lambda p: p["due"],
        )

        render_timeline(
            s.history,
            pending,
        )

        if st.button(
            "Resign & Start New Career"
        ):

            engine.resign()
            st.rerun()


# ============================================================
# DECISIONS & CRISES
# ============================================================

def crisis_screen():

    crisis = scen.get(
        s.active_crisis
    )

    if crisis is None:

        s.active_crisis = None
        st.rerun()

    crisis_card(
        crisis["title"]
    )

    humphrey_message(
        crisis["humphrey"]
    )

    if s.get("crisis_reason"):

        st.caption(
            s.crisis_reason
        )

    labels = scen.option_labels(
        crisis
    )

    choice = st.radio(
        "Choose emergency response:",
        labels,
        index=None,
        key=f"crisis_{s.steps}",
    )

    if st.button(
        "Resolve Crisis",
        type="primary",
        disabled=choice is None,
    ):

        engine.resolve_crisis(
            labels.index(choice)
        )

        st.rerun()


def decision_screen():

    decision = engine.current_decision()

    if not decision:

        st.write(
            "No decision data found for this block."
        )

        return

    options = engine.current_options()

    st.subheader(
        f"Block {s.block}: "
        f"{decision['title']}"
    )

    st.write(
        decision["text"]
    )

    humphrey_message(
        decision["humphrey"]
    )

    labels = [
        o["label"]
        for o in options
    ]

    choice = st.radio(
        "Select strategy:",
        labels,
        index=None,
        key=(
            f"dec_{s.term}_"
            f"{s.year}_{s.block}"
        ),
    )

    if st.button(
        "Execute Policy",
        type="primary",
        disabled=choice is None,
    ):

        engine.execute_decision(
            options[
                labels.index(choice)
            ]
        )

        st.rerun()


# ============================================================
# MAIN GAME LOOP
# ============================================================

if (
    s.block == 3
    and s.active_crisis is None
):

    budget_screen()

else:

    col_game, col_dash = st.columns(
        2,
        gap="large",
    )

    with col_dash:

        dashboard()

    with col_game:

        for ev in s.event_cards:

            event_card(
                ev["title"],
                ev["text"],
                ev["summary"],
            )

        if s.get("message"):

            news_box(
                s.message
            )

        if s.get("humphrey_note"):

            humphrey_message(
                s.humphrey_note,
                title=(
                    "Sir Humphrey on your "
                    "last decision"
                ),
            )

        if s.get("headlines"):

            render_newspapers(
                *s.headlines
            )

        if s.active_crisis is not None:

            crisis_screen()

        else:

            decision_screen()
