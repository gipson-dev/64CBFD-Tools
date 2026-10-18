"""Recover the mode-dependent record heading setter without unordered rewrites."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_record_heading_clamp import compile_owner
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-record-heading-setter'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_15087EF0',0x15087EF0,0xB53A0,53
TABLE,MODE,PROVIDER=0x800872A0,0x800D23A8,0x1505A630
INPUTS={
    'conker/src/game/generated_B3020.c':'576b4ce003c0b1a625864fbd2d5f1313e048593bcd4e972221ed59bc18a0d5f3',
    'conker/build/conker.us.elf':'6f4bfb1be74457784dde6ad0f497d131956d7b110017c92357b0ad43a9cc0b7c',
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
    'conker/asm/nonmatchings/game_77AD0/func_15051558.s':'3a8ce50a9047b92b90c212f4307834c7231cc200c508b6c529e8ed1159284acd',
    'conker/src/game_77AD0.c':'13a6c3e9988e846027f06a092eac6935e65b86043268af16f6678db83ffe01e8',
}
SELECTED='''/* Select a wrapped heading offset from the live mode and record speed. */
void func_15087EF0(s32 recordIndex, u8 *actor) {
    extern u16 func_1505A630(f32, f32, s32);
    extern s8 D_800D23A8;
    u8 *table = D_800872A0;
    u8 *record;
    u16 angle;
    u16 heading;

    if (table != 0) {
        record = table + recordIndex * 0x84;
        angle = func_1505A630(*(f32 *)(record + 0x10), *(f32 *)(record + 0x0C), 0);
        if (D_800D23A8 == 0) {
            heading = angle + 0x3600;
            if (*(f32 *)record < 0.5f) {
                heading = angle + 0x4A00;
            }
        } else {
            heading = angle + 0x3600;
            if (*(f32 *)record >= 0.5f) {
                heading = angle + 0x4A00;
            }
        }
        *(u16 *)(actor + 0x76) = heading;
    }
}
'''
INITIAL=SELECTED
raw_read,raw_text=Path.read_bytes,Path.read_text


def forms():
    yield 'initial',INITIAL
    explicit=INITIAL.replace('''            heading = angle + 0x3600;
            if (*(f32 *)record < 0.5f) {
                heading = angle + 0x4A00;
            }''','''            if (*(f32 *)record < 0.5f) {
                heading = angle + 0x4A00;
            } else {
                heading = angle + 0x3600;
            }''').replace('''            heading = angle + 0x3600;
            if (*(f32 *)record >= 0.5f) {
                heading = angle + 0x4A00;
            }''','''            if (*(f32 *)record >= 0.5f) {
                heading = angle + 0x4A00;
            } else {
                heading = angle + 0x3600;
            }''')
    ternary=explicit.replace('''            if (*(f32 *)record < 0.5f) {
                heading = angle + 0x4A00;
            } else {
                heading = angle + 0x3600;
            }''','''            heading = *(f32 *)record < 0.5f ? (u16)(angle + 0x4A00) : (u16)(angle + 0x3600);''').replace(
            '''            if (*(f32 *)record >= 0.5f) {
                heading = angle + 0x4A00;
            } else {
                heading = angle + 0x3600;
            }''','''            heading = *(f32 *)record >= 0.5f ? (u16)(angle + 0x4A00) : (u16)(angle + 0x3600);''')
    for name,body in (('explicit',explicit),('ternary',ternary)):
        yield name,body
        yield name+'-wide-angle',body.replace('    u16 angle;','    s32 angle;')
        yield name+'-wide-heading',body.replace('    u16 heading;','    s32 heading;').replace(
            'heading = angle + 0x4A00;','heading = (u16)(angle + 0x4A00);').replace(
            'heading = angle + 0x3600;','heading = (u16)(angle + 0x3600);')
    one=explicit.replace('    u8 *table = D_800872A0;\n    u8 *record;',
        '    u8 *record = D_800872A0;').replace('if (table != 0)','if (record != 0)').replace(
        'record = table + recordIndex * 0x84;','record += recordIndex * 0x84;')
    yield 'record-only',one
    yield 'record-only-last',one.replace('    u8 *record = D_800872A0;\n','').replace(
        '    u16 heading;','    u16 heading;\n    u8 *record = D_800872A0;')
    yield 'record-only-wide-angle',one.replace('    u16 angle;','    s32 angle;')
    yield 'record-only-reverse-angles',one.replace('    u16 angle;\n    u16 heading;',
        '    u16 heading;\n    u16 angle;')
    yield 'record-last',explicit.replace('    u8 *record;\n','').replace(
        '    u16 heading;','    u16 heading;\n    u8 *record;')
    yield 'word-record-index',explicit.replace('    u8 *record;\n','').replace(
        'record = table + recordIndex * 0x84;','recordIndex = (s32)table + recordIndex * 0x84;').replace(
        '(record + 0x10)','(recordIndex + 0x10)').replace('(record + 0x0C)','(recordIndex + 0x0C)').replace(
        '*(f32 *)record','*(f32 *)recordIndex')
    yield 'index-angle',explicit.replace('    u16 angle;\n','').replace('angle','recordIndex')
    yield 'index-angle-wide-heading',explicit.replace('    u16 angle;\n','').replace('angle','recordIndex').replace(
        '    u16 heading;','    s32 heading;').replace('heading = recordIndex + 0x4A00;',
        'heading = (u16)(recordIndex + 0x4A00);').replace('heading = recordIndex + 0x3600;',
        'heading = (u16)(recordIndex + 0x3600);')
    for name,expression in (
            ('integer-first','record = (u8 *)(recordIndex * 0x84 + (s32)record);'),
            ('integer-last','record = (u8 *)((s32)record + recordIndex * 0x84);'),
            ('array-record','record = (u8 *)((u8 (*)[0x84])record + recordIndex);')):
        yield name,one.replace('record += recordIndex * 0x84;',expression)
    yield 'shared-angle',explicit.replace('    u16 angle;\n','').replace('angle','heading')
    direct=explicit.replace('    u8 *table = D_800872A0;\n','').replace(
        'if (table != 0)','if (D_800872A0 != 0)').replace('record = table + recordIndex * 0x84;',
        'record = D_800872A0 + recordIndex * 0x84;')
    yield 'direct-table',direct
    yield 'direct-table-wide-angle',direct.replace('    u16 angle;','    s32 angle;')
    yield 'direct-table-record-last',direct.replace('    u8 *record;\n','').replace(
        '    u16 heading;','    u16 heading;\n    u8 *record;')


SELECTED=dict(forms())['direct-table']
RAW_SHA='00ecca182903df384b4ff5d0a6b25210dfbd2208d4ce0d9f7ce10add963c25d9'
AFTER={
    'conker/build/conker.us.elf':'c1e56f1d074a85813ef0e6cedd22b1d41f109ec0f60abdf43cd80914f7ec6407',
    'conker/src/game/generated_B3020.c':'b087b1069a1e0db0629bffd448962a2c726a56b07099f1cc0735e3d5fcdfc0be',
}


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15087EF0() {\n    return 0;\n}':
        raise ValueError('Unknown heading setter placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='selected',body=None):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>53I',values['conker/conker.us.bin'],ROM)
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
        52:[('R_MIPS_26','func_1505A630')],60:[('R_MIPS_HI16','D_800D23A8')],
        64:[('R_MIPS_LO16','D_800D23A8')]}
    if len(raw)!=212 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown heading setter body or five bindings')
    return raw,bindings


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences'] or row['frame']!=32 or \
            normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed heading setter diagnostics/shape/pools')
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',filename=OWNER,
        word_patches_path=root/'conker/retail_word_patches.us.csv'))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=212 or data[f['value']:f['value']+212]!=values['conker/conker.us.bin'][ROM:ROM+212]:
        raise ValueError('Padded heading setter differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected heading setter linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,212)
    if image[at:at+212]!=values['conker/conker.us.bin'][ROM:ROM+212]:
        raise ValueError('Complete heading setter prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Heading setter prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode()}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first heading setter successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=53,
        raw_differences=0,guards=0,frame=32,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact heading setter successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Heading setter image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Heading setter installation changes other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],212,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Heading setter changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    for p in ('conker/retail_word_patches.us.csv','conker/Makefile'):
        if hashlib.sha256(raw_read(root/p)).hexdigest()!=INPUTS[p]:raise ValueError('Heading setter changed guards/build')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Heading setter changed protected Game data')
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
            print(json.dumps(dict(name=name,words=row['words'],frame=row['frame'],differences=row['differences'],sha=row['raw_sha256'])),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
