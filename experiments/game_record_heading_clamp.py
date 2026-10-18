"""Recover the record-driven actor heading clamp with its asymmetric limits."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_remaining_donor_candidates import compile_owner as generic_owner,link_owner,function_span
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-record-heading-clamp'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_15087E54',0x15087E54,0xB5304,39
TABLE,PROVIDER=0x800872A0,0x1505A630
INPUTS={
    'conker/src/game/generated_B3020.c':'d39e5d0631120d0259b91164420a9adbbd69afa3b5030570a367d74bb29c16e1',
    'conker/build/conker.us.elf':'23478930a3dea7a22178648e4c9330cb4b09d9271474b01fd9ddd2240826b85a',
    'conker/retail_word_patches.us.csv':'8f709f6c1cb03108c0f1e6f7b460e624d76f29734c97ed5fe9739f411f2046a1',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/B3020.s':'26ef139d5592329ed22f9287267c13fefadf7f17290bc5ef1085cbe20e80b187',
    'conker/Makefile':'840897f11d9fea8109c4e67c57e927efa6e1686de2b399fec2c9025828b92d49',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/include/structs.h':'081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/2.0L/PR/sched.h':'40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
    'conker/src/game_83300.c':'8ab68786c757c4ebcaa85e806adc337649aa67aefc4a7a2d64d7bd67bf1da846',
    'conker/asm/nonmatchings/game_77AD0/func_1504CB98.s':'b4aab7c79ac1b73fdb75439d62477bbc6baa7bcaf3d561fcbf6ada14786cc201',
    'conker/src/game_77AD0.c':'13a6c3e9988e846027f06a092eac6935e65b86043268af16f6678db83ffe01e8',
}
SELECTED='''/* Keep the actor heading within the record's asymmetric wrapped-angle limits. */
void func_15087E54(s32 recordIndex, u8 *actor) {
    extern u16 func_1505A630(f32, f32, s32);
    u8 *table = D_800872A0;
    u8 *record;
    s32 target;
    s32 delta;

    if (table != 0) {
        record = table + recordIndex * 0x84;
        target = (func_1505A630(*(f32 *)(record + 0x10),
                              *(f32 *)(record + 0x0C), 0) + 0x4000) & 0xFFFF;
        delta = (target - *(u16 *)(actor + 0x76)) & 0xFFFF;
        if (delta & 0x8000) {
            if (delta < 0xDBFF) {
                *(u16 *)(actor + 0x76) = target + 0x2400;
            }
        } else {
            if (delta >= 0x2401) {
                *(u16 *)(actor + 0x76) = target - 0x2400;
            }
        }
    }
}
'''
raw_read,raw_text=Path.read_bytes,Path.read_text
INITIAL=SELECTED


def forms():
    yield 'initial',INITIAL
    for kind in ('u8 *','void *','s32 '):
        body=INITIAL.replace('u8 *actor)',kind+'inputActor)').replace(
            '    u8 *table = D_800872A0;',
            '    u8 *actor = (u8 *)inputActor;\n    u8 *table = D_800872A0;')
        yield 'actor-alias-'+kind.split()[0],body
        yield 'actor-alias-last-'+kind.split()[0],body.replace(
            '    u8 *actor = (u8 *)inputActor;\n','').replace(
            '    s32 delta;','    s32 delta;\n    u8 *actor = (u8 *)inputActor;')
    body=INITIAL.replace('    s32 target;\n','').replace('target','recordIndex')
    yield 'reuse-index',body
    yield 'reuse-index-alias',body.replace('u8 *actor)','u8 *inputActor)').replace(
        '    u8 *table = D_800872A0;','    u8 *actor = inputActor;\n    u8 *table = D_800872A0;')
    for target in ('u16','u32','s32'):
        for delta in ('u16','u32','s32'):
            if target==delta=='s32':continue
            body=INITIAL.replace('s32 target;',target+' target;').replace('s32 delta;',delta+' delta;')
            if target=='u16':body=body.replace('0x0C), 0) + 0x4000) & 0xFFFF;', '0x0C), 0) + 0x4000);')
            if delta=='u16':body=body.replace('(target - *(u16 *)(actor + 0x76)) & 0xFFFF;', 'target - *(u16 *)(actor + 0x76);')
            yield 'types-'+target+'-'+delta,body


SELECTED=dict(forms())['types-u16-u16']
RAW_SHA='a304c18e4118445cedd0dde67af888f0f0744ea2d151d690dbc0813cb087b7ae'
AFTER={
    'conker/build/conker.us.elf':'6f4bfb1be74457784dde6ad0f497d131956d7b110017c92357b0ad43a9cc0b7c',
    'conker/src/game/generated_B3020.c':'576b4ce003c0b1a625864fbd2d5f1313e048593bcd4e972221ed59bc18a0d5f3',
}


def compile_owner(root,out,source,name):
    run=subprocess.run
    invocations=[]
    def profile(argv,**kwargs):
        if argv[0]==str(root/'ido/ido5.3_recomp/cc'):
            argv=list(argv)
            argv.insert(argv.index('-mips2'),'-Wo,-loopunroll,0')
            invocations.append(argv)
        return run(argv,**kwargs)
    # Only the compiler receives this CFLAGS option, not GLOBAL_ASM preprocessing.
    with patch.object(subprocess,'run',side_effect=profile):
        result=generic_owner(root,out,source,name)
    if len(invocations)!=1:raise ValueError('Expected one B3020 owner compiler invocation')
    return result


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15087E54() {\n    return 0;\n}':
        raise ValueError('Unknown heading clamp placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='selected',body=None):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>39I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={12:[('R_MIPS_HI16','D_800872A0')],16:[('R_MIPS_LO16','D_800872A0')],
        52:[('R_MIPS_26','func_1505A630')]}
    if len(raw)!=156 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown heading clamp body or three bindings')
    return raw,bindings


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences'] or row['frame']!=24 or \
            normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed heading clamp diagnostics/shape/pools')
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',filename=OWNER,
        word_patches_path=root/'conker/retail_word_patches.us.csv'))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=156 or data[f['value']:f['value']+156]!=values['conker/conker.us.bin'][ROM:ROM+156]:
        raise ValueError('Padded heading clamp differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected heading clamp linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,156)
    if image[at:at+156]!=values['conker/conker.us.bin'][ROM:ROM+156]:
        raise ValueError('Complete heading clamp prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Heading clamp prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode()}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first heading clamp successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=39,
        raw_differences=0,guards=0,frame=24,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact heading clamp successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Heading clamp image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Heading clamp installation changes other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],156,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Heading clamp changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    for p in ('conker/retail_word_patches.us.csv','conker/Makefile'):
        if hashlib.sha256(raw_read(root/p)).hexdigest()!=INPUTS[p]:raise ValueError('Heading clamp changed guards/build')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Heading clamp changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),guards_and_makefile_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true');parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            row=measure(root,root/BUILD,name,body)[2]
            print(json.dumps(dict(name=name,words=row['words'],differences=row['differences'],sha=row['raw_sha256'])),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
