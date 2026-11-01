"""Packed scale command guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15076D3C','game_A28B0'
ENTRY,ROM,BODY,SIZE=0x15076D3C,0xA41EC,184,184
SOURCE='conker/src/game_A28B0.c'
OBJECT='conker/build/src/game_A28B0.c.o'
ASM='conker/asm/nonmatchings/game_A28B0/func_15076D3C.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-packed-scale-command-15076D3C-match'
RAW_SHA='998d83eecf7cdddabd3edf636d0ad3c3b9303129e3e887598c72dcd9525be6de'
TRUTH_SHA='af73d56953b8f2dcbafc141bdd9c0f4b7e96590d944a2927217a7e1e86e0565e'
BEFORE_ELF_SHA='78b75a647842e90bf3af632a8761064999a87791aee8e00bbddee5e1ed1b4eb1'
BINDINGS={4: [('R_MIPS_HI16', 'D_800D154C')], 8: [('R_MIPS_LO16', 'D_800D154C')], 92: [('R_MIPS_HI16', 'D_8009A144')], 96: [('R_MIPS_LO16', 'D_8009A144')], 24: [('R_MIPS_HI16', 'D_800D1890')], 28: [('R_MIPS_LO16', 'D_800D1890')], 16: [('R_MIPS_HI16', 'D_800D1891')], 20: [('R_MIPS_LO16', 'D_800D1891')], 44: [('R_MIPS_HI16', 'D_800D1892')], 52: [('R_MIPS_LO16', 'D_800D1892')], 32: [('R_MIPS_HI16', 'D_800D1893')], 40: [('R_MIPS_LO16', 'D_800D1893')], 160: [('R_MIPS_26', 'func_15062BDC')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n'
SELECTED='/* Decode signed little-endian script scales and update the current actor. */\nvoid func_15076D3C(void) {\n    f32 scale = D_8009A144;\n    s32 x;\n    s32 y;\n\n    x = (s16)(D_800D1890 | (D_800D1891 << 8));\n    y = (s16)(D_800D1892 | (D_800D1893 << 8));\n    D_800D154C->xz_scale = (f32)x * scale;\n    D_800D154C->y_scale = (f32)y * scale;\n    D_800D154C->unk154 = D_800D154C->xz_scale;\n    D_800D154C->unk158 = D_800D154C->y_scale;\n    func_15062BDC(D_800D154C, D_800D154C->xz_scale, D_800D154C->y_scale);\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Packed scale command payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 if before.count(OLD_BODY)!=1:raise ValueError('Packed scale predecessor changed')
 return before.replace(OLD_BODY,SELECTED.rstrip(),1)

def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);words=struct.unpack('>46I',raw);result=struct.pack('>46I',*[words[i]for i in ORDER])
 if sha(result)!=NORMALIZED_RAW_SHA:raise ValueError('Packed scale independent schedule changed')
 return result

def normalized_bindings(bindings):
 if bindings!=BINDINGS:raise ValueError('Packed scale bindings changed')
 return{j*4:list(bindings[i*4])for j,i in enumerate(ORDER)if i*4 in bindings}

def derive_guards(raw,bindings):
 normalized=normalized_payload(raw,bindings);target=normalized_bindings(bindings)
 rows=[(i,struct.unpack_from('>I',raw,i)[0],struct.unpack_from('>I',normalized,i)[0])for i in range(0,BODY,4)if raw[i:i+4]!=normalized[i:i+4]or bindings.get(i,[])!=target.get(i,[])]
 if len(rows)!=25:raise ValueError('Packed scale guard count changed')
 return rows

def proposed_guards(before):
 prefix=(OWNER+','+FUNCTION+',').encode()
 if any(v.startswith(prefix)for v in before.splitlines()):raise ValueError('Packed scale guards already present')
 newline=b'\r\n'if b'\r\n'in before else b'\n'
 if not before.endswith(newline):raise ValueError('Packed scale guard newline changed')
 relocation=lambda rows:';'.join(k+':'+n for k,n in rows)or'-'
 result=before;target=normalized_bindings(BINDINGS)
 for at,a,b in NEW_GUARDS:
  line='%s,%s,0x%03X,0x%08X,0x%08X,%s,%s,Normalize packed scale independent coefficient-load schedule,,,false'%(OWNER,FUNCTION,at,a,b,relocation(BINDINGS.get(at,[])),relocation(target.get(at,[])))
  result+=line.encode()+newline
 return result

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
 if a!=b:raise ValueError(('Packed scale owner diagnostics changed',a-b,b-a))
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Packed scale prediction input changed')
 return predict(before,truth)[0]

SNAPSHOT_SHA='b746912870e369f72c13864d1c3a02d179a4f050eed4de84aaf8465389d60068'
PREPARED_SHA='843ab80d8cb2092c695b6ab020175b091b88c1b62c20592a1cb2e3f0b7e33ff3'
NEIGHBORS=210
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_15076D3C.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_A28B0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv', 'closed-guard-proof.json', 'overflow-prediction.json', 'overflow-closure.json', 'before-conker_build_conker.us.map', 'installed-conker_build_conker.us.map', 'linker-map-prediction.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Packed scale command input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Packed scale command frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Packed scale command preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Packed scale command evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Packed scale command prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==25 and q['exclusions']==0):raise ValueError('Packed scale command preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Packed scale literal whole-image mismatch')
 return closure_definitions(before,actual)

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Packed scale command live input changed: '+name)
 before_map=(output/'before-conker_build_conker.us.map').read_bytes();expected_map=predict_map(before_map)if installed else before_map
 if(root/'conker/build/conker.us.map').read_bytes()!=expected_map:raise ValueError('Packed scale live linker map changed')
 return values
def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE]);closure=closure_audit(output/'before-conker_build_conker.us.elf',root/'conker/build/conker.us.elf')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Packed scale protected data changed')
 result=dict(closure,target_words=46,frame=24,alignment_words=0,guards=25,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

NORMALIZED_RAW_SHA='39d6fe73dd47b28b051a4f18785aabc1fc0f696251084edc61055af595851172'
NEW_GUARDS=[(8, 608305152, 1006698496), (12, 2948530196, 3290431488), (16, 1007616000, 608305152), (20, 2448359424, 2948530196), (24, 1007550464, 1007616000), (28, 2446196736, 2448359424), (32, 1007288320, 1007550464), (36, 1032704, 2446196736), (40, 2437545984, 1007288320), (44, 1007222784, 1032704), (48, 30939173, 2437545984), (52, 2435383296, 1007222784), (56, 248832, 30939173), (60, 1645571, 2435383296), (64, 1149444096, 248832), (68, 678400, 1645571), (72, 19609637, 1149444096), (76, 484352, 678400), (80, 1182802336, 19609637), (84, 801795, 484352), (88, 1149718528, 1182802336), (92, 1006698496, 801795), (96, 3290431488, 1149718528), (100, 1182815264, 2353987584), (104, 2353987584, 1182815264)]

ORDER=[0, 1, 23, 24, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 26, 25, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]
OLD_BODY='// ???\nvoid func_15076D3C(void) {\n    s32 temp_a3;\n    s32 tmp2;\n\n    temp_a3 = D_800D1892 | (D_800D1893 << 8);\n    tmp2 = D_800D1890 | (D_800D1891 << 8);\n    D_800D154C->xz_scale = (s16)tmp2 * D_8009A144;\n    D_800D154C->y_scale = (s16)temp_a3 * D_8009A144;\n    D_800D154C->unk154 = D_800D154C->xz_scale;\n    D_800D154C->unk158 = D_800D154C->y_scale;\n    func_15062BDC(D_800D154C, D_800D154C->xz_scale, D_800D154C->y_scale);\n}'

"""Predict removal of one obsolete private overflow body, without exclusions."""
import hashlib,struct
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,SYMBOL,read_c_string
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

BASELINE='78b75a647842e90bf3af632a8761064999a87791aee8e00bbddee5e1ed1b4eb1'
TARGET='func_15076D3C'
DELETED='__retail_overflow_'+TARGET
PH=struct.Struct('>8I')
sha=lambda b:hashlib.sha256(b).hexdigest()

def predict(before,truth):
 assert sha(before)==BASELINE and len(truth)==184
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
 assert symbol_names.count(DELETED)==1 and tuple(removed[1:])==(0x15F006F4,192,2,0,8)
 cut_va,length=removed[1:3];end_va=cut_va+length
 moved={name:row[1]for name,row in zip(symbol_names,symbols)if row[5]==8 and end_va<=row[1]<overflow[3]+overflow[5]}
 assert set(moved)=={'__retail_overflow_func_150781F4','__retail_overflow_func_150A7B80','__retail_overflow_func_150A7D00','__retail_overflow_func_15125490'}
 assert all(name.startswith('__retail_overflow_')for name in moved)
 root_index=symbol_names.index(TARGET);root=symbols[root_index]
 assert tuple(root[1:])==(0x15076D3C,184,18,0,5)
 prefix=bytearray(before[:overflow[4]])
 target_at=elf_slot_offset(before,root[1],184)
 assert struct.unpack_from('>I',prefix,target_at)[0]==0x08000000|((cut_va>>2)&0x3FFFFFF)
 prefix[target_at:target_at+184]=truth

 # Only generated trampoline entries can reference these private implementations.
 trampolines=[]
 by_name=dict(zip(symbol_names,symbols))
 for private,old_address in moved.items():
  canonical=private.removeprefix('__retail_overflow_');row=by_name[canonical]
  at=elf_slot_offset(before,row[1],4);word=struct.unpack_from('>I',before,at)[0]
  if word==0x08000000|((old_address>>2)&0x3FFFFFF):
   struct.pack_into('>I',prefix,at,0x08000000|(((old_address-length)>>2)&0x3FFFFFF));trampolines.append(canonical)
 assert set(trampolines)=={'func_150781F4','func_150A7D00'}
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
 insertion_old=max(row[0]+len(name.encode())+1 for i,(name,row)in enumerate(zip(symbol_names,symbols))if i<root_index and i!=deleted_index and name)
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
   assert tuple(row[1:])==(2469936,0,16,0,65521)
   fresh[1]-=length;changed_definitions.append(name)
  new_symbols.append(fresh)
 assert len(changed_definitions)==6
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
   assert ph[4:6]==[0xA44,0xA44];ph[4]-=length;ph[5]-=length;PH.pack_into(result,at,*ph);changed_program_headers+=1
 assert changed_program_headers==1 and len(result)==len(before)-224
 return bytes(result),dict(deleted_private_body=DELETED,removed_body_bytes=length,moved_private_definitions=moved,retargeted_trampolines=sorted(trampolines),changed_absolute_ROM_symbols=['__romPos','debugger_overflow_ROM_START'],symbol_rows_removed=1,string_bytes_removed=18,ELF_bytes_removed=224,all_other_section_payloads_retained=True,strict_exclusions=0)


def closure_definitions(before,actual):
 old_rows=symbol_rows(before);new_rows=symbol_rows(actual)
 old={name:f for at,name,f,string in old_rows};new={name:f for at,name,f,string in new_rows}
 if set(old)-set(new)!={DELETED}or set(new)-set(old):raise ValueError('Packed scale named symbol set changed')
 moved={'__retail_overflow_func_150781F4','__retail_overflow_func_150A7B80','__retail_overflow_func_150A7D00','__retail_overflow_func_15125490'}
 abs_names={'__romPos','debugger_overflow_ROM_START'};expected=Counter()
 for at,name,f,string in old_rows:
  if name==DELETED:continue
  fields=list(f[1:])
  if name in moved|abs_names:fields[0]-=192
  expected[(name,*fields)]+=1
 if expected!=Counter((name,*f[1:])for at,name,f,string in new_rows):raise ValueError('Packed scale named definition multiset changed')
 return dict(named_definition_multiset_verified=True,removed_definition=DELETED,changed_definitions=sorted(moved|abs_names))

def closure_audit(before_path,actual_path):
 from tools.match_progress import load_elf_functions
 before=before_path.read_bytes();actual=actual_path.read_bytes();closure_definitions(before,actual)
 a,_,aa=load_elf_functions(str(before_path),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(actual_path),'mips-linux-gnu-objdump')
 if len(a)!=6056 or set(a)-set(b)!={DELETED}or set(b)-set(a):raise ValueError('Packed scale executable function inventory changed')
 moved={'__retail_overflow_func_150781F4','__retail_overflow_func_150A7B80','__retail_overflow_func_150A7D00','__retail_overflow_func_15125490'}
 trampolines={'func_150781F4','func_150A7D00'};fixed=public=0
 for name in b:
  expected_address=aa[name]-(192 if name in moved else 0)
  if bb[name]!=expected_address:raise ValueError('Packed scale executable address changed: '+name)
  if name==FUNCTION:
   slot=elf_slot_offset(actual,ENTRY,SIZE)
   if sha(actual[slot:slot+SIZE])!=TRUTH_SHA:raise ValueError('Packed scale target is not retail exact')
  else:
   wanted=a[name][:]
   if name in trampolines:
    word=wanted[0];destination=(aa[name]&0xF0000000)|((word&0x3FFFFFF)<<2)
    if word>>26!=2 or destination!=aa['__retail_overflow_'+name]:raise ValueError('Packed scale trampoline target changed')
    wanted[0]=(word&0xFC000000)|(((destination-192)>>2)&0x3FFFFFF)
   if b[name]!=wanted:raise ValueError('Packed scale executable body changed: '+name)
   if name not in trampolines:fixed+=1
  if not name.startswith('__retail_overflow_'):
   if bb[name]!=aa[name]:raise ValueError('Packed scale canonical address changed')
   public+=1
 if public!=6045 or fixed!=6052:raise ValueError('Packed scale closure count changed')
 return dict(functions_before=len(a),functions=len(b),canonical_function_addresses_fixed=public,all_canonical_function_addresses_fixed=True,other_bodies_fixed=fixed,private_bodies_moved=sorted(moved),retargeted_trampolines=sorted(trampolines),obsolete_private_body_removed=DELETED,removed_private_bytes=192,ELF_bytes_removed=224,strict_image_exclusions=0)

def predict_map(before):
 if sha(before)!=MAP_BEFORE_SHA:raise ValueError('Packed scale map predecessor changed')
 old=b'0x0025b030';new=b'0x0025af70'
 for line in before.splitlines():
  if old in line and b'__romPos'not in line and b'debugger_overflow_ROM_START'not in line:raise ValueError('Packed scale map ROM symbol context changed')
 result=before.replace(old,new)
 rules=((b'.game_overflow  0x15f00000      0xa44 load address',b'.game_overflow  0x15f00000      0x984 load address'),
 (b'0x15f00470      0x43c build/src/game_A28B0.c.o',b'0x15f00470      0x37c build/src/game_A28B0.c.o'),
 (b'0x15f008ac       0x84 build/src/game_D5030.c.o',b'0x15f007ec       0x84 build/src/game_D5030.c.o'),
 (b'0x15f00930       0xac build/src/game_D51B0.c.o',b'0x15f00870       0xac build/src/game_D51B0.c.o'),
 (b'0x15f009dc       0x68 build/src/game_14FF90.c.o',b'0x15f0091c       0x68 build/src/game_14FF90.c.o'))
 for a,b in rules:
  if result.count(a)!=1:raise ValueError('Packed scale map section context changed')
  result=result.replace(a,b)
 return result

def check_map(before,actual):
 if predict_map(before)!=actual:raise ValueError('Packed scale literal linker-map prediction mismatch')

MAP_BEFORE_SHA='19139e6eb3cb32838dba4e8909f0275dc9bc2b9ce99a8efd030e800380070e85'
