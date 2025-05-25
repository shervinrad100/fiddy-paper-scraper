from bs4 import BeautifulSoup
from google.cloud import storage

storage.Client.from_service_account_json("key.json")
client = storage.Client()

