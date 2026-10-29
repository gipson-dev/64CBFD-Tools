"""Record address relocator: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
from tools import pad_generated_object as _pad
sys.modules.setdefault('pad_generated_object',_pad)
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15003120','game_305D0'
ENTRY,ROM,BODY,SIZE=0x15003120,0x305D0,204,204
SOURCE='conker/src/game_305D0.c'
OBJECT='conker/build/src/game_305D0.c.o'
ASM='conker/asm/nonmatchings/game_305D0/func_15003120.s'
HEADER='conker/include/variables.h'
BUILD='conker/build/game-record-address-relocator-match'
RODATA_SYMBOL=None
RAW_SHA='4e1da0c4aca1f610e094b44913958f14c6e3d30093b6336abac4de5e2ccea2bf'
SNAPSHOT_SHA='fbd63a230d375de49de704ba7ca37dc73b83a2ad931e0568f8948cc06bad317b'
BEFORE_ELF_SHA='c5a6aaa4f456945acddc61bade7f17188756d3cd3195b4af1dd77b8d416b0f8d'
TRUTH_SHA='0878890f2971af6eaddb6dfb0b79e25055aa3a3da7b6cf6ddf352435ce6362c1'
BINDINGS={0:[('R_MIPS_HI16','D_800B0E30')],12:[('R_MIPS_LO16','D_800B0E30')],4:[('R_MIPS_HI16','D_800B0E34')],8:[('R_MIPS_LO16','D_800B0E34')]}
HEADERS='#include <ultra64.h>\nextern u32 **D_800B0E30;\nextern u8 *D_800B0E34;\n\n'
SELECTED='/* Install a record list and relocate its two address fields in place. */\nvoid func_15003120(s32 index, u32 offset, u32 *records) {\n    s32 count;\n\n    D_800B0E30[index] = records;\n    D_800B0E34[index] = 0;\n    if (records != 0) {\n        D_800B0E30[index] = (u32 *)((u32)D_800B0E30[index] + offset);\n        for (count = 0; D_800B0E30[index][count * 3] != 0; count++) {\n            D_800B0E30[index][count * 3] += offset;\n            D_800B0E30[index][count * 3 + 1] += offset;\n        }\n        D_800B0E34[index] = count;\n    }\n}\n'

HEADER_DEPENDENTS={'conker/build/src/debugger_258ED0.c.o': {'source': 'conker/src/debugger_258ED0.c', 'object': 'conker/build/src/debugger_258ED0.c.o', 'before_SHA256': '162aef6d254b861bb00fbbe0c4270f67471c52db803fbda12b840dff773fedb2', 'after_SHA256': '6dfa5112ffc7ac8695bfe9ab269c4408e5f8cc301402a50d175e796eed1178f6', 'identical': False, 'shadow': 'header-shadow/src/debugger_258ED0.c.o'}, 'conker/build/src/game/done/game_75810.c.o': {'source': 'conker/src/game/done/game_75810.c', 'object': 'conker/build/src/game/done/game_75810.c.o', 'before_SHA256': 'd06e2f6d517face79259c8344238d07b01b34cbd78a8a9465b540f4aee8c0531', 'after_SHA256': '6e910d1193e3553dd6e8d6a5bcd5fb6378dc4b09ee2333245a70a2befb91b74b', 'identical': False, 'shadow': 'header-shadow/src/game/done/game_75810.c.o'}, 'conker/build/src/game/done/game_75950.c.o': {'source': 'conker/src/game/done/game_75950.c', 'object': 'conker/build/src/game/done/game_75950.c.o', 'before_SHA256': '68aea79d7d0b6dde9fea76d6400dda4fd6696ce71d9796132e775b93d3f815b4', 'after_SHA256': '14fc40242742ca17b8f0b4e0e00c6851e1f5de2d25fd7f5ad4430403e5005de6', 'identical': False, 'shadow': 'header-shadow/src/game/done/game_75950.c.o'}, 'conker/build/src/libultra/audio/init_128D0.c.o': {'source': 'conker/src/libultra/audio/init_128D0.c', 'object': 'conker/build/src/libultra/audio/init_128D0.c.o', 'before_SHA256': 'cf0df90565a597ec276ae1e6acd6490eeea4f57fee0b34d80eedff1214849b7b', 'after_SHA256': '7e7201abdb403247bbe7a853de92a9723ad8cc4865f6644fb5c77dcf6a5e455e', 'identical': False, 'shadow': 'header-shadow/src/libultra/audio/init_128D0.c.o'}, 'conker/build/src/libultra/gu/guPerspectiveF.c.o': {'source': 'conker/src/libultra/gu/guPerspectiveF.c', 'object': 'conker/build/src/libultra/gu/guPerspectiveF.c.o', 'before_SHA256': 'bc5f2b9b7645bd6f95f634640c2ff64da803db9ea6f996a2b327384f5ff23f6d', 'after_SHA256': '225ed8159478d2b4ea66382b7c6fc061da97aba8141f5b85965426194bd6d430', 'identical': False, 'shadow': 'header-shadow/src/libultra/gu/guPerspectiveF.c.o'}, 'conker/build/src/libultra/gu/guRotateF.c.o': {'source': 'conker/src/libultra/gu/guRotateF.c', 'object': 'conker/build/src/libultra/gu/guRotateF.c.o', 'before_SHA256': 'c60ce8d54376f1162fdb0a56a6593ad89492a05007eb9f8dff0e2fdb5c1ac310', 'after_SHA256': 'ff91ce2d6d46114e39b8482fb988de0654e1a80a4d0e4a5c4c56cc6e877b338a', 'identical': False, 'shadow': 'header-shadow/src/libultra/gu/guRotateF.c.o'}, 'conker/build/src/libultra/gu/sinf.c.o': {'source': 'conker/src/libultra/gu/sinf.c', 'object': 'conker/build/src/libultra/gu/sinf.c.o', 'before_SHA256': '100de92468889c8cce6f771bf2ca3ebe8fd9b78ead6ecf013f47834f525d2c42', 'after_SHA256': 'b52c401b82ad45ce0d7d3f5d3ba8002c5f68651900962216814cef224eaed438', 'identical': False, 'shadow': 'header-shadow/src/libultra/gu/sinf.c.o'}}

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected record-address-relocator owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=204 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record address relocator body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15003120() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Record relocator placeholder changed')
    return before.replace('s32 func_15003120();','void func_15003120(s32 index, u32 offset, u32 *records);').replace('// what is this loop doing?\n/* Non-matching C placeholders for asm/nonmatchings/game_305D0/func_15003120.s. */\n','').replace(stub,SELECTED.strip())

def recovered_header(before):
    if before.count('extern s32  D_800B0E30[];')!=1 or before.count('extern u8   D_800B0E34[];')!=1:raise ValueError('Record relocator globals changed')
    return before.replace('extern s32  D_800B0E30[];','extern u32 **D_800B0E30;').replace('extern u8   D_800B0E34[];','extern u8 *D_800B0E34;')

def compile_frozen_owner(root,out,text,header,label):
    # Separate copied headers allow both tools copies to run concurrently.
    path=out/(label+'-variables.h');path.write_bytes(header)
    assert text.count('#include "variables.h"')==1
    return compile_owner(root,out,text.replace('#include "variables.h"','#include "'+str(path)+'"'),label)


def dependent_sections(data):
    h=struct.unpack_from('>16sHHIIIIIHHHHHH',data);rows=[struct.unpack_from('>10I',data,h[6]+h[11]*i)for i in range(h[12])];name=rows[h[13]];names=data[name[4]:name[4]+name[5]]
    return {names[x[0]:].split(b'\0',1)[0].decode():(x,data[x[4]:x[4]+x[5]]if x[1]!=8 else b'')for x in rows}

def dependent_debug(data):
    sh,raw=dependent_sections(data)['.mdebug'];h=struct.unpack_from('>HH23I',raw);assert h[0]==0x7009
    def table(count,offset,size):return data[h[offset]:h[offset]+h[count]*size]
    strings=table(15,16,1);extstrings=table(17,18,1)
    def clean(s):
        s=s.replace(b'build/game-record-address-relocator-match/header-shadow/',b'build/')
        if re.fullmatch(rb'1[0-9]{9}',s):return b'<compiler-build-time>'
        return s
    def name(at):return clean(strings[at:].split(b'\0',1)[0])
    fdr=table(19,20,72);syms=table(9,10,12);files=[];symbols=[];seen=set()
    for i in range(h[19]):
        f=struct.unpack_from('>10I2H7I',fdr,i*72);files.append((f[0],name(f[2]+f[1]),*f[4:]))
        for j in range(f[4],f[4]+f[5]):
            assert j not in seen;seen.add(j);a,b,c=struct.unpack_from('>3I',syms,j*12);symbols.append((j,name(f[2]+a),b,c))
    assert seen==set(range(h[9]))
    fixed=tuple(h[i]for i in(0,1,2,3,5,7,9,11,13,17,19,21,23))
    return(fixed,tuple(clean(s)for s in strings.rstrip(b'\0').split(b'\0')),extstrings,files,sorted(symbols),*[table(a,b,n)for a,b,n in((3,4,1),(5,6,8),(7,8,52),(11,12,12),(13,14,4),(21,22,4),(23,24,16))])

def check_dependent(expected,actual):
    a=dependent_sections(expected);b=dependent_sections(actual)
    if a.keys()!=b.keys():raise ValueError('Dependent section names differ')
    for name,(h,data)in a.items():
        hh,dd=b[name]
        indexes=(0,1,2,3,6,7,8,9)if name=='.mdebug'else(0,1,2,3,5,6,7,8,9)
        if tuple(h[i]for i in indexes)!=tuple(hh[i]for i in indexes):raise ValueError('Dependent section geometry differs: '+name)
        if name!='.mdebug'and data!=dd:raise ValueError('Dependent section bytes differ: '+name)
    if dependent_debug(expected)!=dependent_debug(actual):raise ValueError('Dependent debug records differ beyond output path and build time')
    return True

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record address relocator snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record address relocator frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record address relocator predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={HEADER:recovered_header(values[HEADER].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    if installed:
        for name,row in HEADER_DEPENDENTS.items():
            actual=(root/name).read_bytes();check_dependent((output/row['shadow']).read_bytes(),actual);changes[name]=actual
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record address relocator live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record address relocator frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Record address relocator original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record address relocator strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record address relocator named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='82a037c271b5f3a9f248316290dcb31008db70397b5ec399ebc415cdd6bd8f3a':raise ValueError('Record address relocator inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15003120.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game_305D0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game_305D0.c.o","make-shadow/src/game_305D0.c.o.padded.s","proposed-variables.h",)

EVIDENCE += ('header-owner-audit.json', 'header-section-audit.json', 'header-linked.elf', 'header-shadow-build.json', 'header-shadow-build.log', 'header-before-build.log', 'header-shadow/src/debugger_258ED0.c.o', 'header-shadow/src/game/done/game_75810.c.o', 'header-shadow/src/game/done/game_75950.c.o', 'header-shadow/src/libultra/audio/init_128D0.c.o', 'header-shadow/src/libultra/gu/guPerspectiveF.c.o', 'header-shadow/src/libultra/gu/guRotateF.c.o', 'header-shadow/src/libultra/gu/sinf.c.o', 'header-before-shadow/src/debugger_258ED0.c.o', 'header-before-shadow/src/game/done/game_75810.c.o', 'header-before-shadow/src/game/done/game_75950.c.o', 'header-before-shadow/src/libultra/audio/init_128D0.c.o', 'header-before-shadow/src/libultra/gu/guPerspectiveF.c.o', 'header-before-shadow/src/libultra/gu/guRotateF.c.o', 'header-before-shadow/src/libultra/gu/sinf.c.o')

EVIDENCE += ('production-dependent-audit.json', 'production-diagnostic/conker/build/src/debugger_258ED0.c.o', 'production-diagnostic/conker/build/src/game/done/game_75810.c.o', 'production-diagnostic/conker/build/src/game/done/game_75950.c.o', 'production-diagnostic/conker/build/src/libultra/audio/init_128D0.c.o', 'production-diagnostic/conker/build/src/libultra/gu/guPerspectiveF.c.o', 'production-diagnostic/conker/build/src/libultra/gu/guRotateF.c.o', 'production-diagnostic/conker/build/src/libultra/gu/sinf.c.o')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record address relocator artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record address relocator artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record address relocator raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record address relocator evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record address relocator Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_305D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record address relocator Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record address relocator private qualification changed')
    header=json.loads((output/'header-owner-audit.json').read_text())
    if not header['complete'] or header['owners']!=209 or len(header['dependency_audit'])!=7:raise ValueError('Incomplete header-dependent owner audit')
    if(output/'header-linked.elf').read_bytes()!=(output/'first-linked.elf').read_bytes():raise ValueError('Header-dependent relink differs')
    for name,row in HEADER_DEPENDENTS.items():
        if sha((output/row['shadow']).read_bytes())!=row['after_SHA256']:raise ValueError('Rebuilt header dependent differs: '+name)
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record address relocator changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record address relocator protected data changed')
    q=dict(header_dependent_owners=209,metadata_only_dependent_objects=7,functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=0,alignment_words=0,slot_words=51,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
