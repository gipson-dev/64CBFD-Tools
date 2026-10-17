"""Certify the scan's bounded opening schedule and all-loop scratch/LO roles."""
from collections import deque
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_sequence_event_scan as source
from tools.experiments import game_sequence_record_setup_matching as prior
from tools.experiments.game_sequence_state_reset_match import original
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import game_sequence_event_scan_oracle as model

BUILD = 'conker/build/game-sequence-event-scan-match'
RAW_SHA = '887e373590a5a49348a3264073762e84372b897230e37fd67ca26f240683e8c0'
RAW_BINDINGS_SHA = '77f161495d6b613e5c7c3aa5516667d29a5651db9a0c9f997119ebc37f51f2a4'
ORIGINAL_SHA = '30d85150cb453cac13e88a479e246fa3cac65f91c09252aa601c3aecb4ef6681'
ORIGINAL_BINDINGS_SHA = '454f45e9bc69d2383579570cddac1395b0befcfeb65c6095af7e52a008c35995'
GUARD_SUFFIX_SHA = 'bb872e87cfc12ad85231ef64e2582d70306773d9a66f0c9c785cc805b0b9f158'
ROUTING = {0x4C:0x50,0x50:0x4C,0x64:0x68,0x68:0x64,0x70:0x74,0x74:0x70,0x90:0x94,0x94:0x90}
CALLS = {'func_15023BB0':(11,True),'func_1517EE40':(6,False)}


def fields(word):
    if word>>26 == 0 and word&63 == 25: return (21,16),()
    if word>>26 == 0 and word&63 == 18: return (),(11,)
    return prior.fields(word)


def step_constants(word,values,relocated):
    result=list(values); _,writes=fields(word); value,_=prior.value_and_copy(word,values,relocated)
    for shift in writes:
        register=word>>shift&31
        if register: result[register]=value
    if word>>26 == 3: result[31]=None
    result[0]=0; return tuple(result)


def edges(words,index,bindings):
    word=words[index]; op=word>>26
    if op in prior.BRANCHES:
        result=[(prior.target(index,word),(index,index+1),None)]
        if not (op in (4,20) and word>>21&31 == word>>16&31):
            result.append((index+2,(index,) if op in (20,21,22,23) else (index,index+1),None))
        return result
    if op == 3:
        uses=bindings.get(index*4,[])
        if len(uses)!=1 or uses[0][0]!='R_MIPS_26' or uses[0][1] not in CALLS: raise ValueError('Unknown event scan call')
        return [(index+2,(index,index+1),CALLS[uses[0][1]])]
    if op == 0 and word&63 == 8: return [(None,(index,index+1),'return')]
    if op == 2: raise ValueError('Unexpected event scan jump')
    return [(index+1,(index,),None)]


