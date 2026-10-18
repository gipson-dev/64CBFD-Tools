"""Recover cubic value and derivative with a separate 62-word lineage proof."""
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

from tools.experiments import game_route_cubic_spline as cubic
from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-route-spline-derivative'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_76C90','func_150498A4',0x150498A4,0x76D54,62
INPUTS=dict(cubic.INPUTS,**cubic.AFTER)
SELECTED='''/* Evaluate a cubic route segment and publish its derivative. */
f32 func_150498A4(f32 *points, s32 index, f32 fraction, f32 *slope) {
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
    *slope = (cubic * 3.0f * fraction + (quadratic + quadratic)) * fraction + linear;
    return value;
}
'''
raw_read,raw_text=Path.read_bytes,Path.read_text
RAW_SHA='95dc59ef79203db705b8f261e6497fd8ab8402edb6bf62b977044e339b3faea0'
AFTER={
    'conker/build/conker.us.elf':'fc9f2b74bd97121aa678270092047b76914852ea483a10c1bc35a32b504c021b',
    'conker/src/game/generated_76C90.c':'8e9c9885e7772fbd356120a036307a2ba8202d04fc72de82a3027dba7f750dde',
    'conker/retail_word_patches.us.csv':'65de253d70fd8071c62dd8c1f87dbe89107c2713dbb3d30ae3a728d5b9a6447f',
}


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150498A4() {\n    return 0;\n}':raise ValueError('Unknown derivative placeholder')
    text=before[:lo]+body.rstrip()+before[hi:]
    old='/* Route interpolation; the derivative helper below remains unfinished. */'
    if text.count(old)!=1:raise ValueError('Unknown partial spline owner comment')
    return text.replace(old,'/* Cubic route interpolation and derivative helpers. */')


def lineage(words):
    """Model rounded FP nodes and identity routing without weakening the cubic proof."""
    if len(words)!=62:raise ValueError('Derivative lineage requires all 62 words')
    r=[('arg',i) for i in range(32)];r[0]=('bits',0);r[29]=('stack',0)
    f=[('fpr',i) for i in range(32)];memory={};events=[];stores=[];loads=[];identity=[]
    def address(base,offset):
        v=r[base]
        return (v[0],v[1]+offset) if v[0]=='stack' else ('address',v,offset)
    for i,w in enumerate(words):
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=((w&65535)^32768)-32768
        if op==9 and rs==rt==29:
            r[29]=address(29,imm);event=('stack-adjust',imm)
        elif op==61 and rs==29 and rt==20:
            at=address(rs,imm);low=(at[0],at[1]+4)
            memory[at],memory[low]=f[21],f[20]
            event=('save-pair',at,(f[21],f[20]));stores.append(event)
        elif op==53 and rs==29 and rt==20:
            at=address(rs,imm);low=(at[0],at[1]+4)
            f[21],f[20]=memory.get(at,('load',at)),memory.get(low,('load',low))
            event=('restore-pair',at,(f[21],f[20]));loads.append(event)
        elif op==0 and fn==0 and w:
            r[rd]=('shift',r[rt],sa);event=('shift',r[rt],sa)
        elif op==0 and fn==33:
            r[rd]=cubic.commutative('unsigned-add',r[rs],r[rt]);event=r[rd]
        elif op==15:
            r[rt]=('bits',(w&65535)<<16);event=('constant',r[rt])
        elif op==17 and rs==4:
            f[rd]=r[rt];event=('to-fpr',r[rt])
        elif op==49:
            at=address(rs,imm);value=memory.get(at,('load',at));f[rt]=value;event=('read',at,value);loads.append(event)
        elif op==17 and rs==16 and fn in (0,2):
            f[sa]=cubic.commutative('add' if fn==0 else 'multiply',f[rd],f[rt]);event=f[sa]
        elif op==17 and rs==16 and fn==6:
            f[sa]=f[rd];event=('identity',);identity.append((i,'copy',sa,rd))
        elif w==0:
            event=('identity',);identity.append((i,'nop'))
        elif op==57 and rs in (7,29):
            at=address(rs,imm);memory[at]=f[rt];event=('store-float',at,f[rt]);stores.append(event)
        elif op==0 and fn==8 and rs==31 and i==60:event=('return',r[rs])
        else:raise ValueError('Unknown derivative lineage word %d:0x%08X'%(i,w))
        events.append(event)
    return dict(events=events,stores=stores,loads=loads,result=f[0],gprs=r,preserved_fprs=f[20:],identity=identity)


