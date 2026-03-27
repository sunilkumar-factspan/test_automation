import os
import time
import uuid
import logging
import asyncio
import streamlit as st
from dotenv import load_dotenv

from app import MODEL
from automation_service import AutomationService

# ------------------------
# LOGGING CONFIG
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("automation_streamlit")

# ------------------------
# LOAD ENV
# ------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is required")

VALIDATION_MODEL = os.getenv("VALIDATION_MODEL", "llama-3.3-70b-versatile")
AGENT_MODEL = os.getenv("AGENT_MODEL", "llama-3.3-70b-versatile")
# ------------------------
# INIT SERVICE (PERSIST)
# ------------------------
if "service" not in st.session_state:
    st.session_state.service = AutomationService(
        groq_api_key=GROQ_API_KEY,
        VALIDATION_MODEL=VALIDATION_MODEL,
        AGENT_MODEL=AGENT_MODEL,
    )

if "execution_store" not in st.session_state:
    st.session_state.execution_store = {}

service = st.session_state.service
execution_store = st.session_state.execution_store

# ------------------------
# UI
# ------------------------
st.title("Android UI Automation")

test_name = st.text_input("Test Name")

steps_input = st.text_area(
    "Steps (one per line)",
    height=200
)

col1, col2 = st.columns(2)

# ------------------------
# EXECUTION
# ------------------------
def run_async(coro):
    return asyncio.run(coro)

if col1.button("Execute Test"):
    if not test_name or not steps_input.strip():
        st.error("Test name and steps are required")
    else:
        steps = [s.strip() for s in steps_input.split("\n") if s.strip()]
        execution_id = str(uuid.uuid4())

        st.info(f"Execution started | id={execution_id}")

        execution_store[execution_id] = {
            "status": "running",
            "result": None,
            "error": None
        }

        start_time = time.time()

        try:
            result = run_async(service.execute(test_name, steps))

            duration = round(time.time() - start_time, 2)

            execution_store[execution_id]["status"] = "completed"
            execution_store[execution_id]["result"] = result
            execution_store[execution_id]["duration"] = duration

            st.success(f"Completed in {duration}s")
            st.code(result)

        except Exception as e:
            execution_store[execution_id]["status"] = "failed"
            execution_store[execution_id]["error"] = str(e)

            st.error(f"Execution failed: {e}")

# ------------------------
# STATUS VIEW
# ------------------------
st.subheader("Execution History")

if execution_store:
    for exec_id, data in execution_store.items():
        with st.expander(f"{exec_id} | {data['status']}"):
            st.write(data)
else:
    st.write("No executions yet")

# ------------------------
# SHUTDOWN
# ------------------------
if col2.button("Shutdown MCP"):
    try:
        run_async(service.cleanup())
        st.success("MCP connection closed")
    except Exception as e:
        st.error(f"Shutdown failed: {e}")