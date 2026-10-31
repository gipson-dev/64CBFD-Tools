"""Settings packet write: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys,csv,io
import tools.pad_generated_object as _pad
sys.modules.setdefault('pad_generated_object',_pad)
from tools.pad_c_object import emit_padded_assembly as _emit
def emit_padded_assembly(obj,asm,filename,word_patches_path):
    asm=Path(asm)
    if asm.name!='func_15007558.s'or filename!='game_33990':raise ValueError('Script-lookup padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER=('func_15007558', 'game_33990')
ENTRY,ROM,BODY,SIZE=(352351576, 215560, 236, 236)
SOURCE='conker/src/game_33990.c'
OBJECT='conker/build/src/game_33990.c.o'
ASM='conker/asm/nonmatchings/game_33990/func_15007558.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-settings-packet-write-15007558-match'
RODATA_SYMBOL=None
RAW_SHA='2d7422666bf39e7f4f4487b3aae9590d9493ddbc0afa249ae69235f8554cd4f3'
SNAPSHOT_SHA='be7c495e201234213101acd0570e4f70a699fce2b085b22ccfb18cfc2c99e201'
BEFORE_ELF_SHA='d4a370151ebe4e7d4b1037e84479848fd95b4398ab7018c29ec07dfb462720ac'
TRUTH_SHA='f089f90c443471a35e83de645b6c32de47a6e787e13c47822932856cb09a6587'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE358')], 20: [('R_MIPS_LO16', 'D_800BE358')], 12: [('R_MIPS_HI16', 'D_800E0BE0')], 24: [('R_MIPS_LO16', 'D_800E0BE0')], 16: [('R_MIPS_HI16', 'D_800E0BFC')], 28: [('R_MIPS_LO16', 'D_800E0BFC')], 56: [('R_MIPS_HI16', 'D_800BE35A')], 64: [('R_MIPS_LO16', 'D_800BE35A')], 172: [('R_MIPS_HI16', 'D_800BE358')], 176: [('R_MIPS_LO16', 'D_800BE358')], 184: [('R_MIPS_HI16', 'D_8002AC5C')], 188: [('R_MIPS_LO16', 'D_8002AC5C')], 192: [('R_MIPS_HI16', 'D_800BE900')], 196: [('R_MIPS_LO16', 'D_800BE900')], 208: [('R_MIPS_26', 'func_151DCEF0')]}
ORIGINAL_BINDINGS={16: [('R_MIPS_HI16', 'D_800E0BFC')], 20: [('R_MIPS_LO16', 'D_800E0BFC')], 12: [('R_MIPS_HI16', 'D_800E0BE0')], 24: [('R_MIPS_LO16', 'D_800E0BE0')], 8: [('R_MIPS_HI16', 'D_800BE358')], 28: [('R_MIPS_LO16', 'D_800BE358')], 56: [('R_MIPS_HI16', 'D_800BE35A')], 64: [('R_MIPS_LO16', 'D_800BE35A')], 172: [('R_MIPS_HI16', 'D_800BE358')], 176: [('R_MIPS_LO16', 'D_800BE358')], 184: [('R_MIPS_HI16', 'D_8002AC5C')], 188: [('R_MIPS_LO16', 'D_8002AC5C')], 192: [('R_MIPS_HI16', 'D_800BE900')], 196: [('R_MIPS_LO16', 'D_800BE900')], 208: [('R_MIPS_26', 'func_151DCEF0')]}
HEADERS='#include <ultra64.h>\nextern u8 D_800BE358[128];\nextern u8 D_800BE35A[28];\nextern s8 D_800E0BE0[28];\nextern s8 D_800E0BFC[];\nextern u8 D_8002AC5C;\nextern OSMesgQueue D_800BE900;\ns32 func_151DCEF0(OSMesgQueue *, s32, void *, s32);\n\n'
DECLARATIONS=''
SELECTED='/* Copy the settings payload, checksum it, and queue the 32-byte EEPROM record. */\nvoid func_15007558(void) {\n    u16 checksum;\n    volatile s32 result;\n    s32 index;\n    s8 *settings;\n    u8 *record;\n\n    record = D_800BE358 + 2;\n    settings = D_800E0BE0;\n    do {\n        *record++ = *settings++;\n    } while ((u32)settings < (u32)D_800E0BFC);\n    checksum = 0xCC;\n    record = D_800BE35A;\n    index = 2;\n    do {\n        checksum += *record++ << (index++ & 3);\n    } while (index < 30);\n    *(u16 *)D_800BE358 = checksum;\n    if (D_8002AC5C == 0) {\n        result = func_151DCEF0(&D_800BE900, 0, D_800BE358, 32);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected settings packet write owner diagnostics')
    return 0



sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Settings packet write body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_15007558() {\n    return 0;\n}':raise ValueError('Settings packet placeholder changed')
    after=before[:a]+SELECTED.rstrip()+before[b:]
    after=after.replace('s32 func_15007558();','void func_15007558(void);',1)
    after=after.replace('/* Non-matching C placeholders for asm/nonmatchings/game_33990/func_15007558.s. */\n','',1)
    return after.replace('extern u8 D_8002AC5C;','extern u8 D_800BE35A[28];\nextern s8 D_800E0BE0[28];\nextern s8 D_800E0BFC[];\nextern u8 D_8002AC5C;',1)




def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Settings packet write snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Settings packet write frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Settings packet write predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:
        changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),
                 SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),
                 HEADER:recovered_header(values[HEADER]),DEPENDENCY:recovered_settings_owner(values[DEPENDENCY].decode()).encode(),
                 'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Settings packet live input differs: '+name)
    return values


METADATA_GROUPS=((2898804, ('D_800E0BFC', 'D_800A36CC'), (1, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Settings packet write named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Settings packet write symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Settings packet write metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Settings packet write frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Settings packet write original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Settings packet write strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Settings packet write named definitions changed')

NEW_GUARDS=[{'filename': 'game_33990', 'function': 'func_15007558', 'offset': '0x014', 'expected': '0x24420002', 'replacement': '0x24840000', 'expected_relocations': 'R_MIPS_LO16:D_800BE358', 'replacement_relocations': 'R_MIPS_LO16:D_800E0BFC', 'note': 'Normalize closed payload-pointer displacement and independent address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007558', 'offset': '0x01C', 'expected': '0x24840000', 'replacement': '0x24420000', 'expected_relocations': 'R_MIPS_LO16:D_800E0BFC', 'replacement_relocations': 'R_MIPS_LO16:D_800BE358', 'note': 'Normalize closed payload-pointer displacement and independent address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007558', 'offset': '0x034', 'expected': '0xA04EFFFF', 'replacement': '0xA04E0001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed payload-pointer displacement and independent address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited settings packet write guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Script-lookup guard already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Settings packet normalization scope changed')
    checked_payload(raw,bindings);words=list(struct.unpack('>59I',raw));rs=dict(bindings)
    fmt=lambda rel:';'.join(k+':'+n for k,n in rel)if rel else '-'
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if words[at//4]!=int(row['expected'],0)or fmt(rs.get(at,[]))!=row['expected_relocations']:raise ValueError('Settings packet expected preimage changed')
        words[at//4]=int(row['replacement'],0)
        if row['replacement_relocations']=='-':rs.pop(at,None)
        else:rs[at]=[tuple(part.split(':',1))for part in row['replacement_relocations'].split(';')]
    result=struct.pack('>59I',*words)
    if sha(result)!=NORMALIZED_SHA or rs!=ORIGINAL_BINDINGS:raise ValueError('Settings packet normalized bytes/bindings changed')
    return result,rs



NORMALIZED_SHA='65ab7c37e99216c2dee5f8abcee68cbde80db8450d9e7f65af632d0f2911e084'

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15007558.o', 'first-linked.elf', 'proposed-variables.h', 'proposed-settings-owner.c', 'after-settings-owner-padded.o')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_33990.c.o', 'make-shadow/src/game_33990.c.o.compact', 'make-shadow/src/game_33990.c.o.padded.s', 'before-settings-owner.c', 'before-settings-owner-processed.c', 'before-settings-owner.o', 'before-settings-owner-diagnostics.txt', 'after-settings-owner.c', 'after-settings-owner-processed.c', 'after-settings-owner.o', 'after-settings-owner-diagnostics.txt', 'settings-Make-plan.txt', 'settings-Make-commands.json', 'make-shadow/src/game/generated_20AE20.c.o')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Settings packet write artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Settings packet write artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Settings packet write raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Settings packet write evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Settings packet write Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_33990.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Settings packet write Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=3 or q['exclusions']!=0:raise ValueError('Settings packet write private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Settings packet write changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Settings packet write protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=32,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=3,insertions=0,omissions=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='ec60562ac74252fb404bfbf61692e37f558e50a4bbdbfc1db1af47140aecdcff'

from contextlib import contextmanager
from tools.experiments.game_remaining_donor_candidates import compile_owner as _compile_owner
HEADER='conker/include/variables.h'
DEPENDENCY='conker/src/game/generated_20AE20.c'
DEPENDENCY_OBJECT='conker/build/src/game/generated_20AE20.c.o'
def recovered_header(before):
    old=b'extern u8   D_800BE358[8];'
    if before.count(old)!=1:raise ValueError('Settings record declaration changed')
    return before.replace(old,b'extern u8   D_800BE358[128]; // Shared EEPROM scratch; settings use 32 bytes, erase uses eight.')
def recovered_settings_owner(before):
    before=before.replace('\r\n','\n');old='s8 D_800E0BE0[23];'
    if before.count(old)!=1:raise ValueError('Settings region declaration changed')
    return before.replace(old,'s8 D_800E0BE0[28]; // Persisted settings span; reset initializes the first 23 bytes.')
@contextmanager
def candidate_header(root,output):
    p=root/HEADER;saved=p.read_bytes();before=(output/'before-conker_include_variables.h').read_bytes()
    pins=json.loads((output/'input-snapshot.json').read_text())['INPUTS']
    if sha(before)!=pins[HEADER]:raise ValueError('Frozen header changed')
    wanted=recovered_header(before)
    if saved not in(before,wanted)or(output/'proposed-variables.h').read_bytes()!=wanted:raise ValueError('Candidate header changed')
    try:
        p.write_bytes(wanted)
        yield
    finally:p.write_bytes(saved)
def compile_owner(root,output,text,name,flags=('-O2','-g3')):
    if '#include "variables.h"'in text:
        with candidate_header(root,root/BUILD):return _compile_owner(root,output,text,name,flags)
    return _compile_owner(root,output,text,name,flags)
