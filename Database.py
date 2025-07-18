import sqlite3

con = sqlite3.connect("database.db")
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS AnalysisContext (
    analysisCommentID VARCHAR(255) PRIMARY KEY,                         -- The unique ID for this analysis case (defined by you, not auto-incremented)
    triggerCommentID VARCHAR(255) NOT NULL,                             -- The ID of the comment that triggered the analysis
    redditThreadID VARCHAR(255) NOT NULL,                      -- The ID of the overall Reddit thread/submission
    overall_summary TEXT,                                      -- A new field for the summary of the entire interaction or thread
    overall_argument_type VARCHAR(255)                         -- A new field for the main argument type of the overall interaction
);""")
cur.execute("""CREATE TABLE IF NOT EXISTS CommentAnalysis (
    redditCommentID VARCHAR(255) PRIMARY KEY,                  -- The unique ID from Reddit for the specific comment being analysed
    analysisCommentID VARCHAR(255) NOT NULL,                     -- Links to the context; must be unique to enforce a one-to-one relationship
    author VARCHAR(255),                                       -- The username of the comment's author
    comment_summary TEXT,                                      -- A summary of this specific comment
    argument_type VARCHAR(255),                                -- The type of argument identified in this specific comment
    fallacy_type VARCHAR(255),                                 -- The specific type of fallacy identified
    flaw_description TEXT,                                     -- A detailed description of the logical flaw in this comment
    
    FOREIGN KEY (analysisCommentID) REFERENCES AnalysisContext(analysisCommentID)
);""")

def storeAnalysis(threadID,triggerCommentID, analysisCommentID, analysis):
    cur.execute("""
        INSERT OR IGNORE INTO AnalysisContext (
            analysisCommentID, 
            triggerCommentID, 
            redditThreadID, 
            overall_summary, 
            overall_argument_type
        ) VALUES (?, ?, ?, ?, ?);
    """, (analysisCommentID, triggerCommentID,threadID, analysis["overall_summary"],analysis["overall_argument_type"]))
    if analysis['analysis_entries']:
        for entry in analysis['analysis_entries']:
            cur.execute("""
                INSERT OR IGNORE INTO CommentAnalysis (
                    redditCommentID, 
                    analysisCommentID, 
                    author, 
                    comment_summary, 
                    argument_type, 
                    fallacy_type, 
                    flaw_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, ())
