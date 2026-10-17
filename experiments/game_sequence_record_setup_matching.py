"""Certify the setup cursor invariant and closed scratch allocation on every CFG edge."""
from collections import deque
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_sequence_record_setup as source
from tools.experiments import game_sequence_record_setup_frame as frame
from tools.experiments import game_sequence_state_reset_match as reset_match
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_owner_endpoint_quad_matching import fields as prior_fields
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import game_sequence_record_setup_oracle as contract

BUILD = 'conker/build/game-sequence-record-setup-match'
SELECTED = frame.PREHEADER
OMIT, ADDRESS = 279, 282
RAW_SHA = '7591a7e391b9c2d3a36cd1e86e8200e5794d8f5f1ef149f0ec1b20bc2708e2e8'
RAW_BINDINGS_SHA = '19aeaceffebfc1008e6faa7023b1bacc129f134af966962ced320d537e6cd331'
ORIGINAL_SHA = 'fed829450c08e9bb8a198c16a1d20d8e139a95b9b9f9c8aa437824e5e092fd4b'
ORIGINAL_BINDINGS_SHA = '603e444031fa99b5f8e464abc59fd43134ffc586e38a814680354702f4608eb2'
GUARD_SUFFIX_SHA = '5b608c639774703df51abc471e893f1d9cc9e4058f03cfcb2275717176a7891c'
SCRATCH = frozenset((*range(1,16),24,25))
CLOBBER = SCRATCH | {31}
SAVED = (*range(16,24),28,29,30)
BRANCHES = (1,4,5,6,7,20,21,22,23)
MASK = 0xFFFFFFFF


def fields(word):
    op,fn=word>>26,word&63
    if op==0 and fn in (42,43):return (21,16),(11,)
    if op==0 and fn==9:return (21,),(11,)
    if op in (6,7,22,23):return (21,),()
    if op==1:
        if word>>16&31 not in (0,1,2,3):raise ValueError('Unknown setup REGIMM')
        return (21,),()
    return prior_fields(word)


def signed(value,bits=32):return value-(1<<bits) if value>>(bits-1) else value


def target(index,word):return index+1+signed(word&65535,16)


def call_info(word,index,bindings):
    if word>>26==3:
        uses=bindings.get(index*4,[])
        if len(uses)!=1 or uses[0][0]!='R_MIPS_26':raise ValueError('Unbound setup call')
        name=uses[0][1]
        address={'allocate_memory':contract.ALLOC,'bzero':contract.ZERO}.get(name)
        if address is None and name.startswith('func_'):address=int(name[5:],16)
        if address not in contract.ARITIES:raise ValueError('Unknown setup call contract: '+name)
        return contract.ARITIES[address],name in ('allocate_memory','func_1501D1D4','func_1501CFF8')
    if word>>26==0 and word&63==9:
        if word>>11&31!=31:raise ValueError('Unknown setup indirect link register')
        return 4,False
    return None


def edges(words,index,bindings):
    word=words[index];op=word>>26
    if op in BRANCHES:
        destination=target(index,word)
        choices=[(destination,(index,index+1),None)]
        unconditional=op in (4,20) and word>>21&31==word>>16&31
        if not unconditional:
            choices.append((index+2,(index,) if op in (20,21,22,23) or op==1 and word>>16&2 else (index,index+1),None))
        return choices
    call=call_info(word,index,bindings)
    if call is not None:return [(index+2,(index,index+1),call)]
    if op==0 and word&63==8:return [(None,(index,index+1),'return')]
    if op==2:raise ValueError('Unexpected setup absolute jump')
    return [(index+1,(index,),None)]


def value_and_copy(word,values,relocated=False):
    op,rs,rt,shift,fn=word>>26,word>>21&31,word>>16&31,word>>6&31,word&63
    a,b=values[rs],values[rt];imm=word&65535
    # A relocatable immediate is not the numeric zero present before linking.
    if relocated:return None,None
    if op==15:return imm<<16,None
    if op==9:
        return None if a is None else (a+signed(imm,16))&MASK,rs if imm==0 else None
    if op in (12,13,14):
        value=None if a is None else (a&imm if op==12 else a|imm if op==13 else a^imm)
        return value,rs if op in (13,14) and imm==0 else None
    if op==0:
        if fn in (0,2,3):
            value=None if b is None else ((b<<shift)&MASK if fn==0 else b>>shift if fn==2 else signed(b)>>shift&MASK)
            return value,rt if shift==0 else None
        if fn in (33,37) and (a==0 or b==0):return b if a==0 else a,rt if a==0 else rs
        if a is not None and b is not None:
            if fn==33:return (a+b)&MASK,None
            if fn==35:return (a-b)&MASK,None
            if fn==37:return a|b,None
            if fn==42:return int(signed(a)<signed(b)),None
            if fn==43:return int(a<b),None
    return None,None


