"""Script sorted insertion: semantic C, checked normalization and literal image audit."""
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
    if asm.name!='func_1509B810.s'or filename!='game_C8950':raise ValueError('Script-lookup padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER=('func_1509B810', 'game_C8950')
ENTRY,ROM,BODY,SIZE=(352958480, 822464, 236, 236)
SOURCE='conker/src/game_C8950.c'
OBJECT='conker/build/src/game_C8950.c.o'
ASM='conker/asm/nonmatchings/game_C8950/func_1509B810.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-script-sorted-insert-1509B810-match'
RODATA_SYMBOL=None
RAW_SHA='faf3c39355c34ccdb6e403cf7ca7ef36440c73f000b74052e05869cf9ea05a40'
SNAPSHOT_SHA='c48795ef9e9d7972ecae67ad44e3601f5cc0f854192b68bcbc14897276ffdedb'
BEFORE_ELF_SHA='f3f2bcd185eea3d186342924109c3599b0cd83704b48aef6c1ae749c613c6b8c'
TRUTH_SHA='ceb54f06386307b05ca7caed0a033b2b2aa390d6683eafb319c0e8ccb2407651'
BINDINGS={0: [('R_MIPS_HI16', 'D_800D2F48')], 12: [('R_MIPS_LO16', 'D_800D2F48')]}
ORIGINAL_BINDINGS={0: [('R_MIPS_HI16', 'D_800D2F48')], 12: [('R_MIPS_LO16', 'D_800D2F48')]}
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n\nvoid *func_1502B5C8(s32 *size, u32 depth, ...);\n\ntypedef struct ScriptNodeC8950 {\n    u16 kind;\n    u8 padding[0x16];\n    struct ScriptNodeC8950 *next;\n    struct ScriptNodeC8950 *prev;\n} ScriptNodeC8950;\ntypedef struct {\n    u16 length;\n    u16 padding;\n    ScriptNodeC8950 *unk4;\n    ScriptNodeC8950 *unk8;\n} ScriptListC8950;\n#define SCRIPT_LIST_C8950 (*(ScriptListC8950 *)&D_800D2F48)\n\n'
DECLARATIONS=''
SELECTED='/* Insert by the low ten kind bits, scanning backward from the script-list tail. */\nvoid func_1509B810(ScriptNodeC8950 *node) {\n    s32 length;\n    ScriptNodeC8950 *cursor;\n    ScriptNodeC8950 *tail;\n    s32 key;\n    s32 count;\n    s32 mask = 0xFFFF03FF;\n\n    cursor = SCRIPT_LIST_C8950.unk8;\n    tail = cursor;\n    key = node->kind & mask;\n    length = SCRIPT_LIST_C8950.length;\n    if (length == 0) {\n        SCRIPT_LIST_C8950.unk4 = node;\n        SCRIPT_LIST_C8950.unk8 = node;\n        node->next = NULL;\n        node->prev = NULL;\n        SCRIPT_LIST_C8950.length++;\n        return;\n    }\n    if (length > 0) {\n        count = 0;\n        do {\n            count++;\n            if ((cursor->kind & mask) >= key) {\n                goto next_node;\n            }\n            {\n                if (cursor == tail) {\n                    node->prev = cursor;\n                    node->next = NULL;\n                    cursor->next = node;\n                    SCRIPT_LIST_C8950.unk8 = node;\n                    SCRIPT_LIST_C8950.length++;\n                    return;\n                }\n                node->prev = cursor;\n                node->next = cursor->next;\n                cursor->next->prev = node;\n                cursor->next = node;\n                SCRIPT_LIST_C8950.length++;\n                return;\n            }\nnext_node:\n            cursor = cursor->prev;\n        } while ((count < length) != 0);\n    }\n    cursor = SCRIPT_LIST_C8950.unk4;\n    SCRIPT_LIST_C8950.unk4 = node;\n    node->prev = NULL;\n    node->next = cursor;\n    cursor->prev = node;\n    SCRIPT_LIST_C8950.length++;\n}\n'

def check_owner_diagnostics(text):
    norm=lambda t:re.sub(r'build/[^,]+, line [0-9]+','<owner>',t)
    frozen=(Path.cwd()/BUILD/'before-owner-diagnostics.txt').read_text()
    if norm(text)!=norm(frozen) or text.count('Warning')!=3:raise ValueError('Script insertion inherited owner diagnostics changed')
    return 3




sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Script sorted insertion body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_1509B810() {\n    return 0;\n}':raise ValueError('Script insertion placeholder changed')
    after=before[:a]+SELECTED.rstrip()+before[b:]
    return after.replace('s32 func_1509B810();','void func_1509B810(ScriptNodeC8950 *node);',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_C8950/func_1509B810.s. */\n','',1)





def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Script sorted insertion snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Script sorted insertion frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Script sorted insertion predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Script sorted insertion live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Script sorted insertion named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Script sorted insertion symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Script sorted insertion metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Script sorted insertion frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Script sorted insertion original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Script sorted insertion strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Script sorted insertion named definitions changed')

NEW_GUARDS=[{'filename': 'game_C8950', 'function': 'func_1509B810', 'offset': '0x014', 'expected': '0x8D020008', 'replacement': '0x8D030008', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail snapshot, loop predicate and final increment temporaries', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_C8950', 'function': 'func_1509B810', 'offset': '0x01C', 'expected': '0x00401825', 'replacement': '0x00601025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail snapshot, loop predicate and final increment temporaries', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_C8950', 'function': 'func_1509B810', 'offset': '0x064', 'expected': '0x00E6C82A', 'replacement': '0x00E6082A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail snapshot, loop predicate and final increment temporaries', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_C8950', 'function': 'func_1509B810', 'offset': '0x0B8', 'expected': '0x00E6C82A', 'replacement': '0x00E6082A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail snapshot, loop predicate and final increment temporaries', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_C8950', 'function': 'func_1509B810', 'offset': '0x0BC', 'expected': '0x1720FFE4', 'replacement': '0x1420FFE4', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail snapshot, loop predicate and final increment temporaries', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_C8950', 'function': 'func_1509B810', 'offset': '0x0D8', 'expected': '0x950A0000', 'replacement': '0x95190000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail snapshot, loop predicate and final increment temporaries', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_C8950', 'function': 'func_1509B810', 'offset': '0x0DC', 'expected': '0x254B0001', 'replacement': '0x272A0001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail snapshot, loop predicate and final increment temporaries', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_C8950', 'function': 'func_1509B810', 'offset': '0x0E0', 'expected': '0xA50B0000', 'replacement': '0xA50A0000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail snapshot, loop predicate and final increment temporaries', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited script sorted insertion guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Script-lookup guard already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Script insertion normalization scope changed')
    checked_payload(raw,bindings);words=list(struct.unpack('>59I',raw))
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if at in bindings or words[at//4]!=int(row['expected'],0):raise ValueError('Script insertion expected preimage changed')
        words[at//4]=int(row['replacement'],0)
    result=struct.pack('>59I',*words)
    if sha(result)!=NORMALIZED_SHA or bindings!=ORIGINAL_BINDINGS:raise ValueError('Script insertion normalized bytes/bindings changed')
    return result,bindings



NORMALIZED_SHA='62a739afc79cd942a72b271ba64db23e977d9314025a3642878d83af37736284'

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1509B810.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_C8950.c.o', 'make-shadow/src/game_C8950.c.o.compact', 'make-shadow/src/game_C8950.c.o.padded.s', 'make-shadow/src/game_C8950.c')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Script sorted insertion artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Script sorted insertion artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Script sorted insertion raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Script sorted insertion evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Script sorted insertion Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_C8950.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Script sorted insertion Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=8 or q['exclusions']!=0:raise ValueError('Script sorted insertion private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Script sorted insertion changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Script sorted insertion protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=57,frame=0,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=8,insertions=0,omissions=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='cb1cc89f318ba1aa37ff543479191c2525c17f6de79d6813e5441bc60ec835c4'
