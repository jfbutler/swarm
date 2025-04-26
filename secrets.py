import boto3
import json
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
        decoded_binary_secret = base64.b64decode(response["SecretBinary"])
        return json.loads(decoded_binary_secret)

# Example usage
secrets = get_secret("MyApp/APIKey")
print(secrets["api_key"])
