"""
Gym & Fitness Assistant - dynamic Streamlit app.
Chatbot + BMI / calorie / water calculators + weekly workout planner + progress tracker.
Run:  streamlit run app.py
General wellness information only - not medical advice.
"""
import base64
import html
import re
from datetime import date, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gym & Fitness Assistant", page_icon="🏋️", layout="wide")

DISCLAIMER = ("General wellness information only, not medical advice. "
              "If you have a health condition, are pregnant, or feel unwell, check with a doctor first.")


# =====================================================================
#                          CHATBOT LOGIC
# =====================================================================
# Order matters: the first matching topic wins.
TOPICS = [
    ("SAFETY", r"\b(chest pain|dizzy|dizziness|faint|fainting|injury|injured|sprain|severe pain|pain)\b",
     "Please take this seriously: if you feel chest pain, dizziness, fainting or sharp pain, "
     "stop exercising and get medical help. For an ongoing injury, see a doctor or physiotherapist "
     "before training that area."),
    ("GREETING", r"\b(hello|hi|hey)\b",
     "Hello! Welcome to your Gym and Fitness Assistant."),
    ("THANKS", r"\b(thanks|thank|thankyou)\b",
     "You're welcome! Keep moving towards your fitness goals!"),
    ("WEIGHT_LOSS", r"\b(weight loss|lose weight|fat loss|losing weight)\b",
     "Combine regular exercise, balanced meals and sufficient sleep for healthy weight management. "
     "Aim for slow, steady progress rather than crash diets."),
    ("PROTEIN", r"\bprotein\b",
     "Good protein sources: eggs, dairy, lentils, beans, tofu, fish and chicken. Many active adults "
     "aim for about 1.2 to 2.0 g per kg of body weight a day. Check with a doctor or dietitian "
     "if you have kidney or other health conditions."),
    ("MUSCLE", r"\b(muscle|muscles|bulk|bulking)\b",
     "Strength training and adequate protein can support muscle development. Train each muscle "
     "group about twice a week and let it recover."),
    ("WORKOUT", r"\b(workout|workouts|exercise|exercises|training|routine)\b",
     "Try squats, push-ups, lunges and walking. Start slowly and maintain proper form. "
     "Use the Workout Planner page for a full weekly plan."),
    ("DIET", r"\b(diet|food|foods|eat|meal|meals|nutrition)\b",
     "Eat a balanced diet with protein, fruits, vegetables and whole grains."),
    ("WATER", r"\b(water|hydrate|hydration|hydrated)\b",
     "Stay hydrated throughout the day. Your water needs depend on your activity and health. "
     "Try the Water calculator on the Calculators page."),
    ("SLEEP", r"\b(sleep|rest day|recovery)\b",
     "Most adults do well with 7 to 9 hours of sleep. Muscles recover and grow during rest, "
     "so plan at least one or two rest days a week."),
    ("CARDIO", r"\b(cardio|running|jogging|cycling|walking)\b",
     "For general health, many adults aim for about 150 minutes of moderate cardio a week, "
     "such as brisk walking or cycling. Build up gradually."),
    ("MEMBERSHIP", r"\b(membership|fee|fees|gym plans)\b",
     "Please contact your gym reception for membership plans and fees."),
]

FALLBACK = ("I can help with workouts, diet, weight loss, muscle building and general fitness. "
            "Please ask me a question!")


def get_response(text):
    """Return (topic, reply) for one message."""
    t = text.lower().strip()
    for topic, pattern, reply in TOPICS:
        if re.search(pattern, t):
            return topic, reply
    return "UNKNOWN", FALLBACK


# =====================================================================
#                          CALCULATORS & PLANNER
# =====================================================================
def calc_bmi(weight_kg, height_cm):
    return weight_kg / ((height_cm / 100) ** 2)


def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal range"
    if bmi < 30:
        return "Overweight"
    return "Obesity range"


ACTIVITY = {
    "Sedentary (little or no exercise)": 1.2,
    "Light (1-3 days/week)": 1.375,
    "Moderate (3-5 days/week)": 1.55,
    "Very active (6-7 days/week)": 1.725,
}
GOAL_ADJUST = {"Maintain weight": 0.0, "Lose weight gently": -0.15, "Build muscle": 0.10}


