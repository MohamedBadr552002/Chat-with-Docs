"""
Evaluator Agent — judges the quality of Generator answers.

Evaluation dimensions:
  • Accuracy      — factual correctness relative to context
  • Relevance     — directly addresses the user's question
  • Completeness  — covers all important aspects
  • Grounding     — claims are supported by retrieved context
  • No hallucination — no invented facts
  • Overall quality

Returns a structured decision: accept | reject, with a numeric score
and actionable feedback when the answer needs improvement.
Maintains isolated ConversationBufferMemory.
"""

import json
import re
from typing import Optional, List

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_openai import ChatOpenAI

from src.knowledge.cache import get_cached_evaluation, cache_evaluation
from src.utils.config import EVALUATOR_MODEL, GOOGLE_API_KEY
from src.utils.logger_config import logger

# ─── System prompt ─────────────────────────────────────────────────────────────
EVALUATOR_SYSTEM_PROMPT = """You are a strict and objective Answer Quality Evaluator.

Your task is to evaluate whether a Generated Answer adequately addresses the User Question,
given the Available Context retrieved from the knowledge base.

Evaluate on these six dimensions (each scored 0–10):
  1. Accuracy      — Is every factual claim correct and traceable to the context?
  2. Relevance     — Does the answer directly address what was asked?
  3. Completeness  — Are all important aspects of the question covered?
  4. Grounding     — Are claims backed by the provided context?
  5. No hallucination — Does the answer avoid inventing unsupported information?
  6. Clarity       — Is the answer well-structured and easy to understand?

Evaluation History (for continuity):
{history}

You MUST return your evaluation as a valid JSON object with exactly this structure:
{{
  "decision": "accept" or "reject",
  "overall_score": <float 0.0–10.0>,
  "dimension_scores": {{
    "accuracy": <0–10>,
    "relevance": <0–10>,
    "completeness": <0–10>,
    "grounding": <0–10>,
    "no_hallucination": <0–10>,
    "clarity": <0–10>
  }},
  "feedback": "<detailed actionable feedback if rejecting, or 'Answer meets quality standards.' if accepting>",
  "reasoning": "<brief explanation of your decision>"
}}

Acceptance threshold: overall_score >= 7.5 AND no individual dimension below 6.0.
If the answer says 'not available in the provided sources' and the question genuinely cannot
be answered from the context, this is CORRECT behaviour — score it highly.
"""

EVALUATOR_HUMAN_TEMPLATE = """User Question:
{question}

Available Context (from knowledge base):
<context>
{context}
</context>

Generated Answer:
{answer}

Evaluate the answer now and return your JSON response."""


