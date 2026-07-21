from fastapi import FastAPI, HTTPException, status
from schemas import DisclosureAudit, InventionInput
from services import evaluate_disclosure
app = FastAPI()


@app.post(
    "/evaluate-dislosure",
    response_model=DisclosureAudit,
    status_code=200
    )
async def evaluate_disclosure(user_in: InventionInput):
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