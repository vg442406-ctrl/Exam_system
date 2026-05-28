import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nexus_ultra_secure_pass_key_8849')

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///nexus_exam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------------------------------------------------------
# COMPREHENSIVE PRODUCTION SYSTEM DATABASE SCHEMAS
# -------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student') # student, teacher

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, default=30)
    total_marks = db.Column(db.Integer, default=2)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(100), nullable=False)
    option_b = db.Column(db.String(100), nullable=False)
    option_c = db.Column(db.String(100), nullable=False)
    option_d = db.Column(db.String(100), nullable=False)
    correct_option = db.Column(db.String(5), nullable=False) # A, B, C, or D

class ScoreRecord(db.Model):
    __tablename__ = 'score_records'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    exam_title = db.Column(db.String(100), nullable=False)
    score_earned = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    percent = db.Column(db.Float, nullable=False)
    violations = db.Column(db.Integer, default=0)

# -------------------------------------------------------------------------
# WEB ROUTING PIPELINE & VALIDATION ENGINES
# -------------------------------------------------------------------------
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('dashboard'))
            
        flash("Invalid identification credentials entered.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        role = request.form.get('role')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash("Username variant already claimed inside our ledger system.")
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, role=role, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))
    if session.get('role') == 'teacher': return redirect(url_for('admin_panel'))
    
    exams = Exam.query.all()
    return render_template('dashboard.html', exams=exams)

@app.route('/exam/<int:exam_id>')
def take_exam(exam_id):
    if 'username' not in session: return redirect(url_for('login'))
    exam_instance = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).all()
    return render_template('exam.html', exam=exam_instance, questions=questions)

@app.route('/exam/<int:exam_id>/submit', methods=['POST'])
def submit_exam(exam_id):
    if 'username' not in session: return redirect(url_for('login'))
    exam_instance = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).all()
    
    score = 0
    for q in questions:
        selected_answer = request.form.get(f'q_{q.id}')
        if selected_answer == q.correct_option:
            score += 1
            
    violations = int(request.form.get('violations', 0))
    pct = round((score / len(questions)) * 100, 2) if len(questions) > 0 else 0.0
    
    record = ScoreRecord(
        username=session['username'],
        exam_title=exam_instance.title,
        score_earned=score,
        total_marks=len(questions),
        percent=pct,
        violations=violations
    )
    db.session.add(record)
    db.session.commit()
    
    return f"<h1>Exam processing finalized! Instantly Graded Score: {score}/{len(questions)} ({pct}%). Security Tab Violations Logged: {violations}. You can safely close this browser instance.</h1>"

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'teacher': return "Unauthorized Role Access Blocked.", 403
    results = ScoreRecord.query.all()
    return render_template('admin.html', results=results)

@app.route('/admin/create-exam', methods=['POST'])
def create_exam():
    if session.get('role') != 'teacher': return "Unauthorized", 403
    title = request.form.get('title')
    duration = int(request.form.get('duration'))
    
    new_exam = Exam(title=title, duration=duration, total_marks=2)
    db.session.add(new_exam)
    db.session.commit()
    
    # Injection routine mapping automated test patterns cleanly
    q1 = Question(exam_id=new_exam.id, question_text="What is the runtime behavior of an SQLite engine lookup?", option_a="Serverless Engine File mapping", option_b="Network socket streaming interface", option_c="Non-relational document matrix lookup", option_d="Distributed vector array alignment", correct_option="A")
    q2 = Question(exam_id=new_exam.id, question_text="Which decorator model enforces dynamic route processing methods in a clean Flask wrapper layout?", option_a="@app.render", option_b="@app.route", option_c="@app.post", option_d="@app.blueprint", correct_option="B")
    db.session.add_all([q1, q2])
    db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------------------------------------------------------------
# ENVIRONMENT SEED ENGINES
# -------------------------------------------------------------------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password_hash=generate_password_hash('nexus123'), role='teacher'))
        db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
