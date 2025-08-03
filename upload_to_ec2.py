import os
from datetime import datetime
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Constants from environment variables
EC2_IP = os.getenv("ec2_ip")                # Example: "13.234.22.11"
EC2_USER = os.getenv("ec2_user")            # Example: "ubuntu"
EC2_KEY_PATH = os.getenv("ec2_key_path")    # Example: "/home/pi/ec2-key.pem"
REMOTE_BASE_PATH = os.getenv("remote_ec2_path")       # Example: "/home/ubuntu/images"

def upload_to_ec2(local_folder):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    remote_path = f"{REMOTE_BASE_PATH}/{timestamp}/"

    if not os.path.exists(local_folder):
        print(f"❌ Local folder not found: {local_folder}")
        return

    # Step 1: Create remote directory on EC2
    mkdir_cmd = f'ssh -i {EC2_KEY_PATH} {EC2_USER}@{EC2_IP} "mkdir -p {remote_path}"'
    os.system(mkdir_cmd)

    # Step 2: Run SCP command
    scp_cmd = f"scp -i {EC2_KEY_PATH} -r {local_folder}/* {EC2_USER}@{EC2_IP}:{remote_path}"

    print(f"📤 Uploading images from '{local_folder}' to EC2 at '{remote_path}'...")
    result = os.system(scp_cmd)

    if result == 0:
        print("✅ Upload successful.")
    else:
        print("❌ Upload failed.")

# Allow standalone execution
if __name__ == "__main__":
    upload_to_ec2(os.getenv("local_image_folder"))
