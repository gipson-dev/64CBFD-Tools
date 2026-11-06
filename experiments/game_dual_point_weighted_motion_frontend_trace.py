"""Owned normal-profile compiler capture for the recovered early X lifetime."""
import json
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as core
from tools.experiments import game_text_measurer_frontend_trace as front
from tools.experiments import game_dual_point_weighted_motion_candidates as candidate
from tools.pad_generated_object import parse_object
PROFILES=dict(owner=('-O2','-g3'))
def payload(obj):
    t,fs,rs=parse_object(obj);f=fs[candidate.FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def compile_isolated(root,work,name,body):
    with patch.multiple(core,ENTRY=candidate.ENTRY,ROM=candidate.ROM,WORDS=67,FUNCTION=candidate.FUNCTION,RECORD='',DECLARATIONS='extern f32 D_800BE9A4;\n',SYMBOLS=dict(D_800BE9A4=0x800BE9A4),PROFILES=PROFILES):meta,words=core.compile_candidate(root,work,name,body,'owner')
    meta['frame']=next((-w&65535 for w in words if w>>16==0x27BD),0)
    if payload(work/(name+'.o'))!=payload(root/candidate.BUILD/'selected-screen.o'):raise ValueError('Weighted observed isolated/complete-owner body differs')
    return meta,words
def capture(root):
    with patch.object(front.trace.screen,'compile_candidate',side_effect=compile_isolated),patch.object(front.trace.screen,'PROFILES',PROFILES):r=front.capture_frontend(root,root/candidate.BUILD,'wire-weighted',candidate.SELECTED)
    summary=dict(code_unchanged=r['code_unchanged'],baseline=r['complete']['baseline'],frontend_records=r['record_count'],optimizer_records=r['optimizer_record_count'],frontend_sha256=r['frontend']['sha256'],optimizer_sha256=r['optimizer']['sha256'],compiler_fingerprints=front.compiler_fingerprints(root))
    (root/candidate.BUILD/'weighted-wire-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');return summary
if __name__=='__main__':print(json.dumps(capture(candidate.ROOT),indent=2))