def calc_calories(sex, age, height_cm, weight_kg, activity_mult, goal):
    """Mifflin-St Jeor estimate. The target never goes below BMR or 1,200 kcal."""
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "Male" else -161)
    tdee = bmr * activity_mult
    target = max(round(tdee * (1 + GOAL_ADJUST[goal])), round(bmr), 1200)
    protein = round(weight_kg * (1.6 if goal == "Build muscle" else 1.2))
    fat = round(target * 0.25 / 9)
    carbs = max(0, round((target - protein * 4 - fat * 9) / 4))
    return {"bmr": round(bmr), "tdee": round(tdee), "target": target,
            "protein": protein, "fat": fat, "carbs": carbs}


def calc_water(weight_kg, exercise_min, hot_weather):
    """About 33 ml per kg, plus about 12 ml per exercise minute, plus extra in hot weather."""
    return weight_kg * 0.033 + exercise_min * 0.012 + (0.5 if hot_weather else 0)


FOCUS_EMOJI = {"Full body A": "🏋️", "Full body B": "🏋️", "Upper body": "💪", "Lower body": "🦵",
               "Push": "🤜", "Pull": "🧗", "Legs": "🦵", "Cardio & core": "🏃", "Rest": "😴"}

EXERCISES = {
    "Full body A": {
        "Bodyweight": ["Squats", "Push-ups", "Glute bridges", "Plank"],
        "Dumbbells": ["Goblet squat", "Dumbbell bench press", "Dumbbell row", "Plank"],
        "Gym": ["Leg press", "Chest press machine", "Lat pulldown", "Plank"]},
    "Full body B": {
        "Bodyweight": ["Lunges", "Incline push-ups", "Superman hold", "Mountain climbers"],
        "Dumbbells": ["Romanian deadlift", "Shoulder press", "One-arm row", "Dead bug"],
        "Gym": ["Hack squat or leg press", "Seated row", "Shoulder press machine", "Cable crunch"]},
    "Upper body": {
        "Bodyweight": ["Push-ups", "Pike push-ups", "Inverted rows or towel rows", "Plank shoulder taps"],
        "Dumbbells": ["Dumbbell bench press", "Dumbbell row", "Shoulder press", "Bicep curls"],
        "Gym": ["Bench press", "Lat pulldown", "Overhead press", "Cable triceps pushdown"]},
    "Lower body": {
        "Bodyweight": ["Squats", "Reverse lunges", "Glute bridges", "Calf raises"],
        "Dumbbells": ["Goblet squat", "Romanian deadlift", "Walking lunges", "Calf raises"],
        "Gym": ["Squat or leg press", "Leg curl", "Hip thrust", "Calf raise machine"]},
    "Push": {
        "Bodyweight": ["Push-ups", "Pike push-ups", "Bench dips", "Diamond push-ups"],
        "Dumbbells": ["Dumbbell bench press", "Shoulder press", "Lateral raises", "Triceps extension"],
        "Gym": ["Bench press", "Overhead press", "Incline dumbbell press", "Triceps pushdown"]},
    "Pull": {
        "Bodyweight": ["Towel rows", "Superman hold", "Reverse snow angels", "Hip hinge good mornings"],
        "Dumbbells": ["One-arm row", "Rear delt fly", "Bicep curls", "Hammer curls"],
        "Gym": ["Lat pulldown", "Seated cable row", "Face pulls", "Bicep curls"]},
    "Legs": {
        "Bodyweight": ["Squats", "Split squats", "Glute bridges", "Wall sit"],
        "Dumbbells": ["Goblet squat", "Romanian deadlift", "Step-ups", "Calf raises"],
        "Gym": ["Squat or leg press", "Leg extension", "Leg curl", "Calf raise machine"]},
    "Cardio & core": {
        "Bodyweight": ["Brisk walk or jog", "Plank", "Bicycle crunches", "Dead bug"],
        "Dumbbells": ["Brisk walk or jog", "Plank", "Russian twist", "Farmer's carry"],
        "Gym": ["Treadmill or cycle", "Plank", "Cable crunch", "Hanging knee raise"]},
}

