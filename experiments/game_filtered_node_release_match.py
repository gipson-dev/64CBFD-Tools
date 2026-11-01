"""Filtered list-node release: direct C, full-width countdown and literal image audit."""
from pathlib import Path
import hashlib,json
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15030310','generated_5D2C0'
ENTRY,ROM,BODY,SIZE=0x15030310,0x5D7C0,212,212
SOURCE='conker/src/game/generated_5D2C0.c'
OBJECT='conker/build/src/game/generated_5D2C0.c.o'
BUILD='conker/build/game-filtered-node-release-15030310-match'
NEW_GUARDS=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\nextern u8 *D_800C3EE0;\nvoid func_15030158(u8 *,s32);\n'
SELECTED='/* Release one indexed match, or all matches for the 0xFF sentinel. */\ns32 func_15030310(u8 *actor, s32 filter, u32 skip) {\n    u8 *current;\n    u8 *next;\n    s32 released;\n\n    if (actor[0x3B] == 0) {\n        return 0;\n    }\n    current = D_800C3EE0;\n    released = 0;\n    if (current != NULL) {\n        do {\n            next = *(u8 **)(current + 0x54);\n            if (actor[0x3B] == current[0] && filter == current[6]) {\n                if (skip != 0xFF && skip != 0) {\n                    skip--;\n                    current = next;\n                    continue;\n                } else {\n                    func_15030158(current, 0);\n                    released = 1;\n                    if (skip == 0) {\n                        break;\n                    }\n                }\n            }\n            current = next;\n        } while (current != NULL);\n    }\n    return released;\n}\n'
RAW_SHA='df93afbea48b766642a70c3b64c13cac15c138f8be5fb44078bc75b9e77bb65c'
BINDINGS={48: [('R_MIPS_HI16', 'D_800C3EE0')], 68: [('R_MIPS_LO16', 'D_800C3EE0')], 148: [('R_MIPS_26', 'func_15030158')]}
SNAPSHOT_SHA='ddea16a0668c4b316934e1a4396709bcc9e59b7276059910f5cc1cad1a211cbe'
ARTIFACT_SHA='9f444ef1e9a7681c14ca6d45607a8e0298e8232666fb7fe89391298b7d97299c'
def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Filtered node release payload/bindings changed')
 return raw,bindings

OLD_BODY='s32 func_15030310() {\n    return 0;\n}'

def recovered_owner(before):
 if before.count(OLD_BODY)!=1 or before.count('s32 func_15030310();')!=1:raise ValueError('Filtered node release predecessor changed')
 result=before.replace(OLD_BODY,SELECTED.rstrip(),1)
 return result.replace('s32 func_15030310();','s32 func_15030310(u8 *, s32, u32);').replace('func_15030310(arg0, arg1, 0xFF);','func_15030310((u8 *)arg0, arg1, 0xFF);')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Filtered node release snapshot index changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Filtered node release frozen input changed: '+n)
  values[n]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Filtered node release prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Filtered node release prepared evidence changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-filtered-node-release-15030310-match/make-shadow/src/game/generated_5D2C0.c.o'
 if data.count(private)!=9:raise ValueError('Filtered node release private map object occurrences changed')
 data=data.replace(private,b'build/src/game/generated_5D2C0.c.o');name=b'build/game-filtered-node-release-15030310-match/first-linked.elf'
 if data.count(name)!=1:raise ValueError('Filtered node release private output map occurrence changed')
 return data.replace(name,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Filtered node release live input changed: '+n)
 return values

def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Filtered node release literal full-image prediction differs')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 reference=(output/'first-linked.elf').read_bytes()
 if actual!=reference:raise ValueError('Filtered node release production differs from qualified first link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Filtered node release protected data changed')
 q=json.loads((output/'private-image-qualification.json').read_text())
 if not q['success']or not q['strict_whole_image_prediction']or q['strict_exclusions']!=0:raise ValueError('Filtered node release image qualification failed')
 q.update(private_only=False,installed=True,matching_credit=1,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

"""Predict only the recovered 212-byte slot and 12-to-212-byte symbol extent."""
from collections import Counter
import hashlib,struct
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
BASELINE='5ac59aad2748c59364549a911e4e7ce1576fce3de31e7f440e2d6414250d3fbe'
TARGET='func_15030310'
def predict(before,truth):
 if hashlib.sha256(before).hexdigest()!=BASELINE or len(truth)!=212:raise ValueError('Filtered node release image predecessor/slot changed')
 rows=[row for row in symbol_rows(before)if row[1]==TARGET]
 if len(rows)!=1 or rows[0][2][1:3]!=(0x15030310,12):raise ValueError('Filtered node release predecessor extent changed')
 result=bytearray(before);at=elf_slot_offset(before,0x15030310,212);result[at:at+212]=truth;struct.pack_into('>I',result,rows[0][0]+8,212)
 return bytes(result),dict(target=TARGET,target_words=53,frame=48,guards=0,old_symbol_bytes=12,new_symbol_bytes=212,ELF_length_unchanged=True,strict_exclusions=0)
