from lexsentinel.analyzers.scoring import classify_risk


def test_classify_risk_safe():
    assert classify_risk(0) == "SAFE"
    assert classify_risk(24) == "SAFE"


def test_classify_risk_suspicious():
    assert classify_risk(25) == "SUSPICIOUS"
    assert classify_risk(59) == "SUSPICIOUS"


def test_classify_risk_high_risk():
    assert classify_risk(60) == "HIGH RISK"
    assert classify_risk(89) == "HIGH RISK"


def test_classify_risk_critical():
    assert classify_risk(90) == "CRITICAL"
    assert classify_risk(999) == "CRITICAL"