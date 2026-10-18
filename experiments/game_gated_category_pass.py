"""Recover the exact-one category gate and ordered live-count callback pass."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_grouped_actor_dispatch_candidates import compile_owner
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-gated-category-pass'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_49D30','func_15022848',0x15022848,0x4FCF8,39
GATE,COUNT,CONTEXT,FIRST,SECOND=0x800C35EA,0x800C363A,0x800C3638,0x15022398,0x150222E0
INPUTS={
    'conker/src/game/generated_49D30.c':'62d13a9969d88b5ecb7fbeddc96183d998ecc9cb9a881b43c527021591fec6c0',
    'conker/build/conker.us.elf':'db45bf1c6025f9a265e35df1671986996d3e81230b2879d3187c890f3aeb30a1',
    'conker/retail_word_patches.us.csv':'625033dd1c2150ce2edb45badf13c05d09aa95b83a0c2b1231e092105d3fc2b3',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/49D30.s':'745b8aaa3c4871d74f21c6cf2479a494cb5e01bcb2df1486c8dbc56004c3ae41',
    'conker/Makefile':'840897f11d9fea8109c4e67c57e927efa6e1686de2b399fec2c9025828b92d49',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/include/structs.h':'081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/2.0L/PR/sched.h':'40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
}
SELECTED='''/* Run both callbacks per active entry, reloading the count after each pair. */
void func_15022848(s32 index) {
    s32 i;
    u8 *count;

    if (D_800C35EA[index] == 1) {
        D_800C3638 = 0;
        count = &D_800C363A[index];
        for (i = 0; i < *count; i++) {
            func_15022398(i, index);
            func_150222E0(i, index);
        }
        D_800C3638 = 1;
    }
}
'''
raw_read,raw_text=Path.read_bytes,Path.read_text
AFTER={
    'conker/build/conker.us.elf':'6f9f3636ee46917e8815196a03dfa8a3755e7cfd4763f64dc2b074d21013c3a6',
    'conker/src/game/generated_49D30.c':'e0376d1609bcde42ce5b340453f9fbfcce6022a230b9016a0944f4044f23e187',
}
RAW_SHA='644f3b919ab4d6d5b1b29aee2da07514107c6b385cd49511a7cf434d020e2243'


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15022848() {\n    return 0;\n}' or before.count('s32 func_15022848();')!=1:
        raise ValueError('Unknown gated category placeholder/prototype')
    return (before[:lo]+body.rstrip()+before[hi:]).replace('s32 func_15022848();','void func_15022848(s32 index);',1)


def measure(root,out,label='selected',body=None):
    if body is None:body=SELECTED
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_49D30.c'].decode(),body),label)
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
    expected={24:[('R_MIPS_HI16','D_800C35EA')],32:[('R_MIPS_LO16','D_800C35EA')],
        40:[('R_MIPS_HI16','D_800C363A')],48:[('R_MIPS_LO16','D_800C363A')],
        52:[('R_MIPS_HI16','D_800C3638')],56:[('R_MIPS_LO16','D_800C3638')],
        80:[('R_MIPS_26','func_15022398')],92:[('R_MIPS_26','func_150222E0')],
        124:[('R_MIPS_HI16','D_800C3638')],128:[('R_MIPS_LO16','D_800C3638')]}
    if len(raw)!=156 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown gated category body or ten bindings')
    return raw,bindings


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_49D30.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences'] or row['frame']!=40 or \
            normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed category diagnostics/shape/pools')
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/49D30.s',filename=OWNER,
        word_patches_path=root/'conker/retail_word_patches.us.csv'))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=156 or data[f['value']:f['value']+156]!=values['conker/conker.us.bin'][ROM:ROM+156]:
        raise ValueError('Padded category pass differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected category linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,156)
    if image[at:at+156]!=values['conker/conker.us.bin'][ROM:ROM+156]:
        raise ValueError('Complete category prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Category prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_49D30.c':recovered_owner(values['conker/src/game/generated_49D30.c'].decode()).encode()}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first category successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=39,
        raw_differences=0,guards=0,frame=40,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner')) for p in AFTER}
    if {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact category successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Category image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Category installation changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],156,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Category changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    for p in ('conker/retail_word_patches.us.csv','conker/Makefile'):
        if hashlib.sha256(raw_read(root/p)).hexdigest()!=INPUTS[p]:raise ValueError('Category changed guards/build')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Category changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),guards_and_makefile_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
