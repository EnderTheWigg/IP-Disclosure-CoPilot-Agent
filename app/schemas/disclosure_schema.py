from typing import List
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

class InventionInput(BaseModel):
    """
    Input payload received from Copilot Studio / Power Automate.
    Represents the structured intake fields collected during the conversational flow.
    """

    title: str = Field(
        ...,
        description="Title of the invention disclosure",
        examples=["Dynamic Cache Eviction Unit for Automotive MCUs"],
    )
    target_domain: str = Field(
        ...,
        description="Target business line, product family, or engineering domain",
        examples=["Embedded Microcontrollers / Automotive Systems"],
    )
    problem_statement: str = Field(
        ...,
        description="Description of the technical problem and current limitations in prior art",
        examples=[
            "Standard cache clearing causes high latency during context switches, slowing down real-time control loops."
        ],
    )
    technical_solution: str = Field(
        ...,
        description="Detailed step-by-step description of the proposed hardware/software implementation",
        examples=[
            "Introduces a hardware reset flag in the DMA register that triggers asynchronous line eviction in 1 clock cycle."
        ],
    )
    novel_features: str = Field(
        ...,
        description="Specific features that make this invention novel over existing industry methods",
        examples=[
            "Zero-wait-state cache line clearing driven directly by hardware interrupts without CPU cycle overhead."
        ],
    )


class DisclosureAudit(BaseModel):
    """
    Structured output returned by the local Ollama LLM via Instructor.
    Evaluates technical clarity, completeness, and patent committee readiness.
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True  # Allows both snake_case and camelCase
    )

    overall_patent_readiness_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall score from 0 to 100 based on patent readiness",
    )
    is_ready_for_filing: bool = Field(
        ...,
        description="True if score >= 80, indicating the draft is ready for formal filing",
    )
    clarity_critique: str = Field(
        ...,
        description="Detailed critique identifying vague, high-level, or unspecific language",
    )
    missing_elements: List[str] = Field(
        default_factory=list,
        description="Specific technical details or metrics that need to be added",
    )
    suggested_refinements: List[str] = Field(
        default_factory=list,
        description="Actionable, step-by-step suggestions for the engineer to improve the draft",
    )
    novelty_flag: str = Field(
        ...,
        description="Use if there is a high similarity to existing art, otherwise return 'None'. If high similarity exists, return the name, id and inventors of the patent it is similar to, as well as the exact reason you believe they are similar",
    )