from lexsentinel.analyzers.core import analyze


def test_analyze_missing_file():
    result = analyze("/arquivo/que/nao/existe.pdf")

    assert result.errors
    assert "Falha ao abrir PDF" in result.errors[0]
    assert result.risk == "SAFE"