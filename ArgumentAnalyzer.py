import praw
from google import genai  # New import for Google Generative AI
import os
import time
import json  # Will be used to parse JSON output from Gemini
from dotenv import load_dotenv

load_dotenv()

# --- Configuration (from environment variables) ---
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Changed from OPENAI_API_KEY

trigger_phrases = ["check the above comments", "analyze thread", "flawed arguments", "bad arguments",
                                   "point out users", "score users"]

# --- Initialize PRAW and Google Generative AI ---
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USERNAME,
    password=REDDIT_PASSWORD,
    user_agent="ArgumentQualityBot by u/YOUR_REDDIT_USERNAME"  # Match your bot's actual username
)

# Configure the Gemini API with your API key
genai = genai.Client()

# --- Define the Response Schema for Structured Output ---
# This schema defines the expected JSON structure of the AI's analysis.
# We want a list of analysis entries, and an overall summary.
response_schema = {
    "type": "object",
    "properties": {
        "analysis_entries": {
            "type": "array",
            "description": "A list of individual argument analyses.",
            "items": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "The Reddit username of the commenter."
                    },
                    "comment_summary": {
                        "type": "string",
                        "description": "A brief summary of the comment's argument."
                    },
                    "argument_type": {
                        "type": "string",
                        "enum": ["valid_argument", "fallacy", "no_argument_found"],
                        "description": "Classification of the argument in this comment."
                    },
                    "fallacy_type": {
                        "type": "string",
                        "description": "The specific name of the fallacy, if 'argument_type' is 'fallacy'. Empty otherwise."
                    },
                    "flaw_description": {
                        "type": "string",
                        "description": "Description of the fallacy or weakness, if any. Empty if valid or no argument."
                    }
                },
                "required": ["username", "comment_summary", "argument_type"]
            }
        },
        "overall_summary": {
            "type": "string",
            "description": "A concise overall summary of the argument quality in the entire thread."
        },
        "overall_argument_type": {
            "type": "string",
            "enum": ["valid_discussion", "fallacious_discussion", "mixed_discussion", "no_arguments_found"],
            "description": "Overall classification of the entire discussion thread."
        }
    },
    "required": ["analysis_entries", "overall_summary", "overall_argument_type"]
}


# --- Helper Function for Gemini Analysis (Now uses structured output) ---
def analyze_comment_thread_for_flaws(comment_thread_text):
    if not comment_thread_text.strip():
        # Return default structure if no text to analyze
        return {
            "analysis_entries": [],
            "overall_summary": "No relevant comments found in the discussion thread to analyze.",
            "overall_argument_type": "no_arguments_found"
        }

    try:
        # Construct the prompt for the Gemini model
        prompt_parts = [
            """You are a highly logical and unbiased argument analysis bot. Analyze the following Reddit comment thread to identify arguments, their validity, and any logical fallacies.
            For each comment that presents an argument, classify it as 'valid_argument', 'fallacy', or 'no_argument_found'.
            If it's a 'fallacy', clearly state the **specific name of the fallacy** (e.g., 'Slippery Slope', 'Ad Hominem', 'Strawman') and provide a **brief, easy-to-understand explanation** of why that argument fits the fallacy, making it accessible to a general audience.
            If it's a 'valid_argument', explain why it's well-constructed.
            If 'no_argument_found', state that the comment does not contain a discernible argument.
            Provide a concise summary of each comment's main point.
            Finally, give an overall summary and classification for the entire discussion thread.
            Ensure your output strictly follows the provided JSON schema. Maintain a neutral and educational tone.""",
            f"Reddit Comment Thread for Analysis:\n\n{comment_thread_text}"
        ]

        # Call the Gemini model with structured output configuration
        response = genai.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_parts,
            config={
                "temperature":0.2,
                "response_mime_type":"application/json",  # Request JSON output
                "response_schema":response_schema,  # Provide the defined schema
            },
            # safety_settings=... # Optionally add safety settings if needed
        )

        # Gemini's structured output response.text returns a string, so parse it
        try:
            parsed_response = json.loads(response.text)
            return parsed_response
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from Gemini API: {e}")
            print(f"Raw Gemini response text: {response.text}")
            return {
                "analysis_entries": [],
                "overall_summary": "Error parsing AI response. Please try again.",
                "overall_argument_type": "no_arguments_found"
            }

    except Exception as e:
        print(f"An unexpected error occurred during Gemini API call: {e}")
        return {
            "analysis_entries": [],
            "overall_summary": "An unexpected error occurred during analysis.",
            "overall_argument_type": "no_arguments_found"
        }


