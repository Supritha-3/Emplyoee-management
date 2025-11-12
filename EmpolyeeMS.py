"""
Employee Management System
Flask web application for managing employee records
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this in production

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Change to your MySQL username
    'password': '',  # Change to your MySQL password
    'database': 'employee_db'
}

def get_db_connection():
    """
    Establishes and returns a MySQL database connection
    Returns: MySQL connection object or None if connection fails
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def is_logged_in():
    """
    Checks if user is logged in by checking session
    Returns: True if logged in, False otherwise
    """
    return 'logged_in' in session and session['logged_in'] == True

def login_required(f):
    """
    Decorator to protect routes that require authentication
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """
    Dashboard route - displays summary statistics
    """
    if not is_logged_in():
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if not connection:
        flash('Database connection error', 'danger')
        return render_template('index.html', stats={})
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get total employees count
        cursor.execute("SELECT COUNT(*) as total FROM employees")
        total_employees = cursor.fetchone()['total']
        
        # Get average salary
        cursor.execute("SELECT AVG(salary) as avg_salary FROM employees")
        avg_salary_result = cursor.fetchone()
        avg_salary = avg_salary_result['avg_salary'] if avg_salary_result['avg_salary'] else 0
        
        # Get total departments
        cursor.execute("SELECT COUNT(DISTINCT department) as total_depts FROM employees")
        total_departments = cursor.fetchone()['total_depts']
        
        # Get total payroll (sum of all salaries)
        cursor.execute("SELECT SUM(salary) as total_payroll FROM employees")
        total_payroll_result = cursor.fetchone()
        total_payroll = total_payroll_result['total_payroll'] if total_payroll_result['total_payroll'] else 0
        
        # Get department-wise employee count
        cursor.execute("""
            SELECT department, COUNT(*) as count 
            FROM employees 
            GROUP BY department
        """)
        department_stats = cursor.fetchall()
        
        stats = {
            'total_employees': total_employees,
            'avg_salary': round(avg_salary, 2),
            'total_departments': total_departments,
            'total_payroll': round(total_payroll, 2),
            'department_stats': department_stats
        }
        
        cursor.close()
        connection.close()
        
        return render_template('index.html', stats=stats)
        
    except Error as e:
        flash(f'Error fetching statistics: {str(e)}', 'danger')
        return render_template('index.html', stats={})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route - handles user authentication
    GET: Displays login form
    POST: Validates credentials and creates session
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection error', 'danger')
            return render_template('login.html')
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM admin WHERE username = %s AND password = %s", 
                          (username, password))
            admin = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if admin:
                session['logged_in'] = True
                session['username'] = username
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'danger')
                
        except Error as e:
            flash(f'Error during login: {str(e)}', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """
    Logout route - clears session and redirects to login
    """
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    """
    Add Employee route - handles adding new employees
    GET: Displays add employee form
    POST: Processes form data and inserts into database
    """
    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        name = request.form.get('name')
        department = request.form.get('department')
        role = request.form.get('role')
        salary = request.form.get('salary')
        attendance = request.form.get('attendance', 0)
        performance_rating = request.form.get('performance_rating', 0.0)
        
        # Validate required fields
        if not all([emp_id, name, department, role, salary]):
            flash('All fields are required', 'danger')
            return render_template('add.html')
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection error', 'danger')
            return render_template('add.html')
        
        try:
            cursor = connection.cursor()
            
            # Check if employee ID already exists
            cursor.execute("SELECT * FROM employees WHERE emp_id = %s", (emp_id,))
            if cursor.fetchone():
                flash('Employee ID already exists', 'danger')
                cursor.close()
                connection.close()
                return render_template('add.html')
            
            # Insert new employee
            insert_query = """
                INSERT INTO employees (emp_id, name, department, role, salary, attendance, performance_rating)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (emp_id, name, department, role, float(salary), 
                                         int(attendance), float(performance_rating)))
            connection.commit()
            
            cursor.close()
            connection.close()
            
            flash('Employee added successfully!', 'success')
            return redirect(url_for('view_employees'))
            
        except Error as e:
            flash(f'Error adding employee: {str(e)}', 'danger')
            if connection:
                connection.rollback()
                connection.close()
    
    return render_template('add.html')

@app.route('/view')
@login_required
def view_employees():
    """
    View Employees route - displays all employees in a table
    Supports filtering by department or searching by ID
    """
    connection = get_db_connection()
    if not connection:
        flash('Database connection error', 'danger')
        return render_template('view.html', employees=[], departments=[], search_id='', search_department='')
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get filter parameters
        search_id = request.args.get('search_id', '')
        search_department = request.args.get('search_department', '')
        
        # Build query based on filters
        query = "SELECT * FROM employees WHERE 1=1"
        params = []
        
        if search_id:
            query += " AND emp_id LIKE %s"
            params.append(f'%{search_id}%')
        
        if search_department:
            query += " AND department = %s"
            params.append(search_department)
        
        query += " ORDER BY id DESC"
        
        cursor.execute(query, params)
        employees = cursor.fetchall()
        
        # Get distinct departments for filter dropdown
        cursor.execute("SELECT DISTINCT department FROM employees ORDER BY department")
        departments = [row['department'] for row in cursor.fetchall()]
        
        cursor.close()
        connection.close()
        
        return render_template('view.html', employees=employees, departments=departments,
                             search_id=search_id, search_department=search_department)
        
    except Error as e:
        flash(f'Error fetching employees: {str(e)}', 'danger')
        return render_template('view.html', employees=[], departments=[], search_id='', search_department='')

