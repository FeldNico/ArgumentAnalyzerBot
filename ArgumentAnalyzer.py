import os

from dotenv import load_dotenv

from RedditBot import RedditBot

load_dotenv()
# It's crucial that this environment variable is set before running the script
DB_PASSPHRASE = os.getenv("DB_PASSPHRASE")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Main execution block ---
if __name__ == "__main__":
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, GOOGLE_API_KEY]):
        print(
            "ERROR: One or more environment variables are not set. Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, and GOOGLE_API_KEY.")
        exit(1)

    bot = RedditBot()
    bot.run()
