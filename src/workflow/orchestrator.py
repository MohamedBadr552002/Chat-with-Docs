"""
LCEL-based Evaluator–Generator workflow orchestrator.

Implements the iterative feedback loop:
  User Question → Generator → Answer → Evaluator → Decision
    ├─ Accept → Final Answer
    └─ Reject → Feedback → Generator → (repeat, max 4 iterations)

State is tracked via a WorkflowState dataclass and the loop is
implemented as a pure Python LCEL-composable runnable.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Callable

from langchain_core.runnables import RunnableLambda

from src.agents.generator import GeneratorAgent
from src.agents.evaluator import EvaluatorAgent
from src.utils.config import MAX_ITERATIONS
from src.utils.logger_config import logger


# ─── State Model ─────────────────────────────────────────────────────────────

@dataclass
class IterationRecord:
    """Record of a single Generator→Evaluator iteration."""
    iteration: int
    answer: str
    evaluation: dict
    context_used: str


@dataclass
class WorkflowState:
    """Mutable state carried through the feedback loop."""
    question: str
    iterations: List[IterationRecord] = field(default_factory=list)
    current_answer: str = ""
    current_feedback: Optional[str] = None
    final_decision: str = "pending"
    loop_count: int = 0
    terminated_by_limit: bool = False


# ─── Orchestrator ─────────────────────────────────────────────────────────────

class WorkflowOrchestrator:
    """
    Evaluator–Generator workflow with LCEL-style composition.

    The workflow is exposed as two entry points:
      • run(question) — full synchronous execution
      • run_streaming(question, callback) — step-by-step with callback for UI updates
    """

    def __init__(
        self,
        generator: Optional[GeneratorAgent] = None,
        evaluator: Optional[EvaluatorAgent] = None,
        max_iterations: int = MAX_ITERATIONS,
    ):
        self.generator = generator or GeneratorAgent()
        self.evaluator = evaluator or EvaluatorAgent()
        self.max_iterations = max_iterations
        logger.info(
            f"WorkflowOrchestrator initialised "
            f"(max_iterations={self.max_iterations})"
        )

    # ── LCEL Runnables ─────────────────────────────────────────────────────────

    def _generate_step(self) -> RunnableLambda:
        """LCEL runnable wrapping the Generator."""
        def _run(state: WorkflowState) -> WorkflowState:
            result = self.generator.generate(
                question=state.question,
                feedback=state.current_feedback,
                iteration=state.loop_count + 1,
            )
            state.current_answer = result["answer"]
            # Store context on the state for evaluator
            state._last_context = result.get("context_used", "")
            return state
        return RunnableLambda(_run)

    def _evaluate_step(self) -> RunnableLambda:
        """LCEL runnable wrapping the Evaluator."""
        def _run(state: WorkflowState) -> WorkflowState:
            context = getattr(state, "_last_context", "")
            evaluation = self.evaluator.evaluate(
                question=state.question,
                answer=state.current_answer,
                context=context,
            )
            state.loop_count += 1
            record = IterationRecord(
                iteration=state.loop_count,
                answer=state.current_answer,
                evaluation=evaluation,
                context_used=context,
            )
            state.iterations.append(record)

            if evaluation["decision"] == "accept":
                state.final_decision = "accept"
                state.current_feedback = None
            else:
                state.final_decision = "reject"
                state.current_feedback = evaluation.get("feedback", "")
            return state
        return RunnableLambda(_run)

    # ── Main Run Methods ───────────────────────────────────────────────────────

    def run(self, question: str) -> dict:
        """
        Execute the full Evaluator–Generator feedback loop.

        Returns a result dict with:
          - final_answer: str
          - iterations: list of IterationRecord dicts
          - total_iterations: int
          - terminated_by_limit: bool
          - final_score: float
          - final_decision: str
        """
        logger.info(f"[Workflow] Starting for question: '{question[:80]}…'")

        state = WorkflowState(question=question)
        generate_step = self._generate_step()
        evaluate_step = self._evaluate_step()

        while state.loop_count < self.max_iterations:
            logger.info(f"[Workflow] Iteration {state.loop_count + 1}/{self.max_iterations}")

            # Generate
            state = generate_step.invoke(state)

            # Evaluate
            state = evaluate_step.invoke(state)

            logger.info(
                f"[Workflow] Iter {state.loop_count}: "
                f"decision={state.final_decision}, "
                f"score={state.iterations[-1].evaluation.get('overall_score', 0):.1f}"
            )

            if state.final_decision == "accept":
                logger.info(f"[Workflow] Answer accepted at iteration {state.loop_count}.")
                break
        else:
            # Max iterations reached without acceptance
            state.terminated_by_limit = True
            logger.warning(
                f"[Workflow] Max iterations ({self.max_iterations}) reached "
                f"without acceptance. Returning last answer."
            )

        return self._build_result(state)

    def run_streaming(
        self,
        question: str,
        on_iteration: Callable[[dict], None],
    ) -> dict:
        """
        Execute the feedback loop with per-iteration callbacks for live UI updates.

        Args:
            question: User's question.
            on_iteration: Callable invoked after each Generator→Evaluator cycle.
                          Receives a dict with iteration details.

        Returns:
            Same result dict as run().
        """
        logger.info(f"[Workflow] Streaming run for: '{question[:80]}…'")

        state = WorkflowState(question=question)
        generate_step = self._generate_step()
        evaluate_step = self._evaluate_step()

        while state.loop_count < self.max_iterations:
            logger.info(f"[Workflow] Streaming iteration {state.loop_count + 1}/{self.max_iterations}")

            state = generate_step.invoke(state)
            state = evaluate_step.invoke(state)

            record = state.iterations[-1]
            on_iteration({
                "iteration": record.iteration,
                "answer": record.answer,
                "evaluation": record.evaluation,
                "decision": state.final_decision,
                "feedback": state.current_feedback,
            })

            if state.final_decision == "accept":
                break
        else:
            state.terminated_by_limit = True
            logger.warning("[Workflow] Max iterations reached.")

        return self._build_result(state)

    def _build_result(self, state: WorkflowState) -> dict:
        """Serialise the final WorkflowState into a clean result dict."""
        last_eval = state.iterations[-1].evaluation if state.iterations else {}
        final_score = last_eval.get("overall_score", 0.0)

        result = {
            "final_answer": state.current_answer,
            "final_decision": state.final_decision,
            "final_score": final_score,
            "total_iterations": state.loop_count,
            "terminated_by_limit": state.terminated_by_limit,
            "iterations": [
                {
                    "iteration": r.iteration,
                    "answer": r.answer,
                    "evaluation": r.evaluation,
                }
                for r in state.iterations
            ],
        }

        if state.terminated_by_limit:
            result["warning"] = (
                f"Maximum iterations ({self.max_iterations}) reached. "
                "The answer below is the best generated but could not be "
                "fully validated by the Evaluator."
            )

        return result

    def reset_agents(self) -> None:
        """Clear both agent memories for a fresh session."""
        self.generator.clear_memory()
        self.evaluator.clear_memory()
        logger.info("[Workflow] Both agent memories cleared.")
