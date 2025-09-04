# app/analytics.py
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest
from google.oauth2 import service_account
import pandas as pd
from flask import current_app

def get_analytics_data():
    creds_file = current_app.config["SERVICE_ACCOUNT_FILE"]
    property_id = current_app.config["PROPERTY_ID"]

    credentials = service_account.Credentials.from_service_account_file(creds_file)
    client = BetaAnalyticsDataClient(credentials=credentials)

    # Request multiple metrics & dimensions
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

    # Convert to dataframe
    data = []
    for row in response.rows:
        data.append([d.value for d in row.dimension_values] +
                    [m.value for m in row.metric_values])

    if not data:
        print("No GA data returned. Check GA4 property & events.")

    df = pd.DataFrame(
        data,
        columns=["PagePath", "Country", "DeviceCategory",
                 "ActiveUsers", "PageViews", "AvgSessionDuration"]
    )

    # Save for later
    df.to_csv("data/analytics_data.csv", index=False)
    return df