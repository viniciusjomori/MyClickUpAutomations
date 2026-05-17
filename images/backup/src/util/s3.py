import boto3
import json
import os

BUCKET_NAME = os.getenv("BUCKET_NAME")

s3_client = boto3.client("s3")

def put_json(path: str, filename: str, obj: dict):
    json_str = json.dumps(
        obj,
        ensure_ascii=False,
        indent=2
    ).encode('utf-8')

    key = path + "/" + filename

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json_str,
        ContentType="application/json; charset=utf-8"
    )

    return True