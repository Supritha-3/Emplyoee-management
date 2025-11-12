"""
Database Setup Script
Creates the employee_db database and employees table
Run this script once before starting the Flask application
"""

import mysql.connector
from mysql.connector import Error

def create_database():
    """
    Creates the employee_db database if it doesn't exist
    """
    try:
        # Connect to MySQL server (without specifying database)
        connection = mysql.connector.connect(
            host='localhost',
            user='root',  # Change to your MySQL username
            password=''   # Change to your MySQL password
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS employee_db")
            print("Database 'employee_db' created successfully or already exists")
            
            # Close cursor and connection
            cursor.close()
            connection.close()
            
    except Error as e:
        print(f"Error creating database: {e}")
        return False
    
    return True

def create_tables():
    """
    Creates the employees and attendance tables in employee_db
    """
    try:
        # Connect to employee_db database
        connection = mysql.connector.connect(
            host='localhost',
            user='root',  # Change to your MySQL username
            password='',  # Change to your MySQL password
            database='employee_db'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create employees table
            employees_table = """
            CREATE TABLE IF NOT EXISTS employees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                department VARCHAR(50) NOT NULL,
                role VARCHAR(50) NOT NULL,
                salary FLOAT NOT NULL,
                attendance INT DEFAULT 0,
                performance_rating FLOAT DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(employees_table)
            print("Table 'employees' created successfully or already exists")
            
            # Create attendance table (optional extension)
            attendance_table = """
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'Present',
                hours_worked FLOAT DEFAULT 8.0,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE,
                UNIQUE KEY unique_attendance (emp_id, date)
            )
            """
            cursor.execute(attendance_table)
            print("Table 'attendance' created successfully or already exists")
            
            # Create admin table for login system
            admin_table = """
            CREATE TABLE IF NOT EXISTS admin (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(admin_table)
            print("Table 'admin' created successfully or already exists")
            
            # Insert default admin if not exists
            cursor.execute("SELECT COUNT(*) FROM admin")
            if cursor.fetchone()[0] == 0:
                # Default admin credentials: admin/admin123
                # In production, use password hashing (bcrypt)
                default_admin = """
                INSERT INTO admin (username, password) 
                VALUES ('admin', 'admin123')
                """
                cursor.execute(default_admin)
                connection.commit()
                print("Default admin user created (username: admin, password: admin123)")
            
            # Commit changes
            connection.commit()
            
            # Close cursor and connection
            cursor.close()
            connection.close()
            
    except Error as e:
        print(f"Error creating tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Setting up database...")
    if create_database():
        if create_tables():
            print("\nDatabase setup completed successfully!")
            print("\nDefault admin credentials:")
            print("Username: admin")
            print("Password: admin123")
            print("\nPlease change the database credentials in database_setup.py and app.py before running the application.")
        else:
            print("Failed to create tables")
    else:
        print("Failed to create database")
