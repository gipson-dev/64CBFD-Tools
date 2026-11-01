"""Y-plane interpolation: complete direct C, exact bindings and whole-image qualification."""
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,struct
from tools.experiments.game_remaining_donor_candidates import function_span,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
import sys
import tools.pad_generated_object as pad
sys.modules.setdefault("pad_generated_object",pad)
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
FUNCTION,OWNER='func_15185C6C','generated_1B1600'
SOURCE='conker/src/game/generated_1B1600.c'
OBJECT='conker/build/src/game/generated_1B1600.c.o'
ASM='conker/asm/1B1600.s'
BUILD='conker/build/game-y-plane-interpolation-15185C6C-match'
ENTRY,ROM,BODY,SIZE=0x15185C6C,0x1B311C,240,240
RAW_SHA='83071b1795b83aa425c651afe729bca58e63d11f52625e6442960925833f940d'
NORMALIZED_SHA='83071b1795b83aa425c651afe729bca58e63d11f52625e6442960925833f940d'
TRUTH_SHA='83071b1795b83aa425c651afe729bca58e63d11f52625e6442960925833f940d'
BEFORE_ELF_SHA='18be5f55c4862b1dede8af4bb5b4d32ff7cf84c57dfffdf0fa74d8877d76c8f2'
GUARD_SHA='173f3280db84aff3022faeb4a612900e42e80e9cd2d483fdfe90819bdeb63b92'
SNAPSHOT_SHA='c64e5d7325456c599175b7464da69a70dc49f9c42e171a6e11f4e21296b9d299'
BINDINGS={}
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\ntypedef struct {\n    f32 x, y, z;\n    s16 first, second, third;\n    u8 retained[2];\n} ClipVertex;\n\n'
DECLARATIONS='typedef struct {\n    f32 x, y, z;\n    s16 first, second, third;\n    u8 retained[2];\n} ClipVertex;\n\n'
SELECTED='/* Interpolate the Y=0 crossing and advance the output vertex cursor. */\nClipVertex *func_15185C6C(ClipVertex *a, ClipVertex *b, ClipVertex *out) {\n    f32 ratio;\n    ratio = a->y / (a->y - b->y);\n    out->y = 0.0f;\n    out->x = a->x + (b->x - a->x) * ratio;\n    out->z = a->z + (b->z - a->z) * ratio;\n    out->first = a->first + (b->first - a->first) * ratio;\n    out->second = a->second + (b->second - a->second) * ratio;\n    out->third = a->third + (b->third - a->third) * ratio;\n    return out + 1;\n}\n'
NEW_GUARDS=[]

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Y-plane interpolation compiler payload or ABI bindings changed')
 return raw,bindings

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Y-plane interpolation scope changed')
 return checked_payload(raw,bindings)

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Y-plane interpolation inherited guards changed')
 return before

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15185C6C() {\n    return 0;\n}':raise ValueError('Y-plane interpolation placeholder changed')
 if before.count('} ClipVertex;')!=1:raise ValueError('Qualified vertex layout changed')
 return before[:a]+SELECTED.rstrip()+before[b:]

LAYOUT=ASM

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Y-plane interpolation snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Y-plane interpolation frozen input changed: '+n)
  values[n]=value
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Y-plane interpolation predecessor image changed')
 return values

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Y-plane interpolation predictor inputs changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 matches=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(matches)!=1 or matches[0][2][1:3]!=(ENTRY,12):raise ValueError('Y-plane interpolation predecessor symbol changed')
 struct.pack_into('>I',result,matches[0][0]+8,BODY)
 return bytes(result)

def check_image(before,actual,truth):
 expected=predicted_image(before,truth)
 if expected!=actual:raise ValueError('Y-plane interpolation strict whole-image prediction differs')
 definitions=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if definitions!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Y-plane interpolation named definitions changed')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Y-plane interpolation live input changed: '+name)
 return values



PREPARED_SHA='d86a9dc69fba5fb26361ab68b842decc109b528b80e2ca13cc5905b26abcbb50'
EVIDENCE=('before-padded.o', 'qualified-padded.o', 'qualified-padded.s', 'proposed-owner.c', 'proposed-guards.csv', 'selected-semantic-input.c', 'selected-final.c', 'selected-final.o', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_15185C6C.o', 'before-owner.o', 'before-owner.c', 'before-owner-processed.c', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner.c', 'after-owner-processed.c', 'after-owner-diagnostics.txt', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1B1600.c.o', 'make-shadow/src/game/generated_1B1600.c.o.compact', 'make-shadow/src/game/generated_1B1600.c.o.padded.s', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification-v4.json', 'native-interpolation.json')

def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Y-plane interpolation prepared evidence index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Y-plane interpolation prepared evidence set changed')
 for name,wanted in rows.items():
  if sha((output/name).read_bytes())!=wanted:raise ValueError('Y-plane interpolation prepared evidence changed: '+name)
 for name in ('selected-final','before-owner','after-owner','actual-Make'):
  if (output/(name+'-diagnostics.txt')).read_bytes():raise ValueError('Y-plane interpolation owner diagnostics changed')
 if (output/'make-shadow/src/game/generated_1B1600.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Y-plane interpolation actual Make object changed')
 q=json.loads((output/'preparation.json').read_text())
 if not all(q[k] for k in ('complete','normal_O2_g3','owner_diagnostics_empty','actual_Make_object_equals_qualified','strict_whole_image_prediction','all_function_addresses_fixed')) or q['guards']!=0 or q['guard_preimage_controls']!=0 or q['exclusions']!=0:raise ValueError('Y-plane interpolation private preparation failed')
 return rows

def audit(root,output):
 values=check_inputs(root,output,True)
 before=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(before,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
 b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys() or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Y-plane interpolation changed another linked body or address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Y-plane interpolation protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,
  target_words=60,reachable_words=60,frame=0,alignment_words=0,slot_words=60,
  strict_first_link_reproduced=True,guards=0,direct_C_match=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