def get_ancestor_comments_and_post(start_comment):
    """
    Traverses up the comment tree from a starting comment
    to the original post, collecting all ancestor comments.
    """
    path = []
    current_item = start_comment

    while True:
        parent = current_item.parent()
        if isinstance(parent, praw.models.Submission):
            print(f"Reached original post (Submission): {parent.title} ({parent.url})")
            break

        elif isinstance(parent, praw.models.Comment):
            path.insert(0, parent)
            current_item = parent
            print(f"Traversing up to parent comment: {current_item.body[:50]}...")
        else:
            print("Unexpected parent type or end of tree without reaching submission.")
            break

    return path, parent


# --- Main Bot Loop ---
def run_bot_by_mentions():
    print(f"Starting bot, listening for mentions for: {reddit.user.me()}")

    for item in reddit.inbox.stream():
        if isinstance(item, praw.models.Comment):
            bot_username_lower = reddit.user.me().name.lower()
            if item.was_comment and bot_username_lower in item.body.lower():
                if any(phrase in item.body.lower() for phrase in trigger_phrases):
                    print(f"Bot triggered by comment: {item.id} by {item.author}")

                    ancestor_comments, original_post = get_ancestor_comments_and_post(item)

                    comment_thread_for_analysis = ""
                    if original_post:
                        comment_thread_for_analysis += f"--- Original Post ---\n"
                        comment_thread_for_analysis += f"Title: {original_post.title}\n"
                        if original_post.selftext:
                            comment_thread_for_analysis += f"Content: {original_post.selftext}\n"
                        author_name = original_post.author.name if original_post.author else '[Deleted User]'
                        comment_thread_for_analysis += f"By: u/{author_name}\n"
                        comment_thread_for_analysis += "---\n\n"

                    if ancestor_comments:
                        comment_thread_for_analysis += "--- Comment Thread --- (Oldest to Newest, excluding trigger comment)\n"
                        for comment_ancestor in ancestor_comments:
                            author_name = comment_ancestor.author.name if comment_ancestor.author else '[Deleted User]'
                            comment_thread_for_analysis += f"User ({author_name}): {comment_ancestor.body}\n---\n"
                        comment_thread_for_analysis += "\n"

                    if not ancestor_comments and (not original_post.selftext and not original_post.title):
                        reply_text = "It seems there are no parent comments or original post content for me to analyze in this thread. Please ensure the mention is in a comment that is part of a discussion you want analyzed."
                        print(reply_text)
                    else:
                        analysis_output = analyze_comment_thread_for_flaws(comment_thread_for_analysis)

                        formatted_analysis = f"**Overall Discussion Analysis:** {analysis_output['overall_summary']} ({analysis_output['overall_argument_type'].replace('_', ' ').capitalize()})\n\n"
                        formatted_analysis += "**Individual Comment Breakdown:**\n"

                        if analysis_output['analysis_entries']:
                            for entry in analysis_output['analysis_entries']:
                                formatted_analysis += f"- **u/{entry['username']}** (Type: {entry['argument_type'].replace('_', ' ').capitalize()}):\n"
                                formatted_analysis += f"  > *{entry['comment_summary']}*\n"  # Using blockquote for summary
                                if entry['argument_type'] == "fallacy" and entry['fallacy_type']:
                                    formatted_analysis += f"  **Fallacy Type:** {entry['fallacy_type']}\n"
                                if entry['flaw_description']:
                                    formatted_analysis += f"  **Explanation:** {entry['flaw_description']}\n"
                                formatted_analysis += "\n"  # Add extra newline for readability between entries
                        else:
                            formatted_analysis += "  *No specific arguments identified in the comments.*\n\n"

                        reply_text = f"**Argument Quality Analysis (triggered by your mention in {item.id}):**\n\n{formatted_analysis}\n\n---\n\n*Beep boop. I am a bot. This analysis is generated by AI and may not be perfect. The analysis focused on the discussion thread leading up to this comment.*"

                    try:
                        item.reply(reply_text)
                        print(f"Replied to comment {item.id}")
                        item.mark_read()
                    except praw.exceptions.RedditAPIException as e:
                        print(f"Error replying to comment {item.id}: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred while replying: {e}")
                else:
                    print(f"Bot mentioned in {item.id} but no specific analysis command found. Marking as read.")
                    #item.mark_read()
            else:
                print(f"Item {item.id} is not a relevant mention. Marking as read.")
                #item.mark_read()
        elif isinstance(item, praw.models.Message):
            print(f"Received direct message {item.id}. Marking as read.")
            #item.mark_read()

        time.sleep(1)


if __name__ == "__main__":
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, GOOGLE_API_KEY]):
        print(
            "ERROR: One or more environment variables are not set. Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, and GOOGLE_API_KEY.")
        exit(1)

    run_bot_by_mentions()