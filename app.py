from flask import Flask, render_template, request
import pandas as pd
from recommender import recommend_courses
from generate_plan import generate_plan

app = Flask(__name__)

@app.route('/')
def index():
    df = pd.read_csv('data/towson_courses.csv')
    courses = df[['course_id', 'course_name']].drop_duplicates().to_dict(orient='records')
    return render_template('index.html', courses=sorted(courses, key=lambda x: x['course_id']))

@app.route('/recommend', methods=['POST'])
def recommend():
    track = request.form.get('track')
    completed_courses = request.form.getlist('completed_courses')
    recommendations = recommend_courses(track, completed_courses)
    return render_template('results.html', recommendations=recommendations)

@app.route('/plan', methods=['POST'])
def plan():
    track = request.form.get('track')
    completed_courses = request.form.getlist('completed_courses')
    max_credits = request.form.get('max_credits', type=int, default=16)
    plan, unscheduled = generate_plan(track, completed_courses, max_credits)
    return render_template('plan.html', plan=plan, unscheduled=unscheduled)

if __name__ == '__main__':
    app.run(debug=True)
