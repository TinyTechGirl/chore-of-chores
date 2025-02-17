# app.py
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import random
import datetime

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # redirect to login if unauthorized access

# ---------------------
# Database Models
# ---------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # Relationship: One user can have many chores
    chores = db.relationship('Chore', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Chore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chore_text = db.Column(db.String(256), nullable=False)
    chore_type = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', or 'monthly'
    # You could also store counts for daily/monthly selections if you want to track usage per chore.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ---------------------
# Flask-Login Loader
# ---------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------
# Routes for Authentication
# ---------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('wheel'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if the user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        # Create new user
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('wheel'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('wheel'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------------------
# Routes for the Chore Wheel
# ---------------------

@app.route('/')
def index():
    return redirect(url_for('wheel'))

@app.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    """Page where the user enters chores. Chores are stored in the database."""
    if request.method == 'POST':
        # Here, assume chores are input as multiline text separated by category.
        daily = request.form.get('daily', '')
        weekly = request.form.get('weekly', '')
        monthly = request.form.get('monthly', '')
        
        # Split and save each chore into the database, associated with the current user
        for chore_text in [c.strip() for c in daily.splitlines() if c.strip()]:
            chore = Chore(chore_text=chore_text, chore_type='daily', owner=current_user)
            db.session.add(chore)
        for chore_text in [c.strip() for c in weekly.splitlines() if c.strip()]:
            chore = Chore(chore_text=chore_text, chore_type='weekly', owner=current_user)
            db.session.add(chore)
        for chore_text in [c.strip() for c in monthly.splitlines() if c.strip()]:
            chore = Chore(chore_text=chore_text, chore_type='monthly', owner=current_user)
            db.session.add(chore)
        db.session.commit()

        # Initialize session counts for spinning the wheel
        today = datetime.date.today().isoformat()
        month = datetime.date.today().strftime("%Y-%m")
        session['daily_count'] = {'date': today, 'count': 0}
        session['monthly_count'] = {'month': month, 'count': 0}
        
        return redirect(url_for('wheel'))
    
    return render_template('setup.html')

@app.route('/wheel')
@login_required
def wheel():
    """Chore wheel page."""
    return render_template('wheel.html')

@app.route('/spin', methods=['POST'])
@login_required
def spin():
    """Spin the wheel and choose an eligible chore based on limits."""
    # Retrieve current user's chores from the database
    chores = Chore.query.filter_by(user_id=current_user.id).all()
    # Organize chores by type
    chore_dict = {'daily': [], 'weekly': [], 'monthly': []}
    for chore in chores:
        chore_dict[chore.chore_type].append(chore.chore_text)

    today = datetime.date.today().isoformat()
    month = datetime.date.today().strftime("%Y-%m")

    # Reset daily count if day has changed
    daily_count = session.get('daily_count', {'date': today, 'count': 0})
    if daily_count.get('date') != today:
        daily_count = {'date': today, 'count': 0}

    # Reset monthly count if month has changed
    monthly_count = session.get('monthly_count', {'month': month, 'count': 0})
    if monthly_count.get('month') != month:
        monthly_count = {'month': month, 'count': 0}

    allowed = []
    if daily_count['count'] < 2:
        for chore in chore_dict.get('daily', []):
            allowed.append({'chore': chore, 'type': 'daily'})
    # Weekly chores are always allowed
    for chore in chore_dict.get('weekly', []):
        allowed.append({'chore': chore, 'type': 'weekly'})
    # Monthly chores allowed only once per month
    if monthly_count['count'] < 1:
        for chore in chore_dict.get('monthly', []):
            allowed.append({'chore': chore, 'type': 'monthly'})

    if not allowed:
        return jsonify({'error': 'No eligible chores available at the moment.'})

    selected = random.choice(allowed)

    if selected['type'] == 'daily':
        daily_count['count'] += 1
        session['daily_count'] = daily_count
    elif selected['type'] == 'monthly':
        monthly_count['count'] += 1
        session['monthly_count'] = monthly_count

    session.modified = True
    return jsonify(selected)

if __name__ == '__main__':
    app.run(debug=True)
