import streamlit as st

st.set_page_config(
    page_title="Gym & Fitness Chatbot",
    page_icon="🏋️",
    layout="centered"
)

st.title("🏋️ Gym & Fitness Assistant")
st.write("Your personal fitness chatbot!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

user_input = st.chat_input("Ask me about fitness, diet or workouts...")

def get_response(text):
    text = text.lower()

    if any(word in text for word in ["hello", "hi", "hey"]):
        return "Hello! Welcome to your Gym and Fitness Assistant."

    elif "workout" in text or "exercise" in text:
        return "Try squats, push-ups, lunges and walking. Start slowly and maintain proper form."

    elif "diet" in text or "food" in text:
        return "Eat a balanced diet with protein, fruits, vegetables and whole grains."

    elif "weight loss" in text or "lose weight" in text:
        return "Combine regular exercise, balanced meals and sufficient sleep for healthy weight management."

    elif "muscle" in text:
        return "Strength training and adequate protein can support muscle development."

    elif "water" in text:
        return "Stay hydrated throughout the day. Your water needs depend on your activity and health."

    elif "membership" in text or "fees" in text:
        return "Please contact your gym reception for membership plans and fees."

    elif "thank" in text:
        return "You're welcome! Keep moving towards your fitness goals!"

    else:
        return "I can help with workouts, diet, weight loss, muscle building and general fitness. Please ask me a question!"

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    response = get_response(user_input)

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )

    st.rerun()

st.sidebar.title("Fitness Tips")
st.sidebar.write("💧 Stay hydrated")
st.sidebar.write("🥗 Eat balanced meals")
st.sidebar.write("🏃 Exercise regularly")
st.sidebar.write("😴 Get enough sleep")
