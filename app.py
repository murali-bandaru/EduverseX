
# Full CSV-backed Education Finder app (copy-paste)
import os
import csv
import json
import random
import string
import base64
from io import BytesIO
from datetime import datetime, date, timedelta

from flask import (Flask, render_template, request, redirect, url_for, flash,
                   session, send_from_directory, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- App setup ---
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET', 'edu-finder-secret-123')

# data directory
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# CSV file paths
USERS_CSV = os.path.join(DATA_DIR, 'users.csv')
INSTITUTIONS_CSV = os.path.join(DATA_DIR, 'institutions.csv')
RESOURCES_CSV = os.path.join(DATA_DIR, 'resources.csv')
BLOGS_CSV = os.path.join(DATA_DIR, 'blogs.csv')
PROJECTS_CSV = os.path.join(DATA_DIR, 'projects.csv')
ACHIEVEMENTS_CSV = os.path.join(DATA_DIR, 'achievements.csv')
FAQS_CSV = os.path.join(DATA_DIR, 'faqs.csv')
COURSES_CSV = os.path.join(DATA_DIR, 'courses.csv')
HACKATHONS_CSV = os.path.join(DATA_DIR, 'hackathons.csv')
INTERNSHIPS_CSV = os.path.join(DATA_DIR, 'internships.csv')
SCHOLARSHIPS_CSV = os.path.join(DATA_DIR, 'scholarships.csv')
CODING_CSV = os.path.join(DATA_DIR, 'coding_practice.csv')
RESOURCES_EXTRA_CSV = os.path.join(DATA_DIR, 'resources.csv')  # same as RESOURCES_CSV

# ensure CSVs exist with headers
def ensure_csv(path, headers):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=headers)
        df.to_csv(path, index=False)

ensure_csv(USERS_CSV, ['id','name','email','password_hash','created_at'])
ensure_csv(INSTITUTIONS_CSV, ['id','institution','city','country','program','level','duration_months','tuition_usd','ranking','website'])
ensure_csv(RESOURCES_CSV, ['id','category','title','link','description'])
ensure_csv(BLOGS_CSV, ['title','author','content','link',])
ensure_csv(PROJECTS_CSV, ['title','description','link'])
ensure_csv(ACHIEVEMENTS_CSV, ['user_email','points','badges','last_checkin','streak'])
ensure_csv(FAQS_CSV, ['question','answer'])
ensure_csv(COURSES_CSV, ['Course','Platform','Link','Description'])
ensure_csv(HACKATHONS_CSV, ['Hackathon','Organizer','Link','Deadline'])
ensure_csv(INTERNSHIPS_CSV, ['Company','Role','Link','Duration'])
ensure_csv(SCHOLARSHIPS_CSV, ['Scholarship','Provider','Link','Eligibility'])
ensure_csv(CODING_CSV, ['Platform','Link','Focus'])

# small id generator
def next_id(csv_path):
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            return 1
        return int(df.iloc[:,0].max()) + 1
    except Exception:
        # fallback: count lines
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return max(1, len(lines))

# user helpers
def find_user_by_email(email):
    df = pd.read_csv(USERS_CSV)
    df = df.fillna('')
    row = df[df['email'].str.lower() == email.lower()]
    if row.empty:
        return None
    return row.iloc[0].to_dict()

