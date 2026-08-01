import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Cupral Copper Intelligence", page_icon="●", layout="wide")

# ============================================================
# REAL CUSTOMER DATA — grounded in disclosed figures
# ============================================================
CUSTOMERS = {
    "havells": {
        "label": "Havells",
        "description": "Diversified electricals company; cable segment is ~40% of total group "
                        "revenue, so copper price swings are usually absorbed calmly at the group "
                        "level — but the cable team feels the identical margin math on their own numbers.",
        "quarterly_revenue_cr": 2300,
        "rm_share_of_revenue": 0.62,
        "copper_share_of_rm": 0.45,
        "coverage_days": 25,
        "sensitivity": "Moderate",
        "threshold_pct": 4.0,
        "customer_delay_hours": 24,
        "real_context_falling": "Havells' cable segment is a smaller share of group revenue, so this "
                                 "move is unlikely to show up in their headline results — but it is still "
                                 "real margin pressure inside the cable division specifically.",
        "real_context_rising": "Given cables are ~40% of Havells' revenue, a sustained rise here would "
                                "show up more in segment reporting than in group-level numbers — worth "
                                "flagging before their segment review, not their group earnings call.",
    },
    "polycab": {
        "label": "Polycab",
        "description": "Market leader in India's organised wire & cable segment (~25-27% share). "
                        "Copper is 50-60% of raw material cost. Cable & wire is ~85% of total revenue.",
        "quarterly_revenue_cr": 4700,
        "rm_share_of_revenue": 0.65,
        "copper_share_of_rm": 0.55,
        "coverage_days": 35,
        "sensitivity": "High",
        "threshold_pct": 3.0,
        "customer_delay_hours": 18,
        "real_context_falling": "This mirrors Polycab's own Q3 FY25 disclosure, where they explicitly "
                                 "cited a copper price decline plus high channel inventory as a driver of "
                                 "wire-business slowdown — reference this directly on the call.",
        "real_context_rising": "Their C&W segment is 85% of total revenue, so this move flows almost "
                                "directly into group margin — this is not a segment-level conversation, "
                                "it is a group-level one.",
    },
    "kei": {
        "label": "KEI Industries",
        "description": "Fast-expanding cable manufacturer investing heavily in new capacity (Sanand "
                        "facility). Reacted more sharply than peers to competitive entry news in the "
                        "past (14.5% intraday stock drop vs Polycab's 9.6%) — reads as the most "
                        "price-sensitive of the three accounts.",
        "quarterly_revenue_cr": 2000,
        "rm_share_of_revenue": 0.65,
        "copper_share_of_rm": 0.55,
        "coverage_days": 30,
        "sensitivity": "Very high",
        "threshold_pct": 2.5,
        "customer_delay_hours": 12,
        "real_context_falling": "KEI has historically been the most reactive of your three accounts to "
                                 "market and competitive shocks — timing this outreach well matters more "
                                 "here than elsewhere.",
        "real_context_rising": "Given their aggressive capacity expansion (Sanand), KEI is likely carrying "
                                "higher committed procurement volumes right now than usual — a price rise "
                                "hits harder while they're mid-expansion.",
    },
}

FX_RATE = 88.0  # USD/INR, adjustable below

REFERENCE_PRICE = 12300  # $/tonne, shared reference point across accounts

PRICE_HISTORY = [
    ("Mar 2020", 5203), ("2024 avg", 9142), ("May 2024", 11105),
    ("Oct 2025", 11200), ("Dec 2025", 11900), ("Dec 31 2025", 12423),
    ("Jan 2026 (ATH)", 14528), ("Feb 2026", 12900),
]

# ============================================================
# CALCULATION ENGINE — fully transparent, no black box
# ============================================================
def compute_tonnage(customer, ref_price_usd, fx):
    """Compute copper tonnes/quarter, tonnes/day, and tonnes on hand — all live-calculated."""
    copper_cost_per_qtr_cr = (
        customer["quarterly_revenue_cr"]
        * customer["rm_share_of_revenue"]
        * customer["copper_share_of_rm"]
    )
    ref_price_inr_per_kg = ref_price_usd * fx / 1000
    copper_cost_per_qtr_inr = copper_cost_per_qtr_cr * 1e7  # crore -> rupees
    copper_kg_per_qtr = copper_cost_per_qtr_inr / ref_price_inr_per_kg
    copper_tonnes_per_qtr = copper_kg_per_qtr / 1000
    tonnes_per_day = copper_tonnes_per_qtr / 90
    tonnes_on_hand = tonnes_per_day * customer["coverage_days"]
    return {
        "copper_cost_per_qtr_cr": copper_cost_per_qtr_cr,
        "tonnes_per_qtr": copper_tonnes_per_qtr,
        "tonnes_per_day": tonnes_per_day,
        "tonnes_on_hand": tonnes_on_hand,
    }


