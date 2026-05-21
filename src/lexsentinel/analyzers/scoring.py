from lexsentinel.models import Finding


def add_finding(result, finding: Finding):
    result.findings.append(finding)
    result.total_score += finding.score


def classify_risk(score: int) -> str:
    if score >= 90:
        return "CRITICAL"
    if score >= 60:
        return "HIGH RISK"
    if score >= 25:
        return "SUSPICIOUS"
    return "SAFE"
