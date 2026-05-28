import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nexus_secure_key_8849')

# --- FIND AND REPLACE ONLY THIS TOP SECTION IN YOUR APP.PY ---
DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///nexus_exam.db')
if DB_URL.startswith("postgres://"): 
    # This explicitly links Flask to our modern Python 3.14 driver!
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models (Explicit Table Names to Match Your Live Postgres Database)
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student')

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, default=30)
    total_marks = db.Column(db.Integer, default=0)
    host_username = db.Column(db.String(50), default='')
    admin_passcode = db.Column(db.String(50), default='1234')
    is_active = db.Column(db.Boolean, default=False)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(100), nullable=False)
    option_b = db.Column(db.String(100), nullable=False)
    option_c = db.Column(db.String(100), nullable=False)
    option_d = db.Column(db.String(100), nullable=False)
    correct_option = db.Column(db.String(5), nullable=False)

class ScoreRecord(db.Model):
    __tablename__ = 'score_records'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    exam_title = db.Column(db.String(100), nullable=False)
    score_earned = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    percent = db.Column(db.Float, nullable=False)
    violations = db.Column(db.Integer, default=0)

class WebcamSnapshot(db.Model):
    __tablename__ = 'webcam_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    image_base64 = db.Column(db.Text, nullable=False)

# Core Authentication Endpoints
@app.route('/')
def home():
    return redirect(url_for('dashboard')) if 'username' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username').strip(), request.form.get('password')
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password_hash, p):
            session['username'], session['role'] = user.username, user.role
            return redirect(url_for('dashboard'))
        flash("Invalid identification credentials.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, r, p = request.form.get('username').strip(), request.form.get('role'), request.form.get('password')
        if User.query.filter_by(username=u).first():
            flash("Username claimed.")
            return redirect(url_for('register'))
        db.session.add(User(username=u, role=r, password_hash=generate_password_hash(p)))
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))
    return redirect(url_for('admin_panel')) if session.get('role') == 'teacher' else render_template('dashboard.html', exams=Exam.query.all())

# Student Exam Testing Endpoints
@app.route('/exam/<int:exam_id>')
def take_exam(exam_id):
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('exam.html', exam=Exam.query.get_or_404(exam_id), questions=Question.query.filter_by(exam_id=exam_id).all())

@app.route('/exam/<int:exam_id>/submit', methods=['POST'])
def submit_exam(exam_id):
    if 'username' not in session: return redirect(url_for('login'))
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).all()
    score = sum([1 for q in questions if request.form.get(f'q_{q.id}') == q.correct_option])
    v = int(request.form.get('violations', 0))
    pct = round((score / len(questions)) * 100, 2) if questions else 0.0
    
    db.session.add(ScoreRecord(username=session['username'], exam_title=exam.title, score_earned=score, total_marks=len(questions), percent=pct, violations=v))
    WebcamSnapshot.query.filter_by(username=session['username']).delete()
    db.session.commit()
    return f"<h1>Exam Submitted! Score: {score}/{len(questions)} ({pct}%).</h1>"

# Live Video Proctoring Endpoints
@app.route('/api/proctor/upload', methods=['POST'])
def proctor_upload():
    if 'username' not in session: return jsonify({"error": "Unauthorized"}), 401
    img = request.get_json().get('image')
    feed = WebcamSnapshot.query.filter_by(username=session['username']).first()
    if feed: feed.image_base64 = img
    else: db.session.add(WebcamSnapshot(username=session['username'], image_base64=img))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/proctor/feeds')
def proctor_feeds():
    if session.get('role') != 'teacher': return jsonify({"error": "Unauthorized"}), 403
    return jsonify({"feeds": [{"username": f.username, "image": f.image_base64} for f in WebcamSnapshot.query.all()]})

# Host Meeting Monitoring Endpoints
@app.route('/api/meeting/<int:exam_id>/status')
def meeting_status(exam_id):
    e = Exam.query.get_or_404(exam_id)
    return jsonify({"is_active": e.is_active, "host_username": e.host_username})

@app.route('/api/meeting/<int:exam_id>/claim-host', methods=['POST'])
def claim_host(exam_id):
    if 'username' not in session: return jsonify({"error": "Unauthorized"}), 401
    e = Exam.query.get_or_404(exam_id)
    if request.get_json().get('passcode') == e.admin_passcode:
        e.host_username, e.is_active = session['username'], True
        session['role'] = 'teacher'
        db.session.commit()
        return jsonify({"status": "success", "message": "Host Recovery Accepted!"})
    return jsonify({"status": "error", "message": "Incorrect Passcode!"}), 400

# Teacher Management Panel Endpoints
@app.route('/admin')
def admin_panel():
    if session.get('role') != 'teacher': return "Unauthorized Access", 403
    return render_template('admin.html', results=ScoreRecord.query.all(), exams=Exam.query.all())

@app.route('/admin/create-exam', methods=['POST'])
def create_exam():
    if session.get('role') != 'teacher': return "Unauthorized", 403
    db.session.add(Exam(title=request.form.get('title'), duration=int(request.form.get('duration')), admin_passcode=request.form.get('admin_passcode', '1234'), host_username=session['username'], is_active=True))
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add-question', methods=['POST'])
def add_question():
    if session.get('role') != 'teacher': return "Unauthorized", 403
    e_id = int(request.form.get('exam_id'))
    db.session.add(Question(exam_id=e_id, question_text=request.form.get('question_text'), option_a=request.form.get('option_a'), option_b=request.form.get('option_b'), option_c=request.form.get('option_c'), option_d=request.form.get('option_d'), correct_option=request.form.get('correct_option')))
    exam = Exam.query.get(e_id)
    if exam: exam.total_marks += 1
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/leave-meeting/<int:exam_id>')
def leave_meeting(exam_id):
    if session.get('role') != 'teacher': return "Unauthorized", 403
    e = Exam.query.get_or_404(exam_id)
    e.host_username, e.is_active = "", False
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    for e in Exam.query.filter_by(host_username=session.get('username')).all(): e.host_username, e.is_active = "", False
    WebcamSnapshot.query.filter_by(username=session.get('username')).delete()
    db.session.commit()
    session.clear()
    return redirect(url_for('login'))

with app.app_context(): db.create_all()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
