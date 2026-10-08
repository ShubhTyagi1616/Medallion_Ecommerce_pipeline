import os
import requests
from dotenv import load_dotenv
from logger import setup_logger

# Initialize logger
log = setup_logger("BronzeIngestion_UC")

# Load credentials
load_dotenv()
DATABRICKS_URL = os.getenv("DATABRICKS_INSTANCE_URL").rstrip('/')
TOKEN = os.getenv("DATABRICKS_PAT_TOKEN")

# Unity Catalog Structure
CATALOG = "remote_ecommerce_medallion_pipeline"
SCHEMA = "medallion"
VOLUME = "bronze_raw"
FILENAME = "Ecommerce_Transactions_Data.csv"

def upload_to_uc_volume(local_file_path):
    if not os.path.exists(local_file_path):
        log.error(f"File not found on local machine: {local_file_path}")
        return

    # Unity Catalog API Path
    volume_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{FILENAME}"
    api_endpoint = f"{DATABRICKS_URL}/api/2.0/fs/files{volume_path}"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/octet-stream"
    }
    
    log.info(f"Starting direct upload to Unity Catalog: {volume_path}")
    
    try:
        # The modern Files API supports direct streaming uploads in a single PUT request
        with open(local_file_path, 'rb') as file_data:
            response = requests.put(api_endpoint, headers=headers, data=file_data, params={"overwrite": "true"})
            
        if response.status_code == 200:
            log.info(f"Upload complete! File successfully saved to {volume_path}")
        else:
            log.error(f"Upload failed (Status {response.status_code}): {response.text}")
            
    except Exception as e:
        log.error(f"Upload interrupted: {str(e)}")

if __name__ == "__main__":
    # Point to the local CSV file
    LOCAL_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'bronze', FILENAME)
    
    upload_to_uc_volume(LOCAL_CSV)