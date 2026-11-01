"""Actor category event callback: direct C, retained switch table and full-image audit."""
from pathlib import Path
import hashlib,json
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1513DF9C','game_169510'
ENTRY,ROM,BODY,SIZE=0x1513DF9C,0x16B44C,212,212
SOURCE='conker/src/game_169510.c'
OBJECT='conker/build/src/game_169510.c.o'
BUILD='conker/build/game-actor-category-callback-1513DF9C-match'
NEW_GUARDS=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\nextern void (*D_80089F64[])(void *, s32, u8);\n'
SELECTED='/* Dispatch an actor event by category, using entry zero when flag 22 is clear. */\nvoid func_1513DF9C(void *actorPointer, s32 eventAddress, u8 command) {\n    u8 *actor = actorPointer;\n    s32 index;\n    if ((*(u32 *)(actor + 0x58) & 0x400000) == 0) {\n        index = 0;\n    } else {\n        switch (actor[0x19]) {\n        case 12: index = 10; break;\n        case 11: index = 9; break;\n        case 0:\n        case 2: index = 0; break;\n        case 1: index = 1; break;\n        case 5: index = 2; break;\n        case 6: index = 3; break;\n        case 3: index = 4; break;\n        case 7: index = 5; break;\n        case 8: index = 6; break;\n        case 9: index = 7; break;\n        case 4: index = 8; break;\n        default: index = 0; break;\n        }\n    }\n    D_80089F64[index](actor, eventAddress, command);\n}\n'
RAW_SHA='e637d580f5562fe3b4f256d2b11b25721ff09d4b7f952e8d8ec853001dd86ec3'
BINDINGS={60: [('R_MIPS_HI16', '.rodata')], 68: [('R_MIPS_LO16', '.rodata')], 176: [('R_MIPS_HI16', 'D_80089F64')], 184: [('R_MIPS_LO16', 'D_80089F64')]}
SNAPSHOT_SHA='1a26d03e5d4485fa3f658f4a64be63cdb971865fa244a720eaffdd8be87f140e'
ARTIFACT_SHA='dca6679dc2873b833e5352b328997a160e3e60d6ba9759eb1e092a75ddc71029'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor category callback payload/bindings changed')
 return raw,bindings

def recovered_owner(before):
 from tools.experiments.game_remaining_donor_candidates import function_span
 marker='/* Non-matching C placeholders for asm/nonmatchings/game_169510/func_1513DF9C.s. */\n'
 if before.count('s32 func_1513DF9C();')!=1 or before.count(marker)!=1:raise ValueError('Actor category callback predecessor changed')
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi].strip()!='s32 func_1513DF9C() {\n    return 0;\n}':raise ValueError('Actor category callback stub changed')
 result=before[:lo]+SELECTED.rstrip()+before[hi:]
 result=result.replace('s32 func_1513DF9C();','void func_1513DF9C(void *, s32, u8);').replace(marker,'')
 anchor='/* End generated placeholder declarations. */'
 if result.count(anchor)!=1:raise ValueError('Actor category callback declaration anchor changed')
 return result.replace(anchor,'extern void (*D_80089F64[])(void *, s32, u8);\n'+anchor)

def recovered_makefile(before):
 anchor='$(BUILD_DIR)/$(SRC_DIR)/game_A9D90.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009B884_game'
 binding='$(BUILD_DIR)/$(SRC_DIR)/game_169510.c.o: RETAIL_RODATA_SYMBOL := jtbl_800A5188_game'
 if before.count(anchor)!=1 or binding in before:raise ValueError('Actor category callback Make binding predecessor changed')
 return before.replace(anchor,anchor+'\n'+binding)

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor category callback snapshot index changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Actor category callback frozen input changed: '+n)
  values[n]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Actor category callback prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Actor category callback prepared evidence changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-actor-category-callback-1513DF9C-match/make-shadow/src/game_169510.c.o'
 if data.count(private)!=9:raise ValueError('Actor category callback private map object occurrences changed')
 data=data.replace(private,b'build/src/game_169510.c.o');name=b'build/game-actor-category-callback-1513DF9C-match/first-linked.elf'
 if data.count(name)!=1:raise ValueError('Actor category callback private output map occurrence changed')
 return data.replace(name,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={'conker/Makefile':recovered_makefile(values['conker/Makefile'].decode()).encode(),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Actor category callback live input changed: '+n)
 return values

def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Actor category callback literal full-image prediction differs')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 reference=(output/'first-linked.elf').read_bytes()
 if actual!=reference:raise ValueError('Actor category callback production differs from qualified first link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Actor category callback protected data changed')
 q=json.loads((output/'private-image-qualification.json').read_text())
 if not q['success']or not q['strict_whole_image_prediction']or q['strict_exclusions']!=0:raise ValueError('Actor category callback image qualification failed')
 q.update(private_only=False,installed=True,matching_credit=1,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q


"""Predict only the recovered 212-byte slot and 12-to-212-byte symbol extent."""
from collections import Counter
import hashlib,struct
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
BASELINE='860997333f77ca8592380dc62a6be70141037cd54e8ae01e8455036e0d9e68fe'
TARGET='func_1513DF9C'
def predict(before,truth):
 if hashlib.sha256(before).hexdigest()!=BASELINE or len(truth)!=212:raise ValueError('Actor category callback image predecessor/slot changed')
 rows=[row for row in symbol_rows(before)if row[1]==TARGET]
 if len(rows)!=1 or rows[0][2][1:3]!=(0x1513DF9C,12):raise ValueError('Actor category callback predecessor extent changed')
 result=bytearray(before);at=elf_slot_offset(before,0x1513DF9C,212);result[at:at+212]=truth;struct.pack_into('>I',result,rows[0][0]+8,212)
 result=reorder_metadata(bytes(result))
 return result,dict(metadata_symbol_order_swap=['func_151A6B3C','D_8009E698'],target=TARGET,target_words=53,frame=24,guards=0,old_symbol_bytes=12,new_symbol_bytes=212,ELF_length_unchanged=True,strict_exclusions=0)

def reorder_metadata(image):
 from tools.experiments.game_actor_state_tick_integration import SYMBOL
 names=('func_151A6B3C','D_8009E698');entries={name:(at,fields,string)for at,name,fields,string in symbol_rows(image)}
 group=[entries[name]for name in names];start,string_at=group[0][0],group[0][2];strings_base=string_at-group[0][1][0]
 if any(row[0]!=start+i*SYMBOL.size or row[2]-row[1][0]!=strings_base for i,row in enumerate(group)):raise ValueError('Unknown bounded callback-dispatch symbol order')
 old=b''.join(name.encode()+b'\0'for name in names)
 if image[string_at:string_at+len(old)]!=old:raise ValueError('Unknown bounded callback-dispatch symbol strings')
 result=bytearray(image)
 for i,name in enumerate(reversed(names)):
  fields=list(entries[name][1]);fields[0]=string_at-strings_base;SYMBOL.pack_into(result,start+i*SYMBOL.size,*fields);literal=name.encode()+b'\0';result[string_at:string_at+len(literal)]=literal;string_at+=len(literal)
 if Counter((n,*f[1:])for _,n,f,_ in symbol_rows(image))!=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(result)):raise ValueError('Metadata reordering changed named definitions')
 return bytes(result)
