"""Lifetime/callback/fade dispatcher: complete C and a closed private byte/register normalization."""
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
FUNCTION,OWNER='func_15154C90','generated_17CAF0'
SOURCE='conker/src/game/generated_17CAF0.c'
OBJECT='conker/build/src/game/generated_17CAF0.c.o'
ASM='conker/asm/17CAF0.s'
BUILD='conker/build/game-lifetime-callback-fade-15154C90-match'
ENTRY,ROM,BODY,SIZE=0x15154C90,0x182140,240,240
RAW_SHA='91684ebae828dec4f850e288ea2b27048aef20c3a971f4e39a7f822314b370a2'
NORMALIZED_SHA='0df54f4e5464cb930e2ac3263afa0098b8997a14f8d7d7cb2f31b8f5774b1b13'
TRUTH_SHA='6ef4a0708ec62b750be1c9e09753cfd28017222b4a817cab988ffaf235145e77'
BEFORE_ELF_SHA='164df1215699e8a1c71efe922af788dbe97ff180ded1ecd2770e73265b09e108'
GUARD_SHA='2a5b2b21c2a8b254d4608fb9c7b9113a755fa1efd3dd73199b4c6ab154235f0e'
SNAPSHOT_SHA='6effb0654d70ee3f5f00fdfa033682ae1415c8aa899b1d977d17d94b03b84f27'
BINDINGS={16: [('R_MIPS_HI16', 'D_800BE9E4')], 36: [('R_MIPS_LO16', 'D_800BE9E4')], 88: [('R_MIPS_HI16', 'D_8008ACC8')], 96: [('R_MIPS_LO16', 'D_8008ACC8')], 216: [('R_MIPS_26', 'func_1516972C')]}
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\nextern s32 D_800BE9E4;\nextern s32 (*D_8008ACC8[])(u8 *);\nvoid func_1516972C(u8 *);\n'
DECLARATIONS='extern s32 D_800BE9E4;\nextern s32 (*D_8008ACC8[])(u8 *);\nvoid func_1516972C(u8 *);\n'
SELECTED='/* Advance a live effect, dispatch its update and limit the fading byte. */\nvoid func_15154C90(u8 *owner) {\n    s8 expired;\n    s32 method;\n    s16 opacity;\n    expired = 0;\n    if (*(u16 *)(owner + 0x24) & 1) {\n        *(s16 *)(owner + 0x22) = (u32)*(s16 *)(owner + 0x22) - (u32)D_800BE9E4;\n        if (*(s16 *)(owner + 0x22) < 0) expired = 1;\n    }\n    if ((method = owner[0x68] & 15) && !expired) {\n        if (!D_8008ACC8[method](owner)) expired = 1;\n    }\n    if ((*(u16 *)(owner + 0x24) & 8) &&\n        *(s16 *)(owner + 0x22) < *(s16 *)(owner + 0x26)) {\n        opacity = *(s16 *)(owner + 0x22) * *(s16 *)(owner + 0x28);\n        if (opacity < owner[0x2E]) owner[0x2E] = opacity;\n    }\n    if (expired) func_1516972C(owner);\n}\n'
NEW_GUARDS=[{'offset': '0x68', 'expected': '0xA3A5001F', 'replacement': '0xA3A5001B', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x7c', 'expected': '0x83A5001F', 'replacement': '0x83A5001B', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x94', 'expected': '0x84820022', 'replacement': '0x84830022', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0x9c', 'expected': '0x004E082A', 'replacement': '0x006E082A', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0xb0', 'expected': '0x01E20019', 'replacement': '0x006F0019', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0xb4', 'expected': '0x00001812', 'replacement': '0x00001012', 'expected_relocations': '-', 'replacement_relocations': '-'}, {'offset': '0xb8', 'expected': '0x0003C400', 'replacement': '0x0002C400', 'expected_relocations': '-', 'replacement_relocations': '-'}]

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Lifetime dispatcher compiler payload or ABI bindings changed')
 return raw,bindings

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError("Lifetime dispatcher normalization scope changed")
 checked_payload(raw,bindings);words=list(struct.unpack('>60I',raw));seen=set()
 for row in NEW_GUARDS:
  at=int(row['offset'],0);i=at//4
  if at%4 or at in seen or words[i]!=int(row['expected'],0)or at in bindings or row['expected_relocations']!='-'or row['replacement_relocations']!='-':raise ValueError('Lifetime dispatcher expected word/relocation contract changed')
  words[i]=int(row['replacement'],0);seen.add(at)
 result=struct.pack('>60I',*words)
 if len(seen)!=7 or sha(result)!=NORMALIZED_SHA:raise ValueError('Lifetime dispatcher normalized payload changed')
 return result,bindings

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Lifetime dispatcher inherited guards changed')
 reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
 if any(x['filename']==OWNER and x['function']==FUNCTION for x in rows):raise ValueError('Lifetime dispatcher guards already exist')
 out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator='\r\n')
 for row in NEW_GUARDS:
  item=dict.fromkeys(fields,'');item.update(filename=OWNER,function=FUNCTION,note='Normalize closed lifetime dispatcher byte spill and V0/V1 register roles',omit='false',**row);writer.writerow(item)
 return before+out.getvalue().encode()

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15154C90() {\n    return 0;\n}':raise ValueError('Lifetime dispatcher placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 if after.count('#include <ultra64.h>')!=1:raise ValueError('Lifetime dispatcher owner include changed')
 return after.replace('#include <ultra64.h>','#include <ultra64.h>\n'+DECLARATIONS,1)

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Lifetime dispatcher snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Lifetime dispatcher frozen input changed: '+n)
  values[n]=value
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Lifetime dispatcher predecessor image changed')
 return values

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Lifetime dispatcher predictor inputs changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 matches=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(matches)!=1 or matches[0][2][1:3]!=(ENTRY,12):raise ValueError('Lifetime dispatcher predecessor symbol changed')
 struct.pack_into('>I',result,matches[0][0]+8,BODY)
 return bytes(result)

def check_image(before,actual,truth):
 expected=predicted_image(before,truth)
 if expected!=actual:raise ValueError('Lifetime dispatcher strict whole-image prediction differs')
 definitions=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if definitions!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Lifetime dispatcher named definitions changed')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Lifetime dispatcher live input changed: '+name)
 return values


