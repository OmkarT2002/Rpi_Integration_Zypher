import pyudev
import os
import shutil
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import time
import sys
import glob
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
# Add your module paths
sys.path.append("/home/plnxtqube/Desktop/Inventory")

from rds_handler import image_exists_in_rds, insert_image_metadata
from upload_to_ec2 import upload_to_ec2
from run_ec2 import run_ec2_script
class SDCardMonitor:
    def __init__(self):
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='block', device_type='partition')

        self.base_destination = "/home/plnxtqube/Desktop/Inventory/Images"
        self.log_file = "/home/plnxtqube/sdcard_events.log"
        os.makedirs(self.base_destination, exist_ok=True)

    def log(self, message):
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with open(self.log_file, "a") as f:
            f.write(f"{timestamp} {message}\n")
        print(f"{timestamp} {message}")

    def find_mount_point(self, device_name):
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == device_name:
                        return parts[1]
        except Exception as e:
            self.log(f"❌ Error reading mount info: {str(e)}")
        return None

    def find_dji_folder(self, mount_path):
        for root, dirs, files in os.walk(mount_path):
            if "DCIM" in root and os.path.basename(root).lower() == "dji":
                return root
        return None

    def get_exif_creation_time(self, image_path):
        try:
            image = Image.open(image_path)
            exif_data = image._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    if TAGS.get(tag) == "DateTimeOriginal":
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        except Exception as e:
            self.log(f"❌ Error reading EXIF from {image_path}: {str(e)}")
        return None

    def is_today(self, dt):
        today = datetime.now().date()
        return dt.date() == today

    
    def copy_images(self, dji_folder):
        today_str = datetime.now().strftime("%Y-%m-%d")
        dest_dir = os.path.join(self.base_destination, today_str)
        os.makedirs(dest_dir, exist_ok=True)

        copied_files = []
        tasks = []

        # Collect all files first (faster than processing inside os.walk loop)
        image_files = [
            os.path.join(root, file)
            for root, _, files in os.walk(dji_folder)
            for file in files
            if file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".dng", ".mp4"))
        ]

        def process_file(src):
            file = os.path.basename(src)
            exif_time = self.get_exif_creation_time(src)
            if not exif_time:
                exif_time = datetime.fromtimestamp(os.path.getmtime(src))
                self.log(f"⚠️ No EXIF for {file}, using file modified time")

            if not self.is_today(exif_time):
                return None

            created_time_str = exif_time.strftime("%Y-%m-%d %H:%M:%S")

            if image_exists_in_rds(file, created_time_str):
                self.log(f"⏭️ Skipped (already in RDS): {file}")
                return None

            dst = os.path.join(dest_dir, file)
            if not os.path.exists(dst):
                try:
                    shutil.copy(src, dst)  # ✅ Faster than copy2 (doesn't preserve metadata)
                    self.log(f"✅ Copied: {src} -> {dst}")
                    return (file, created_time_str)
                except Exception as e:
                    self.log(f"❌ Failed to copy {file}: {str(e)}")
            else:
                self.log(f"⚠️ Already exists locally: {file}")
            return None

        # ✅ Use multithreading to speed up copying
        with ThreadPoolExecutor(max_workers=8) as executor:  # Adjust threads based on CPU
            futures = [executor.submit(process_file, src) for src in image_files]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    copied_files.append(result)

        return dest_dir, copied_files

    def monitor_sd_card(self):
        self.log("🔍 Waiting for SD card...")
        for device in iter(self.monitor.poll, None):
            if device.action == 'add':
                dev_node = device.device_node
                self.log(f"📦 Detected device: {dev_node}")
                time.sleep(3)

                mount_path = None
                for _ in range(10):
                    mount_path = self.find_mount_point(dev_node)
                    if mount_path and os.path.isdir(mount_path):
                        break
                    time.sleep(1)

                if not mount_path or not os.path.isdir(mount_path):
                    self.log("❌ Could not find valid mount point after waiting.")
                    continue

                dji_folder = self.find_dji_folder(mount_path)
                if not dji_folder:
                    self.log("❌ DJI folder not found in mounted device.")
                    continue

                self.log(f"DJI folder located at: {dji_folder}")

                dest_dir, copied_files = self.copy_images(dji_folder)
                
                if copied_files:
                    self.log("🚀 Starting parallel upload and metadata insert...")

                    def upload_task():
                        try:
                            upload_to_ec2(dest_dir)
                            self.log("✅ Upload complete.")
                        except Exception as e:
                            self.log(f"❌ Upload failed: {str(e)}")

                    def insert_task(filename, timestamp):
                        try:
                            insert_image_metadata(filename, timestamp, user_id=1)
                            self.log(f"📝 Metadata saved: {filename}")
                        except Exception as e:
                            self.log(f"❌ DB insert error: {filename}: {str(e)}")

                    with ThreadPoolExecutor(max_workers=5) as executor:
                        # Submit EC2 upload as one task
                        futures = [executor.submit(upload_task)]

                        # Submit metadata inserts as separate tasks
                        for filename, timestamp in copied_files:
                            futures.append(executor.submit(insert_task, filename, timestamp))

                        # Wait for all tasks to complete
                        for future in as_completed(futures):
                            future.result()

                    self.log("✅ All uploads and metadata inserts completed.")

                    # 🧹 Clean up after successful upload
                    run_ec2_script()
                    delete_all_inside(self.base_destination)
                    self.log("🧹 Cleaned up Images folder.")
                else:
                    self.log("ℹ️ No new images to upload.")

                self.log("♻️ Monitoring resumed. Insert next SD card when ready.")

# 🧹 Delete all files & subfolders inside a directory
def delete_all_inside(folder_path):
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
            print(f"Deleted: {item_path}")
        except Exception as e:
            print(f"Failed to delete {item_path}: {e}")

# 🚀 Entry point
if __name__ == "__main__":
    monitor = SDCardMonitor()
    monitor.monitor_sd_card()