def schedule(words,bindings):
    if len(words)!=219 or words[0]!=0x27BDFF80: raise ValueError('Complete scan frame required')
    expected={0x4C:0xA0200000,0x50:0x3C0E0000,0x64:0x904F0000,0x68:0xAFA20068,
        0x70:0x19E000AC,0x74:0x00008825,0x78:0x0013C100,0x90:0x0319B021,0x94:0x26F70000}
    if any(words[at//4]!=word for at,word in expected.items()): raise ValueError('Unknown scan opening schedule')
    if bindings.get(0x4C)!=[('R_MIPS_LO16','D_800C35AA')] or bindings.get(0x50)!=[('R_MIPS_HI16','D_800C363A')] or bindings.get(0x94)!=[('R_MIPS_LO16','D_80084110')]:
        raise ValueError('Unknown scan schedule bindings')
    for a,b in ((0x4C,0x50),(0x90,0x94)):
        read_a,write_a=fields(words[a//4]); read_b,write_b=fields(words[b//4])
        regs=lambda word,shifts:{word>>shift&31 for shift in shifts}-{0}
        if regs(words[a//4],write_a)&regs(words[b//4],read_b+write_b) or regs(words[b//4],write_b)&regs(words[a//4],read_a+write_a):
            raise ValueError('Dependent opening swap')
    moved=set(ROUTING)|{0x78}
    if any(prior.target(i,w)*4 in moved for i,w in enumerate(words) if w>>26 in prior.BRANCHES):
        raise ValueError('Schedule has an independent branch entry')
    # The shift added to the empty-path delay is nontrapping and dead before return.
    for word in words[0x324//4:]:
        reads,writes=fields(word)
        if any(word>>shift&31 == 24 for shift in reads): raise ValueError('Empty path observes the added delay result')
        if any(word>>shift&31 == 24 for shift in writes): break
    result=[words[ROUTING.get(i*4,i*4)//4] for i in range(len(words))]
    result[0x74//4]=result[0x74//4]&~65535|0xAB
    moved_bindings={}
    for index in range(len(words)):
        uses=bindings.get(ROUTING.get(index*4,index*4),[])
        if uses: moved_bindings[index*4]=uses
    return result,moved_bindings,dict(independent_register_swaps=2,
        private_count_store_and_public_count_load_disjoint_for_valid_slots=True,
        index_zero_before_branch_and_nontrapping_dead_empty_path_shift=True,
        valid_slots=[0,1],private_stack_disjoint_from_public_globals=True,
        raw_C_fault_prefix_equivalence_not_claimed=True)


def certify(words,wanted,bindings):
    if len(words)!=219 or len(wanted)!=219: raise ValueError('Complete scan proof bodies required')
    for i,(a,b) in enumerate(zip(words,wanted)):
        reads,writes=fields(a)
        if fields(b)!=(reads,writes): raise ValueError('Changed scan operand class')
        mask=sum(31<<shift for shift in set(reads+writes))
        if a&~mask != b&~mask: raise ValueError('Non-register scan field differs at %X'%(i*4))
        for shift in set(reads+writes):
            ra,rb=a>>shift&31,b>>shift&31
            if ra!=rb and not {ra,rb}<=prior.SCRATCH: raise ValueError('Non-scratch scan role differs')
    initial=(frozenset((r,r) for r in range(32)),(0,)+(None,)*31,(0,)+(None,)*31,False)
    states={0:initial}; pending=deque([0]); visited=set(); calls=set(); returns=set(); steps=0
    def step(pc,state):
        nonlocal steps
        relation,av,bv,lo=state; a,b=words[pc],wanted[pc]; reads,writes=fields(a)
        if not all((a>>shift&31,b>>shift&31) in relation for shift in reads):
            raise ValueError('Live scan operand mismatch at %X'%(pc*4))
        if a>>26 == 0 and a&63 == 18 and not lo: raise ValueError('Unrelated scan LO read')
        if a>>26 == 0 and a&63 == 25: lo=True
        ca,copya=prior.value_and_copy(a,av,bool(bindings.get(pc*4)))
        cb,copyb=prior.value_and_copy(b,bv,bool(bindings.get(pc*4)))
        before=relation; da={a>>shift&31 for shift in writes}-{0}; db={b>>shift&31 for shift in writes}-{0}
        relation={(x,y) for x,y in relation if x not in da and y not in db}
        for shift in writes:
            ra,rb=a>>shift&31,b>>shift&31
            if ra and rb: relation.add((ra,rb))
            if ra and copya is not None: relation.update((ra,y) for x,y in before if x==copya and y not in db)
            if rb and copyb is not None: relation.update((x,rb) for x,y in before if y==copyb and x not in da)
        av=step_constants(a,av,bool(bindings.get(pc*4))); bv=step_constants(b,bv,bool(bindings.get(pc*4)))
        if a>>26 == 3: relation.add((31,31))
        relation.update((ra,rb) for ra,v in enumerate(av) if v is not None for rb,u in enumerate(bv) if v==u)
        visited.add(pc); steps+=1
        return frozenset(relation),av,bv,lo
    while pending:
        index=pending.popleft()
        for destination,sequence,call in edges(words,index,bindings):
            state=states[index]
            for pc in sequence: state=step(pc,state)
            relation,av,bv,lo=state
            if isinstance(call,tuple):
                arity,returned=call
                if any((r,r) not in relation for r in (*range(4,4+min(4,arity)),*prior.SAVED)):
                    raise ValueError('Scan ABI/saved role escapes')
                relation=frozenset((a,b) for a,b in relation if a not in prior.CLOBBER and b not in prior.CLOBBER)
                if returned: relation=relation|{(2,2)}
                av=tuple(None if r in prior.CLOBBER else v for r,v in enumerate(av)); bv=tuple(None if r in prior.CLOBBER else v for r,v in enumerate(bv))
                calls.add(index); lo=False
            if call=='return':
                if any((r,r) not in relation for r in (*prior.SAVED,31)): raise ValueError('Scan return role escapes')
                returns.add(index)
            if destination is None: continue
            if not 0<=destination<len(words): raise ValueError('Scan CFG escapes complete body')
            next_state=relation,av,bv,lo
            if destination in states:
                old=states[destination]
                next_state=(old[0]&relation,prior.meet_constants(old[1],av),prior.meet_constants(old[2],bv),old[3] and lo)
            if next_state!=states.get(destination): states[destination]=next_state; pending.append(destination)
    if visited!=set(range(219)) or len(returns)!=1 or len(calls)!=8: raise ValueError('Incomplete scan fixed point')
    return dict(words_reached=219,CFG_nodes=len(states),transfer_steps=steps,call_sites=len(calls),
        return_sites=len(returns),ordered_operands_memory_and_ABI_closed=True,
        multiply_LO_provenance_closed_and_call_clobbered=True,no_commutative_rewrites=True)


def parts(obj):
    if any(data for name,(_,data) in source.sections(obj).items() if name.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))):
        raise ValueError('Unexpected scan private pool')
    text,functions,relocations=parse_object(obj); f=functions[source.FUNCTION]; data=text[f['value']:f['value']+f['size']]
    return list(struct.unpack('>%dI'%(len(data)//4),data)),{at-f['value']:uses for at,uses in relocations.items() if f['value']<=at<f['value']+f['size']},hashlib.sha256(data).hexdigest()


def qualify(root,out):
    obj,linked,row=source.measure(root,out,'raw',source.SELECTED); original_obj=original(root,out,'original-event-scan-match',source.FUNCTION)
    raw,bindings,digest=parts(obj); wanted,wanted_bindings,original_digest=parts(original_obj)
    checked_pair(raw,bindings,wanted,wanted_bindings)
    if digest!=RAW_SHA or row['diagnostics'] or row['frame']!=128: raise ValueError('Unknown scan compiler output')
    normalized,moved,opening=schedule(raw,bindings)
    if moved!=wanted_bindings: raise ValueError('Scan relocation routing differs')
    roles=certify(normalized,wanted,moved)
    receipt=dict(raw_words=219,frame=128,opening=opening,roles=roles,not_installed=True,no_matching_credit=True)
    (out/'certificate.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return obj,original_obj,raw,bindings,wanted,wanted_bindings,receipt


def checked_pair(raw,bindings,wanted,wanted_bindings):
    words_hash=lambda words:hashlib.sha256(struct.pack('>%dI'%len(words),*words)).hexdigest()
    binding_hash=lambda uses:hashlib.sha256(json.dumps(uses,sort_keys=True).encode()).hexdigest()
    if (words_hash(raw),binding_hash(bindings),words_hash(wanted),binding_hash(wanted_bindings))!=(
            RAW_SHA,RAW_BINDINGS_SHA,ORIGINAL_SHA,ORIGINAL_BINDINGS_SHA): raise ValueError('Unknown complete scan words/bindings')


def guard_bytes(before,raw,bindings,wanted,wanted_bindings):
    checked_pair(raw,bindings,wanted,wanted_bindings)
    normalized,moved,_=schedule(raw,bindings)
    if moved!=wanted_bindings: raise ValueError('Changed scan guard bindings')
    certify(normalized,wanted,moved)
    reader=csv.DictReader(io.StringIO(before.decode('ascii')))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader): raise ValueError('Scan guards already exist')
    stream=io.StringIO(newline=''); writer=csv.DictWriter(stream,fieldnames=reader.fieldnames,lineterminator='\n')
    encode=lambda uses:';'.join(kind+':'+name for kind,name in uses) or '-'
    count=0
    for index,(a,b) in enumerate(zip(raw,wanted)):
        if a==b and bindings.get(index*4,[])==wanted_bindings.get(index*4,[]): continue
        writer.writerow(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=encode(bindings.get(index*4,[])),
            replacement_relocations=encode(wanted_bindings.get(index*4,[])),
            note='Normalize certified event scan opening schedule and closed scratch roles',insert_after='',insert_after_relocations='',omit='false'))
        count+=1
    if count!=77 or not before.endswith(b'\n'): raise ValueError('Unknown scan guard extent')
    result=before+stream.getvalue().encode('ascii'); checked_guards(before,result); return result


def checked_guards(before,after):
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['guards']: raise ValueError('Unknown scan guard predecessor')
    if not after.startswith(before) or hashlib.sha256(after[len(before):]).hexdigest()!=GUARD_SUFFIX_SHA:
        raise ValueError('Changed certified scan guard suffix')


def guarded(root,out):
    obj,original_obj,raw,bindings,wanted,wanted_bindings,receipt=qualify(root,out)
    guards=out/'qualified-guards.csv'; guards.write_bytes(guard_bytes((out/'before-guards').read_bytes(),raw,bindings,wanted,wanted_bindings))
    script=out/'qualified-padded.s'; script.write_text(emit_padded_assembly(obj,out/'before-view_list_caller_original',
        word_patches_path=guards,filename=source.OWNER)); padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],capture_output=True,check=True)
    data,functions=source.build.link_owner(root,out,padded,source.OWNER); f=functions[source.FUNCTION]
    truth=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+876]
    if f['size']!=876 or data[f['value']:f['value']+876]!=truth: raise ValueError('Guarded complete scan differs from retail')
    receipt.update(byte_exact=True,direct=False,guards=77,insertions=0,omissions=0)
    (out/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return obj,padded,linked_words(data,f),receipt


def linked_words(data,function): return list(struct.unpack_from('>%dI'%(function['size']//4),data,function['value']))


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(guarded(root,root/BUILD)[-1],indent=2),flush=True)