PREPARED_SHA='6aa140a0d740ae72b033a3ae01ab651228c3578f7f3f8a79bba30bd778133b83'
EVIDENCE=('before-padded.o','qualified-padded.o','qualified-padded.s',
 'proposed-owner.c','proposed-guards.csv','selected-semantic-input.c',
 'selected-final.c','selected-final.o','selected-final-processed.c',
 'selected-final-diagnostics.txt','original-func_15154C90.o',
 'before-owner.o','before-owner.c','before-owner-processed.c','before-owner-diagnostics.txt',
 'after-owner.o','after-owner.c','after-owner-processed.c','after-owner-diagnostics.txt',
 'actual-Make-plan.txt','Make-commands.json','actual-Make-diagnostics.txt',
 'make-shadow/src/game/generated_17CAF0.c.o',
 'make-shadow/src/game/generated_17CAF0.c.o.compact',
 'make-shadow/src/game/generated_17CAF0.c.o.padded.s',
 'first-link.ld','first-linked.elf','preparation.json',
 'root-parent-v4.json','parent-two-nodes-v6.json','closed-normalization-v5.json',
 'semantic-screen-v1.json','native-lifetime.json')

def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Lifetime dispatcher prepared evidence index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Lifetime dispatcher prepared evidence set changed')
 for name,wanted in rows.items():
  if sha((output/name).read_bytes())!=wanted:raise ValueError('Lifetime dispatcher prepared evidence changed: '+name)
 for name in ('selected-final','before-owner','after-owner','actual-Make'):
  if (output/(name+'-diagnostics.txt')).read_bytes():raise ValueError('Lifetime dispatcher owner diagnostics changed')
 if (output/'make-shadow/src/game/generated_17CAF0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Lifetime dispatcher actual Make object changed')
 q=json.loads((output/'preparation.json').read_text())
 if not all(q[k] for k in ('complete','normal_O2_g3','owner_diagnostics_empty','actual_Make_object_equals_qualified','strict_whole_image_prediction','all_function_addresses_fixed')) or q['guards']!=7 or q['guard_preimage_controls']!=14 or q['exclusions']!=0:raise ValueError('Lifetime dispatcher private preparation failed')
 return rows

def audit(root,output):
 values=check_inputs(root,output,True)
 before=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(before,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
 b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys() or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Lifetime dispatcher changed another linked body or address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Lifetime dispatcher protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,
  target_words=60,reachable_words=60,frame=32,alignment_words=0,slot_words=60,
  strict_first_link_reproduced=True,guards=7,normalization_is_not_merely_scheduling=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
