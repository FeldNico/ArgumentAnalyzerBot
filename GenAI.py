import json

from google import genai


class GenAI:
    def __init__(self):

        self.API = genai.Client()
        with open("prompt.txt", 'r', encoding='utf-8') as f:
            self.systemPrompt = f.read()
        with open("response_schema.json", 'r', encoding='utf-8') as f:
            self.schema = json.load(f)

    def analyze_comment_thread_for_flaws(self,comment_thread_text):
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
                self.systemPrompt,
                f"Reddit Comment Thread for Analysis:\n\n{comment_thread_text}"
            ]

            # Call the Gemini model with structured output configuration
            response = self.API.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_parts,
                config={
                    "temperature": 0.0,
                    "response_mime_type": "application/json",  # Request JSON output
                    "response_schema": self.schema,  # Provide the defined schema
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