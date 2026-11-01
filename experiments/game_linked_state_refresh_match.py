"""Linked-state refresh: semantic C, closed private spill pair and full-image audit."""
from pathlib import Path
import hashlib,json
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_151A084C','generated_1CC440'
ENTRY,ROM,BODY,SIZE=0x151A084C,0x1CDCFC,220,220
SOURCE='conker/src/game/generated_1CC440.c'
OBJECT='conker/build/src/game/generated_1CC440.c.o'
BUILD='conker/build/game-linked-state-refresh-151A084C-match'
NEW_GUARDS=[(0x68,0xAFA80024,0xAFA80028),(0x8C,0x8FA80024,0x8FA80028)]
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\ns32 func_1519F1C8(u8 *,u8);\nvoid func_151A0928(u8 *);\ntypedef struct {s32 first, second, third, fourth;} FourWord1CC440;\n#include "structs.h"\n'
SELECTED='/* Refresh the selected linked-state value and invalidate a completed entry. */\nvoid func_151A084C(struct260 *entry) {\n    u8 **link;\n    u8 *actor;\n    FourWord1CC440 *outputs;\n    u8 invalid;\n    link = (u8 **)((u8 *)entry + 0x28);\n    actor = *(u8 **)(*link + 0x18);\n    outputs = (FourWord1CC440 *)(*link + 0x58);\n    invalid = 0;\n    if (*(s32 *)actor == 0) invalid = 1;\n    if ((*link)[0x1C] != actor[0x3B]) invalid = 1;\n    if (invalid == 0 && *(s32 *)(actor + 0x1D4) != 0) {\n        s32 result;\n        invalid = 1;\n        result = func_1519F1C8(*link, ((u8 *)link)[4]);\n        if (((u8 *)link)[4] == 6) outputs->first = result;\n        else outputs->third = result;\n    }\n    if (invalid) {\n        func_151A0928((u8 *)entry);\n        entry->unkE = -1;\n        entry->unkD |= 1;\n    }\n}\n'
RAW_SHA='90346cf34a47d6b39bef66ac3ae745f5ccb063d16dbd5cce01a7c63a50b700d9'
BINDINGS={112: [('R_MIPS_26', 'func_1519F1C8')], 172: [('R_MIPS_26', 'func_151A0928')]}
SNAPSHOT_SHA='3d53aa1b7dc74a006f172a6857576da1489c85a8ac3b61334f29d60a1d925c4d'
ARTIFACT_SHA='45062515b9c52e8997e8c8f49a017a723fc09c95e1bdb52109f8e83c79ae48bb'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Linked-state refresh payload/bindings changed')
 return raw,bindings

def recovered_owner(before):
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi].strip()!='s32 func_151A084C() {\n    return 0;\n}':raise ValueError('Linked-state refresh predecessor stub changed')
 return before[:lo]+SELECTED.rstrip()+before[hi:]

GUARD_ROWS=b'generated_1CC440,func_151A084C,0x068,0xAFA80024,0xAFA80028,-,-,Restore closed output-base spill to its retail private frame slot,,,false\ngenerated_1CC440,func_151A084C,0x08C,0x8FA80024,0x8FA80028,-,-,Reload closed output-base spill from its retail private frame slot,,,false\n'
def recovered_guards(before):
 if not before.endswith(b'\n') or b',func_151A084C,' in before:raise ValueError('Linked-state refresh guard predecessor changed')
 return before+GUARD_ROWS

def normalized_payload(raw):
 import struct
 if len(raw)!=BODY or sha(raw)!=RAW_SHA:raise ValueError('Linked-state refresh closed spill payload changed')
 result=bytearray(raw)
 for at,old,new in NEW_GUARDS:
  if struct.unpack_from('>I',result,at)[0]!=old:raise ValueError('Linked-state refresh closed spill expected word changed')
  struct.pack_into('>I',result,at,new)
 return bytes(result)

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Linked-state refresh snapshot index changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Linked-state refresh frozen input changed: '+n)
  values[n]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Linked-state refresh prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Linked-state refresh prepared evidence changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-linked-state-refresh-151A084C-match/make-shadow/src/game/generated_1CC440.c.o'
 if data.count(private)!=9:raise ValueError('Linked-state refresh private map object occurrences changed')
 data=data.replace(private,b'build/src/game/generated_1CC440.c.o');name=b'build/game-linked-state-refresh-151A084C-match/first-linked.elf'
 if data.count(name)!=1:raise ValueError('Linked-state refresh private output map occurrence changed')
 return data.replace(name,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={'conker/retail_word_patches.us.csv':recovered_guards(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Linked-state refresh live input changed: '+n)
 return values

def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Linked-state refresh literal full-image prediction differs')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 reference=(output/'first-linked.elf').read_bytes()
 if actual!=reference:raise ValueError('Linked-state refresh production differs from qualified first link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Linked-state refresh protected data changed')
 q=json.loads((output/'private-owner-image-v12.json').read_text())
 if not q['success']or not q['strict_whole_image_prediction']or q['strict_exclusions']!=0:raise ValueError('Linked-state refresh image qualification failed')
 q.update(private_only=False,installed=True,matching_credit=1,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q


from collections import Counter
import struct
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
BASELINE='82be01b39fa42cbc62f1ec773ca0e38b838018630dd35b3631cc0acd03f93a20'
def predict(before,truth):
 if sha(before)!=BASELINE or len(truth)!=220:raise ValueError('Linked-state refresh image predecessor or slot changed')
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Linked-state refresh original extent changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,220);result[at:at+220]=truth;struct.pack_into('>I',result,rows[0][0]+8,220)
 return bytes(result),dict(target=FUNCTION,target_words=55,frame=48,guards=2,old_symbol_bytes=12,new_symbol_bytes=220,ELF_length_unchanged=True,strict_exclusions=0)
