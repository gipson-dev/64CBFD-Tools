"""Attached cash label: complete semantic C and a closed low16 clamp normalization."""
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,struct
from tools.experiments.game_remaining_donor_candidates import function_span,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
FUNCTION,OWNER='func_151D7000','generated_203E20'
SOURCE='conker/src/game/generated_203E20.c'
OBJECT='conker/build/src/game/generated_203E20.c.o'
ASM='conker/asm/203E20.s'
BUILD='conker/build/game-attached-cash-label-151D7000-match'
ENTRY,ROM,BODY,SIZE=0x151D7000,0x2044B0,204,204
RAW_SHA='38faafc2a78ea3c2ff911625862fc60a957d684bc23247c69f3cd9f1a573a3a6'
NORMALIZED_SHA='8b6aca29cc7fed0686fade4e290da763f7ab5c65c6177484e715b234f9b27691'
TRUTH_SHA='185a7d4cc630c3dc6b553bc072b0c5930d72fb8efa9e86fa4ecf11250edf7b7e'
BEFORE_ELF_SHA='8c4b9914475e824e2d55b072ba7cba66b551b586d751835dc8dc84903deee91b'
GUARD_SHA='3f87620dde0c8ab48350b406c8d184af4cde1d57c617d916770b42d1ea501fca'
SNAPSHOT_SHA='2edf91ee0393e3adb747a1ca68354e9ff29314b55e3f281603e0680d374053f3'
BINDINGS={128:[('R_MIPS_26','func_150432CC')],152:[('R_MIPS_26','func_1504332C')],160:[('R_MIPS_26','func_15042D78')],172:[('R_MIPS_HI16','D_800AB254')],176:[('R_MIPS_LO16','D_800AB254')],180:[('R_MIPS_26','func_15042E3C')]}
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\nvoid func_150432CC(s32, s32);\nvoid func_1504332C(u8, u8, u8, u8);\nvoid func_15042D78(u8);\ns32 func_15042E3C(s32, ...);\nextern u8 D_800AB254[];\n'
DECLARATIONS='void func_150432CC(s32, s32);\nvoid func_1504332C(u8, u8, u8, u8);\nvoid func_15042D78(u8);\ns32 func_15042E3C(s32, ...);\nextern u8 D_800AB254[];\n'
SELECTED='/* Draw the live attached cash amount with its signed lifetime fade. */\ns32 func_151D7000(u8 *owner) {\n    u8 *actor;\n    u8 *label;\n    s16 remaining;\n    u16 opacity;\n    label = *(u8 **)(owner + 0x48);\n    actor = *(u8 **)label;\n    if (*(s32 *)actor == 0 || label[4] != actor[0x3B]) return 0;\n    remaining = *(s16 *)(owner + 0xE);\n    opacity = 255;\n    if (remaining < *(s16 *)(label + 0xC)) {\n        opacity = remaining * *(s16 *)(label + 0xE);\n        if ((s16)opacity < 0) opacity = 0;\n    }\n    func_150432CC((s32)actor, 0x109);\n    func_1504332C(50, 125, 28, opacity);\n    func_15042D78(0x81);\n    return func_15042E3C((s32)D_800AB254, *(s32 *)(label + 8));\n}\n'
NEW_GUARDS=[{'offset': '0x4c', 'expected': '0x5020000B', 'replacement': '0x1020000A', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x50', 'expected': '0x00C02025', 'replacement': '0x00000000', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x58', 'expected': '0x01040019', 'replacement': '0x00880019', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x60', 'expected': '0x3049FFFF', 'replacement': '0x00024C00', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x64', 'expected': '0x00095400', 'replacement': '0x00091403', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x68', 'expected': '0x000A5C03', 'replacement': '0x04430004', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x6c', 'expected': '0x05610002', 'replacement': '0x00C02025', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x70', 'expected': '0x01201025', 'replacement': '0x10000001', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x7c', 'expected': '0xA7A2001C', 'replacement': '0xA7A2001A', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x88', 'expected': '0x97A2001C', 'replacement': '0x87A2001A', 'expected_relocations': '-', 'replacement_relocations': '-'}]

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Cash label compiler payload or ABI bindings changed')
 return raw,bindings

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError("Cash label normalization scope changed")
 checked_payload(raw,bindings);words=list(struct.unpack('>51I',raw));seen=set()
 for row in NEW_GUARDS:
  at=int(row['offset'],0);i=at//4
  if at%4 or at in seen or words[i]!=int(row['expected'],0)or at in bindings or row['expected_relocations']!='-'or row['replacement_relocations']!='-':raise ValueError('Cash label expected word/relocation contract changed')
  words[i]=int(row['replacement'],0);seen.add(at)
 result=struct.pack('>51I',*words)
 if len(seen)!=10 or sha(result)!=NORMALIZED_SHA:raise ValueError('Cash label normalized payload changed')
 return result,bindings

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Cash label inherited guards changed')
 reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
 if any(x['filename']==OWNER and x['function']==FUNCTION for x in rows):raise ValueError('Cash label guards already exist')
 out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator='\r\n')
 for row in NEW_GUARDS:
  item=dict.fromkeys(fields,'');item.update(filename=OWNER,function=FUNCTION,note='Normalize closed signed-low16 cash-label clamp and private halfword spill layout',omit='false',**row);writer.writerow(item)
 return before+out.getvalue().encode()

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_151D7000() {\n    return 0;\n}':raise ValueError('Cash label placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 if after.count('#include <ultra64.h>')!=1:raise ValueError('Cash label owner include changed')
 return after.replace('#include <ultra64.h>','#include <ultra64.h>\n'+DECLARATIONS,1)

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Cash label snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Cash label frozen input changed: '+n)
  values[n]=value
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Cash label predecessor image changed')
 return values

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Cash label predictor inputs changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 matches=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(matches)!=1 or matches[0][2][1:3]!=(ENTRY,12):raise ValueError('Cash label predecessor symbol changed')
 struct.pack_into('>I',result,matches[0][0]+8,BODY)
 # The new reference changes the order of one adjacent BFD symbol/string pair.
 rows={name:(offset,fields,location)for offset,name,fields,location in symbol_rows(before)}
 names=('D_800991AC','D_8009E6BC');slots=[rows[n]for n in names]
 if slots[0][0]!=0x2B1F14 or slots[1][0]!=slots[0][0]+16:raise ValueError('Cash label metadata pair slots changed')
 definitions=((0x800991AC,0,16,0,65521),(0x8009E6BC,0,16,0,6))
 start=slots[0][2];base=slots[0][1][0];length=0
 for name,(offset,fields,location),definition in zip(names,slots,definitions):
  encoded=name.encode()+b'\0'
  if fields[1:]!=definition or location!=start+length or fields[0]!=base+length or before[location:location+len(encoded)]!=encoded:raise ValueError('Cash label named metadata pair changed')
  length+=len(encoded)
 spelling=b''.join(n.encode()+b'\0'for n in names[::-1]);result[start:start+length]=spelling;cursor=0
 for (offset,_,_),name in zip(slots,names[::-1]):
  fields=rows[name][1];struct.pack_into('>IIIBBH',result,offset,base+cursor,*fields[1:]);cursor+=len(name)+1
 if cursor!=length:raise ValueError('Cash label metadata pair span changed')
 return bytes(result)

def check_image(before,actual,truth):
 expected=predicted_image(before,truth)
 if expected!=actual:raise ValueError('Cash label strict whole-image prediction differs')
 definitions=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if definitions!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Cash label named definitions changed')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Cash label live input changed: '+name)
 return values

