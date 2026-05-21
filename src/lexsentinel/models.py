from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any


@dataclass
class Finding:
    category: str
    severity: str
    score: int
    confidence: str
    title: str
    details: str
    page: Optional[int] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    evidence_path: Optional[str] = None


@dataclass
class Fingerprint:
    filename: str
    file_size: int
    sha256: str
    pdf_version: Optional[str]
    creator: Optional[str]
    producer: Optional[str]
    creation_date: Optional[str]
    mod_date: Optional[str]
    encrypted: bool
    linearized: bool


@dataclass
class Result:
    file_path: str
    metadata: Dict[str, str]
    fingerprint: Optional[Fingerprint] = None
    findings: List[Finding] = field(default_factory=list)
    total_score: int = 0
    risk: str = "SAFE"
    errors: List[str] = field(default_factory=list)
