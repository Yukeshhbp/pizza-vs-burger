import hashlib
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, login_manager
from models import User, Vote, ResponseHistory
from gemini_agent import generate_funny_response
import logging

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_default_users():
    """Create 2-3 default users if they don't exist"""
    default_users = [
        {'username': 'foodie_mike', 'password': 'pizza123'},
        {'username': 'hungry_sarah', 'password': 'burger456'},
        {'username': 'taste_tester', 'password': 'food789'}
    ]
    
    for user_data in default_users:
        existing_user = User.query.filter_by(username=user_data['username']).first()
        if not existing_user:
            user = User(username=user_data['username'])
            user.set_password(user_data['password'])
            db.session.add(user)
    
    try:
        db.session.commit()
        logging.info("Default users created successfully")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating default users: {e}")

# Create default users on app startup
with app.app_context():
    create_default_users()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('vote'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('vote'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('vote'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/vote', methods=['GET', 'POST'])
@login_required
def vote():
    if request.method == 'POST':
        food_type = request.form['food_type']
        vote_id = request.form['vote_id'].strip()
        
        if not vote_id:
            flash('Please enter a vote ID', 'error')
            return redirect(url_for('vote'))
        
        if food_type not in ['pizza', 'burger']:
            flash('Invalid food type', 'error')
            return redirect(url_for('vote'))
        
        try:
            # Generate unique funny response from Gemini
            response_text = generate_funny_response(current_user.username, food_type, vote_id)
            
            # Create and save the vote
            new_vote = Vote(
                user_id=current_user.id,
                food_type=food_type,
                vote_id=vote_id,
                gemini_response=response_text
            )
            db.session.add(new_vote)
            db.session.commit()
            
            flash(f'Vote cast successfully! {response_text}', 'success')
            logging.info(f"Vote cast by {current_user.username} for {food_type} with ID {vote_id}")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error casting vote: {e}")
            flash('Error casting vote. Please try again.', 'error')
        
        return redirect(url_for('vote'))
    
    # Get vote counts
    pizza_count = Vote.query.filter_by(food_type='pizza').count()
    burger_count = Vote.query.filter_by(food_type='burger').count()
    
    # Get recent votes for display (limited to 3)
    recent_votes = Vote.query.order_by(Vote.timestamp.desc()).limit(3).all()
    
    return render_template('vote.html', 
                         pizza_count=pizza_count, 
                         burger_count=burger_count,
                         recent_votes=recent_votes)

@app.route('/api/vote', methods=['POST'])
@login_required
def api_vote():
    """API endpoint for casting votes via AJAX"""
    try:
        food_type = request.form.get('food_type')
        vote_id = request.form.get('vote_id', '').strip()
        
        if not vote_id:
            return jsonify({'success': False, 'error': 'Please enter a vote ID'}), 400
        
        if food_type not in ['pizza', 'burger']:
            return jsonify({'success': False, 'error': 'Invalid food type'}), 400
        
        # Generate unique funny response from Gemini
        response_text = generate_funny_response(current_user.username, food_type)
        
        # Create and save the vote
        new_vote = Vote(
            user_id=current_user.id,
            food_type=food_type,
            vote_id=vote_id,
            gemini_response=response_text
        )
        db.session.add(new_vote)
        db.session.commit()
        
        logging.info(f"Vote cast by {current_user.username} for {food_type} with ID {vote_id}")
        
        # Get updated counts
        pizza_count = Vote.query.filter_by(food_type='pizza').count()
        burger_count = Vote.query.filter_by(food_type='burger').count()
        
        return jsonify({
            'success': True,
            'message': response_text,
            'pizza_count': pizza_count,
            'burger_count': burger_count
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error casting vote: {e}")
        return jsonify({'success': False, 'error': 'Error casting vote. Please try again.'}), 500

@app.route('/api/vote-counts')
@login_required
def get_vote_counts():
    """API endpoint for real-time vote count updates"""
    pizza_count = Vote.query.filter_by(food_type='pizza').count()
    burger_count = Vote.query.filter_by(food_type='burger').count()
    
    return jsonify({
        'pizza': pizza_count,
        'burger': burger_count
    })

@app.route('/api/more-votes')
@login_required
def get_more_votes():
    """API endpoint for loading more votes with pagination"""
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 5, type=int)
        
        votes = Vote.query.order_by(Vote.timestamp.desc()).offset(offset).limit(limit).all()
        
        votes_data = []
        for vote in votes:
            votes_data.append({
                'id': vote.id,
                'username': vote.voter.username,
                'food_type': vote.food_type,
                'vote_id': vote.vote_id,
                'timestamp': vote.timestamp.strftime('%m/%d %H:%M'),
                'gemini_response': vote.gemini_response
            })
        
        return jsonify({
            'success': True,
            'votes': votes_data,
            'has_more': len(votes) == limit
        })
        
    except Exception as e:
        logging.error(f"Error loading more votes: {e}")
        return jsonify({'success': False, 'error': 'Error loading votes'}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