@app.route('/update/<emp_id>', methods=['GET', 'POST'])
@login_required
def update_employee(emp_id):
    """
    Update Employee route - handles updating employee details
    GET: Displays update form with current employee data
    POST: Processes form data and updates database
    """
    connection = get_db_connection()
    if not connection:
        flash('Database connection error', 'danger')
        return redirect(url_for('view_employees'))
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name')
            department = request.form.get('department')
            role = request.form.get('role')
            salary = request.form.get('salary')
            attendance = request.form.get('attendance', 0)
            performance_rating = request.form.get('performance_rating', 0.0)
            
            # Validate required fields
            if not all([name, department, role, salary]):
                flash('All fields are required', 'danger')
                cursor.execute("SELECT * FROM employees WHERE emp_id = %s", (emp_id,))
                employee = cursor.fetchone()
                cursor.close()
                connection.close()
                return render_template('update.html', employee=employee)
            
            # Update employee
            update_query = """
                UPDATE employees 
                SET name = %s, department = %s, role = %s, salary = %s, 
                    attendance = %s, performance_rating = %s
                WHERE emp_id = %s
            """
            cursor.execute(update_query, (name, department, role, float(salary), 
                                         int(attendance), float(performance_rating), emp_id))
            connection.commit()
            
            cursor.close()
            connection.close()
            
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('view_employees'))
        
        else:
            # GET request - fetch employee data
            cursor.execute("SELECT * FROM employees WHERE emp_id = %s", (emp_id,))
            employee = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if not employee:
                flash('Employee not found', 'danger')
                return redirect(url_for('view_employees'))
            
            return render_template('update.html', employee=employee)
        
    except Error as e:
        flash(f'Error updating employee: {str(e)}', 'danger')
        if connection:
            connection.rollback()
            connection.close()
        return redirect(url_for('view_employees'))

@app.route('/delete/<emp_id>')
@login_required
def delete_employee(emp_id):
    """
    Delete Employee route - deletes an employee from database
    """
    connection = get_db_connection()
    if not connection:
        flash('Database connection error', 'danger')
        return redirect(url_for('view_employees'))
    
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM employees WHERE emp_id = %s", (emp_id,))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        flash('Employee deleted successfully!', 'success')
        
    except Error as e:
        flash(f'Error deleting employee: {str(e)}', 'danger')
        if connection:
            connection.rollback()
            connection.close()
    
    return redirect(url_for('view_employees'))

@app.route('/attendance')
@login_required
def attendance():
    """
    Attendance route - displays attendance records with employee details (JOIN query)
    """
    connection = get_db_connection()
    if not connection:
        flash('Database connection error', 'danger')
        return render_template('attendance.html', records=[], employees=[], today_date=date.today().isoformat())
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # JOIN query to get attendance with employee details
        query = """
            SELECT a.*, e.name, e.department, e.role
            FROM attendance a
            INNER JOIN employees e ON a.emp_id = e.emp_id
            ORDER BY a.date DESC, e.name
        """
        cursor.execute(query)
        records = cursor.fetchall()
        
        # Get all employees for adding attendance
        cursor.execute("SELECT emp_id, name FROM employees ORDER BY name")
        employees = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('attendance.html', records=records, employees=employees, today_date=date.today().isoformat())
        
    except Error as e:
        flash(f'Error fetching attendance: {str(e)}', 'danger')
        return render_template('attendance.html', records=[], employees=[], today_date=date.today().isoformat())

@app.route('/attendance/add', methods=['POST'])
@login_required
def add_attendance():
    """
    Add Attendance route - adds attendance record for an employee
    """
    emp_id = request.form.get('emp_id')
    date_str = request.form.get('date')
    status = request.form.get('status', 'Present')
    hours_worked = request.form.get('hours_worked', 8.0)
    
    if not emp_id or not date_str:
        flash('Employee ID and date are required', 'danger')
        return redirect(url_for('attendance'))
    
    connection = get_db_connection()
    if not connection:
        flash('Database connection error', 'danger')
        return redirect(url_for('attendance'))
    
    try:
        cursor = connection.cursor()
        
        # Insert attendance record (ON DUPLICATE KEY UPDATE if exists)
        insert_query = """
            INSERT INTO attendance (emp_id, date, status, hours_worked)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status = %s, hours_worked = %s
        """
        cursor.execute(insert_query, (emp_id, date_str, status, float(hours_worked), 
                                     status, float(hours_worked)))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        flash('Attendance record added successfully!', 'success')
        
    except Error as e:
        flash(f'Error adding attendance: {str(e)}', 'danger')
        if connection:
            connection.rollback()
            connection.close()
    
    return redirect(url_for('attendance'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

