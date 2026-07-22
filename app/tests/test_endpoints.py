from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app 

# Create a test client using your FastAPI app
client = TestClient(app)

# The mock data we want the "LLM" to return during the test
MOCK_LLM_RESPONSE = {
    "overall_patent_readiness_score": 85,
    "is_ready_for_filing": False,
    "clarity_critique": "The disclosure is well-structured but lacks specific voltage thresholds.",
    "missing_elements": ["Voltage ranges for the N-drift region", "Specific dimensions of the trench"],
    "suggested_refinements": ["Define the exact doping concentration for the P+ anode."],
    "novelty_flag": "Integrating the series P+ anode carrier injection layer is highly novel."
}

# Replace 'app.main.evaluate_disclosure' with the actual path to your LLM function
@patch("app.main.evaluate_disclosure")
def test_evaluate_disclosure_success(mock_evaluate):
    # Tell the mock function to return our fake data
    mock_evaluate.return_value = MOCK_LLM_RESPONSE

    # The payload Power Automate would send
    payload = {
        "title": "Vertical Power MOSFET",
        "target_domain": "Power Semiconductors",
        "problem_statement": "High specific ON-resistance.",
        "technical_solution": "A vertical MOSFET structure...",
        "novel_features": "Integrating a series P+ anode."
    }

    # Send the POST request to the local test server
    response = client.post("/evaluate-disclosure", json=payload)
    print(response.json())
    
    assert response.status_code == 200

def test_evaluate_disclosure_invalid_payload():
    # Test that FastAPI correctly rejects bad data (missing required fields)
    bad_payload = {
        "title": "Only the title is provided"
    }
    
    response = client.post("/evaluate-disclosure", json=bad_payload)
    
    # FastAPI should automatically return a 422 Unprocessable Entity
    assert response.status_code == 422