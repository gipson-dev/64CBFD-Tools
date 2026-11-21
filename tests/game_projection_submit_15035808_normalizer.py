"""Closed expected-input source-origin derivation; reads no retail bytes/assembly."""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
import hashlib,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_list_draw_1517e4a8_normalizer import gpr_fields,branch
OUT=recovery.OUT
PLAN_SHA='d5a67b544eac81613a4f8d0bc7194415cf7d3e8cfff632fd8862570022e2ef1c'

def fp_fields(w):
    if w>>26 in(49,53,57,61):return(16,)
    if w>>26==17:
        fmt=w>>21&31
        if fmt in(0,4):return(11,)
        if fmt in(16,20):return(16,11,6)
    return()

def derive(raw,refs,plan):
    if hashlib.sha256((json.dumps(plan,indent=2)+'\n').encode()).hexdigest()!=PLAN_SHA:raise ValueError('Changed projection submission plan')
    if hashlib.sha256(raw).hexdigest()!=plan['source_raw_sha256']:raise ValueError('Changed projection submission payload')
    if json.loads(json.dumps(refs))!=plan['source_refs']:raise ValueError('Changed projection submission bindings')
    words=struct.unpack('>345I',raw);result=[];bindings={}
    assert words[0]==0x27bdff28
    for dest in range(345):
        origin=plan['origins'][str(dest)];w=words[origin];original=w
        for fields,colors in((gpr_fields(w),plan['gpr_roles'].get(str(dest),{})),(fp_fields(w),plan['fp_roles'].get(str(dest),{}))):
            for shift in fields:
                reg=original>>shift&31
                if str(reg)in colors:w=(w&~(31<<shift))|(colors[str(reg)]<<shift)
        action=plan['control_actions'].get(str(dest))
        if action=='nonlikely-fp-branch':
            assert original>>26==17 and original>>21&31==8 and original>>16&31==2
            w&=~(2<<16)
        elif action=='initial-true-flag':
            assert original>>26==9 and original>>21&31==0 and original&65535==1
        elif action=='attachment-nonzero-branch':
            assert original>>26==5 and original>>16&31==0
        elif action=='false-flag-zero':
            assert original>>26==0 and original&63==37
        elif action is not None:raise ValueError(('Unknown control action',action))
        if str(dest)in plan['stack_offsets']:
            assert original>>26 in(35,43)and original>>21&31==29 and original&65535==0x88
            w=(w&0xffff0000)|plan['stack_offsets'][str(dest)]
        if str(dest)in plan['branch_destinations']:
            assert branch(w);target=plan['branch_destinations'][str(dest)];assert 0<=target<345
            immediate=target-dest-1;w=(w&0xffff0000)|(immediate&65535)
        result.append(w)
        if origin*4 in refs:bindings[dest*4]=refs[origin*4]
    return struct.pack('>345I',*result),bindings

def run():
    plan=recovery.SPEC['schedule_plan']
    raw,refs=payload(recovery.WHERE/'candidate.o','func_15035808')
    blob,bindings=derive(raw,refs,plan)
    (OUT/'closed-schedule.bin').write_bytes(blob)
    (OUT/'closed-schedule-bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    print(json.dumps(dict(words=len(blob)//4,frame=216,source_origin_only=True,output_sha256=hashlib.sha256(blob).hexdigest(),relocation_sites=len(bindings),matching_credit=0)))
