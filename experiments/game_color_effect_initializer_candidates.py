"""Private color-effect initializer experiment: 25 word differences, no adoption credit."""
from pathlib import Path
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15187EC0','generated_1B5370'
ENTRY,ROM,SIZE=0x15187EC0,0x1B5370,208
SOURCE='conker/src/game/generated_1B5370.c'
OBJECT='conker/build/src/game/generated_1B5370.c.o'
BUILD='conker/build/game-five-record-initializer-15187EC0-match'
ADOPTABLE=False
MATCHING_CREDIT=0
NEW_GUARDS=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\ntypedef struct { u8 startRed,startGreen,startBlue,targetRed,targetGreen,targetBlue,currentRed,currentGreen,currentBlue; u8 pad[3]; f32 blend; s32 mode; f32 rate; u8 state[12]; } ColorEffectRecord;\nextern ColorEffectRecord D_800DF700[];\nextern s32 D_800DF7B4;\n'
SELECTED='/* Append a color-effect record to the five-entry pool; return its index or -1. */\ns32 func_15187EC0(s32 mode, f32 rate, u8 startRed, u8 startGreen, u8 startBlue, u8 targetRed, u8 targetGreen, u8 targetBlue) {\n    ColorEffectRecord *record;\n    if (D_800DF7B4 < 5) {\n        record = &D_800DF700[D_800DF7B4];\n        record->rate = rate;\n        record->currentRed = startRed; record->startRed = startRed;\n        record->currentGreen = startGreen; record->startGreen = startGreen;\n        record->currentBlue = startBlue; record->startBlue = startBlue;\n        record->targetRed = targetRed;\n        record->targetGreen = targetGreen;\n        record->targetBlue = targetBlue;\n        record->mode = mode;\n        bzero(record->state, 12);\n        return ++D_800DF7B4 - 1;\n    }\n    return -1;\n}\n'
RAW_SHA='b3fe6ba4767d92a58fd0794f821d473b4f07f9394039192922a55672aba72363'
BINDINGS={20: [('R_MIPS_HI16', 'D_800DF7B4')], 28: [('R_MIPS_LO16', 'D_800DF7B4')], 56: [('R_MIPS_HI16', 'D_800DF700')], 80: [('R_MIPS_LO16', 'D_800DF700')], 152: [('R_MIPS_26', 'bzero')], 160: [('R_MIPS_HI16', 'D_800DF7B4')], 164: [('R_MIPS_LO16', 'D_800DF7B4')]}
SNAPSHOT_SHA='bd17193552745bdc4ae3e78155ada55c729ebbca2f8e9aca625e8b40f6436ba3'
ARTIFACT_SHA='42c8b5b78bb9f656092cfc07d9f4d9584cde282505815854f9234a17c8d31db2'
PRIVATE_SLOT_SHA='d831e4b0d21e7128b6a11b34e89469f7e58c870bd62681cf3327780defc3e05e'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Private initializer payload/bindings changed')
 return raw,bindings

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Private initializer snapshot index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Private initializer frozen input changed: '+name)
  values[name]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Private initializer artifact index changed')
 for name,h in json.loads(data).items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Private initializer prepared artifact changed: '+name)
 return True

def check_inputs(root,output):
 values=snapshot(output)
 for name,data in values.items():
  if(root/name).read_bytes()!=data:raise ValueError('Production input changed during private initializer experiment: '+name)
 return values

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-five-record-initializer-15187EC0-match/make-shadow/src/game/generated_1B5370.c.o'
 if data.count(private)!=9:raise ValueError('Private map owner count changed')
 data=data.replace(private,b'build/src/game/generated_1B5370.c.o');private=b'build/game-five-record-initializer-15187EC0-match/first-linked.elf'
 if data.count(private)!=1:raise ValueError('Private map output count changed')
 return data.replace(private,b'build/conker.us.elf')

def predict_private(before,slot):
 if sha(before)!='860997333f77ca8592380dc62a6be70141037cd54e8ae01e8455036e0d9e68fe' or len(slot)!=SIZE or sha(slot)!=PRIVATE_SLOT_SHA:raise ValueError('Private initializer predecessor/slot changed')
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Private initializer predecessor extent changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=slot;struct.pack_into('>I',result,rows[0][0]+8,SIZE)
 return bytes(result)

def check_private_image(before,actual,slot):
 if actual!=predict_private(before,slot):raise ValueError('Literal private image prediction differs')

def require_adoptable(root,output):
 # A passing private suite never grants installation or matching credit.
 values=check_inputs(root,output);data,_=link_owner(root,output,output/'selected-final.o',OWNER)
 truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 if data[:SIZE]!=truth or not ADOPTABLE:raise ValueError('Not adoptable: 25 retail word differences and an early argument read remain')
 return False
