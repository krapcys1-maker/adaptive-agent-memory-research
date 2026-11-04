"""Flash-only paid reader with permanent cumulative per-attempt reservations.

No Pro/alternate provider, fallback, automatic retry, tools, thinking persistence
or credential output. This version is frozen once execution manifests pin it.
"""
from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import re
import time
import urllib.request

import metered_proxy
import nie_reader_pilot as P


def permitted(config):
    if config.get('api_model')!='deepseek-flash' or config.get('api_url')!='https://api.deepseek.com':
        raise ValueError('Only official DeepSeek V4.1 Flash is authorized; no other model/provider.')
    if config.get('api_advertised_name_prefix')!='DeepSeek-V4.1-Flash':
        raise ValueError('V4.1 Flash identity must not be relaxed.')
    if not 0 < config['api_reserved_cap_usd'] <= 1 or not 0 < config['max_calls'] <= 205:
        raise ValueError('API budget/call ceiling exceeds the committed task cap.')
    if config['api_reservation_usd']!=.004 or config['max_api_message_bytes']>6000 or config['max_api_messages']>4:
        raise ValueError('Reservation/input limits must retain the proved task bound.')
    if config['input_usd_per_million_upper']<.30 or config['output_usd_per_million_upper']<1.20:
        raise ValueError('Usage pricing cannot understate the verified peak rates.')


class ReservationLedger:
    def __init__(self,path,config):
        self.path=Path(path);self.cfg=config
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=self.path.with_suffix(self.path.suffix+'.lock')
        with self.lock.open('x',encoding='utf-8') as stream:stream.write('single active Flash client\n')
        self.owned=True

    def rows(self):
        try:
            rows=P.read_rows(self.path);reserved=set();settled=set()
            for row in rows:
                if row.get('event')=='reserve':
                    if row['key'] in reserved or row['model']!='deepseek-flash' or row['usd']!=self.cfg['api_reservation_usd']:
                        raise ValueError('Invalid reservation entry.')
                    reserved.add(row['key'])
                elif row.get('event')=='usage':
                    if row['key'] not in reserved or row['key'] in settled or row['usd_peak_uncached_upper']<0:
                        raise ValueError('Invalid usage entry.')
                    settled.add(row['key'])
                else:raise ValueError('Unknown ledger event.')
            return rows
        except (OSError,ValueError) as exc:raise ValueError('Unreadable/torn budget ledger; refusing to undercount.') from exc

    def reserve(self,key):
        rows=self.rows();reserved=[r for r in rows if r['event']=='reserve']
        if any(r['key']==key for r in reserved):raise ValueError('Paid attempt already reserved; no retry.')
        if len(reserved)>=self.cfg['max_calls']:raise RuntimeError('Cumulative paid-call cap reached.')
        spent=sum((Decimal(str(r['usd'])) for r in reserved),Decimal(0))
        reserve=Decimal(str(self.cfg['api_reservation_usd']))
        if spent+reserve>Decimal(str(self.cfg['api_reserved_cap_usd'])):raise RuntimeError('Cumulative API reservation cap reached.')
        P.append(self.path,{'event':'reserve','key':key,'model':'deepseek-flash','usd':float(reserve)})

    def settle(self,key,usage):
        prompt,completion=usage.get('prompt_tokens'),usage.get('completion_tokens')
        if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in (prompt,completion)):
            raise ValueError('Unknown usage: keep reservation and stop.')
        upper=(Decimal(prompt)*Decimal(str(self.cfg['input_usd_per_million_upper']))+
               Decimal(completion)*Decimal(str(self.cfg['output_usd_per_million_upper'])))/Decimal(1000000)
        P.append(self.path,{'event':'usage','key':key,'prompt_tokens':prompt,'completion_tokens':completion,
                           'usd_peak_uncached_upper':float(upper)})
        if upper>Decimal(str(self.cfg['api_reservation_usd'])):raise RuntimeError('Provider usage exceeded reservation assumption; stop.')

    def summary(self):
        rows=self.rows();reserve=[r for r in rows if r['event']=='reserve'];used=[r for r in rows if r['event']=='usage']
        return {'reserved_calls':len(reserve),'reserved_usd':round(sum(r['usd'] for r in reserve),6),
                'usage_priced_upper_usd':round(sum(r['usd_peak_uncached_upper'] for r in used),6),
                'unknown_usage_attempts':len(reserve)-len(used),'cap_usd':self.cfg['api_reserved_cap_usd'],
                'cost_semantics':'Permanent reservations and peak/uncached usage upper estimate; not an account invoice.'}

    def close(self):
        if self.owned:
            self.lock.unlink();self.owned=False


