"""Random positional sound: explicitly sequenced C and literal entire-image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_151618BC','game_18D770'
ENTRY,ROM,BODY,SIZE=0x151618BC,0x18ED6C,228,228
SOURCE='conker/src/game_18D770.c'
OBJECT='conker/build/src/game_18D770.c.o'
BUILD='conker/build/game-random-positional-sound-151618BC-match'
NEW_GUARDS=[]
BASELINE='83088793cafaec148da7082549742f2dd2c964ba2049ca56acb368fc8e01e6d1'
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct { s32 ids[10]; } SoundIds;\nextern s32 D_800A66E4[10];\ns32 func_150ADA20(void);\nu16 func_10010F88(s32, u16, s16, u8, s32, s16, s16, s16, s16, s16);\n'
SELECTED='void func_151618BC(u16 volume, s16 pitch, u8 flags, s32 channel, struct17 *position, s16 minimum, s16 maximum) {\n    SoundIds sounds;\n    s32 selected;\n    sounds = *(SoundIds *)D_800A66E4;\n    selected = sounds.ids[(u32)func_150ADA20() % 10U];\n    func_10010F88(selected, volume, pitch, flags, channel, (s32)position->unk0, (s32)position->unk4, (s32)position->unk8, minimum, maximum);\n}\n'
RAW_SHA='e8b39d79ee227ec99370a1ced79b6f0375a9ddc45cb44c031d7ee49cad0dad39'
BINDINGS={24: [('R_MIPS_HI16', 'D_800A66E4')], 28: [('R_MIPS_LO16', 'D_800A66E4')], 80: [('R_MIPS_26', 'func_150ADA20')], 204: [('R_MIPS_26', 'func_10010F88')]}
SNAPSHOT_SHA='3a99c30262f59a9e43069e2ca0108d701f304ed2117c2d183fef4ffc945b0dbf'
ARTIFACT_SHA='dfadbaeac5b492fb4a964f6c9edd671a0b71a3160d248cee4c78f5e3272edf4a'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Random positional sound payload or bindings changed')
 return raw,bindings
def recovered_owner(before):
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi].strip()!='s32 func_151618BC(s32 arg0, s32 arg1, s32 arg2, s32 arg3, s32 arg4, s32 arg5, s32 arg6) {\n    return 0;\n}':raise ValueError('Random sound predecessor changed')
 result=before[:lo]+'/* Copy the sound choices before RNG, then submit one positional sound. */\n'+SELECTED.rstrip()+before[hi:]
 old='s32 func_151618BC(s32 arg0, s32 arg1, s32 arg2, s32 arg3, s32 arg4, s32 arg5, s32 arg6);'
 if result.count(old)!=1:raise ValueError('Random sound forward prototype changed')
 result=result.replace(old,'void func_151618BC(u16, s16, u8, s32, struct17 *, s16, s16);',1)
 result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_18D770/func_151618BC.s. */\n','',1)
 anchor='#include "variables.h"\n'
 if result.count(anchor)!=1:raise ValueError('Random sound declaration anchor changed')
 return result.replace(anchor,anchor+'\ntypedef struct { s32 ids[10]; } SoundIds;\n',1)
def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Random sound snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Random sound frozen input changed: '+n)
  values[n]=data
 return values
def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Random sound prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Random sound prepared artifact changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-random-positional-sound-151618BC-match/make-shadow/src/game_18D770.c.o'
 if data.count(private)!=9:raise ValueError('Random sound map owner count changed')
 data=data.replace(private,b'build/src/game_18D770.c.o');private=b'build/game-random-positional-sound-151618BC-match/first-linked.elf'
 if data.count(private)!=1:raise ValueError('Random sound map output count changed')
 return data.replace(private,b'build/conker.us.elf')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Random sound live input changed: '+n)
 return values
def predict(before,truth):
 if sha(before)!=BASELINE or len(truth)!=SIZE:raise ValueError('Random sound image predecessor or slot changed')
 rows=[v for v in symbol_rows(before)if v[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,28):raise ValueError('Random sound predecessor extent changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth;struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result),dict(target=FUNCTION,target_words=57,frame=96,guards=0,old_symbol_bytes=28,new_symbol_bytes=228,ELF_length_unchanged=True,strict_exclusions=0)
def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Random sound literal whole-image prediction differs')
def check_owner_diagnostics(before,after):
 a,b=diagnostic_rows(before),diagnostic_rows(after)
 removed=Counter({('712','illegal combination of pointer and integer','func_151618BC(25000, 0, 0, 0, &tmp, 500, 1500);'):1})
 if a-b!=removed or b-a:raise ValueError('Random sound diagnostics differ beyond the repaired local caller prototype')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=1)
def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 if actual!=(output/'first-linked.elf').read_bytes():raise ValueError('Random sound actual production differs from qualified private link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Random sound protected Game data changed')
 q=json.loads((output/'private-owner-image-v12.json').read_text())
 if not q['success']or not q['strict_whole_image_prediction']or q['strict_exclusions']!=0:raise ValueError('Random sound owner/image qualification failed')
 q.update(private_only=False,installed=True,matching_credit=1,guest_native_caller_gates_pending=False,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
