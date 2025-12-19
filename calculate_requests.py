#!/usr/bin/env python3
"""
Calculate total available requests with current API keys
"""

# Your API key configuration
total_api_keys = 13
models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
total_models = len(models)

# Free tier limits
requests_per_day_per_model = 20
requests_per_day_per_key = requests_per_day_per_model * total_models

print("🔑 API Key Request Calculation")
print("=" * 50)
print(f"📊 Total API Keys: {total_api_keys}")
print(f"🤖 Models in rotation: {total_models}")
print(f"   - {models}")
print(f"📈 Free tier limit: {requests_per_day_per_model} requests/day/model")
print()

print("📋 Breakdown:")
print(f"   • Requests per key per model: {requests_per_day_per_model}")
print(f"   • Requests per key (all models): {requests_per_day_per_key}")
print(f"   • Total requests per day: {total_api_keys} × {requests_per_day_per_key} = {total_api_keys * requests_per_day_per_key}")
print()

# Your script generates both review and rating for each row
requests_per_row = 2  # 1 for review + 1 for rating
total_daily_requests = total_api_keys * requests_per_day_per_key
max_rows_per_day = total_daily_requests // requests_per_row

print("🎯 For Your Use Case:")
print(f"   • Requests per row: {requests_per_row} (review + rating)")
print(f"   • Maximum rows per day: {max_rows_per_day}")
print(f"   • Total daily requests available: {total_daily_requests}")
print()

# Calculate for different scenarios
print("📈 Scaling Scenarios:")
scenarios = [100, 500, 1000, 2000, 5000]
for rows in scenarios:
    requests_needed = rows * requests_per_row
    days_needed = (requests_needed + total_daily_requests - 1) // total_daily_requests  # Ceiling division
    print(f"   • {rows:,} rows = {requests_needed:,} requests = {days_needed} day(s)")

print()
print("⚠️  Note: This assumes all API keys are valid and active.")
print("   From the test, some keys appear to be invalid or expired.")