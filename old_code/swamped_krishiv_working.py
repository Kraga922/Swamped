mport streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import folium
from streamlit_folium import st_folium
from authlib.integrations.requests_client import OAuth2Session
import requests
from dotenv import load_dotenv
import os
from urllib.parse import urlencode
import geocoder
import pymysql

# Load environment variables
load_dotenv()

# Auth0 configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
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

# Auth0 functions
def login():
    auth0 = OAuth2Session(
        AUTH0_CLIENT_ID,
        AUTH0_CLIENT_SECRET,
        scope="openid profile email"
    )
    authorization_url, _ = auth0.create_authorization_url(
        f"https://{AUTH0_DOMAIN}/authorize",
        redirect_uri=AUTH0_CALLBACK_URL
    )
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
    params = {
        'returnTo': 'http://localhost:8501',
        'client_id': AUTH0_CLIENT_ID
    }
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
    st.markdown(
        """
        <style>
        .big-button {
            font-size: 24px !important;
            height: 75px !important;
            width: 100% !important;
            margin-bottom: 20px !important;
            border-radius: 15px !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        }
        .stButton>button {
            width: 100%;
        }
        .stSelectbox>div>div>select {
            font-size: 20px !important;
            height: 60px !important;
        }
        .stTextInput>div>div>input {
            font-size: 20px !important;
            height: 60px !important;
        }
        .stNumberInput>div>div>input {
            font-size: 20px !important;
            height: 60px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("Swamped 🍹")

    menu = ["Home", "Log Drinks", "Groups", "Dashboard", "Location"]
    choice = st.selectbox("Menu", menu, key="menu_select")

    if choice == "Home":
        st.header("Welcome to Swamped! 👋")
        st.write(f"Hello, {st.session_state['user'].get('email', 'User')}!")
        st.write("Track your drinks and stay safe with friends.")

    elif choice == "Log Drinks":
        st.header("Log Your Drinks 🍻")
        username = st.text_input("Username", key="username_input")
        drink_type = st.selectbox("Drink Type", ["🍺 Beer", "🍷 Wine", "🍸 Cocktail", "🥤 Other"], key="drink_type_select")
        quantity = st.number_input("Quantity (mL)", min_value=0.0, step=10.0, key="quantity_input")
        if st.button("Log Drink", key="log_drink_button", use_container_width=True):
            log_drink(username, drink_type, quantity, datetime.datetime.now())
            st.success("Drink logged successfully! 🎉")

    elif choice == "Groups":
        st.header("Manage Groups 👥")
        group_name = st.text_input("Group Name", key="group_name_input")
        action = st.radio("Action", ["Create Group", "Join Group"], key="group_action_radio")
        if st.button("Submit", key="group_submit_button", use_container_width=True):
            if action == "Create Group":
                if group_name not in st.session_state['groups']:
                    st.session_state['groups'][group_name] = []
                    st.success(f"Group '{group_name}' created successfully! 🎉")
                else:
                    st.error("Group already exists! 😕")
            elif action == "Join Group":
                if group_name in st.session_state['groups']:
                    st.success(f"Joined group '{group_name}' successfully! 🎉")
                else:
                    st.error("Group does not exist! 😕")

    elif choice == "Dashboard":
        st.header("Your Dashboard 📊")
        username = st.text_input("Username", key="dashboard_username_input")
        if st.button("Show Data", key="show_data_button", use_container_width=True):
            drink_logs = get_drink_logs(username)
            if drink_logs:
                logs_df = pd.DataFrame(drink_logs)
                logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])
                st.write("### Your Drink Logs")
                st.dataframe(logs_df)
                total_drinks = logs_df['quantity_ml'].sum()
                st.metric("Total Drinks Logged", f"{total_drinks} mL")
                daily_summary = logs_df.groupby(logs_df['timestamp'].dt.date)['quantity_ml'].sum().reset_index()
                fig = px.line(daily_summary, x='timestamp', y='quantity_ml', title="Drinks Over Time")
                st.plotly_chart(fig)
            else:
                st.info("No drinks logged yet.")

    elif choice == "Location":
        st.header("Location Sharing 📍")
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
        if st.button("Share My Location", key="share_location_button", use_container_width=True):
            if latitude and longitude:
                st.session_state['locations'].append({"latitude": latitude, "longitude": longitude})
                st.success("Location shared with close friends!")
            else:
                st.error("Unable to share location. Try again later.")

    st.markdown("---")
    if st.button("Need a Ride? 🚗", key="ride_button", use_container_width=True):
        st.markdown("[Book Uber](https://www.uber.com)")
        st.markdown("[Book Lyft](https://www.lyft.com)")

# Main execution
if 'user' not in st.session_state or st.session_state['user'] is None:
    if "code" in st.query_params:
        callback()
    elif st.button("Login with Auth0", key="login_button", use_container_width=True):
        auth_url = login()
        st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
else:
    main_app()

# Logout button
if st.session_state['user'] is not None:
    if st.sidebar.button("Logout", key="logout_button", use_container_width=True):
        logout_url = logout()
        st.session_state['user'] = None
        st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
