import pytest
from quantlab.data.providers.tiingo import TiingoProvider


def test_missing_credentials(monkeypatch):
    monkeypatch.delenv("TIINGO_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="TIINGO_API_TOKEN"):
        TiingoProvider().download(["A"], "2020-01-02", "2020-01-03")


def test_provider_mapping(monkeypatch):
    monkeypatch.setenv("TIINGO_API_TOKEN", "test-secret")

    class Response:
        status_code = 200

        def json(self):
            return [
                {
                    "date": d + "T00:00:00.000Z",
                    "open": 10,
                    "high": 10,
                    "low": 10,
                    "close": 10,
                    "volume": 100,
                    "splitFactor": 1,
                    "divCash": 0,
                    "adjClose": 999,
                }
                for d in ["2020-01-02", "2020-01-03"]
            ]

    def request(url, headers, params, timeout):
        assert headers == {"Authorization": "Token test-secret"}
        assert params["startDate"] == "2020-01-02"
        assert timeout == 60
        return Response()

    monkeypatch.setattr("quantlab.data.providers.tiingo.requests.get", request)
    data = TiingoProvider().download(["A"], "2020-01-02", "2020-01-03")
    assert data.frame.close.tolist() == [10, 10]
    assert data.frame.split.tolist() == [1, 1]
    assert "test-secret" not in str(data.metadata)


def test_provider_error_not_fabricated(monkeypatch):
    monkeypatch.setenv("TIINGO_API_TOKEN", "test-secret")

    class Response:
        status_code = 403

    monkeypatch.setattr("quantlab.data.providers.tiingo.requests.get", lambda *a, **k: Response())
    with pytest.raises(ValueError, match="HTTP 403"):
        TiingoProvider().download(["A"], "2020-01-02", "2020-01-03")