def add_user(name, email, password):
    if find_user_by_email(email):
        return False, "Email already registered"

    user_id = next_id(USERS_CSV)
    pw_hash = generate_password_hash(password)
    created_at = datetime.utcnow().isoformat()

    df = pd.read_csv(USERS_CSV)
    new_row = pd.DataFrame([{
        'id': user_id,
        'name': name,
        'email': email,
        'password_hash': pw_hash,
        'created_at': created_at
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USERS_CSV, index=False)

    # create achievement row
    ach_df = pd.read_csv(ACHIEVEMENTS_CSV)
    new_ach = pd.DataFrame([{
        'user_email': email,
        'points': 0,
        'badges': '[]',
        'last_checkin': '',
        'streak': 0
    }])
    ach_df = pd.concat([ach_df, new_ach], ignore_index=True)
    ach_df.to_csv(ACHIEVEMENTS_CSV, index=False)

    return True, "Registered"


# seed sample data if empty
def seed_sample_data():
    # Institutions
    df = pd.read_csv(INSTITUTIONS_CSV)
    if df.empty:
        rows = [
            {'id':1,'institution':'Massachusetts Institute of Technology (MIT)','city':'Cambridge','country':'USA','program':'Computer Science','level':'Bachelors','duration_months':48,'tuition_usd':55000,'ranking':1,'website':'https://www.mit.edu'},
            {'id':2,'institution':'Stanford University','city':'Stanford','country':'USA','program':'Artificial Intelligence','level':'Masters','duration_months':24,'tuition_usd':60000,'ranking':2,'website':'https://www.stanford.edu'},
            {'id':3,'institution':'IIT Bombay','city':'Mumbai','country':'India','program':'Computer Science','level':'Bachelors','duration_months':48,'tuition_usd':3000,'ranking':3,'website':'https://www.iitb.ac.in'},
            {'id':4,'institution':'University of Oxford','city':'Oxford','country':'UK','program':'Data Science','level':'Masters','duration_months':12,'tuition_usd':45000,'ranking':4,'website':'https://www.ox.ac.uk'},
            {'id':5,'institution':'National University of Singapore','city':'Singapore','country':'Singapore','program':'Software Engineering','level':'Bachelors','duration_months':48,'tuition_usd':20000,'ranking':5,'website':'https://www.nus.edu.sg'},
        ]
        pd.DataFrame(rows).to_csv(INSTITUTIONS_CSV, index=False)

    # Resources
    rdf = pd.read_csv(RESOURCES_CSV)
    if rdf.empty:
        resources = [
            {'id':1,'category':'Courses','title':'Coursera - Machine Learning (Andrew Ng)','link':'https://www.coursera.org/learn/machine-learning','description':'Classic ML course.'},
            {'id':2,'category':'Courses','title':'AWS Skill Builder','link':'https://skillbuilder.aws/','description':'AWS free and paid courses.'},
            {'id':3,'category':'Hackathons','title':'Devpost','link':'https://devpost.com','description':'Global hackathon platform.'},
            {'id':4,'category':'Internships','title':'Internshala','link':'https://internshala.com','description':'Indian internships platform.'},
            {'id':5,'category':'Coding','title':'LeetCode','link':'https://leetcode.com','description':'Coding interview practice.'},
        ]
        pd.DataFrame(resources).to_csv(RESOURCES_CSV, index=False)

    # FAQs
    faqdf = pd.read_csv(FAQS_CSV)
    if faqdf.empty:
        faqs = [
            {'question':'How to apply for a course?','answer':'Check the program link and follow application instructions.'},
            {'question':'Can I submit a blog?','answer':'Yes — go to Write Blog and submit. Admin approval simulated.'}
        ]
        pd.DataFrame(faqs).to_csv(FAQS_CSV, index=False)

    # Courses
    cdf = pd.read_csv(COURSES_CSV)
    if cdf.empty:
        courses = [
            {'Course':'Python for Beginners','Platform':'Coursera','Link':'https://www.coursera.org/learn/python','Description':'Learn Python basics and data structures.'},
            {'Course':'AWS Skill Builder','Platform':'AWS','Link':'https://skillbuilder.aws/','Description':'Cloud and AWS fundamentals.'},
            {'Course':'Machine Learning','Platform':'Stanford/ Coursera','Link':'https://www.coursera.org/learn/machine-learning','Description':'Andrew Ng ML course.'},
        ]
        pd.DataFrame(courses).to_csv(COURSES_CSV, index=False)

@app.route('/profile')
def profile():
    # Default values (if user session not set)
    user_name = session.get('user_name', 'Student')
    user_email = session.get('user_email', 'student@eduversex.com')
    
    # Example static data (can later come from DB)
    join_date = "October 2025"
    user_points = 125
    achievements_count = 4

    return render_template(
        'profile.html',
        join_date=join_date,
        user_points=user_points,
        achievements_count=achievements_count
    )

    # Hackathons
    hdf = pd.read_csv(HACKATHONS_CSV)
    if hdf.empty:
        hackathons = [
            {'Hackathon':'Smart India Hackathon','Organizer':'Govt. of India','Link':'https://www.sih.gov.in','Deadline':'2025-12-15'},
            {'Hackathon':'Devpost Global','Organizer':'Devpost','Link':'https://devpost.com','Deadline':'2026-01-15'},
        ]
        pd.DataFrame(hackathons).to_csv(HACKATHONS_CSV, index=False)

    # Internships
    idf = pd.read_csv(INTERNSHIPS_CSV)
    if idf.empty:
        internships = [
            {'Company':'Google','Role':'Software Engineering Intern','Link':'https://careers.google.com/students','Duration':'3 Months'},
            {'Company':'Microsoft','Role':'AI Research Intern','Link':'https://careers.microsoft.com','Duration':'6 Months'},
        ]
        pd.DataFrame(internships).to_csv(INTERNSHIPS_CSV, index=False)

    # Scholarships
    sdf = pd.read_csv(SCHOLARSHIPS_CSV)
    if sdf.empty:
        scholarships = [
            {'Scholarship':'AICTE Pragati Scholarship','Provider':'AICTE','Link':'https://www.aicte-india.org','Eligibility':'Girl Students in Technical Education'},
            {'Scholarship':'Google India Scholarship','Provider':'Google','Link':'https://buildyourfuture.withgoogle.com','Eligibility':'Students in Tech Fields'},
        ]
        pd.DataFrame(scholarships).to_csv(SCHOLARSHIPS_CSV, index=False)

    # Coding practice
    codf = pd.read_csv(CODING_CSV)
    if codf.empty:
        coding = [
            {'Platform':'LeetCode','Link':'https://leetcode.com','Focus':'Algorithms & Data Structures'},
            {'Platform':'HackerRank','Link':'https://www.hackerrank.com','Focus':'Programming Practice'},
        ]
        pd.DataFrame(coding).to_csv(CODING_CSV, index=False)

    # Blogs & Projects & Achievements ensure headers but empty
    ensure_csv(BLOGS_CSV, ['title','author','content',''])
    ensure_csv(PROJECTS_CSV, ['title','description','link'])
    ensure_csv(ACHIEVEMENTS_CSV, ['user_email','points','badges','last_checkin','streak'])

seed_sample_data()

# --- helper to load CSV to records ---
def load_csv_records(path):
    try:
        df = pd.read_csv(path)
        df = df.fillna('')
        return df.to_dict(orient='records')
    except Exception:
        return []

# --- routes ---
@app.route('/')
def index():
    institutions = load_csv_records(INSTITUTIONS_CSV)
    featured = sorted(institutions, key=lambda r: int(r.get('ranking') or 999))[:6]
    # chart: avg tuition by country top 5
    chart_b64 = None
    try:
        df = pd.read_csv(INSTITUTIONS_CSV)
        if not df.empty:
            agg = df.groupby('country')['tuition_usd'].mean().nlargest(5)
            fig, ax = plt.subplots(figsize=(6,3))
            ax.bar(agg.index, agg.values)
            ax.set_title('Top 5 Countries by Avg Tuition (USD)')
            plt.xticks(rotation=30)
            buf = BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format='png')
            buf.seek(0)
            chart_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)
    except Exception:
        chart_b64 = None
    return render_template('index.html', featured=featured, chart=chart_b64)

