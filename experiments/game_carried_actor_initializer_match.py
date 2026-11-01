"""Carried actor initialization command: direct C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1507266C','game_981E0'
ENTRY,ROM,BODY,SIZE=0x1507266C,0x9FB1C,212,212
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
ASM='conker/asm/nonmatchings/game_981E0/func_1507266C.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-carried-actor-initialize-1507266C-match'
RAW_SHA='efe8d0924f16381ef4f55eae6199493c424f6156150c5a61e24575c71ec592d6'
TRUTH_SHA='01e4aa0033ae82b7d0ae40841c525e048eb95c8c82bac420184a2dc51b9c6534'
BEFORE_ELF_SHA='56dfb862d6a37ea40ec9e0bfdb47acc8a1d1faefbd4d69fdfa26afe27741e3d6'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE616')], 12: [('R_MIPS_LO16', 'D_800BE616')], 16: [('R_MIPS_HI16', 'D_800D154C')], 32: [('R_MIPS_LO16', 'D_800D154C')], 20: [('R_MIPS_HI16', 'D_800CC2D0')], 84: [('R_MIPS_LO16', 'D_800CC2D0')], 56: [('R_MIPS_HI16', 'D_800C3E78')], 64: [('R_MIPS_LO16', 'D_800C3E78')], 28: [('R_MIPS_HI16', 'D_800D154C')], 48: [('R_MIPS_LO16', 'D_800D154C')], 68: [('R_MIPS_HI16', 'D_800D1580')], 76: [('R_MIPS_LO16', 'D_800D1580')], 188: [('R_MIPS_26', 'func_151B5BA0')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[(76, 2353135616, 2353201152, 'R_MIPS_LO16:D_800D1580'), (104, 138243, 209923, '-'), (124, 2896363612, 2896560220, '-'), (152, 2694971954, 2695037490, '-')]
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct127 D_800CC2D0[26];\nextern struct127 *D_800D154C;\nextern u8 D_800BE616,D_800C3E78;\nextern s32 D_800D1580;\nvoid func_151B5BA0(struct127 *,struct127 *);\n'
SELECTED='/* Initialize the carried actor from the packed command, then notify its owner. */\nvoid func_1507266C(void) {\n    s32 parameter;\n    s32 command;\n    struct127 *carried;\n\n    if (D_800BE616 || D_800D154C->unk222) {\n        carried = &D_800CC2D0[D_800D154C->unk222];\n        parameter = D_800D1580 >> 16;\n        command = D_800D1580;\n        carried->unk65 = D_800C3E78 + 1;\n        carried->unk5C = parameter;\n        carried->unk101 = 4;\n        carried->stunned = 0;\n        carried->immune = 255;\n        carried->unk218 = 0;\n        carried->unkE4 = 0;\n        carried->unkE6 = 0;\n        carried->unk232 = command;\n        carried->unkEC = 1.0f;\n        carried->unkF0 = 1.0f;\n        carried->unkDC = 1.0f;\n        carried->unkE0 = 1.0f;\n        func_151B5BA0(&D_800CC2D0[D_800C3E78],carried);\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Carried actor initialization payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='/* Non-matching C placeholders for asm/nonmatchings/game_981E0/func_1507266C.s. */\n/* Note 454: original carried actor attachment/effect. */\n#pragma GLOBAL_ASM("asm/nonmatchings/game_981E0/func_1507266C.s")'
 if before.count(old)!=1 or before.count('s32 func_1507266C();')!=1:raise ValueError('Carried initializer assembly marker changed')
 declaration='void func_151B5BA0(struct127 *owner, struct127 *carried);\n'
 return before.replace(old,SELECTED.rstrip(),1).replace('s32 func_1507266C();','void func_1507266C(void);',1).replace('/* Generated placeholder declarations. */',declaration+'\n/* Generated placeholder declarations. */',1)

def proposed_guards(before):
 if b'game_981E0,func_1507266C,' in before:raise ValueError('Carried initializer guards already present')
 if not before.endswith(b'\n'):raise ValueError('Guard table lost final newline')
 newline='\r\n'if b'\r\n'in before else'\n'
 rows=[]
 for offset,expected,replacement,reloc in NEW_GUARDS:
  rows.append('game_981E0,func_1507266C,0x%X,0x%08X,0x%08X,%s,%s,Normalize closed carried initializer command register lifetimes,,,false'%(offset,expected,replacement,reloc,reloc))
 return before+(newline.join(rows)+newline).encode()

def progress_after(data):
 rows=data.splitlines(keepends=True);matches=0;out=[]
 for row in rows:
  if b',func_1507266C,'in row:
   assert row.rstrip(b'\r\n').endswith(b',asm'),row
   row=row.replace(b',asm',b',c');matches+=1
  out.append(row)
 if matches!=1:raise ValueError('Missing unique initializer inventory row')
 return b''.join(out)

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
 if a!=b:raise ValueError('Carried actor initialization owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Carried initializer predictor baseline changed')
 at=elf_slot_offset(before,ENTRY,SIZE)
 if before[at:at+SIZE]!=truth:raise ValueError('Prior assembly slot no longer exact')
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,BODY):raise ValueError('Carried initializer prior extent changed')
 return before # Assembly and qualified C have identical bytes and symbol extent.


SNAPSHOT_SHA='4cd3f9c34a9056d49472147e37c3a2dc7c6706534c3450e9c5e9c530c0dab975'
PREPARED_SHA='063d71b9c74561747af8c246b666cebd371916fb217cdd1a7b47b7794b903f63'
NEIGHBORS=327
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1507266C.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_981E0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Carried actor initialization input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Carried actor initialization frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Carried actor initialization preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Carried actor initialization evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Carried actor initialization prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==4 and q['exclusions']==0):raise ValueError('Carried actor initialization preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Carried actor initialization literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Carried actor initialization named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  for n in ('conker/progress.csv','conker/progress.game.csv'):changes[n]=progress_after(values[n])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Carried actor initialization live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[]:raise ValueError('Carried actor initialization linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Carried actor initialization protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=53,frame=24,alignment_words=0,guards=4,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
