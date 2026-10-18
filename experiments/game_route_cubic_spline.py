"""Recover a four-point cubic spline with closed FP-lineage scheduling guards."""
import argparse
from collections import Counter,defaultdict
from contextlib import contextmanager
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-route-cubic-spline'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_76C90','func_150497E0',0x150497E0,0x76C90,49
INPUTS={
    'conker/src/game/generated_76C90.c':'32c8d5cd739d4cca4b46bd604365d2ab3ff8ed96d600ea17005b1bce9cb29665',
    'conker/build/conker.us.elf':'a5c5541dc8f6863ebefac2896237ce0bc39a88e3893711c35cd0393fd851ecd7',
    'conker/retail_word_patches.us.csv':'eb4dc7f42da17c278c908b8e5ab721c4b420edd2210b4a691c343b8aa0fcfd42',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/76C90.s':'45f439d3beb500a34a1ac6a681b270d878681313347b6e095d0fdc6ee517d27e',
    'conker/Makefile':'840897f11d9fea8109c4e67c57e927efa6e1686de2b399fec2c9025828b92d49',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/include/structs.h':'081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/2.0L/PR/sched.h':'40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
    'conker/src/game/generated_B3020.c':'ce0cf9b5504e5b41b267c09d69c3bdc9ed2f24533ed7de0dd68935bd678f467f',
}
SELECTED='''/* Evaluate the four-point cubic route segment at the supplied fraction. */
f32 func_150497E0(f32 *points, s32 index, f32 fraction) {
    f32 half = -0.5f * points[index];
    f32 linear;
    f32 quadratic;
    f32 cubic;
    f32 value;

    cubic = points[index + 3] * 0.5f +
        ((half + 1.5f * points[index + 1]) + -1.5f * points[index + 2]);
    quadratic = points[index + 3] * -0.5f +
        ((points[index] + -2.5f * points[index + 1]) + (points[index + 2] + points[index + 2]));
    linear = points[index + 2] * 0.5f + half;
    value = ((cubic * fraction + quadratic) * fraction + linear) * fraction + points[index + 1];
    return value;
}
'''
raw_read,raw_text=Path.read_bytes,Path.read_text
RAW_SHA='b2d8f9b5410e50f177b8f8b59a4bbcb956473af9d1481f190f95cadc66d72468'
AFTER={
    'conker/build/conker.us.elf':'055db7d5df3a748216eb8cf6b24368f725a9ceda248401800f20de907fd784aa',
    'conker/src/game/generated_76C90.c':'3484c495a255bd206395c84453825482f9e53030eb7aef8edeab667ba78f2ce7',
    'conker/retail_word_patches.us.csv':'af22dc5c79d21f0e0cab24517eae418e3e970d9309176c84fe52d12be0560362',
}


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150497E0() {\n    return 0;\n}':raise ValueError('Unknown cubic spline placeholder')
    result=before[:lo]+body.rstrip()+before[hi:]
    old='/* Non-matching placeholders for the text-only asm slice asm/76C90.s. */'
    if result.count(old)!=1:raise ValueError('Unknown spline owner comment')
    return result.replace(old,'/* Route interpolation; the derivative helper below remains unfinished. */')


def commutative(op,a,b):return (op,*sorted((a,b),key=repr))


def lineage(words):
    """Track exact rounded-expression DAGs; never reassociate floating operations."""
    if len(words)!=49:raise ValueError('Cubic lineage needs the complete 49-word slot')
    r=[('arg',i) for i in range(32)];r[0]=('bits',0);r[29]=('stack',0)
    f=[('fpr',i) for i in range(32)];memory={};events=[];stores=[];loads=[]
    def address(base,offset):
        v=r[base]
        return (v[0],v[1]+offset) if v[0]=='stack' else ('address',v,offset)
    for i,w in enumerate(words):
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=((w&65535)^32768)-32768
        if op==9 and rs==rt==29:
            r[29]=address(29,imm);event=('stack-adjust',imm)
        elif op==43 and rs==29:
            at=address(rs,imm);memory[at]=r[rt];event=('store-word',at,r[rt]);stores.append(event)
        elif op==0 and fn==0 and w:
            r[rd]=('shift',r[rt],sa);event=('shift',r[rt],sa)
        elif op==0 and fn==33:
            r[rd]=commutative('unsigned-add',r[rs],r[rt]);event=r[rd]
        elif op==15:
            r[rt]=('bits',(w&65535)<<16);event=('constant',r[rt])
        elif op==17 and rs==4:
            f[rd]=r[rt];event=('to-fpr',r[rt])
        elif op==49:
            at=address(rs,imm);value=memory.get(at,('load',at));f[rt]=value;event=('read',at,value);loads.append(event)
        elif op==17 and rs==16 and fn in (0,2):
            f[sa]=commutative('add' if fn==0 else 'multiply',f[rd],f[rt]);event=f[sa]
        elif op==17 and rs==16 and fn==6:
            f[sa]=f[rd];event=('move-fpr',f[rd])
        elif op==57 and rs==29:
            at=address(rs,imm);memory[at]=f[rt];event=('store-float',at,f[rt]);stores.append(event)
        elif op==0 and fn==8 and rs==31 and i==47:event=('return',r[rs])
        else:raise ValueError('Unknown cubic lineage word %d:0x%08X'%(i,w))
        events.append(event)
    return dict(events=events,stores=stores,loads=loads,result=f[0],gprs=r,preserved_fprs=f[20:])


