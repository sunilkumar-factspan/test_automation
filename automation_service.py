import os
import logging
import asyncio
from groq import Groq
from langchain_groq import ChatGroq

logger = logging.getLogger("automation_service")

class AutomationService:
    def __init__(
        self,
        groq_api_key: str | None = None,
        VALIDATION_MODEL: str = "llama-3.3-70b-versatile",
        AGENT_MODEL: str = "llama-3.3-70b-versatile",
    ):
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY is required")

        logger.info("Initializing AutomationService with Groq")

        self.groq_api_key = groq_api_key
        self.groq_client = Groq(api_key=self.groq_api_key)
        self.validation_model = VALIDATION_MODEL
        self.agent_model = AGENT_MODEL

        # Initialize LangChain Groq models
        self.llm = ChatGroq(
            model=VALIDATION_MODEL,
            temperature=0,
            api_key=self.groq_api_key,
        )
        self.agent_llm = ChatGroq(
            model=AGENT_MODEL,
            temperature=0,
            api_key=self.groq_api_key,
        )

        self.prompt_template = self._load_prompt("system_prompt.md")
        self.validation_prompt = self._load_prompt("improve_steps.md")

    def _load_prompt(self, file_name: str):
        try:
            with open(file_name, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load prompt: {e}")
            raise

    async def _groq_invoke(self, text: str, model: str) -> str:
        if not self.groq_client:
            raise RuntimeError("GROQ client not initialized")

        response = self.groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": text}],
            temperature=0,
            max_tokens=1024,
        )

        return response.choices[0].message.content.strip()

    async def _ensure_ready(self) -> bool:
        logger.info("GROQ mode enabled: ready to process requests")
        return True

    async def format_steps(self, raw_steps_text: str) -> str:
        logger.info("Refining raw steps using LLM validation prompt")

        prompt = f"""
{self.validation_prompt}

# Raw User Steps:
{raw_steps_text}
"""
        refined_text = await self._groq_invoke(prompt, self.validation_model)
        logger.info(f"Refined steps generated (GROQ):\n{refined_text}")
        return refined_text

    async def execute(self, test_name: str, steps: list[str]):
        logger.info(f"Executing test: {test_name}")

        raw_steps_text = "\n".join([f"- {step}" for step in steps])
        
        # Execute setup and formatting concurrently
        setup_status, refined_steps_text = await asyncio.gather(
            self._ensure_ready(),
            self.format_steps(raw_steps_text)
        )

        logger.info(f"Setup status returned: {setup_status}")

        execution_prompt = f"""
You are a strict mobile automation executor. Follow the steps exactly and summarize the execution result.

Refined steps:
{refined_steps_text}
"""
        result_text = await self._groq_invoke(execution_prompt, self.agent_model)
        logger.info("Execution completed via GROQ")
        return result_text

    async def cleanup(self):
        logger.info("Cleanup completed")