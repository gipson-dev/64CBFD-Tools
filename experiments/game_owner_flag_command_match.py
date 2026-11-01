"""Owner flag command command: direct C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1506D958','game_981E0'
ENTRY,ROM,BODY,SIZE=0x1506D958,0x9AE08,288,288
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
ASM='conker/asm/nonmatchings/game_981E0/func_1506D958.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-owner-flag-command-1506D958-match'
RAW_SHA='76c311ebb56531540a75eafa0c5511b91d37e6a685e7b17da579139aa233173e'
TRUTH_SHA='ef48959c40db7ef89de7c7ba1fca903baa576b0dde7c58df979e2d9bcca6fec5'
BEFORE_ELF_SHA='c5481db684aba3e151677335b0274e567bfcfe4b20fcbb1f79fba9ce204071da'
BINDINGS={0: [('R_MIPS_HI16', 'D_800D1580')], 4: [('R_MIPS_LO16', 'D_800D1580')], 8: [('R_MIPS_HI16', 'D_800CC2D0')], 12: [('R_MIPS_LO16', 'D_800CC2D0')], 36: [('R_MIPS_HI16', 'D_800CC2D0')], 40: [('R_MIPS_LO16', 'D_800CC2D0')], 44: [('R_MIPS_HI16', 'D_800C3E78')], 48: [('R_MIPS_LO16', 'D_800C3E78')], 56: [('R_MIPS_HI16', 'D_800CC2D0')], 64: [('R_MIPS_LO16', 'D_800CC2D0')], 80: [('R_MIPS_HI16', 'D_800CC2D0')], 84: [('R_MIPS_LO16', 'D_800CC2D0')], 88: [('R_MIPS_HI16', 'D_800CC2D0')], 104: [('R_MIPS_LO16', 'D_800CC2D0')], 108: [('R_MIPS_HI16', 'D_800C3E78')], 128: [('R_MIPS_LO16', 'D_800C3E78')], 112: [('R_MIPS_HI16', 'D_800CC2D0')], 124: [('R_MIPS_LO16', 'D_800CC2D0')], 116: [('R_MIPS_HI16', 'D_800CC2D0')], 120: [('R_MIPS_LO16', 'D_800CC2D0')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct127 D_800CC2D0[26];\nextern s32 D_800D1580;\nextern u8 D_800C3E78;\n'
SELECTED='/* Clear bit zero, then apply the packed high byte to the first matching owner/tag record. */\nvoid func_1506D958(void) {\n    s32 flagBits;\n    s32 matchByte;\n    s32 slot;\n\n    matchByte = D_800D1580 & 0xFF;\n    flagBits = (D_800D1580 >> 8) & 0xFF;\n    for (slot = 0; slot < 25; slot++) {\n        if ((D_800CC2D0[slot].interaction_state != 0) &&\n            (D_800CC2D0[slot].unkAB == matchByte) &&\n            (D_800CC2D0[slot].unk65 == D_800C3E78 + 1)) {\n            D_800CC2D0[slot].unk101 &= ~1;\n            D_800CC2D0[slot].unk101 |= flagBits;\n            return;\n        }\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner flag command payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='/* Non-matching C placeholders for asm/nonmatchings/game_981E0/func_1506D958.s. */\ns32 func_1506D958() {\n    return 0;\n}'
 if before.count(old)!=1 or before.count('s32 func_1506D958();')!=1:raise ValueError('Owner flag command placeholder changed')
 return before.replace(old,SELECTED.rstrip(),1).replace('s32 func_1506D958();','void func_1506D958(void);',1)

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
 if a!=b:raise ValueError('Owner flag command owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Owner flag command predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner flag command predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)


SNAPSHOT_SHA='c36ab9bf303d8015ef82ad29bba32891ce265d68cc2e8a6252aa9ce15d326d03'
PREPARED_SHA='aa73f13bd8647507203023429c871131178589e328ef758fb03132c9bd536250'
NEIGHBORS=327
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_1506D958.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_981E0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner flag command input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Owner flag command frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Owner flag command preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Owner flag command evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Owner flag command prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==q['exclusions']==0):raise ValueError('Owner flag command preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Owner flag command literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Owner flag command named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Owner flag command live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Owner flag command linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Owner flag command protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=72,frame=0,alignment_words=0,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
