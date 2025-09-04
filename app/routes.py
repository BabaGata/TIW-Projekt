import json
import os
from flask import render_template, request, redirect, url_for, Blueprint
from app.analytics import get_analytics_data
from app.recommendation import recommendation_system, recommend_events
from datetime import datetime

bp = Blueprint("main", __name__)

DATA_FILE = os.path.join("data", "events.json")

def load_events():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_events(events):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

@bp.route("/")
def index():
    events = load_events()
    # sort by date (ascending, soonest first)
    events.sort(key=lambda e: datetime.strptime(e["date"], "%Y-%m-%d"))
    return render_template("index.html", events=events)

@bp.route("/event/<int:event_id>")
def event_detail(event_id):
    events = load_events()
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        return "Event not found", 404
    return render_template("event.html", event=event)

@bp.route("/like/<int:event_id>", methods=["POST"])
def like_event(event_id):
    events = load_events()
    for e in events:
        if e["id"] == event_id:
            e["likes"] += 1
            break
    save_events(events)
    return redirect(url_for("main.index"))

@bp.route("/dislike/<int:event_id>", methods=["POST"])
def dislike_event(event_id):
    events = load_events()
    for e in events:
        if e["id"] == event_id:
            e["dislikes"] += 1
            break
    save_events(events)
    return redirect(url_for("main.index"))

@bp.route("/recommendations")
def recommendations():
    events = load_events()
    recs = recommend_events(events)
    return render_template("recommendations.html", events=recs)

@bp.route("/map")
def event_map():
    events = load_events()
    return render_template("map.html", events=events)

@bp.route("/analytics")
def analytics_view():
    df = get_analytics_data()
    recommendations = recommendation_system(df)
    df_html = df.to_html(classes="table table-striped", index=False)
    df_json = df.to_dict(orient="records")  # <-- add this
    return render_template(
        "analytics.html",
        df=df_html,
        df_json=df_json,
        recommendations=recommendations
    )