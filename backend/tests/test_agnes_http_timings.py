import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.services import agnes


@pytest.mark.parametrize('timeout', [False, True])
def test_transport_timings_are_safe(monkeypatch, timeout):
    rows = []
    def capture(stage, status=None, error=None):
        rows.append((stage, status, error))
        # Do not write a real diagnostic file in this unit test.
        if agnes._trace.get():
            agnes._trace.get()['stage'] = stage
    monkeypatch.setattr(agnes, 'trace_stage', capture)
    real_client = httpx.AsyncClient
    def handler(request):
        if timeout:
            raise httpx.ConnectTimeout('secret-url-or-key', request=request)
        return httpx.Response(200, json={'choices':[{'message':{'role':'assistant','content':'private-answer'}, 'finish_reason':'stop'}]})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    settings = SimpleNamespace(model='test', api_key='secret-key', base_url='https://example.invalid/v1', timeout=45)
    if timeout:
        with pytest.raises(agnes.ProviderError) as error:
            asyncio.run(agnes.AgnesProvider().answer(settings, 'private-question'))
        assert error.value.code == 'provider_timeout'
        assert rows[-1] == ('timeout_after_request_start', None, 'ConnectTimeout')
    else:
        asyncio.run(agnes.AgnesProvider().answer(settings, 'private-question'))
        assert [r[0] for r in rows] == ['request_start','response_headers','first_byte','response_complete','parsed_validated']
        assert rows[-1][1] == 200
    assert agnes._trace.get() is None
    assert all(s not in json.dumps(rows) for s in ('secret-key','private-question','private-answer','secret-url'))
