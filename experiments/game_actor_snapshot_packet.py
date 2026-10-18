"""Recover the actor snapshot packet while retaining inherited stack padding."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-actor-snapshot-packet'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_1D6E80','func_151AB930',0x151AB930,0x1D8DE0,38
PROVIDER,ALLOCATOR,MEMCPY,COEFFICIENT=0x151D8E20,0x151491F4,0x10022EC0,0x800A9014
INPUTS={
    'conker/src/game/generated_1D6E80.c':'14a92d97a80f5effa6122c8b7346f2eabd2e30452fc6e3a79b2b3ea688e414a1',
    'conker/build/conker.us.elf':'d6f9ef39a264d51413b532ae5a4b587400864b346d0cbab1b9e066eaf09c327b',
    'conker/retail_word_patches.us.csv':'625033dd1c2150ce2edb45badf13c05d09aa95b83a0c2b1231e092105d3fc2b3',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/1D6E80.s':'3d203700398c8864a2ec721620c6f412c6b1204ebeb13a955b464476defde90e',
    'conker/Makefile':'840897f11d9fea8109c4e67c57e927efa6e1686de2b399fec2c9025828b92d49',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/src/game_981E0.c':'e83baa9f46721ba0cdfae136976b6f4d36c1945b75a33998d212250dc7e2b9bb',
    'conker/src/game_2062D0.c':'f0e096816c0414498b58bc39260a553c196898eb06f04ea106d0317d6a6df1a4',
    'conker/src/game/done/game_1765E0.c':'19dd4f8a4e0561ad2de70ee59e12e50c11a9938357816dd0eacb2334d8c0c5af',
    'conker/asm/data/24DA30.rodata.s':'dc49fcae2f50b6de8d04b6f8f75fd63a90e80b118418e238a4eb218c8f3e26fc',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
    'conker/retail_layout.us.txt':'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5',
    'conker/build/src/game_981E0.c.o':'b4afd346661f95805348f9e1f28bf6b3bab6e43a11a68ce71020732da49767a2',
    'conker/include/functions.h':'2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81',
    'conker/include/structs.h':'081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/variables.h':'1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8',
}
SELECTED='''/* Snapshot actor fields, then copy the packet if allocation succeeds. */
void func_151AB930(u8 *actor) {
    extern f32 D_800A9014;
    extern u8 func_151D8E20(void);
    extern void *func_151491F4(s16, s8, s8, u8, u8, s32, u8, s32);
    extern void *memcpy(void *, const void *, u32);
    struct {
        u8 *actor;
        u8 slot;
        u32 value;
        f32 time, scale, lifetime;
        u8 selector;
    } packet;
    u8 *created;

    packet.actor = actor;
    packet.slot = actor[0x3B];
    packet.value = *(u16 *)(actor + 0x84);
    packet.time = 0.0f;
    packet.scale = D_800A9014;
    packet.lifetime = 3.0f;
    packet.selector = func_151D8E20();
    created = func_151491F4(0x3C, -1, 0xE, 1, 9, 0x1C, 0xFF, 0);
    if (created != NULL) {
        memcpy(created + 0x28, &packet, 0x1C);
    }
}
'''
INITIAL=SELECTED
raw_read,raw_text=Path.read_bytes,Path.read_text
AFTER={
    'conker/build/conker.us.elf':'db45bf1c6025f9a265e35df1671986996d3e81230b2879d3187c890f3aeb30a1',
    'conker/src/game/generated_1D6E80.c':'e6f4d1e63adc28a0a76e8e223fe26bc8ee47e160a7d0a99388129eba2006e9d0',
    'conker/src/game_981E0.c':'07c26340d73cc90060d92e03c870b270e1f10141a9e02759f5a8e8f495ed6b45',
}
RAW_SHA='fa3aed733b58109f80a3c4f3ba95c91a90381f4d6a2a550ddfffb0fa2de99fe4'


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_151AB930() {\n    return 0;\n}':
        raise ValueError('Unknown actor snapshot placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='selected',body=None):
    if body is None:body=SELECTED
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,
        recovered_owner(values['conker/src/game/generated_1D6E80.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>38I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def forms():
    yield 'initial',INITIAL
    yield 'destination-first',INITIAL.replace('    u8 *created;\n','').replace(
        '    struct {','    u8 *created;\n    struct {',1)


SELECTED=dict(forms())['destination-first']


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={16:[('R_MIPS_HI16','D_800A9014')],20:[('R_MIPS_LO16','D_800A9014')],
        56:[('R_MIPS_26','func_151D8E20')],108:[('R_MIPS_26','func_151491F4')],
        128:[('R_MIPS_26','memcpy')]}
    if len(raw)!=152 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown snapshot packet body or five bindings')
    return raw,bindings


def recovered_caller(before):
    marker='void func_15131D4C(s32 *arg0, s32 arg1);'
    call='    func_151AB930(D_800D154C);'
    if before.count(marker)!=1 or before.count(call)!=1 or 'void func_151AB930(' in before:
        raise ValueError('Unknown snapshot caller declaration/body')
    return before.replace(marker,'void func_151AB930(u8 *actor);\n'+marker,1).replace(
        call,'    func_151AB930((u8 *)D_800D154C);',1)


def qualify_caller(root,out,values):
    before=values['conker/src/game_981E0.c'].decode();after=recovered_caller(before)
    a,da=compile_owner(root,out,before,'caller-before')
    b,db=compile_owner(root,out,after,'caller-after')
    line=before[:before.index('void func_15131D4C(')].count('\n')+1
    db=re.sub(r'line (\d+)',lambda m:'line '+str(int(m[1])-(int(m[1])>=line+1)),
        db.replace('caller-after.c','caller.c'))
    if da.replace('caller-before.c','caller.c')!=db or normalized_pools(a)!=normalized_pools(b):
        raise ValueError('Changed caller diagnostics/pools beyond inserted prototype line')
    count=same_functions(a,b)
    script=out/'caller-padded.s'
    script.write_text(pad_c_object.emit_padded_assembly(b,root/'conker/retail_layout.us.txt',
        'game_981E0',word_patches_path=root/'conker/retail_word_patches.us.csv'))
    obj=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(script)],check=True,capture_output=True)
    if obj.read_bytes()!=values['conker/build/src/game_981E0.c.o']:
        raise ValueError('Typed caller changes complete production object')
    return dict(functions=count,whole_object_identical=True,diagnostics=da)


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_1D6E80.c'].decode(),'owner-before')
    neighbors=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences'] or row['frame']!=72 or \
            normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed packet diagnostics/shape/pools')
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/1D6E80.s',filename=OWNER,
        word_patches_path=root/'conker/retail_word_patches.us.csv'))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=152 or data[f['value']:f['value']+152]!=values['conker/conker.us.bin'][ROM:ROM+152]:
        raise ValueError('Padded snapshot packet differs from retail')
    row['neighbors']=neighbors
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    caller=qualify_caller(root,out,values)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected snapshot owner linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,152)
    if image[at:at+152]!=values['conker/conker.us.bin'][ROM:ROM+152]:
        raise ValueError('Complete snapshot prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Snapshot prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_1D6E80.c':recovered_owner(values['conker/src/game/generated_1D6E80.c'].decode()).encode(),
        'conker/src/game_981E0.c':recovered_caller(values['conker/src/game_981E0.c'].decode()).encode()}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else
            'after-caller' if p.endswith('game_981E0.c') else 'after-owner' if p.endswith('.c') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first snapshot successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=38,
        raw_differences=0,guards=0,frame=72,functions=len(a),neighbors=row['neighbors'],bytes=len(image),caller=caller)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else
        'after-caller' if p.endswith('game_981E0.c') else 'after-owner')) for p in AFTER}
    if {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact snapshot successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Actual snapshot differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Snapshot installation changed other functions/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],152,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Snapshot changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    if raw_read(root/'conker/build/src/game_981E0.c.o')!=raw_read(out/'caller-padded.o'):
        raise ValueError('Installed typed caller changes complete object')
    for p in ('conker/retail_word_patches.us.csv','conker/Makefile','conker/asm/data/24DA30.rodata.s'):
        if hashlib.sha256(raw_read(root/p)).hexdigest()!=INPUTS[p]:raise ValueError('Snapshot changed guards/build/data source')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Snapshot changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),guards_and_makefile_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true')
    parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            print(json.dumps(dict(name=name,**measure(root,root/BUILD,name,body)[2])),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
