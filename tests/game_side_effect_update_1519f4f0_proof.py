"""Whole-CFG equivalence from three checked local transformation lemmas.

The relation maps only unpassed private save homes, exchanges two internal
single FP roles and commutes one ordinary field read past a disjoint field
write. Every control edge, call, arithmetic operation and public write remains.
Storage is valid/aligned ordinary memory, public objects do not alias private
stack, and ABI providers observe arguments/public memory/FCSR, not unpassed
registers, implementation PCs or private homes. Raw fault scratch states,
volatile/MMIO and concurrent observers are outside this normal-execution proof.
The guarded stream separately restores retail's actual access/fault order.
"""
import json,struct
from tools.experiments import game_side_effect_update_1519f4f0_match as s

def fp_roles(w):
    op,fmt,fn=w>>26,w>>21&31,w&63
    fields=(16,) if op in (49,57) else (11,) if op==17 and fmt in (0,4) else (11,16,6) if op==17 and fmt==16 and fn<8 else (11,16) if op==17 and fmt==16 and fn==60 else ()
    for shift in fields:
        v=(w>>shift)&31
        if v in (20,22):w=(w&~(31<<shift))|((42-v)<<shift)
    return w

def normalize_words(raw):
    assert len(raw)==192 and raw[0]==0x27BDFF80 and raw[-1]==0x27BD0080
    result=[]
    for index,w in enumerate(raw):
        op,rs,rt=w>>26,w>>21&31,w>>16&31
        if index==0:w+=8
        elif index==191:w-=8
        elif rs==29 and ((op in (49,57) and (w&65535) in (0x60,0x64,0x68)) or op==9 and rt==4 and (w&65535)==0x60):w-=8
        # Callee-saved entry/exit pairs retain their ABI registers. Only the
        # loop's two single-value roles are renamed; both dominate every use.
        if 0x80<=4*index<0x1C8:w=fp_roles(w)
        result.append(w)
    at=0x154//4
    assert result[at:at+4]==[0xC6280000,0x46128102,0x46045180,0xE6260004]
    result[at:at+4]=result[at+1:at+4]+result[at:at+1]
    return result

def branch_targets(words):
    result=[]
    for i,w in enumerate(words):
        op,rs=w>>26,w>>21&31
        if op in (1,4,5,6,7,20,21,22,23) or op==17 and rs==8:
            result.append((4*i,4*(i+1+(((w&65535)^32768)-32768))))
    return result

