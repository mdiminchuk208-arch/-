#!/usr/bin/env python3
"""Run explicit native app-server RPC checks; never starts a model turn."""
import argparse,json,os,queue,subprocess,threading
from pathlib import Path

class Runtime:
    def __init__(self, cwd='/workspace', stderr_path=None):
        self.stderr_path=Path(stderr_path or '/workspace/ecc-setup/logs/runtime_rpc_stderr.log')
        self.stderr=self.stderr_path.open('w')
        runtime_env=os.environ.copy()
        runtime_env['RUST_LOG']='warn'
        self.proc=subprocess.Popen(['/workspace/ecc-setup/codex-ecc','app-server','--stdio'],cwd=cwd,env=runtime_env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,text=True,bufsize=1)
        self.messages=queue.Queue()
        self.counter=0
        def consume():
            for line in self.proc.stdout:
                self.messages.put(json.loads(line))
            self.messages.put(None)
        threading.Thread(target=consume,daemon=True).start()
        self.rpc('initialize',{'clientInfo':{'name':'crypto-research-runtime-verification','version':'1.0'},'capabilities':{'experimentalApi':True}})
        self.proc.stdin.write(json.dumps({'method':'initialized'})+'\n')
        self.proc.stdin.flush()
    def rpc(self,method,params):
        self.counter+=1
        self.proc.stdin.write(json.dumps({'id':self.counter,'method':method,'params':params})+'\n')
        self.proc.stdin.flush()
        while True:
            msg=self.messages.get(timeout=45)
            if msg is None:
                raise RuntimeError('app-server closed stdout')
            if msg.get('id')==self.counter:
                if 'error' in msg: raise RuntimeError(json.dumps(msg['error']))
                return msg['result']
    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try: self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.stderr.close()

def safe_config(result):
    keep={'features','plugins','agents','projects','hooks'}
    return {'config':{k:v for k,v in result.get('config',{}).items() if k in keep},'layers':[{'name':x['name'],'disabledReason':x.get('disabledReason'),'version':x['version'],'config':{k:v for k,v in x.get('config',{}).items() if k in keep}} for x in result.get('layers',[])],'origins':{k:v for k,v in result.get('origins',{}).items() if k.split('.')[0] in keep}}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--trust-workspace',action='store_true')
    parser.add_argument('--cwd',default='/workspace/-')
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    runtime=Runtime(stderr_path=str(Path(args.out).with_suffix('.stderr.log')))
    results=[]
    try:
        if args.trust_workspace:
            params={'filePath':'/workspace/ecc-setup/codex-home/config.toml','keyPath':'projects','value':{'/workspace':{'trust_level':'trusted'}},'mergeStrategy':'upsert'}
            results.append({'method':'config/value/write','params':params,'result':runtime.rpc('config/value/write',params)})
        result=runtime.rpc('config/read',{'cwd':args.cwd,'includeLayers':True})
        results.append({'method':'config/read','cwd':args.cwd,'result':safe_config(result)})
        skills=runtime.rpc('skills/list',{'cwds':[args.cwd],'forceReload':True})
        for entry in skills['data']:
            ecc=[s for s in entry['skills'] if s.get('pluginId')=='ecc@ecc']
            results.append({'method':'skills/list','cwd':entry['cwd'],'ecc_skills':len(ecc),'enabled_ecc_skills':sum(x['enabled'] for x in ecc),'errors':entry['errors'],'crypto_research_skills':[s for s in entry['skills'] if 'crypto-strategy-research' in s['name']]})
        Path(args.out).write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(results,ensure_ascii=False,indent=2))
    finally: runtime.close()
