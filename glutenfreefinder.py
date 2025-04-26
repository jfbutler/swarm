import streamlit as st
import boto3
import json
import requests
import base64
import pandas as pd
import pydeck as pdk
from botocore.exceptions import ClientError

# -- Helper to get secret from AWS Secrets Manager
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

# -- Helper to search for gluten-free restaurants
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
            "address": format_address(place["location"]),
            "lat": place.get("geocodes", {}).get("main", {}).get("latitude"),
            "lon": place.get("geocodes", {}).get("main", {}).get("longitude"),
        }
        for place in results if place.get("geocodes", {}).get("main")
    ]

# -- Helper to format addresses nicely
def format_address(location):
    parts = [
        location.get("address"),
        location.get("locality"),
        location.get("region"),
        location.get("postcode"),
        location.get("country")
    ]
    return ", ".join(part for part in parts if part)

# -- Helper to get user's current location based on IP
def get_my_location():
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        loc = data.get("loc")  # e.g., "40.7128,-74.0060"
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

# -- Helper to geocode a manual address input
def geocode_address(address):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json"
        }
        response = requests.get(url, params=params, headers={"User-Agent": "streamlit-app"})
        if response.status_code == 200:
            results = response.json()
            if results:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                formatted_address = results[0].get("display_name", address)
                return lat, lon, formatted_address
    except Exception as e:
        print(f"Error geocoding address: {e}")
    return None, None, "Unknown Location"

# -- Main app
def main():
    st.set_page_config(page_title="Gluten-Free Restaurant Finder", page_icon="🍽️", layout="wide")
    st.title("🍽️ Gluten-Free Restaurant Finder")

    search_option = st.radio(
        "Choose search option:",
        ["Use my current location", "Enter a different address"],
        index=0
    )

    if search_option == "Use my current location":
        with st.spinner('Determining your location...'):
            latitude, longitude, my_address = get_my_location()
    else:
        address_input = st.text_input("Enter an address (e.g., New York, NY):")
        if address_input:
            with st.spinner('Looking up address...'):
                latitude, longitude, my_address = geocode_address(address_input)
        else:
            latitude = longitude = None
            my_address = "No address entered"

    if not latitude:
        st.error("Could not determine a valid location. Please try again.")
        return

    st.success(f"Searching around: {my_address}")

    # Get Foursquare API key from Secrets Manager
    with st.spinner('Retrieving API credentials...'):
        secrets = get_secret("swarm/api_key")
        swarm_api_key = secrets["api_key"]

    # Search for restaurants
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

    # Show interactive map
    df = pd.DataFrame(restaurants)

    st.subheader("🗺️ Interactive Map of Restaurants")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_color='[255, 0, 0, 160]',  # Red markers
        get_radius=50,
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
        "html": "<b>{name}</b><br/>{address}",
        "style": {
            "backgroundColor": "white",
            "color": "black"
        }
    }

    view_state = pdk.ViewState(
        latitude=latitude,
        longitude=longitude,
        zoom=13,
        pitch=0,
    )

    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/streets-v12",
            initial_view_state=view_state,
            layers=[layer],
            tooltip=tooltip,
        )
    )

# -- Run the app
if __name__ == "__main__":
    main()

