import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv

# ✅ MySQL DB config
DB_CONFIG = {
    'host': 'inventory.cru2esa0auwo.ap-south-1.rds.amazonaws.com',
    'user': 'admin',
    'password': '(7(]GCCeqUMTlf)cZ3J-wNMmjb_U',
    'database': 'inventory'
}

def connect_to_rds():
    return mysql.connector.connect(**DB_CONFIG)

def image_exists_in_rds(image_name, created_at):
    try:
        conn = connect_to_rds()
        cur = conn.cursor()
        query = """
        SELECT 1 FROM images
        WHERE image_name = %s AND created_at = %s;
        """
        cur.execute(query, (image_name, created_at))
        exists = cur.fetchone() is not None
        cur.close()
        conn.close()
        return exists
    except Exception as e:
        print(f"❌ Database error (exists check): {e}")
        return False

def insert_image_metadata(image_name, created_at, user_id=1):
    try:
        conn = connect_to_rds()
        cur = conn.cursor()
        query = """
        INSERT INTO images(image_name, created_at, user_id)
        VALUES (%s, %s, %s);
        """
        cur.execute(query, (image_name, created_at, user_id))
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Inserted into DB: {image_name}")
    except Exception as e:
        print(f"❌ Database error (insert): {e}")
if __name__ == "__main__":
    image_path = "/home/plnxtqube/Desktop/Inventory/Images/DJI_0928.JPG"
    created_at = datetime.now()
    if not image_exists_in_rds(image_path, created_at):
        insert_image_metadata(image_path, created_at, user_id=1)
