"""First active actor ID lookup: direct C, alias-aware links and literal image audit."""
from pathlib import Path
import hashlib,json
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1505F0AC','game_83300'
ENTRY,ROM,BODY,SIZE=0x1505F0AC,0x8C55C,220,220
SOURCE='conker/src/game_83300.c'
OBJECT='conker/build/src/game_83300.c.o'
BUILD='conker/build/game-active-actor-id-1505F0AC-match'
NEW_GUARDS=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n'
SELECTED='/* Return the first active actor with this ID, excluding reserved slot 25. */\nstruct127 *func_1505F0AC(s32 id) {\n    struct127 *actor;\n    s32 index;\n\n    actor = D_800CC2D0;\n    for (index = 0; index < 25; actor++, index++) {\n        if (actor->interaction_state != 0 && actor->id == id) {\n            return actor;\n        }\n    }\n    return NULL;\n}\n'
RAW_SHA='f2c695803e461196564bcd63c1501cfc01c8df2a9fa02626c97f3201ba8ab8a2'
BINDINGS={0: [('R_MIPS_HI16', 'D_800CC2D0')], 4: [('R_MIPS_LO16', 'D_800CC2D0')], 20: [('R_MIPS_HI16', 'D_800CC2D0')], 24: [('R_MIPS_LO16', 'D_800CC2D0')], 28: [('R_MIPS_HI16', 'D_800CC2D0')], 44: [('R_MIPS_LO16', 'D_800CC2D0')], 8: [('R_MIPS_HI16', 'D_800CC2D0')], 12: [('R_MIPS_LO16', 'D_800CC2D0')]}
SNAPSHOT_SHA='a971d519f393f0352aafc68dad03e71db40a1a26e82fe77927bfccbeebab2c4c'
ARTIFACT_SHA='12b4caa5b67294311fa8a529e575f9bc5045005371700ad54706779cb0aa60f2'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Active actor ID lookup payload/bindings changed')
 return raw,bindings

OLD_BODY='struct127 * func_1505F0AC(s32 arg0) {\n    return 0;\n}'

def recovered_owner(before):
 if before.count(OLD_BODY)!=1:raise ValueError('Actor ID lookup predecessor changed')
 result=before.replace(OLD_BODY,SELECTED.rstrip(),1)
 return result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_1505F0AC.s. */\n','')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Active actor ID lookup snapshot index changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Active actor ID lookup frozen input changed: '+n)
  values[n]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Active actor ID lookup prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Active actor ID lookup prepared evidence changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-active-actor-id-1505F0AC-match/make-shadow/src/game_83300.c.o'
 if data.count(private)!=9:raise ValueError('Active actor ID lookup private map object occurrences changed')
 data=data.replace(private,b'build/src/game_83300.c.o');name=b'build/game-active-actor-id-1505F0AC-match/first-linked.elf'
 if data.count(name)!=1:raise ValueError('Active actor ID lookup private output map occurrence changed')
 return data.replace(name,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Active actor ID lookup live input changed: '+n)
 return values

def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Active actor ID lookup literal full-image prediction differs')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 reference=(output/'first-linked.elf').read_bytes()
 if actual!=reference:raise ValueError('Active actor ID lookup production differs from qualified first link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Active actor ID lookup protected data changed')
 q=json.loads((output/'private-image-qualification.json').read_text())
 if not q['success']or not q['strict_whole_image_prediction']or q['strict_exclusions']!=0:raise ValueError('Active actor ID lookup image qualification failed')
 q.update(private_only=False,installed=True,matching_credit=1,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q


import hashlib,struct
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
BASELINE='af12e1ecafe8eba532a5fdbdb840b9f480c3fab078a50c72efd00fbf084d0bf4'
TARGET='func_1505F0AC'
def predict(before,truth):
 if hashlib.sha256(before).hexdigest()!=BASELINE or len(truth)!=220:raise ValueError('Record flag image predecessor/slot changed')
 rows=[row for row in symbol_rows(before)if row[1]==TARGET]
 if len(rows)!=1 or rows[0][2][1:3]!=(0x1505F0AC,16):raise ValueError('Record flag predecessor extent changed')
 result=bytearray(before);at=elf_slot_offset(before,0x1505F0AC,220);result[at:at+220]=truth;struct.pack_into('>I',result,rows[0][0]+8,220)
 return bytes(result),dict(target=TARGET,target_words=55,frame=0,guards=0,old_symbol_bytes=16,new_symbol_bytes=220,ELF_length_unchanged=True,strict_exclusions=0)
