import boto3
import json
import requests
from botocore.exceptions import ClientError

def get_secret(secret_name, region_name="us-east-1"):
    # Create a Secrets Manager client
    client = boto3.client('secretsmanager', region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise Exception(f"Unable to retrieve secret: {e}")

    # Decrypts secret using the associated KMS key.
    if "SecretString" in response:
        secret = response["SecretString"]
        return json.loads(secret)
    else:
        # Handle if secret is binary
        decoded_binary_secret = base64.b64decode(response["SecretBinary"]) # type: ignore
        return json.loads(decoded_binary_secret)

def search_gluten_free_restaurants(lat, lon, radius=1000, limit=10):
    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": swarm_api_key
    }
    params = {
        "ll": f"{lat},{lon}",
        "query": "Gluten Free",
        "radius": radius,
        "limit": limit,
        "categories": "13065"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
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


def format_address(location):
    parts = [
        location.get("address"),
        location.get("locality"),
        location.get("region"),
        location.get("postcode"),
        location.get("country")
    ]
    return ", ".join(part for part in parts if part)

latitude = 30.085136
longitude = -95.425186

# Example usage
secrets = get_secret("swarm/api_key")
swarm_api_key = secrets["api_key"]

restaurants = search_gluten_free_restaurants(latitude, longitude)

print("\nNearby Gluten-Free Restaurants:")
for r in restaurants:
    #print("- {} ({})".format(r['name'], r['address']))
    print("- " + r['name'] + " - " + r['address'])

 # type: ignore