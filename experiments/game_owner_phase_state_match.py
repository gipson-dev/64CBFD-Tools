"""Owner phase state: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,csv,io
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15108C38','generated_135D00'
ENTRY,ROM,BODY,SIZE=(353406008, 1269992, 236, 236)
SOURCE='conker/src/game/generated_135D00.c'
OBJECT='conker/build/src/game/generated_135D00.c.o'
ASM='conker/asm/135D00.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-owner-phase-state-15108C38-match'
RODATA_SYMBOL=None
RAW_SHA='0bbad063ddad2f138c13f3c4c50ba5df443891b29b54cc7d616f78a1286e2be9'
SNAPSHOT_SHA='c32b09e3ea7d52b8e2660313549cbe7e7d9f6ad096dbdaf32553062e5b61b568'
BEFORE_ELF_SHA='e24ab1f1ea77c2912eda733e38ac9d2b2cbc648ba6ac8bf3bf5343267bedd3ec'
TRUTH_SHA='d5b248e9d2f80769026a02232b9533ccef7948e8f93aedc99cf5a0a72bad2801'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE9A4')], 12: [('R_MIPS_LO16', 'D_800BE9A4')], 28: [('R_MIPS_HI16', 'D_800A2480')], 32: [('R_MIPS_LO16', 'D_800A2480')], 44: [('R_MIPS_HI16', 'D_800A2484')], 80: [('R_MIPS_LO16', 'D_800A2484')], 96: [('R_MIPS_26', 'func_15144B68')], 108: [('R_MIPS_26', 'func_15144B68')], 120: [('R_MIPS_26', 'sinf')], 128: [('R_MIPS_HI16', 'D_800A2488')], 132: [('R_MIPS_LO16', 'D_800A2488')], 144: [('R_MIPS_26', 'sinf')], 152: [('R_MIPS_HI16', 'D_800A248C')], 156: [('R_MIPS_LO16', 'D_800A248C')], 168: [('R_MIPS_26', 'func_15108B80')], 176: [('R_MIPS_26', 'func_15108BC0')]}
ORIGINAL_BINDINGS={8: [('R_MIPS_HI16', 'D_800BE9A4')], 12: [('R_MIPS_LO16', 'D_800BE9A4')], 28: [('R_MIPS_HI16', 'D_800A2480')], 32: [('R_MIPS_LO16', 'D_800A2480')], 44: [('R_MIPS_HI16', 'D_800A2484')], 80: [('R_MIPS_LO16', 'D_800A2484')], 96: [('R_MIPS_26', 'func_15144B68')], 108: [('R_MIPS_26', 'func_15144B68')], 120: [('R_MIPS_26', 'sinf')], 128: [('R_MIPS_HI16', 'D_800A2488')], 132: [('R_MIPS_LO16', 'D_800A2488')], 144: [('R_MIPS_26', 'sinf')], 152: [('R_MIPS_HI16', 'D_800A248C')], 156: [('R_MIPS_LO16', 'D_800A248C')], 168: [('R_MIPS_26', 'func_15108B80')], 176: [('R_MIPS_26', 'func_15108BC0')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800BE9A4;\nextern f32 D_800A2480, D_800A2484, D_800A2488, D_800A248C;\nf32 func_15144B68(f32);\nf32 sinf(f32);\nvoid func_15108B80(u8 *);\nvoid func_15108BC0(u8 *);\n\n'
DECLARATIONS='extern f32 D_800A2480, D_800A2484, D_800A2488, D_800A248C;\n\n'
SELECTED='/* Advance the two phases and derive their sine-scaled offsets.\n * Refresh the owner timer and lookup value, then publish the live state mode and keep the callback active. */\ns32 func_15108C38(u8 *owner) {\n    f32 *delta = &D_800BE9A4;\n    f32 *state = (f32 *)(owner + *(s32 *)(owner + 0x50) + 0xF8);\n\n    state[2] += D_800A2480 * *delta;\n    state[3] += D_800A2484 * *delta;\n    state[2] = func_15144B68(state[2]);\n    state[3] = func_15144B68(state[3]);\n    state[0] = sinf(state[2]) * D_800A2488;\n    state[1] = sinf(state[3]) * D_800A248C;\n    func_15108B80(owner);\n    func_15108BC0(owner);\n    if (*((u8 *)state + 0x20) != 0) {\n        owner[0x12] = 4;\n    } else {\n        owner[0x12] = 2;\n    }\n    return 1;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected slot refresh diagnostics')
    return 0




sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner phase state body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15108C38() {\n    return 0;\n}':raise ValueError('Phase-state placeholder changed')
 return before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]







def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner phase state snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner phase state frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner phase state predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner phase state live input differs: '+name)
    return values

METADATA_GROUPS=((2736756, ('D_800A2480', 'D_800D2C28', 'D_8008FE20'), (1, 2, 0)), (2912100, ('.L15172474_game_data', 'D_8009E6C4'), (1, 0)), (2930948, ('func_151668B8', 'D_8009E6C0'), (1, 0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Owner phase state named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Owner phase state symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Owner phase state metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner phase state frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner phase state original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner phase state strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner phase state named definitions changed')

NEW_GUARDS=[{'filename': 'generated_135D00', 'function': 'func_15108C38', 'offset': '0x034', 'expected': '0x01D18021', 'replacement': '0x022E8021', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Preserve retail commutative owner-offset ADDU operand order', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited owner-phase-state guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Owner-matrix guards already present')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Owner phase state normalization scope changed')
 checked_payload(raw,bindings);words=list(struct.unpack('>59I',raw));result_bindings={at:list(rows)for at,rows in bindings.items()}
 encode=lambda rows:';'.join(kind+':'+symbol for kind,symbol in rows)if rows else '-'
 for row in NEW_GUARDS:
  at=int(row['offset'],0)
  if words[at//4]!=int(row['expected'],0)or encode(bindings.get(at,[]))!=row['expected_relocations']:raise ValueError('Owner phase state word/binding preimage changed')
  words[at//4]=int(row['replacement'],0);replacements=row['replacement_relocations']
  if replacements=='-':result_bindings.pop(at,None)
  else:result_bindings[at]=[tuple(item.split(':',1))for item in replacements.split(';')]
 result=struct.pack('>59I',*words)
 if sha(result)!=NORMALIZED_SHA or result_bindings!=ORIGINAL_BINDINGS:raise ValueError('Owner phase state normalized bytes/bindings changed')
 return result,result_bindings


ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15108C38.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_135D00.c.o', 'make-shadow/src/game/generated_135D00.c.o.compact', 'make-shadow/src/game/generated_135D00.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner phase state artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner phase state artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner phase state raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner phase state evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner phase state Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_135D00.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner phase state Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=1 or q['exclusions']!=0:raise ValueError('Owner phase state private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner phase state changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner phase state protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=32,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=1,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='c0ac0ea7d44ac6fb46585874ac7522ea4067ec290ac3b1005aa374b168cb0a7c'

NORMALIZED_SHA='d532cec1b69bbd25337e8fd5dcd483f4a17b686ccaaad893b098b6247c3ab223'


def schedule_proof(raw,bindings,truth,retail_bindings):
 checked_payload(raw,bindings);words=list(struct.unpack('>59I',raw));old=words[13];new=struct.unpack_from('>I',truth,52)[0]
 if old!=0x01D18021 or new!=0x022E8021 or bindings!=retail_bindings or 52 in bindings:raise ValueError('Owner-offset ADDU scope changed')
 if old&0xFC00FFFF!=new&0xFC00FFFF or(old>>21&31,old>>16&31)!=(new>>16&31,new>>21&31):raise ValueError('ADDU is not an exact operand swap')
 words[13]=new
 if struct.pack('>59I',*words)!=truth:raise ValueError('Other phase-state instruction changed')
 return dict(commutative_ADDU=True,word_index=13,raw_sources=['T6','S1'],retail_sources=['S1','T6'],destination='S0',opcode_immediate_and_all_bindings_preserved=True,all_other_words_identical=True)


CALLER=0x1513B798