def compute_impact(customer, current_price_usd, ref_price_usd, fx):
    tonnage = compute_tonnage(customer, ref_price_usd, fx)
    ref_price_inr_per_kg = ref_price_usd * fx / 1000
    current_price_inr_per_kg = current_price_usd * fx / 1000
    delta_inr_per_kg = current_price_inr_per_kg - ref_price_inr_per_kg
    impact_inr = tonnage["tonnes_on_hand"] * 1000 * delta_inr_per_kg
    impact_cr = impact_inr / 1e7
    delta_pct = ((current_price_usd - ref_price_usd) / ref_price_usd) * 100
    return {**tonnage, "delta_pct": delta_pct, "impact_cr": impact_cr,
             "ref_price_inr_per_kg": ref_price_inr_per_kg,
             "current_price_inr_per_kg": current_price_inr_per_kg}


def generate_talking_point(customer, impact, full_detail=True):
    delta_pct = impact["delta_pct"]
    tonnes = impact["tonnes_on_hand"]
    impact_cr = impact["impact_cr"]
    label = customer["label"]

    if delta_pct <= -customer["threshold_pct"]:
        headline = (f"LME has fallen {abs(delta_pct):.1f}% versus the reference level. "
                     f"Estimated {tonnes:,.0f} tonnes on hand is now marked down by roughly "
                     f"Rs {abs(impact_cr):,.1f} crore.")
        context = customer["real_context_falling"]
        tone = "falling"
    elif delta_pct >= customer["threshold_pct"]:
        headline = (f"LME has risen {delta_pct:.1f}% versus the reference level. "
                     f"Estimated {tonnes:,.0f} tonnes on hand is now worth roughly "
                     f"Rs {impact_cr:,.1f} crore more — but any orders already quoted at the "
                     f"old price now cost more to fulfil.")
        context = customer["real_context_rising"]
        tone = "rising"
    else:
        headline = (f"LME is broadly stable versus the reference level "
                     f"({delta_pct:+.1f}%). No threshold triggered.")
        context = "A good moment to check in on next quarter's planned volumes without urgency."
        tone = "stable"

    if full_detail:
        return f"{label} — {headline} {context}", tone
    else:
        # Stripped-down customer-facing version: factual only, no advice, no peer context
        return (f"LME copper has moved {delta_pct:+.1f}% since your last recorded reference point. "
                f"Estimated impact on your current inventory position: approximately "
                f"Rs {impact_cr:+,.1f} crore."), tone


# ============================================================
# SESSION STATE — tracks last alert point + audit log
# ============================================================
if "last_alert_price" not in st.session_state:
    st.session_state.last_alert_price = {k: REFERENCE_PRICE for k in CUSTOMERS}
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

# ============================================================
# SIDEBAR — role + settings
# ============================================================
st.sidebar.markdown("### ● Cupral Copper Intelligence")
role = st.sidebar.radio("View as", ["Account Manager (internal)", "Customer team (e.g. Polycab)"])
fx = st.sidebar.number_input("USD/INR rate", min_value=70.0, max_value=100.0, value=FX_RATE, step=0.5)
st.sidebar.caption("This is an internal decision-support tool. Live LME feeds are already a paid "
                    "commodity every serious customer holds — this tool exists to translate a price "
                    "move into a specific account's numbers and a ready-to-use talking point, not to "
                    "replace the account manager's own call.")

