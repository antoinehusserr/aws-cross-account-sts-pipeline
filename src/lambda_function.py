"""
Projet 1 — AWS STS cross-account : ISS tracker
Compte A (source) -> assume un rôle dans le Compte B (cible) -> écrit dans S3.

Variables d'environnement Lambda à configurer :
- TARGET_ROLE_ARN : arn:aws:iam::<ACCOUNT_B_ID>:role/ISSDataWriterRole
- BUCKET_NAME     : iss-tracker-data-<votre-id>
- EXTERNAL_ID     : iss-tracker-project  (doit matcher la trust policy)
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

import boto3

ISS_API_URL = "https://api.wheretheiss.at/v1/satellites/25544"


def get_iss_position():
    """Appelle l'API publique ISS et retourne la réponse JSON."""
    with urllib.request.urlopen(ISS_API_URL, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def assume_cross_account_role(role_arn: str, external_id: str, session_name: str):
    """Assume le rôle du Compte B via STS et retourne des credentials temporaires."""
    sts_client = boto3.client("sts")
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        ExternalId=external_id,
        DurationSeconds=900,  # 15 min, minimum autorisé, largement suffisant ici
    )
    return response["Credentials"]


def write_to_s3(credentials: dict, bucket_name: str, data: dict):
    """Utilise les credentials temporaires du Compte B pour écrire dans S3."""
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    key = f"iss-positions/{timestamp}.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return key


def lambda_handler(event, context):
    role_arn = os.environ["TARGET_ROLE_ARN"]
    bucket_name = os.environ["BUCKET_NAME"]
    external_id = os.environ["EXTERNAL_ID"]

    iss_data = get_iss_position()

    credentials = assume_cross_account_role(
        role_arn=role_arn,
        external_id=external_id,
        session_name="iss-tracker-lambda",
    )

    s3_key = write_to_s3(credentials, bucket_name, iss_data)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Position ISS écrite avec succès",
                "s3_key": s3_key,
                "iss_data": iss_data,
            }
        ),
    }