def constant_step(word,values,relocated=False):
    values=list(values);_,writes=fields(word)
    result,_=value_and_copy(word,values,relocated)
    for shift in writes:
        register=word>>shift&31
        if register:values[register]=result
    if word>>26==3:values[31]=None
    values[0]=0
    return tuple(values)


def meet_constants(a,b):return tuple(x if x==y else None for x,y in zip(a,b))


def constants(words,bindings):
    initial=(0,)+(None,)*31;states={0:initial};pending=deque([0]);visited=set()
    while pending:
        index=pending.popleft()
        for destination,sequence,call in edges(words,index,bindings):
            state=states[index]
            for pc in sequence:
                state=constant_step(words[pc],state,bool(bindings.get(pc*4)));visited.add(pc)
            if isinstance(call,tuple):state=tuple(None if r in CLOBBER else v for r,v in enumerate(state))
            if destination is None:continue
            if not 0<=destination<len(words):raise ValueError('Setup CFG escapes complete body')
            merged=state if destination not in states else meet_constants(states[destination],state)
            if merged!=states.get(destination):states[destination]=merged;pending.append(destination)
    return states,visited


def cursor_certificate(words,bindings):
    if len(words)!=474 or words[OMIT]!=0x0013C0C0 or words[ADDRESS]!=0x00F81021:
        raise ValueError('Unknown cursor scale/add shape')
    if bindings.get(OMIT*4) or bindings.get(ADDRESS*4):raise ValueError('Cursor arithmetic has a relocation')
    if any(OMIT in sequence[1:] for i in range(len(words)) for _,sequence,_ in edges(words,i,bindings)):
        raise ValueError('Scale is a delay instruction')
    if any(target(i,w)==OMIT for i,w in enumerate(words) if w>>26 in BRANCHES):
        raise ValueError('Scale is an independent branch target')
    states,visited=constants(words,bindings)
    if OMIT not in states or states[OMIT][19]!=1:raise ValueError('Cursor is not invariant one at the preheader')
    temp=24;pending=[OMIT+1];seen=set();uses=set()
    while pending:
        index=pending.pop()
        if index in seen:continue
        seen.add(index)
        for destination,sequence,call in edges(words,index,bindings):
            killed=False
            for pc in sequence:
                reads,writes=fields(words[pc])
                if any(words[pc]>>shift&31==temp for shift in reads):uses.add(pc)
                if any(words[pc]>>shift&31==temp for shift in writes):killed=True;break
            if isinstance(call,tuple):killed=True
            if not killed and destination is not None:pending.append(destination)
    if uses!={ADDRESS}:raise ValueError('Cursor scale result has another live use')
    ra_reads=[i for i,w in enumerate(words) if any(w>>shift&31==31 for shift in fields(w)[0])]
    if ra_reads!=[7,472]:raise ValueError('Return links escape the normal save/return boundary')
    return dict(invariant_register=19,invariant_value=1,extra_word=OMIT,
        sole_result_use=ADDRESS,caller_saved_temp=temp,return_link_reads=ra_reads,
        CFG_words_reached=len(visited))


def fold_cursor(words,bindings):
    certificate=cursor_certificate(words,bindings);result=[];moved={}
    for index,word in enumerate(words):
        if index==OMIT:continue
        placed=index if index<OMIT else index-1
        if index==ADDRESS:
            word=(9<<26)|(word>>21&31)<<21|(word>>11&31)<<16|8
        elif word>>26 in BRANCHES:
            destination=target(index,word);destination-=int(destination>OMIT)
            word=word&~65535|(destination-placed-1)&65535
        result.append(word)
        if index*4 in bindings:moved[placed*4]=bindings[index*4]
    return result,moved,certificate