def normalization_proof(words,truth):
    a,b=map(lineage,(words,truth));left,right=(Counter(map(repr,x['events'])) for x in (a,b))
    if left!=right or a['stores']!=b['stores'] or any(a[k]!=b[k] for k in ('result','gprs','preserved_fprs')):
        raise ValueError('Cubic transformation changes operation lineage, private stores, result or preserved state')
    for body in (a,b):
        public_reads=[i for i,e in enumerate(body['events']) if e[0]=='read' and e[1][0]!='stack']
        word_stores=[i for i,e in enumerate(body['events']) if e[0]=='store-word']
        float_stores=[i for i,e in enumerate(body['events']) if e[0]=='store-float']
        if len(public_reads)!=4 or len(word_stores)!=1 or len(float_stores)!=2 or \
                word_stores[0]>=min(public_reads) or max(public_reads)>=min(float_stores):
            raise ValueError('Cubic read scheduling crosses a possibly aliased private store')
    positions=defaultdict(list)
    for i,event in enumerate(b['events']):positions[repr(event)].append(i)
    mapping=[positions[repr(event)].pop(0) for event in a['events']]
    if sorted(mapping)!=list(range(49)):raise ValueError('Cubic operation map is not a complete bijection')
    return dict(operation_bijection=mapping,words=49,private_stores=3,rounded_DAG_identical=True,
        public_read_order_identical=a['loads']==b['loads'],no_FP_reassociation=True,
        commutative_NaN_payload_and_FCSR_not_claimed_for_raw=True)


def measure(root,out,label='qualified',body=SELECTED):
    values=freeze(root,out);obj,diagnostics=compile_owner(root,out,
        recovered_owner(values['conker/src/game/generated_76C90.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>49I',values['conker/conker.us.bin'],ROM))
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-49),
        raw_sha256=hashlib.sha256(raw).hexdigest(),bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']})
    row['proof']=normalization_proof(words,truth)
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=196 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings:
        raise ValueError('Unknown cubic spline body or bindings')
    return raw,bindings


def owner_guards(raw,truth):
    words=list(struct.unpack('>49I',raw));normalization_proof(words,truth)
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
        replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
        note='Normalize closed cubic FP register lineage and independent schedule',
        insert_after='',insert_after_relocations='',omit='false') for i,(a,b) in enumerate(zip(words,truth)) if a!=b]


def recovered_guards(before,raw,truth):
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('Preexisting cubic guards')
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks line terminator')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\r\n')
    writer.writerows(owner_guards(raw,truth));return before+out.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out);raw,_=checked_object(obj)
    truth=list(struct.unpack_from('>49I',values['conker/conker.us.bin'],ROM))
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_76C90.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if diagnostics or row['diagnostics'] or row['words']!=49 or row['frame']!=16 or row['differences']!=34 or row['neighbors']!=1 or \
            normalized_pools(before)!=normalized_pools(obj):raise ValueError('Changed cubic owner/shape/pools')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,truth))
    script=out/'qualified-padded.s';script.write_text(emit_padded_assembly(obj,root/'conker/asm/76C90.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=196 or data[f['value']:f['value']+196]!=values['conker/conker.us.bin'][ROM:ROM+196]:
        raise ValueError('Padded cubic spline differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=raw_text(root/'conker/build/conker.ld');old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected cubic linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,196)
    if image[at:at+196]!=values['conker/conker.us.bin'][ROM:ROM+196]:raise ValueError('Cubic prediction slot mismatch')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Cubic prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_76C90.c':recovered_owner(values['conker/src/game/generated_76C90.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first cubic successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=49,
        raw_differences=34,guards=34,frame=16,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:raise ValueError('Changed exact cubic successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(checkpoint,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):yield


def verify(root,out,installed=False):
    with checkpoint_context():return checkpoint.verify(root,out,installed)


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),checkpoint.historical_view(root,out):yield


def audit(root,out):
    verify(root,out,True)
    from tools.match_progress import load_elf_functions
    from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows
    from tools.check_game_data_layout import audit_layout
    before=raw_read(out/'before-01');actual=raw_read(root/'conker/build/conker.us.elf')
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Cubic image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Cubic changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],196,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Cubic changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,_=checked_object(out/'qualified.o');truth=list(struct.unpack_from('>49I',raw_read(root/'conker/conker.us.bin'),ROM))
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,truth):
        raise ValueError('Cubic guards differ from appended rows')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Cubic changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=34,old_guard_prefix_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
