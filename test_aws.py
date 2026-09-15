import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

def run_aws_diagnostics():
    print("=" * 60)
    print("Monarch / Vasooli -- AWS Connectivity Diagnostics")
    print("=" * 60)
    
    region = os.getenv("AWS_REGION", "us-east-1")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    use_bedrock = os.getenv("USE_BEDROCK", "false").lower() == "true"
    bedrock_model = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    s3_bucket = os.getenv("S3_DOCUMENTS_BUCKET", "monarch-docs-storage")
    use_dynamodb = os.getenv("USE_DYNAMODB", "false").lower() == "true"
    dynamo_table = os.getenv("DYNAMODB_TABLE_NAME", "MonarchSaaS")
    auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    cognito_pool = os.getenv("COGNITO_USER_POOL_ID")

    print(f"Configured AWS Region: {region}")
    
    if not access_key or not secret_key:
        print("\n[NOTICE] AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY is not set in .env.")
        print("  - If testing locally/offline: Built-in local fallbacks are active.")
        print("  - To connect to live AWS: Add your IAM Access Key & Secret to .env.")
    else:
        masked_key = access_key[:4] + "..." + access_key[-4:] if len(access_key) > 8 else "***"
        print(f"AWS Access Key ID: {masked_key}")

    try:
        import boto3
        from botocore.config import Config
        fast_config = Config(connect_timeout=3, read_timeout=3, retries={'max_attempts': 1})
    except ImportError:
        print("\n[ERROR] boto3 is not installed in the virtualenv. Run: pip install boto3")
        return

    # 1. AWS STS (Identity & Credentials verification)
    print("\n--- 1. AWS STS Authentication ---")
    try:
        sts = boto3.client("sts", region_name=region, config=fast_config)
        identity = sts.get_caller_identity()
        print(f"[PASS] STS Connected: Account={identity.get('Account')}, User/ARN={identity.get('Arn')}")
    except Exception as exc:
        print(f"[FAIL] STS Auth: {exc}")

    # 2. Amazon Bedrock
    print("\n--- 2. Amazon Bedrock Runtime ---")
    print(f"  Config: USE_BEDROCK={use_bedrock}, Model={bedrock_model}")
    try:
        bedrock = boto3.client("bedrock-runtime", region_name=region, config=fast_config)
        print("[PASS] Bedrock Runtime Client initialized successfully.")
    except Exception as exc:
        print(f"[WARN] Bedrock initialization error: {exc}")

    # 3. Amazon S3
    print("\n--- 3. Amazon S3 Document Storage ---")
    print(f"  Target Bucket: {s3_bucket}")
    try:
        s3 = boto3.client("s3", region_name=region, config=fast_config)
        s3.head_bucket(Bucket=s3_bucket)
        print(f"[PASS] S3 Bucket '{s3_bucket}' is accessible and verified.")
    except Exception as exc:
        print(f"[WARN] S3 Check: {exc}")

    # 4. Amazon DynamoDB
    print("\n--- 4. Amazon DynamoDB ---")
    print(f"  Config: USE_DYNAMODB={use_dynamodb}, Table={dynamo_table}")
    try:
        dynamo = boto3.client("dynamodb", region_name=region, config=fast_config)
        desc = dynamo.describe_table(TableName=dynamo_table)
        status = desc.get("Table", {}).get("TableStatus", "UNKNOWN")
        print(f"[PASS] DynamoDB Table '{dynamo_table}' found (Status: {status}).")
    except Exception as exc:
        print(f"[WARN] DynamoDB Check: {exc}")

    # 5. Amazon Cognito
    print("\n--- 5. Amazon Cognito User Pool ---")
    print(f"  Config: AUTH_ENABLED={auth_enabled}, Pool ID={cognito_pool}")
    if cognito_pool:
        try:
            cognito = boto3.client("cognito-idp", region_name=region, config=fast_config)
            desc = cognito.describe_user_pool(UserPoolId=cognito_pool)
            pool_name = desc.get("UserPool", {}).get("Name", "Unknown")
            print(f"[PASS] Cognito User Pool found: '{pool_name}'")
        except Exception as exc:
            print(f"[WARN] Cognito Check: {exc}")
    else:
        print("[INFO] Cognito User Pool ID not configured (using local dev mock auth).")

    print("\n" + "=" * 60)
    print("Diagnostics Complete")
    print("=" * 60)

if __name__ == "__main__":
    run_aws_diagnostics()
