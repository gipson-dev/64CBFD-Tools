"""Save checksum submission: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
import tools.pad_generated_object as _pad
sys.modules.setdefault('pad_generated_object',_pad)
from tools.pad_c_object import emit_padded_assembly as _emit
def emit_padded_assembly(obj,asm,filename,word_patches_path):
    asm=Path(asm)
    if asm.name!='func_15007360.s'or filename!='game_33990':raise ValueError('Save checksum padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15007360','game_33990'
ENTRY,ROM,BODY,SIZE=0x15007360,0x34810,224,224
SOURCE='conker/src/game_33990.c'
OBJECT='conker/build/src/game_33990.c.o'
ASM='conker/asm/nonmatchings/game_33990/func_15007360.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-save-checksum-submit-15007360-match'
RODATA_SYMBOL=None
RAW_SHA='b4633c45e22edea4384385bff9d378190669c77fa8086914cc5a1602c84cb4b8'
SNAPSHOT_SHA='4edd6ed813514609170952dd988ee25537c2f4dabda144d1c2e9cc54e064563b'
BEFORE_ELF_SHA='81837f4f25a6eb7560053415605197f957b3ed3cdd70423729891547536b7334'
TRUTH_SHA='dbed982f5e39ef09cf4a39bf885eace6bdaf257debc57284e8a6e99f40af41ea'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE2F2')], 12: [('R_MIPS_LO16', 'D_800BE2F2')], 16: [('R_MIPS_HI16', 'D_800BE2F3')], 20: [('R_MIPS_LO16', 'D_800BE2F3')], 44: [('R_MIPS_HI16', 'D_800BE2F0')], 52: [('R_MIPS_LO16', 'D_800BE2F0')], 160: [('R_MIPS_HI16', 'D_800BE2F0')], 164: [('R_MIPS_LO16', 'D_800BE2F0')], 172: [('R_MIPS_HI16', 'D_8002AC5C')], 176: [('R_MIPS_LO16', 'D_8002AC5C')], 180: [('R_MIPS_HI16', 'D_800BE900')], 184: [('R_MIPS_LO16', 'D_800BE900')], 196: [('R_MIPS_26', 'func_151DCEF0')]}
ORIGINAL_BINDINGS={8: [('R_MIPS_HI16', 'D_800BE2F2')], 12: [('R_MIPS_LO16', 'D_800BE2F2')], 16: [('R_MIPS_HI16', 'D_800BE2F3')], 20: [('R_MIPS_LO16', 'D_800BE2F3')], 44: [('R_MIPS_HI16', 'D_800BE2F4')], 48: [('R_MIPS_LO16', 'D_800BE2F4')], 160: [('R_MIPS_HI16', 'D_800BE2F0')], 164: [('R_MIPS_LO16', 'D_800BE2F0')], 172: [('R_MIPS_HI16', 'D_8002AC5C')], 176: [('R_MIPS_LO16', 'D_8002AC5C')], 180: [('R_MIPS_HI16', 'D_800BE900')], 184: [('R_MIPS_LO16', 'D_800BE900')], 196: [('R_MIPS_26', 'func_151DCEF0')]}
HEADERS='#include <ultra64.h>\ntypedef union { u16 checksum; u8 bytes[0x70]; } SaveBlock33990;\nextern SaveBlock33990 D_800BE2F0;\nextern u8 D_800BE2F2;\nextern u8 D_800BE2F3;\nextern u8 D_8002AC5C;\nextern OSMesgQueue D_800BE900;\ns32 func_151DCEF0(OSMesgQueue *, s32, void *, s32);\n\n'
DECLARATIONS='typedef union { u16 checksum; u8 bytes[0x70]; } SaveBlock33990;\nextern SaveBlock33990 D_800BE2F0;\nextern u8 D_800BE2F2;\nextern u8 D_800BE2F3;\nextern u8 D_8002AC5C;\nextern OSMesgQueue D_800BE900;\ns32 func_151DCEF0(OSMesgQueue *, s32, void *, s32);\n\n'
SELECTED='/* Recompute the weighted checksum and submit the save block when enabled. */\nvoid func_15007360(void) {\n    u16 checksum;\n    volatile s32 result;\n    s32 index;\n\n    checksum = D_800BE2F2;\n    checksum = (checksum << 2) + 0xCC;\n    checksum += D_800BE2F3 << 3;\n    for (index = 4; index < 104; index++) {\n        checksum += D_800BE2F0.bytes[index] << (index & 3);\n    }\n    D_800BE2F0.checksum = checksum;\n    if (D_8002AC5C == 0) {\n        result = func_151DCEF0(&D_800BE900, 0x44, &D_800BE2F0, 0x70);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected save checksum submission diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Save checksum submission body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 start,end=function_span(before,FUNCTION)
 if before[start:end]!='s32 func_15007360() {\n    return 0;\n}':raise ValueError('Save checksum placeholder changed')
 after=before[:start]+SELECTED.rstrip()+before[end:]
 if after.count('s32 func_15007360();')!=1:raise ValueError('Save checksum prototype changed')
 return after.replace('s32 func_15007360();','void func_15007360(void);',1).replace('/* Generated placeholder declarations. */',DECLARATIONS+'/* Generated placeholder declarations. */',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_33990/func_15007360.s. */\n','',1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Save checksum submission snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Save checksum submission frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Save checksum submission predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Save checksum submission live input differs: '+name)
    return values

METADATA_GROUPS=((2738052, ('D_800BE2F3', 'func_151BD750'), (1, 0)), (2841364, ('func_151E5034', 'D_8009EDC4'), (1, 0)), (2935172, ('D_800BE2F0', 'D_800BE6E0'), (1, 0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Save checksum submission named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Save checksum submission symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Save checksum submission metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Save checksum submission frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Save checksum submission original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Save checksum submission strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Save checksum submission named definitions changed')

NEW_GUARDS=[{'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x2c', 'expected': '0x3C040000', 'replacement': '0x3C040000', 'expected_relocations': 'R_MIPS_HI16:D_800BE2F0', 'replacement_relocations': 'R_MIPS_HI16:D_800BE2F4', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x30', 'expected': '0x01001025', 'replacement': '0x24840000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800BE2F4', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x34', 'expected': '0x24840004', 'replacement': '0x01001025', 'expected_relocations': 'R_MIPS_LO16:D_800BE2F0', 'replacement_relocations': '-', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x48', 'expected': '0x246E0001', 'replacement': '0x306A0003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x4c', 'expected': '0x306A0003', 'replacement': '0x246E0001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x64', 'expected': '0x24690002', 'replacement': '0x004B6021', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x68', 'expected': '0x004B6021', 'replacement': '0x24690002', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x6c', 'expected': '0x0198C821', 'replacement': '0x312A0003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_15007360', 'offset': '0x70', 'expected': '0x312A0003', 'replacement': '0x0198C821', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed checksum loop schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited group guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Save checksum scope changed')
 checked_payload(raw,bindings);result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for row in NEW_GUARDS:
  at=int(row['offset'],16)
  if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],16):raise ValueError('Save checksum preimage changed')
  expected=';'.join(k+':'+s for k,s in rs.get(at,[]))or'-'
  if expected!=row['expected_relocations']:raise ValueError('Save checksum binding changed')
  struct.pack_into('>I',result,at,int(row['replacement'],16));rs.pop(at,None)
  if row['replacement_relocations']!='-':rs[at]=[tuple(x.split(':',1))for x in row['replacement_relocations'].split(';')]
 if sha(result)!='ad42d20c2b9adff81968ed407758c9c1fe8359d5a74c3b772668325d7269e51f'or rs!=ORIGINAL_BINDINGS:raise ValueError('Save checksum result changed')
 return bytes(result),rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15007360.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_33990.c.o', 'make-shadow/src/game_33990.c.o.compact', 'make-shadow/src/game_33990.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Save checksum submission artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save checksum submission artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save checksum submission raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Save checksum submission evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save checksum submission Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_33990.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Save checksum submission Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=9 or q['exclusions']!=0:raise ValueError('Save checksum submission private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Save checksum submission changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Save checksum submission protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=32,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=9,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='6c9db8a2745f65f7dcc9a014752df7bf92ec870ac121ea2cdd28fb4147b06f04'