TEMPLATES = {
    2: ["Full body A", "Full body B"],
    3: ["Full body A", "Full body B", "Cardio & core"],
    4: ["Upper body", "Lower body", "Upper body", "Lower body"],
    5: ["Push", "Pull", "Legs", "Upper body", "Cardio & core"],
    6: ["Push", "Pull", "Legs", "Push", "Pull", "Legs"],
}
DAY_SLOTS = {2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 4, 5], 6: [0, 1, 2, 3, 4, 5]}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
REPS = {"Build muscle": "8-12", "Lose weight": "12-15", "General fitness": "10-12"}
SETS = {"Beginner": 2, "Intermediate": 3, "Advanced": 4}
FINISHER = {"Build muscle": "", "Lose weight": " + 15-20 min brisk walk or cycle",
            "General fitness": " + 10 min easy cardio"}


def build_plan(goal, level, days, equipment):
    """Return a list of 7 dicts (Mon-Sun) with Focus, Exercises and Prescription."""
    focus_by_day = dict(zip(DAY_SLOTS[days], TEMPLATES[days]))
    plan = []
    for i, day in enumerate(DAYS):
        focus = focus_by_day.get(i)
        if not focus:
            plan.append({"Day": day, "Focus": "Rest", "Exercises": "Rest, stretching or an easy walk",
                         "Prescription": "-"})
            continue
        exercises = EXERCISES[focus][equipment]
        if focus == "Cardio & core":
            rx = "20-30 min easy-moderate cardio, then core: 3 rounds of 30-45 sec"
        else:
            rx = f"{SETS[level]} sets x {REPS[goal]} reps{FINISHER[goal]}"
        plan.append({"Day": day, "Focus": focus, "Exercises": ", ".join(exercises), "Prescription": rx})
    return plan


# =====================================================================
#                          IMAGES (SVG drawn in code)
# =====================================================================
def svg_img(svg, radius=14):
    b64 = base64.b64encode(svg.encode("utf-8")).decode()
    return (f'<img src="data:image/svg+xml;base64,{b64}" '
            f'style="width:100%;border-radius:{radius}px;" />')


def hero_svg():
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 230">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#b71c1c"/><stop offset="1" stop-color="#ff7043"/></linearGradient></defs>
<rect width="900" height="230" fill="url(#g)"/>
<circle cx="760" cy="60" r="140" fill="#fff" opacity="0.08"/>
<g fill="#ffffff" opacity="0.93">
<rect x="620" y="108" width="200" height="14" rx="4"/>
<rect x="600" y="78" width="20" height="74" rx="5"/><rect x="578" y="92" width="18" height="46" rx="5"/>
<rect x="820" y="78" width="20" height="74" rx="5"/><rect x="844" y="92" width="18" height="46" rx="5"/></g>
<text x="50" y="105" font-family="sans-serif" font-size="46" font-weight="bold" fill="#fff">Gym &amp; Fitness Assistant</text>
<text x="50" y="145" font-family="sans-serif" font-size="20" fill="#ffe0d6">Chat, calculate, plan your week and track your progress</text>
<rect x="50" y="165" width="400" height="34" rx="17" fill="#ffffff" opacity="0.2"/>
<text x="68" y="188" font-family="sans-serif" font-size="16" fill="#fff">Workouts  |  Nutrition  |  Hydration  |  Tracking</text>
</svg>"""


def feature_svg(emoji, title, sub, c1, c2):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 170">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
<rect width="300" height="170" fill="url(#g)"/>
<circle cx="250" cy="40" r="70" fill="#fff" opacity="0.12"/>
<text x="24" y="85" font-size="52">{emoji}</text>
<text x="24" y="124" font-family="sans-serif" font-size="22" font-weight="bold" fill="#fff">{html.escape(title)}</text>
<text x="24" y="148" font-family="sans-serif" font-size="13" fill="#fff" opacity="0.9">{html.escape(sub)}</text>
</svg>"""


def day_svg(day, focus):
    rest = focus == "Rest"
    c1, c2 = ("#90a4ae", "#b0bec5") if rest else ("#c62828", "#ff7043")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
