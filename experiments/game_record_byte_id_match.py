"""Lifetime/callback/fade dispatcher: complete C and a closed private byte/register normalization."""
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,struct
from tools.experiments.game_remaining_donor_candidates import function_span,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
import sys
import tools.pad_generated_object as pad
sys.modules.setdefault("pad_generated_object",pad)
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
FUNCTION,OWNER='func_15004BF0','game_30E90'
SOURCE='conker/src/game_30E90.c'
OBJECT='conker/build/src/game_30E90.c.o'
ASM='conker/asm/nonmatchings/game_30E90/func_15004BF0.s'
BUILD='conker/build/game-record-byte-id-15004BF0-match'
ENTRY,ROM,BODY,SIZE=0x15004BF0,0x320A0,240,240
RAW_SHA='544b07fdb0d4cc0f80f8ac3839d82c217e1ee76ee841f39af95a4d23f9991d91'
NORMALIZED_SHA='544b07fdb0d4cc0f80f8ac3839d82c217e1ee76ee841f39af95a4d23f9991d91'
TRUTH_SHA='3dfee8b5797034998503ea649788eec3b7b71a0e3256a25dd517b56e7c8cb384'
BEFORE_ELF_SHA='a0da86a005be514b9ea4c80fdbcd6c80e506804436f61f85566499c59ae0f9cc'
GUARD_SHA='173f3280db84aff3022faeb4a612900e42e80e9cd2d483fdfe90819bdeb63b92'
SNAPSHOT_SHA='28326a6c8f815db7e038b4a419b6bb2c9a892fbb1a313877cbe367cbd7d78a12'
BINDINGS={8: [('R_MIPS_HI16', 'D_800DBF00')], 20: [('R_MIPS_LO16', 'D_800DBF00')], 12: [('R_MIPS_HI16', 'D_800DBEF0')], 16: [('R_MIPS_LO16', 'D_800DBEF0')], 28: [('R_MIPS_HI16', 'D_800DBEF4')], 44: [('R_MIPS_LO16', 'D_800DBEF4')], 4: [('R_MIPS_HI16', 'D_800DBF00')], 124: [('R_MIPS_LO16', 'D_800DBF00')], 128: [('R_MIPS_HI16', 'D_800DBEF0')], 132: [('R_MIPS_LO16', 'D_800DBEF0')], 156: [('R_MIPS_HI16', 'D_800DBEF4')], 160: [('R_MIPS_LO16', 'D_800DBEF4')]}
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\n#include "variables.h"\ntypedef struct { u8 reserved[0x72]; u8 id; u8 tail[0x2D]; } ByteIdRecordView;\n'
DECLARATIONS='typedef struct { u8 reserved[0x72]; u8 id; u8 tail[0x2D]; } ByteIdRecordView;\n'
SELECTED='/* Search record byte IDs in either direction, retaining saturation fallbacks. */\ns32 func_15004BF0(s32 descending) {\n    s32 id;\n    s32 index;\n    /* After choosing direction, retain the scan boundary in the argument. */\n    if (descending == 0) {\n        id = 1;\n        for (index = descending = D_800DBF00; index < D_800DBEF0; index++) {\n            if (id == ((ByteIdRecordView *)D_800DBEF4)[index].id) {\n                id++;\n                index = descending - 1;\n            }\n            if (id >= 256) { id = 255; break; }\n        }\n    } else {\n        descending = 255 - D_800DBF00;\n        id = descending;\n        for (index = 0; index < D_800DBEF0; index++) {\n            if (id == ((ByteIdRecordView *)D_800DBEF4)[index].id) {\n                id--;\n                index = -1;\n            }\n            if (id <= 0) { id = descending; break; }\n        }\n    }\n    return id;\n}\n'
NEW_GUARDS=[]

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Lifetime dispatcher compiler payload or ABI bindings changed')
 return raw,bindings

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Byte-ID search scope changed')
 return checked_payload(raw,bindings)

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Byte-ID inherited guards changed')
 return before

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15004BF0() {\n    return 0;\n}':raise ValueError('Byte-ID placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 retired='/* Non-matching C placeholders for asm/nonmatchings/game_30E90/func_15004BF0.s. */\n'
 if before.count(retired)!=1:raise ValueError('Byte-ID retired placeholder comment changed')
 after=after.replace(retired,'',1)
 return after.replace('s32 func_15004BF0();','s32 func_15004BF0(s32 descending);').replace('#include "variables.h"','#include "variables.h"\n'+DECLARATIONS,1)

LAYOUT='conker/retail_layout.us.txt'

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



PREPARED_SHA='2d4076325229e2b3f6ede9af21607a5f120aab09735886151f607455bda08dcd'
EVIDENCE=('before-padded.o','qualified-padded.o','qualified-padded.s',
 'proposed-owner.c','proposed-guards.csv','selected-semantic-input.c',
 'selected-final.c','selected-final.o','selected-final-processed.c',
 'selected-final-diagnostics.txt','original-func_15004BF0.o',
 'before-owner.o','before-owner.c','before-owner-processed.c','before-owner-diagnostics.txt',
 'after-owner.o','after-owner.c','after-owner-processed.c','after-owner-diagnostics.txt',
 'actual-Make-plan.txt','Make-commands.json','actual-Make-diagnostics.txt',
 'make-shadow/src/game_30E90.c.o',
 'make-shadow/src/game_30E90.c.o.compact',
 'make-shadow/src/game_30E90.c.o.padded.s',
 'first-link.ld','first-linked.elf','preparation.json',
 'search-qualification-v9.json','exact-owner-v10.json','native-byte-id.json',
 'load-order-v8.json')

def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Lifetime dispatcher prepared evidence index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Lifetime dispatcher prepared evidence set changed')
 for name,wanted in rows.items():
  if sha((output/name).read_bytes())!=wanted:raise ValueError('Lifetime dispatcher prepared evidence changed: '+name)
 for name in ('selected-final','before-owner','after-owner','actual-Make'):
  if (output/(name+'-diagnostics.txt')).read_bytes():raise ValueError('Lifetime dispatcher owner diagnostics changed')
 if (output/'make-shadow/src/game_30E90.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Lifetime dispatcher actual Make object changed')
 q=json.loads((output/'preparation.json').read_text())
 if not all(q[k] for k in ('complete','normal_O2_g3','owner_diagnostics_empty','actual_Make_object_equals_qualified','strict_whole_image_prediction','all_function_addresses_fixed')) or q['guards']!=0 or q['guard_preimage_controls']!=0 or q['exclusions']!=0:raise ValueError('Lifetime dispatcher private preparation failed')
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
  target_words=60,reachable_words=60,frame=0,alignment_words=0,slot_words=60,
  strict_first_link_reproduced=True,guards=0,direct_C_match=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
