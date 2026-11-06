"""Owned, fingerprint-locked CFE/UOPT capture for the fade gate and pointer homes."""
import argparse,json
from unittest.mock import patch
from tools.experiments import game_text_measurer_frontend_trace as front
from tools.experiments import game_record_constructor_candidates as core
from tools.experiments import game_text_buffer_fade_recovery as historical
from tools.experiments import game_text_buffer_fade_candidates as selected
from tools.tests import game_text_buffer_fade_oracle as guest
from tools.tests import game_text_buffer_fade_native as native
PROFILES=dict(owner=('-O2','-g3'))

def compile_isolated(root,work,name,body):
    with patch.multiple(core,ENTRY=selected.ENTRY,ROM=selected.ROM,WORDS=69,FUNCTION=selected.FUNCTION,RECORD='',DECLARATIONS=native.HEADERS,SYMBOLS=guest.symbols(),PROFILES=PROFILES):
        meta,words=core.compile_candidate(root,work,name,body,'owner')
    expected=root/selected.BUILD/('qualified-private.o'if body==historical.SELECTED else 'match-qualified-compact.o')
    if body in(historical.SELECTED,selected.SELECTED)and guest.payload(work/(name+'.o'))!=guest.payload(expected):raise ValueError('Observed isolated and complete-owner target differ')
    return meta,words

def capture(root,variant='matched'):
    body={'historical':historical.SELECTED,'direct':historical.SELECTED.replace('(((u8 **)&owner)[0])','owner'),'matched':selected.SELECTED}[variant]
    with patch.object(front.trace.screen,'compile_candidate',side_effect=compile_isolated),patch.object(front.trace.screen,'PROFILES',PROFILES):
        r=front.capture_frontend(root,root/selected.BUILD,'wire-'+variant,body)
    summary=dict(variant=variant,code_unchanged=r['code_unchanged'],baseline=r['complete']['baseline'],frontend_records=r['record_count'],optimizer_records=r['optimizer_record_count'],frontend_sha256=r['frontend']['sha256'],optimizer_sha256=r['optimizer']['sha256'],compiler_fingerprints=front.compiler_fingerprints(root))
    if variant=='matched':
        records=r['optimizer_records'];start=max(i for i,v in enumerate(records)if v['name']=='ent');body_records=records[start:]
        home=[v for v in body_records if v['storage']=='M'and v['offset']==-16]
        if [(v['name'],v['dtype'],v['length'])for v in home]!=[('rstr','A',4),('rlod','A',4)]:raise ValueError('Second descriptor no longer owns M-16 alone')
        summary['M_minus16_pointer_store_reload_only']=True
    (root/selected.BUILD/('wire-'+variant+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=('historical','direct','matched'),default='matched');args=p.parse_args();print(json.dumps(capture(selected.ROOT,args.variant),indent=2))
if __name__=='__main__':main()