def normalization_proof(words,truth):
    a,b=map(lineage,(words,truth));left,right=(Counter(map(repr,x['events'])) for x in (a,b))
    if left!=right or a['stores']!=b['stores'] or any(a[k]!=b[k] for k in ('result','gprs','preserved_fprs')):
        raise ValueError('Derivative changes rounded lineage, ordered stores, return or preserved registers')
    for body in (a,b):
        e=body['events'];save=[i for i,x in enumerate(e) if x[0]=='save-pair'];restore=[i for i,x in enumerate(e) if x[0]=='restore-pair']
        reads=[i for i,x in enumerate(e) if x[0]=='read' and x[1][0]!='stack']
        private=[i for i,x in enumerate(e) if x[0]=='store-float' and x[1][0]=='stack']
        public=[i for i,x in enumerate(e) if x[0]=='store-float' and x[1][0]!='stack']
        if len(save)!=1 or len(restore)!=1 or len(reads)!=4 or len(private)!=2 or len(public)!=1 or \
                not save[0]<min(reads)<=max(reads)<min(private)<=max(private)<public[0]<restore[0]:
            raise ValueError('Derivative scheduling crosses a potentially aliased save/read/store/restore boundary')
        if len(body['identity'])!=4:raise ValueError('Unknown derivative copy/NOP budget')
    positions=defaultdict(list)
    for i,event in enumerate(b['events']):positions[repr(event)].append(i)
    mapping=[positions[repr(event)].pop(0) for event in a['events']]
    if sorted(mapping)!=list(range(62)):raise ValueError('Derivative instruction lineage map is not bijective')
    return dict(words=62,operation_bijection=mapping,identities_raw=a['identity'],identities_retail=b['identity'],
        same_rounded_return_and_derivative=True,ordered_private_and_public_stores=True,
        no_FP_reassociation=True,alias_ordering_gate=True,raw_NaN_payload_FCSR_and_fault_register_state_not_claimed=True)


def measure(root,out,label='qualified',body=SELECTED):
    values=freeze(root,out);obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_76C90.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>62I',values['conker/conker.us.bin'],ROM))
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-62),raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']})
    row['proof']=normalization_proof(words,truth)
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=248 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings:
        raise ValueError('Unknown derivative body or bindings')
    return raw,bindings


def owner_guards(raw,truth):
    words=list(struct.unpack('>62I',raw));normalization_proof(words,truth)
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
        replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
        note='Normalize closed derivative FP lineage, identity routing and independent schedule',
        insert_after='',insert_after_relocations='',omit='false') for i,(a,b) in enumerate(zip(words,truth)) if a!=b]


def recovered_guards(before,raw,truth):
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('Preexisting derivative guards')
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks line terminator')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\r\n')
    writer.writerows(owner_guards(raw,truth));return before+out.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out);raw,_=checked_object(obj)
    truth=list(struct.unpack_from('>62I',values['conker/conker.us.bin'],ROM))
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_76C90.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if diagnostics or row['diagnostics'] or row['words']!=62 or row['frame']!=32 or row['differences']!=45 or row['neighbors']!=1 or \
            normalized_pools(before)!=normalized_pools(obj):raise ValueError('Changed derivative owner/shape/pools')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,truth))
    script=out/'qualified-padded.s';script.write_text(emit_padded_assembly(obj,root/'conker/asm/76C90.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=248 or data[f['value']:f['value']+248]!=values['conker/conker.us.bin'][ROM:ROM+248]:
        raise ValueError('Padded derivative differs from retail')
    f=functions[cubic.FUNCTION]
    if data[f['value']:f['value']+196]!=values['conker/conker.us.bin'][cubic.ROM:cubic.ROM+196]:
        raise ValueError('Derivative qualification changed matched cubic neighbor')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=raw_text(root/'conker/build/conker.ld');old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected derivative linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,248)
    if image[at:at+248]!=values['conker/conker.us.bin'][ROM:ROM+248]:raise ValueError('Derivative prediction slot mismatch')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Derivative prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_76C90.c':recovered_owner(values['conker/src/game/generated_76C90.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first derivative successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=62,
        raw_differences=45,guards=45,frame=32,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:raise ValueError('Changed exact derivative successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Derivative image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Derivative changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],248,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Derivative changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,_=checked_object(out/'qualified.o');truth=list(struct.unpack_from('>62I',raw_read(root/'conker/conker.us.bin'),ROM))
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,truth):
        raise ValueError('Derivative guards differ from appended rows')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Derivative changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=45,old_guard_prefix_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
