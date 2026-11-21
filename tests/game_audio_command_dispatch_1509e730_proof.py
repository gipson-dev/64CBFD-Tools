"""Closed path/instruction proof for the dominated zero-return move."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
root=recovery.ROOT;out=recovery.OUT

from tools.tests import game_audio_command_dispatch_1509e730_guest as g
from tools.tests.game_audio_command_dispatch_1509e730_normalizer import ORDER

class Fetches(dict):
    def __init__(self,values):super().__init__(values);self.order=[]
    def __getitem__(self,key):self.order.append(key);return super().__getitem__(key)

def reads(word):
    op,rs,rt,fn=word>>26,word>>21&31,word>>16&31,word&63
    if op==0:
        if fn==0:return{rt}
        if fn==8:return{rs}
        assert fn in(33,37),(op,fn,hex(word));return{rs,rt}
    if op==3:return{4,5,6,7} # Defined o32 argument inputs, with V0 killed by the call.
    if op in(4,5,43):return{rs,rt}
    if op==15:return set()
    assert op in(9,11,12,13,35),hex(word)
    return{rs}

def audit(raw,rawtable,normal,table):
    assert len(raw)==len(normal)==92 and sorted(ORDER)==list(range(92))
    assert raw[8]==normal[86]==0x00001025 and raw[9]==0x00057080
    for new,old in enumerate(ORDER):
        a,b=raw[old],normal[new]
        if a>>26 in(4,5):assert(a&0xffff0000)==(b&0xffff0000)
        else:assert a==b,(new,old,'instruction identity')
    assert tuple(table)==tuple(g.ENTRY+4*ORDER.index((value-g.ENTRY)//4)for value in rawtable)
    conditionals=[]
    for i,word in enumerate(raw):
        if word>>26 in(4,5)and(word>>16&0x3ff)!=0:
            conditionals.append(word&0xffff0000)
    assert conditionals==[0x10200000,0x15e10000,0x17010000,0x15010000]
    assert raw[6]==0x2ca10007 and raw.count(0x24010005)==2 and raw.count(0x24010003)==1
    paths={};covered=[set(),set()]
    for command in range(8):
        for version in(0,3,5):
            models=[];traces=[]
            for index,(words,case_table)in enumerate(((raw,rawtable),(normal,table))):
                initial,args=g.fixture(case_table,command,version,0x1234f123,0x13579bdf,1,8,0)
                m=g.Oracle(words,initial,args,0x13579bdf,1,8);m.code=Fetches(m.code);m.run()
                trace=[(address-g.ENTRY)//4 for address in m.code.order]
                covered[index].update(trace)
                traces.append(trace if index==0 else[ORDER[i]for i in trace]);models.append(m)
            a,b=traces
            assert a.count(8)==1
            if command<7:
                assert b.count(8)==0 and len(models[0].calls)==len(models[1].calls)==1
                first_call=next(i for i,index in enumerate(a)if raw[index]>>26==3)
                assert all(2 not in reads(raw[index])for index in a[:first_call]),'V0 live before provider'
                assert[a for a in a if a!=8]==b
            else:
                assert b.count(8)==b.count(9)==1 and not models[0].calls and not models[1].calls
                assert models[0].r[2]==models[1].r[2]==0
                assert[a for a in a if a!=8]==[i for i in b if i not in(8,9)]
                zero_position=b.index(8)
                assert all(14 not in reads(raw[i])for i in b[zero_position+1:]),'default shift result is live'
            key=','.join(map(str,a));paths.setdefault(key,dict(commands=[],versions=[],raw=a,normalized_as_input_indices=b))
            paths[key]['commands'].append(command);paths[key]['versions'].append(version)
    assert covered==[set(range(92)),set(range(92))]
    return list(paths.values())

def run():
    obj=out/'qualified-source-screen/candidate.o';raw,rawtable=g.program(obj);normal,table=g.program(obj,True)
    paths=audit(raw,rawtable,normal,table);controls={}
    for name,at,value,badtable in(('wrong-instruction',14,normal[14]^0xf00,False),
     ('wrong-default-value',86,0x24020001,False),('skipped-default-zero',7,0x1020004f,False),
     ('wrong-command-table',0,0,True)):
        changed=list(normal);t=list(table)
        if badtable:t[1],t[2]=t[2],t[1]
        else:changed[at]=value
        try:audit(raw,rawtable,changed,t)
        except AssertionError:controls[name]=True
        else:raise AssertionError(name)
    report=dict(passes=True,unique_control_paths=len(paths),covered_words=92,
     complete_command_partition='Unsigned command <7 gives seven table targets; all other 32-bit values share default.',
     complete_version_partition='Only equality to 3 or 5 is tested; 0 represents all other 32-bit values.',
     instruction_permutation_bijective=True,only_removed_comparison_effect='V0=0 before every valid helper is dead under the o32 provider contract.',
     default_only_added_effect='Pure shift into caller-saved T6 is dead on default return.',
     ordered_effectful_instruction_sequences_identical=True,private_stack_operations_identical=True,
     effective_controls=controls,source_installed=recovery.installed(),matching_credit=0,
     assumptions='Read-only seven-entry code table, mapped ordinary RAM disjoint from private stack, and o32 providers observing defined arguments/public RAM, not nonargument registers or return-PC identity.')
    (out/'proof-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
    (out/'proof-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return report
