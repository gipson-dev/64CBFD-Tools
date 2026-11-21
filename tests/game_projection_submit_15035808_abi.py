"""Original caller CFG audit for the unused V0 result and typed caller check."""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
root=recovery.ROOT
import json,re
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
out=recovery.OUT;where=out/'abi';where.mkdir(exist_ok=True)

def rw(w):
    op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
    if op==0:
        if fn in(0,2,3):return{rt},{rd}
        if fn in(4,6,7,*range(32,44)):return{rs,rt},{rd}
        if fn in(16,18):return set(),{rd}
        if fn in(17,19,8):return{rs},set()
        if fn==9:return{rs},{rd}
        if fn in(24,25,26,27):return{rs,rt},set()
    if op in(2,3):return set(),{31}if op==3 else set()
    if op in(4,5,20,21):return{rs,rt},set()
    if op in(1,6,7,22,23):return{rs},set()
    if 8<=op<=15:return({rs}if op!=15 else set()),{rt}
    if 32<=op<=39:return{rs},{rt}
    if 40<=op<=46:return{rs,rt},set()
    if op in(49,53,57,61):return{rs},set()
    if op==17:
        if rs in(0,2):return set(),{rt}
        if rs in(4,6):return{rt},set()
        return set(),set()
    raise AssertionError(('unsupported caller opcode',hex(w)))

def function(path,callrom):
    text=path.read_text();current=None;functions={}
    for line in text.splitlines():
        if line.startswith('glabel '):current=line.split()[1];functions[current]=[]
        m=re.search(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]+) \*/',line)
        if m and current:functions[current].append(tuple(int(v,16)for v in m.groups()))
    found=[(name,rows)for name,rows in functions.items()if any(r==callrom for r,_,_ in rows)];assert len(found)==1
    return found[0]

def dead_result(path,callrom,inject_result_read=False):
    name,rows=function(path,callrom);code={v:w for _,v,w in rows};va=next(v for r,v,_ in rows if r==callrom)
    assert code[va]>>26==3 and code[va]&0x3ffffff==0x15035808>>2&0x3ffffff
    if inject_result_read:code[va+8]=0x00404025
    pending=[va+8];seen=set();stops=[]
    def execute(pc):
        reads,writes=rw(code[pc]);assert 2 not in reads,('V0 result used',name,hex(pc),hex(code[pc]))
        if 2 in writes:stops.append(('redefinition',pc));return False
        return True
    while pending:
        pc=pending.pop()
        if pc in seen:continue
        seen.add(pc);assert pc in code,('escaped caller',name,hex(pc))
        if not execute(pc):continue
        w=code[pc];op=w>>26
        if op in(1,4,5,6,7,20,21,22,23)or op==17 and w>>21&31==8:
            dest=pc+4+4*(((w&65535)^32768)-32768)
            if execute(pc+4):pending.append(dest)
            if op>=20 or op==17 and w>>16&2:pending.append(pc+8)
            elif execute(pc+4):pending.append(pc+8)
        elif op==3 or op==0 and w&63==9:
            execute(pc+4);stops.append(('next_o32_call',pc))
        elif op==2:
            if execute(pc+4):pending.append(((pc+4)&0xf0000000)|((w&0x3ffffff)<<2))
        elif op==0 and w&63==8:
            assert w>>21&31==31,('computed return',name,hex(pc));execute(pc+4);stops.append(('void_caller_return',pc))
        else:pending.append(pc+4)
    assert stops
    return dict(function=name,call_rom=callrom,call_va=va,visited_successor_words=len(seen),stops=stops,
        result_reads_before_redefinition_call_or_void_return=0)

def run():
    reports=[dead_result(root/path,rom)for path,rom in(('conker/asm/61D10.s',0x63764),('conker/asm/CDE80.s',0xCE44C),('conker/asm/CDE80.s',0xCE480))]
    controls=[]
    for path,rom in(('conker/asm/61D10.s',0x63764),('conker/asm/CDE80.s',0xCE44C),('conker/asm/CDE80.s',0xCE480)):
        try:dead_result(root/path,rom,True)
        except AssertionError as error:
            assert 'V0 result used'in str(error),str(error);controls.append(rom)
        else:raise AssertionError('Ineffective caller result-read control')
    for path,name in(('conker/src/game/generated_61D10.c','func_15036148'),('conker/src/game/generated_CDE80.c','func_150A0D8C')):
        assert re.search(r'^void '+name+r'\([^;{}]*\)\s*\{',(root/path).read_text(),re.M),name
    caller='conker/src/game/generated_CDE80.c';before=(out/'baseline'/caller).read_text()
    old='s32 func_15035808(s32, s32, f32, f32, f32, f32, f32, f32, f32, f32);'
    new='void func_15035808(s32, s32, f32, f32, f32, f32, f32, f32, f32, f32);'
    assert before.count(old)==1;selected=before.replace(old,new)
    a,ad=compile_owner(root,where,before,'caller-before');b,bd=compile_owner(root,where,selected,'caller-after')
    assert ad.replace('caller-before','caller-input')==bd.replace('caller-after','caller-input')
    neighbors=same_functions(a,b,());assert normalized_pools(a)==normalized_pools(b)
    (where/'selected-caller.c').write_text(selected)
    r=dict(callers=reports,return_interface='void: all three known original callers discard V0',computed_callers_unexcluded=True,
        effective_result_read_controls=controls,known_callers_have_void_C_definitions=True,
        unchanged_caller_functions=neighbors,caller_diagnostics=ad,matching_credit=0)
    (out/'abi.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

    return r
