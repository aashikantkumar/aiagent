import pytest
from pydantic import ValidationError
from agent.architectural_artifacts import ArchitecturalArtifacts, ArchitectureDecisionRecord, ArchitecturalPlan
from agent.stage_checkpoint import StageCheckpoint, VerificationResult, VerificationMode
from datetime import datetime

# Sample valid diagrams for testing
VALID_SYSTEM_DIAGRAM = """graph TD
    A[User] --> B[Web App]
"""

VALID_COMPONENT_DIAGRAM = """flowchart LR
    A[API Gateway] --> B[Auth Service]
"""

VALID_DATA_FLOW_DIAGRAM = """graph LR
    A[(Database)] --> B[Data Processor]
"""

VALID_SEQUENCE_DIAGRAM = """sequenceDiagram
    User->>System: login()
    System-->>User: token
"""

VALID_DEPLOYMENT_DIAGRAM = """graph TB
    subgraph Cloud
        Server
    end
"""

def test_architectural_artifacts_valid():
    artifacts = ArchitecturalArtifacts(
        system_diagram=VALID_SYSTEM_DIAGRAM,
        component_diagram=VALID_COMPONENT_DIAGRAM,
        data_flow_diagram=VALID_DATA_FLOW_DIAGRAM,
        sequence_diagrams=[VALID_SEQUENCE_DIAGRAM],
        deployment_diagram=VALID_DEPLOYMENT_DIAGRAM
    )
    assert artifacts.system_diagram == VALID_SYSTEM_DIAGRAM
    assert len(artifacts.sequence_diagrams) == 1

def test_architectural_artifacts_invalid_mermaid():
    with pytest.raises(ValidationError) as excinfo:
        ArchitecturalArtifacts(
            system_diagram="invalid diagram content here",
            component_diagram=VALID_COMPONENT_DIAGRAM,
            data_flow_diagram=VALID_DATA_FLOW_DIAGRAM,
            sequence_diagrams=[VALID_SEQUENCE_DIAGRAM],
            deployment_diagram=VALID_DEPLOYMENT_DIAGRAM
        )
    assert "Invalid Mermaid diagram syntax" in str(excinfo.value)

def test_architectural_artifacts_empty_sequences():
    with pytest.raises(ValidationError) as excinfo:
        ArchitecturalArtifacts(
            system_diagram=VALID_SYSTEM_DIAGRAM,
            component_diagram=VALID_COMPONENT_DIAGRAM,
            data_flow_diagram=VALID_DATA_FLOW_DIAGRAM,
            sequence_diagrams=[],
            deployment_diagram=VALID_DEPLOYMENT_DIAGRAM
        )
    assert "sequence_diagrams must contain at least 1 diagram" in str(excinfo.value)

def test_adr_valid():
    adr = ArchitectureDecisionRecord(
        id="ADR-001",
        title="Use PostgreSQL for persistent storage",
        status="Accepted",
        context="We need to store relational data.",
        decision="We will use PostgreSQL.",
        consequences="Relational schema migrations are required.",
        alternatives=["MongoDB", "SQLite"],
        created_at=datetime.utcnow().isoformat()
    )
    assert adr.id == "ADR-001"
    assert adr.status == "Accepted"

def test_adr_invalid_id():
    with pytest.raises(ValidationError) as excinfo:
        ArchitectureDecisionRecord(
            id="ADR-abc",
            title="Use PostgreSQL",
            status="Accepted",
            context="Context",
            decision="Decision",
            consequences="Consequences",
            created_at=datetime.utcnow().isoformat()
        )
    assert "ADR id must follow the pattern" in str(excinfo.value)

def test_stage_checkpoint_lifecycle():
    checkpoint = StageCheckpoint(stage_name="bootstrap")
    assert checkpoint.verification_status == "Pending"
    assert checkpoint.retry_count == 0
    
    checkpoint.increment_retry()
    assert checkpoint.retry_count == 1
    assert checkpoint.verification_timestamp is not None
    
    checkpoint.update_status("Pass", {"some_detail": "all fields OK"})
    assert checkpoint.verification_status == "Pass"
    assert checkpoint.verification_details["some_detail"] == "all fields OK"
    
    checkpoint.reset()
    assert checkpoint.retry_count == 0
