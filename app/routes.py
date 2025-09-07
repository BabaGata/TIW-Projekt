import json
import os
import pandas as pd
from datetime import datetime

from flask import current_app, render_template, request, redirect, url_for, Blueprint, session

from app.analytics import get_analytics_data
from app.recommendation import recommend_events

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

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
    events.sort(key=lambda e: datetime.strptime(e["date"], "%Y-%m-%d"))
    return render_template("index.html", events=events)

@bp.route("/event/<int:event_id>")
def event_detail(event_id):
    events = load_events()
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        return "Event not found", 404
    return render_template("event.html", event=event)

@bp.route("/clear_likes")
def clear_likes():
    session.pop("user_likes", None)
    return redirect(url_for("main.index"))

@bp.route("/like/<int:event_id>", methods=["POST"])
def like_event(event_id):
    events = load_events()
    for e in events:
        if e["id"] == event_id:
            e["likes"] += 1
            break
    save_events(events)

    user_likes = session.get("user_likes", [])
    if str(event_id) not in user_likes:
        user_likes.append(str(event_id))
    session["user_likes"] = user_likes
    print("Session user_likes:", session.get("user_likes"))

    return redirect(url_for("main.index"))


@bp.route("/dislike/<int:event_id>", methods=["POST"])
def dislike_event(event_id):
    events = load_events()
    for e in events:
        if e["id"] == event_id:
            e["dislikes"] += 1
            break
    save_events(events)

    user_dislikes = session.get("user_dislikes", [])
    if str(event_id) not in user_dislikes:
        user_dislikes.append(event_id)
    session["user_dislikes"] = user_dislikes

    return redirect(url_for("main.index"))

@bp.route("/recommendations")
def recommendations():
    events = load_events()
    user_likes = [int(x) for x in session.get("user_likes", [])]
    
    print("Session user_likes:", session.get("user_likes"))
    recs = recommend_events(events, user_likes=user_likes)
    return render_template("recommendations.html", events=recs)

@bp.route("/map")
def event_map():
    events = load_events()
    return render_template("map.html", events=events)

@bp.route("/authorize")
def authorize():
    client_secret_file = current_app.config["CLIENT_SECRET"]
    SCOPES = current_app.config["SCOPES"]
    REDIRECT_URI = current_app.config["REDIRECT_URI"]

    flow = Flow.from_client_secrets_file(
        client_secret_file,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"    
    )
    session["state"] = state
    return redirect(authorization_url)


@bp.route("/oauth2callback")
def oauth2callback():
    client_secret_file = current_app.config["CLIENT_SECRET"]
    SCOPES = current_app.config["SCOPES"]
    REDIRECT_URI = current_app.config["REDIRECT_URI"]

    state = session["state"]
    flow = Flow.from_client_secrets_file(
        client_secret_file,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    return redirect(url_for("main.analytics_view"))

@bp.route("/analytics")
def analytics_view():
    if "credentials" not in session:
        return redirect(url_for("main.authorize"))

    creds = Credentials(**session["credentials"])

    if creds.expired:
        if creds.refresh_token:
            creds.refresh(Request())
            session["credentials"] = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes
            }
        else:
            return redirect(url_for("main.authorize"))

    df, df_transitions_aggregated = get_analytics_data(creds)

    for col in ["PageViews", "ActiveUsers", "AvgSessionDuration"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    page_activity = (
        df.groupby("PagePath", as_index=False)[["PageViews", "ActiveUsers"]]
        .sum()
    )
    total_page_activity = page_activity.drop(columns=["ActiveUsers"]).sort_values("PageViews", ascending=False).head(6)
    page_activity["PageViewsPerUser"] = page_activity.apply(
        lambda row: row["PageViews"] / row["ActiveUsers"] if row["ActiveUsers"] > 0 else 0,
        axis=1
    )
    avg_page_activity = (
        page_activity[["PagePath", "PageViewsPerUser"]]
        .sort_values("PageViewsPerUser", ascending=False)
        .head(6)
        .rename(columns={"PageViewsPerUser": "PageViews"})  # keep same key name for template
    )
    avg_time_activity = (
        df.groupby("PagePath", as_index=False)["AvgSessionDuration"]
        .mean().sort_values("AvgSessionDuration", ascending=False).head(6)
    )
    country_summary = (
        df.groupby("Country", as_index=False)["ActiveUsers"]
        .sum().sort_values("ActiveUsers", ascending=False)
    )
    country_pageviews = (
        df.groupby("Country", as_index=False)["PageViews"]
        .sum().sort_values("PageViews", ascending=False)
    )

    df_html = (
        df.nlargest(8, "AvgSessionDuration")
        .to_html(classes="table table-striped text-start", index=False, justify="left")
    )

    return render_template(
        "analytics.html",
        df=df_html,
        total_page_activity=total_page_activity.to_dict(orient="records"),
        avg_page_activity=avg_page_activity.to_dict(orient="records"),
        avg_time_activity=avg_time_activity.to_dict(orient="records"),
        country_summary=country_summary.to_dict(orient="records"),
        country_pageviews=country_pageviews.to_dict(orient="records"),
        user_flow=df_transitions_aggregated.to_dict(orient="records"),
    )

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))