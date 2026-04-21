import time
from fastapi import FastAPI                        # the web framework
from fastapi.middleware.cors import CORSMiddleware # allows browser to call this API
from fastapi.staticfiles import StaticFiles        # serves index.html as a static file
from fastapi.responses import FileResponse         # sends index.html when you open /
from pydantic import BaseModel                     # validates incoming request data

from database import create_database               # our DB builder
from llm import generate_sql                       # our LLM function
from query_runner import run_query                 # our SQL runner

#CREATE THE APP 
#This one line creates the entire FastAPI application
#Think of `app` as the server object — everything attaches to it
app = FastAPI(title="IPL Query Engine", version="1.0")

#CORS MIDDLEWARE
#CORS = Cross Origin Resource Sharing
#Without this, the browser BLOCKS requests from index.html → api.py
#Because they're on different "origins" (even though both are localhost)
#allow_origins=["*"] means — accept requests from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],   # allow GET, POST, PUT, DELETE etc.
    allow_headers=["*"],   # allow all headers
)

#BUILD DATABASE ON STARTUP
#When the server starts, immediately check if ipl.db exists
#If not → build it from CSVs automatically
#If yes → skip (database.py handles this check internally)
create_database()

#REQUEST MODEL
#This defines what shape of data we EXPECT from the browser
#When browser sends: {"question": "Who hit most sixes?"}
#Pydantic automatically validates it matches this model
#If browser sends wrong data → FastAPI auto-returns a 422 error
class QuestionRequest(BaseModel):
    question: str   # must have a "question" field, must be a string

#THE MAIN ENDPOINT
# @app.post("/query") means:
#   → when a POST request hits the URL /query
#   → run the function below
# This is the only endpoint our frontend calls
@app.post("/query")
def query(req: QuestionRequest):
    """
    Receives a plain English question.
    Returns SQL + query results as JSON.
    """

    # start the clock — we want to show response time in the UI
    start = time.time()

    #Step 1: Generate SQL 
    # Send the question to llm.py
    # Returns: (sql_string, source_name)
    # source_name is either "Groq ☁️" or "Ollama 🦙"
    sql, source = generate_sql(req.question)

    #Step 2: Run SQL on ipl.db 
    # Send the generated SQL to query_runner.py
    # Returns: (DataFrame, None) on success
    #          (None, error_message) on failure
    df, error = run_query(sql)

    # calculate how long the whole thing took
    latency = round(time.time() - start, 2)

    #Step 3: Return result 
    # If SQL had an error — return the error so UI can show it
    if error:
        return {
            "sql"      : sql,
            "source"   : source,
            "error"    : error,
            "columns"  : [],
            "rows"     : [],
            "row_count": 0,
            "latency"  : latency,
        }

    # If success — return columns + rows as lists
    # Why lists? Because JSON doesn't understand pandas DataFrames
    # .columns gives column names, .values.tolist() gives rows as nested list
    return {
        "sql"      : sql,
        "source"   : source,
        "error"    : None,
        "columns"  : list(df.columns),
        "rows"     : df.values.tolist(),   # [[val1,val2], [val1,val2], ...]
        "row_count": len(df),
        "latency"  : latency,
    }

#SERVE index.html 
# This mounts the current folder (.) as a static file server
# So when browser requests /index.html → it gets the file
# IMPORTANT: This must come AFTER all @app routes
# Otherwise it would intercept the /query route
app.mount("/", StaticFiles(directory=".", html=True), name="static")

#ROOT ROUTE 
# When someone opens http://localhost:8000 in browser
# This explicitly sends index.html
# (The StaticFiles mount above handles this too, but explicit is better)
@app.get("/")
def root():
    return FileResponse("index.html")