# auth
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if not name or not email or not password:
            flash('Please fill all fields')
            return redirect(url_for('register'))
        ok, msg = add_user(name, email, password)
        if not ok:
            flash(msg)
            return redirect(url_for('register'))
        session['user_email'] = email
        session['user_name'] = name
        flash('Registered and logged in.')
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user = find_user_by_email(email)
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid credentials')
            return redirect(url_for('login'))
        session['user_email'] = user['email']
        session['user_name'] = user['name']
        flash('Logged in.')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('index'))

# institutions listing/search/details
@app.route('/institutions')
def institutions():
    q = request.args.get('q','').strip()
    country = request.args.get('country','').strip()
    level = request.args.get('level','').strip()
    budget = request.args.get('budget', type=float)
    df = pd.read_csv(INSTITUTIONS_CSV)
    if not df.empty:
        if q:
            df = df[df.apply(lambda r: q.lower() in str(r['program']).lower() or q.lower() in str(r['institution']).lower(), axis=1)]
        if country:
            df = df[df['country'].str.contains(country, case=False, na=False)]
        if level:
            df = df[df['level'].str.contains(level, case=False, na=False)]
        if budget is not None:
            df = df[df['tuition_usd'] <= budget]
    results = df.sort_values('ranking').to_dict(orient='records') if not df.empty else []
    return render_template('institutions.html', results=results, q=q)

