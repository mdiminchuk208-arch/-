"""Bounded public repository discovery; retain raw metadata bytes."""
import hashlib
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('/workspace/-/docs/machine_strategy_v3_prospective_readiness/evidence/warmup')
SAFE = {'date','content-type','content-length','server','via','x-cache','x-ratelimit-limit','x-ratelimit-remaining','x-ratelimit-reset'}
def now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
for tag, query in [('bybit_btc_m15','bybit BTCUSDT 15m candles'),('bybit_kline_2026','bybit historical kline 2026'),('bybit_kline','bybit kline')]:
    name=f'github_search_{tag}'
    if (OUT/(name+'.raw')).exists() or (OUT/(name+'.receipt.json')).exists():
        raise FileExistsError('Immutable mirror discovery receipt already exists: '+name)
    url='https://api.github.com/search/repositories?'+urllib.parse.urlencode({'q':query,'per_page':'10','sort':'updated'})
    started=now();error=None;status=None;headers={}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'Codex-Warmup-Integrity/1.0'}),timeout=20,context=ssl.create_default_context()) as response:
            status=response.status;headers={k.lower():v for k,v in response.headers.items() if k.lower() in SAFE};raw=response.read(500000)
    except urllib.error.HTTPError as exc:
        status=exc.code;error=str(exc);headers={k.lower():v for k,v in exc.headers.items() if k.lower() in SAFE};raw=exc.read(500000)
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc);raw=b''
    ended=now()
    (OUT/(name+'.raw')).write_bytes(raw)
    receipt={'request_url':url,'requested_at_utc':started,'completed_at_utc':ended,'http_status':status,'error':error,'response_headers_allowlist':headers,'raw_path':name+'.raw','raw_byte_count':len(raw),'raw_sha256':hashlib.sha256(raw).hexdigest(),'tls_verification':'stdlib_default_context_enabled','credentials_used':False}
    (OUT/(name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    try:
        obj=json.loads(raw)
        candidates=[{'full_name':x['full_name'],'description':x['description'],'updated_at':x['updated_at'],'html_url':x['html_url']} for x in obj.get('items',[])]
        print(json.dumps({'tag':tag,'status':status,'total_count':obj.get('total_count'),'candidates':candidates}))
    except (ValueError,KeyError,TypeError):
        print(json.dumps({'tag':tag,'status':status,'error':error}))