def operand_certificate(words,wanted,bindings):
    if len(words)!=len(wanted) or len(words)!=473:raise ValueError('Complete paired setup bodies required')
    for index,(a,b) in enumerate(zip(words,wanted)):
        reads,writes=fields(a)
        if fields(b)!=(reads,writes):raise ValueError('Changed setup operand class')
        mask=sum(31<<shift for shift in set(reads+writes))
        if a&~mask!=b&~mask:raise ValueError('Non-register setup field differs at %X'%(index*4))
        for shift in set(reads+writes):
            ra,rb=a>>shift&31,b>>shift&31
            if ra!=rb and not {ra,rb}<=SCRATCH:raise ValueError('Non-scratch setup role differs')
    # Must-equal register pairs meet by intersection, covering arbitrary loop counts.
    initial=(frozenset((r,r) for r in range(32)),(0,)+(None,)*31,(0,)+(None,)*31)
    states={0:initial};pending=deque([0]);visited=set();calls=set();returns=set();commuted=set();steps=0
    def step(pc,state):
        nonlocal steps
        relation,av,bv=state;a,b=words[pc],wanted[pc];reads,writes=fields(a)
        operands=[(a>>shift&31,b>>shift&31) for shift in reads]
        if not all(pair in relation for pair in operands):
            op,fn=a>>26,a&63
            reversible=op==0 and fn in (33,37) or op in (4,5,20,21)
            reversed_pairs=[(a>>reads[0]&31,b>>reads[1]&31),(a>>reads[1]&31,b>>reads[0]&31)] if len(reads)==2 else []
            if not reversible or len(reads)!=2 or not all(pair in relation for pair in reversed_pairs):
                raise ValueError('Live setup operand mismatch at %X: %s'%(pc*4,operands))
            commuted.add(pc)
        ca,copya=value_and_copy(a,av,bool(bindings.get(pc*4)))
        cb,copyb=value_and_copy(b,bv,bool(bindings.get(pc*4)))
        before=relation;da={a>>shift&31 for shift in writes}-{0};db={b>>shift&31 for shift in writes}-{0}
        relation={(ra,rb) for ra,rb in relation if ra not in da and rb not in db}
        for shift in writes:
            ra,rb=a>>shift&31,b>>shift&31
            if ra and rb:relation.add((ra,rb))
            if ra and copya is not None:relation.update((ra,y) for x,y in before if x==copya and y not in db)
            if rb and copyb is not None:relation.update((x,rb) for x,y in before if y==copyb and x not in da)
        av=constant_step(a,av,bool(bindings.get(pc*4)));bv=constant_step(b,bv,bool(bindings.get(pc*4)))
        if a>>26==3:relation.add((31,31))
        relation.update((ra,rb) for ra,v in enumerate(av) if v is not None for rb,u in enumerate(bv) if v==u)
        visited.add(pc);steps+=1
        return frozenset(relation),av,bv
    while pending:
        index=pending.popleft()
        for destination,sequence,call in edges(words,index,bindings):
            state=states[index]
            for pc in sequence:state=step(pc,state)
            relation,av,bv=state
            if isinstance(call,tuple):
                arity,returned=call
                if any((r,r) not in relation for r in (*range(4,4+min(4,arity)),*SAVED)):
                    raise ValueError('Setup ABI role escapes at call %X'%(index*4))
                # Calls observe ABI inputs/shared memory; retain only defined return values.
                relation=frozenset((a,b) for a,b in relation if a not in CLOBBER and b not in CLOBBER)
                if returned:relation=relation|{(2,2)}
                av=tuple(None if r in CLOBBER else v for r,v in enumerate(av));bv=tuple(None if r in CLOBBER else v for r,v in enumerate(bv))
                calls.add(index)
            if call=='return':
                if any((r,r) not in relation for r in (*SAVED,31)):
                    raise ValueError('Setup saved/return role escapes')
                returns.add(index)
            if destination is None:continue
            next_state=relation,av,bv
            if destination in states:
                old=states[destination]
                next_state=(old[0]&relation,meet_constants(old[1],av),meet_constants(old[2],bv))
            if next_state!=states.get(destination):states[destination]=next_state;pending.append(destination)
    if visited!=set(range(473)) or len(returns)!=1:raise ValueError('Incomplete setup fixed-point proof')
    return dict(words_reached=len(visited),CFG_nodes=len(states),transfer_steps=steps,
        call_sites=len(calls),return_sites=len(returns),commutative_words=sorted(commuted),
        ordered_operands_memory_and_control_invariant=True,ABI_and_nonvolatile_roles_closed=True)