@app.route('/details/<int:inst_id>')
def details(inst_id):
    df = pd.read_csv(INSTITUTIONS_CSV)
    row = df[df['id']==inst_id]
    if row.empty:
        flash('Institution not found.')
        return redirect(url_for('institutions'))
    inst = row.iloc[0].to_dict()
    return render_template('details.html', inst=inst)

# resources & categories
@app.route('/resources')
def resources():
    resources = load_csv_records(RESOURCES_CSV)
    return render_template('resources.html', resources=resources)

@app.route('/courses')
def courses():
    courses = load_csv_records(COURSES_CSV)
    return render_template('courses.html', courses=courses)

@app.route('/hackathons')
def hackathons():
    hackathons = load_csv_records(HACKATHONS_CSV)
    return render_template('hackathons.html', hackathons=hackathons)

@app.route('/internships')
def internships():
    internships = load_csv_records(INTERNSHIPS_CSV)
    return render_template('internships.html', internships=internships)

@app.route('/scholarships')
def scholarships():
    scholarships = load_csv_records(SCHOLARSHIPS_CSV)
    return render_template('scholarships.html', scholarships=scholarships)

@app.route('/coding_practice')
def coding_practice():
    coding = load_csv_records(CODING_CSV)
    return render_template('coding_practice.html', coding=coding)

# blogs
@app.route('/blogs')
def blogs():
    blogs = load_csv_records(BLOGS_CSV)
    
    
    return render_template('blogs.html', blogs=blogs)

