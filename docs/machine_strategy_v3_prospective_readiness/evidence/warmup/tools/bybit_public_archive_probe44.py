"""Bounded public archive availability probe; no market data processing."""
import hashlib
import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://public.bybit.com/kline_for_metatrader4/BTCUSDT/'
OUT = Path('/workspace/-/docs/machine_strategy_v3_prospective_readiness/evidence/warmup')
if (OUT/'bybit_public_archive_probe.raw').exists() or (OUT/'bybit_public_archive_probe.receipt.json').exists():
    raise FileExistsError('Immutable public archive receipt already exists')
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
start = now(); status = None; error = None; headers = {}
try:
    with urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent':'Codex-Warmup-Integrity/1.0'}), timeout=20, context=ssl.create_default_context()) as response:
        status = response.status
        headers = {k.lower():v for k,v in response.headers.items() if k.lower() in {'date','content-type','content-length','server','via','x-cache'}}
        raw = response.read(131072)
except urllib.error.HTTPError as exc:
    status=exc.code; error=str(exc)
    headers={k.lower():v for k,v in exc.headers.items() if k.lower() in {'date','content-type','content-length','server','via','x-cache'}}
    raw=exc.read(131072)
except Exception as exc:
    error=type(exc).__name__+': '+str(exc); raw=b''
end=now(); path=OUT/'bybit_public_archive_probe.raw';path.write_bytes(raw)
receipt={'request_url':URL,'requested_at_utc':start,'completed_at_utc':end,'http_status':status,'error':error,
         'response_headers_allowlist':headers,'raw_path':path.name,'raw_byte_count':len(raw),
         'raw_sha256':hashlib.sha256(raw).hexdigest(),'body_read_limit_bytes':131072,
         'tls_verification':'stdlib_default_context_enabled','credentials_used':False}
(OUT/'bybit_public_archive_probe.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
