from __future__ import annotations

from flask import Flask, render_template, request

from recommender import recommend_courses
from generate_plan import generate_4_year_plan
from utils import load_courses

app = Flask(__name__)


@app.route("/")
def index():
    df = load_courses()
    courses = (
        df[["course_id", "course_name"]].drop_duplicates().to_dict(orient="records")
    )
    return render_template(
        "index.html", courses=sorted(courses, key=lambda x: x["course_id"])
    )


@app.route("/recommend", methods=["POST"])
def recommend():
    track = request.form.get("track")
    completed_courses = request.form.getlist("completed_courses")
    recommendations, locked = recommend_courses(track, completed_courses)
    return render_template(
        "results.html", recommendations=recommendations, locked=locked
    )


@app.route("/plan", methods=["POST"])
def plan():
    track = request.form.get("track")
    completed_courses = request.form.getlist("completed_courses")
    max_credits = request.form.get("max_credits", type=int, default=18)
    plan = generate_4_year_plan(track, completed_courses, max_credits)

    df = load_courses()
    total = df["units"].astype(int).sum()
    completed_df = df[df["course_id"].isin(completed_courses)]
    completed = completed_df["units"].astype(int).sum()
    stats = {"completed": int(completed), "total": int(total)}

    return render_template("plan.html", plan=plan, stats=stats)


if __name__ == "__main__":
    app.run(debug=True)
