"""Recover the live-base/count record flag refresh as a void procedure."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_yxz_matrix_compose as previous
from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.pad_generated_object import parse_object,emit_padded_assembly

BUILD='conker/build/game-record-flag-refresh'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_13D350','func_15113180',0x15113180,0x140630,38
COUNT,BASE=0x800DBEF0,0x800DBEF4
INPUTS=dict(previous.INPUTS,**{
    'conker/src/game/generated_13D350.c':'750c682e2aac536d6a48f9b403e4b50d3cd65482c519b2658ea54d7a7bf1f05f',
    'conker/build/conker.us.elf':'2d972c777f17469fec9c85c80f7ed5951bee4cc9e5b5c4c87706de2b4752a0b1',
    'conker/src/game_45B80.c':'de6b587a3966b174777e1d038378db6da3a918e77ba4151a3d54058185d6a012',
    'conker/build/src/game_45B80.c.o':'6f93d458b6a4991ee00a8d815534c58451aad5b9864fff79c9ceaf0c9533fafc',
})
SELECTED='''/* Refresh the active flag for each record and return the visited count. */
s32 func_15113180(void) {
    s32 index = 0;
    u32 offset = 0;
    u8 *record;
    u8 flags;

    if (D_800DBEF0 > 0) {
        do {
            D_800DBEF4[offset + 0x6F] &= ~0x40;
            record = D_800DBEF4 + offset;
            flags = record[0x6F];
            if (((flags & 0x0F) != 0 || (record[0x70] & 4) != 0) &&
                *(s32 *)(record + 0x38) != 0) {
                record[0x6F] = flags | 0x40;
            }
            index++;
            offset += 0xA0;
        } while (index < D_800DBEF0);
    }
    return index;
}
'''
INITIAL=SELECTED
compile_owner,link_owner,function_span=previous.compile_owner,previous.link_owner,previous.function_span
same_functions,normalized_pools=previous.same_functions,previous.normalized_pools
elf_slot_offset=previous.elf_slot_offset
raw_read,raw_text=Path.read_bytes,Path.read_text
RAW_SHA='0ebf63ce1434334e558ab0614cf8fc5ef50dea3c6c2b601cb6dccb3782a36235'
AFTER={
    'conker/build/conker.us.elf':'c20a95cd43bb3ea44e97fdd57f7691f530144cabe398370943f4aa04d074b5ec',
    'conker/src/game/generated_13D350.c':'5c781613db2a007870cf4e0c83a54324f7789fa5a0ed65364e996941eaa3195b',
    'conker/src/game_45B80.c':'63ff5cd1051b8ed117581dcc5321b4e4dd5370f8cffaf62bc5091087e968b210',
}


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15113180() {\n    return 0;\n}':
        raise ValueError('Unknown record flag placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='selected',body=None):
    if body is None:body=SELECTED
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,
        recovered_owner(values['conker/src/game/generated_13D350.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>38I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def forms():
    body=INITIAL.replace('            D_800DBEF4[offset + 0x6F] &= ~0x40;',
        '            record = D_800DBEF4 + offset;\n            record[0x6F] &= ~0x40;')
    yield 'local-record',body
    body=body.replace('(record[0x70] & 4) != 0','(record[0x70] & 4) == 4')
    yield 'local-record-four',body
    yield 'signed-offset',body.replace('u32 offset','s32 offset')
    yield 'reverse-initializers',body.replace('    s32 index = 0;\n    u32 offset = 0;',
        '    u32 offset = 0;\n    s32 index = 0;')
    yield 'separate-initializers',body.replace('    s32 index = 0;\n    u32 offset = 0;',
        '    s32 index;\n    u32 offset;').replace('    if (D_800DBEF0 > 0)',
        '    index = 0;\n    offset = 0;\n    if (D_800DBEF0 > 0)')
    yield 'wide-flags',body.replace('u8 flags;','u32 flags;')
    wide=body.replace('u8 flags;','u32 flags;')
    yield 'wide-register-index',wide.replace('s32 index = 0;','register s32 index = 0;')
    yield 'wide-void',wide.replace('s32 func_15113180(void)','void func_15113180(void)').replace('    return index;\n','')
    yield 'wide-reverse-updates',wide.replace('            index++;\n            offset += 0xA0;',
        '            offset += 0xA0;\n            index++;')
    yield 'wide-signed-flags',wide.replace('u32 flags;','s32 flags;')
    yield 'joint-zero',body.replace('    s32 index = 0;\n    u32 offset = 0;',
        '    s32 index;\n    u32 offset;').replace('    if (D_800DBEF0 > 0)',
        '    index = offset = 0;\n    if (D_800DBEF0 > 0)')
    yield 'pointer-declared-first',body.replace('    s32 index = 0;\n    u32 offset = 0;\n    u8 *record;',
        '    u8 *record;\n    u32 offset = 0;\n    s32 index = 0;')
    yield 'void-four',body.replace('s32 func_15113180(void)','void func_15113180(void)').replace('    return index;\n','')
    yield 'for-loop',body.replace('    if (D_800DBEF0 > 0) {\n        do {',
        '    for (; index < D_800DBEF0; index++, offset += 0xA0) {').replace(
        '            index++;\n            offset += 0xA0;\n        } while (index < D_800DBEF0);\n    }','    }')
    yield 'for-post-reversed',body.replace('    if (D_800DBEF0 > 0) {\n        do {',
        '    for (; index < D_800DBEF0; offset += 0xA0, index++) {').replace(
        '            index++;\n            offset += 0xA0;\n        } while (index < D_800DBEF0);\n    }','    }')


SELECTED=dict(forms())['wide-void'].replace(
    '/* Refresh the active flag for each record and return the visited count. */',
    '/* Refresh bit 0x40 from each record\'s flags and attached-object state. */')


def recovered_caller(before):
    declaration='s32 func_15113180(void);'
    if before.count(declaration)!=1:raise ValueError('Unknown flag-refresh caller declaration')
    return before.replace(declaration,'void func_15113180(void);',1)


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={0:[('R_MIPS_HI16','D_800DBEF0')],4:[('R_MIPS_LO16','D_800DBEF0')],
        28:[('R_MIPS_HI16','D_800DBEF4')],32:[('R_MIPS_LO16','D_800DBEF4')]}
    if len(raw)!=152 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown record flags body or global bindings')
    return raw,bindings


def qualify(root,out):
    values=freeze(root,out)
    obj,words,row=measure(root,out,'qualified',SELECTED)
    checked_object(obj)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_13D350.c'].decode(),'owner-before')
    if row['diagnostics'] or diagnostics or row['differences'] or \
            same_functions(before,obj,(FUNCTION,))!=33 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed flags diagnostics/shape/neighbors/pools')
    a,da=compile_owner(root,out,values['conker/src/game_45B80.c'].decode(),'caller-before')
    b,db=compile_owner(root,out,recovered_caller(values['conker/src/game_45B80.c'].decode()),'caller-after')
    caller_neighbors=same_functions(a,b)
    if da.replace('caller-before.c','caller.c')!=db.replace('caller-after.c','caller.c') or \
            normalized_pools(a)!=normalized_pools(b):
        raise ValueError('Caller declaration changes diagnostics or pools')
    (out/'caller-qualification.json').write_text(json.dumps(dict(functions=caller_neighbors,
        diagnostics_unchanged=True,pools_unchanged=True),indent=2)+'\n')
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/13D350.s',filename=OWNER,
        word_patches_path=root/'conker/retail_word_patches.us.csv'))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=152 or data[f['value']:f['value']+152]!=values['conker/conker.us.bin'][ROM:ROM+152]:
        raise ValueError('Padded flag refresh differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out)
    obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if old not in script:raise ValueError('Missing flags owner linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'first-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,152)
    if image[at:at+152]!=values['conker/conker.us.bin'][ROM:ROM+152]:
        raise ValueError('Complete flags prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Flags prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_13D350.c':recovered_owner(values['conker/src/game/generated_13D350.c'].decode(),SELECTED).encode(),
        'conker/src/game_45B80.c':recovered_caller(values['conker/src/game_45B80.c'].decode()).encode()}
    for p,data in expected.items():
        path=out/('after-elf' if p.endswith('.elf') else 'after-caller' if p.endswith('game_45B80.c') else 'after-owner')
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first flags successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=38,
        raw_differences=0,guards=0,functions=len(a),neighbors=33)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else
        'after-caller' if p.endswith('game_45B80.c') else 'after-owner')) for p in AFTER}
    if {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact flags successor')
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
        raise ValueError('Flags installation changed other functions/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],152,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Flags changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    for p in ('conker/retail_word_patches.us.csv','conker/build/src/game_45B80.c.o'):
        if hashlib.sha256(raw_read(root/p)).hexdigest()!=INPUTS[p]:
            raise ValueError('Flags changed guards or actual caller object')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Flags changed protected Game data')
    result=dict(functions=len(a),neighbors=33,only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),guards_unchanged=True,
        actual_caller_object_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true')
    parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            row=measure(root,root/BUILD,name,body)[2]
            print(json.dumps(dict(name=name,words=row['words'],differences=row['differences'],
                diagnostics=row['diagnostics'])),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD,body=SELECTED)[2],indent=2))
