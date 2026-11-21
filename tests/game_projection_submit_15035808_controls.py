"""Effective instruction defects and a positive FP-register recoloring control."""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
import json,struct
from tools.tests import game_projection_submit_15035808_proof as p
OUT=recovery.OUT

def check(words):
    original=struct.unpack_from('>345I',(ROOT/'conker/conker.us.bin').read_bytes(),0x62cb8)
    terms=p.g.Terms();streams={'raw':words,'retail':original};report={}
    for phase in('prefix','first-loop','retained-loop'):
        paths={}
        for side,stream in streams.items():
            program=p.Program(stream,terms)
            state=p.State()if phase=='prefix'else p.loop_initial(side,stream,phase=='retained-loop')
            paths[side]=program.paths(0 if phase=='prefix'else 0x368,{0x368:'loop-header',-4:'return'},state)
        result=p.compare(paths,streams)
        if result['differences']or not result['all_abstract_paths_covered']:
            return dict(passed=False,phase=phase,differences=len(result['differences']),first=next(iter(result['differences']),None))
        report[phase]=dict(raw_paths=result['raw_paths'],retail_paths=result['retail_paths'],joint_paths=result['joint_paths'])
    return dict(passed=True,phases=report)

def run():
    raw=list(struct.unpack('>344I',(OUT/'matrix-normal-form.bin').read_bytes()))
    answer={'baseline':check(raw)};assert answer['baseline']['passed']
    variants={}
    bad=raw[:]
    at=next(i for i,w in enumerate(bad)if w>>26==17 and w>>21&31==16 and w&63==3)
    assert bad[at]>>16&31==12;bad[at]=(bad[at]&~(31<<16))|(2<<16);variants['wrong-fade-denominator']=bad
    bad=raw[:]
    for i,w in enumerate(bad):
        if w>>26==3 and ((p.target.ENTRY&0xf0000000)|((w&0x3ffffff)<<2))==p.target.DISTANCE:
            before=i;break
    found=[]
    for i in range(before-16,before):
        w=bad[i]
        if w>>26==17 and w>>21&31==0 and w>>16&31 in(4,5):
            found.append(i);bad[i]=(w&~(31<<16))|((9-(w>>16&31))<<16)
    assert len(found)==2;variants['swapped-distance-arguments']=bad
    bad=raw[:]
    allocator=next(i for i,w in enumerate(bad)if w>>26==3 and ((p.target.ENTRY&0xf0000000)|((w&0x3ffffff)<<2))==p.target.ALLOC)
    assert bad[allocator+2]>>26==36;bad[allocator+2]=0;variants['missing-allocation-index-reload']=bad
    bad=raw[:];binding=p.roles(raw);descriptor,next_reg=binding['descriptor'],binding['next']
    advance=(next_reg<<21)|(descriptor<<11)|37
    copies=[i for i,w in enumerate(bad)if w==advance];assert len(copies)==3,copies
    for i in copies:bad[i]=(descriptor<<21)|(descriptor<<11)|37
    variants['lost-preloaded-next']=bad
    bad=raw[:];assert bad[before+1]==0;bad[before+1]=0xafa0007c;variants['unwritten-private-gap']=bad
    bad=raw[:]
    spill=[i for i,w in enumerate(bad)if w>>26==43 and w>>21&31==29 and w&65535==0x80]
    assert len(spill)==1;bad[spill[0]]=(bad[spill[0]]&0xffff0000)|0x84;variants['wrong-alpha-spill-home']=bad
    for name,words in variants.items():
        result=check(words);assert not result['passed'],('ineffective control',name);answer[name]=result
    # F14 is unused in the whole function. Recolor F6 consistently, preserving
    # every FP operation, transfer, status effect and private byte.
    assert not any(w>>26 in(49,57)and w>>16&31==14 for w in raw)
    positive=raw[:]
    def mapped(n):return 14 if n==6 else n
    for i,w in enumerate(positive):
        op,fmt=w>>26,w>>21&31
        if op in(49,57):positive[i]=(w&~(31<<16))|(mapped(w>>16&31)<<16)
        elif op==17 and fmt in(0,4):positive[i]=(w&~(31<<11))|(mapped(w>>11&31)<<11)
        elif op==17 and fmt in(16,20):
            positive[i]=(w&~((31<<16)|(31<<11)|(31<<6)))|(mapped(w>>16&31)<<16)|(mapped(w>>11&31)<<11)|(mapped(w>>6&31)<<6)
    result=check(positive);assert result['passed'],result;answer['positive-f6-to-f14']=result
    report=dict(controls=answer,negative_controls=len(variants),positive_controls=1,matching_credit=0)
    (OUT/'induction-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({name:{k:v for k,v in r.items()if k!='first'}for name,r in answer.items()}))
    return report
