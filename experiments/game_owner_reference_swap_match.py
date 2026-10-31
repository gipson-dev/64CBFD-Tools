"""Owner reference swap: semantic C, checked normalization and literal image audit."""
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
    if asm.name!='func_15161F4C.s'or filename!='game_18D770':raise ValueError('Reference-command padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15161F4C','game_18D770'
ENTRY,ROM,BODY,SIZE=0x15161F4C,0x18F3FC,232,232
SOURCE='conker/src/game_18D770.c'
OBJECT='conker/build/src/game_18D770.c.o'
ASM='conker/asm/nonmatchings/game_18D770/func_15161F4C.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-owner-reference-swap-15161F4C-match'
RODATA_SYMBOL=None
RAW_SHA='5e1948a8dc4f67ad4d73606d5f76cc5e5b32f66cd45f17f6e60b284eae44996e'
SNAPSHOT_SHA='1719407b62b258cdcf1dda676c554e863eed1e6c71d3a20210c8525921b1f822'
BEFORE_ELF_SHA='8de49d6bdff7a6e38fb3a06e66840cdb2b84ee8c0fa5a6ab1a7f77e922a20977'
TRUTH_SHA='3cd4f6d538ac8a3bb8870307ab52576543ff9410414430659536ea92d0b9822f'
BINDINGS={80: [('R_MIPS_26', 'func_1516972C')], 180: [('R_MIPS_HI16', 'D_8008B358')], 192: [('R_MIPS_LO16', 'D_8008B358')]}
ORIGINAL_BINDINGS={80: [('R_MIPS_26', 'func_1516972C')], 184: [('R_MIPS_HI16', 'D_8008B358')], 196: [('R_MIPS_LO16', 'D_8008B358')]}
HEADERS='#include <ultra64.h>\ntypedef struct {void *reference;u8 unique_id;u8 callback;} ReferencePayload;\ntypedef struct {u8 pad0[0x18];ReferencePayload payload;} ReferenceRecord;\ntypedef union {\n struct {void *reference;u8 unique_id;} single;\n struct {void *first;void *second;u8 first_id;u8 second_id;} swap;\n} ReferenceCommand;\nvoid func_1516972C(void *);\nextern void (*D_8008B358[])(ReferenceRecord *, const ReferenceCommand *, u8);\n'
DECLARATIONS=''
SELECTED='/* Remove a matching reference, replace either side of a pair, then run its callback. */\nvoid func_15161F4C(ReferenceRecord *record, const ReferenceCommand *command, u8 mode) {\n ReferencePayload *payload = &record->payload;\n if (mode == 0) {\n  if (command->single.reference == payload->reference || command->single.unique_id == payload->unique_id) {\n   func_1516972C((void *)record);\n  }\n } else if (mode == 0x2D) {\n  if (payload->reference == command->swap.first) {\n   payload->reference = command->swap.second;\n   payload->unique_id = command->swap.second_id;\n  } else if (payload->reference == command->swap.second) {\n   payload->reference = command->swap.first;\n   payload->unique_id = command->swap.first_id;\n  }\n }\n if (D_8008B358[payload->callback] != NULL) {\n  D_8008B358[payload->callback](record, command, mode);\n }\n}\n'

def check_owner_diagnostics(text):
    normalized=re.sub(r'build/[^,]+, line [0-9]+','<owner>',text)
    if hashlib.sha256(normalized.encode()).hexdigest()!='06dbe20054aed9a29572ec2520f9a46ce1bf82d027fb85f9fa0edc0d0a3bbee7':raise ValueError('Inherited reference-owner diagnostics changed')
    return 48


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=228 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner reference swap body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_15161F4C() {\n    return 0;\n}':raise ValueError('Reference-command placeholder changed')
    declarations=HEADERS.replace('#include <ultra64.h>\n','',1).replace('void func_1516972C(void *);\n','',1)
    after=before[:a]+declarations+SELECTED.rstrip()+before[b:]
    if after.count('s32 func_15161F4C();')!=1:raise ValueError('Reference-command placeholder prototype changed')
    return after.replace('s32 func_15161F4C();\n','',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_18D770/func_15161F4C.s. */\n','',1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner reference swap snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner reference swap frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner reference swap predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner reference swap live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Owner reference swap named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Owner reference swap symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Owner reference swap metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner reference swap frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner reference swap original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner reference swap strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner reference swap named definitions changed')

NEW_GUARDS=[{'filename': 'game_18D770', 'function': 'func_15161F4C', 'offset': '0x018', 'expected': '0x14C00013', 'replacement': '0x14C00014', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore reference-command owner reload and callback-selector branch-delay placement', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_18D770', 'function': 'func_15161F4C', 'offset': '0x040', 'expected': '0x5728001C', 'replacement': '0x5728001D', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore reference-command owner reload and callback-selector branch-delay placement', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_18D770', 'function': 'func_15161F4C', 'offset': '0x060', 'expected': '0x10000013', 'replacement': '0x8FA70018', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore reference-command owner reload and callback-selector branch-delay placement', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_18D770', 'function': 'func_15161F4C', 'offset': '0x064', 'expected': '0x8FA70018', 'replacement': '0x10000014', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore reference-command owner reload and callback-selector branch-delay placement', 'insert_after': '0x90ED001D', 'insert_after_relocations': '-', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited reference-command guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Reference-command guard already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Reference-command normalization scope changed')
    checked_payload(raw,bindings);words=struct.unpack('>57I',raw);rows={int(r['offset'],0):r for r in NEW_GUARDS};out=[];rs={}
    for i,word in enumerate(words):
        at=i*4;row=rows.get(at)
        if at in bindings:rs[len(out)*4]=bindings[at]
        if row:
            if word!=int(row['expected'],0)or at in bindings:raise ValueError('Reference-command expected word/binding changed')
            word=int(row['replacement'],0)
        out.append(word)
        if row and row['insert_after']:out.append(int(row['insert_after'],0))
    result=struct.pack('>58I',*out)
    if sha(result)!='921a2f2fca45458f37c561a55766de7ed573ee308498d66b09f5659b560c7cee'or rs!=ORIGINAL_BINDINGS:raise ValueError('Reference-command normalized bytes/bindings changed')
    return result,rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15161F4C.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_18D770.c.o', 'make-shadow/src/game_18D770.c.o.compact', 'make-shadow/src/game_18D770.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner reference swap artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner reference swap artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner reference swap raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner reference swap evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner reference swap Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_18D770.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner reference swap Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=4 or q['exclusions']!=0:raise ValueError('Owner reference swap private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner reference swap changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner reference swap protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=57,frame=24,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=4,insertions=1,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='aed0e4cd810ec80495d0ae68c91267510384590c4c2f64df642ba085c61aed7f'
