"""Allowlisted AI operation metadata only; never log payloads or credentials."""
import json
import logging
from datetime import datetime,timezone
from pathlib import Path
from threading import Lock

logger=logging.getLogger(__name__)
lock=Lock()
PATH=Path(__file__).resolve().parents[3]/'outputs/ai-request-diagnostics.jsonl'

def log(event,identity,mode,source=None,http_status=None,latency_ms=None):
    entry={'at_utc':datetime.now(timezone.utc).isoformat(),'event':event,'user_id':identity,
           'mode':mode,'source':source,'http_status':http_status,'latency_ms':latency_ms}
    try:
        with lock:
            PATH.parent.mkdir(parents=True,exist_ok=True)
            with PATH.open('a',encoding='utf-8') as stream:stream.write(json.dumps(entry)+'\n')
    except OSError:
        logger.warning('AI diagnostic metadata write failed')
