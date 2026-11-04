from typing import Literal
from pydantic import BaseModel, Field

class TransactionRequest(BaseModel):
    amount: float = Field(ge=0, le=1_000_000_000)
    typical_amount: float = Field(gt=0, le=1_000_000_000)
    unusual_transaction_time: bool = False
    unusual_location: bool = False
    multiple_rapid_transactions: bool = False
    related_phishing_message_reported: bool = False

class PhishingRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)


class IncidentReport(BaseModel):
    incident_id: str = Field(min_length=1, max_length=100)
    incident_type: str = Field(min_length=1, max_length=100)
    risk_score: int
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    summary: str = Field(min_length=1, max_length=1000)


class IncidentEvent(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    risk_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1, max_length=1000)
    evidence: list[str] = Field(default_factory=list, max_length=20)
    source: str = "CyberShield UI"
