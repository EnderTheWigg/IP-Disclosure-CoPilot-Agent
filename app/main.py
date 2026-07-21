from fastapi import FastAPI, HTTPException, status
from schemas import DisclosureAudit, InventionInput
from services.evaluator import evaluate_disclosure

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
    "/evaluate-dislosure",
    response_model=DisclosureAudit,
    status_code=200
    )
def evaluate_disclosure(user_in: InventionInput):
    """
    Receives invention disclosure data from Power Automate,
    runs local LLM quality audit, and returns structured feedback.
    """
    try:
        audit_report = evaluate_disclosure(user_in)
        return audit_report
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during evaluation: {str(e)}"
        )