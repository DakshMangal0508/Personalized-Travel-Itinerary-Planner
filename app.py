import streamlit as st
import pandas as pd
import datetime
import random
import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="Personalized Travel Itinerary Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Wanderlust CSS Styling
st.markdown("""
<style>
    .main {
        background-color: #f8fafc;
    }
    .stButton>button {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 100%);
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 1rem;
        border: 1px solid #e2e8f0;
    }
    h1, h2, h3 {
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# --- SUPABASE AUTHENTICATION AND PERSISTENT TRIP STORAGE ---
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    st.error("Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY in your local environment or Render service settings.")
    st.stop()

if "supabase_client" not in st.session_state:
    st.session_state.supabase_client = create_client(supabase_url, supabase_key)
supabase = st.session_state.supabase_client

if "auth_user_id" not in st.session_state:
    st.session_state.auth_user_id = None

if not st.session_state.auth_user_id:
    st.title("Travel Planner Account")
    st.caption("Sign in or create an account to save and access your trips securely.")
    signin_tab, signup_tab = st.tabs(["Sign in", "Create account"])

    with signin_tab:
        with st.form("signin_form"):
            signin_email = st.text_input("Email", key="signin_email")
            signin_password = st.text_input("Password", type="password", key="signin_password")
            signin_submit = st.form_submit_button("Sign in")
        if signin_submit:
            try:
                auth_response = supabase.auth.sign_in_with_password(
                    {"email": signin_email, "password": signin_password}
                )
                st.session_state.auth_user_id = auth_response.user.id
                st.session_state.auth_email = auth_response.user.email
                st.rerun()
            except Exception as exc:
                st.error(f"Sign-in failed: {exc}")

    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            signup_submit = st.form_submit_button("Create account")
        if signup_submit:
            try:
                auth_response = supabase.auth.sign_up(
                    {"email": signup_email, "password": signup_password}
                )
                if auth_response.session:
                    st.session_state.auth_user_id = auth_response.user.id
                    st.session_state.auth_email = auth_response.user.email
                    st.rerun()
                else:
                    st.info("Check your email to confirm your account, then sign in here.")
            except Exception as exc:
                st.error(f"Account creation failed: {exc}")
    st.stop()

with st.sidebar:
    st.caption(f"Signed in as {st.session_state.get('auth_email', '')}")
    if st.button("Sign out"):
        try:
            supabase.auth.sign_out()
        finally:
            st.session_state.auth_user_id = None
            st.session_state.pop("auth_email", None)
            st.session_state.pop("trips_loaded", None)
            st.session_state.pop("trips_history", None)
            st.session_state.pop("trip_records", None)
            st.session_state.pop("current_trip_id", None)
            st.session_state.pop("current_itinerary", None)
            st.session_state.pop("customized_days", None)
            st.rerun()

# Initialize Session State for persistence
if "trips_history" not in st.session_state:
    st.session_state.trips_history = []
if "current_itinerary" not in st.session_state:
    st.session_state.current_itinerary = None
if "customized_days" not in st.session_state:
    st.session_state.customized_days = {}

if not st.session_state.get("trips_loaded"):
    try:
        result = (
            supabase.table("trips")
            .select("id, destination, itinerary, created_at")
            .eq("owner_id", st.session_state.auth_user_id)
            .order("created_at", desc=True)
            .execute()
        )
        st.session_state.trip_records = result.data
        st.session_state.trips_history = [row["itinerary"] for row in result.data]
        st.session_state.trips_loaded = True
    except Exception as exc:
        st.error(f"Could not load saved trips. Check the trips table and its RLS policies: {exc}")
        st.stop()

if st.session_state.get("success_message"):
    st.success(st.session_state.pop("success_message"))
if st.session_state.get("error_message"):
    st.error(st.session_state.pop("error_message"))

# --- SIDEBAR: CONFIG & PREFERENCES ---
st.sidebar.title("🧭 Traveler Dashboard")
st.sidebar.markdown("---")

# Epic 3: Secure API Key Input & Demo Mode
with st.sidebar.expander("🔑 AI Engine Configuration", expanded=False):
    api_provider = st.selectbox("Select Provider", ["Demo Mode (No Key Required)", "Google Gemini", "Groq AI"])
    api_key = st.text_input("API Key", type="password", help="Enter your Gemini or Groq API key if using live mode.")
    if api_provider != "Demo Mode (No Key Required)" and not api_key:
        st.warning("Running in fallback demo mode until valid key is provided.")

st.sidebar.subheader("🌍 Trip Preferences")

destination_mode = st.sidebar.radio("Destination Mode", ["Specific Destination", "Open-Ended Vibe (Smart Recommender)"])

destination_input = ""
selected_vibe = "Beach"

if destination_mode == "Specific Destination":
    destination_input = st.sidebar.text_input("Destination City/Country", value="Kyoto, Japan")
else:
    selected_vibe = st.sidebar.selectbox("Travel Mood / Vibe", ["Beach & Coastal", "Mountain & Alpine", "Cultural & Heritage", "Urban Metropolis", "Nature & Wildlife"])

col_d1, col_d2 = st.sidebar.columns(2)
with col_d1:
    start_date = st.date_input("Start Date", datetime.date.today() + datetime.timedelta(days=30))
with col_d2:
    duration_days = st.number_input("Duration (Days)", min_value=1, max_value=14, value=5)

budget_level = st.sidebar.selectbox("Budget Tier", ["Budget ($)", "Moderate ($$)", "Luxury ($$$)"])
travel_party = st.sidebar.selectbox("Travel Party", ["Solo", "Couple", "Family", "Friends"])
pace = st.sidebar.selectbox("Pace", ["Relaxed", "Moderate", "Fast-Paced"])

interests = st.sidebar.multiselect(
    "Interests & Activities",
    ["Food & Culinary", "Adventure & Outdoors", "History & Architecture", "Nightlife & Bars", "Shopping", "Art & Museums"],
    default=["Food & Culinary", "History & Architecture"]
)

generate_btn = st.sidebar.button("✨ Generate Itinerary & Plan")

# --- MOCK DATA GENERATOR & ENGINE ---
def generate_mock_itinerary(dest, days, budget, party, pace, interests_list):
    itinerary = []
    base_cost_map = {"Budget ($)": 50, "Moderate ($$)": 150, "Luxury ($$$)": 400}
    daily_base = base_cost_map[budget]
    
    attractions_pool = {
        "History & Architecture": ["Ancient Citadel", "Historic Old Town Square", "Royal Heritage Palace", "Cathedral of Spires"],
        "Food & Culinary": ["Artisan Food Market", "Michelin Star Tasting", "Street Food Alley Tour", "Sunset Rooftop Bistro"],
        "Adventure & Outdoors": ["Scenic Mountain Trail", "Coastal Cliff Hike", "Kayaking Cove Expedition", "Botanical Canopy Walk"],
        "Art & Museums": ["National Modern Art Gallery", "Sculpture Garden & Museum", "Design & Craft Pavilion", "Historical Artifacts Museum"],
        "Nightlife & Bars": ["Neon Underground Lounge", "Craft Brewery Tour", "Live Jazz Speakeasy", "Beachside Bonfire Club"]
    }
    
    for day in range(1, days + 1):
        day_slots = []
        # Morning Slot
        m_cat = interests_list[0] if interests_list else "History & Architecture"
        m_act = random.choice(attractions_pool.get(m_cat, ["City Walking Tour"]))
        day_slots.append({
            "slot": "Morning Sightseeing",
            "activity": f"Explore {m_act}",
            "location": f"{dest} Central District",
            "cost_usd": round(daily_base * 0.2, 2)
        })
        
        # Lunch Slot
        day_slots.append({
            "slot": "Lunch Recommendation",
            "activity": f"Authentic local dining experience featuring regional specialties",
            "location": f"{dest} Culinary Quarter",
            "cost_usd": round(daily_base * 0.15, 2)
        })
        
        # Afternoon Slot
        a_cat = interests_list[1] if len(interests_list) > 1 else "Art & Museums"
        a_act = random.choice(attractions_pool.get(a_cat, ["Scenic Park Walk"]))
        day_slots.append({
            "slot": "Afternoon Leisure",
            "activity": f"Visit {a_act} with guided walkthrough",
            "location": f"{dest} Cultural Zone",
            "cost_usd": round(daily_base * 0.25, 2)
        })
        
        # Evening Slot
        day_slots.append({
            "slot": "Evening Dining & Entertainment",
            "activity": f"Dinner at a top-rated venue & evening relaxation",
            "location": f"{dest} Waterfront/Downtown",
            "cost_usd": round(daily_base * 0.4, 2)
        })
        
        itinerary.append({"day": day, "slots": day_slots})
    return itinerary

# Trigger generation from sidebar
if generate_btn:
    target_dest = destination_input if destination_mode == "Specific Destination" else f"Top {selected_vibe} Destination"
    st.session_state.current_itinerary = {
        "destination": target_dest,
        "duration": duration_days,
        "budget": budget_level,
        "party": travel_party,
        "pace": pace,
        "interests": interests,
        "start_date": str(start_date),
        "plans": generate_mock_itinerary(target_dest, duration_days, budget_level, travel_party, pace, interests)
    }
    st.session_state.customized_days = {}
    st.session_state.current_trip_id = None
    try:
        save_result = supabase.table("trips").insert({
            "destination": target_dest,
            "itinerary": st.session_state.current_itinerary,
            "owner_id": st.session_state.auth_user_id,
        }).select("id, destination, itinerary, created_at").execute()
        st.session_state.trip_records.insert(0, save_result.data[0])
        st.session_state.trips_history.insert(0, st.session_state.current_itinerary)
        st.session_state.current_trip_id = save_result.data[0]["id"]
    except Exception as exc:
        st.session_state.error_message = f"Itinerary generated, but saving it failed: {exc}"
        st.rerun()
    st.success("🎉 Itinerary successfully generated and optimized!")

# --- MAIN APP LAYOUT ---
st.title("✈️ Personalized Travel Itinerary Planner")
st.markdown("Your autonomous AI-powered travel architect delivering optimized, geographically clustered itineraries.")

# Tabs Setup
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Smart Destination Recommender",
    "📅 Day-by-Day Itinerary",
    "⚡ Vibe & Activity Customizer",
    "📂 Trip Management & Export"
])

# --- TAB 1: SMART DESTINATION RECOMMENDER (Epic 3) ---
with tab1:
    st.header("Smart Destination Recommender")
    st.markdown("Unsure where to go? Based on your selected budget, travel mood, and seasonal weather, our AI matches you with top destinations.")
    
    col_r1, col_r2 = st.columns([2, 1])
    with col_r1:
        rec_mood = st.selectbox("Select Travel Mood for Recommendations", ["Beach & Coastal", "Mountain & Alpine", "Cultural & Heritage", "Urban Metropolis", "Nature & Wildlife"], key="rec_mood")
        rec_budget = st.selectbox("Select Target Budget", ["Budget ($)", "Moderate ($$)", "Luxury ($$$)"], key="rec_budget")
    with col_r2:
        st.markdown("<br>", unsafe_allow_html=True)
        find_dest_btn = st.button("🔍 Discover Top Cities")
        
    if find_dest_btn or "recommendations" not in st.session_state:
        recommendations_db = {
            "Beach & Coastal": [
                {"city": "Bali, Indonesia", "tagline": "Tropical paradise with vibrant beach clubs & ancient temples.", "weather": "28°C, Sunny & Breezy", "cost": "Moderate ($$)"},
                {"city": "Phuket, Thailand", "tagline": "Stunning white sands, crystal-clear waters and seafood.", "weather": "30°C, Warm & Tropical", "cost": "Budget ($)"},
                {"city": "Amalfi Coast, Italy", "tagline": "Dramatic cliffs, pastel villages, and Mediterranean luxury.", "weather": "24°C, Pleasant Sun", "cost": "Luxury ($$$)"}
            ],
            "Mountain & Alpine": [
                {"city": "Interlaken, Switzerland", "tagline": "Majestic alpine peaks, glacial lakes, and adventure sports.", "weather": "15°C, Crisp Air", "cost": "Luxury ($$$)"},
                {"city": "Banff, Canada", "tagline": "Turquoise glacial lakes and rugged Rocky Mountain trails.", "weather": "12°C, Clear Skies", "cost": "Moderate ($$)"},
                {"city": "Manali, India", "tagline": "Snow-capped peaks, pine forests, and cozy mountain cafes.", "weather": "14°C, Cool Breeze", "cost": "Budget ($)"}
            ],
            "Cultural & Heritage": [
                {"city": "Kyoto, Japan", "tagline": "Thousands of classical Buddhist temples, gardens, and imperial palaces.", "weather": "20°C, Mild Autumn", "cost": "Moderate ($$)"},
                {"city": "Rome, Italy", "tagline": "Living museum with iconic ancient ruins, art, and Vatican history.", "weather": "22°C, Sunny", "cost": "Moderate ($$)"},
                {"city": "Cairo, Egypt", "tagline": "Legendary pyramids, Sphinx, and rich pharaonic heritage.", "weather": "29°C, Dry & Warm", "cost": "Budget ($)"}
            ],
            "Urban Metropolis": [
                {"city": "Tokyo, Japan", "tagline": "Ultra-modern neon skyscrapers mixed with historic temples.", "weather": "19°C, Crisp", "cost": "Moderate ($$)"},
                {"city": "New York City, USA", "tagline": "The city that never sleeps, Broadway, and world-class dining.", "weather": "18°C, Mild", "cost": "Luxury ($$$)"},
                {"city": "Singapore", "tagline": "Futuristic skyline, lush gardens by the bay, and hawker food culture.", "weather": "31°C, Humid & Warm", "cost": "Luxury ($$$)"}
            ],
            "Nature & Wildlife": [
                {"city": "Costa Rica (Arenal)", "tagline": "Lush rainforests, active volcanoes, and exotic wildlife.", "weather": "26°C, Tropical Showers", "cost": "Moderate ($$)"},
                {"city": "Cape Town, South Africa", "tagline": "Dramatic coastlines, vineyards, and safari wildlife proximity.", "weather": "21°C, Sunny", "cost": "Moderate ($$)"},
                {"city": "Queenstown, New Zealand", "tagline": "Adventure capital surrounded by dramatic Southern Alps and fjords.", "weather": "16°C, Fresh Alpine", "cost": "Luxury ($$$)"}
            ]
        }
        st.session_state.recommendations = recommendations_db.get(rec_mood, recommendations_db["Beach & Coastal"])

    if "recommendations" in st.session_state:
        st.markdown("### 🌟 Top 3 Recommended Destinations")
        cols = st.columns(3)
        for idx, rec in enumerate(st.session_state.recommendations):
            with cols[idx]:
                st.markdown(f"""
                <div class="card">
                    <h4>{rec['city']}</h4>
                    <p><em>{rec['tagline']}</em></p>
                    <hr style="margin: 0.5rem 0; border-color: #e2e8f0;">
                    <p><b>🌤️ Weather:</b> {rec['weather']}</p>
                    <p><b>💰 Tier:</b> {rec['cost']}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Select {rec['city'].split(',')[0]}", key=f"select_rec_{idx}"):
                    st.success(f"Selected {rec['city']}! Go to Sidebar or Tab 2 to generate itinerary.")

# --- TAB 2: DAY-BY-DAY OPTIMIZED ITINERARY (Epic 4) ---
with tab2:
    st.header("Day-by-Day Optimized Itinerary")
    
    if not st.session_state.current_itinerary:
        st.info("👈 Please generate an itinerary using the sidebar controls or select a destination from Tab 1.")
    else:
        itinerary = st.session_state.current_itinerary
        
        total_days = itinerary['duration']
        total_usd = sum([sum([slot['cost_usd'] for slot in day['slots']]) for day in itinerary['plans']])
        total_inr = total_usd * 83.5 
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Destination", itinerary['destination'])
        with col_m2:
            st.metric("Duration", f"{total_days} Days")
        with col_m3:
            st.metric("Total Budget (USD)", f"${total_usd:,.2f}")
        with col_m4:
            st.metric("Total Budget (INR)", f"₹{total_inr:,.2f}")
            
        st.markdown("---")
        st.markdown("### 📍 Geographic Clustering & Time-Slot Breakdown")
        st.markdown("Activities are algorithmically grouped by geographic proximity to minimize transit fatigue.")

        for day_plan in itinerary['plans']:
            day_num = day_plan['day']
            with st.expander(f"📅 Day {day_num} - Optimized Itinerary Schedule", expanded=(day_num == 1)):
                active_slots = st.session_state.customized_days.get(day_num, day_plan['slots'])
                
                for slot in active_slots:
                    col_s1, col_s2, col_s3 = st.columns([1, 3, 1])
                    with col_s1:
                        st.markdown(f"**⏰ {slot['slot']}**")
                    with col_s2:
                        st.markdown(f"🎯 **{slot['activity']}**<br><small>📍 {slot['location']}</small>", unsafe_allow_html=True)
                    with col_s3:
                        st.markdown(f"💵 **${slot['cost_usd']:.2f}**<br><small>₹{slot['cost_usd']*83.5:,.0f}</small>", unsafe_allow_html=True)
                    st.markdown("---")

# --- TAB 3: VIBE CUSTOMIZATION & DYNAMIC ACTIVITY SWAP (Epic 4) ---
with tab3:
    st.header("Vibe Customization & Dynamic Activity Swap")
    st.markdown("Fine-tune specific time slots or regenerate individual days without disrupting the rest of your trip.")
    
    if not st.session_state.current_itinerary:
        st.info("Please generate an itinerary first.")
    else:
        current_itin = st.session_state.current_itinerary
        selected_day_idx = st.selectbox("Select Day to Customize", options=[d['day'] for d in current_itin['plans']], format_func=lambda x: f"Day {x}")
        
        target_day_plan = next(d for d in current_itin['plans'] if d['day'] == selected_day_idx)
        current_slots = st.session_state.customized_days.get(selected_day_idx, target_day_plan['slots'])
        
        st.subheader(f"Modifying Day {selected_day_idx} Slots")
        slot_to_edit = st.selectbox("Select Time Slot to Modify", options=[s['slot'] for s in current_slots])
        
        swap_action = st.radio("Customization Action", ["Swap Activity Category", "Custom Activity Description", "Find Vegetarian/Vegan Dining Spot"])
        
        new_activity_input = ""
        if swap_action == "Swap Activity Category":
            new_cat = st.selectbox("Choose New Vibe/Category", ["Hidden Gem Local Spot", "Relaxing Café & Bookstore", "Scenic Viewpoint & Photography", "Adventure & Thrill Activity", "Local Cultural Workshop"])
            new_activity_input = f"Explore {new_cat}"
        elif swap_action == "Find Vegetarian/Vegan Dining Spot":
            new_activity_input = "Plant-based culinary experience at top local vegetarian bistro"
        else:
            new_activity_input = st.text_input("Enter custom activity description", value="Custom curated experience")
            
        if st.button("⚡ Apply Activity Swap & Regenerate Slot"):
            updated_slots = []
            for s in current_slots:
                if s['slot'] == slot_to_edit:
                    s_copy = s.copy()
                    s_copy['activity'] = new_activity_input
                    updated_slots.append(s_copy)
                else:
                    updated_slots.append(s)
            st.session_state.customized_days[selected_day_idx] = updated_slots
            target_day_plan["slots"] = updated_slots
            try:
                supabase.table("trips").update({
                    "itinerary": current_itin,
                }).eq("id", st.session_state.current_trip_id).eq(
                    "owner_id", st.session_state.auth_user_id
                ).execute()
                st.session_state.success_message = "Activity updated and saved to your trip."
            except Exception as exc:
                st.session_state.error_message = f"Activity updated for this session, but saving it failed: {exc}"
            st.rerun()

# --- TAB 4: TRIP MANAGEMENT & OFFLINE PDF EXPORT (Epic 5) ---
with tab4:
    st.header("Trip Management & Offline Export")
    st.markdown("Manage your saved itineraries in session memory and export clean, beautifully formatted offline PDF guidebooks with emergency checklists.")
    
    if not st.session_state.trips_history:
        st.info("No saved trips in history yet.")
    else:
        st.subheader("📂 Saved Trips History")
        for idx, trip in enumerate(st.session_state.trips_history):
            col_h1, col_h2, col_h3 = st.columns([3, 2, 1])
            with col_h1:
                st.markdown(f"**Trip #{idx+1}: {trip['destination']}** ({trip['duration']} Days)")
            with col_h2:
                st.markdown(f"Tier: {trip['budget']} | Party: {trip['party']}")
            with col_h3:
                if st.button("Load Trip", key=f"load_trip_{idx}"):
                    st.session_state.current_itinerary = trip
                    st.session_state.current_trip_id = st.session_state.trip_records[idx]["id"]
                    st.session_state.customized_days = {}
                    st.success(f"Loaded Trip to {trip['destination']}!")
                    st.rerun()
                    
        st.markdown("---")
        st.subheader("📥 Export Offline Itinerary Guidebook")
        st.markdown("Generate a comprehensive markdown/PDF export bundle with emergency contact checklists and daily schedules.")
        
        if st.session_state.current_itinerary:
            active_trip = st.session_state.current_itinerary
            
            export_content = f"""# TRAVEL ITINERARY GUIDEBOOK
**Destination:** {active_trip['destination']}
**Duration:** {active_trip['duration']} Days
**Travel Dates:** {active_trip.get('start_date', 'N/A')}
**Budget Level:** {active_trip['budget']}
**Travel Party:** {active_trip['party']}
**Pace:** {active_trip['pace']}

---

## EMERGENCY CONTACTS & CHECKLIST
- **Local Police/Emergency:** 112 / 911
- **Tourist Helpline:** Available 24/7
- **Embassy / Consulate:** Register with local mission
- **Checklist:** Passport, Travel Insurance, Universal Adapter, Prescriptions

---
"""
            for day_p in active_trip['plans']:
                export_content += f"\n### Day {day_p['day']}\n"
                d_slots = st.session_state.customized_days.get(day_p['day'], day_p['slots'])
                for s in d_slots:
                    export_content += f"- **{s['slot']}**: {s['activity']} @ {s['location']} (Est. ${s['cost_usd']:.2f})\n"
            
            st.download_button(
                label="📄 Download Complete Itinerary (Markdown / PDF Ready)",
                data=export_content,
                file_name=f"Itinerary_{active_trip['destination'].replace(', ', '_')}.md",
                mime="text/markdown"
            )

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b;'>Personalized Travel Itinerary Planner | Skill Wallet Capstone Project 4 | Built with Streamlit</p>", unsafe_allow_html=True)
