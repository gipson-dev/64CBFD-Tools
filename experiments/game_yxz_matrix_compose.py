"""Recover the ordered Y/X/Z matrix constructor with its existing float ABI."""
import argparse
from contextlib import contextmanager
import hashlib
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

BUILD='conker/build/game-yxz-matrix-compose'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_13D350','func_151102CC',0x151102CC,0x13D77C,37
ROTATE,PRODUCT,WRAPPER=0x150A8050,0x150A7A48,0x15110360
INPUTS={
    'conker/src/game/generated_13D350.c':'68d7d45a9b71049426ee12b4af3af36c7c7d455fb42bac2979e857eacc71fd89',
    'conker/build/conker.us.elf':'9f79786e248e2384422e8237865a30273a7ae17f1d3690cc9a4c87f1d46543c4',
    'conker/retail_word_patches.us.csv':'625033dd1c2150ce2edb45badf13c05d09aa95b83a0c2b1231e092105d3fc2b3',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/13D350.s':'aae655875cae186bc7377f14463dc61e80cb55f511b1931a0ed03d1308333a2c',
    'conker/Makefile':'a6e92d90cdeb8c65e7d1ff57f6603ea4f0e5bee6c09d5a028a51a1e0e369bfd6',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/src/game_D5500.c':'6cf42acdb32617b934d526cabc47e3e5e58eb3352b5175dd19ff4b6c4ffa071d',
    'conker/src/game/generated_D4E10.c':'68fb4b7b0106aa77100dfdbc354871c48b4944462d657e61122168d5b6496f38',
    'conker/src/game/generated_DAC30.c':'e831af23ec9a00c80f5500d0d23f3c525140ca1a965fe98332b09085c28d82ee',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
}
SELECTED='''/* Compose separate Y, X and Z rotations using one temporary matrix. */
void func_151102CC(f32 matrix[4][4], f32 x, f32 y, f32 z) {
    f32 temporary[4][4];

    func_150A8050(matrix, 0.0f, y, 0.0f);
    func_150A8050(temporary, x, 0.0f, 0.0f);
    func_150A7A48(matrix, temporary, matrix);
    func_150A8050(temporary, 0.0f, 0.0f, z);
    func_150A7A48(matrix, temporary, matrix);
}
'''
raw_read,raw_text=Path.read_bytes,Path.read_text
AFTER={
    'conker/build/conker.us.elf':'2d972c777f17469fec9c85c80f7ed5951bee4cc9e5b5c4c87706de2b4752a0b1',
    'conker/src/game/generated_13D350.c':'750c682e2aac536d6a48f9b403e4b50d3cd65482c519b2658ea54d7a7bf1f05f',
}
RAW_SHA='1b696790f7ad55b68eb9bf1dd953d32614a8a717192d3283ad8150f13396a190'


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='void func_151102CC(f32 arg0[4][4], f32 arg1, f32 arg2, f32 arg3) {\n}':
        raise ValueError('Unknown matrix constructor placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='selected',body=SELECTED):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,
        recovered_owner(values['conker/src/game/generated_13D350.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>37I',values['conker/conker.us.bin'],ROM)
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
    expected={i:[('R_MIPS_26','func_150A8050')] for i in (48,68,104)}
    expected.update({i:[('R_MIPS_26','func_150A7A48')] for i in (84,120)})
    if len(raw)!=148 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown matrix body or five call bindings')
    return raw,bindings


def qualify(root,out):
    values=freeze(root,out)
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_13D350.c'].decode(),'owner-before')
    if row['diagnostics'] or diagnostics or row['differences'] or row['frame']!=104 or \
            same_functions(before,obj,(FUNCTION,))!=33 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed matrix diagnostics/shape/neighbors/pools')
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/13D350.s',filename=OWNER,
        word_patches_path=root/'conker/retail_word_patches.us.csv'))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=148 or data[f['value']:f['value']+148]!=values['conker/conker.us.bin'][ROM:ROM+148]:
        raise ValueError('Padded matrix constructor is not retail exact')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out)
    obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text()
    old='build/src/game/'+OWNER+'.c.o'
    if old not in script:raise ValueError('Missing matrix owner linker input')
    ld=out/'predicted.ld'
    ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'first-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,148)
    if image[at:at+148]!=values['conker/conker.us.bin'][ROM:ROM+148]:
        raise ValueError('Complete matrix prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Matrix prediction changes other bodies/addresses')
    values={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_13D350.c':recovered_owner(values['conker/src/game/generated_13D350.c'].decode()).encode()}
    for p,data in values.items():
        path=out/('after-elf' if p.endswith('.elf') else 'after-owner')
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first matrix successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in values.items()},words=37,frame=104,
        raw_differences=0,guards=0,functions=len(a),neighbors=33)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner')) for p in AFTER}
    if {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact matrix successor')
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
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Matrix installation changed other functions/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1
    old[(FUNCTION,fields[1],148,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Matrix changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    if hashlib.sha256(raw_read(root/'conker/retail_word_patches.us.csv')).hexdigest()!=INPUTS['conker/retail_word_patches.us.csv']:
        raise ValueError('Direct matrix match changed guards')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Matrix changed protected Game data')
    result=dict(functions=len(a),neighbors=33,only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),guards_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