def parts(obj):
    if any(data for name,(_,data) in sections(obj).items() if name.startswith(
            ('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))):
        raise ValueError('Unexpected setup private pool')
    text,functions,relocations=parse_object(obj);f=functions[source.FUNCTION]
    data=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:uses for at,uses in relocations.items() if f['value']<=at<f['value']+f['size']}
    return list(struct.unpack('>%dI'%(len(data)//4),data)),bindings,hashlib.sha256(data).hexdigest()


def checked_pair(raw,bindings,wanted,wanted_bindings):
    word_hash=lambda words:hashlib.sha256(struct.pack('>%dI'%len(words),*words)).hexdigest()
    binding_hash=lambda uses:hashlib.sha256(json.dumps(uses,sort_keys=True).encode()).hexdigest()
    if (word_hash(raw),binding_hash(bindings),word_hash(wanted),binding_hash(wanted_bindings))!=(
            RAW_SHA,RAW_BINDINGS_SHA,ORIGINAL_SHA,ORIGINAL_BINDINGS_SHA):
        raise ValueError('Unknown complete setup words/bindings')


def qualify(root,out):
    obj,_,row=source.measure(root,out,'raw',SELECTED)
    original=reset_match.original(root,out,'original-setup-match',source.FUNCTION)
    raw,bindings,digest=parts(obj);wanted,wanted_bindings,original_digest=parts(original)
    checked_pair(raw,bindings,wanted,wanted_bindings)
    if row['diagnostics'] or row['pools'] or row['frame']!=120:
        raise ValueError('Unknown setup compiler frame/diagnostics/pools')
    folded,moved,cursor=fold_cursor(raw,bindings)
    if moved!=wanted_bindings:raise ValueError('Setup relocation routing differs')
    roles=operand_certificate(folded,wanted,moved)
    receipt=dict(cursor=cursor,roles=roles,raw_words=474,normalized_words=473,
        frame=120,private_homes_unchanged=True,not_installed=True,no_matching_credit=True)
    (out/'certificate.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return obj,original,raw,folded,wanted,bindings,receipt


def guard_rows(raw,bindings,wanted):
    word_hash=lambda words:hashlib.sha256(struct.pack('>%dI'%len(words),*words)).hexdigest()
    binding_hash=hashlib.sha256(json.dumps(bindings,sort_keys=True).encode()).hexdigest()
    if (word_hash(raw),binding_hash,word_hash(wanted))!=(RAW_SHA,RAW_BINDINGS_SHA,ORIGINAL_SHA):
        raise ValueError('Unknown setup guard input words/bindings')
    folded,moved,_=fold_cursor(raw,bindings)
    operand_certificate(folded,wanted,moved)
    result=[]
    encode=lambda uses:';'.join(kind+':'+name for kind,name in uses) or '-'
    placed=0
    for index,word in enumerate(raw):
        omit=index==OMIT
        if omit:
            replacement=word;replacements=[]
        else:
            reads,writes=fields(folded[placed]);mask=sum(31<<shift for shift in set(reads+writes))
            replacement=folded[placed]&~mask|wanted[placed]&mask
            if replacement!=wanted[placed]:raise ValueError('Setup differs beyond certified operand fields')
            replacements=moved.get(placed*4,[])
        uses=bindings.get(index*4,[])
        if omit or word!=replacement or uses!=replacements:
            result.append(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%(index*4),
                expected='0x%08X'%word,replacement='0x%08X'%replacement,
                expected_relocations=encode(uses),replacement_relocations=encode(replacements),
                note='Normalize certified setup cursor-one induction and closed scratch roles',
                insert_after='',insert_after_relocations='',omit=str(omit).lower()))
        placed+=int(not omit)
    if len(result)!=165:raise ValueError('Unknown complete setup guard extent')
    return result


def guard_bytes(before,raw,bindings,wanted):
    if not before.endswith(b'\n'):raise ValueError('Unknown guard manifest ending')
    reader=csv.DictReader(io.StringIO(before.decode('ascii')))
    if any(row['filename']==source.OWNER and row['function']==source.FUNCTION for row in reader):
        raise ValueError('Setup guards already exist')
    stream=io.StringIO(newline='')
    csv.DictWriter(stream,fieldnames=reader.fieldnames,lineterminator='\n').writerows(guard_rows(raw,bindings,wanted))
    result=before+stream.getvalue().encode('ascii')
    checked_guard_bytes(before,result)
    return result


def checked_guard_bytes(before,after):
    if hashlib.sha256(before).hexdigest()!=source.BASELINE['guards']:
        raise ValueError('Unknown setup guard predecessor')
    if not after.startswith(before) or hashlib.sha256(after[len(before):]).hexdigest()!=GUARD_SUFFIX_SHA:
        raise ValueError('Changed certified setup guard suffix')


def guarded(root,out):
    obj,original,raw,folded,wanted,bindings,receipt=qualify(root,out)
    before=(out/'before-guards').read_bytes();guards=out/'qualified-guards.csv'
    guards.write_bytes(guard_bytes(before,raw,bindings,wanted))
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,out/'before-view_list_caller_original',
        word_patches_path=guards,filename=source.OWNER))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],capture_output=True,check=True)
    data,functions=source.build.link_owner(root,out,padded,source.OWNER);f=functions[source.FUNCTION]
    truth=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+1892]
    if f['size']!=1892 or data[f['value']:f['value']+f['size']]!=truth:
        raise ValueError('Guarded complete setup differs from retail')
    receipt.update(byte_exact=True,direct=False,installed=False,
        guards=len(guard_rows(raw,bindings,wanted)),omitted_words=1,inserted_words=0)
    (out/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return obj,padded,raw,list(struct.unpack_from('>473I',data,f['value'])),receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--guarded',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    print(json.dumps((guarded if args.guarded else qualify)(root,root/BUILD)[-1],indent=2))
