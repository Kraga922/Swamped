import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import folium
from streamlit_folium import st_folium

# Initialize session state for storing data
if 'drink_logs' not in st.session_state:
    st.session_state['drink_logs'] = []

if 'groups' not in st.session_state:
    st.session_state['groups'] = {}

if 'locations' not in st.session_state:
    st.session_state['locations'] = []

# Sidebar for Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Home", "Log Drinks", "Groups", "Dashboard", "Location Sharing"])

# Home Page
if page == "Home":
    st.title("Welcome to the Drink Tracker App")
    st.write("This app helps you log your drinks, share locations, and manage groups to keep track of drinking habits.")
    st.write("Features:")
    st.write("- Log your drinks and view drink history.")
    st.write("- Create and join groups to track drinks together.")
    st.write("- Share your location with group members in real-time.")
    st.write("- View insightful dashboards and trends.")

# Log Drinks Page
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

    # Log Drinks for Group Members
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

# Dashboard Page
elif page == "Dashboard":
    st.title("Your Dashboard")

    if st.session_state['drink_logs']:
        logs_df = pd.DataFrame(st.session_state['drink_logs'])

        # Summary Stats
        total_drinks = logs_df['quantity'].sum()
        st.write(f"### Total Drinks Logged: {total_drinks}")

        # Drinks Over Time
        logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])
        daily_summary = logs_df.groupby('timestamp')['quantity'].sum().reset_index()
        fig = px.line(daily_summary, x='timestamp', y='quantity', title="Drinks Over Time")
        st.plotly_chart(fig)
    else:
        st.write("No drink logs available to display.")

# Location Sharing Page
elif page == "Location Sharing":
    st.title("Location Sharing")

    with st.form("location_form"):
        latitude = st.number_input("Enter Latitude:", format="%.6f")
        longitude = st.number_input("Enter Longitude:", format="%.6f")
        submit_location = st.form_submit_button("Share Location")

        if submit_location:
            st.session_state['locations'].append({
                "latitude": latitude,
                "longitude": longitude
            })
            st.success("Location shared successfully!")

    st.write("### Shared Locations")
    if st.session_state['locations']:
        m = folium.Map(location=[0, 0], zoom_start=2)
        for loc in st.session_state['locations']:
            folium.Marker([loc['latitude'], loc['longitude']]).add_to(m)
        st_folium(m, width=700, height=500)
    else:
        st.write("No locations shared yet.")