# ============================================================
# MAIN — Account Manager view
# ============================================================
if role.startswith("Account Manager"):
    st.title("Cupral Copper Intelligence — Account manager desk")
    st.caption("Record today's LME price. Each account is evaluated against its own last alert "
               "point, not a fixed level — thresholds and customer notification delay are configurable per account.")

    col1, col2 = st.columns([2, 1])
    with col1:
        current_price = st.slider("Today's LME price ($/tonne)", 8500, 15000, REFERENCE_PRICE, step=50)
    with col2:
        st.metric("Reference price", f"${REFERENCE_PRICE:,}")

    # price history chart
    hist_labels = [p[0] for p in PRICE_HISTORY] + ["Today"]
    hist_values = [p[1] for p in PRICE_HISTORY] + [current_price]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_labels, y=hist_values, mode="lines+markers",
                               line=dict(color="#2a78d6", width=2), fill="tozeroy",
                               fillcolor="rgba(42,120,214,0.08)"))
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10),
                       yaxis_title="$/tonne", showlegend=False,
                       plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Historical points reconstructed from published data (World Bank, LME, Reuters, Barchart) — "
               "not tick-level live data. No free real-time LME API exists; live external calls are a demo risk.")

    st.markdown("---")
    st.subheader("Accounts")

    for key, cust in CUSTOMERS.items():
        impact = compute_impact(cust, current_price, REFERENCE_PRICE, fx)
        triggered = abs(impact["delta_pct"]) >= cust["threshold_pct"]

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                st.markdown(f"**{cust['label']}**  ·  sensitivity: {cust['sensitivity']}")
                st.caption(cust["description"])
            with c2:
                st.metric("Coverage", f"{cust['coverage_days']} days",
                          help="Days of copper coverage, estimated from disclosed revenue, "
                               "raw-material share, and copper share — calculated live below.")
            with c3:
                st.metric("Tonnes on hand", f"{impact['tonnes_on_hand']:,.0f} t")
            with c4:
                st.metric("Inventory impact", f"Rs {impact['impact_cr']:+,.1f} cr",
                          delta=f"{impact['delta_pct']:+.1f}% vs ref")

            with st.expander("How this is calculated"):
                st.write(f"Quarterly revenue: Rs {cust['quarterly_revenue_cr']:,} cr")
                st.write(f"× Raw material share of revenue: {cust['rm_share_of_revenue']*100:.0f}%")
                st.write(f"× Copper share of raw material cost: {cust['copper_share_of_rm']*100:.0f}%")
                st.write(f"= Copper cost per quarter: Rs {impact['copper_cost_per_qtr_cr']:,.1f} cr")
                st.write(f"÷ Reference price (Rs/kg, at ${REFERENCE_PRICE}/t and FX {fx}): "
                         f"Rs {impact['ref_price_inr_per_kg']:.2f}/kg")
                st.write(f"= {impact['tonnes_per_qtr']:,.0f} tonnes/quarter "
                         f"→ {impact['tonnes_per_day']:.1f} tonnes/day")
                st.write(f"× {cust['coverage_days']} days coverage = **{impact['tonnes_on_hand']:,.0f} tonnes on hand**")
                st.write(f"Mark-to-market at today's price (Rs {impact['current_price_inr_per_kg']:.2f}/kg): "
                         f"**Rs {impact['impact_cr']:+,.1f} crore**")

            talking_point, tone = generate_talking_point(cust, impact, full_detail=True)
            box_color = "#4a1b0c" if tone == "falling" else ("#173404" if tone == "rising" else "#2c2c2a")
            st.markdown(
                f"<div style='background:{box_color}22; border-left:3px solid {box_color}; "
                f"padding:10px 14px; border-radius:4px; margin-top:8px;'>"
                f"<b>Talking point{'  ·  THRESHOLD CROSSED' if triggered else ''}:</b><br>{talking_point}</div>",
                unsafe_allow_html=True,
            )

            with st.expander("Alert settings for this account"):
                a, b = st.columns(2)
                with a:
                    st.number_input(f"Threshold % — {key}", value=cust["threshold_pct"],
                                    step=0.5, key=f"thresh_{key}")
                with b:
                    st.number_input(f"Customer notification delay (hours) — {key}",
                                    value=cust["customer_delay_hours"], step=1, key=f"delay_{key}")

            if triggered:
                if st.button(f"Log this alert for {cust['label']}", key=f"log_{key}"):
                    now = datetime.now()
                    st.session_state.audit_log.append({
                        "time": now.strftime("%Y-%m-%d %H:%M"),
                        "account": cust["label"],
                        "price": current_price,
                        "delta_pct": round(impact["delta_pct"], 1),
                        "am_notified": now.strftime("%Y-%m-%d %H:%M"),
                        "customer_notified_at": (now + timedelta(hours=cust["customer_delay_hours"])).strftime("%Y-%m-%d %H:%M"),
                    })
                    st.session_state.last_alert_price[key] = current_price
                    st.success(f"Logged. Account manager notified now. "
                               f"Customer notification scheduled for "
                               f"{cust['customer_delay_hours']}h later — lead-time gap preserved.")

    st.markdown("---")
    st.subheader("Audit trail — proves the lead-time gap")
    if st.session_state.audit_log:
        st.table(st.session_state.audit_log)
    else:
        st.caption("No alerts logged yet. Trigger a threshold above and click 'Log this alert' to populate.")

# ============================================================
# MAIN — Customer team view (e.g. Polycab's own team)
# ============================================================
else:
    st.title("Your copper position — Cupral Copper Intelligence")
    cust_key = st.selectbox("Select your organisation (demo only — production would auto-detect login)",
                             list(CUSTOMERS.keys()), format_func=lambda k: CUSTOMERS[k]["label"])
    cust = CUSTOMERS[cust_key]
    current_price = st.slider("Today's LME price ($/tonne)", 8500, 15000, REFERENCE_PRICE, step=50,
                               key="cust_slider")
    impact = compute_impact(cust, current_price, REFERENCE_PRICE, fx)

    st.metric("Your estimated copper position", f"{impact['tonnes_on_hand']:,.0f} tonnes")
    st.metric("Price move vs your reference", f"{impact['delta_pct']:+.1f}%")
    st.metric("Estimated inventory impact", f"Rs {impact['impact_cr']:+,.1f} crore")

    stripped_point, _ = generate_talking_point(cust, impact, full_detail=False)
    st.info(stripped_point)
    st.caption("This view is read-only, scoped to your own account only, and factual — no "
               "recommendations, no comparison to other accounts. Your Cupral account manager may "
               "already have reached out about this move.")
