import streamlit as st
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

# Load environment variables
load_dotenv()

# Auth0 configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_CALLBACK_URL = "http://localhost:8501/"

# Initialize session state
if 'user' not in st.session_state:
    st.session_state['user'] = None

if 'drink_logs' not in st.session_state:
    st.session_state['drink_logs'] = []

if 'groups' not in st.session_state:
    st.session_state['groups'] = {}

if 'locations' not in st.session_state:
    st.session_state['locations'] = []

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
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Login failed. Please try again.")
    else:
        st.error("No authorization code received. Please try logging in again.")

def logout():
    params = {
        'returnTo': 'http://localhost:8501',
        'client_id': AUTH0_CLIENT_ID
    }
    return f'https://{AUTH0_DOMAIN}/v2/logout?{urlencode(params)}'

def main_app():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to:", ["Home", "Log Drinks", "Groups", "Dashboard", "Location Sharing"])

    if page == "Home":
        st.title("Welcome to the Drink Tracker App")
        st.write(f"Hello, {st.session_state['user'].get('email', 'User')}!")
        st.write("This app helps you log your drinks, share locations, and manage groups to keep track of drinking habits.")
        st.write("Features:")
        st.write("- Log your drinks and view drink history.")
        st.write("- Create and join groups to track drinks together.")
        st.write("- Share your location with group members in real-time.")
        st.write("- View insightful dashboards and trends.")

    elif page == "Log Drinks":
        st.title("Log Your Drinks")

        with st.form("drink_log_form"):
            drink_type = st.selectbox("Select Drink Type:", ["Beer", "Wine", "Cocktail", "Other"])
            quantity = st.number_input("Quantity (in standard drinks):", min_value=0.0, step=0.1)
            timestamp = st.date_input("Date:", datetime.date.today())
            submit = st.form_submit_button("Log Drink")

            if submit:
                st.session_state['drink_logs'].append({
                    "type": drink_type,
                    "quantity": quantity,
                    "timestamp": timestamp
                })
                st.success("Drink logged successfully!")

        st.write("### Your Drink Logs")
        if st.session_state['drink_logs']:
            logs_df = pd.DataFrame(st.session_state['drink_logs'])
            st.dataframe(logs_df)
        else:
            st.write("No drinks logged yet.")

    elif page == "Groups":
        st.title("Manage Groups")

        with st.form("group_form"):
            group_name = st.text_input("Group Name:")
            action = st.radio("Action:", ["Create Group", "Join Group"])
            submit_group = st.form_submit_button("Submit")

            if submit_group:
                if action == "Create Group":
                    if group_name not in st.session_state['groups']:
                        st.session_state['groups'][group_name] = []
                        st.success(f"Group '{group_name}' created successfully!")
                    else:
                        st.error("Group already exists!")
                elif action == "Join Group":
                    if group_name in st.session_state['groups']:
                        st.success(f"Joined group '{group_name}' successfully!")
                    else:
                        st.error("Group does not exist!")

        st.write("### Your Groups")
        if st.session_state['groups']:
            for group, members in st.session_state['groups'].items():
                st.write(f"- {group}")
        else:
            st.write("You are not part of any groups yet.")

        st.write("### Log Drinks for Group Members")
        selected_group = st.selectbox("Select Group:", list(st.session_state['groups'].keys()))
        if selected_group:
            with st.form("group_drink_log_form"):
                member_name = st.text_input("Member Name:")
                drink_type = st.selectbox("Select Drink Type:", ["Beer", "Wine", "Cocktail", "Other"])
                quantity = st.number_input("Quantity (in standard drinks):", min_value=0.0, step=0.1)
                timestamp = st.date_input("Date:", datetime.date.today())
                submit_member_log = st.form_submit_button("Log Drink for Member")

                if submit_member_log:
                    st.session_state['groups'][selected_group].append({
                        "member": member_name,
                        "type": drink_type,
                        "quantity": quantity,
                        "timestamp": timestamp
                    })
                    st.success(f"Logged drink for {member_name} in group '{selected_group}'")

    elif page == "Dashboard":
        st.title("Your Dashboard")

        if st.session_state['drink_logs']:
            logs_df = pd.DataFrame(st.session_state['drink_logs'])

            total_drinks = logs_df['quantity'].sum()
            st.write(f"### Total Drinks Logged: {total_drinks}")

            logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])
            daily_summary = logs_df.groupby('timestamp')['quantity'].sum().reset_index()
            fig = px.line(daily_summary, x='timestamp', y='quantity', title="Drinks Over Time")
            st.plotly_chart(fig)
        else:
            st.write("No drink logs available to display.")

    elif page == "Location Sharing":
        st.title("Location Sharing")

        # Get the user's current location using geocoder
        g = geocoder.ip('me')
        latitude = g.latlng[0] if g.latlng else None
        longitude = g.latlng[1] if g.latlng else None

        if latitude and longitude:
            st.write(f"Your current location: Latitude: {latitude}, Longitude: {longitude}")

            # Create a smaller folium map centered at the user's current location
            m = folium.Map(location=[latitude, longitude], zoom_start=12)
            folium.Marker([latitude, longitude], popup="Your Location").add_to(m)
            st_folium(m, width=700, height=400)
        else:
            st.write("Unable to get your location. Please try again later.")

        # Share Location Button
        if st.button("Share My Location"):
            if latitude and longitude:
                st.session_state['locations'].append({
                    "latitude": latitude,
                    "longitude": longitude
                })
                st.success("Location shared with close friends!")
            else:
                st.error("Unable to share location. Try again later.")

        st.markdown("---")

        st.write("### Shared Locations")
        if st.session_state['locations']:
            for loc in st.session_state['locations']:
                st.write(f"Latitude: {loc['latitude']}, Longitude: {loc['longitude']}")
        else:
            st.write("No locations shared yet.")

        # Sidebar for Uber and Lyft
        with st.sidebar:
            st.header("Need a Ride?")
            st.write("Click below to book your ride.")

            col1, col2 = st.columns(2)
            with col1:
                st.link_button("Book Uber", "https://www.uber.com", type="primary")
            with col2:
                st.link_button("Book Lyft", "https://www.lyft.com", type="primary")

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
                </style>
                """, unsafe_allow_html=True)

# Main execution
if 'user' not in st.session_state or st.session_state['user'] is None:
    if "code" in st.query_params:
        callback()
    elif st.button("Login with Auth0"):
        auth_url = login()
        st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
else:
    main_app()

# Logout button
if st.session_state['user'] is not None:
    if st.sidebar.button("Logout"):
        logout_url = logout()
        st.session_state['user'] = None
        st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
