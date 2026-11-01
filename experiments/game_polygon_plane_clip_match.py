"""Polygon plane clip: complete direct C, exact bindings and whole-image qualification."""
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
FUNCTION,OWNER='func_15185DD4','generated_1B1600'
SOURCE='conker/src/game/generated_1B1600.c'
OBJECT='conker/build/src/game/generated_1B1600.c.o'
ASM='conker/asm/1B1600.s'
BUILD='conker/build/game-polygon-plane-clip-15185DD4-match'
ENTRY,ROM,BODY,SIZE=0x15185DD4,0x1B3284,336,336
RAW_SHA='331a3e51bf13fc97f98238442c7adf73af459759e38c6f9f3b7d5b27fd019b44'
NORMALIZED_SHA='331a3e51bf13fc97f98238442c7adf73af459759e38c6f9f3b7d5b27fd019b44'
TRUTH_SHA='6b9814498cb4e2f2e2744af4fa26330816840e42c3ece47e545ea72214e0fa69'
BEFORE_ELF_SHA='16fbd460baf2f940cd902c41ab76754220d15a5148ad63c4b0717d8562f8b00d'
GUARD_SHA='173f3280db84aff3022faeb4a612900e42e80e9cd2d483fdfe90819bdeb63b92'
SNAPSHOT_SHA='40aee0d2978ceb0d589691e0bd856bc475e7e618f73cf9bfeb1503045627439f'
BINDINGS={60: [('R_MIPS_HI16', 'D_8008D498')], 84: [('R_MIPS_LO16', 'D_8008D498')], 64: [('R_MIPS_HI16', 'D_8008D4C0')], 88: [('R_MIPS_LO16', 'D_8008D4C0')]}
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\ntypedef struct {\n    f32 x, y, z;\n    s16 first, second, third;\n    u8 retained[2];\n} ClipVertex;\ntypedef ClipVertex *(*ClipInterpolate)(ClipVertex *, ClipVertex *, ClipVertex *);\ntypedef s32 (*ClipClassify)(ClipVertex *);\nextern ClipInterpolate D_8008D498[];\nextern ClipClassify D_8008D4C0[];\n\n'
DECLARATIONS='typedef ClipVertex *(*ClipInterpolate)(ClipVertex *, ClipVertex *, ClipVertex *);\ntypedef s32 (*ClipClassify)(ClipVertex *);\nextern ClipInterpolate D_8008D498[];\nextern ClipClassify D_8008D4C0[];\n\n'
SELECTED="/* Clip a closed polygon against the selected plane and return the output cursor. */\nClipVertex *func_15185DD4(ClipVertex *vertices, s32 count, u32 plane, ClipVertex *out) {\n    ClipVertex *current;\n    /* Preserve the guest's word-address calculation even when count is nonpositive. */\n    ClipVertex *previous = (ClipVertex *)((u32)count * sizeof(ClipVertex) + (u32)vertices - sizeof(ClipVertex));\n    ClipInterpolate interpolate = D_8008D498[plane];\n    ClipClassify classify = D_8008D4C0[plane];\n    s32 i;\n    current = vertices;\n\n    for (i = 0; i < count; i++) {\n        if (classify(current)) {\n            if (classify(previous)) {\n                *out++ = *current;\n            } else {\n                out = interpolate(previous, current, out);\n                *out++ = *current;\n            }\n        } else if (classify(previous)) {\n            out = interpolate(previous, current, out);\n        }\n        previous = current;\n        current++;\n    }\n    return out;\n}\n"
NEW_GUARDS=[]

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Polygon plane clip compiler payload or ABI bindings changed')
 return raw,bindings

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Polygon plane clip scope changed')
 return checked_payload(raw,bindings)

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Polygon plane clip inherited guards changed')
 return before

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15185DD4() {\n    return 0;\n}':raise ValueError('Polygon plane clip placeholder changed')
 if before.count('} ClipVertex;')!=1:raise ValueError('Qualified vertex layout changed')
 return before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]

LAYOUT=ASM

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Polygon plane clip snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Polygon plane clip frozen input changed: '+n)
  values[n]=value
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Polygon plane clip predecessor image changed')
 return values

METADATA_PAIR=(0x2D3944,('D_8008D4C0','D_80088740'),0x310D09)

def reorder_metadata(before,result):
 at,names,string_at=METADATA_PAIR
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 group=[rows[at+16*i]for i in range(2)]
 if tuple(n for n,f,s in group)!=names or tuple(s for n,f,s in group)!=(string_at,string_at+11):raise ValueError('Polygon clipper metadata pair changed')
 expected=b''.join(n.encode()+b'\0'for n in names)
 if before[string_at:string_at+22]!=expected:raise ValueError('Polygon clipper metadata strings changed')
 result[string_at:string_at+22]=b''.join(n.encode()+b'\0'for n in reversed(names))
 for i in range(2):struct.pack_into('>IIIBBH',result,at+16*i,group[i][1][0],*group[1-i][1][1:])
 return result

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Polygon plane clip predictor inputs changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 matches=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(matches)!=1 or matches[0][2][1:3]!=(ENTRY,12):raise ValueError('Polygon plane clip predecessor symbol changed')
 struct.pack_into('>I',result,matches[0][0]+8,BODY)
 return bytes(reorder_metadata(before,result))

def check_image(before,actual,truth):
 expected=predicted_image(before,truth)
 if expected!=actual:raise ValueError('Polygon plane clip strict whole-image prediction differs')
 definitions=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if definitions!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Polygon plane clip named definitions changed')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Polygon plane clip live input changed: '+name)
 return values



PREPARED_SHA='39cdfa6e303cbaa4ceec9434f312a6223a470532edc293d4e75bb2a66bc8e5f0'
EVIDENCE=('before-padded.o', 'qualified-padded.o', 'qualified-padded.s', 'proposed-owner.c', 'proposed-guards.csv', 'selected-semantic-input.c', 'selected-final.c', 'selected-final.o', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_15185DD4.o', 'before-owner.o', 'before-owner.c', 'before-owner-processed.c', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner.c', 'after-owner-processed.c', 'after-owner-diagnostics.txt', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1B1600.c.o', 'make-shadow/src/game/generated_1B1600.c.o.compact', 'make-shadow/src/game/generated_1B1600.c.o.padded.s', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification-v10.json', 'native-polygon.json')

def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Polygon plane clip prepared evidence index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Polygon plane clip prepared evidence set changed')
 for name,wanted in rows.items():
  if sha((output/name).read_bytes())!=wanted:raise ValueError('Polygon plane clip prepared evidence changed: '+name)
 for name in ('selected-final','before-owner','after-owner','actual-Make'):
  if (output/(name+'-diagnostics.txt')).read_bytes():raise ValueError('Polygon plane clip owner diagnostics changed')
 if (output/'make-shadow/src/game/generated_1B1600.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Polygon plane clip actual Make object changed')
 q=json.loads((output/'preparation.json').read_text())
 if not all(q[k] for k in ('complete','normal_O2_g3','owner_diagnostics_empty','actual_Make_object_equals_qualified','strict_whole_image_prediction','all_function_addresses_fixed')) or q['guards']!=0 or q['guard_preimage_controls']!=0 or q['exclusions']!=0:raise ValueError('Polygon plane clip private preparation failed')
 return rows

def audit(root,output):
 values=check_inputs(root,output,True)
 before=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(before,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
 b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys() or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Polygon plane clip changed another linked body or address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Polygon plane clip protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,
  target_words=84,reachable_words=84,frame=56,alignment_words=0,slot_words=84,
  strict_first_link_reproduced=True,guards=0,direct_C_match=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
