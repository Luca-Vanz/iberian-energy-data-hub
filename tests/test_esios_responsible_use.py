from datetime import datetime

import requests

import src.collectors.esios_balancing_prices as collector


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, *args, **kwargs):
        response = self.responses[self.calls]
        self.calls += 1
        return response


def _response(status, payload=None):
    response = requests.Response()
    response.status_code = status
    response.url = "https://api.esios.ree.es/indicators/1782"
    if payload is not None:
        import json

        response._content = json.dumps(payload).encode("utf-8")
        response.headers["Content-Type"] = "application/json"
    return response


def test_temporary_block_stops_immediately():
    session = FakeSession([_response(403)])
    original_headers = collector.get_headers
    collector.get_headers = lambda: {}
    try:
        try:
            collector.request_indicator_chunk(
                session,
                1782,
                datetime(2025, 12, 1),
                datetime(2025, 12, 1),
            )
        except collector.TemporaryApiBlockError:
            pass
        else:
            raise AssertionError("Expected a temporary block error")
    finally:
        collector.get_headers = original_headers

    assert session.calls == 1


def test_rate_limit_retries_with_backoff():
    session = FakeSession(
        [_response(429), _response(200, {"indicator": {"values": []}})]
    )
    original_headers = collector.get_headers
    original_sleep = collector.time.sleep
    sleeps = []
    collector.get_headers = lambda: {}
    collector.time.sleep = sleeps.append
    try:
        result = collector.request_indicator_chunk(
            session,
            1782,
            datetime(2025, 12, 1),
            datetime(2025, 12, 1),
        )
    finally:
        collector.get_headers = original_headers
        collector.time.sleep = original_sleep

    assert result == {"indicator": {"values": []}}
    assert session.calls == 2
    assert sleeps == [5.0]


if __name__ == "__main__":
    test_temporary_block_stops_immediately()
    test_rate_limit_retries_with_backoff()
    print("ESIOS responsible-use tests passed")