class FlashReader:
    def __init__(self,config,output,ledger_path,phase,*,key_loader=metered_proxy.load_key,transport=None):
        permitted(config)  # Must happen before touching credentials or network.
        self.cfg,self.output,self.phase=config,output,phase
        self._key=key_loader()
        self.ledger=ReservationLedger(ledger_path,config)
        self.started=time.monotonic();self.keys=set();self.responses=[]
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),P.NoRedirect())
        self.request=transport or self.http

    def http(self,path,body=None):
        if path not in ('/models','/chat/completions'):raise ValueError('Unsupported paid-provider operation.')
        req=urllib.request.Request('https://api.deepseek.com'+path,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Content-Type':'application/json','Authorization':'Bearer '+self._key})
        remaining=self.cfg['max_seconds']-(time.monotonic()-self.started)
        if remaining<=0:raise RuntimeError('API phase deadline reached.')
        with self.opener.open(req,timeout=min(90,remaining)) as response:return json.load(response)

    def identity(self):
        matches=[m for m in self.request('/models').get('data',[]) if m.get('id')=='deepseek-flash']
        if len(matches)!=1 or not re.fullmatch(r'DeepSeek-V4\.1-Flash(?:-\d+)?',matches[0].get('name','')):
            raise ValueError('Provider does not advertise the required V4.1 Flash; no generation.')
        return matches[0]

    def preflight(self):
        self.before=self.identity()
        return {'provider':'DeepSeek official API','requested_model':'deepseek-flash','advertised_model':self.before,
                'thinking':'disabled','seed_semantics':'Controller seed is recorded but not sent as an unsupported API guarantee.'}

    def ask(self,key,messages,seed,*,max_tokens=64):
        if key in self.keys:raise ValueError('Duplicate completion key.')
        if len(self.keys)>=self.cfg['max_calls'] or time.monotonic()-self.started>=self.cfg['max_seconds']:
            raise RuntimeError('Phase call/time cap reached.')
        size=len(json.dumps(messages,ensure_ascii=False).encode())
        if len(messages)>self.cfg['max_api_messages'] or size>self.cfg['max_api_message_bytes'] or not 0<max_tokens<=512:
            raise ValueError('Request exceeds reserved input/output bound.')
        estimated=(size+4096+256*len(messages))*.30/1e6+max_tokens*1.20/1e6
        if estimated>self.cfg['api_reservation_usd']:raise ValueError('Request cannot fit its reservation.')
        payload={'model':'deepseek-flash','messages':messages,'stream':False,'temperature':0,
                 'max_tokens':max_tokens,'thinking':{'type':'disabled'},'response_format':{'type':'json_object'}}
        self.ledger.reserve(self.phase+':'+key)
        self.keys.add(key)
        P.append(self.output/'attempts.jsonl',{'key':key,'request_sha256':P.sha(payload),'request':payload,
                                             'controller_seed_not_sent':seed})
        start=time.monotonic()
        response=self.request('/chat/completions',payload)
        usage=response.get('usage') or {}
        self.ledger.settle(self.phase+':'+key,usage)
        model=response.get('model','')
        if not (model=='deepseek-flash' or re.fullmatch(r'deepseek-v4\.1-flash(?:-\d+)?',model.lower())):
            raise ValueError('Unexpected returned model; no fallback or further calls.')
        choice=response.get('choices',[{}])[0];message=choice.get('message') or {}
        if message.get('reasoning_content'):raise RuntimeError('Unexpected thinking content; stop without storing it.')
        text=message.get('content')
        if not isinstance(text,str):raise ValueError('No final response content.')
        row={'key':key,'text':text,'done_reason':choice.get('finish_reason'),'returned_model':model,
             'system_fingerprint':response.get('system_fingerprint'),'wall_seconds':time.monotonic()-start,
             'usage':usage}
        self.responses.append(row);P.append(self.output/'responses.jsonl',row)
        print(f'{len(self.keys):03d} {key}',flush=True)
        return row

    def finish(self):
        after=self.identity()
        if after!=self.before:raise RuntimeError('Advertised API model changed during phase.')
        return {'calls':len(self.keys),'seconds':time.monotonic()-self.started,'advertised_model_unchanged':True,
                'advertised_model_after':after,'budget':self.ledger.summary()}

    def release(self):
        self.ledger.close();self._key=''
