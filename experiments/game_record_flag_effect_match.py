"""Record flag effect callback: direct conditional C and literal image prediction."""
from pathlib import Path
import hashlib,json
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15014144','game_40490'
ENTRY,ROM,BODY,SIZE=0x15014144,0x415F4,220,220
SOURCE='conker/src/game_40490.c'
OBJECT='conker/build/src/game_40490.c.o'
BUILD='conker/build/game-record-flag-effect-15014144-match'
NEW_GUARDS=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\nvoid func_151A9390(u8,u8,const void*,const f32*,f32,f32,s32,u8,s32);\n'
SELECTED='/* Submit record effect flags, inverting bit 1 and preserving bits 0..4. */\ns32 func_15014144(u8 *record) {\n    s32 bits = *(s32 *)(record + 0x18);\n\n    func_151A9390((bits & 1 ? 1 : 0) | (bits & 2 ? 0 : 2) | (bits & 4 ? 4 : 0) | (bits & 8 ? 8 : 0) | (bits & 0x10 ? 0x10 : 0), record[0x1F], record, NULL,\n        *(f32 *)&D_8009667C, 100.0f, -1, 0xFF, 1);\n    return 1;\n}\n'
RAW_SHA='dd2d838a7cb2a94ae483c4b53efa82bf1f5c1bfbe585c1b6522105c7bd0d3a84'
BINDINGS={20: [('R_MIPS_HI16', 'D_8009667C')], 132: [('R_MIPS_LO16', 'D_8009667C')], 192: [('R_MIPS_26', 'func_151A9390')]}
SNAPSHOT_SHA='0e2ba67e339e2f87668509edb27b9fbde3fde40bde9c82a9ed0e6fec16ddb77d'
ARTIFACT_SHA='aa31d2a8fd7ce1edf6ddc6c3fdda9d45b804c381af2ae326138554695cd3c301'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record flag effect payload/bindings changed')
 return raw,bindings

OLD_BODY='s32 func_15014144(u8 *arg0) {\n    s32 flags = 0;\n    s32 bits = *(s32 *)(arg0 + 0x18);\n\n    if (bits & 8) {\n        flags |= 8;\n    }\n    if (bits & 4) {\n        flags |= 4;\n    }\n    if ((bits & 2) == 0) {\n        flags |= 2;\n    }\n    if (bits & 1) {\n        flags |= 1;\n    }\n    if (bits & 0x10) {\n        flags |= 0x10;\n    }\n\n    func_151A9390(flags, arg0[0x1F], arg0, NULL, *(f32 *)&D_8009667C, 100.0f, -1, 0xFF, 1);\n    return 1;\n}'

def recovered_owner(before):
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi]!=OLD_BODY:raise ValueError('Record flag predecessor changed')
 return before[:lo]+SELECTED.rstrip()+before[hi:]

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record flag effect snapshot index changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Record flag effect frozen input changed: '+n)
  values[n]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Record flag effect prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Record flag effect prepared evidence changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-record-flag-effect-15014144-match/make-shadow/src/game_40490.c.o'
 if data.count(private)!=9:raise ValueError('Record flag effect private map object occurrences changed')
 data=data.replace(private,b'build/src/game_40490.c.o');name=b'build/game-record-flag-effect-15014144-match/first-linked.elf'
 if data.count(name)!=1:raise ValueError('Record flag effect private output map occurrence changed')
 return data.replace(name,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Record flag effect live input changed: '+n)
 return values

def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Record flag effect literal full-image prediction differs')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 reference=(output/'first-linked.elf').read_bytes()
 if actual!=reference:raise ValueError('Record flag effect production differs from qualified first link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Record flag effect protected data changed')
 q=json.loads((output/'private-image-qualification.json').read_text())
 if not q['success']or not q['strict_whole_image_prediction']or q['strict_exclusions']!=0:raise ValueError('Record flag effect image qualification failed')
 q.update(private_only=False,installed=True,matching_credit=1,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q


import hashlib,struct
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
BASELINE='02f7f9a233d6ef184772a7fcb9e4aeb2f18a2dab8062e32cc627e430c603e5cf'
TARGET='func_15014144'
def predict(before,truth):
 if hashlib.sha256(before).hexdigest()!=BASELINE or len(truth)!=220:raise ValueError('Record flag image predecessor/slot changed')
 rows=[row for row in symbol_rows(before)if row[1]==TARGET]
 if len(rows)!=1 or rows[0][2][1:3]!=(0x15014144,180):raise ValueError('Record flag predecessor extent changed')
 result=bytearray(before);at=elf_slot_offset(before,0x15014144,220);result[at:at+220]=truth;struct.pack_into('>I',result,rows[0][0]+8,220)
 return bytes(result),dict(target=TARGET,target_words=55,frame=48,guards=0,old_symbol_bytes=180,new_symbol_bytes=220,ELF_length_unchanged=True,strict_exclusions=0)
