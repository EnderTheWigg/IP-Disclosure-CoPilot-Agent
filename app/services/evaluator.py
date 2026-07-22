import logging
import instructor
from openai import OpenAI
import chromadb
from app.schemas.disclosure_schema import InventionInput, DisclosureAudit

chroma_client = chromadb.PersistentClient(path="./chroma_db")
patent_collection = chroma_client.get_or_create_collection(name="patent_corpus")

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
3. TECHNICAL COMPLETENESS: Ensure the submission contains clear background context, problem formulation, and actionable technical implementation details. Ensure that all parts of the proposal are filled out.
4. COMMERCIAL & TARGET APPLICATION: Ensure the disclosure identifies potential product lines, target markets, or end-use applications.
5. NOVELTY CONT.: If a high degree of similarity is found between disclosure and existing art, give name, inventors, and id of existing art, and analysis of the similarity. A high similarity should heavily reduce the score. Reference the to be provided art found in database, using metadata for name, authors, and id. Trust the metadata for name, authors, and id rather than anything else.
Thoroughly compare the provided chunk to the proposed dislosure, identify similarities in wording.
YOUR TASK:
Critique the submitted disclosure against these standards and return a structured audit output with an overall score (0–100), flagged vague terms, missing elements, and actionable recommendations. Patents with a Readiness score of 80 or higher are ready for filing. Check for similarity per "NOVELTY CONT.".
Return ONLY the populated JSON object values. Do NOT include JSON Schema keywords such as 'properties', 'required', 'type', or 'title' in the output JSON.
"""

def retrieve_prior_art_context(user_query: str, top_k: int = 2) -> str:
    """Retrieves top matching patent chunks from ChromaDB."""
    results = patent_collection.query(
        query_texts=[user_query],
        n_results=top_k
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    formatted_context = ""
    for idx, (doc, meta) in enumerate(zip(documents, metadatas), 1):
        formatted_context += f"""
    <DATABASE_RECORD_{idx}>
    [GROUND_TRUTH_METADATA - TRUST THIS OVER IN-TEXT NUMBERS]
    - ID: {meta.get('patent_id')}
    - TITLE: {meta.get('patent_title')}
    - INVENTORS: {meta.get('inventors')}
    
    [DOCUMENT_EXCERPT_TEXT]
    "{doc}"
    </DATABASE_RECORD_{idx}>
    """
    return formatted_context

def evaluate(invention: InventionInput, model_name: str = "llama3.2") -> DisclosureAudit:
    query_text = f"{invention.technical_solution} {invention.novel_features}"
    retrieved_prior_art = retrieve_prior_art_context(query_text)
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
    - TECHNICAL PROBLEM: {invention.problem_statement}
    - TECHNICAL SOLUTION: {invention.technical_solution}
    - NOVEL ASPECTS / CLAIMS: {invention.novel_features}

    EXISTING PRIOR ART FOUND IN DATABASE:
    {retrieved_prior_art}
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
            temperature=0,
            seed=123
        )
        return audit_result

    except Exception as e:
        logger.error(f"Failed to evaluate disclosure: {str(e)}")
        raise RuntimeError(f"Ollama evaluation failed: {str(e)}")

# 3. Direct execution test block (for quick testing via `uv run`)
if __name__ == "__main__":
    # Sample test submission (intentionally vague to test grading logic)
    test_input = InventionInput(
        title="POWER MOSFET WITH AN ANODE REGION",
        target_domain="Null",
        problem_statement="Null",
        technical_solution="A vertical MOSFET device having source, body and drain regions, includes an anode region in series with the drain region. The source, body and drain regions have a first forward current gain and the anode, drain and body regions have a second forward current gain, such that the sum of the current gains is less than unity. The anode region provides minority carrier injection into the drain region, enhancing device performance in power applications. ",
        novel_features="Null",
    )

    print("\n--- Running Test Evaluation against Ollama ---")
    result = evaluate_disclosure(test_input)
    print(f"\nReadiness Score: {result.overall_patent_readiness_score}/100")
    print(f"Is Ready for Filing: {result.is_ready_for_filing}")
    print(f"Clarity Critique:\n{result.clarity_critique}")
    print(f"\nSuggested Refinements:\n{result.suggested_refinements}")
    print(f"\nNovelty Flag:\n{result.novelty_flag}")