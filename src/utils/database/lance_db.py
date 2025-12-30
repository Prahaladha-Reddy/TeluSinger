import lancedb
from dotenv import load_dotenv
load_dotenv()
import os 
LANCEDB_API_KEY=os.getenv("LANCEDB_API_KEY")
LANCEDB_URL=os.getenv("LANCEDB_URL")

def get_lance():
  db = lancedb.connect(
    api_key=LANCEDB_API_KEY,
    uri=LANCEDB_URL,
    region="us-east-1"
  )
  return db

def get_lance_table(table_name:str):
  db=get_lance()
  table = db.open_table(table_name)
  return table

