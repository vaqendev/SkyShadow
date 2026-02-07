import ee
import os
import json
import requests
from google.oauth2.service_account import Credentials


PROJECT_ID = 'possible-stock-485917-k8' 

key_content = os.environ.get("GEE_PRIVATE_KEY")
if not key_content:
    if os.path.exists("credentials.json"):
        print(" Running Locally: Loading credentials.json")
        with open("credentials.json", "r") as f:
            key_content = f.read()

if not key_content:
    print(" Key Missing ")
else:
    try:
        service_account_info = json.loads(key_content)
        SCOPES = ['https://www.googleapis.com/auth/earthengine']
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        ee.Initialize(credentials=creds, project=PROJECT_ID)
        print(" [SUCCESS] Connected to Earth Engine!")
    except Exception as e:
        print(f" Auth Error: {e}")