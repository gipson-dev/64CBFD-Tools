"""Record-key chain: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15195D00','generated_1C2C60'
ENTRY,ROM,BODY,SIZE=0x15195D00,0x1C31B0,212,212
SOURCE='conker/src/game/generated_1C2C60.c'
OBJECT='conker/build/src/game/generated_1C2C60.c.o'
ASM='conker/asm/1C2C60.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-record-key-chain-match'
RODATA_SYMBOL=None
RAW_SHA='4a9a17f92379bd7f9bfa92b51d00b982ccc957d4d81174ed02c4b734312c3234'
SNAPSHOT_SHA='46f1b9970fc590cbff1b54464bac18e079e33654c5403353fdb34d651d4e2cb4'
BEFORE_ELF_SHA='a38b8269ea49acf42651d9db0f5573850f5cfb71ce935a4dc4d14712d6b343e2'
TRUTH_SHA='60647929c035be01d2f2433d9d3285ef05a59bc129b927655de124737b515e48'
BINDINGS={116: [('R_MIPS_HI16', 'D_800E08E0')], 128: [('R_MIPS_LO16', 'D_800E08E0')], 120: [('R_MIPS_HI16', 'D_800E08E4')], 124: [('R_MIPS_LO16', 'D_800E08E4')], 136: [('R_MIPS_26', 'func_151957B0')], 36: [('R_MIPS_HI16', 'D_800E08E0')], 40: [('R_MIPS_LO16', 'D_800E08E0')], 52: [('R_MIPS_HI16', 'D_800E08E4')], 160: [('R_MIPS_LO16', 'D_800E08E4')], 156: [('R_MIPS_26', 'func_151957B0')]}
ORIGINAL_BINDINGS={36: [('R_MIPS_HI16', 'D_800E08E0')], 40: [('R_MIPS_LO16', 'D_800E08E0')], 120: [('R_MIPS_HI16', 'D_800E08E4')], 124: [('R_MIPS_LO16', 'D_800E08E4')], 116: [('R_MIPS_HI16', 'D_800E08E0')], 128: [('R_MIPS_LO16', 'D_800E08E0')], 136: [('R_MIPS_26', 'func_151957B0')], 156: [('R_MIPS_26', 'func_151957B0')], 52: [('R_MIPS_HI16', 'D_800E08E4')], 160: [('R_MIPS_LO16', 'D_800E08E4')]}
HEADERS='#include <ultra64.h>\nextern s32 D_800E08E0,D_800E08E4;\ns32 func_151957B0(s32, u8 *, u8 *);\n'
DECLARATIONS=''
SELECTED='/* Preserve the retail key-chain cursor and append a missing association. */\nvoid func_15195D00(u8 *owner, s32 key, s32 index, s32 mode) {\n    u8 *cursor = *(u8 **)(owner + 0x18);\n    u8 *record;\n\n    if (cursor != NULL) {\n        record = cursor;\n        do {\n            if (*(s32 *)(record + 8) == key && *(u16 *)(record + 0xC) == index) {\n                return;\n            }\n            /* The look-ahead cursor exits before testing the final record. */\n            cursor = *(u8 **)(record + 0x10);\n            if (cursor != NULL) {\n                record = cursor;\n                cursor = *(u8 **)(cursor + 0x10);\n            }\n        } while (cursor != NULL);\n        cursor = (u8 *)func_151957B0(0x14, (u8 *)&D_800E08E0, (u8 *)&D_800E08E4);\n        *(u8 **)(record + 0x10) = cursor;\n    } else {\n        cursor = (u8 *)func_151957B0(0x14, (u8 *)&D_800E08E0, (u8 *)&D_800E08E4);\n        *(u8 **)(owner + 0x18) = cursor;\n    }\n    *(s32 *)(cursor + 8) = key;\n    *(u16 *)(cursor + 0xC) = index;\n    *(u8 **)(cursor + 0x10) = NULL;\n    cursor[0xE] = mode;\n    return;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Record-key chain owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=212 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record-key chain body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_15195D00() {\n    return 0;\n}':raise ValueError('Record-key placeholder changed')
    return before[:start]+SELECTED.rstrip()+before[end:]




def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record-key chain snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record-key chain frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record-key chain predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record-key chain live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Record-key chain named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Record-key chain symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Record-key chain metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record-key chain frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Record-key chain original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record-key chain strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record-key chain named definitions changed')

NEW_GUARDS=[{'filename': 'generated_1C2C60', 'function': 'func_15195D00', 'offset': '0x08C', 'expected': '0xAFA30020', 'replacement': '0xAFA30024', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize one record spill home within the unchanged frame and retail mode-load schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1C2C60', 'function': 'func_15195D00', 'offset': '0x090', 'expected': '0x8FA30020', 'replacement': '0x8FA30024', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize one record spill home within the unchanged frame and retail mode-load schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1C2C60', 'function': 'func_15195D00', 'offset': '0x0B4', 'expected': '0xAC400010', 'replacement': '0x8FA80034', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize one record spill home within the unchanged frame and retail mode-load schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1C2C60', 'function': 'func_15195D00', 'offset': '0x0B8', 'expected': '0x8FA80034', 'replacement': '0xAC400010', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize one record spill home within the unchanged frame and retail mode-load schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!='df35545460f559d729287f6e9d5c84412c910315fda7637ebf9fb3181894b184':raise ValueError('Record-key inherited guards changed')
    return before+b'generated_1C2C60,func_15195D00,0x08C,0xAFA30020,0xAFA30024,-,-,Normalize one record spill home within the unchanged frame and retail mode-load schedule,,,false\r\ngenerated_1C2C60,func_15195D00,0x090,0x8FA30020,0x8FA30024,-,-,Normalize one record spill home within the unchanged frame and retail mode-load schedule,,,false\r\ngenerated_1C2C60,func_15195D00,0x0B4,0xAC400010,0x8FA80034,-,-,Normalize one record spill home within the unchanged frame and retail mode-load schedule,,,false\r\ngenerated_1C2C60,func_15195D00,0x0B8,0x8FA80034,0xAC400010,-,-,Normalize one record spill home within the unchanged frame and retail mode-load schedule,,,false\r\n'






def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw);relocations=dict(bindings)
    parse=lambda text:[]if text=='-'else[tuple(v.split(':',1))for v in text.split(';')]
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],0)or bindings.get(at,[])!=parse(row['expected_relocations']):raise ValueError('Record-key chain expected word or binding changed')
        struct.pack_into('>I',result,at,int(row['replacement'],0));relocations.pop(at,None)
        if row['replacement_relocations']!='-':relocations[at]=parse(row['replacement_relocations'])
    if sha(result)!='0fd7ab50e2a51988063addf8bfb5fabf67f10bf81c40b009382e77e7a22c0278'or relocations!=ORIGINAL_BINDINGS:raise ValueError('Record-key chain normalized body/bindings changed')
    return bytes(result),relocations



ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15195D00.o','first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected.c', 'selected-processed.c', 'selected.o', 'selected-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1C2C60.c.o', 'make-shadow/src/game/generated_1C2C60.c.o.compact', 'make-shadow/src/game/generated_1C2C60.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record-key chain artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record-key chain artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record-key chain raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record-key chain evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record-key chain Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1C2C60.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record-key chain Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=4 or q['exclusions']!=0:raise ValueError('Record-key chain private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record-key chain changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record-key chain protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=53,frame=40,alignment_words=0,slot_words=53,strict_first_link_reproduced=True,guards=4,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
