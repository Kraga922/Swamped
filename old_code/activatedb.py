import boto3
from botocore.exceptions import ClientError

# Initialize RDS client
rds_client = boto3.client('rds', region_name='us-east-1')  # Replace with your AWS region

# Database configuration
DB_INSTANCE_IDENTIFIER = "UserDrinksDB"
DB_NAME = "UserDrinks"
DB_USERNAME = "admin"
DB_PASSWORD = "StrongPassword123"  # Replace with a strong password
DB_ENGINE = "mysql"  # or "postgres" if you prefer PostgreSQL

# Create RDS instance
def create_rds_instance():
    try:
        response = rds_client.create_db_instance(
            DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER,
            AllocatedStorage=20,  # 20 GB
            DBInstanceClass='db.t3.micro',  # Free tier eligible instance type
            Engine=DB_ENGINE,
            MasterUsername=DB_USERNAME,
            MasterUserPassword=DB_PASSWORD,
            DBName=DB_NAME,
            BackupRetentionPeriod=7,
            MultiAZ=False,
            PubliclyAccessible=True,
            StorageType="gp2"
        )
        print("Creating RDS instance...")
        print(response)
    except ClientError as e:
        print(f"Error creating RDS instance: {e.response['Error']['Message']}")

# Call the function to create the instance
create_rds_instance()