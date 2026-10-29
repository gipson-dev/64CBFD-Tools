"""Active record lookup: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,sys
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1509CA98','generated_C9EC0'
ENTRY,ROM,BODY,SIZE=0x1509CA98,0xC9F48,208,208
SOURCE='conker/src/game/generated_C9EC0.c'
OBJECT='conker/build/src/game/generated_C9EC0.c.o'
ASM='conker/asm/C9EC0.s'
BUILD='conker/build/game-active-record-lookup-match'
RODATA_SYMBOL=None
TABLE=0x80087430
NORMALIZED_BINDINGS={0:[("R_MIPS_HI16","D_80087430")],16:[("R_MIPS_LO16","D_80087430")]}
RAW_SHA='18dd8078c405cec410edda45b8af30c21e8b62310bd2ffbf5b5e27b2b0333631'
SNAPSHOT_SHA='37d684c362dfa7d8b4fbb40b627576a1d5a4004bba91e23754f95a298101a937'
BEFORE_ELF_SHA='ca2136210cc2b6554c27c2dc888afe2af11a237094a8df6ca47c8e15317bf9d7'
TRUTH_SHA='a7403f03913353d7a2a3c5c41615195861ba3c41bd81daa7c7b460b4366f83b3'
BINDINGS={0: [('R_MIPS_HI16', 'D_80087430')], 12: [('R_MIPS_LO16', 'D_80087430')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    s32 field0;\n    s32 field4;\n    u16 field8;\n    u8 padA[0xA];\n} GeneratedC9EC0Entry;\n\nextern GeneratedC9EC0Entry D_80087430[];\nextern GeneratedC9EC0Entry D_80088420[];\n\n'
DECLARATIONS=''
SELECTED='/* Find the first active record whose masked key equals the requested value. */\ns32 func_1509CA98(u32 key) {\n    s32 index = 0;\n    GeneratedC9EC0Entry *entry = D_80087430;\n\n    do {\n        if (entry[0].field0 != 0 &&\n            ((u32)entry[0].field4 & 0x1FFFFFFF) + 1 == key) {\n            return index;\n        }\n        if (entry[1].field0 != 0 &&\n            ((u32)entry[1].field4 & 0x1FFFFFFF) + 1 == key) {\n            return index + 1;\n        }\n        if (entry[2].field0 != 0 &&\n            ((u32)entry[2].field4 & 0x1FFFFFFF) + 1 == key) {\n            return index + 2;\n        }\n        if (entry[3].field0 != 0 &&\n            ((u32)entry[3].field4 & 0x1FFFFFFF) + 1 == key) {\n            return index + 3;\n        }\n        index += 4;\n        entry += 4;\n    } while (index != 204);\n    return 204;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Active record lookup owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=208 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Active record lookup body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1509CA98() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Active record lookup placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED.strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Active record lookup snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Active record lookup frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Active record lookup predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Active record lookup live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Active record lookup frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Active record lookup original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Active record lookup strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Active record lookup named definitions changed')

NEW_GUARDS=[dict(filename=OWNER,function=FUNCTION,offset=hex(at),expected=hex(old),replacement=hex(new),expected_relocations=er,replacement_relocations=rr,note='Exchange independent mask and table-address completions',insert_after='',insert_after_relocations='',omit='false')for at,old,new,er,rr in ((12,0x24420000,0x34A5FFFF,'R_MIPS_LO16:D_80087430','-'),(16,0x34A5FFFF,0x24420000,'-','R_MIPS_LO16:D_80087430'))]

def guard_manifest(before):
    import csv,io
    if sha(before)!='e800c51d09743626c1f1c510d66940511b7ce848746e8add05d95be041ec4be1':raise ValueError('Inherited guard bytes changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Lookup guards already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw)
    struct.pack_into('>II',out,12,0x34A5FFFF,0x24420000)
    if sha(out)!='818ce7241e76826cf6e9e1527c9a9e5d12561624e6230882bec3390049b4d642':raise ValueError('Normalized lookup words differ')
    return bytes(out),NORMALIZED_BINDINGS


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1509CA98.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_C9EC0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_C9EC0.c.o","make-shadow/src/game/generated_C9EC0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Active record lookup artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active record lookup artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active record lookup raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Active record lookup evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active record lookup Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_C9EC0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Active record lookup Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Active record lookup private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Active record lookup changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Active record lookup protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=0,alignment_words=0,slot_words=52,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q


def compile_owner(root, out, source, name, flags=('-O2', '-g3', '-Wo,-loopunroll,0')):
    raw, processed, obj = (out / (name + suffix) for suffix in ('.c', '-processed.c', '.o'))
    raw.write_text(source)
    processor = [sys.executable, str(root / 'tools/asm-processor/asm_processor.py'), *[f for f in flags if not f.startswith('-Wo,')],
        str(raw.relative_to(root / 'conker'))]
    preprocess = subprocess.run(processor, cwd=root / 'conker', capture_output=True, text=True, check=True)
    if preprocess.stderr:
        raise ValueError(preprocess.stderr)
    processed.write_text(preprocess.stdout)
    includes = ['.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc',
        'src/libultra/os', 'src/libultra/audio', 'src/libultra/io']
    command = [str(root / 'ido/ido5.3_recomp/cc'), '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-D_LANGUAGE_C', '-D_FINALROM',
        '-DF3DEX_GBI_2', '-D_MIPS_SZLONG=32', '-woff', '649,838',
        *[flag for path in includes for flag in ('-I', path)], *flags, '-mips2', '-o32',
        '-o', str(obj.relative_to(root / 'conker')), str(processed.relative_to(root / 'conker'))]
    result = subprocess.run(command, cwd=root / 'conker', capture_output=True, text=True)
    diagnostics = result.stdout + result.stderr
    (out / (name + '-diagnostics.txt')).write_text(diagnostics)
    if result.returncode:
        raise ValueError(diagnostics)
    subprocess.run([*processor, '--post-process', str(obj.relative_to(root / 'conker')),
        '--assembler', 'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
        '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=root / 'conker',
        capture_output=True, text=True, check=True)
    return obj, diagnostics
