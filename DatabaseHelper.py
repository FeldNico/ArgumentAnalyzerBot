import os
from sqlcipher3 import dbapi2 as sqlite3

class DatabaseHelper:
    def __init__(self):
        self.init_db()

    # --- Helper function to get a database connection ---
    def get_db_connection(self):
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(f"PRAGMA key='{os.getenv('DB_PASSPHRASE')}';")

        return conn

    # --- Database Initialization Function ---
    def init_db(self):  # Renamed to init_db for clarity, good practice
        """Initializes database tables for AnalysisContext and CommentAnalysis."""
        conn = None  # Initialize conn to None for finally block
        try:
            conn = self.get_db_connection()  # Use the helper function
            cur = conn.cursor()

            cur.execute("""CREATE TABLE IF NOT EXISTS AnalysisContext (
                analysisCommentID VARCHAR(255) PRIMARY KEY,
                triggerCommentID VARCHAR(255) NOT NULL,
                redditThreadID VARCHAR(255) NOT NULL,
                redditCommunity VARCHAR(255) NOT NULL, -- Correctly included in CREATE TABLE
                overall_summary TEXT,
                overall_argument_type VARCHAR(255)
            );""")

            cur.execute("""CREATE TABLE IF NOT EXISTS CommentAnalysis (
                redditCommentID VARCHAR(255) PRIMARY KEY,
                analysisCommentID VARCHAR(255) NOT NULL,
                author VARCHAR(255),
                comment_summary TEXT,
                argument_type VARCHAR(255),
                fallacy_type VARCHAR(255),
                flaw_description TEXT,
    
                FOREIGN KEY (analysisCommentID) REFERENCES AnalysisContext(analysisCommentID)
            );""")
            conn.commit()
            print("Database tables initialized successfully.")
        except Exception as e:
            print(f"Error during database initialization: {e}")
            # Optionally re-raise the exception if the bot cannot proceed without DB
            # raise
        finally:
            if conn:
                conn.close()  # Ensure connection is closed even if an error occurs


    # --- Function to Store Analysis ---
    def storeAnalysis(self,original_post, triggerCommentID, analysisCommentID, analysis):
        """
        Stores the overall analysis context and individual comment analyses.

        Args:
            original_post: The PRAW Submission object for the Reddit thread.
            triggerCommentID: The ID of the comment that triggered the analysis.
            analysisCommentID: A unique ID for this specific analysis instance.
            analysis: The parsed JSON output from the Gemini API.
        """
        conn = None  # Initialize conn to None
        try:
            conn = self.get_db_connection()  # Get a new connection for this operation
            cur = conn.cursor()

            # Fix: Mismatch in INSERT statement for AnalysisContext
            # Ensure column names match the VALUES and the number of placeholders
            cur.execute("""
                INSERT OR REPLACE INTO AnalysisContext (
                    analysisCommentID, 
                    triggerCommentID, 
                    redditThreadID, 
                    redditCommunity, -- Added this column to the INSERT list
                    overall_summary, 
                    overall_argument_type
                ) VALUES (?, ?, ?, ?, ?, ?); -- Ensure 6 placeholders for 6 columns
            """, (
                analysisCommentID,
                triggerCommentID,
                original_post.id,  # This is the redditThreadID (Submission ID)
                original_post.subreddit.display_name,  # Use display_name for community
                analysis["overall_summary"],
                analysis["overall_argument_type"]
            ))

            if analysis['analysis_entries']:
                for entry in analysis['analysis_entries']:
                    # The 'fallacy_type' and 'flaw_description' might be None/empty strings if not a fallacy.
                    # SQLite handles None as NULL, which is fine for TEXT fields.
                    # Ensure author exists (not deleted) before getting name
                    author_name = entry["username"] if entry["username"] else '[Deleted User]'

                    cur.execute("""
                        INSERT OR REPLACE INTO CommentAnalysis (
                            redditCommentID, 
                            analysisCommentID, 
                            author, 
                            comment_summary, 
                            argument_type, 
                            fallacy_type, 
                            flaw_description
                        ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (
                        entry["comment_id"],  # Make sure your analysis_output provides this
                        analysisCommentID,
                        author_name,
                        entry["comment_summary"],
                        entry["argument_type"],
                        entry.get("fallacy_type", None),  # Use .get() with default None for optional fields
                        entry.get("flaw_description", None)  # Use .get() with default None for optional fields
                    ))

            conn.commit()
            print(f"Analysis '{analysisCommentID}' stored successfully.")
        except Exception as e:
            print(f"Error storing analysis '{analysisCommentID}': {e}")
            # Consider logging the full traceback here for debugging: traceback.print_exc()
            # Optionally rollback if only partial data was committed
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()  # Ensure connection is closed

    def get_user_analysis_history(self,username):
        conn = None
        results = []
        try:
            conn = self.get_db_connection()
            conn.row_factory = sqlite3.Row # This allows access to columns by name
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    ca.redditCommentID,
                    ca.analysisCommentID,
                    ca.argument_type,
                    ca.fallacy_type,
                    ac.triggerCommentID,
                    ac.redditThreadID,
                    ac.redditCommunity,
                    ac.overall_argument_type AS context_overall_argument_type -- Alias
                FROM
                    CommentAnalysis AS ca
                JOIN
                    AnalysisContext AS ac ON ca.analysisCommentID = ac.analysisCommentID
                WHERE
                    ca.author = ?
                ORDER BY
                    ac.redditThreadID, ca.redditCommentID; -- Order for better readability
            """, (username,))

            # Fetch all results
            rows = cur.fetchall()

            # Convert rows to a list of dictionaries for easier use
            for row in rows:
                results.append(dict(row))

        except Exception as e:
            print(f"Error retrieving analysis history for user '{username}': {e}")
            # In a real bot, you might log this error more formally
        finally:
            if conn:
                conn.close()
        return results