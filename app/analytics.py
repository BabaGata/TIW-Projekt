import re
import os
import pandas as pd
from flask import current_app
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest

def normalize_url(url: str) -> str:
    if url in ["Direct", ""]:
        return "Direct"
    return re.sub(r'^https?://[^/]+', '', url)

def normalize_event_for_agg(url: str) -> str:
    url = normalize_url(url)
    return re.sub(r'^/event/\d+$', '/event/all', url)

def get_analytics_data(credentials):
    property_id = current_app.config["PROPERTY_ID"]

    client = BetaAnalyticsDataClient(credentials=credentials)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration")
        ],
        dimensions=[
            Dimension(name="pagePath"),
            Dimension(name="country"),
            Dimension(name="deviceCategory")
        ],
    )

    response = client.run_report(request)
    data = [
        [d.value for d in row.dimension_values] + [m.value for m in row.metric_values]
        for row in response.rows
    ]
    df = pd.DataFrame(
        data,
        columns=["PagePath", "Country", "DeviceCategory", "ActiveUsers", "PageViews", "AvgSessionDuration"]
    )

    request_transitions = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="pagePath"), Dimension(name="pageReferrer")],
        metrics=[Metric(name="screenPageViews")]
    )

    response_transitions = client.run_report(request_transitions)

    transitions = [
        {
            "from": row.dimension_values[1].value or "Direct",
            "to": row.dimension_values[0].value,
            "value": int(row.metric_values[0].value)
        }
        for row in response_transitions.rows
    ]
    df_transitions = pd.DataFrame(transitions)

    df_transitions["from"] = df_transitions["from"].apply(normalize_url)
    df_transitions["to"] = df_transitions["to"].apply(normalize_url)
    df_transitions = df_transitions[
        (df_transitions["from"] != "Direct") & (df_transitions["to"] != "Direct")
    ]

    df_aggregated_transitions = df_transitions.copy()
    df_aggregated_transitions["from"] = df_aggregated_transitions["from"].apply(normalize_event_for_agg)
    df_aggregated_transitions["to"] = df_aggregated_transitions["to"].apply(normalize_event_for_agg)

    df_aggregated_transitions = (
        df_aggregated_transitions
        .groupby(["from", "to"], as_index=False)
        .agg({"value": "sum"})
        .sort_values("value", ascending=False)
    )

    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    df.to_csv(os.path.join(output_dir, "analytics_pages.csv"), index=False)
    df_transitions.to_csv(os.path.join(output_dir, "analytics_transitions.csv"), index=False)   # normalized, raw events
    df_aggregated_transitions.to_csv(os.path.join(output_dir, "analytics_transitions_aggregated.csv"), index=False)  # aggregated

    return df, df_aggregated_transitions