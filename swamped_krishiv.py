import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
import geocoder

# Database Configuration
DB_HOST = "userdrinksdb.czs6iaqeqm1d.us-east-1.rds.amazonaws.com"
DB_NAME = "UserDrinks"
DB_USERNAME = "admin"
DB_PASSWORD = "StrongPassword123"

# Connect to the RDS Database
def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

# Function to insert a new user
def insert_user(username):
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO Users (username) VALUES (%s)", (username,))
        connection.commit()
    connection.close()

# Function to log a drink for the user
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
            st.error("User not found.")
    connection.close()

# Function to retrieve the user's drink logs
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
            st.error("User not found.")
            return []

# Initialize session state
if 'locations' not in st.session_state:
    st.session_state['locations'] = []

# Sidebar for Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Home", "Log Drinks", "Groups", "Dashboard", "Location Sharing", "Add User"])

# Home Page
if page == "Home":
    st.title("Welcome to Swamped")
    st.write("This app helps you log and track your drink consumption.")
    st.write("Features:")
    st.write("- Log your drinks and view drink history.")
    st.write("- Create and join groups to track drinks together.")
    st.write("- Share your location with group members in real-time.")
    st.write("- View insightful dashboards and trends.")

# Log Drinks Page
elif page == "Log Drinks":
    st.title("Log Your Drinks")

    with st.form("drink_log_form"):
        username = st.text_input("Username:")
        drink_type = st.selectbox("Select Drink Type:", ["Beer", "Wine", "Cocktail", "Other"])
        quantity = st.number_input("Quantity (in mL):", min_value=0.0, step=10.0)
        date = st.date_input("Date:", datetime.today())
        time = st.time_input("Time:", datetime.now().time())
        timestamp = datetime.combine(date, time)
        submit = st.form_submit_button("Log Drink")

        if submit:
            log_drink(username, drink_type, quantity, timestamp)
            st.success("Drink logged successfully!")

# Groups Page
elif page == "Groups":
    st.title("Manage Groups")

    # Create or Join a Group
    with st.form("group_form"):
        group_name = st.text_input("Group Name:")
        action = st.radio("Action:", ["Create Group", "Join Group"])
        submit_group = st.form_submit_button("Submit")

        if submit_group:
            if action == "Create Group":
                # Implement group creation logic here
                st.success(f"Group '{group_name}' created successfully!")
            elif action == "Join Group":
                # Implement group joining logic here
                st.success(f"Joined group '{group_name}' successfully!")

    st.write("### Your Groups")
    # Implement group listing logic here

    # Log Drinks for Group Members
    st.write("### Log Drinks for Group Members")
    selected_group = st.selectbox("Select Group:", ["Group 1", "Group 2"])  # Replace with actual group names
    if selected_group:
        with st.form("group_drink_log_form"):
            member_name = st.text_input("Member Name:")
            drink_type = st.selectbox("Select Drink Type:", ["Beer", "Wine", "Cocktail", "Other"])
            quantity = st.number_input("Quantity (in mL):", min_value=0.0, step=10.0)
            date = st.date_input("Date:", datetime.today())
            time = st.time_input("Time:", datetime.now().time())
            timestamp = datetime.combine(date, time)
            submit_member_log = st.form_submit_button("Log Drink for Member")

            if submit_member_log:
                # Implement group member drink logging logic here
                st.success(f"Logged drink for {member_name} in group '{selected_group}'")

# Dashboard Page
elif page == "Dashboard":
    st.title("Your Dashboard")

    username = st.text_input("Username:")
    show_data = st.button("Show Data")

    if show_data:
        drink_logs = get_drink_logs(username)

        if drink_logs:
            logs_df = pd.DataFrame(drink_logs)
            logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])

            st.write("### Your Drink Logs")
            st.dataframe(logs_df)

            # Summary Stats
            total_drinks = logs_df['quantity_ml'].sum()
            st.write(f"### Total Drinks Logged: {total_drinks} mL")

            # Drinks Over Time
            daily_summary = logs_df.groupby(logs_df['timestamp'].dt.date)['quantity_ml'].sum().reset_index()
            fig = px.line(daily_summary, x='timestamp', y='quantity_ml', title="Drinks Over Time")
            st.plotly_chart(fig)
        else:
            st.write("No drinks logged yet.")

# Location Sharing Page
elif page == "Location Sharing":
    st.title("Location Sharing")

    g = geocoder.ip('me')
    latitude = g.latlng[0] if g.latlng else None
    longitude = g.latlng[1] if g.latlng else None

    if latitude and longitude:
        st.write(f"Your current location: Latitude: {latitude}, Longitude: {longitude}")

        m = folium.Map(location=[latitude, longitude], zoom_start=12)
        folium.Marker([latitude, longitude], popup="Your Location").add_to(m)
        st_folium(m, width=700, height=400)
    else:
        st.write("Unable to get your location. Please try again later.")

    if st.button("Share My Location"):
        if latitude and longitude:
            st.session_state['locations'].append({"latitude": latitude, "longitude": longitude})
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

    with st.sidebar:
        st.header("Need a Ride?")
        st.write("Click below to book your ride.")

        col1, col2 = st.columns(2)
        with col1:
            st.link_button("Book Uber", "https://www.uber.com", type="primary")
        with col2:
            st.link_button("Book Lyft", "https://www.lyft.com", type="primary")

# Add User Page
elif page == "Add User":
    st.title("Add New User")

    with st.form("add_user_form"):
        new_username = st.text_input("Enter New Username:")
        submit_user = st.form_submit_button("Add User")

        if submit_user:
            if new_username:
                insert_user(new_username)
                st.success(f"User '{new_username}' added successfully!")
            else:
                st.error("Please enter a valid username.")

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
    """, unsafe_allow_html=True
)