<rect width="120" height="120" fill="url(#g)"/>
<text x="12" y="28" font-family="sans-serif" font-size="16" font-weight="bold" fill="#fff">{day}</text>
<text x="12" y="76" font-size="38">{FOCUS_EMOJI.get(focus, "🏋️")}</text>
<text x="12" y="102" font-family="sans-serif" font-size="13" fill="#fff">{html.escape(focus)}</text>
</svg>"""


def flow_svg():
    boxes = [
        (20, "1  You ask", "workouts, diet, goals", "#e3f2fd", "#1565c0"),
        (330, "2  Bot picks topic", "or you use the tools", "#fff3e0", "#e65100"),
        (640, "3  Plan and track", "tips, plans, progress", "#e8f5e9", "#2e7d32"),
    ]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 200">',
             '<rect width="900" height="200" fill="#f7f9fc"/>']
    for x, t, s, bg, fg in boxes:
        parts.append(f'<rect x="{x}" y="40" width="240" height="120" rx="16" fill="{bg}" stroke="{fg}" stroke-width="2"/>')
        parts.append(f'<text x="{x + 20}" y="90" font-family="sans-serif" font-size="24" font-weight="bold" fill="{fg}">{t}</text>')
        parts.append(f'<text x="{x + 20}" y="124" font-family="sans-serif" font-size="16" fill="#444">{s}</text>')
    for x in (268, 578):
        parts.append(f'<polygon points="{x},85 {x + 40},100 {x},115" fill="#90a4ae"/>')
    parts.append("</svg>")
    return "".join(parts)


# =====================================================================
#                          STREAMLIT UI
# =====================================================================
WELCOME = ("Hello! I'm your Gym and Fitness Assistant. Ask about workouts, diet, weight loss, "
           "muscle building or hydration, or use the tools in the sidebar.")

SAMPLE_PROMPTS = [
    "Hello", "Give me a workout", "What should I eat?", "How to lose weight?",
    "How to build muscle?", "How much water should I drink?", "Gym membership fees",
    "I feel dizzy while exercising",
]

PAGES = ["🏠 Home", "💬 Chat", "🧮 Calculators", "📅 Workout Planner", "📈 Progress Tracker"]


def reset_chat():
    st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
    st.session_state.last_topic = None


def init_session():
    st.session_state.setdefault("log", [])
    if "messages" not in st.session_state:
        reset_chat()


def send_message(user_text):
    topic, reply = get_response(user_text)
    name = st.session_state.get("user_name", "").strip()
    if name and topic == "GREETING":
        reply = reply.replace("Hello!", f"Hello {name}!", 1)
    st.session_state.messages.append({"role": "user", "content": user_text})
    st.session_state.messages.append({"role": "assistant", "content": reply, "topic": topic})
    st.session_state.last_topic = topic


def week_minutes(goal_days=7):
    cutoff = date.today() - timedelta(days=goal_days - 1)
    return sum(e["Minutes"] for e in st.session_state.log if e["Date"] >= cutoff)


# ---------- Pages ----------
def page_home():
    st.markdown(svg_img(hero_svg(), 18), unsafe_allow_html=True)
    st.write("")
    n_user = sum(1 for m in st.session_state.messages if m["role"] == "user")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Topics I can answer", len(TOPICS))
    m2.metric("Messages you sent", n_user)
    m3.metric("Workouts logged", len(st.session_state.log))
    m4.metric("Minutes this week", week_minutes())

    st.subheader("What can you do here?")
    cards = [
        ("💪", "Workouts", "Exercise ideas and weekly plans", "#b71c1c", "#ef5350"),
        ("🥗", "Diet", "Balanced eating and protein tips", "#1b5e20", "#66bb6a"),
        ("⚖️", "Weight goals", "BMI and calorie estimates", "#4a148c", "#ab47bc"),
        ("🏋️", "Muscle", "Strength training basics", "#0d47a1", "#42a5f5"),
        ("💧", "Hydration", "Daily water estimate", "#006064", "#26c6da"),
        ("📈", "Progress", "Log sessions and weight", "#e65100", "#ffa726"),
    ]
    for row in (cards[:3], cards[3:]):
        cols = st.columns(3)
        for col, (e, t, s, c1, c2) in zip(cols, row):
            col.markdown(svg_img(feature_svg(e, t, s, c1, c2)), unsafe_allow_html=True)
        st.write("")

    st.subheader("How it works")
    st.markdown(svg_img(flow_svg()), unsafe_allow_html=True)
    st.info("Open **Chat** for quick answers, **Calculators** for BMI, calories and water, "
            "**Workout Planner** for a weekly plan, or **Progress Tracker** to log your sessions.")
    st.caption(DISCLAIMER)


def page_chat():
    st.subheader("💬 Chat with your fitness assistant")
    cols = st.columns(4)
    for i, p in enumerate(SAMPLE_PROMPTS):
        if cols[i % 4].button(p, key=f"sample_{i}", use_container_width=True):
            st.session_state.queued = p

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("topic"):
                st.caption(f"Topic detected: {m['topic']}")

    user_input = st.chat_input("Ask me about fitness, diet or workouts...")
    if "queued" in st.session_state:
        user_input = st.session_state.pop("queued")
    if user_input:
        send_message(user_input)
        st.rerun()


def tab_bmi():
    c1, c2 = st.columns(2)
    height = c1.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=170.0, step=0.5, key="bmi_h")
    weight = c2.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=65.0, step=0.5, key="bmi_w")
    bmi = calc_bmi(weight, height)
    k1, k2 = st.columns(2)
    k1.metric("BMI", f"{bmi:.1f}")
    k2.metric("Category (adult)", bmi_category(bmi))
    lo, hi = 18.5 * (height / 100) ** 2, 24.9 * (height / 100) ** 2
    st.caption(f"The normal BMI range for your height is about {lo:.0f} to {hi:.0f} kg. "
               "BMI is only a rough screen: it does not separate muscle from fat. For adults only.")


def tab_calories():
    c1, c2, c3 = st.columns(3)
    sex = c1.selectbox("Sex", ["Male", "Female"], key="cal_sex")
    age = c2.number_input("Age (18 or older)", min_value=18, max_value=90, value=25, key="cal_age")
    activity = c3.selectbox("Activity level", list(ACTIVITY.keys()), key="cal_act")
    d1, d2, d3 = st.columns(3)
    height = d1.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=170.0, step=0.5, key="cal_h")
    weight = d2.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=65.0, step=0.5, key="cal_w")
    goal = d3.selectbox("Goal", list(GOAL_ADJUST.keys()), key="cal_goal")

    r = calc_calories(sex, age, height, weight, ACTIVITY[activity], goal)
    k1, k2, k3 = st.columns(3)
    k1.metric("Resting burn (BMR)", f"{r['bmr']} kcal")
    k2.metric("Daily burn (TDEE)", f"{r['tdee']} kcal")
    k3.metric("Suggested intake", f"{r['target']} kcal")
    p1, p2, p3 = st.columns(3)
    p1.metric("Protein", f"{r['protein']} g")
    p2.metric("Carbs", f"{r['carbs']} g")
    p3.metric("Fat", f"{r['fat']} g")
    st.bar_chart(pd.DataFrame({"kcal": [r["protein"] * 4, r["carbs"] * 4, r["fat"] * 9]},
                              index=["Protein", "Carbs", "Fat"]))
    st.caption("Estimate using the Mifflin-St Jeor formula. Weight loss uses a gentle 15% reduction and "
               "never goes below your resting burn or 1,200 kcal. Real needs vary, so adjust with your doctor or dietitian.")


def tab_water():
    c1, c2, c3 = st.columns(3)
    weight = c1.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=65.0, step=0.5, key="wat_w")
    minutes = c2.slider("Exercise today (minutes)", 0, 180, 45, key="wat_min")
    hot = c3.checkbox("Hot or humid weather", key="wat_hot")
    litres = calc_water(weight, minutes, hot)
    k1, k2 = st.columns(2)
    k1.metric("Estimated water", f"{litres:.1f} L")
    k2.metric("In glasses (250 ml)", f"{litres * 4:.0f}")
    st.progress(min(1.0, litres / 5.0))
    st.caption("Rough guide only. Needs depend on your health, diet and climate. "
               "Follow your doctor's advice if you have a heart or kidney condition.")


def page_calculators():
    st.subheader("🧮 Calculators")
    st.caption(DISCLAIMER)
    t1, t2, t3 = st.tabs(["⚖️ BMI", "🔥 Calories & macros", "💧 Water"])
    with t1:
        tab_bmi()
    with t2:
        tab_calories()
    with t3:
        tab_water()


def page_planner():
    st.subheader("📅 Workout Planner")
    st.caption("Choose your details and get a weekly plan. " + DISCLAIMER)
    c1, c2, c3, c4 = st.columns(4)
    goal = c1.selectbox("Goal", list(REPS.keys()), index=2)
    level = c2.selectbox("Experience", list(SETS.keys()))
    equipment = c3.selectbox("Equipment", ["Bodyweight", "Dumbbells", "Gym"])
    days = c4.slider("Training days per week", 2, 6, 3)

    plan = build_plan(goal, level, days, equipment)
    cols = st.columns(7)
    for col, row in zip(cols, plan):
        col.markdown(svg_img(day_svg(row["Day"], row["Focus"]), 10), unsafe_allow_html=True)

    st.write("")
    st.dataframe(pd.DataFrame(plan), hide_index=True, use_container_width=True)
    st.info("Warm up for 5 to 10 minutes first, keep good form, and stop if anything hurts. "
            "Increase weights or reps gradually.")


def page_tracker():
    st.subheader("📈 Progress Tracker")
    with st.form("log_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        d = f1.date_input("Date", value=date.today())
        weight = f2.number_input("Body weight (kg)", min_value=30.0, max_value=250.0, value=65.0, step=0.1)
        minutes = f3.number_input("Workout minutes", min_value=0, max_value=300, value=45, step=5)
        g1, g2 = st.columns(2)
        kind = g1.selectbox("Type", ["Strength", "Cardio", "Yoga / mobility", "Sports", "Rest day"])
        note = g2.text_input("Note (optional)", placeholder="e.g. felt strong today")
        saved = st.form_submit_button("Add entry")
    if saved:
        st.session_state.log.append({"Date": d, "Weight (kg)": weight, "Minutes": int(minutes),
                                     "Type": kind, "Note": note.strip()})
        st.success("Entry added.")

    goal_min = st.number_input("Weekly goal (minutes)", min_value=30, max_value=1000, value=150, step=10)
    done = week_minutes()
    st.progress(min(1.0, done / goal_min))
    st.write(f"**{done}** of **{goal_min}** minutes in the last 7 days")

    if not st.session_state.log:
        st.info("No entries yet. Add your first session above.")
        return
    df = pd.DataFrame(st.session_state.log).sort_values("Date")
    k1, k2, k3 = st.columns(3)
    k1.metric("Sessions logged", len(df))
    k2.metric("Total minutes", int(df["Minutes"].sum()))
    change = df["Weight (kg)"].iloc[-1] - df["Weight (kg)"].iloc[0]
    k3.metric("Latest weight", f"{df['Weight (kg)'].iloc[-1]:.1f} kg", f"{change:+.1f} kg since first entry",
              delta_color="off")
    st.markdown("**Body weight over time**")
    st.line_chart(df.set_index("Date")[["Weight (kg)"]])
    st.markdown("**Minutes per session**")
    st.bar_chart(df.set_index("Date")[["Minutes"]])
    st.dataframe(df, hide_index=True, use_container_width=True)
    if st.button("Clear all entries"):
        st.session_state.log = []
        st.rerun()


# ---------- Sidebar + routing ----------
init_session()

with st.sidebar:
    st.title("🏋️ Fitness Assistant")
    page = st.radio("Go to", PAGES, key="page")
    st.text_input("Your name (optional)", key="user_name", placeholder="e.g. Pallavi")
    st.divider()
    if st.button("🔄 Reset conversation", use_container_width=True):
        reset_chat()
        st.rerun()
    if st.session_state.last_topic:
        st.markdown(f"**Last topic:** `{st.session_state.last_topic}`")
    st.subheader("Fitness Tips")
    st.write("💧 Stay hydrated")
    st.write("🥗 Eat balanced meals")
    st.write("🏃 Exercise regularly")
    st.write("😴 Get enough sleep")

if page == PAGES[0]:
    page_home()
elif page == PAGES[1]:
    page_chat()
elif page == PAGES[2]:
    page_calculators()
elif page == PAGES[3]:
    page_planner()
else:
    page_tracker()
