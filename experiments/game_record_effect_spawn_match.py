"""Record type-0x21 effect callback: direct C and full overflow-removal prediction."""
from pathlib import Path
import hashlib,json
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15014094','game_40490'
ENTRY,ROM,BODY,SIZE=0x15014094,0x41544,176,176
SOURCE='conker/src/game_40490.c'
OBJECT='conker/build/src/game_40490.c.o'
BUILD='conker/build/game-record-effect-spawn-15014094-match'
NEW_GUARDS=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n'
SELECTED="/* Spawn a type-0x21 effect with the original partially initialized record. */\ns32 func_15014094(u8 *record) {\n    /* Retail copies the untouched payload bytes; do not clear this buffer. */\n    u8 data[0x34];\n    u8 *effect;\n\n    record[0x16] |= 4;\n    *(void **)(data + 0) = record;\n    *(f32 *)(data + 4) = func_15144598((struct134 *)record);\n    *(f32 *)(data + 8) = 0.0f;\n    func_1510F800(0);\n    *(s32 *)(data + 0xC) = func_1510FD20(*(s16 *)(record + 0), *(s16 *)(record + 4));\n    data[0x2C] = 0;\n    effect = (u8 *)func_15149130(0x12C, -1, 0x21, -1, 0, 0, (struct37 *)0x34, 0xFF, 1);\n    if (effect != NULL) {\n        memcpy(effect + 0x28, data, 0x34);\n    }\n    /* The record dispatcher ignores this callback's incidental return value. */\n}\n"
RAW_SHA='d12462835f7e20a840db166afe576c608aef6d4d998c67554175594c1d6841a7'
BINDINGS={32: [('R_MIPS_26', 'func_15144598')], 52: [('R_MIPS_26', 'func_1510F800')], 68: [('R_MIPS_26', 'func_1510FD20')], 128: [('R_MIPS_26', 'func_15149130')], 152: [('R_MIPS_26', 'memcpy')]}
SNAPSHOT_SHA='426488275de9bcbaadcfd6b4661f4875db9c1a934773a827a3cb5ad8c8a4bcfb'
ARTIFACT_SHA='094f500d1336a4ab2203b85bd3f97b089ab99d2b761c333960620d97febb40ca'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record effect payload/bindings changed')
 return raw,bindings

