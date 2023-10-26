from dotenv import load_dotenv
import os

# Environment variables
load_dotenv()
CS213BOT_KEY = os.getenv("CS213BOT_KEY")
DASHBOARD_CHANNEL_ID = int(os.getenv("PL_DASHBOARD_CHANNEL"))
COURSE_ID = int(os.getenv("COURSE_ID"))
NOTIF_CHANNEL_ID = int(os.getenv("NOTIF_CHANNEL"))
PL_TOKEN = os.getenv("PLTOKEN")
SERVER_ID = int(os.getenv("SERVER_ID"))
