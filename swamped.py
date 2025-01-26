import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import folium
from streamlit_folium import st_folium
from authlib.integrations.requests_client import OAuth2Session
import requests
import os
from urllib.parse import urlencode
import geocoder
import pymysql
from PIL import Image

# Auth0 configuration
AUTH0_DOMAIN = "dev-i0xqob7z3wcxgnv6.us.auth0.com"
AUTH0_CLIENT_ID = "nli9lfPOU4Et0gyypt0yW3k2aBVEnj9T"
AUTH0_CLIENT_SECRET = "uAKVGMg_BwlbxpXciZ6VHESXGAz6u-nU2AHVLiw1CELwaz_WF0C3ToWqVw9dCkg3"
AUTH0_CALLBACK_URL = "http://localhost:8501/"

# Database Configuration
DB_HOST = "userdrinksdb.czs6iaqeqm1d.us-east-1.rds.amazonaws.com"
DB_NAME = "UserDrinks"
DB_USERNAME = "admin"
DB_PASSWORD = "StrongPassword123"

# Initialize session state
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'drink_logs' not in st.session_state:
    st.session_state['drink_logs'] = []
if 'groups' not in st.session_state:
    st.session_state['groups'] = {}
if 'locations' not in st.session_state:
    st.session_state['locations'] = []

# Load the logo image
logo = Image.open("smallpngswamped.png")

# Display logo in sidebar
st.sidebar.image(logo)

# Auth0 functions
def login():
    auth0 = OAuth2Session(AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, scope="openid profile email")
    authorization_url, _ = auth0.create_authorization_url(f"https://{AUTH0_DOMAIN}/authorize", redirect_uri=AUTH0_CALLBACK_URL)
    return authorization_url

def callback():
    code = st.query_params.get("code")
    if code:
        token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
        token_payload = {
            "grant_type": "authorization_code",
            "client_id": AUTH0_CLIENT_ID,
            "client_secret": AUTH0_CLIENT_SECRET,
            "code": code,
            "redirect_uri": AUTH0_CALLBACK_URL
        }
        token_response = requests.post(token_url, json=token_payload)
        if token_response.status_code == 200:
            tokens = token_response.json()
            st.session_state['user'] = tokens
            st.success("Login successful! 🎉")
            st.rerun()
        else:
            st.error("Login failed. Please try again. 😕")
    else:
        st.error("No authorization code received. Please try logging in again. 🔄")

def logout():
    params = {'returnTo': 'http://localhost:8501', 'client_id': AUTH0_CLIENT_ID}
    return f'https://{AUTH0_DOMAIN}/v2/logout?{urlencode(params)}'

# Database functions
def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def insert_user(username):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO Users (username) VALUES (%s)", (username,))
        connection.commit()
    connection.close()

def log_drink(username, drink_type, quantity, timestamp):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id FROM Users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if user:
            user_id = user['user_id']
            cursor.execute(
                "INSERT INTO Drinks (user_id, drink_type, quantity_ml, timestamp) VALUES (%s, %s, %s, %s)",
                (user_id, drink_type, quantity, timestamp)
            )
            connection.commit()
        else:
            st.error("User not found. 😕")
    connection.close()

def get_drink_logs(username):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id FROM Users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if user:
            user_id = user['user_id']
            cursor.execute("SELECT drink_type, quantity_ml, timestamp FROM Drinks WHERE user_id=%s", (user_id,))
            drink_logs = cursor.fetchall()
            connection.close()
            return drink_logs
        else:
            connection.close()
            st.error("User not found. 😕")
            return []

