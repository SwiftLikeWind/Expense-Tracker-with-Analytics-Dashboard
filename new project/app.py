from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import bcrypt
import matplotlib.pyplot as plt
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
engine = create_engine('sqlite:///expense_tracker.db', echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# User model
class User(Base, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)

# Expense model
class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String)

# Create tables
Base.metadata.create_all(engine)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(int(user_id))

# Helper functions
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        new_user = User(username=username, hashed_password=hashed_password)
        session.add(new_user)
        session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = session.query(User).filter_by(username=username).first()
        if user and check_password(user.hashed_password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Generate monthly spending trends
    monthly_totals = session.query(
        func.strftime('%Y-%m', Expense.date).label('month'),
        func.sum(Expense.amount).label('total')
    ).filter(Expense.user_id == current_user.id).group_by('month').all()

    months = [row.month for row in monthly_totals]
    totals = [row.total for row in monthly_totals]

    plt.bar(months, totals)
    plt.xlabel('Month')
    plt.ylabel('Total Spending')
    plt.title('Monthly Spending Trends')
    plt.savefig('static/monthly_trends.png')
    plt.close()

    # Generate category-wise spending
    category_totals = session.query(
        Expense.category,
        func.sum(Expense.amount).label('total')
    ).filter(Expense.user_id == current_user.id).group_by(Expense.category).all()

    categories = [row.category for row in category_totals]
    totals = [row.total for row in category_totals]

    plt.pie(totals, labels=categories, autopct='%1.1f%%')
    plt.title('Spending by Category')
    plt.savefig('static/category_pie.png')
    plt.close()

    return render_template('dashboard.html')

@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        description = request.form['description']
        new_expense = Expense(user_id=current_user.id, category=category, amount=amount, date=date, description=description)
        session.add(new_expense)
        session.commit()
        flash('Expense added successfully!')
        return redirect(url_for('dashboard'))
    return render_template('add_expense.html')

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = session.query(Expense).filter_by(id=expense_id, user_id=current_user.id).first()
    if request.method == 'POST':
        expense.category = request.form['category']
        expense.amount = float(request.form['amount'])
        expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        expense.description = request.form['description']
        session.commit()
        flash('Expense updated successfully!')
        return redirect(url_for('dashboard'))
    return render_template('edit_expense.html', expense=expense)

@app.route('/delete_expense/<int:expense_id>')
@login_required
def delete_expense(expense_id):
    expense = session.query(Expense).filter_by(id=expense_id, user_id=current_user.id).first()
    session.delete(expense)
    session.commit()
    flash('Expense deleted successfully!')
    return redirect(url_for('dashboard'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)