"""Private record sound-start semantics; the retail epilogue is still unmatched."""
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_actor_transform_position_match import check_owner_diagnostics
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_150A23E4','generated_CDE80'
ENTRY,ROM,BODY,SIZE=0x150A23E4,0xCF894,216,220
SOURCE='conker/src/game/generated_CDE80.c'
OBJECT='conker/build/src/game/generated_CDE80.c.o'
BUILD='conker/build/game-record-sound-start-150A23E4-match'
BASELINE='c1ba81dadb31b6a5e1cbbb16d5444ebca6bd85da0b4326ab78e5059a70997e34'
RAW_SHA='c543a36df03e35fa34f5f8fe30d2cae9649ad718370a723e6b24494cb141801d'
BINDINGS={172:[('R_MIPS_26','func_1000FA64')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Private sound-start code/bindings changed')
 return raw,bindings

def recovered_owner(before):
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi]!='s32 func_150A23E4() {\n    return 0;\n}':raise ValueError('Sound-start predecessor changed')
 declaration='u16 func_1000FA64(u16,s16,s16,s16,s32,u16,s16,s32,void*,s32,s32,s32);\n'
 return before[:lo]+declaration+'/* Submit an inactive record sound before publishing its active state. */\n'+SELECTED.rstrip()+before[hi:]

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Private sound-start snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Private sound-start frozen file changed: '+n)
  values[n]=data
 return values

def check_inputs(root,output):
 values=snapshot(output)
 for n,data in values.items():
  if(root/n).read_bytes()!=data:raise ValueError('Private sound-start live file changed: '+n)
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Private sound-start artifact index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Private sound-start artifact changed: '+n)
 return True

def predict(before,raw,bindings):
 checked_payload(raw,bindings)
 if sha(before)!=BASELINE:raise ValueError('Private sound-start image predecessor changed')
 row,=[v for v in symbol_rows(before)if v[1]==FUNCTION]
 if row[2][1:3]!=(ENTRY,12):raise ValueError('Private sound-start predecessor extent changed')
 helper,=[v for v in symbol_rows(before)if v[1]=='func_1000FA64']
 if helper[2][1]!=0x1000FA64:raise ValueError('Retained enqueue address changed')
 body=bytearray(raw)
 if struct.unpack_from('>I',body,172)[0]!=0x0C000000:raise ValueError('Private sound-start call opcode changed')
 struct.pack_into('>I',body,172,0x0C000000|((helper[2][1]>>2)&0x3FFFFFF))
 out=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);out[at:at+SIZE]=body+bytes(4);struct.pack_into('>I',out,row[0]+8,BODY)
 return bytes(out)

def check_image(before,actual,raw,bindings):
 if actual!=predict(before,raw,bindings):raise ValueError('Private sound-start entire image differs')

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-record-sound-start-150A23E4-match/make-shadow/src/game/generated_CDE80.c.o'
 if data.count(private)!=9:raise ValueError('Private sound-start map object count changed')
 data=data.replace(private,b'build/src/game/generated_CDE80.c.o');private=b'build/game-record-sound-start-150A23E4-match/first-linked.elf'
 if data.count(private)!=1:raise ValueError('Private sound-start map output changed')
 return data.replace(private,b'build/conker.us.elf')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 verify_prepared(output);values=check_inputs(root,output);raw,refs=checked_payload(*payload(output/'flow-10.o'))
 actual=(output/'first-linked.elf').read_bytes();check_image(values['conker/build/conker.us.elf'],actual,raw,refs)
 if sha(actual)!='f88a211d92648be3f637ca1561ff121be38984dc9808f2ad1461d72895227abc':raise ValueError('Private sound-start linked image changed')
 data=audit_layout(output/'first-linked.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Private sound-start protected data changed')
 expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(values['conker/build/conker.us.elf']))
 if expected!=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual)):raise ValueError('Private sound-start named definition changed')
 q=json.loads((output/'private-owner-image-v22.json').read_text())
 if not q['private_only'] or q['installed'] or q['matching_credit']!=0:raise ValueError('Private sound-start falsely credited')
 return q

HEADERS='#include <ultra64.h>\ntypedef struct {\n    s16 origin0;\n    s16 origin1;\n    s16 origin2;\n    u8 pad6[0xF];\n    u8 flags;\n    u8 pad16;\n    u8 field17;\n    s32 field18;\n    s32 field1C;\n    s32 field20;\n    f32 coefficient0;\n    f32 scale;\n    f32 coefficient1;\n    f32 coefficient2;\n} GeneratedCDE80Record;\nu16 func_1000FA64(u16,s16,s16,s16,s32,u16,s16,s32,void*,s32,s32,s32);\n'
SELECTED='void func_150A23E4(GeneratedCDE80Record *record) {\n    s32 extra;\n    s32 mode;\n    if (record->field20 == 0) {\n        extra = 0;\n        mode = 8;\n        if ((record->flags & 3) == 0) extra = 0x8000;\n        if (record->field17 >> 7) mode = 0x108;\n        func_1000FA64((u32)record->field1C >> 16,\n            record->origin0, record->origin1, record->origin2,\n            (record->field17 & 0x7F) * 327,\n            record->field18 | extra, record->field1C & 0xFFFF, 0, 0, 0, mode, 0);\n        record->field20 = 1;\n    } else {\n        record->field20 = 1;\n    }\n}\n'
SNAPSHOT_SHA='91bda089c1f51cd67579ac330269124889652fed49f398eab29c46eec998c813'
ARTIFACT_SHA='62f87b8e7d6df8a20bdf4f2c89a4c18fb9a5e8e862b161de1caba697477ba575'
