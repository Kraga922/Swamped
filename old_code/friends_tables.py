import pymysql

# RDS configuration
DB_HOST = "userdrinksdb.czs6iaqeqm1d.us-east-1.rds.amazonaws.com"  # Replace with your RDS endpoint
DB_PORT = 3306
DB_USERNAME = "admin"
DB_PASSWORD = "StrongPassword123"  # Replace with your DB password
DB_NAME = "UserDrinks"


# Function to create the users table
def create_users_table():
    connection = None
    try:
        # Connect to the RDS instance
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )

        with connection.cursor() as cursor:
            # SQL to create the users table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL
            );
            """
            cursor.execute(create_table_query)
            print("Users table created successfully!")

        # Commit the transaction
        connection.commit()
    except Exception as e:
        print(f"Error creating users table: {e}")
    finally:
        if connection:
            connection.close()


# Function to create the friends table
def create_friends_table():
    connection = None
    try:
        # Connect to the RDS instance
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )

        with connection.cursor() as cursor:
            # SQL to create the friends table with foreign key references
            create_table_query = """
            CREATE TABLE IF NOT EXISTS friends (
                user_id INT NOT NULL,
                friend_id INT NOT NULL,
                PRIMARY KEY (user_id, friend_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (friend_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_table_query)
            print("Friends table created successfully!")

        # Commit the transaction
        connection.commit()
    except Exception as e:
        print(f"Error creating friends table: {e}")
    finally:
        if connection:
            connection.close()


# Create both tables
create_users_table()
create_friends_table()
