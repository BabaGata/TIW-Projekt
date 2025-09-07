import pandas as pd
import os

def load_analytics_data():
    """Load analytics data to get event popularity"""
    try:
        analytics_file = os.path.join("data", "analytics_pages.csv")
        df = pd.read_csv(analytics_file)
        
        event_views = {}
        for _, row in df.iterrows():
            path = row['PagePath']
            if path.startswith('/event/'):
                try:
                    event_id = int(path.split('/event/')[1])
                    page_views = row['PageViews']
                    if event_id in event_views:
                        event_views[event_id] += page_views
                    else:
                        event_views[event_id] = page_views
                except (ValueError, IndexError):
                    continue
        
        return event_views
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading analytics data: {e}")
        return {}

def recommend_events(events, user_likes=None, limit=5):
    if not events:
        return []

    if user_likes is None:
        user_likes = []

    event_popularity = load_analytics_data()
    
    liked_genres = set()
    for e in events:
        if e["id"] in user_likes:
            liked_genres.add(e.get("genre", "").lower())

    recommendations = []
    if liked_genres:
        genre_matches = [e for e in events if e.get("genre", "").lower() in liked_genres and e["id"] not in user_likes]
        
        genre_matches.sort(key=lambda e: (
            event_popularity.get(e["id"], 0),
            e.get("likes", 0)
        ), reverse=True)
        
        recommendations.extend(genre_matches)

    remaining_events = [e for e in events if e["id"] not in user_likes and e not in recommendations]
    
    remaining_events.sort(key=lambda e: (
        event_popularity.get(e["id"], 0),
        e.get("likes", 0)
    ), reverse=True)
    
    recommendations.extend(remaining_events)

    seen_ids = set()
    unique_recommendations = []
    for event in recommendations:
        if event["id"] not in seen_ids:
            seen_ids.add(event["id"])
            unique_recommendations.append(event)
    
    return unique_recommendations[:limit]