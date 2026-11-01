"""Aligned zero tail guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1509B950','game_C8950'
ENTRY,ROM,BODY,SIZE=0x1509B950,0xC8E00,180,180
SOURCE='conker/src/game_C8950.c'
OBJECT='conker/build/src/game_C8950.c.o'
ASM='conker/asm/nonmatchings/game_C8950/func_1509B950.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-aligned-zero-tail-1509B950-match'
RAW_SHA='6c44e98a6f2f7f773f28487d8263edbd9291a9c75b057d03c359113d7db77f2a'
TRUTH_SHA='c9d4e9ce153fda6cb14c237561896c6c8a3f390219438e3c09de8ad74f059646'
BEFORE_ELF_SHA='56dfb862d6a37ea40ec9e0bfdb47acc8a1d1faefbd4d69fdfa26afe27741e3d6'
BINDINGS={92:[('R_MIPS_26','allocate_memory')],124:[('R_MIPS_26','bcopy')],140:[('R_MIPS_26','bzero')],148:[('R_MIPS_26','func_10004074')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[(40, 51335203, 51320867, '-'), (44, 4866081, 4407329, '-'), (48, 17373217, 17371169, '-'), (52, 33773601, 33708065, '-'), (60, 7104547, 5007395, '-'), (64, 2785214468, 2785148932, '-')]
HEADERS='#include <ultra64.h>\n#include "structs.h"\ns32 allocate_memory(s32,s32,s32,s32);\nvoid func_10004074(void *);\n'
SELECTED='/* Append a zeroed tail at the next eight-byte boundary and release the source.\n * Both alignments advance a full eight bytes when already aligned.\n * Keep header updates before allocation and reload fields after helper calls. */\nstruct248 *func_1509B950(struct248 *block) {\n    s32 alignmentPadding;\n    u32 tailOffset;\n    u32 newSize;\n    u32 tailSize;\n    struct248 *copy;\n\n    tailSize = block->unk6;\n    alignmentPadding = 8 - (((u32)block + block->unk4) & 7);\n    tailOffset = block->unk4 + alignmentPadding;\n    newSize = tailOffset + tailSize;\n    block->unk4 = newSize;\n    block->unkA = tailOffset;\n    block->unk4 = block->unk4 - (((u32)block + block->unk4) & 7) + 8;\n    copy = (struct248 *)allocate_memory(block->unk4, 255, 2, 0);\n    if (copy == NULL) {\n        for (;;) {}\n    }\n    bcopy(block, copy, block->unk4);\n    bzero((u8 *)copy + copy->unkA, copy->unk6);\n    func_10004074(block);\n    return copy;\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Aligned zero tail payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='/* Non-matching C placeholders for asm/nonmatchings/game_C8950/func_1509B950.s. */\ns32 func_1509B950(s32 arg0) {\n    return 0;\n}'
 declaration='s32 func_1509B950(s32 arg0);'
 if before.count(old)!=1 or before.count(declaration)!=1:raise ValueError('Zero tail placeholder changed')
 return before.replace(old,SELECTED.rstrip(),1).replace(declaration,'struct248 *func_1509B950(struct248 *block);',1).replace('/* Generated placeholder declarations. */','s32 allocate_memory(s32 size, s32 color, s32 side, s32 flags);\n\n/* Generated placeholder declarations. */',1)

def proposed_guards(before):
 if b'game_C8950,func_1509B950,' in before:raise ValueError('Aligned zero tail guards already present')
 if not before.endswith(b'\n'):raise ValueError('Guard table lost final newline')
 newline='\r\n'if b'\r\n'in before else'\n'
 rows=[]
 for offset,expected,replacement,reloc in NEW_GUARDS:
  rows.append('game_C8950,func_1509B950,0x%X,0x%08X,0x%08X,%s,%s,Normalize closed zero tail padding and size register lifetimes,,,false'%(offset,expected,replacement,reloc,reloc))
 return before+(newline.join(rows)+newline).encode()

def diagnostic_rows(text):
 rows=[]
 lines=text.splitlines()
 for i,line in enumerate(lines):
  match=re.match(r'cfe: Warning (\d+): .*?, line \d+: (.*)',line)
  if match:rows.append((match[1],match[2],lines[i+1].strip()))
  elif line.startswith('cfe:')and 'Warning'not in line:raise ValueError('Unexpected compiler diagnostic')
 return Counter(rows)
def check_owner_diagnostics(before,after):
 a,b=diagnostic_rows(before),diagnostic_rows(after)
 removed=Counter({('712','illegal combination of pointer and integer','func_1509B950(temp_v0);'):1})
 if a-b!=removed or b-a or sum(a.values())!=3 or sum(b.values())!=2:raise ValueError('Unexpected owner diagnostic change')
 return dict(before=3,after=2,removed_pointer_integer_argument_warning=1)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Zero tail predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,16):raise ValueError('Zero tail predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)

SNAPSHOT_SHA='a9c003893ddf5bba5232e90128c51da25c48dfb20937304c14ded70fd73d00fb'
PREPARED_SHA='ebbdc964a9885c0c26fa0f543ca7dc85a0c6fa69f9abb7b59cf3ec765c4bb340'
NEIGHBORS=16
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1509B950.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_C8950.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Aligned zero tail input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Aligned zero tail frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Aligned zero tail preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Aligned zero tail evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Aligned zero tail prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==6 and q['exclusions']==0):raise ValueError('Aligned zero tail preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Aligned zero tail literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Aligned zero tail named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Aligned zero tail live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Aligned zero tail linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Aligned zero tail protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=45,frame=32,alignment_words=0,guards=6,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
