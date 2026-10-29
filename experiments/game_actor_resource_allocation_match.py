"""Actor resource allocation: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150832AC','generated_AEB40'
ENTRY,ROM,BODY,SIZE=0x150832AC,0xB075C,216,216
SOURCE='conker/src/game/generated_AEB40.c'
OBJECT='conker/build/src/game/generated_AEB40.c.o'
ASM='conker/asm/AEB40.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-resource-allocation-match'
RODATA_SYMBOL='jtbl_8009CC40_game'
RAW_SHA='d6e04892527fb26a9a00dc317506d20ae92f66ef72f1937f67fb2fb9eda8f682'
SNAPSHOT_SHA='c1d6dcbaab5df3b4900d80a65f77ab1f2b31b9942c8361ea01fe814ba780e6ef'
BEFORE_ELF_SHA='d0b63f826b9da140efaf02c86cf7899e7b3c2725b145bbc866ac839711b5ec9c'
TRUTH_SHA='14b7df0be085ab37b075df09a3e271de4835e77cf9299fc0ea291bd6d38f1f34'
BINDINGS={36: [('R_MIPS_HI16', 'D_80082FA0')], 40: [('R_MIPS_LO16', 'D_80082FA0')], 108: [('R_MIPS_26', 'func_1515D480')], 168: [('R_MIPS_26', 'func_1515D440')]}
ORIGINAL_BINDINGS={36: [('R_MIPS_HI16', 'D_80082FA0')], 40: [('R_MIPS_LO16', 'D_80082FA0')], 112: [('R_MIPS_26', 'func_1515D480')], 172: [('R_MIPS_26', 'func_1515D440')]}
HEADERS='#include <ultra64.h>\nextern s32 D_80082FA0;\nu8 *func_1515D480(s32);\nu8 *func_1515D440(void);\n\n'
DECLARATIONS='extern s32 D_80082FA0;\nu8 *func_1515D480(s32);\nu8 *func_1515D440(void);\n\n'
SELECTED="/* Allocate each active view's resources and retain the shared trailing resource. */\nvoid func_150832AC(u8 *actor) {\n    u8 *descriptor = *(u8 **)(actor + 0x144);\n    u8 *cursor;\n    s32 index;\n    s32 resourceCount;\n    s32 rawCount;\n\n    if (descriptor != NULL) {\n        rawCount = descriptor[0x2F];\n        cursor = actor;\n        resourceCount = rawCount;\n        if (rawCount == 0) {\n            resourceCount = actor[0x127] == 0 ? 5 : 3;\n        }\n        index = 0;\n        while (index <= D_80082FA0) {\n            *(u8 **)(cursor + 0x304) = func_1515D480(resourceCount);\n            index++;\n            cursor += 4;\n        }\n        if (*(u32 *)(actor + index * 4 + 0x300) != 0) {\n            actor[0x301] = resourceCount;\n        }\n        *(u8 **)(actor + 0x314) = func_1515D440();\n    }\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Actor resource allocation owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=212 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor resource body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150832AC() {\n    return 0;\n}':raise ValueError('Actor resource placeholder changed')
    before=before.replace('extern s32 D_80082FA0;\n','').replace('u32 func_1515D480(s32);\n','').replace('u32 func_1515D440(void);\n','')
    before=before.replace('*(u32 *)(cursor + 0x304) = func_1515D480','*(u8 **)(cursor + 0x304) = func_1515D480').replace('*(u32 *)(created + 0x314) = func_1515D440','*(u8 **)(created + 0x314) = func_1515D440')
    start,end=function_span(before,FUNCTION)
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor resource allocation snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor resource allocation frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor resource allocation predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor resource allocation live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Actor resource allocation named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Actor resource allocation symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Actor resource allocation metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor resource allocation frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor resource allocation original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor resource allocation strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor resource allocation named definitions changed')

NEW_GUARDS=[{'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x02C', 'expected': '0x50600022', 'replacement': '0x50600023', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x034', 'expected': '0x9073002F', 'replacement': '0x9064002F', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x038', 'expected': '0x02808825', 'replacement': '0x02808025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x03C', 'expected': '0x56600008', 'replacement': '0x14800008', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x040', 'expected': '0x8E4F0000', 'replacement': '0x00809825', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x048', 'expected': '0x24130003', 'replacement': '0x15C00003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x04C', 'expected': '0x15C00003', 'replacement': '0x00000000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x050', 'expected': '0x00000000', 'replacement': '0x10000003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x054', 'expected': '0x10000001', 'replacement': '0x24130005', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x058', 'expected': '0x24130005', 'replacement': '0x10000001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '0x24130003', 'insert_after_relocations': '-', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x060', 'expected': '0x00008025', 'replacement': '0x00008825', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x068', 'expected': '0x0010C880', 'replacement': '0x0011C880', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x074', 'expected': '0xAE220304', 'replacement': '0xAE020304', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x07C', 'expected': '0x26100001', 'replacement': '0x26310001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x080', 'expected': '0x26310004', 'replacement': '0x26100004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x084', 'expected': '0x0310082A', 'replacement': '0x0311082A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x090', 'expected': '0x0010C880', 'replacement': '0x0011C880', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_AEB40', 'function': 'func_150832AC', 'offset': '0x094', 'expected': '0x03344021', 'replacement': '0x02994021', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize actor resource count CFG and closed register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!='fdc175af1f717d9a7502ce5bacd8969decd21ef2739c9d9e291136c54406bfcc':raise ValueError('Inherited guards changed')
    return before+b'generated_AEB40,func_150832AC,0x02C,0x50600022,0x50600023,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x034,0x9073002F,0x9064002F,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x038,0x02808825,0x02808025,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x03C,0x56600008,0x14800008,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x040,0x8E4F0000,0x00809825,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x048,0x24130003,0x15C00003,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x04C,0x15C00003,0x00000000,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x050,0x00000000,0x10000003,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x054,0x10000001,0x24130005,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x058,0x24130005,0x10000001,-,-,Normalize actor resource count CFG and closed register allocation,0x24130003,-,false\r\ngenerated_AEB40,func_150832AC,0x060,0x00008025,0x00008825,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x068,0x0010C880,0x0011C880,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x074,0xAE220304,0xAE020304,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x07C,0x26100001,0x26310001,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x080,0x26310004,0x26100004,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x084,0x0310082A,0x0311082A,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x090,0x0010C880,0x0011C880,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\ngenerated_AEB40,func_150832AC,0x094,0x03344021,0x02994021,-,-,Normalize actor resource count CFG and closed register allocation,,,false\r\n'





def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray();relocations={};patches={int(x['offset'],0):x for x in NEW_GUARDS}
    parse=lambda s:[]if not s or s=='-'else[tuple(v.split(':',1))for v in s.split(';')]
    for at in range(0,len(raw),4):
        word=struct.unpack_from('>I',raw,at)[0];rels=bindings.get(at,[]);row=patches.get(at)
        if row:
            if word!=int(row['expected'],0)or rels!=parse(row['expected_relocations']):raise ValueError('Actor resource preimage changed')
            word=int(row['replacement'],0);rels=parse(row['replacement_relocations'])
        if rels:relocations[len(result)]=rels
        result.extend(struct.pack('>I',word))
        if row and row['insert_after']:
            extra=parse(row['insert_after_relocations'])
            if extra:relocations[len(result)]=extra
            result.extend(struct.pack('>I',int(row['insert_after'],0)))
    if len(result)!=216 or sha(result)!='7345ae5cbe1f558ae8b3e3f1bfeb695282b572b3f02a3904164839aee3276f5f'or relocations!=ORIGINAL_BINDINGS:raise ValueError('Actor resource normalized body/bindings changed')
    return bytes(result),relocations



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150832AC.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_AEB40.c', 'make-shadow/src/game/generated_AEB40.c.o', 'make-shadow/src/game/generated_AEB40.c.o.compact', 'make-shadow/src/game/generated_AEB40.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor resource allocation artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor resource allocation artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor resource allocation raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor resource allocation evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor resource allocation Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_AEB40.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor resource allocation Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=18 or q['exclusions']!=0:raise ValueError('Actor resource allocation private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor resource allocation changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor resource allocation protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,compiler_words=53,frame=48,alignment_words=0,slot_words=54,strict_first_link_reproduced=True,guards=18,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
