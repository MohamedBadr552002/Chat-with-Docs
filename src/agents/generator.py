from typing import Optional, List

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI


from langchain_openai import ChatOpenAI
from src.knowledge.retriever import retrieve_context, format_context
from src.knowledge.cache import get_cached_llm_response, cache_llm_response
from src.utils.config import GENERATOR_MODEL, GOOGLE_API_KEY
from src.utils.logger_config import logger

# System prompt 
GENERATOR_SYSTEM_PROMPT = """You are a precise and reliable Question-Answering Assistant.

Your primary responsibility is to answer the user's question using ONLY the information
provided in the <context> section below. You must NOT invent, guess, or extrapolate
information that is not directly supported by the context.

Rules you MUST follow:
1. Base your answer exclusively on the provided context.
2. If the context does not contain sufficient information to answer the question,
   explicitly say: "The required information is not available in the provided knowledge sources."
3. If you receive feedback from the Evaluator, carefully address every point raised
   and produce an improved answer.
4. Be concise, accurate, and complete.
5. Cite the source when possible (e.g., "According to [Source 1]…").
6. Do NOT hallucinate facts, statistics, or names not present in the context.

Conversation history (for context continuity):
{history}

Context from Knowledge Base:
<context>
{context}
</context>
"""

GENERATOR_HUMAN_TEMPLATE = """{question}

{feedback_section}"""


class GeneratorAgent:
    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set. Please configure your .env file.")

        
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            model=GENERATOR_MODEL,
            api_key=GOOGLE_API_KEY,
            temperature=0.2,
            max_tokens=2048,
        )



        # self._llm = ChatGoogleGenerativeAI(
        #     model=GENERATOR_MODEL,
        #     google_api_key=GOOGLE_API_KEY,
        #     temperature=0.2,
        #     max_output_tokens=2048,
        # )

        # Isolated memory — only Generator accesses this instance
        self._memory = InMemoryChatMessageHistory()

        self._prompt = ChatPromptTemplate.from_messages([
            ("system", GENERATOR_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", GENERATOR_HUMAN_TEMPLATE),
        ])

        self._chain = self._prompt | self.llm | StrOutputParser()
        logger.info(f"GeneratorAgent initialised with model: {GENERATOR_MODEL}")

    # Public API 

    def generate(
        self,
        question: str,
        feedback: Optional[str] = None,
        iteration: int = 1,
    ) -> dict:
        """
        Generate an answer for the given question.

        Args:
            question: The user's original question.
            feedback: Evaluator feedback from the previous iteration (or None).
            iteration: Current loop iteration number.

        Returns:
            dict with keys: answer, context_used, iteration.
        """
        logger.info(f"[Generator] Generating answer (iteration {iteration})…")

        #  Retrieve context 
        context_docs = retrieve_context(question)
        context_str = format_context(context_docs)

        #  Build feedback section 
        if feedback and iteration > 1:
            feedback_section = (
                f"\n\n[EVALUATOR FEEDBACK — please address all points below in your improved answer]\n"
                f"{feedback}"
            )
        else:
            feedback_section = ""

        # ── Redis cache check (only on first iteration with no feedback) ───────
        cache_key = f"{question}|iter{iteration}|{feedback or ''}"
        cached = get_cached_llm_response(cache_key)
        if cached:
            logger.info("[Generator] Returning cached LLM response.")
            return {
                "answer": cached,
                "context_used": context_str,
                "iteration": iteration,
                "cached": True,
            }

        #  Load memory 
        history = self._memory.messages

        #  Invoke chain 
        try:
            answer = self._chain.invoke({
                "history": history,
                "context": context_str,
                "question": question,
                "feedback_section": feedback_section,
            })
        except Exception as e:
            logger.error(f"[Generator] LLM invocation failed: {e}")
            raise

        #  Save to memory 
        self._memory.add_message(HumanMessage(content=question))
        self._memory.add_message(AIMessage(content=answer))

        #  Cache response 
        cache_llm_response(cache_key, answer)

        logger.info(f"[Generator] Answer produced ({len(answer)} chars).")
        return {
            "answer": answer,
            "context_used": context_str,
            "iteration": iteration,
            "cached": False,
        }

    def clear_memory(self) -> None:
        """Clear the Generator's conversation memory."""
        self._memory.clear()
        logger.info("[Generator] Memory cleared.")

    def get_memory_summary(self) -> List:
        """Return the current memory messages for inspection."""
        return self._memory.messages
