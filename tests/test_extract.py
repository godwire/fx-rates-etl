from unittest.mock import Mock, patch

import pytest

from src import extract


def _mock_response(json_data, status_code=200):
    mock_resp = Mock()
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = Mock()
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = Exception("HTTP error")
    return mock_resp


@patch("src.extract.requests.get")
def test_fetch_latest_builds_correct_request(mock_get):
    mock_get.return_value = _mock_response(
        {"base": "EUR", "date": "2024-01-02", "rates": {"USD": 1.09}}
    )

    payload = extract.fetch_latest("EUR", ["USD"])

    mock_get.assert_called_once()
    called_url = mock_get.call_args[0][0]
    called_params = mock_get.call_args[1]["params"]
    assert called_url == "https://api.frankfurter.app/latest"
    assert called_params == {"from": "EUR", "to": "USD"}
    assert payload["rates"]["USD"] == 1.09


@patch("src.extract.requests.get")
def test_fetch_range_builds_correct_url(mock_get):
    mock_get.return_value = _mock_response(
        {"base": "EUR", "rates": {"2024-01-01": {"USD": 1.1}, "2024-01-02": {"USD": 1.09}}}
    )

    payload = extract.fetch_range("2024-01-01", "2024-01-02", "EUR", ["USD"])

    called_url = mock_get.call_args[0][0]
    assert called_url == "https://api.frankfurter.app/2024-01-01..2024-01-02"
    assert len(payload["rates"]) == 2


@patch("src.extract.requests.get")
def test_get_raises_extract_error_on_bad_shape(mock_get):
    mock_get.return_value = _mock_response({"unexpected": "shape"})

    with pytest.raises(extract.ExtractError):
        extract.fetch_latest("EUR", ["USD"])


@patch("src.extract.requests.get")
def test_get_raises_extract_error_on_request_exception(mock_get):
    import requests

    mock_get.side_effect = requests.RequestException("boom")

    with pytest.raises(extract.ExtractError):
        extract.fetch_latest("EUR", ["USD"])
