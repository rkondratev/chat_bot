import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN=os.getenv("BOT_TOKEN")
LLM_API_KEY=os.getenv("LLM_API_KEY")
