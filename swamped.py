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

# Set page config
st.set_page_config(
    page_title="🍹 Swamped - Drink Tracker",
    page_icon="🍹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #f0f8ff;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        padding: 10px 20px;
    }
    .stTextInput>div>div>input {
        background-color: #e6f3ff;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stAlert {
        background-color: #ffebee;
        color: #b71c1c;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

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
            st.success("🎉 Login successful!")
            st.rerun()
        else:
            st.error("❌ Login failed. Please try again.")
    else:
        st.error("❌ No authorization code received. Please try logging in again.")

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

def update_user_weight(username, weight):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("UPDATE Users SET weight=%s WHERE username=%s", (weight, username))
        connection.commit()
    connection.close()

def get_user_weight(username):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT weight FROM Users WHERE username=%s", (username,))
        user = cursor.fetchone()
        connection.close()
        if user:
            return user['weight']
        else:
            return None

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
            st.error("❌ User not found.")
    connection.close()

# BAL Calculation Function (simplified)
def calculate_BAL(username, weight):
    if weight is None or weight <= 0:
        return None

    drink_logs = get_drink_logs(username)
    total_alcohol = 0

    for log in drink_logs:
        quantity_ml = log['quantity_ml']
        drink_type = log['drink_type']

        alcohol_content = {
            "Beer": 0.05,
            "Wine": 0.12,
            "Cocktail": 0.40,
            "Other": 0.15
        }

        alcohol_in_drink = quantity_ml * alcohol_content.get(drink_type, 0.15) * 0.789
        total_alcohol += alcohol_in_drink

    r = 0.68  # for males, use 0.55 for females
    BAL = (total_alcohol / (weight * 1000 * r)) * 100
    return BAL

def add_friend(friend_username):
    if 'logged_in_user' not in st.session_state:
        st.error("❌ You must log in to add friends.")
        return

    user_username = st.session_state['logged_in_user']

    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id FROM Users WHERE username=%s", (user_username,))
        user = cursor.fetchone()

        cursor.execute("SELECT user_id FROM Users WHERE username=%s", (friend_username,))
        friend = cursor.fetchone()

        if user and friend:
            user_id = user['user_id']
            friend_id = friend['user_id']

            cursor.execute(
                "SELECT * FROM Friends WHERE user_id=%s AND friend_id=%s", (user_id, friend_id)
            )
            existing_friendship = cursor.fetchone()

            if not existing_friendship:
                cursor.execute(
                    "INSERT INTO Friends (user_id, friend_id) VALUES (%s, %s)",
                    (user_id, friend_id)
                )
                connection.commit()
                st.success(f"🎉 Friend '{friend_username}' added!")
            else:
                st.warning(f"ℹ️ '{friend_username}' is already your friend.")
        else:
            if not friend:
                st.error(f"❌ User '{friend_username}' not found.")
    connection.close()

def get_friends(username):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id FROM Users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user:
            user_id = user['user_id']
            cursor.execute("SELECT f.friend_id, u.username FROM Friends f JOIN Users u ON f.friend_id = u.user_id WHERE f.user_id=%s", (user_id,))
            friends = cursor.fetchall()
            connection.close()
            return [friend['username'] for friend in friends]
        else:
            connection.close()
            return []

def get_drink_logs(username):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id FROM Users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if user:
                user_id = user['user_id']
                cursor.execute("SELECT drink_type, quantity_ml, timestamp FROM Drinks WHERE user_id=%s", (user_id,))
                drink_logs = cursor.fetchall()
                return drink_logs
            else:
                st.error("❌ User not found.")
                return []
    except Exception as e:
        st.error(f"❌ Database error: {str(e)}")
        return []
    finally:
        connection.close()

def login_user(username):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if user:
            st.session_state['logged_in_user'] = user['username']
            st.success(f"🎉 Logged in as {user['username']}")
        else:
            st.error("❌ User not found. Please register first.")
    connection.close()

def main_app():
    st.sidebar.title("🧭 Navigation")
    page = st.sidebar.radio("Go to:", ["🏠 Home", "🍺 Log Drinks", "👥 Groups", "📊 Dashboard", "📍 Location Sharing", "➕ Add User", "🔑 Login"])

    if page == "🏠 Home":
        st.title("🍹 Welcome to Swamped")
        st.write(f"Hello, {st.session_state['user'].get('email', 'User')}! 👋")
        st.write("This app helps you log and track your drink consumption.")
        st.write("Features:")
        st.write("- 📝 Log your drinks and view drink history.")
        st.write("- 👥 Create and join groups to track drinks together.")
        st.write("- 📍 Share your location with group members in real-time.")
        st.write("- 📊 View insightful dashboards and trends.")

    elif page == "🍺 Log Drinks":
        st.title("🍺 Log Your Drinks")

        with st.form("drink_log_form"):
            username = st.text_input("Username:")
            drink_type = st.selectbox("Select Drink Type:", ["🍺 Beer", "🍷 Wine", "🍸 Cocktail", "🥃 Other"])
            quantity = st.number_input("Quantity (in mL):", min_value=0.0, step=10.0)
            date = st.date_input("Date:", datetime.date.today())
            time = st.time_input("Time:", datetime.datetime.now().time())
            timestamp = datetime.datetime.combine(date, time)
            submit = st.form_submit_button("🍻 Log Drink")

            if submit:
                log_drink(username, drink_type, quantity, timestamp)
                st.success("🎉 Drink logged successfully!")

    elif page == "👥 Groups":
        st.title("👥 Manage Groups")

        with st.form("group_form"):
            group_name = st.text_input("Group Name:")
            action = st.radio("Action:", ["🆕 Create Group", "🤝 Join Group"])
            submit_group = st.form_submit_button("Submit")

            if submit_group:
                if action == "🆕 Create Group":
                    if group_name not in st.session_state['groups']:
                        st.session_state['groups'][group_name] = {"members": [], "logs": []}
                        st.success(f"🎉 Group '{group_name}' created successfully!")
                    else:
                        st.error("❌ Group already exists!")
                elif action == "🤝 Join Group":
                    if group_name in st.session_state['groups']:
                        st.success(f"🎉 Joined group '{group_name}' successfully!")
                    else:
                        st.error("❌ Group does not exist!")

        st.write("### 👥 Your Groups")
        if st.session_state['groups']:
            for group, details in st.session_state['groups'].items():
                st.write(f"- {group} ({len(details['members'])} members)")
        else:
            st.write("You are not part of any groups yet.")

        st.write("### 👥 Manage Group Members and Drinks")
        selected_group = st.selectbox("Select Group:", list(st.session_state['groups'].keys()))

        if selected_group:
            with st.form("add_member_form"):
                new_member = st.text_input("Member Name:")
                submit_add_member = st.form_submit_button("➕ Add Member")

                if submit_add_member:
                    if new_member:
                        if new_member not in st.session_state['groups'][selected_group]["members"]:
                            st.session_state['groups'][selected_group]["members"].append(new_member)
                            st.success(f"🎉 Added {new_member} to group '{selected_group}'")
                        else:
                            st.error(f"❌ {new_member} is already in the group!")
                    else:
                        st.error("❌ Member name cannot be empty!")

            st.write(f"### 👥 Members of '{selected_group}'")
            current_members = st.session_state['groups'][selected_group]["members"]
            if current_members:
                for member in current_members:
                    st.write(f"- {member}")
            else:
                st.write("No members in this group.")

            st.write("### 🍺 Log Drinks for Group Members")
            with st.form("group_drink_log_form"):
                member_name = st.selectbox("Select Member:", current_members)
                drink_type = st.selectbox("Select Drink Type:", ["🍺 Beer", "🍷 Wine", "🍸 Cocktail", "🥃 Other"])
                quantity = st.number_input("Quantity (in mL):", min_value=0.0, step=10.0)
                date = st.date_input("Date:", datetime.date.today())
                time = st.time_input("Time:", datetime.datetime.now().time())
                timestamp = datetime.datetime.combine(date, time)
                submit_member_log = st.form_submit_button("🍻 Log Drink")

                if submit_member_log:
                    if member_name:
                        log_drink(member_name, drink_type, quantity, timestamp)
                        st.success(
                            f"🎉 Logged {quantity} mL of {drink_type} for {member_name} in group '{selected_group}'")
                    else:
                        st.error("❌ Please select a member to log the drink for.")

            elif page == "📊 Dashboard":
            st.title("📊 Your Dashboard")

            username = st.text_input("Username:")
            weight = st.number_input("Weight (in kg):", min_value=0.0, step=1.0)
            show_data = st.button("📊 Show Data")

            if show_data:
                drink_logs = get_drink_logs(username)
                if drink_logs:
                    logs_df = pd.DataFrame(drink_logs)
                    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])

                    st.write("### 📜 Your Drink Logs")
                    st.dataframe(logs_df)

                    total_drinks = logs_df['quantity_ml'].sum()
                    st.write(f"### 🍺 Total Drinks Logged: {total_drinks} mL")

                    BAL = calculate_BAL(username, weight)
                    if BAL is not None:
                        st.write(f"### 🩸 Estimated Blood Alcohol Level: {BAL:.3f}%")

                        if BAL >= 0.08:
                            st.error(
                                "🚨 DANGER: Your estimated BAL is dangerously high. Please stop drinking immediately.")
                            st.warning(
                                "⚠️ You should not be operating this app. Please seek help or call a trusted friend or family member for assistance.")
                            st.info(
                                "ℹ️ If you're feeling unwell or experiencing any concerning symptoms, don't hesitate to call emergency services.")
                        elif BAL >= 0.05:
                            st.warning(
                                "🚧 CAUTION: Your BAL is approaching unsafe levels. It's time to slow down or stop drinking.")
                            st.info(
                                "ℹ️ Consider eating some food and drinking water to help metabolize the alcohol. Stay safe and avoid any risky activities.")
                        elif BAL >= 0.03:
                            st.info("💧 REMINDER: Remember to stay hydrated. Alternate alcoholic drinks with water.")
                            st.info(
                                "🍽️ Eating a snack can help slow alcohol absorption. Be mindful of your consumption and stay safe.")

                        # Display BAL chart
                        daily_summary = logs_df.groupby(logs_df['timestamp'].dt.date)['quantity_ml'].sum().reset_index()
                        fig = px.line(daily_summary, x='timestamp', y='quantity_ml', title="🍺 Drinks Over Time")
                        st.plotly_chart(fig)

                        # Provide general safety tips
                        st.subheader("🛡️ Safety Tips")
                        st.markdown("""
                                    - 🐢 Pace yourself and sip slowly
                                    - 🥤 Use drink "spacers" — non-alcoholic drinks between alcoholic ones
                                    - 🍺 Choose drinks with lower alcohol content
                                    - 🍽️ Eat before or while drinking to slow alcohol absorption
                                    - 🚫 Be ready to say "no thanks" if offered a drink when you don't want one
                                    - 🚗 Never drink and drive - always have a designated driver or use a ride-sharing service
                                    """)
                    else:
                        st.error("❌ Unable to calculate BAL. Please check your weight input.")
                else:
                    st.write("No drinks logged yet.")

        elif page == "📍 Location Sharing":
            st.title("📍 Location Sharing")

            g = geocoder.ip('me')
            latitude = g.latlng[0] if g.latlng else None
            longitude = g.latlng[1] if g.latlng else None

            if latitude and longitude:
                st.write(f"📌 Your current location: Latitude: {latitude}, Longitude: {longitude}")

                m = folium.Map(location=[latitude, longitude], zoom_start=12)
                folium.Marker([latitude, longitude], popup="Your Location").add_to(m)
                st_folium(m, width=700, height=400)
            else:
                st.write("❌ Unable to get your location. Please try again later.")

            if st.button("📡 Share My Location"):
                if latitude and longitude:
                    st.session_state['locations'].append({"latitude": latitude, "longitude": longitude})
                    st.success("🎉 Location shared with close friends!")
                else:
                    st.error("❌ Unable to share location. Try again later.")

            st.markdown("---")

            st.write("### 🗺️ Shared Locations")
            if st.session_state['locations']:
                for loc in st.session_state['locations']:
                    st.write(f"📍 Latitude: {loc['latitude']}, Longitude: {loc['longitude']}")
            else:
                st.write("No locations shared yet.")

            with st.sidebar:
                st.header("🚗 Need a Ride?")
                st.write("Click below to book your ride.")

                col1, col2 = st.columns(2)
                with col1:
                    st.link_button("🚕 Book Uber", "https://www.uber.com", type="primary")
                with col2:
                    st.link_button("🚖 Book Lyft", "https://www.lyft.com", type="primary")

        elif page == "➕ Add User":
            st.title("➕ Add New User")

            with st.form("add_user_form"):
                new_username = st.text_input("Enter New Username:")
                submit_user = st.form_submit_button("➕ Add User")

                if submit_user:
                    if new_username:
                        insert_user(new_username)
                        st.success(f"🎉 User '{new_username}' added successfully!")
                    else:
                        st.error("❌ Please enter a valid username.")

        elif page == "🔑 Login":
            st.header("🔑 Login")
            username = st.text_input("Username")
            if st.button("🔐 Login"):
                if username:
                    login_user(username)
                else:
                    st.warning("⚠️ Please enter a username.")

        # Main execution
        if 'user' not in st.session_state or st.session_state['user'] is None:
            if "code" in st.query_params:
                callback()
            elif st.button("🔑 Login with Auth0"):
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
                background-color: #f0f8ff;
                padding: 15px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .css-1v3fvcr:hover {
                background-color: #e6f3ff;
                transition: background-color 0.3s ease;
            }
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 10px 20px;
                transition: background-color 0.3s ease;
            }
            .stButton>button:hover {
                background-color: #45a049;
            }
            </style>
            """, unsafe_allow_html=True
        )

