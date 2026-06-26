from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
import re
from agent.mermaid_validator import is_valid_mermaid

class ArchitecturalArtifacts(BaseModel):
    system_diagram: str = Field(..., description="Mermaid diagram of system components")
    component_diagram: str = Field(..., description="Component interaction diagram")
    data_flow_diagram: str = Field(..., description="Data flow through system")
    sequence_diagrams: List[str] = Field(default_factory=list, description="Key interaction sequences")
    deployment_diagram: str = Field(..., description="Runtime deployment architecture")

    @field_validator("system_diagram", "component_diagram", "data_flow_diagram", "deployment_diagram")
    @classmethod
    def validate_diagram_syntax(cls, v: str) -> str:
        valid, err = is_valid_mermaid(v)
        if not valid:
            raise ValueError(f"Invalid Mermaid diagram syntax: {err}")
        return v

    @field_validator("sequence_diagrams")
    @classmethod
    def validate_sequences(cls, v: List[str]) -> List[str]:
        if not v or len(v) < 1:
            raise ValueError("sequence_diagrams must contain at least 1 diagram")
        for idx, diagram in enumerate(v):
            valid, err = is_valid_mermaid(diagram)
            if not valid:
                raise ValueError(f"Sequence diagram at index {idx} has invalid Mermaid syntax: {err}")
        return v


class ArchitectureDecisionRecord(BaseModel):
    id: str = Field(..., description="Unique identifier (ADR-001, ADR-002, ...)")
    title: str = Field(..., description="Short decision title")
    status: Literal['Proposed', 'Accepted', 'Superseded'] = 'Proposed'
    context: str = Field(..., description="Why this decision was needed")
    decision: str = Field(..., description="What was decided")
    consequences: str = Field(..., description="Positive and negative implications")
    alternatives: List[str] = Field(default_factory=list, description="Other options considered")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    updated_at: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not re.match(r"^ADR-\d{3}$", v):
            raise ValueError("ADR id must follow the pattern 'ADR-\\d{3}' (e.g. ADR-001)")
        return v


class ArchitecturalPlan(BaseModel):
    architecture_generated_at: str = Field(..., description="ISO 8601 timestamp")
    architectural_artifacts: ArchitecturalArtifacts
    architecture_decisions: List[ArchitectureDecisionRecord] = Field(default_factory=list)
    architecture_approved: bool = False
    architecture_revision: int = 1
    architecture_feedback: str = ""
    tech_stack_summary: str = ""
    estimated_complexity: Literal['Low', 'Medium', 'High', 'VeryHigh'] = 'Medium'
