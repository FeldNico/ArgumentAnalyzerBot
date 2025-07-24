import json
import time
from threading import Thread

from google import genai
from google.genai import types


class GenAI:
    def __init__(self):

        self.API = genai.Client()
        with open("prompts/fallacy_prompt.txt", 'r', encoding='utf-8') as f:
            self.fallacyPrompt = f.read()
        with open("prompts/claim_extraction_prompt.txt", 'r', encoding='utf-8') as f:
            self.claimPrompt = f.read()
        with open("prompts/factcheck_prompt.txt", 'r', encoding='utf-8') as f:
            self.factchecking_prompt = f.read()
        with open("schemas/fallacy_response_schema.json", 'r', encoding='utf-8') as f:
            self.fallacy_response_schema = json.load(f)
        with open("schemas/claims_response_schema.json", 'r', encoding='utf-8') as f:
            self.claim_response_schema = json.load(f)
        with open("schemas/fact_check_output_schema.json", 'r', encoding='utf-8') as f:
            self.factchecking_schema = json.load(f)

        self.groundingTool = types.Tool(
            google_search=types.GoogleSearch()
        )

    def extract_claims_from_thread(self, comment_thread_text):
        if not comment_thread_text.strip():
            # Return default structure if no text to analyze
            return {
                "claim_entries": [],
            }

        try:
            # Construct the prompt for the Gemini model

            prompt_parts = [
                self.claimPrompt,
                f"Reddit Comment Thread for Analysis:\n\n{comment_thread_text}"
            ]

            # Call the Gemini model with structured output configuration
            response = self.API.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_parts,
                config={
                    "temperature": 0.0,
                    "response_mime_type": "application/json",  # Request JSON output
                    "response_schema": self.claim_response_schema,  # Provide the defined schema
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
                    "claim_entries": [],
                }

        except Exception as e:
            print(f"An unexpected error occurred during Gemini API call: {e}")
            return {
                "claim_entries": [],
            }

    def factcheckClaims(self, claims):
        if not claims or not claims.get('claim_entries'):
            return []

        threads = []
        responses = []

        for entry in claims['claim_entries']:
            username = entry.get('username', 'N/A')
            comment_id = entry.get('comment_id', 'N/A')
            claim = entry.get('claim', '')
            arguments = entry.get('arguments_entries', [])

            if not claim:
                continue  # Skip if claim is empty or invalid

            # Construct the factual query for the grounded model
            # Emphasize factual verification, neutrality, and source citation.
            # Ensure the prompt is clear that it needs to *use* the search tool.
            fact_check_query_text = (
                f"{self.factchecking_prompt}\n\n"+
                f"Claim to fact-check: {claim}\n"+
                f"Supporting arguments: {'; '.join(arguments) if arguments else 'None provided.'}\n\n"
            )

            def sendGroundingPrompts():
                response = self.API.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=fact_check_query_text,
                    config={
                        "temperature": 0.0,
                        "response_mime_type": "application/json",  # Request JSON output
                        "response_schema": self.factchecking_schema,  # Provide the defined schema
                    },
                    # safety_settings=... # Optionally add safety settings if needed
                )
                responses.append(response)

            t = Thread(target=sendGroundingPrompts)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return responses

    def analyze_comment_thread_for_flaws(self, comment_thread_text):
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
                self.fallacyPrompt,
                f"Reddit Comment Thread for Analysis:\n\n{comment_thread_text}"
            ]

            # Call the Gemini model with structured output configuration
            response = self.API.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_parts,
                config={
                    "temperature": 0.0,
                    "response_mime_type": "application/json",  # Request JSON output
                    "response_schema": self.fallacy_response_schema,  # Provide the defined schema
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