def control_graph(words):
    edges={};todo=[(0,None)]
    while todo:
        node=todo.pop()
        if node in edges:continue
        pc,after=node
        if pc==-4:edges[node]=set();continue
        assert pc%4==0 and 0<=pc<4*len(words)
        w=words[pc//4];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if after is not None:successors={(after,None)}
        elif op in (1,4,5,6,7,20,21,22,23) or op==17 and rs==8:
            target=pc+4+4*(((w&65535)^32768)-32768)
            likely=op in (20,21,22,23) or op==1 and rt in (2,3) or op==17 and bool(rt&2)
            fixed=(rs==rt) if op in (4,20) and rs==rt else False if op in (5,21) and rs==rt else None
            successors=set()
            if fixed is not False:successors.add((pc+4,target))
            if fixed is not True:successors.add((pc+8,None) if likely else (pc+4,pc+8))
        elif op==3:successors={(pc+4,pc+8)}
        elif op==0 and w&63==8:assert rs==31;successors={(pc+4,-4)}
        else:successors={(pc+4,None)}
        edges[node]=successors;todo.extend(successors)
    return edges

def dominance(words):
    graph=control_graph(words);nodes=set(graph);preds={n:set() for n in nodes}
    for n,es in graph.items():
        for m in es:preds[m].add(n)
    dom={n:{n} if n==(0,None) else set(nodes) for n in nodes};changed=True
    while changed:
        changed=False
        for n in nodes-{(0,None)}:
            updated={n}|set.intersection(*(dom[p] for p in preds[n]))
            if updated!=dom[n]:dom[n]=updated;changed=True
    for n in nodes:
        pc,_=n
        if not 0x80<=pc<0x1C8:continue
        w=words[pc//4];op,fmt,fn=w>>26,w>>21&31,w&63
        reads=[]
        if op==17 and fmt==16:reads=[w>>11&31,w>>16&31]
        for reg,definition in ((20,0x80),(22,0x8C)):
            if reg in reads:assert (definition,None) in dom[n],('undominated FP role',pc,reg)
    return {pc for pc,after in nodes if pc>=0}

def qualify(raw,normal):
    assert normalize_words(raw)==normal
    assert branch_targets(raw)==branch_targets(normal)
    assert all(not 0x154<target<=0x160 for _,target in branch_targets(raw)), 'Interior entry into commute block'
    assert [i for i,w in enumerate(raw) if w>>26==3]==[0x1C4//4]
    # Both values are defined before all body uses, on the sole entrance to
    # the loop. No double/saved-pair operation observes these internal roles.
    assert raw[0x80//4]>>16&31==20 and raw[0x8C//4]==0x4481B000
    assert normal[0x80//4]>>16&31==22 and normal[0x8C//4]==0x4481A000
    assert raw[0x78//4]==normal[0x78//4]==0x12590075
    fp_use_offsets=[]
    for i,w in enumerate(raw):
        if fp_roles(w)!=w:
            if w>>26 in (53,61):raise AssertionError('Changed ABI double lane')
            fp_use_offsets.append(4*i)
            assert 0x80<=4*i<0x1C8
    assert fp_use_offsets==[0x80,0x8C,0x170,0x17C,0x194,0x1B8]
    # All stack memory accesses are either matching ABI save/reload pairs or
    # the twelve-byte vector. Their regions and the callback's four-word
    # home area are disjoint and inside their respective complete frames.
    homes={}
    for label,words,frame in (('raw',raw,128),('retail',normal,120)):
        saves={};loads={};vector=[]
        for i,w in enumerate(words):
            op,rs,rt,off=w>>26,w>>21&31,w>>16&31,w&65535
            if rs!=29 or op not in (35,43,49,53,57,61):continue
            size=8 if op in (53,61) else 4;assert 16<=off and off+size<=frame
            if op in (43,61):assert off not in saves;saves[off]=(op,rt,size)
            elif op in (35,53):assert off not in loads;loads[off]=(op,rt,size)
            else:vector.append((op,rt,off-frame))
        assert len(saves)==len(loads)==12
        for off,(op,reg,size) in saves.items():assert loads[off]==(35 if op==43 else 53,reg,size)
        assert sorted(saves)==[0x18,0x20,0x28,0x2C,0x30,0x34,0x38,0x3C,0x40,0x44,0x48,0x4C]
        assert sorted({off for _,_,off in vector})==[-32,-28,-24]
        homes[label]=(saves,loads,vector)
    assert homes['raw'][2]==homes['retail'][2]
    assert raw[0x1B0//4]==0x27A40060 and normal[0x1B0//4]==0x27A40058
    # The read defines F8, unused by the intervening MUL/ADD/SWC1. Their
    # base S1 is unchanged; offsets zero and four cannot alias. FP operation
    # order and FCSR effects are unchanged, including exceptional operands.
    commute=raw[0x154//4:0x164//4]
    assert commute==[0xC6280000,0x46128102,0x46045180,0xE6260004]
    assert (commute[0]>>21&31,commute[0]&65535)==(17,0)
    assert (commute[3]>>21&31,commute[3]&65535)==(17,4)
    for w in commute[1:3]:assert all((w>>shift&31)!=8 for shift in (6,11,16))
    assert raw[0x290//4]==normal[0x290//4], 'Unproved tail operand rewrite'
    reachable=dominance(raw);assert len(reachable)==187
    assert control_graph(raw)==control_graph(normal)
    return dict(whole_CFG=True,control_edges=len(branch_targets(raw)),loop_induction=True,private_frames=[128,120],
                vector_absolute_offsets=[-32,-28,-24],saved_pairs=12,FP_role_offsets=fp_use_offsets,
                disjoint_read_write_commute=[0,4],opaque_provider_arguments_preserved=True,raw_fault_identity=False,
                reachable_words=len(reachable),unreachable_offsets=[4*i for i in range(192) if 4*i not in reachable])

def main():
    p=s.programs();report=qualify(p['candidate'],p['guarded']);(s.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
