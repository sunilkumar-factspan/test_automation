import os
import time
import uuid
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from pydantic import BaseModel
from automation_service import AutomationService

# ------------------------
# LOGGING CONFIG
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("automation_api")

# ------------------------
# LOAD ENV
# ------------------------
load_dotenv()

# Load environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# fallback for Streamlit secrets (if using Streamlit Cloud)
try:
    import streamlit as st
    GROQ_API_KEY = GROQ_API_KEY or st.secrets.get("GROQ_API_KEY")
except Exception:
    pass

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is required")

MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")
AGENT_MODEL = os.getenv("AGENT_MODEL", "llama-3.3-70b-versatile")

# ------------------------
# INIT APP + SERVICE
# ------------------------
app = FastAPI(title="Android UI Automation API")

service = AutomationService(
    groq_api_key=GROQ_API_KEY,
    VALIDATION_MODEL=MODEL,
    AGENT_MODEL=AGENT_MODEL,
)

execution_store = {}

# ------------------------
# REQUEST MODEL
# ------------------------
class TestCase(BaseModel):
    name: str
    steps: list[str]


# ------------------------
# EXECUTE TEST
# ------------------------
@app.post("/execute_test")
async def run_test(test_case: TestCase):
    execution_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(f"Received test: {test_case.name} | id={execution_id}")

    execution_store[execution_id] = {
        "status": "running",
        "result": None,
        "error": None,
        "start_time": start_time
    }

    try:
        result = await service.execute(
            test_case.name,
            test_case.steps
        )

        duration = round(time.time() - start_time, 2)

        execution_store[execution_id]["status"] = "completed"
        execution_store[execution_id]["result"] = result
        execution_store[execution_id]["duration"] = duration

        logger.info(f"Execution completed in {duration}s | id={execution_id}")

        return {
            "execution_id": execution_id,
            "status": "completed",
            "execution": result,
            "duration": duration
        }

    except Exception as e:
        execution_store[execution_id]["status"] = "failed"
        execution_store[execution_id]["error"] = str(e)

        logger.error(f"Execution failed | id={execution_id} | error={e}")

        raise HTTPException(status_code=500, detail=str(e))


# ------------------------
# STATUS ENDPOINT
# ------------------------
@app.get("/status/{execution_id}")
async def get_status(execution_id: str):
    if execution_id not in execution_store:
        raise HTTPException(status_code=404, detail="Execution ID not found")

    return execution_store[execution_id]


# ------------------------
# SHUTDOWN ENDPOINT
# ------------------------
@app.post("/shutdown")
async def shutdown():
    logger.info("Shutdown requested")

    try:
        await service.cleanup()
        return {"status": "shutdown_completed"}
    except Exception as e:
        logger.error(f"Shutdown failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))