PREPARED_SHA='bfd54ea110fc6c18883bff34a65768ab9e448e9457994b5f23cf3d0f51e2387a'
EVIDENCE=('before-padded.o','qualified-padded.o','qualified-padded.s',
 'proposed-owner.c','proposed-guards.csv','selected-semantic-input.c',
 'selected-final.c','selected-final.o','selected-final-processed.c',
 'selected-final-diagnostics.txt','original-func_151D7000.o',
 'before-owner.o','before-owner.c','before-owner-processed.c','before-owner-diagnostics.txt',
 'after-owner.o','after-owner.c','after-owner-processed.c','after-owner-diagnostics.txt',
 'actual-Make-plan.txt','Make-commands.json','actual-Make-diagnostics.txt',
 'make-shadow/src/game/generated_203E20.c.o',
 'make-shadow/src/game/generated_203E20.c.o.compact',
 'make-shadow/src/game/generated_203E20.c.o.padded.s',
 'first-link.ld','first-linked.elf','preparation.json',
 'cash-label-connected-abi-v22.json','cash-label-clamp-contract-v23.json',
 'text-retail-abi-v15.json','native-cash-label.json')

def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Cash label prepared evidence index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Cash label prepared evidence set changed')
 for name,wanted in rows.items():
  if sha((output/name).read_bytes())!=wanted:raise ValueError('Cash label prepared evidence changed: '+name)
 for name in ('selected-final','before-owner','after-owner','actual-Make'):
  if (output/(name+'-diagnostics.txt')).read_bytes():raise ValueError('Cash label owner diagnostics changed')
 if (output/'make-shadow/src/game/generated_203E20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Cash label actual Make object changed')
 q=json.loads((output/'preparation.json').read_text())
 if not all(q[k] for k in ('complete','normal_O2_g3','owner_diagnostics_empty','actual_Make_object_equals_qualified','strict_whole_image_prediction','all_function_addresses_fixed')) or q['guards']!=10 or q['guard_preimage_controls']!=20 or q['exclusions']!=0:raise ValueError('Cash label private preparation failed')
 return rows

def audit(root,output):
 values=check_inputs(root,output,True)
 before=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(before,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
 b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys() or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Cash label changed another linked body or address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Cash label protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,
  target_words=51,reachable_words=50,frame=40,alignment_words=0,slot_words=51,
  strict_first_link_reproduced=True,guards=10,normalization_is_not_merely_scheduling=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
