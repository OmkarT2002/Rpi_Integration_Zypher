# run_ec2.py
import subprocess
from dotenv import load_dotenv
import os

load_dotenv()

EC2_USER = "ubuntu"
EC2_IP = os.getenv("ec2_ip")
KEY_PATH = "/home/plnxtqube/Desktop/Inventory/deployment.pem"
SCRIPT_PATH = "/home/ubuntu/myscript.sh"

def run_ec2_script():
    """Executes a remote script on the EC2 instance via SSH."""
    command = f"ssh -i {KEY_PATH} {EC2_USER}@{EC2_IP} 'bash {SCRIPT_PATH}'"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Remote EC2 script executed successfully")
    else:
        print(f"❌ Remote script failed: {result.stderr}")
    return result.returncode == 0
