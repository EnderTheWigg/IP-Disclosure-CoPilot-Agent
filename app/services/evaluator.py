import logging
import instructor
from openai import OpenAI
from app.schemas.disclosure_schema import InventionInput, DisclosureAudit

# Configure logger for backend tracing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Initialize Instructor client pointing to local Ollama instance
# Ollama provides an OpenAI-compatible endpoint at http://localhost:11434/v1
client = instructor.from_openai(
    OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",  # Dummy key required by OpenAI client SDK
    ),
    mode=instructor.Mode.JSON,
)

# 2. Define the Patent Committee Evaluation System Prompt
SYSTEM_PROMPT = """
You are a Senior Patent Attorney and Member of an Enterprise Intellectual Property (IP) Review Committee evaluating invention disclosures in hardware, semiconductor, and embedded software domains.

CRITERIA FOR ENTERPRISE PATENT READINESS:
1. TECHNICAL VAGUENESS (Penalty): Flag generic claims (e.g., "improves performance," "makes memory faster," or "lowers power"). Require specific hardware modules, clock cycle latencies, memory registers, software subroutines, or voltage thresholds.
2. NOVELTY & DIFFERENTIATION: Identify the core technical mechanism that differentiates this disclosure from existing industry standards or prior art.
3. TECHNICAL COMPLETENESS: Ensure the submission contains clear background context, problem formulation, and actionable technical implementation details.
4. COMMERCIAL & TARGET APPLICATION: Ensure the disclosure identifies potential product lines, target markets, or end-use applications.

YOUR TASK:
Critique the submitted disclosure against these standards and return a structured audit output with an overall score (0–100), flagged vague terms, missing elements, and actionable recommendations.
"""


def evaluate_disclosure(invention: InventionInput, model_name: str = "llama3.2") -> DisclosureAudit:
    """
    Evaluates an invention disclosure against enterprise patent criteria.
    Forces Ollama output into a strict Pydantic DisclosureAudit object.
    """
    logger.info(f"Evaluating disclosure titled: '{invention.title}' using model '{model_name}'")

    # Format the user submission into a structured prompt
    user_content = f"""
    Please audit the following invention disclosure submission:

    - TITLE: {invention.title}
    - TARGET DOMAIN / PRODUCT: {invention.target_domain}
    - INVENTOR NAME: {invention.inventor_name}
    - TECHNICAL PROBLEM: {invention.problem_statement}
    - TECHNICAL SOLUTION: {invention.technical_solution}
    - NOVEL ASPECTS / CLAIMS: {invention.novel_features}
    """

    try:
        # Instructor calls Ollama and auto-retries if the returned JSON is invalid
        audit_result: DisclosureAudit = client.chat.completions.create(
            model=model_name,
            response_model=DisclosureAudit,
            max_retries=3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        return audit_result

    except Exception as e:
        logger.error(f"Failed to evaluate disclosure: {str(e)}")
        raise RuntimeError(f"Ollama evaluation failed: {str(e)}")


# 3. Direct execution test block (for quick testing via `uv run`)
if __name__ == "__main__":
    # Sample test submission (intentionally vague to test grading logic)
    test_input = InventionInput(
        title="Fast Cache Clearing Circuit",
        inventor_name="Jane Doe",
        target_domain="Microcontrollers / Automotive MCU",
        problem_statement="Cache clearing takes too many clock cycles during context switches.",
        technical_solution="We added a special hardware flag that resets cache lines faster.",
        novel_features="It resets things faster than standard software loops."
    )

    print("\n--- Running Test Evaluation against Ollama ---")
    result = evaluate_disclosure(test_input)
    print(f"\nReadiness Score: {result.overall_patent_readiness_score}/100")
    print(f"Is Ready for Filing: {result.is_ready_for_filing}")
    print(f"Clarity Critique:\n{result.clarity_critique}")
    print(f"\nSuggested Refinements:\n{result.suggested_refinements}")