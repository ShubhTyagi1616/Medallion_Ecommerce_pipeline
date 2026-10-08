import os
import io
import requests
import polars as pl
from dotenv import load_dotenv
from logger import setup_logger

# Initialize logger
log = setup_logger("SilverCleansing_LocalBypass")

# Load credentials
load_dotenv()
DATABRICKS_URL = os.getenv("DATABRICKS_INSTANCE_URL").rstrip('/')
TOKEN = os.getenv("DATABRICKS_PAT_TOKEN")

# Unity Catalog Structure
CATALOG = "remote_ecommerce_medallion_pipeline"
SCHEMA = "medallion"
BRONZE_VOLUME = "bronze_raw"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

def process_silver_layer():
    log.info(f"Step 1: Fetching Bronze data from {CATALOG}.{SCHEMA}.{BRONZE_VOLUME}...")
    
    bronze_path = f"/Volumes/{CATALOG}/{SCHEMA}/{BRONZE_VOLUME}/Ecommerce_Transactions_Data.csv"
    get_endpoint = f"{DATABRICKS_URL}/api/2.0/fs/files{bronze_path}"
    
    response = requests.get(get_endpoint, headers=HEADERS)
    if response.status_code != 200:
        log.error(f"Failed to fetch Bronze data. API said: {response.text}")
        return
        
    log.info("Data downloaded into memory. Loading into Polars...")
    
    csv_bytes = io.BytesIO(response.content)
    df = pl.read_csv(csv_bytes)
    
    log.info("Step 2: Formatting Dates and calculating TotalAmount...")
    df_clean = df.with_columns(
        (pl.col("Price") * pl.col("Quantity")).alias("TotalAmount"),
        pl.col("Date").str.to_date("%Y-%m-%d")
    )
    
    log.info("Step 3: Routing data into Successful and Archived datasets...")
    df_successful = df_clean.filter(~pl.col("TransactionNo").cast(pl.Utf8).str.starts_with("C"))
    df_archived = df_clean.filter(pl.col("TransactionNo").cast(pl.Utf8).str.starts_with("C"))
    
    # --- SAVE LOCALLY TO BYPASS NETWORK FIREWALL ---
    log.info("Step 4: Saving files locally to bypass API upload restrictions...")
    
    # Create the local silver directory if it doesn't exist
    local_silver_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'silver')
    os.makedirs(local_silver_dir, exist_ok=True)
    
    success_path = os.path.join(local_silver_dir, "Ecommerce_Transactions_Silver_Successful.parquet")
    archive_path = os.path.join(local_silver_dir, "Ecommerce_Transactions_Silver_Archived.parquet")
    
    df_successful.write_parquet(success_path)
    df_archived.write_parquet(archive_path)
    
    log.info(f"Successfully saved exactly {df_successful.height} successful orders to: {success_path}")
    log.info(f"Successfully saved exactly {df_archived.height} archived orders to: {archive_path}")
    log.info("ACTION REQUIRED: Please open your Databricks UI and manually drag-and-drop these files into your 'silver_cleansed' volume!")

if __name__ == "__main__":
    process_silver_layer()