# Main app function
def main_app():
    st.sidebar.title("Navigation 🧭")
    page = st.sidebar.radio("Go to:", [
        "🏠 Home",
        "🍺 Log Drinks",
        "👥 Groups",
        "📊 Dashboard",
        "📍 Location Sharing",
        "➕ Add User"
    ])

    if page == "🏠 Home":
        st.title("Welcome to Swamped 🍹")
        st.write(f"Hello, {st.session_state['user'].get('email', 'User')}! 👋")
        st.write("This app helps you log and track your drink consumption.")
        st.write("Features:")
        st.write("- 📝 Log your drinks and view drink history.")
        st.write("- 👥 Create and join groups to track drinks together.")
        st.write("- 📍 Share your location with group members in real-time.")
        st.write("- 📊 View insightful dashboards and trends.")

    elif page == "🍺 Log Drinks":
        st.title("Log Your Drinks 🍻")
        with st.form("drink_log_form"):
            username = st.text_input("👤 Username:")
            drink_type = st.selectbox("🍷 Select Drink Type:", ["🍺 Beer", "🍷 Wine", "🍸 Cocktail", "🥤 Other"])
            quantity = st.number_input("🔢 Quantity (in mL):", min_value=0.0, step=10.0)
            date = st.date_input("📅 Date:", datetime.date.today())
            time = st.time_input("⏰ Time:", datetime.datetime.now().time())
            timestamp = datetime.datetime.combine(date, time)
            submit = st.form_submit_button("🍻 Log Drink")
            if submit:
                log_drink(username, drink_type, quantity, timestamp)
                st.success("Drink logged successfully! 🎉")

    elif page == "👥 Groups":
        st.title("Manage Groups 👥")
        with st.form("group_form"):
            group_name = st.text_input("Group Name:")
            action = st.radio("Action:", ["Create Group", "Join Group"])
            submit_group = st.form_submit_button("Submit")
            if submit_group:
                if action == "Create Group":
                    if group_name not in st.session_state['groups']:
                        st.session_state['groups'][group_name] = {"members": [], "logs": []}
                        st.success(f"Group '{group_name}' created successfully! 🎉")
                    else:
                        st.error("Group already exists! 😕")
                elif action == "Join Group":
                    if group_name in st.session_state['groups']:
                        st.success(f"Joined group '{group_name}' successfully! 🎉")
                    else:
                        st.error("Group does not exist! 😕")

        st.write("### Your Groups 👥")
        if st.session_state['groups']:
            for group, details in st.session_state['groups'].items():
                st.write(f"- {group} ({len(details['members'])} members)")
        else:
            st.write("You are not part of any groups yet. 😊")

        st.write("### Log Drinks for Group Members 🍻")
        selected_group = st.selectbox("Select Group:", list(st.session_state['groups'].keys()))
        if selected_group:
            with st.form("group_drink_log_form"):
                member_name = st.text_input("👤 Member Name:")
                drink_type = st.selectbox("🍷 Select Drink Type:", ["🍺 Beer", "🍷 Wine", "🍸 Cocktail", "🥤 Other"])
                quantity = st.number_input("🔢 Quantity (in mL):", min_value=0.0, step=10.0)
                date = st.date_input("📅 Date:", datetime.date.today())
                time = st.time_input("⏰ Time:", datetime.datetime.now().time())
                timestamp = datetime.datetime.combine(date, time)
                submit_member_log = st.form_submit_button("Log Drink for Member")
                if submit_member_log:
                    st.session_state['groups'][selected_group]["logs"].append({
                        "member": member_name,
                        "type": drink_type,
                        "quantity": quantity,
                        "timestamp": timestamp
                    })
                    st.success(f"Logged drink for {member_name} in group '{selected_group}' 🎉")

    elif page == "📊 Dashboard":
        st.title("Your Dashboard 📊")
        username = st.text_input("👤 Username:")
        show_data = st.button("📈 Show Data")
        if show_data:
            drink_logs = get_drink_logs(username)
            if drink_logs:
                logs_df = pd.DataFrame(drink_logs)
                logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])
                st.write("### 📜 Your Drink Logs")
                st.dataframe(logs_df)
                total_drinks = logs_df['quantity_ml'].sum()
                st.metric("🍾 Total Drinks Logged", f"{total_drinks} mL")
                daily_summary = logs_df.groupby(logs_df['timestamp'].dt.date)['quantity_ml'].sum().reset_index()
                fig = px.line(daily_summary, x='timestamp', y='quantity_ml', title="🥃 Drinks Over Time")
                st.plotly_chart(fig)
            else:
                st.info("🔍 No drinks logged yet.")

    elif page == "📍 Location Sharing":
        st.title("Location Sharing 📍")
        g = geocoder.ip('me')
        latitude = g.latlng[0] if g.latlng else None
        longitude = g.latlng[1] if g.latlng else None
        if latitude and longitude:
            st.write(f"Your current location: Latitude: {latitude}, Longitude: {longitude}")
            m = folium.Map(location=[latitude, longitude], zoom_start=12)
            folium.Marker([latitude, longitude], popup="Your Location").add_to(m)
            st_folium(m, width=700, height=400)
        else:
            st.write("Unable to get your location. Please try again later. 😕")

        if st.button("📡 Share My Location"):
            if latitude and longitude:
                st.session_state['locations'].append({"latitude": latitude, "longitude": longitude})
                st.success("📡 Location shared with close friends!")
            else:
                st.error("❌ Unable to share location. Try again later.")

        st.markdown("---")
        st.write("### 🗺️ Shared Locations")
        if st.session_state['locations']:
            for loc in st.session_state['locations']:
                st.write(f"Latitude: {loc['latitude']}, Longitude: {loc['longitude']}")
        else:
            st.write("No locations shared yet. 😊")

        with st.sidebar:
            st.header("Need a Ride? 🚗")
            st.write("Click below to book your ride.")
            col1, col2 = st.columns(2)
            with col1:
                st.link_button("Book Uber", "https://www.uber.com")
            with col2:
                st.link_button("Book Lyft", "https://www.lyft.com")

    elif page == "➕ Add User":
        st.title("Add New User ➕")
        with st.form("add_user_form"):
            new_username = st.text_input("Enter New Username:")
            submit_user = st.form_submit_button("Add User")
            if submit_user:
                if new_username:
                    insert_user(new_username)
                    st.success(f"User '{new_username}' added successfully! 🎉")
                else:
                    st.error("Please enter a valid username. 😕")

# Main execution
if 'user' not in st.session_state or st.session_state['user'] is None:
    if "code" in st.query_params:
        callback()
    elif st.button("🔐 Login with Auth0"):
        auth_url = login()
        st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
else:
    main_app()

# Logout button
if st.session_state['user'] is not None:
    if st.sidebar.button("🚪 Logout"):
        logout_url = logout()
        st.session_state['user'] = None
        st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)

# Add CSS for styling
st.markdown(
    """
    <style>
    .css-1v3fvcr {
        background-color: #f9f9f9;
        padding: 10px;
        border-radius: 8px;
    }
    .css-1v3fvcr:hover {
        background-color: #e2e2e2;
    }
    .stButton>button {
        color: #ffffff;
        background-color: #4CAF50;
        border: none;
        border-radius: 4px;
        padding: 10px 24px;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    </style>
    """, unsafe_allow_html=True
)
