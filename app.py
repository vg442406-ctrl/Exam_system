import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates')

# SECURITY: Use a secret key from environment variables, or a fallback for local testing
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nexus_fallback_secure_key_1928')

# DATABASE CONFIGURATION: Automatically switches from local SQLite to cloud MySQL when deployed
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///nexus_exam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------------------------------------------------------
# DATABASE MODELS
# -------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

# -------------------------------------------------------------------------
# ROUTES / CONTROLLERS
# -------------------------------------------------------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            return f"<h1>Access Granted. Welcome back to Nexus, {username}!</h1>"
        
        flash("Invalid username or password.")
        return redirect(url_for('login'))
        
    return render_template('login.html')

# -------------------------------------------------------------------------
# INITIALIZATION ROUTINE FOR LIVE SERVERS
# -------------------------------------------------------------------------
with app.app_context():
    db.create_all()
    # Create a default admin user if the database is completely fresh and empty
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('nexus123')
        default_admin = User(username='admin', password_hash=hashed_pw)
        db.session.add(default_admin)
        db.session.commit()

if __name__ == '__main__':
    # Cloud providers like Render tell your app which port to use via an environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
