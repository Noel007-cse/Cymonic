import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Real Estate Lead Qualifier",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

from agent.groq_agent import chat_with_agent, check_missing_fields, get_initial_greeting, compute_pydynite_score
from matching.matcher import match_properties
from qualification.qualifier import qualify_buyer
from database.data_manager import load_properties, load_buyers, save_buyer, get_dashboard_stats
from utils.helpers import format_inr, format_inr_full, get_status_emoji, get_priority_badge, timeline_days_to_text

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #1a1a2e; }
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
.profile-box { background:#f0f7ff; border-radius:10px; padding:14px; border:1px solid #cce0ff; }
.result-box  { background:#f0fff4; border-radius:10px; padding:14px; border:1px solid #b2dfdb; }
.broker-box  { background:#fff8e1; border-radius:10px; padding:14px; border:1px solid #ffe082; }
.prop-card   { background:#fff; border-radius:8px; padding:12px; margin:6px 0; border:1px solid #e0e0e0; }
.score-bar   { height:8px; border-radius:4px; background:#e0e0e0; margin:4px 0; }
.score-fill  { height:8px; border-radius:4px; }
.pydynite-badge {
    display:inline-block; padding:4px 10px; border-radius:20px;
    font-weight:bold; font-size:13px; margin:2px;
}
.q-complete  { background:#e8f5e9; color:#2e7d32; }
.q-pending   { background:#fff3e0; color:#e65100; }
.broker-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius:12px; padding:16px; color:white; margin:6px 0;
}
.no-result-box {
    background:#fff3f3; border:2px dashed #ff6b6b;
    border-radius:12px; padding:20px; text-align:center;
}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar Navigation ───────────────────────────────────────────────────────
st.sidebar.title("🏠 Real Estate\nLead Qualifier")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Buyer Chat", "📊 Broker Dashboard", "🏘️ Properties", "👥 Leads"],
    label_visibility="collapsed"
)
st.sidebar.markdown("---")
st.sidebar.caption("Powered by **Groq AI** • llama-3.3-70b")

# ─── Session State ────────────────────────────────────────────────────────────
for key, default in [
    ("messages", []),
    ("buyer_state", {}),
    ("qualified", False),
    ("qualification_result", None),
    ("matched_properties", []),
    ("conversation_complete", False),
    ("greeted", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helper: PyDynite live score widget ───────────────────────────────────────
def render_pydynite_widget(buyer_state: dict):
    pds = compute_pydynite_score(buyer_state)
    answered = pds["answered"]
    total_q = pds["total_questions"]
    score = pds["total"]
    pct = score  # Already out of 100

    # Color based on score
    if pct >= 70:
        color = "#00c853"
    elif pct >= 40:
        color = "#ff9800"
    else:
        color = "#f44336"

    st.markdown(f"#### 📊 PyDynite Score")
    st.markdown(
        f"<div style='font-size:28px;font-weight:bold;color:{color}'>{score}/100</div>"
        f"<div style='font-size:12px;color:#888'>{answered}/{total_q} questions answered</div>",
        unsafe_allow_html=True,
    )
    st.progress(min(pct / 100, 1.0))

    # Per-dimension breakdown (compact)
    dim_labels = {
        "name": "👤 Name",
        "phone": "📞 Phone",
        "budget": "💰 Budget",
        "location": "📍 Location",
        "property_type": "🏗️ Type",
        "bedrooms": "🛏️ Bedrooms",
        "timeline": "⏰ Timeline",
        "purpose": "🎯 Purpose",
        "parking": "🚗 Parking",
        "size_sqft": "📐 Size",
        "financing": "🏦 Financing",
        "amenities": "✨ Amenities",
    }
    for key, label in dim_labels.items():
        pts = pds["scores"].get(key, 0)
        is_done = pts > 0
        badge_cls = "q-complete" if is_done else "q-pending"
        badge_text = f"✓ {pts}pts" if is_done else "○ pending"
        st.markdown(
            f"<span class='pydynite-badge {badge_cls}'>{label} {badge_text}</span>",
            unsafe_allow_html=True,
        )


# ── Helper: Broker card ───────────────────────────────────────────────────────
def render_broker_cards(matched_properties: list):
    """Show broker contact numbers for matched properties."""
    shown = set()
    broker_count = 0
    for prop in matched_properties:
        broker_phone = prop.get("broker_phone", "").strip()
        broker_name = prop.get("broker_name", "").strip()
        if not broker_phone:
            continue
        key = broker_phone
        if key in shown:
            continue
        shown.add(key)
        broker_count += 1
        st.markdown(
            f"""<div class='broker-card'>
            <b>🏢 {prop['property_name']}</b><br>
            <span style='font-size:12px;opacity:0.85'>📍 {prop['location']} | 🎯 {prop['match_score']:.0f}% match</span><br>
            <span style='font-size:20px'>📞 <b>{broker_phone}</b></span>
            {'<br><span style="font-size:12px;opacity:0.8">Broker: ' + broker_name + '</span>' if broker_name else ''}
            </div>""",
            unsafe_allow_html=True,
        )
    return broker_count


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: BUYER CHAT
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Buyer Chat":
    st.title("🏠 Real Estate Assistant")
    st.caption("Answer 12 quick questions and we'll match your perfect property — instantly.")

    # Initial greeting
    if not st.session_state.greeted:
        st.session_state.messages.append({"role": "assistant", "content": get_initial_greeting()})
        st.session_state.greeted = True

    col_chat, col_profile = st.columns([3, 1])

    with col_chat:
        # Render chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if not st.session_state.conversation_complete:
            user_input = st.chat_input("Type your message here…")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                groq_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

                with st.spinner("Processing…"):
                    ai_response, updated_state, is_complete = chat_with_agent(
                        groq_messages, st.session_state.buyer_state
                    )

                st.session_state.buyer_state = updated_state

                if is_complete:
                    # Run matching pipeline
                    properties_df = load_properties()
                    matched = match_properties(st.session_state.buyer_state, properties_df)
                    st.session_state.matched_properties = matched

                    qual_result = qualify_buyer(
                        st.session_state.buyer_state, matched,
                        message_count=len(st.session_state.messages)
                    )
                    st.session_state.qualification_result = qual_result
                    st.session_state.qualified = True
                    st.session_state.conversation_complete = True

                    save_buyer(st.session_state.buyer_state, qual_result)

                    status = qual_result["status"]
                    name = st.session_state.buyer_state.get("name", "")
                    if status == "HIGHLY_QUALIFIED":
                        done_msg = (f"🎉 Great news, **{name}**! We found excellent property matches for you. "
                                    "Your profile has been created and a broker will contact you shortly!")
                    elif status == "QUALIFIED":
                        done_msg = (f"✅ Thank you, **{name}**! We found some good matches. "
                                    "Our team will arrange site visits for you.")
                    elif status == "NO_MATCH":
                        done_msg = (f"Thank you, **{name}**. Unfortunately no exact matches right now. "
                                    "You can push/relax any of your requirements below to find more options!")
                    else:
                        done_msg = f"Thank you, **{name}**! We've processed your requirements and will be in touch soon."

                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    st.session_state.messages.append({"role": "assistant", "content": done_msg})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

                st.rerun()
        else:
            st.success("✅ Profile collected successfully. View your results below.")
            if st.button("🔄 Start New Conversation"):
                for key in ["messages", "buyer_state", "qualified", "qualification_result",
                            "matched_properties", "conversation_complete", "greeted"]:
                    st.session_state.pop(key, None)
                st.rerun()

    with col_profile:
        st.markdown("#### 📋 Your Profile")
        state = st.session_state.buyer_state
        fields = [
            ("Name", state.get("name")),
            ("Phone", state.get("phone")),
            ("Budget", format_inr(state.get("budget_max", 0)) if state.get("budget_max") else None),
            ("Location", state.get("location")),
            ("Type", state.get("property_type")),
            ("Bedrooms", f"{state['bedrooms']} BHK" if state.get("bedrooms") else None),
            ("Timeline", timeline_days_to_text(state.get("timeline_days", 0)) if state.get("timeline_days") else None),
            ("Purpose", state.get("purpose")),
            ("Parking", state.get("parking")),
            ("Financing", state.get("financing")),
        ]
        for label, val in fields:
            if val:
                st.markdown(f"**{label}:** {val}")

        # Amenities
        amenities = state.get("amenities") or []
        if isinstance(amenities, list) and amenities:
            st.markdown(f"**Amenities:** {', '.join(amenities)}")
        elif isinstance(amenities, str) and amenities:
            st.markdown(f"**Amenities:** {amenities}")

        # Size
        smin = state.get("size_min_sqft")
        smax = state.get("size_max_sqft")
        if smin or smax:
            size_str = f"{smin or '?'}–{smax or '?'} sqft"
            st.markdown(f"**Size:** {size_str}")

        st.markdown("---")

        # Live PyDynite score widget
        if state:
            render_pydynite_widget(state)
        else:
            st.caption("Answer questions to see your score.")

        missing = check_missing_fields(state)
        if missing and state:
            st.caption(f"Still needed: `{'`, `'.join(missing)}`")
        elif not missing and state:
            st.success("✅ Profile complete!")

        # Quick result preview
        if st.session_state.qualified and st.session_state.qualification_result:
            st.markdown("---")
            qr = st.session_state.qualification_result
            emoji = get_status_emoji(qr["status"])
            st.markdown(f"**Result:** {emoji} {qr['status'].replace('_', ' ')}")
            st.metric("Score", f"{qr['qualification_score']}/100")
            if st.session_state.matched_properties:
                best = st.session_state.matched_properties[0]
                st.markdown(f"**Best Match:** {best['match_score']:.0f}%")
                st.caption(best["property_name"])
            st.caption("A broker will contact you for further assistance.")

    # ── Full results section ──────────────────────────────────────────────────
    if st.session_state.qualified and st.session_state.qualification_result:
        st.markdown("---")
        qr = st.session_state.qualification_result
        state = st.session_state.buyer_state
        status = qr["status"]
        emoji = get_status_emoji(status)
        name = state.get("name", "Buyer")

        if status in ("HIGHLY_QUALIFIED", "QUALIFIED"):
            st.success(f"🎉 Congratulations {name}! You're a **{status.replace('_', ' ').title()}**.\nWe found properties matching your requirements.")
        elif status == "NO_MATCH":
            st.warning("⚠️ NO SUITABLE MATCH FOUND")

        r1, r2, r3 = st.columns(3)

        with r1:
            st.markdown("#### 👤 Buyer Profile")
            amenities_val = state.get("amenities") or []
            if isinstance(amenities_val, list):
                amenities_display = ", ".join(amenities_val) if amenities_val else "N/A"
            else:
                amenities_display = str(amenities_val) or "N/A"
            st.markdown(f"""
| Field | Value |
|---|---|
| **Name** | {state.get('name', 'N/A')} |
| **Budget** | {format_inr(state.get('budget_max', 0))} |
| **Location** | {state.get('location', 'N/A')} |
| **Property** | {state.get('bedrooms', 'N/A')} BHK {state.get('property_type', '')} |
| **Timeline** | {timeline_days_to_text(state.get('timeline_days', 0))} |
| **Purpose** | {state.get('purpose', 'N/A')} |
| **Parking** | {state.get('parking', 'N/A')} |
| **Financing** | {state.get('financing', 'N/A')} |
| **Amenities** | {amenities_display} |
| **Status** | {emoji} {status.replace('_', ' ')} |
""")

        with r2:
            st.markdown("#### 📊 PyDynite Qualification")
            st.metric("Qualification Score", f"{qr['qualification_score']}/100")
            st.write(f"**Priority:** {get_priority_badge(qr['priority'])}")
            st.write(f"**Next Action:** {qr['next_action'].replace('_', ' ')}")
            st.markdown("**Score Breakdown:**")
            # Map dimension names to max values for progress
            dimension_max = {
                "Budget Clarity": 20,
                "Location Clarity": 10,
                "Property Requirement": 10,
                "Purchase Timeline": 15,
                "Property Match": 20,
                "Engagement": 10,
                "Purpose & Financing": 10,
                "Size & Amenities": 5,
            }
            for k, v in qr["score_breakdown"].items():
                max_v = dimension_max.get(k, 20)
                pct = int(v / max_v * 100) if max_v else 0
                st.progress(min(pct, 100) / 100, text=f"{k}: {v}/{max_v}")

        with r3:
            st.markdown("#### 💡 Why this decision?")
            for r in qr.get("reasoning", []):
                st.markdown(r)
            tags = qr.get("tags", [])
            if tags:
                st.markdown("**Tags:** " + " · ".join([f"`{t}`" for t in tags]))

        # ── Broker Contact Numbers ────────────────────────────────────────────
        if st.session_state.matched_properties:
            st.markdown("---")
            st.markdown("#### 📞 Broker Contact Numbers")
            broker_count = render_broker_cards(st.session_state.matched_properties)
            if broker_count == 0:
                st.info("🔔 Broker contact numbers are being assigned. Our team will reach out to you shortly.")

        # ── Best match ────────────────────────────────────────────────────────
        if st.session_state.matched_properties:
            st.markdown("---")
            st.markdown("#### 🏆 Best Match")
            best = st.session_state.matched_properties[0]
            bm1, bm2 = st.columns([1, 2])
            with bm1:
                st.markdown(f"**{best['property_id']}**")
                st.markdown(f"### {best['property_name']}")
                st.markdown(f"**{format_inr_full(best['price'])}**")
                score_pct = int(best['match_score'])
                color = "#00c853" if score_pct >= 80 else "#ff9800" if score_pct >= 60 else "#f44336"
                st.markdown(f"<h3 style='color:{color}'>{score_pct}% Match 🎯</h3>", unsafe_allow_html=True)
            with bm2:
                st.markdown(f"📍 {best['location']} | 🛏 {best['bedrooms']} BHK | 📐 {best['area_sqft']} sqft")
                st.markdown(f"🏗️ Possession: {best['possession']} | 🚗 Parking: {best['parking']}")
                st.markdown(f"✨ {best['amenities']}")
                if best.get("explanation"):
                    for p in best["explanation"].get("positives", []):
                        st.markdown(f"✓ {p}")
                    for n in best["explanation"].get("negatives", []):
                        st.markdown(f"✗ {n}")

        # ── Top 10 ────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🏘️ Top Matching Properties")
        if st.session_state.matched_properties:
            for i, prop in enumerate(st.session_state.matched_properties[:10]):
                score_pct = int(prop["match_score"])
                color = "🟢" if score_pct >= 80 else "🟡" if score_pct >= 60 else "🔴"
                with st.expander(f"{i+1}. {color} {prop['property_name']} — {score_pct}% | {format_inr(prop['price'])} | {prop['location']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**ID:** {prop['property_id']}")
                        st.write(f"**Type:** {prop['property_type']}")
                        st.write(f"**Bedrooms:** {prop['bedrooms']} BHK")
                        st.write(f"**Area:** {prop['area_sqft']} sqft")
                        st.write(f"**Possession:** {prop['possession']}")
                    with c2:
                        st.write(f"**Price:** {format_inr_full(prop['price'])}")
                        st.write(f"**Furnishing:** {prop['furnishing']}")
                        st.write(f"**Parking:** {prop['parking']}")
                        st.write(f"**Amenities:** {prop['amenities']}")
                        broker_phone = prop.get("broker_phone", "").strip()
                        if broker_phone:
                            st.markdown(f"📞 **Broker:** {broker_phone}")
                    if prop.get("explanation"):
                        for p in prop["explanation"].get("positives", []):
                            st.markdown(f"✓ {p}")
                        for n in prop["explanation"].get("negatives", []):
                            st.markdown(f"✗ {n}")
        else:
            # ── NO RESULTS section with push-feature chat ─────────────────────
            st.markdown("""
<div class='no-result-box'>
<h3>😔 Sorry, no results found matching your exact requirements.</h3>
<p>Try relaxing one or more of your preferences below to discover available properties.</p>
</div>
""", unsafe_allow_html=True)
            st.markdown("#### 🔧 Adjust Your Preferences")
            state = st.session_state.buyer_state

            with st.form("push_preferences_form"):
                st.markdown("Push/relax any requirement to find more options:")
                col_a, col_b = st.columns(2)
                with col_a:
                    new_budget = st.number_input(
                        "💰 Increase max budget (₹)",
                        min_value=0,
                        value=int(state.get("budget_max", 5000000) or 5000000),
                        step=500000,
                        format="%d",
                    )
                    new_location = st.text_input(
                        "📍 Broaden location (e.g., add nearby area)",
                        value=state.get("location", ""),
                    )
                    new_bedrooms = st.selectbox(
                        "🛏️ Adjust bedrooms",
                        [1, 2, 3, 4, 5],
                        index=max(0, (state.get("bedrooms", 2) or 2) - 1),
                    )
                with col_b:
                    new_type = st.selectbox(
                        "🏗️ Property type",
                        ["Apartment", "Villa", "House", "Plot", "Independent House", "Studio"],
                        index=["Apartment", "Villa", "House", "Plot", "Independent House", "Studio"].index(
                            state.get("property_type", "Apartment")
                        ) if state.get("property_type") in ["Apartment", "Villa", "House", "Plot", "Independent House", "Studio"] else 0,
                    )
                    new_parking = st.selectbox(
                        "🚗 Parking preference",
                        ["Yes", "No", "Preferable"],
                        index=["Yes", "No", "Preferable"].index(
                            state.get("parking", "Preferable")
                        ) if state.get("parking") in ["Yes", "No", "Preferable"] else 2,
                    )
                    new_size_min = st.number_input("📐 Min size (sqft)", min_value=0, value=int(state.get("size_min_sqft", 0) or 0), step=100)
                    new_size_max = st.number_input("📐 Max size (sqft)", min_value=0, value=int(state.get("size_max_sqft", 0) or 0), step=100)

                submitted = st.form_submit_button("🔍 Re-search with new preferences")
                if submitted:
                    # Update state with pushed preferences
                    st.session_state.buyer_state.update({
                        "budget_max": new_budget,
                        "location": new_location,
                        "bedrooms": new_bedrooms,
                        "property_type": new_type,
                        "parking": new_parking,
                        "size_min_sqft": new_size_min if new_size_min > 0 else None,
                        "size_max_sqft": new_size_max if new_size_max > 0 else None,
                    })
                    # Re-run matching
                    properties_df = load_properties()
                    matched = match_properties(st.session_state.buyer_state, properties_df)
                    st.session_state.matched_properties = matched
                    qual_result = qualify_buyer(
                        st.session_state.buyer_state, matched,
                        message_count=len(st.session_state.messages)
                    )
                    st.session_state.qualification_result = qual_result
                    # Add in-chat message
                    push_msg = (
                        f"🔄 I've updated your search with relaxed preferences "
                        f"(Budget: {format_inr(new_budget)}, Location: {new_location}, "
                        f"Type: {new_type}, {new_bedrooms}BHK). "
                        f"Found **{len(matched)}** matching properties!"
                    )
                    st.session_state.messages.append({"role": "assistant", "content": push_msg})
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: BROKER DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Broker Dashboard":
    st.title("📊 Broker Dashboard")
    st.caption("Real-time lead management and buyer qualification overview")

    buyers_df = load_buyers()
    stats = get_dashboard_stats(buyers_df)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Leads", stats["total"])
    c2.metric("🟢 Highly Qualified", stats["highly_qualified"])
    c3.metric("🟡 Qualified", stats["qualified"])
    c4.metric("🔵 Needs Info", stats["needs_information"])
    c5.metric("🟠 Low Priority", stats["low_priority"])
    c6.metric("⚫ No Match", stats["no_match"])

    st.markdown("---")

    if buyers_df.empty:
        st.info("No leads yet. Have buyers use the chat to generate leads.")
    else:
        # Filters
        filter_status = st.multiselect(
            "Filter by Status",
            ["HIGHLY_QUALIFIED", "QUALIFIED", "NEEDS_INFORMATION", "LOW_PRIORITY", "UNQUALIFIED", "NO_MATCH"],
            default=[]
        )
        display_df = buyers_df.copy()
        if filter_status:
            display_df = display_df[display_df["status"].isin(filter_status)]

        st.subheader("📋 Lead Pipeline")
        table_cols = ["name", "phone", "qualification_score", "status", "priority",
                      "purpose", "financing", "best_match_property", "best_match_score", "next_action"]
        avail_cols = [c for c in table_cols if c in display_df.columns]
        show_df = display_df[avail_cols].copy()
        if "qualification_score" in show_df.columns:
            show_df = show_df.sort_values("qualification_score", ascending=False)
        st.dataframe(show_df, use_container_width=True, height=280)

        st.markdown("---")
        st.subheader("🔍 Lead Detail")
        if not buyers_df.empty:
            buyer_options = buyers_df["name"].tolist()
            selected_name = st.selectbox("Select a lead", buyer_options)
            if selected_name:
                lead = buyers_df[buyers_df["name"] == selected_name].iloc[0]
                status = str(lead.get("status", "NEW"))
                priority = str(lead.get("priority", "LOW"))
                emoji = get_status_emoji(status)

                if priority == "HIGH":
                    st.error("🔴 HIGH PRIORITY LEAD — Immediate broker action required")
                elif priority == "MEDIUM":
                    st.warning("🟡 MEDIUM PRIORITY LEAD")
                else:
                    st.info("⚪ LOW PRIORITY LEAD")

                d1, d2, d3 = st.columns(3)

                with d1:
                    st.markdown("**👤 Buyer Information**")
                    st.write(f"**Name:** {lead.get('name', 'N/A')}")
                    st.write(f"**📞 Phone:** {lead.get('phone', 'N/A')}")
                    st.write(f"**Budget:** {format_inr(float(lead.get('budget_max', 0) or 0))}")
                    st.write(f"**Location:** {lead.get('location', 'N/A')}")
                    beds = lead.get('bedrooms', 'N/A')
                    ptype = lead.get('property_type', '')
                    st.write(f"**Property:** {beds} BHK {ptype}")
                    st.write(f"**Timeline:** {lead.get('timeline', 'N/A')}")
                    st.write(f"**Purpose:** {lead.get('purpose', 'N/A')}")
                    st.write(f"**Financing:** {lead.get('financing', 'N/A')}")
                    st.write(f"**Parking:** {lead.get('parking', 'N/A')}")
                    amenities_lead = lead.get("amenities", "N/A")
                    st.write(f"**Amenities:** {amenities_lead}")

                with d2:
                    st.markdown("**📊 Qualification Details**")
                    score = lead.get("qualification_score", 0)
                    st.metric("Qualification Score", f"{score}/100")
                    st.write(f"**Status:** {emoji} {status.replace('_', ' ')}")
                    st.write(f"**Priority:** {get_priority_badge(priority)}")
                    bmp = lead.get('best_match_property', 'N/A')
                    bms = lead.get('best_match_score', 0)
                    st.write(f"**Best Match:** {bmp} ({float(bms):.0f}%)")
                    na = str(lead.get('next_action', 'N/A')).replace('_', ' ')
                    st.write(f"**Next Action:** {na}")

                with d3:
                    st.markdown("**🎯 Broker Action**")
                    if status == "HIGHLY_QUALIFIED":
                        st.success("✅ ESCALATE TO BROKER")
                        st.write("This buyer is ready to purchase. Contact immediately!")
                        st.markdown(f"📞 **Call:** {lead.get('phone', 'N/A')}")
                        st.markdown(f"🏆 Best match: **{bmp}** at **{float(bms):.0f}%**")
                    elif status == "QUALIFIED":
                        st.warning("📅 Schedule Site Visit")
                        st.markdown(f"📞 **Call:** {lead.get('phone', 'N/A')}")
                    elif status == "NEEDS_INFORMATION":
                        st.info("ℹ️ Collect More Information")
                        st.write("Follow up to get complete requirements.")
                    else:
                        st.write("Monitor and nurture this lead.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PROPERTIES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏘️ Properties":
    st.title("🏘️ Property Database")
    properties_df = load_properties()

    if properties_df.empty:
        st.warning("No properties found in database.")
    else:
        total = len(properties_df)
        available = int((properties_df["availability"].str.lower() == "available").sum())
        sold = int((properties_df["availability"].str.lower() == "sold").sum())
        reserved = int((properties_df["availability"].str.lower() == "reserved").sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Properties", total)
        m2.metric("✅ Available", available)
        m3.metric("🔴 Sold", sold)
        m4.metric("🟡 Reserved", reserved)

        st.markdown("---")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            loc_filter = st.multiselect("📍 Location", sorted(properties_df["location"].unique()))
        with f2:
            type_filter = st.multiselect("🏗️ Type", sorted(properties_df["property_type"].unique()))
        with f3:
            bed_filter = st.multiselect("🛏 Bedrooms", sorted(properties_df["bedrooms"].unique()))
        with f4:
            avail_filter = st.multiselect("✅ Availability", sorted(properties_df["availability"].unique()))

        filtered = properties_df.copy()
        if loc_filter:
            filtered = filtered[filtered["location"].isin(loc_filter)]
        if type_filter:
            filtered = filtered[filtered["property_type"].isin(type_filter)]
        if bed_filter:
            filtered = filtered[filtered["bedrooms"].isin(bed_filter)]
        if avail_filter:
            filtered = filtered[filtered["availability"].isin(avail_filter)]

        st.write(f"Showing **{len(filtered)}** of {total} properties")
        st.dataframe(filtered, use_container_width=True, height=500)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LEADS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👥 Leads":
    st.title("👥 All Leads")
    buyers_df = load_buyers()

    if buyers_df.empty:
        st.info("No leads collected yet. Have buyers use the chat.")
    else:
        if "qualification_score" in buyers_df.columns:
            buyers_df = buyers_df.sort_values("qualification_score", ascending=False)

        st.write(f"**{len(buyers_df)}** total leads")
        st.markdown("---")

        for _, buyer in buyers_df.iterrows():
            status = str(buyer.get("status", "NEW"))
            emoji = get_status_emoji(status)
            priority = str(buyer.get("priority", "LOW"))
            score = buyer.get("qualification_score", 0)
            bms = float(buyer.get("best_match_score", 0) or 0)

            with st.expander(
                f"{emoji} **{buyer.get('name', 'Unknown')}** | Score: {score}/100 | {status.replace('_', ' ')} | {get_priority_badge(priority)}"
            ):
                lc1, lc2 = st.columns(2)
                with lc1:
                    st.write(f"**Budget:** {format_inr(float(buyer.get('budget_max', 0) or 0))}")
                    st.write(f"**Location:** {buyer.get('location', 'N/A')}")
                    beds = buyer.get('bedrooms', 'N/A')
                    ptype = buyer.get('property_type', '')
                    st.write(f"**Property:** {beds} BHK {ptype}")
                    st.write(f"**Timeline:** {buyer.get('timeline', 'N/A')}")
                    st.write(f"**Purpose:** {buyer.get('purpose', 'N/A')}")
                    st.write(f"**Financing:** {buyer.get('financing', 'N/A')}")
                    st.write(f"**Parking:** {buyer.get('parking', 'N/A')}")
                    st.write(f"**Amenities:** {buyer.get('amenities', 'N/A')}")
                with lc2:
                    bmp = buyer.get('best_match_property', 'N/A')
                    st.write(f"**Best Match:** {bmp} ({bms:.0f}%)")
                    na = str(buyer.get('next_action', 'N/A')).replace('_', ' ')
                    st.write(f"**Next Action:** {na}")
                    st.write(f"**Priority:** {get_priority_badge(priority)}")
                    st.write(f"**Created:** {buyer.get('created_at', 'N/A')}")
