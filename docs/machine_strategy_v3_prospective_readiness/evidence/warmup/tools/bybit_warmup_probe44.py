"""Capture public Bybit M15 response bytes and safe HTTP metadata."""
import hashlib
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('/workspace/-/docs/machine_strategy_v3_prospective_readiness/evidence/warmup')
SAFE_HEADERS = {'date','content-type','content-length','content-encoding','server','via','x-cache','cf-ray','x-bapi-limit','x-bapi-limit-status','x-bapi-limit-reset-timestamp'}

def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def capture(symbol, tag, start_ms, end_ms):
    basename = f'bybit_{symbol}_{tag}'
    raw_name = basename + '.raw'
    receipt_name = basename + '.receipt.json'
    if (OUT / raw_name).exists() or (OUT / receipt_name).exists():
        raise FileExistsError('Immutable receipt already exists: ' + basename)
    params = {'category':'linear','symbol':symbol,'interval':'15','start':str(start_ms),'end':str(end_ms),'limit':'1000'}
    url = 'https://api.bybit.com/v5/market/kline?' + urllib.parse.urlencode(params)
    requested_at = now()
    request = urllib.request.Request(url, headers={'Accept':'application/json','User-Agent':'Codex-Warmup-Integrity/1.0'})
    status = None
    error = None
    headers = {}
    try:
        with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
            status = response.status
            headers = {k.lower():v for k,v in response.headers.items() if k.lower() in SAFE_HEADERS}
            body = response.read(12_000_000)
    except urllib.error.HTTPError as exc:
        status = exc.code
        headers = {k.lower():v for k,v in exc.headers.items() if k.lower() in SAFE_HEADERS}
        body = exc.read(12_000_000)
        error = str(exc)
    except Exception as exc:
        body = b''
        error = type(exc).__name__ + ': ' + str(exc)
    completed_at = now()
    (OUT / raw_name).write_bytes(body)
    receipt = {'source':'official_bybit_public_v5_market_kline','request_url':url,
               'request_params':params,'requested_at_utc':requested_at,'completed_at_utc':completed_at,
               'http_status':status,'error':error,'response_headers_allowlist':headers,
               'raw_path':raw_name,'raw_byte_count':len(body),'raw_sha256':hashlib.sha256(body).hexdigest(),
               'tls_verification':'stdlib_default_context_enabled','credentials_used':False}
    (OUT / receipt_name).write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))

capture('BTCUSDT','first_gap_probe',1764977400000,1764981000000)
capture('ETHUSDT','first_gap_probe',1764977400000,1764981000000)
