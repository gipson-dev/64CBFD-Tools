"""Dependency visit mark: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_recursive_dependency_readiness_match import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1509CE64','generated_C9EC0'
ENTRY,ROM,BODY,SIZE=0x1509CE64,0xCA314,196,196
SOURCE='conker/src/game/generated_C9EC0.c'
OBJECT='conker/build/src/game/generated_C9EC0.c.o'
ASM='conker/asm/C9EC0.s'
BUILD='conker/build/game-dependency-visit-mark-match'
RODATA_SYMBOL=None
RAW_SHA="e62bdff65d663a9e7de1e336da5ffc94f7822e0291f3bded9d1d8ad98cd96579"
SNAPSHOT_SHA="9391215f18426fade066204896e9b8d41fdb9ac7c26523ab66b0b59d55e302e2"
BEFORE_ELF_SHA="3d06b6465acf80871e73d069921a2701d18617a79d1ce99d9c8ab5bc91883c09"
TRUTH_SHA="75abdaee22efa95a287fe07c426d1fec36372a19725011f53ae464bb516acd36"
PARENT,TABLE,BITMAP,STATE=0x1509CCB4,0x8008743C,0x800D2E4C,0x800D2E70
BINDINGS={52:[('R_MIPS_HI16','D_800D2E4C')],72:[('R_MIPS_LO16','D_800D2E4C')],64:[('R_MIPS_HI16','D_800D2E70')],68:[('R_MIPS_LO16','D_800D2E70')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="extern u8 D_800D2E70[];\nextern u8 *D_800D2E4C;\n\n"
SELECTED="/* Visit a sentinel-terminated dependency list, then mark each live entry. */\nvoid func_1509CE64(u16 *dependency, void (*visit)(s32)) {\n    s32 index;\n    u16 *cursor;\n    if (*dependency != 0xFFFF) {\n        index = *dependency;\n        cursor = dependency;\n        do {\n            visit(index);\n            D_800D2E70[*cursor] = 3;\n            index = *cursor++;\n            D_800D2E4C[index >> 3] |= 1 << (index & 7);\n            index = *cursor;\n        } while (index != 0xFFFF);\n    }\n}"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected dependency owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Dependency visit mark body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1509CE64() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Dependency visitor placeholder changed')
    old='func_1509CE64(*(s32 *) ((u8 *) D_8008743C + arg0 * 20),'
    if before.count(old)!=1:raise ValueError('Dependency dispatcher call changed')
    return before.replace(stub,SELECTED,1).replace('s32 func_1509CE64();','void func_1509CE64(u16 *dependency, void (*visit)(s32));',1).replace(old,'func_1509CE64(*(u16 **) ((u8 *) D_8008743C + arg0 * 20),',1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Dependency visit mark snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Dependency visit mark frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Dependency visit mark predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Dependency visit mark live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Dependency visit mark strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Dependency visit mark original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Dependency visit mark image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Dependency visit mark named ELF definitions changed')

def derive_guards():
    """Closed entry-value and scratch-register exchanges; no memory reordering."""
    expected={44:0x94820000,56:0x12620018,60:0x00408025,88:0x962E0000,92:0x240A0001,100:0x028E7821,104:0xA1F50000,112:0x8ED90000,116:0x0010C0C3,120:0x03191021,124:0x90480000,128:0x32090007,132:0x012A5804,136:0x010B6025,140:0xA04C0000,148:0x1613FFEE}
    result=dict(expected)
    # LHU has already zero-extended the value. The entry transfer may therefore
    # be ANDI 0xffff rather than OR zero, on both taken and fallthrough paths.
    result[44]=(expected[44]&~(31<<16))|(14<<16)
    result[56]=(expected[56]&~(31<<16))|(14<<16)
    result[60]=(12<<26)|(14<<21)|(16<<16)|65535
    allocation={14:15,15:24,25:8,24:25,8:9,9:10,10:11,11:12,12:13}
    fields={88:(16,),92:(16,),100:(21,16,11),104:(21,16),112:(16,),116:(16,11),120:(21,16,11),124:(21,16),128:(21,16),132:(21,16,11),136:(21,16,11),140:(21,16)}
    for at,shifts in fields.items():
        word=expected[at]
        for shift in shifts:
            reg=word>>shift&31;word=(word&~(31<<shift))|(allocation.get(reg,reg)<<shift)
        result[at]=word
    left,right=expected[148]>>21&31,expected[148]>>16&31
    result[148]=(expected[148]&~((31<<21)|(31<<16)))|(right<<21)|(left<<16)
    assert len(result)==16 and all(result[at]!=word for at,word in expected.items())
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,expected='0x%08X'%word,replacement='0x%08X'%result[at],expected_relocations='-',replacement_relocations='-',note='Normalize dependency visitor closed value lifetime and scratch register allocation'if at<148 else'Normalize symmetric dependency loop sentinel comparison',insert_after='',insert_after_relocations='',omit='false')for at,word in sorted(expected.items())]

NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='c9f2d82d72afcd7be14278dbc076ff6b8aa1330ca0f42e11d3bcf51b76923225':raise ValueError('Inherited guard manifest changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Target guards already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10)).writerows(NEW_GUARDS);return before+out.getvalue().encode()
def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw)
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',raw,at)[0]!=int(row['expected'],0)or bindings.get(at):raise ValueError('Guard word/binding changed')
        struct.pack_into('>I',result,at,int(row['replacement'],0))
    if sha(result)!='9529ee3276fcdcd94801d0439686e07682301a6556621f50aeb61d12f92cde82':raise ValueError('Normalized dependency body changed')
    return bytes(result),bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1509CE64.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_C9EC0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_C9EC0.c.o","make-shadow/src/game/generated_C9EC0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Dependency visit mark artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Dependency visit mark artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Dependency visit mark raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Dependency visit mark evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Dependency visit mark Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_C9EC0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Dependency visit mark Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=16 or q['exclusions']!=0:raise ValueError('Dependency visit mark private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Dependency visit mark changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Dependency visit mark protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=56,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=16,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