class EvaluatorAgent:
    """
    Evaluator LLM Agent with isolated memory.

    Responsibilities:
      - Score the Generator's answer on six quality dimensions.
      - Return accept/reject decision with structured feedback.
      - Maintain independent evaluation history.
    """

    ACCEPT_THRESHOLD = 7.5
    MIN_DIMENSION_SCORE = 6.0

    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set. Please configure your .env file.")

        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            model=EVALUATOR_MODEL,
            api_key=GOOGLE_API_KEY,
            temperature=0.1,
            max_tokens=4096,
            model_kwargs={"response_format": {"type": "json_object"}},
        )


        # self._llm = ChatGoogleGenerativeAI(
        #     model=EVALUATOR_MODEL,
        #     google_api_key=GOOGLE_API_KEY,
        #     temperature=0.1,
        #     max_output_tokens=1024,
        # )

        # Isolated memory — completely separate from Generator memory
        self._memory = InMemoryChatMessageHistory()

        self._prompt = ChatPromptTemplate.from_messages([
            ("system", EVALUATOR_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", EVALUATOR_HUMAN_TEMPLATE),
        ])

        self._chain = self._prompt | self.llm | StrOutputParser()
        logger.info(f"EvaluatorAgent initialised with model: {EVALUATOR_MODEL}")

    # ─── Public API ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        question: str,
        answer: str,
        context: str,
    ) -> dict:
        """
        Evaluate a generated answer.

        Args:
            question: Original user question.
            answer: Generator's answer to evaluate.
            context: Retrieved context string used by the Generator.

        Returns:
            dict with: decision, overall_score, dimension_scores, feedback, reasoning.
        """
        logger.info("[Evaluator] Starting evaluation…")

        # ── Redis cache check ─────────────────────────────────────────────────
        cached = get_cached_evaluation(question, answer)
        if cached is not None:
            logger.info("[Evaluator] Returning cached evaluation.")
            return cached

        # ── Load memory ───────────────────────────────────────────────────────
        history = self._memory.messages

        # ── Invoke chain ──────────────────────────────────────────────────────
        try:
            raw_response = self._chain.invoke({
                "history": history,
                "question": question,
                "context": context,
                "answer": answer,
            })
        except Exception as e:
            logger.error(f"[Evaluator] LLM invocation failed: {e}")
            evaluation = self._fallback_evaluation(str(e))
            logger.warning("[Evaluator] Returning conservative fallback evaluation.")
            return evaluation

        # ── Parse JSON response ───────────────────────────────────────────────
        evaluation = self._parse_evaluation(raw_response, question, answer)

        # ── Save to memory ────────────────────────────────────────────────────
        summary = (
            f"Evaluated answer with score {evaluation['overall_score']:.1f} "
            f"→ {evaluation['decision'].upper()}"
        )
        self._memory.add_message(HumanMessage(content=f"Evaluate: {question[:100]}"))
        self._memory.add_message(AIMessage(content=summary))

        # ── Cache result ──────────────────────────────────────────────────────
        cache_evaluation(question, answer, evaluation)

        logger.info(
            f"[Evaluator] Decision: {evaluation['decision'].upper()} "
            f"(score={evaluation['overall_score']:.1f})"
        )
        return evaluation

    def _parse_evaluation(self, raw: str, question: str, answer: str) -> dict:
        """
        Parse the LLM's JSON response. Falls back to a safe default if parsing fails.
        Also enforces the acceptance threshold logic.
        """
        try:
            # Strip markdown code fences if present
            cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
            data = json.loads(cleaned)

            # Validate required keys
            required = {"decision", "overall_score", "dimension_scores", "feedback", "reasoning"}
            if not required.issubset(data.keys()):
                raise ValueError(f"Missing keys: {required - data.keys()}")

            # Enforce threshold logic (in case LLM misjudges)
            score = float(data["overall_score"])
            dims = data.get("dimension_scores", {})
            min_dim = min(dims.values()) if dims else 10

            if score >= self.ACCEPT_THRESHOLD and min_dim >= self.MIN_DIMENSION_SCORE:
                data["decision"] = "accept"
            else:
                data["decision"] = "reject"

            data["overall_score"] = round(score, 2)
            return data

        except Exception as e:
            logger.warning(f"[Evaluator] Failed to parse JSON response: {e}. Using fallback.")
            logger.debug(f"[Evaluator] Raw response: {raw[:500]}")
            # Conservative fallback — reject with low score and ask for retry
            return {
                "decision": "reject",
                "overall_score": 4.0,
                "dimension_scores": {
                    "accuracy": 4, "relevance": 4, "completeness": 4,
                    "grounding": 4, "no_hallucination": 4, "clarity": 4,
                },
                "feedback": (
                    "The evaluation could not be parsed. Please ensure the answer is "
                    "well-structured, grounded in the provided context, and directly "
                    "addresses the question."
                ),
                "reasoning": "Evaluation parsing failed — conservative reject applied.",
                "parse_error": str(e),
            }

    @staticmethod
    def _fallback_evaluation(error: str) -> dict:
        """Return a visible evaluation when the provider is unavailable."""
        return {
            "decision": "reject",
            "overall_score": 0.0,
            "dimension_scores": {
                "accuracy": 0, "relevance": 0, "completeness": 0,
                "grounding": 0, "no_hallucination": 0, "clarity": 0,
            },
            "feedback": (
                "The answer was generated, but the Evaluator LLM was unavailable. "
                "Retry shortly or choose an available evaluator model."
            ),
            "reasoning": "Provider error; conservative reject applied.",
            "provider_error": error[:500],
        }

    def clear_memory(self) -> None:
        """Clear the Evaluator's conversation memory."""
        self._memory.clear()
        logger.info("[Evaluator] Memory cleared.")

    def get_memory_summary(self) -> List:
        """Return the current memory messages for inspection."""
        return self._memory.messages
