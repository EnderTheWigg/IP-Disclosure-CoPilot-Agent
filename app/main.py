from fastapi import FastAPI, HTTPException, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.schemas.disclosure_schema import DisclosureAudit, InventionInput
from app.services.evaluator import evaluate
import chromadb

chroma_client = chromadb.PersistentClient(path="./chroma_db")

patent_collection = chroma_client.get_or_create_collection(name="prior_art_patents")

app = FastAPI(
    title="Enterprise IP Disclosure Copilot API",
    description="Microservice for auditing invention disclosures for technical clarity and patent readiness.",
    version="1.0.0"
)

# 1. Health check route (Best practice for testing ngrok and API uptime)
@app.get("/health")
def health_check():
    return {"status": "online", "engine": "Ollama / Llama 3.2"}

@app.post(
    "/evaluate-disclosure",
    response_model=DisclosureAudit,
    status_code=200
    )
def evaluate_disclosure(user_in: InventionInput):
    """
    Receives invention disclosure data from Power Automate,
    runs local LLM quality audit, and returns structured feedback.
    """
    try:
        audit_report = evaluate(user_in)
        return audit_report
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during evaluation: {str(e)}"
        )
    
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("VALIDATION ERROR DETAILS:", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )