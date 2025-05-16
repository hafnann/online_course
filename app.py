from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret-key'
DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        email TEXT UNIQUE,
                        password TEXT,
                        age INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (
                        id INTEGER PRIMARY KEY,
                        email TEXT,
                        password TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY,
                        name TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS courses (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        description TEXT,
                        duration TEXT,
                        fee INTEGER,
                        category_id INTEGER,
                        FOREIGN KEY (category_id) REFERENCES categories(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS enrollments (
                        id INTEGER PRIMARY KEY,
                        student_id INTEGER,
                        course_id INTEGER,
                        date TEXT,
                        UNIQUE(student_id, course_id),
                        FOREIGN KEY (student_id) REFERENCES students(id),
                        FOREIGN KEY (course_id) REFERENCES courses(id))''')
        # Default admin
        c.execute("INSERT OR IGNORE INTO admins (id, email, password) VALUES (1, 'admin@example.com', 'admin')")
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        age = request.form['age']
        with get_db() as conn:
            try:
                conn.execute("INSERT INTO students (name, email, password, age) VALUES (?, ?, ?, ?)",
                             (name, email, password, age))
                conn.commit()
                flash('Registration successful!', 'success')
                return redirect(url_for('login'))
            except:
                flash('Email already registered!', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with get_db() as conn:
            user = conn.execute("SELECT * FROM students WHERE email = ? AND password = ?", (email, password)).fetchone()
            if user:
                session['student_id'] = user['id']
                session['student_name'] = user['name']
                return redirect(url_for('student_dashboard'))
            else:
                flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with get_db() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE email = ? AND password = ?", (email, password)).fetchone()
            if admin:
                session['admin'] = True
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials!', 'danger')
    return render_template('admin_login.html')

@app.route('/student-dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    with get_db() as conn:
        courses = conn.execute("SELECT courses.*, categories.name as category FROM courses LEFT JOIN categories ON courses.category_id = categories.id").fetchall()
    return render_template('student_dashboard.html', courses=courses)

@app.route('/enroll/<int:course_id>')
def enroll(course_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))
    with get_db() as conn:
        try:
            conn.execute("INSERT INTO enrollments (student_id, course_id, date) VALUES (?, ?, ?)",
                         (session['student_id'], course_id, datetime.now().strftime('%Y-%m-%d')))
            conn.commit()
            flash('Enrolled successfully!', 'success')
        except:
            flash('Already enrolled!', 'warning')
    return redirect(url_for('student_dashboard'))

@app.route('/my-courses')
def my_courses():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    with get_db() as conn:
        courses = conn.execute('''SELECT courses.name, courses.duration, enrollments.date FROM enrollments 
                                  JOIN courses ON enrollments.course_id = courses.id WHERE enrollments.student_id = ?''',
                               (session['student_id'],)).fetchall()
    return render_template('my_courses.html', courses=courses)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/add-category', methods=['GET', 'POST'])
def add_category():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        name = request.form['name']
        with get_db() as conn:
            conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            conn.commit()
            flash('Category added!', 'success')
    return render_template('add_category.html')

@app.route('/add-course', methods=['GET', 'POST'])
def add_course():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    with get_db() as conn:
        categories = conn.execute("SELECT * FROM categories").fetchall()
    if request.method == 'POST':
        name = request.form['name']
        desc = request.form['description']
        duration = request.form['duration']
        fee = request.form['fee']
        category_id = request.form['category']
        with get_db() as conn:
            conn.execute("INSERT INTO courses (name, description, duration, fee, category_id) VALUES (?, ?, ?, ?, ?)",
                         (name, desc, duration, fee, category_id))
            conn.commit()
            flash('Course added!', 'success')
    return render_template('add_course.html', categories=categories)

@app.route('/view-enrollments')
def view_enrollments():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    with get_db() as conn:
        enrollments = conn.execute('''SELECT students.name as student_name, students.email, courses.name as course_name, enrollments.date
                                      FROM enrollments
                                      JOIN students ON enrollments.student_id = students.id
                                      JOIN courses ON enrollments.course_id = courses.id''').fetchall()
    return render_template('view_enrollments.html', enrollments=enrollments)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
