import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime

# Database Configuration
DB_HOST = "userdrinksdb.czs6iaqeqm1d.us-east-1.rds.amazonaws.com"  # Replace with your RDS endpoint
DB_NAME = "UserDrinks"
DB_USERNAME = "admin"
DB_PASSWORD = "StrongPassword123"  # Replace with your password

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
        cursor.execute("""
            INSERT INTO Users (username) 
            VALUES (%s)
        """, (username,))
        connection.commit()
    connection.close()

# Function to log a drink for the user
def log_drink(username, drink_type, quantity, timestamp):
    connection = get_connection()
    with connection.cursor() as cursor:
        # Check if user exists
        cursor.execute("SELECT user_id FROM Users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user:
            user_id = user['user_id']
            cursor.execute("""
                INSERT INTO Drinks (user_id, drink_type, quantity_ml, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (user_id, drink_type, quantity, timestamp))
            connection.commit()
        else:
            st.error("User not found.")
    connection.close()

# Function to retrieve the user's drink logs
def get_drink_logs(username):
    connection = get_connection()
    with connection.cursor() as cursor:
        # Fetch user ID
        cursor.execute("SELECT user_id FROM Users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user:
            user_id = user['user_id']
            # Fetch drink logs for the user
            cursor.execute("SELECT drink_type, quantity_ml, timestamp FROM Drinks WHERE user_id=%s", (user_id,))
            drink_logs = cursor.fetchall()
            connection.close()
            return drink_logs
        else:
            connection.close()
            st.error("User not found.")
            return []

# Sidebar for Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Home", "Log Drinks", "Dashboard", "Add User"])

# Home Page
if page == "Home":
    st.title("Welcome to Swamped")
    st.write("This app helps you log and track your drink consumption.")

# Log Drinks Page
elif page == "Log Drinks":
    st.title("Log Your Drinks")

    # Form to log drinks
    with st.form("drink_log_form"):
        username = st.text_input("Username:")
        drink_type = st.selectbox("Select Drink Type:", ["Beer", "Wine", "Cocktail", "Other"])
        quantity = st.number_input("Quantity (in mL):", min_value=0.0, step=10.0)
        timestamp = st.date_input("Date:", datetime.today())
        submit = st.form_submit_button("Log Drink")

        if submit:
            # Save drink log in the database
            log_drink(username, drink_type, quantity, timestamp)
            st.success("Drink logged successfully!")

# Dashboard Page
elif page == "Dashboard":
    st.title("Your Dashboard")

    username = st.text_input("Username:")
    show_data = st.button("Show Data")

    if show_data:
        # Fetch user drink logs from the database
        drink_logs = get_drink_logs(username)

        if drink_logs:
            logs_df = pd.DataFrame(drink_logs)
            st.write("### Your Drink Logs")
            st.dataframe(logs_df)

            # Plot drinks over time
            logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])
            daily_summary = logs_df.groupby('timestamp')['quantity_ml'].sum().reset_index()
            st.line_chart(daily_summary.set_index('timestamp')['quantity_ml'])
        else:
            st.write("No drinks logged yet.")

# Add User Page
elif page == "Add User":
    st.title("Add New User")

    # Form to add a new user
    with st.form("add_user_form"):
        new_username = st.text_input("Enter New Username:")
        submit_user = st.form_submit_button("Add User")

        if submit_user:
            # Add the new user to the database
            if new_username:
                insert_user(new_username)
                st.success(f"User '{new_username}' added successfully!")
            else:
                st.error("Please enter a valid username.")
