import streamlit as st
import boto3
import json
import requests
from botocore.exceptions import ClientError
import base64

# Function to get secret from AWS Secrets Manager
@st.cache_data
def get_secret(secret_name, region_name="us-east-1"):
    client = boto3.client('secretsmanager', region_name=region_name)
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise Exception(f"Unable to retrieve secret: {e}")

    if "SecretString" in response:
        secret = response["SecretString"]
        return json.loads(secret)
    else:
        decoded_binary_secret = base64.b64decode(response["SecretBinary"])  # type: ignore
        return json.loads(decoded_binary_secret)

# Function to format address nicely
def format_address(location):
    parts = [
        location.get("address"),
        location.get("locality"),
        location.get("region"),
        location.get("postcode"),
        location.get("country")
    ]
    return ", ".join(part for part in parts if part)

# Function to get user's location via IP
def get_my_location():
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        loc = data.get("loc")  # e.g., "53.344,-6.267"
        city = data.get("city")
        region = data.get("region")
        country = data.get("country")
        address = f"{city}, {region}, {country}"

        if loc:
            lat, lon = map(float, loc.split(","))
            return lat, lon, address
    except Exception as e:
        print("Error getting location:", e)
    return None, None, "Unknown Location"

# Function to search for gluten-free restaurants
def search_gluten_free_restaurants(lat, lon, api_key, radius=1000, limit=10):
    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": api_key
    }
    params = {
        "ll": f"{lat},{lon}",
        "query": "Gluten Free",
        "radius": radius,
        "limit": limit,
        "categories": "13065"  # Category for restaurants
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        st.error(f"Error: {response.status_code} - {response.text}")
        return []

    data = response.json()
    results = data.get("results", [])
    return [
        {
            "name": place["name"],
            "address": format_address(place["location"])
        }
        for place in results
    ]

# Streamlit App
def main():
    st.title("🍽️ Find Gluten-Free Restaurants Near You")

    with st.spinner('Determining your location...'):
        latitude, longitude, my_address = get_my_location()

    if not latitude:
        st.error("Could not determine your location. Please try again later.")
        return

    st.success(f"You're in: {my_address}")

    # Get Foursquare API key from AWS Secrets Manager
    with st.spinner('Retrieving API credentials...'):
        secrets = get_secret("swarm/api_key")
        swarm_api_key = secrets["api_key"]

    # Search for gluten-free restaurants
    with st.spinner('Searching for Gluten-Free restaurants nearby...'):
        restaurants = search_gluten_free_restaurants(latitude, longitude, swarm_api_key)

    if not restaurants:
        st.warning("No gluten-free restaurants found nearby.")
        return

    st.subheader(f"Nearby Gluten-Free Restaurants:")

    for r in restaurants:
        st.write(f"**{r['name']}**")
        st.write(f":round_pushpin: {r['address']}")
        st.markdown("---")

if __name__ == "__main__":
    main()
