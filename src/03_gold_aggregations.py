import os
import io
import requests
import polars as pl
from dotenv import load_dotenv
from logger import setup_logger

# Initialize logger
log = setup_logger("GoldAggregations_LocalBypass")

# Load credentials
load_dotenv()
DATABRICKS_URL = os.getenv("DATABRICKS_INSTANCE_URL").rstrip('/')
TOKEN = os.getenv("DATABRICKS_PAT_TOKEN")

# Unity Catalog Structure
CATALOG = "remote_ecommerce_medallion_pipeline"
SCHEMA = "medallion"
SILVER_VOLUME = "silver_cleaned" # using the name you provided

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

def process_gold_layer():
    log.info(f"Step 1: Fetching Silver data from {CATALOG}.{SCHEMA}.{SILVER_VOLUME}...")
    
    # 1. Fetch Parquet from the Silver Volume
    silver_filename = "Ecommerce_Transactions_Silver_Successful.parquet"
    silver_path = f"/Volumes/{CATALOG}/{SCHEMA}/{SILVER_VOLUME}/{silver_filename}"
    get_endpoint = f"{DATABRICKS_URL}/api/2.0/fs/files{silver_path}"
    
    response = requests.get(get_endpoint, headers=HEADERS)
    if response.status_code != 200:
        log.error(f"Failed to fetch Silver data. API said: {response.text}")
        return
        
    log.info("Data downloaded into memory. Loading into Polars...")
    
    # 2. Read directly from memory
    parquet_bytes = io.BytesIO(response.content)
    df = pl.read_parquet(parquet_bytes)
    
    log.info("Step 2: Performing Gold Layer Aggregations to answer assignment questions...")
    
    # A. Distribution of transaction amounts
    df_transaction_dist = df.group_by("TransactionNo").agg(
        pl.sum("TotalAmount").alias("TransactionTotal")
    )
    
    # B. Total transaction amount over time (Daily Revenue)
    df_revenue_time = df.group_by("Date").agg(
        pl.sum("TotalAmount").alias("DailyRevenue")
    ).sort("Date")
    
    # C. Product categories by revenue
    df_category_rev = df.group_by("Category").agg(
        pl.sum("TotalAmount").alias("CategoryRevenue")
    ).sort("CategoryRevenue", descending=True)
    
    # D. Customer purchasing behaviour 
    df_customer_behavior = df.group_by("CustomerNo").agg(
        pl.n_unique("TransactionNo").alias("TotalOrders"),
        pl.sum("TotalAmount").alias("TotalSpend"),
        (pl.sum("TotalAmount") / pl.n_unique("TransactionNo")).alias("AvgOrderValue")
    ).sort("TotalSpend", descending=True)
    
    # --- SAVE LOCALLY TO BYPASS NETWORK FIREWALL ---
    log.info("Step 3: Saving Gold datasets locally...")
    
    # Create the local gold directory
    local_gold_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'gold')
    os.makedirs(local_gold_dir, exist_ok=True)
    
    df_transaction_dist.write_parquet(os.path.join(local_gold_dir, "Gold_Transaction_Distribution.parquet"))
    df_revenue_time.write_parquet(os.path.join(local_gold_dir, "Gold_Revenue_Over_Time.parquet"))
    df_category_rev.write_parquet(os.path.join(local_gold_dir, "Gold_Category_Revenue.parquet"))
    df_customer_behavior.write_parquet(os.path.join(local_gold_dir, "Gold_Customer_Behavior.parquet"))
    
    log.info(f"Successfully created 4 Gold tables in: {local_gold_dir}")
   

if __name__ == "__main__":
    process_gold_layer()