"""Path-distance branch command: direct C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_150781F4','game_A28B0'
ENTRY,ROM,BODY,SIZE=0x150781F4,0xA56A4,216,216
SOURCE='conker/src/game_A28B0.c'
OBJECT='conker/build/src/game_A28B0.c.o'
ASM='conker/asm/nonmatchings/game_A28B0/func_150781F4.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-path-distance-branch-150781F4-match'
RAW_SHA='9c8c7a46715a56f276125f07c2ff18078e4afc78cf937803bafd815c8d7ba5f6'
TRUTH_SHA='ee664d48f4784d3ca10c93741dbd8562361ab0446e5e2eca61feb6acb57ba61b'
BEFORE_ELF_SHA='88e4bf6ae8be845c8f97fd94e26cd88298b65df9e361abe359d976e3a5dd2898'
BINDINGS={28: [('R_MIPS_HI16', 'D_800D1891')], 32: [('R_MIPS_LO16', 'D_800D1891')], 8: [('R_MIPS_HI16', 'D_800D154C')], 12: [('R_MIPS_LO16', 'D_800D154C')], 16: [('R_MIPS_HI16', 'D_800D2104')], 20: [('R_MIPS_LO16', 'D_800D2104')], 88: [('R_MIPS_HI16', 'D_800D1893')], 92: [('R_MIPS_LO16', 'D_800D1893')], 96: [('R_MIPS_HI16', 'D_800D1892')], 100: [('R_MIPS_LO16', 'D_800D1892')], 188: [('R_MIPS_HI16', 'D_800D1890')], 196: [('R_MIPS_LO16', 'D_800D1890')], 192: [('R_MIPS_26', 'func_15075400')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\ntypedef struct {s16 x; s16 pad2; s16 z; s16 pad6;} PathNode8;\nvoid func_15075400(s32);\n'
SELECTED='/* Branch the actor script on strict distance to the selected path node. */\nvoid func_150781F4(void) {\n    s32 nodeIndex;\n    PathNode8 *pathNode;\n    f32 distance;\n    f32 deltaX;\n    f32 deltaZ;\n\n    nodeIndex = D_800D1891 + 1;\n    pathNode = &((PathNode8 **)D_800D2104)[D_800D154C->unk13F][nodeIndex];\n    deltaX = pathNode->x - D_800D154C->x_position;\n    deltaZ = pathNode->z - D_800D154C->z_position;\n    distance = sqrtf((deltaX * deltaX) + (deltaZ * deltaZ));\n    deltaX = (f32)(D_800D1893 << 3);\n\n    if (((D_800D1892 == 0) && (distance < deltaX)) ||\n        ((D_800D1892 != 0) && (deltaX < distance))) {\n        func_15075400(D_800D1890);\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Path-distance branch payload/bindings changed')
 return raw,bindings
OLD_BODY='void func_150781F4(void) {\n    PathNode8 *temp_v1;\n    f32 temp_f0;\n    f32 temp_f2;\n    f32 temp_f12;\n\n    temp_v1 = &((PathNode8 **)D_800D2104)[D_800D154C->unk13F][D_800D1891 + 1];\n    temp_f2 = temp_v1->x - D_800D154C->x_position;\n    temp_f12 = temp_v1->z - D_800D154C->z_position;\n    temp_f0 = sqrtf((temp_f2 * temp_f2) + (temp_f12 * temp_f12));\n    temp_f2 = D_800D1893 * 8.0f;\n\n    if (((D_800D1892 == 0) && (temp_f0 < temp_f2)) ||\n        ((D_800D1892 != 0) && (temp_f2 < temp_f0))) {\n        func_15075400(D_800D1890);\n    }\n}'
def recovered_owner(before):
 if before.count(OLD_BODY)!=1:raise ValueError("Path-distance source baseline changed")
 return before.replace(OLD_BODY,SELECTED.rstrip(),1)


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
 if a!=b:raise ValueError('Path-distance branch owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Path-distance image input changed')
 return predict(before,truth)[0]

SNAPSHOT_SHA='2b5842707eb19647fc4fcfb894e600b208bcf5733f12470e9c1dc36615ca1c5c'
PREPARED_SHA='8f6609a75aa60855f590ca1d933d49cf4a920e6dcdf714889341d0e94323e4ac'
NEIGHBORS=210
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_150781F4.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_A28B0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'raw-isolated-match.json', 'overflow-prediction.json', 'overflow-closure.json', 'overflow-control-flow.json', 'retargeted-trampoline.json', 'before-conker_build_conker.us.map', 'predicted-production.map', 'linker-map-prediction.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Path-distance branch input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Path-distance branch frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Path-distance branch preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Path-distance branch evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Path-distance branch prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==q['exclusions']==0):raise ValueError('Path-distance branch preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Path-distance literal entire-image mismatch')
 return closure_definitions(before,actual)

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
  if 'conker/build/conker.us.map' in values:changes['conker/build/conker.us.map']=predict_map(values['conker/build/conker.us.map'])
 for name,data in values.items():
  if (root/name).read_bytes()!=changes.get(name,data):raise ValueError('Path-distance live input changed: '+name)
 return values

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 closure=closure_audit(output/'before-conker_build_conker.us.elf',root/'conker/build/conker.us.elf');data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Path-distance protected data changed')
 result=dict(closure,target_words=54,frame=24,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

"""Predict removal of one obsolete private overflow body, without exclusions."""
import hashlib,struct
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,SYMBOL,read_c_string
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

BASELINE=BEFORE_ELF_SHA
TARGET='func_150781F4'
DELETED='__retail_overflow_'+TARGET
PH=struct.Struct('>8I')
sha=lambda b:hashlib.sha256(b).hexdigest()

def predict(before,truth):
 assert sha(before)==BASELINE and len(truth)==216
 header=list(ELF_HEADER.unpack_from(before))
 sections=[list(SECTION_HEADER.unpack_from(before,header[6]+i*header[11]))for i in range(header[12])]
 assert header[12:]==[12,11]
 names=before[sections[11][4]:sections[11][4]+sections[11][5]]
 assert [read_c_string(names,h[0])for h in sections][8:]==['.game_overflow','.symtab','.strtab','.shstrtab']
 overflow,symtab,strtab=sections[8],sections[9],sections[10]
 strings=before[strtab[4]:strtab[4]+strtab[5]]
 symbols=[list(SYMBOL.unpack_from(before,at))for at in range(symtab[4],symtab[4]+symtab[5],16)]
 symbol_names=[read_c_string(strings,row[0])for row in symbols]
 deleted_index=symbol_names.index(DELETED);removed=symbols[deleted_index]
 assert symbol_names.count(DELETED)==1 and tuple(removed[1:])==(0x15F006F4,248,2,0,8)
 cut_va,length=removed[1:3];end_va=cut_va+length;rom_delta=((overflow[5]+15)&~15)-((overflow[5]-length+15)&~15)
 assert rom_delta==256
 moved={name:row[1]for name,row in zip(symbol_names,symbols)if row[5]==8 and end_va<=row[1]<overflow[3]+overflow[5]}
 assert set(moved)=={'__retail_overflow_func_150A7B80','__retail_overflow_func_150A7D00','__retail_overflow_func_15125490'}
 assert all(name.startswith('__retail_overflow_')for name in moved)
 root_index=symbol_names.index(TARGET);root=symbols[root_index]
 assert tuple(root[1:])==(0x150781F4,216,18,0,5)
 prefix=bytearray(before[:overflow[4]])
 target_at=elf_slot_offset(before,root[1],216)
 assert struct.unpack_from('>I',prefix,target_at)[0]==0x08000000|((cut_va>>2)&0x3FFFFFF)
 prefix[target_at:target_at+216]=truth

 # Only generated trampoline entries can reference these private implementations.
 trampolines=[]
 by_name=dict(zip(symbol_names,symbols))
 for private,old_address in moved.items():
  canonical=private.removeprefix('__retail_overflow_');row=by_name[canonical]
  at=elf_slot_offset(before,row[1],4);word=struct.unpack_from('>I',before,at)[0]
  if word==0x08000000|((old_address>>2)&0x3FFFFFF):
   struct.pack_into('>I',prefix,at,0x08000000|(((old_address-length)>>2)&0x3FFFFFF));trampolines.append(canonical)
 assert set(trampolines)=={'func_150A7D00'}
 scanned=[]
 for section in sections[1:9]:
  if not(section[2]&4):continue
  for off in range(0,section[5],4):
   at=section[4]+off;word=struct.unpack_from('>I',before,at)[0]
   if word>>26 not in(2,3):continue
   address=((section[3]+off+4)&0xF0000000)|((word&0x3FFFFFF)<<2)
   if address in moved.values():scanned.append(at)
 assert set(scanned)=={elf_slot_offset(before,by_name[n][1],4)for n in trampolines}

 # GNU's string table previously shared the public name with the local name suffix.
 cut_string=removed[0];old_name=DELETED.encode()+b'\0'
 assert strings[cut_string:cut_string+len(old_name)]==old_name
 root_text=TARGET.encode()+b'\0'
 assert root[0]==cut_string+len('__retail_overflow_')
 assert [(n,row[0])for n,row in zip(symbol_names,symbols)if cut_string<=row[0]<cut_string+len(old_name)]==[(DELETED,cut_string),(TARGET,root[0])]
 insertion_old=symbols[root_index-1][0]+len(symbol_names[root_index-1].encode())+1
 assert symbol_names[root_index-1]=='D_800E0BEA' and symbols[root_index+1][0]==insertion_old
 assert insertion_old>=cut_string+len(old_name)
 insertion=insertion_old-len(old_name)
 compact=strings[:cut_string]+strings[cut_string+len(old_name):]
 new_strings=compact[:insertion]+root_text+compact[insertion:]
 assert len(new_strings)==len(strings)-18

 new_symbols=[];changed_definitions=[]
 for i,(name,row)in enumerate(zip(symbol_names,symbols)):
  if i==deleted_index:continue
  fresh=row[:]
  if name==TARGET:fresh[0]=insertion
  else:
   assert not cut_string<=row[0]<cut_string+len(old_name)
   at=row[0]-(len(old_name)if row[0]>=cut_string+len(old_name)else 0)
   fresh[0]=at+(len(root_text)if at>=insertion else 0)
  assert read_c_string(new_strings,fresh[0])==name
  if name in moved:fresh[1]-=length;changed_definitions.append(name)
  if name in('__romPos','debugger_overflow_ROM_START'):
   assert tuple(row[1:])==(2469744,0,16,0,65521)
   fresh[1]-=rom_delta;changed_definitions.append(name)
  new_symbols.append(fresh)
 assert len(changed_definitions)==5
 new_symtab=b''.join(SYMBOL.pack(*row)for row in new_symbols)
 old_overflow=before[overflow[4]:overflow[4]+overflow[5]]
 cut=cut_va-overflow[3]
 new_overflow=old_overflow[:cut]+old_overflow[cut+length:]
 assert len(new_overflow)==overflow[5]-length

 result=prefix
 payloads={8:new_overflow,9:new_symtab,10:new_strings,11:before[sections[11][4]:sections[11][4]+sections[11][5]]}
 for i in range(8,12):
  section=sections[i];alignment=max(1,section[8]);result.extend(b'\0'*((-len(result))%alignment));section[4]=len(result);section[5]=len(payloads[i]);result.extend(payloads[i])
 sections[9][7]-=1
 result.extend(b'\0'*((-len(result))%4));header[6]=len(result)
 result.extend(b''.join(SECTION_HEADER.pack(*h)for h in sections))
 result[:ELF_HEADER.size]=ELF_HEADER.pack(*header)
 changed_program_headers=0
 for i in range(header[10]):
  at=header[5]+i*header[9];ph=list(PH.unpack_from(before,at))
  if ph[2]==0x15F00000:
   assert ph[4:6]==[0x984,0x984];ph[4]-=length;ph[5]-=length;PH.pack_into(result,at,*ph);changed_program_headers+=1
 assert changed_program_headers==1 and len(result)<len(before)-248
 return bytes(result),dict(deleted_private_body=DELETED,removed_body_bytes=length,ROM_cursor_bytes_removed=rom_delta,moved_private_definitions=moved,retargeted_trampolines=sorted(trampolines),changed_absolute_ROM_symbols=['__romPos','debugger_overflow_ROM_START'],symbol_rows_removed=1,string_bytes_removed=18,ELF_bytes_removed=len(before)-len(result),all_other_section_payloads_retained=True,strict_exclusions=0)


def closure_definitions(before,actual):
 old_rows=symbol_rows(before);new_rows=symbol_rows(actual)
 old={name:f for at,name,f,string in old_rows};new={name:f for at,name,f,string in new_rows}
 if set(old)-set(new)!={DELETED}or set(new)-set(old):raise ValueError('Path-distance named symbol set changed')
 moved={'__retail_overflow_func_150A7B80','__retail_overflow_func_150A7D00','__retail_overflow_func_15125490'}
 abs_names={'__romPos','debugger_overflow_ROM_START'};expected=Counter()
 for at,name,f,string in old_rows:
  if name==DELETED:continue
  fields=list(f[1:])
  if name in moved:fields[0]-=248
  elif name in abs_names:fields[0]-=256
  expected[(name,*fields)]+=1
 if expected!=Counter((name,*f[1:])for at,name,f,string in new_rows):raise ValueError('Path-distance named definition multiset changed')
 return dict(named_definition_multiset_verified=True,removed_definition=DELETED,changed_definitions=sorted(moved|abs_names))

def closure_audit(before_path,actual_path):
 from tools.match_progress import load_elf_functions
 before=before_path.read_bytes();actual=actual_path.read_bytes();closure_definitions(before,actual)
 a,_,aa=load_elf_functions(str(before_path),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(actual_path),'mips-linux-gnu-objdump')
 if len(a)!=6055 or set(a)-set(b)!={DELETED}or set(b)-set(a):raise ValueError('Path-distance executable function inventory changed')
 moved={'__retail_overflow_func_150A7B80','__retail_overflow_func_150A7D00','__retail_overflow_func_15125490'}
 trampolines={'func_150A7D00'};fixed=public=0
 for name in b:
  expected_address=aa[name]-(248 if name in moved else 0)
  if bb[name]!=expected_address:raise ValueError('Path-distance executable address changed: '+name)
  if name==FUNCTION:
   slot=elf_slot_offset(actual,ENTRY,SIZE)
   if sha(actual[slot:slot+SIZE])!=TRUTH_SHA:raise ValueError('Path-distance target is not retail exact')
  else:
   wanted=a[name][:]
   if name in trampolines:
    word=wanted[0];destination=(aa[name]&0xF0000000)|((word&0x3FFFFFF)<<2)
    if word>>26!=2 or destination!=aa['__retail_overflow_'+name]:raise ValueError('Path-distance trampoline target changed')
    wanted[0]=(word&0xFC000000)|(((destination-248)>>2)&0x3FFFFFF)
   if b[name]!=wanted:raise ValueError('Path-distance executable body changed: '+name)
   if name not in trampolines:fixed+=1
  if not name.startswith('__retail_overflow_'):
   if bb[name]!=aa[name]:raise ValueError('Path-distance canonical address changed')
   public+=1
 if public!=6045 or fixed!=6052:raise ValueError('Path-distance closure count changed')
 return dict(functions_before=len(a),functions=len(b),canonical_function_addresses_fixed=public,all_canonical_function_addresses_fixed=True,other_bodies_fixed=fixed,private_bodies_moved=sorted(moved),retargeted_trampolines=sorted(trampolines),obsolete_private_body_removed=DELETED,removed_private_bytes=248,ELF_bytes_removed=len(before)-len(actual),strict_image_exclusions=0)

def predict_map(before):
 if sha(before)!=MAP_BEFORE_SHA:raise ValueError('Path-distance map predecessor changed')
 old=b'0x0025af70';new=b'0x0025ae70'
 for line in before.splitlines():
  if old in line and b'__romPos'not in line and b'debugger_overflow_ROM_START'not in line:raise ValueError('Path-distance map ROM symbol context changed')
 result=before.replace(old,new)
 rules=((b'.game_overflow  0x15f00000      0x984 load address',b'.game_overflow  0x15f00000      0x88c load address'),
 (b'0x15f00470      0x37c build/src/game_A28B0.c.o',b'0x15f00470      0x284 build/src/game_A28B0.c.o'),
 (b'0x15f007ec       0x84 build/src/game_D5030.c.o',b'0x15f006f4       0x84 build/src/game_D5030.c.o'),
 (b'0x15f00870       0xac build/src/game_D51B0.c.o',b'0x15f00778       0xac build/src/game_D51B0.c.o'),
 (b'0x15f0091c       0x68 build/src/game_14FF90.c.o',b'0x15f00824       0x68 build/src/game_14FF90.c.o'))
 for a,b in rules:
  if result.count(a)!=1:raise ValueError('Path-distance map section context changed')
  result=result.replace(a,b)
 return result

def check_map(before,actual):
 if predict_map(before)!=actual:raise ValueError('Path-distance literal linker-map prediction mismatch')

MAP_BEFORE_SHA='f67c1a8b5e65c3d94f94fc58439592977a3db9266746b25e8ce546030ec37ea2'
