# Autodesk Platform Services (APS) Credentials
# Please replace these placeholder values with your actual APS Client ID and Client Secret.

APS_CLIENT_ID = "YOUR_APS_CLIENT_ID_HERE"
APS_CLIENT_SECRET = "YOUR_APS_CLIENT_SECRET_HERE"

# You can also add other configuration variables here if needed, for example:
# APS_BUCKET_KEY = "YOUR_APS_BUCKET_KEY_HERE" # If using specific buckets
# APS_CALLBACK_URL = "YOUR_APS_CALLBACK_URL_HERE" # If needed for 3-legged OAuth (not typically for Design Automation)

if __name__ == '__main__':
    if APS_CLIENT_ID == "YOUR_APS_CLIENT_ID_HERE" or APS_CLIENT_SECRET == "YOUR_APS_CLIENT_SECRET_HERE":
        print("WARNING: APS credentials in auth_config.py are still set to placeholder values.")
        print("Please update them with your actual APS Client ID and Client Secret.")
    else:
        print("APS credentials seem to be configured in auth_config.py.")
        print(f"APS_CLIENT_ID: {APS_CLIENT_ID[:4]}...{APS_CLIENT_ID[-4:] if len(APS_CLIENT_ID) > 8 else ''}")
