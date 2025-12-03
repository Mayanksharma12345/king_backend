"""
Test Azure SQL Database Connection

Run this to verify your Azure SQL configuration before starting the app.
"""

import os
import sys
from dotenv import load_dotenv
import pyodbc
import urllib.parse

# Load environment variables
load_dotenv()

def test_pyodbc_connection():
    """Test direct pyodbc connection to Azure SQL"""
    print("\n=== Testing Azure SQL Connection ===\n")
    
    # Get credentials from environment
    server = os.getenv('AZURE_SQL_SERVER', 'your-server.database.windows.net')
    database = os.getenv('AZURE_SQL_DATABASE', 'medicalscribe')
    username = os.getenv('AZURE_SQL_USERNAME', 'sqladmin')
    password = os.getenv('AZURE_SQL_PASSWORD', '')
    
    print(f"Server: {server}")
    print(f"Database: {database}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else '(not set)'}\n")
    
    if not password:
        print("❌ ERROR: AZURE_SQL_PASSWORD not set in .env file")
        return False
    
    # Connection string
    connection_string = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=tcp:{server},1433;"
        f"Database={database};"
        f"Uid={username};"
        f"Pwd={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
    )
    
    try:
        print("Attempting connection...")
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        
        print("✅ Connection successful!")
        print(f"\nSQL Server Version:\n{row[0][:200]}...\n")
        
        # Test creating a simple table
        print("Testing table creation...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'test_connection')
            CREATE TABLE test_connection (
                id INT PRIMARY KEY IDENTITY(1,1),
                test_message NVARCHAR(100)
            )
        """)
        conn.commit()
        
        cursor.execute("INSERT INTO test_connection (test_message) VALUES (?)", ("Connection test successful",))
        conn.commit()
        
        cursor.execute("SELECT * FROM test_connection")
        rows = cursor.fetchall()
        print(f"✅ Table operations successful! Rows: {len(rows)}")
        
        # Cleanup
        cursor.execute("DROP TABLE test_connection")
        conn.commit()
        print("✅ Cleanup successful!")
        
        cursor.close()
        conn.close()
        
        print("\n=== All Tests Passed! ===\n")
        return True
        
    except pyodbc.Error as e:
        print(f"\n❌ Connection failed!")
        print(f"Error: {str(e)}\n")
        
        if "Login failed" in str(e):
            print("Troubleshooting:")
            print("1. Check your username and password")
            print("2. Verify Azure SQL firewall allows your IP address")
            print("3. Ensure 'Allow Azure services' is enabled")
        elif "Cannot open server" in str(e):
            print("Troubleshooting:")
            print("1. Check server name is correct")
            print("2. Verify server exists in Azure portal")
            print("3. Check your internet connection")
        elif "ODBC Driver" in str(e):
            print("Troubleshooting:")
            print("1. Install ODBC Driver 18 for SQL Server")
            print("   Windows: https://go.microsoft.com/fwlink/?linkid=2249004")
            print("   macOS: brew install msodbcsql18")
            print("   Linux: Follow https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server")
        
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}\n")
        return False


def test_sqlalchemy_connection():
    """Test SQLAlchemy connection"""
    print("\n=== Testing SQLAlchemy Connection ===\n")
    
    from sqlalchemy import create_engine, text
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not set in .env file")
        return False
    
    print(f"DATABASE_URL: {database_url[:50]}...\n")
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION"))
            version = result.fetchone()[0]
            print("✅ SQLAlchemy connection successful!")
            print(f"\nVersion: {version[:200]}...\n")
        
        return True
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {str(e)}\n")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Azure SQL Database Connection Test")
    print("=" * 60)
    
    # Test pyodbc first
    pyodbc_success = test_pyodbc_connection()
    
    if pyodbc_success:
        # Test SQLAlchemy
        sqlalchemy_success = test_sqlalchemy_connection()
        
        if sqlalchemy_success:
            print("\n✅ All connection tests passed!")
            print("Your Azure SQL Database is ready to use.\n")
            sys.exit(0)
    
    print("\n❌ Connection tests failed. Please fix the issues above.\n")
    sys.exit(1)
