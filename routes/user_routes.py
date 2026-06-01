from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db_connection import db

user_bp = Blueprint('user', __name__)

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('loginIdentifier', '').strip()
        password = request.form.get('loginPassword', '')

        if not identifier or not password:
            flash('Please enter both email/username and password.', 'error')
            return render_template('login.html')

        user = db.users.find_one({'$or': [{'email': identifier}, {'username': identifier}]})
        if user and check_password_hash(user['password'], password):
            session['current_user'] = {
                'username': user['username'],
                'email': user['email'],
                'delivery_name': user.get('delivery_name', ''),
                'delivery_location': user.get('delivery_location', ''),
                'delivery_pincode': user.get('delivery_pincode', '')
            }
            flash('Login successful. Welcome back! 🛒', 'success')
            return redirect(url_for('shop.location'))

        flash('Invalid credentials. Please try again.', 'error')

    return render_template('login.html')

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirmPassword', '')

        if not username or not email or not password or not confirm_password:
            flash('All fields except contact number are required.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        if db.users.find_one({'$or': [{'email': email}, {'username': username}]}) is not None:
            flash('A user with that email or username already exists.', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        db.users.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'delivery_name': '',
            'delivery_location': '',
            'delivery_pincode': ''
        })

        # After successful registration, require the user to login first
        # so the profile page is only displayed after authentication.
        flash('Registration successful. Please login to continue.', 'success')
        return redirect(url_for('user.login'))

    return render_template('register.html')

@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    current_user_session = session.get('current_user')
    if not current_user_session:
        flash('Please login to view your profile.', 'error')
        return redirect(url_for('user.login'))

    user = db.users.find_one({'username': current_user_session['username']})

    if request.method == 'POST':
        new_name = request.form.get('delivery_name', '').strip()
        new_location = request.form.get('delivery_location', '').strip()
        new_pincode = request.form.get('delivery_pincode', '').strip()

        db.users.update_one(
            {'_id': user['_id']},
            {'$set': {
                'delivery_name': new_name,
                'delivery_location': new_location,
                'delivery_pincode': new_pincode
            }}
        )

        user = db.users.find_one({'_id': user['_id']})
        session['current_user'] = {
            'username': user['username'],
            'email': user['email'],
            'delivery_name': user.get('delivery_name', ''),
            'delivery_location': user.get('delivery_location', ''),
            'delivery_pincode': user.get('delivery_pincode', '')
        }
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile'))

    return render_template('profile.html', current_user=user)

@user_bp.route('/logout')
def logout():
    session.pop('current_user', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))