def recovered_owner(before):
 lo,hi=function_span(before,FUNCTION)
 if 'bzero(data, sizeof(data));'not in before[lo:hi] or 'return 1;'not in before[lo:hi]:raise ValueError('Record effect predecessor changed')
 result=before[:lo]+SELECTED.rstrip()+before[hi:]
 start=result.index('// NON-MATCHING: kinda right idea');end=result.index('s32 func_15014144',start)
 return result[:start]+result[end:]

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record effect snapshot index changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Record effect frozen input changed: '+n)
  values[n]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Record effect prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Record effect prepared evidence changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-record-effect-spawn-15014094-match/make-shadow/src/game_40490.c.o'
 if data.count(private)!=9:raise ValueError('Record effect private map object occurrences changed')
 data=data.replace(private,b'build/src/game_40490.c.o');name=b'build/game-record-effect-spawn-15014094-match/first-linked.elf'
 if data.count(name)!=1:raise ValueError('Record effect private output map occurrence changed')
 return data.replace(name,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Record effect live input changed: '+n)
 return values

def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Record effect literal full-image prediction differs')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 reference=(output/'first-linked.elf').read_bytes()
 if actual!=reference:raise ValueError('Record effect production differs from qualified first link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Record effect protected data changed')
 q=json.loads((output/'private-image-qualification.json').read_text())
 if not q['success']or not q['strict_whole_image_prediction']or q['strict_exclusions']!=0:raise ValueError('Record effect image qualification failed')
 q.update(private_only=False,installed=True,matching_credit=1,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q


import struct
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,SYMBOL,read_c_string
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
BASELINE='2b585aabd9bfae2d0851db1f9c8b140dd3a31f08622da19c055216fc3244b0bb'
TARGET='func_15014094';DELETED='__retail_overflow_'+TARGET;PH=struct.Struct('>8I')
def predict(before,truth):
 assert hashlib.sha256(before).hexdigest()==BASELINE and len(truth)==176
 header=list(ELF_HEADER.unpack_from(before));sections=[list(SECTION_HEADER.unpack_from(before,header[6]+i*header[11]))for i in range(header[12])];assert header[12:]==[12,11]
 names=before[sections[11][4]:sections[11][4]+sections[11][5]];assert [read_c_string(names,h[0])for h in sections][8:]==['.game_overflow','.symtab','.strtab','.shstrtab']
 overflow,symtab,strtab=sections[8],sections[9],sections[10];strings=before[strtab[4]:strtab[4]+strtab[5]];symbols=[list(SYMBOL.unpack_from(before,at))for at in range(symtab[4],symtab[4]+symtab[5],16)];symbol_names=[read_c_string(strings,row[0])for row in symbols]
 deleted_index=symbol_names.index(DELETED);removed=symbols[deleted_index];file_index=deleted_index-1;file_symbol=symbols[file_index];file_name='game_40490.c.o'
 assert symbol_names[file_index]==file_name and tuple(file_symbol[1:])==(0,0,4,0,65521);assert tuple(removed[1:])==(0x15F00000,184,2,0,8)
 cut_va,length=removed[1:3];end_va=cut_va+length;rom_delta=((overflow[5]+15)&~15)-((overflow[5]-length+15)&~15);assert overflow[5]==1968 and rom_delta==176
 moved={n:row[1]for n,row in zip(symbol_names,symbols)if row[5]==8 and end_va<=row[1]<overflow[3]+overflow[5]};assert len(moved)==7 and all(n.startswith('__retail_overflow_')for n in moved)
 root_index=symbol_names.index(TARGET);root=symbols[root_index];assert tuple(root[1:])==(0x15014094,176,18,0,5)
 prefix=bytearray(before[:overflow[4]]);at=elf_slot_offset(before,root[1],176);assert struct.unpack_from('>I',prefix,at)[0]==0x08000000|((cut_va>>2)&0x3FFFFFF);prefix[at:at+176]=truth
 by_name=dict(zip(symbol_names,symbols));trampolines={}
 for private,address in moved.items():
  canonical=private.removeprefix('__retail_overflow_');at=elf_slot_offset(before,by_name[canonical][1],4);word=struct.unpack_from('>I',before,at)[0]
  if word==0x08000000|((address>>2)&0x3FFFFFF):struct.pack_into('>I',prefix,at,0x08000000|(((address-length)>>2)&0x3FFFFFF));trampolines[canonical]=at
 scanned=[]
 for sec in sections[1:9]:
  if not(sec[2]&4):continue
  for off in range(0,sec[5],4):
   at=sec[4]+off;word=struct.unpack_from('>I',before,at)[0]
   if word>>26 not in(2,3):continue
   dest=((sec[3]+off+4)&0xF0000000)|((word&0x3FFFFFF)<<2)
   if end_va<=dest<overflow[3]+overflow[5]:scanned.append(at)
 assert set(scanned)==set(trampolines.values())
 cut_string=file_symbol[0];old_name=file_name.encode()+b'\0'+DELETED.encode()+b'\0';assert removed[0]==cut_string+len(file_name)+1 and strings[cut_string:cut_string+len(old_name)]==old_name
 root_text=TARGET.encode()+b'\0';assert root[0]==removed[0]+len('__retail_overflow_');assert [(n,row[0])for n,row in zip(symbol_names,symbols)if cut_string<=row[0]<cut_string+len(old_name)]==[(file_name,cut_string),(DELETED,removed[0]),(TARGET,root[0])]
 insertion_old=symbols[root_index-1][0]+len(symbol_names[root_index-1].encode())+1;assert symbol_names[root_index-1]=='func_1517E28C' and symbols[root_index+1][0]==insertion_old
 insertion=insertion_old-len(old_name);compact=strings[:cut_string]+strings[cut_string+len(old_name):];new_strings=compact[:insertion]+root_text+compact[insertion:];assert len(new_strings)==len(strings)-33
 fresh=[]
 for i,(name,row)in enumerate(zip(symbol_names,symbols)):
  if i in(deleted_index,file_index):continue
  new=row[:]
  if name==TARGET:new[0]=insertion
  else:
   assert not cut_string<=row[0]<cut_string+len(old_name);at=row[0]-(len(old_name)if row[0]>=cut_string+len(old_name)else 0);new[0]=at+(len(root_text)if at>=insertion else 0)
  assert read_c_string(new_strings,new[0])==name
  if name in moved:new[1]-=length
  if name in('__romPos','debugger_overflow_ROM_START'):assert row[1]==2469264;new[1]-=rom_delta
  fresh.append(new)
 payloads={8:before[overflow[4]+length:overflow[4]+overflow[5]],9:b''.join(SYMBOL.pack(*row)for row in fresh),10:new_strings,11:names};result=prefix
 for i in range(8,12):
  sec=sections[i];result.extend(b'\0'*((-len(result))%max(1,sec[8])));sec[4]=len(result);sec[5]=len(payloads[i]);result.extend(payloads[i])
 sections[9][7]-=2;result.extend(b'\0'*((-len(result))%4));header[6]=len(result);result.extend(b''.join(SECTION_HEADER.pack(*sec)for sec in sections));result[:ELF_HEADER.size]=ELF_HEADER.pack(*header)
 changed=0
 for i in range(header[10]):
  at=header[5]+i*header[9];ph=list(PH.unpack_from(before,at))
  if ph[2]==0x15F00000:assert ph[4:6]==[1968,1968];ph[4]-=length;ph[5]-=length;PH.pack_into(result,at,*ph);changed+=1
 assert changed==1
 return bytes(result),dict(deleted_private_body=DELETED,removed_body_bytes=184,ROM_cursor_bytes_removed=176,moved_private_definitions=moved,retargeted_trampolines=sorted(trampolines),symbol_rows_removed=2,string_bytes_removed=33,ELF_bytes_removed=len(before)-len(result),strict_exclusions=0)
