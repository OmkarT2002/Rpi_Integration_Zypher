import os
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Set AWS credentials directly from environment variables
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("aws_access_key")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("aws_secret_key")
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"

# Constants
LOCAL_IMAGE_FOLDER = "/home/plnxtqube/Desktop/Inventory/Images"
BUCKET_NAME = "zypherv2production"
S3_BASE_FOLDER = "drone-logs"

def upload_to_s3():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    s3_folder = f"{S3_BASE_FOLDER}/{timestamp}/"
    s3 = boto3.client('s3')

    if not os.path.exists(LOCAL_IMAGE_FOLDER):
        print(f"Local folder not found: {LOCAL_IMAGE_FOLDER}")
        return

    files_uploaded = 0
    for filename in os.listdir(LOCAL_IMAGE_FOLDER):
        if filename.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            local_path = os.path.join(LOCAL_IMAGE_FOLDER, filename)
            s3_key = s3_folder + filename
            try:
                s3.upload_file(local_path, BUCKET_NAME, s3_key)
                print(f"Uploaded: {local_path} → s3://{BUCKET_NAME}/{s3_key}")
                files_uploaded += 1
            except Exception as e:
                print(f"Failed to upload {filename}: {e}")

    print(f"Upload complete. {files_uploaded} file(s) uploaded.")

# Allow standalone testing
if __name__ == "__main__":
    upload_to_s3()
