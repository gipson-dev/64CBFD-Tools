"""Dependency activation: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1509CCF4','generated_C9EC0'
ENTRY,ROM,BODY,SIZE=0x1509CCF4,0xCA1A4,232,232
SOURCE='conker/src/game/generated_C9EC0.c'
OBJECT='conker/build/src/game/generated_C9EC0.c.o'
ASM='conker/asm/C9EC0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-dependency-activation-1509CCF4-match'
RODATA_SYMBOL=None
RAW_SHA='97aba6f36d0a65865b41f7f598b96293f2908ce509a63d0cd74da5c8f2a69a5d'
SNAPSHOT_SHA='462033ee12a6abf21f20627393e54a18972c69e19ac5790379a8c37eb7005369'
BEFORE_ELF_SHA='f5e0295c5f8b0776043931231e065492bd3178795224a5815ccc64a633201b7a'
TRUTH_SHA='92734e6f13fe7a9d501dd3e90c8bd91402c27ed4f35b92b00e1e4b51c30dcbc6'
BINDINGS={52: [('R_MIPS_HI16', 'D_80087440')], 60: [('R_MIPS_LO16', 'D_80087440')], 64: [('R_MIPS_HI16', 'D_800D2E70')], 76: [('R_MIPS_LO16', 'D_800D2E70')], 92: [('R_MIPS_HI16', 'D_800D2E4C')], 96: [('R_MIPS_LO16', 'D_800D2E4C')], 160: [('R_MIPS_26', 'func_1509CCB4')]}
ORIGINAL_BINDINGS={52: [('R_MIPS_HI16', 'D_80087440')], 60: [('R_MIPS_LO16', 'D_80087440')], 64: [('R_MIPS_HI16', 'D_800D2E70')], 76: [('R_MIPS_LO16', 'D_800D2E70')], 92: [('R_MIPS_HI16', 'D_800D2E4C')], 96: [('R_MIPS_LO16', 'D_800D2E4C')], 160: [('R_MIPS_26', 'func_1509CCB4')]}
HEADERS='#include <ultra64.h>\ntypedef struct {u16 *entries;u8 reserved[16];} DependencyActivationRow;\nextern DependencyActivationRow D_80087440[];\nextern u8 *D_800D2E4C;\nextern u8 D_800D2E70[];\nvoid func_1509CCB4(s32);\n'
DECLARATIONS=''
SELECTED='/* Mark every listed dependency active and count newly activated callbacks. */\ns32 func_1509CCF4(s32 index) {\n    u16 *entry = D_80087440[index].entries;\n    s32 resource;\n    s32 count = 0;\n    if ((resource = *entry) != 0xFFFF) {\n        do {\n            D_800D2E4C[resource >> 3] |= 1 << (resource & 7);\n            if (D_800D2E70[*entry] != 3) {\n                D_800D2E70[*entry] = 3;\n                func_1509CCB4(*entry);\n                count++;\n            }\n            resource = *++entry;\n        } while (resource != 0xFFFF);\n    }\n    return count;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected dependency-activation owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Dependency activation body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_1509CCF4() {\n    return 0;\n}':raise ValueError('Dependency activation placeholder changed')
    declarations=HEADERS.replace('#include <ultra64.h>\n','',1)
    return before[:a]+declarations+SELECTED.rstrip()+before[b:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Dependency activation snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Dependency activation frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Dependency activation predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Dependency activation live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Dependency activation named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Dependency activation symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Dependency activation metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Dependency activation frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Dependency activation original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Dependency activation strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Dependency activation named definitions changed')

NEW_GUARDS=[{'filename': 'generated_C9EC0', 'function': 'func_1509CCF4', 'offset': '0x054', 'expected': '0x10760019', 'replacement': '0x12C30019', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Preserve retail commutative equality-branch operand order', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_C9EC0', 'function': 'func_1509CCF4', 'offset': '0x0B4', 'expected': '0x5476FFEC', 'replacement': '0x56C3FFEC', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Preserve retail commutative equality-branch operand order', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited dependency-activation guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Dependency-activation guard already present')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\n').writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    from tools.pad_generated_object import parse_relocation_spec
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Dependency-activation normalization scope changed')
    checked_payload(raw,bindings);words=list(struct.unpack('>58I',raw));relocations={at:list(items)for at,items in bindings.items()}
    for row in NEW_GUARDS:
        at=int(row['offset'],0);expected=parse_relocation_spec(row['expected_relocations']);replacement=parse_relocation_spec(row['replacement_relocations'])
        if words[at//4]!=int(row['expected'],0) or relocations.get(at,[])!=expected:raise ValueError('Dependency-activation guard preimage changed')
        words[at//4]=int(row['replacement'],0)
        if replacement:relocations[at]=replacement
        else:relocations.pop(at,None)
    result=struct.pack('>58I',*words)
    if sha(result)!='c384d76ab11f195a41004bccd2d01c156f84f83b0b6689fc9dea949a1603c4dd' or relocations!=ORIGINAL_BINDINGS:raise ValueError('Dependency-activation normalized payload changed')
    return result,relocations


ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1509CCF4.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_C9EC0.c.o', 'make-shadow/src/game/generated_C9EC0.c.o.compact', 'make-shadow/src/game/generated_C9EC0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Dependency activation artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Dependency activation artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Dependency activation raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Dependency activation evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Dependency activation Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_C9EC0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Dependency activation Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Dependency activation private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Dependency activation changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Dependency activation protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=58,frame=56,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='c2215195abbf133bcf3ead6e078c7b6b00d128c41733853b40d7f03121590f94'
