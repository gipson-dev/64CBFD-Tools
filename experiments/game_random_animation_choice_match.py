"""Random animation choice command: direct C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1506B634','game_981E0'
ENTRY,ROM,BODY,SIZE=0x1506B634,0x98AE4,268,268
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
ASM='conker/asm/nonmatchings/game_981E0/func_1506B634.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-random-animation-choice-1506B634-match'
RAW_SHA='9e0dc26802ab957becc320953a6acca8741e593e76b3f986e6728dec2ba520e4'
TRUTH_SHA='cb5f3b38a559e300f46002532eff2549d94b40df6e0f11bd4f3affb567729028'
BEFORE_ELF_SHA='880e6efb3a59c2d3b1d7d8af5f46ce08bcea6a9386940b1d9e8e14ac282b8793'
BINDINGS={12: [('R_MIPS_26', 'func_150ADA20')], 24: [('R_MIPS_HI16', 'D_800D154C')], 28: [('R_MIPS_LO16', 'D_800D154C')], 68: [('R_MIPS_HI16', 'D_800BE9F0')], 84: [('R_MIPS_LO16', 'D_800BE9F0')], 100: [('R_MIPS_HI16', 'D_80099ABC')], 124: [('R_MIPS_LO16', 'D_80099ABC')], 80: [('R_MIPS_HI16', 'D_80099AB4')], 140: [('R_MIPS_LO16', 'D_80099AB4')], 176: [('R_MIPS_HI16', 'D_800D1580')], 184: [('R_MIPS_LO16', 'D_800D1580')], 180: [('R_MIPS_26', 'func_150ADA20')], 196: [('R_MIPS_HI16', 'D_800D154C')], 200: [('R_MIPS_LO16', 'D_800D154C')], 216: [('R_MIPS_26', 'func_1506E8D8')], 224: [('R_MIPS_HI16', 'D_800D154C')], 228: [('R_MIPS_LO16', 'D_800D154C')], 232: [('R_MIPS_HI16', 'D_80099C38')], 236: [('R_MIPS_LO16', 'D_80099C38')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct127 *D_800D154C;\nextern s32 D_800D1580, D_800BE9F0;\nextern s16 D_80099AB4[], D_80099ABC[];\nextern f32 D_80099C38;\ns32 func_150ADA20(void);\nvoid func_1506E8D8(void);\n'
SELECTED='/* Select a packed byte animation entry and apply its special follow-up. */\nvoid func_1506B634(u8 choiceCount) {\n    u32 remainder;\n    u8 choice;\n    struct126 *state;\n\n    remainder = (u32)func_150ADA20() % choiceCount;\n    choice = (u8)remainder;\n    state = D_800D154C->unk31C;\n    if (state->unk16 != 0) {\n        if ((D_800BE9F0 == 0x29) && ((u8)remainder == 7)) {\n            choice = 0;\n        }\n        /* Both choice tables contain bytes despite their legacy s16 declarations. */\n        state->unkE = ((u8 *)D_80099ABC)[choice];\n    } else {\n        state->unkE = ((u8 *)D_80099AB4)[(u8)remainder];\n    }\n    if (D_800D154C->unk31C->unkE == 0xA7) {\n        D_800D1580 = 0xFF020144;\n        D_800D154C->unk31C->unkC = ((u32)func_150ADA20() % 3U) + 2;\n        func_1506E8D8();\n        D_800D154C->xz_velocity *= D_80099C38;\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Random animation choice payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='/* Non-matching C placeholders for asm/nonmatchings/game_981E0/func_1506B634.s. */\ns32 func_1506B634(s32 arg0) {\n    return 0;\n}'
 if before.count(old)!=1 or before.count('s32 func_1506B634(s32 arg0);')!=1:raise ValueError('Random animation placeholder changed')
 result=before.replace(old,SELECTED.rstrip(),1).replace('s32 func_1506B634(s32 arg0);','void func_1506B634(u8 choiceCount);',1)
 start=result.index('// NON-MATCHING: miles away\n// void func_1506B634(')
 end=result.index('\nvoid func_1506B740(void)',start)
 return result[:start]+result[end:]

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
 if a!=b:raise ValueError('Random animation choice owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Random animation choice predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,16):raise ValueError('Random animation choice predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)


SNAPSHOT_SHA='49da47d448ff2b9571781def8fad044f6f111a67ff93e2dfe018ad666772e6d3'
PREPARED_SHA='0c8e2e294fbe8662617a338b3b4ff046b912ed4a4df8fe66cdcafb1fd6882aac'
NEIGHBORS=327
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1506B634.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_981E0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'cached-state-negative.o')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Random animation choice input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Random animation choice frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Random animation choice preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Random animation choice evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Random animation choice prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==q['exclusions']==0):raise ValueError('Random animation choice preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Random animation choice literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Random animation choice named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Random animation choice live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Random animation choice linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Random animation choice protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=67,frame=24,alignment_words=0,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