@app.route('/write_blog', methods=['GET','POST'])
def write_blog():
    if 'user_email' not in session:
        flash('Login to submit a blog.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        content = request.form.get('content','').strip()
        if not title or not content:
            flash('Fill title and content.')
            return redirect(url_for('write_blog'))
        bid = next_id(BLOGS_CSV)
        created = datetime.utcnow().isoformat()
        df = pd.read_csv(BLOGS_CSV)
        df = df.append({'id':bid,'user_email':session['user_email'],'title':title,'content':content,'created_at':created,'status':'Pending'}, ignore_index=True)
        df.to_csv(BLOGS_CSV, index=False)
        flash('Blog submitted for review (simulated). You will get points if approved.')
        return redirect(url_for('blogs'))
    return render_template('write_blog.html')

# projects
@app.route('/projects')
def projects():
    projects = load_csv_records(PROJECTS_CSV)
    
    return render_template('projects.html', projects=projects)

@app.route('/submit_project', methods=['GET','POST'])
def submit_project():
    if 'user_email' not in session:
        flash('Login to submit a project.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        github = request.form.get('github','').strip()
        demo = request.form.get('demo','').strip()
        if not title or not description:
            flash('Fill title and description.')
            return redirect(url_for('submit_project'))
        pid = next_id(PROJECTS_CSV)
        created = datetime.utcnow().isoformat()
        df = pd.read_csv(PROJECTS_CSV)
        df = df.append({'id':pid,'user_email':session['user_email'],'title':title,'description':description,'github_link':github,'demo_link':demo,'created_at':created,'status':'Pending'}, ignore_index=True)
        df.to_csv(PROJECTS_CSV, index=False)
        flash('Project submitted for review (simulated).')
        return redirect(url_for('projects'))
    return render_template('submit_project.html')

# achievements & daily check-in (CSV-backed)
@app.route('/achievements')
def achievements():
    if 'user_email' not in session:
        flash('Login to view achievements.')
        return redirect(url_for('login'))
    df = pd.read_csv(ACHIEVEMENTS_CSV)
    row = df[df['user_email']==session['user_email']]
    if row.empty:
        df = df.append({'user_email':session['user_email'],'points':0,'badges':'[]','last_checkin':'','streak':0}, ignore_index=True)
        df.to_csv(ACHIEVEMENTS_CSV, index=False)
        row = df[df['user_email']==session['user_email']]
    ach = row.iloc[0].to_dict()
    try:
        badges = json.loads(ach['badges'])
    except Exception:
        badges = []
    return render_template('achievements.html', ach=ach, badges=badges)

@app.route('/daily_checkin', methods=['POST'])
def daily_checkin():
    if 'user_email' not in session:
        return jsonify({'status':'login_required'}), 401
    df = pd.read_csv(ACHIEVEMENTS_CSV)
    idx = df.index[df['user_email']==session['user_email']].tolist()
    if not idx:
        df = df.append({'user_email':session['user_email'],'points':0,'badges':'[]','last_checkin':'','streak':0}, ignore_index=True)
        df.to_csv(ACHIEVEMENTS_CSV, index=False)
        idx = df.index[df['user_email']==session['user_email']].tolist()
    i = idx[0]
    today_str = date.today().isoformat()
    last = df.at[i,'last_checkin']
    streak = int(df.at[i,'streak'] or 0)
    points = int(df.at[i,'points'] or 0)
    if last == today_str:
        return jsonify({'status':'already','points':points,'streak':streak})
    if last:
        try:
            last_date = date.fromisoformat(last)
            if last_date == date.today() - timedelta(days=1):
                streak += 1
            else:
                streak = 1
        except:
            streak = 1
    else:
        streak = 1
    points += 10
    df.at[i,'last_checkin'] = today_str
    df.at[i,'streak'] = streak
    df.at[i,'points'] = points
    try:
        badges = json.loads(df.at[i,'badges'])
    except:
        badges = []
    if points >= 100 and "Century Learner" not in badges:
        badges.append("Century Learner")
    if streak >= 7 and "Weekly Streak" not in badges:
        badges.append("Weekly Streak")
    df.at[i,'badges'] = json.dumps(badges)
    df.to_csv(ACHIEVEMENTS_CSV, index=False)
    return jsonify({'status':'ok','points':points,'streak':streak,'badges':badges})

# faqs, about, contact
@app.route('/faqs')
def faqs():
    faqs = load_csv_records(FAQS_CSV)
    return render_template('faqs.html', faqs=faqs)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method=='POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        message = request.form.get('message','').strip()
        flash(f'Thank you {name}, we received your message.')
        return redirect(url_for('index'))
    return render_template('contact.html')

# dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        flash('Login to access dashboard.')
        return redirect(url_for('login'))
    # stats
    users = pd.read_csv(USERS_CSV)
    total_users = len(users)
    resources = pd.read_csv(RESOURCES_CSV)
    categories = resources['category'].value_counts().to_dict() if not resources.empty else {}
    users['created_at'] = pd.to_datetime(users['created_at'], errors='coerce')
    if users['created_at'].notna().any():
        users['date'] = users['created_at'].dt.date
        daily = users.groupby('date').size()
    else:
        daily = pd.Series(dtype=int)
    chart = None
    if not daily.empty:
        fig, ax = plt.subplots(figsize=(6,3))
        daily.plot(ax=ax, marker='o')
        ax.set_title('Daily Registrations')
        plt.xticks(rotation=30)
        buf = BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format='png')
        buf.seek(0)
        chart = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)
    # my points
    ach = pd.read_csv(ACHIEVEMENTS_CSV)
    my_ach = ach[ach['user_email']==session['user_email']]
    my_points = int(my_ach.iloc[0]['points']) if not my_ach.empty else 0
    return render_template('dashboard.html', total_users=total_users, categories=categories, chart=chart, my_points=my_points)

# static files route
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path,'static'), filename)

if __name__ == '__main__':
    app.run(debug=True)
