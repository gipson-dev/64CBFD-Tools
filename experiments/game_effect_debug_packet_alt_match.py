"""Effect debug packet: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_151A0F28','generated_1CC440'
ENTRY,ROM,BODY,SIZE=0x151A0F28,0x1CE3D8,232,232
SOURCE='conker/src/game/generated_1CC440.c'
OBJECT='conker/build/src/game/generated_1CC440.c.o'
ASM='conker/asm/1CC440.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-effect-debug-packet-alt-151A0F28-match'
RODATA_SYMBOL=None
RAW_SHA='1c1536447faa7331fbfdf13d95aa8df10732abbc30097a419b40c5beeb158a5d'
SNAPSHOT_SHA='7e6123a860af312ccb17cc9d76a066317768fec6f0ccf79e13c8400e2ec28a55'
BEFORE_ELF_SHA='79792a1b649a3f08360fcfbc27dd4615c894f574f00c42b72cf29b18c7c44272'
TRUTH_SHA='2f6a29151377cf3001cf847b73236a8060b955b6b7a2d70803d578029bd902a1'
BINDINGS={20: [('R_MIPS_HI16', 'D_800A8D24')], 24: [('R_MIPS_LO16', 'D_800A8D24')], 208: [('R_MIPS_26', 'func_151A11CC')]}
ORIGINAL_BINDINGS={4: [('R_MIPS_HI16', 'D_800A8D24')], 8: [('R_MIPS_LO16', 'D_800A8D24')], 208: [('R_MIPS_26', 'func_151A11CC')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800A8D24;\nvoid func_151A11CC(f32, f32, f32, f32, f32, s32, s32, s32, s32, s32, f32, s32, s32, s32, s32, s32, s32, f32, s32, s32, s32, s32, s32, s32, s32, s32, u32, s32);\n'
DECLARATIONS=''
SELECTED='/* Submit the original fixed debug-display argument packet to its retail stub. */\nvoid func_151A0F28(f32 x, f32 y, f32 value, u8 variant, s32 flags) {\n    func_151A11CC(\n        x, y, value, 163.0f, D_800A8D24,\n        160, 75, 1055, 1270, 1, D_800A8D24,\n        135, 68, 1055, 1270, 2, 1, D_800A8D24,\n        70, 66, 1055, 1270, 7, 65, 4, 1, variant, flags);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected effect-debug owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Effect debug packet body/bindings changed')
    return raw,bindings

HELPER='void func_151A11CC(f32 arg0, f32 arg1, f32 arg2, f32 arg3, f32 arg4, s32 arg5, s32 arg6, s32 arg7, s32 arg8, s32 arg9, f32 arg10, s32 arg11, s32 arg12, s32 arg13, s32 arg14, s32 arg15, s32 arg16, f32 arg17, s32 arg18, s32 arg19, s32 arg20, s32 arg21, s32 arg22, s32 arg23, s32 arg24, s32 arg25, u32 arg26, s32 arg27) {\n}'

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_151A0F28() {\n    return 0;\n}':raise ValueError('Alternate packet placeholder changed')
    helper_start,helper_end=function_span(before,'func_151A11CC')
    if before[helper_start:helper_end]!=HELPER:raise ValueError('Qualified full helper signature changed')
    return before[:a]+'extern f32 D_800A8D24;\n'+SELECTED.rstrip()+before[b:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Effect debug packet snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Effect debug packet frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Effect debug packet predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Effect debug packet live input differs: '+name)
    return values

METADATA_GROUPS=((2834676, ('D_800A8D24', 'D_800A80A4', 'func_150F6850', 'D_80096174'), (1, 2, 3, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Effect debug packet named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Effect debug packet symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Effect debug packet metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Effect debug packet frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Effect debug packet original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Effect debug packet strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Effect debug packet named definitions changed')

NEW_GUARDS=[{'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x004', 'expected': '0xAFBF0074', 'replacement': '0x3C010000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_HI16:D_800A8D24', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x008', 'expected': '0xAFA60080', 'replacement': '0xC4200000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800A8D24', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x00C', 'expected': '0xAFA70084', 'replacement': '0xAFBF0074', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x010', 'expected': '0x30E400FF', 'replacement': '0xAFA60080', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x014', 'expected': '0x3C010000', 'replacement': '0xAFA70084', 'expected_relocations': 'R_MIPS_HI16:D_800A8D24', 'replacement_relocations': '-', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x018', 'expected': '0xC4200000', 'replacement': '0x30E400FF', 'expected_relocations': 'R_MIPS_LO16:D_800A8D24', 'replacement_relocations': '-', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x0C0', 'expected': '0xAFA40068', 'replacement': '0xE7A00010', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x0C4', 'expected': '0xE7A00010', 'replacement': '0xE7A00028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x0C8', 'expected': '0xE7A00028', 'replacement': '0xE7A00044', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1CC440', 'function': 'func_151A0F28', 'offset': '0x0CC', 'expected': '0xE7A00044', 'replacement': '0xAFA40068', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore independent debug constant-load and outgoing-stack-store scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited effect-debug guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Effect-debug guard already present')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\n').writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    from tools.pad_generated_object import parse_relocation_spec
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Effect-debug normalization scope changed')
    checked_payload(raw,bindings);words=list(struct.unpack('>58I',raw));relocations={at:list(items)for at,items in bindings.items()}
    for row in NEW_GUARDS:
        at=int(row['offset'],0);expected=parse_relocation_spec(row['expected_relocations']);replacement=parse_relocation_spec(row['replacement_relocations'])
        if words[at//4]!=int(row['expected'],0) or relocations.get(at,[])!=expected:raise ValueError('Effect-debug guard preimage changed')
        words[at//4]=int(row['replacement'],0)
        if replacement:relocations[at]=replacement
        else:relocations.pop(at,None)
    result=struct.pack('>58I',*words)
    if sha(result)!='bc71de128d113e00e32b916246e571e2743683ef4e3aff7c7923ee240f29c1e7' or relocations!=ORIGINAL_BINDINGS:raise ValueError('Effect-debug normalized payload changed')
    return result,relocations


ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151A0F28.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1CC440.c.o', 'make-shadow/src/game/generated_1CC440.c.o.compact', 'make-shadow/src/game/generated_1CC440.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Effect debug packet artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Effect debug packet artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Effect debug packet raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Effect debug packet evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Effect debug packet Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1CC440.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Effect debug packet Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=10 or q['exclusions']!=0:raise ValueError('Effect debug packet private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Effect debug packet changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Effect debug packet protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=58,frame=120,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=10,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='545f72af89f88c54a6b9011b687ab3f69ad61c49e62c81a6afd8adde795d7470'
