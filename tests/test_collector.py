from monitor.collector import MetricsCollector


def test_result_empty():

    collector = MetricsCollector()
    result = collector.collect("https://httpbin.org/status/400")

    assert result == {}


def test_result():

    collector = MetricsCollector()
    result = collector.collect("https://httpbin.org/status/200")

    assert result["status_code"] == 200
    assert isinstance(result["response_time"], int)
