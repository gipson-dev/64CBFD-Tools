"""Plane coefficients: complete direct C, exact bindings and whole-image qualification."""
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
FUNCTION,OWNER='func_15049350','game_76710'
SOURCE='conker/src/game_76710.c'
OBJECT='conker/build/src/game_76710.c.o'
ASM='conker/asm/nonmatchings/game_76710/func_15049350.s'
BUILD='conker/build/game-plane-coefficients-15049350-match'
ENTRY,ROM,BODY,SIZE=0x15049350,0x76800,228,240
RAW_SHA='a2f2f18f989174f552dfe71225f145b36290a28d9cc160c3478fd9be0a7727e0'
NORMALIZED_SHA='a2f2f18f989174f552dfe71225f145b36290a28d9cc160c3478fd9be0a7727e0'
TRUTH_SHA='4d7ee5d67dd0e6b0c333a348b4350dd044d9d27bd9dba96d1011419600302ff7'
BEFORE_ELF_SHA='8094c1c9a8fdb238b7fa7419e8e4edb53507e81e8e7594d7543953b42642a6ea'
GUARD_SHA='173f3280db84aff3022faeb4a612900e42e80e9cd2d483fdfe90819bdeb63b92'
SNAPSHOT_SHA='e6335e6df34fa59a52ae33e1fd7e9e1998f4af2fcd6e5d99f639b5080daf9479'
BINDINGS={60: [('R_MIPS_HI16', 'D_800CC210')], 112: [('R_MIPS_LO16', 'D_800CC210')], 120: [('R_MIPS_HI16', 'D_800CC214')], 148: [('R_MIPS_LO16', 'D_800CC214')], 156: [('R_MIPS_HI16', 'D_800CC218')], 176: [('R_MIPS_LO16', 'D_800CC218')], 192: [('R_MIPS_HI16', 'D_800CC21C')], 216: [('R_MIPS_LO16', 'D_800CC21C')]}
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\nextern f32 D_800CC210, D_800CC214, D_800CC218, D_800CC21C;\ntypedef struct { f32 a[3], b[3], c[3]; } PlanePoints;\n'
DECLARATIONS='typedef struct { f32 a[3], b[3], c[3]; } PlanePoints;\n'
SELECTED='/* Publish the unnormalized plane normal and its dot product with point A. */\nvoid func_15049350(PlanePoints points) {\n    f32 abx, aby, abz, acx, acy, acz;\n    f32 nx, ny, nz;\n    abx = points.a[0] - points.b[0];\n    aby = points.a[1] - points.b[1];\n    abz = points.a[2] - points.b[2];\n    acx = points.a[0] - points.c[0];\n    acy = points.a[1] - points.c[1];\n    acz = points.a[2] - points.c[2];\n    nx = aby * acz - abz * acy;\n    D_800CC210 = nx;\n    ny = -abx * acz + abz * acx;\n    D_800CC214 = ny;\n    nz = abx * acy - aby * acx;\n    D_800CC218 = nz;\n    D_800CC21C = nx * points.a[0] + ny * points.a[1] + nz * points.a[2];\n}\n'
NEW_GUARDS=[]

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Plane coefficients compiler payload or ABI bindings changed')
 return raw,bindings

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Plane coefficients scope changed')
 return checked_payload(raw,bindings)

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Plane coefficients inherited guards changed')
 return before

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15049350() {\n    return 0;\n}':raise ValueError('Plane placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 retired='// too many temp vars\n/* Non-matching C placeholders for asm/nonmatchings/game_76710/func_15049350.s. */\n'
 if before.count(retired)!=1:raise ValueError('Plane retired comment changed')
 after=after.replace(retired,'',1)
 return after.replace('/* Generated placeholder declarations. */\ns32 func_15049350();\n/* End generated placeholder declarations. */', '/* Three points passed by value through the original 36-byte aggregate ABI. */\n'+DECLARATIONS.rstrip(),1)

LAYOUT='conker/retail_layout.us.txt'

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Plane coefficients snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Plane coefficients frozen input changed: '+n)
  values[n]=value
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Plane coefficients predecessor image changed')
 return values

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Plane coefficients predictor inputs changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 matches=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(matches)!=1 or matches[0][2][1:3]!=(ENTRY,12):raise ValueError('Plane coefficients predecessor symbol changed')
 struct.pack_into('>I',result,matches[0][0]+8,BODY)
 return bytes(result)

def check_image(before,actual,truth):
 expected=predicted_image(before,truth)
 if expected!=actual:raise ValueError('Plane coefficients strict whole-image prediction differs')
 definitions=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if definitions!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Plane coefficients named definitions changed')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Plane coefficients live input changed: '+name)
 return values



PREPARED_SHA='d7235ccb2229e8ea3666a848d02275ab425670f9649f425689cf04ac2cc89293'
EVIDENCE=('before-padded.o', 'qualified-padded.o', 'qualified-padded.s', 'proposed-owner.c', 'proposed-guards.csv', 'selected-semantic-input.c', 'selected-final.c', 'selected-final.o', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_15049350.o', 'before-owner.o', 'before-owner.c', 'before-owner-processed.c', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner.c', 'after-owner-processed.c', 'after-owner-diagnostics.txt', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_76710.c.o', 'make-shadow/src/game_76710.c.o.compact', 'make-shadow/src/game_76710.c.o.padded.s', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification-v12.json', 'native-plane.json')

def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Plane coefficients prepared evidence index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Plane coefficients prepared evidence set changed')
 for name,wanted in rows.items():
  if sha((output/name).read_bytes())!=wanted:raise ValueError('Plane coefficients prepared evidence changed: '+name)
 for name in ('selected-final','before-owner','after-owner','actual-Make'):
  if (output/(name+'-diagnostics.txt')).read_bytes():raise ValueError('Plane coefficients owner diagnostics changed')
 if (output/'make-shadow/src/game_76710.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Plane coefficients actual Make object changed')
 q=json.loads((output/'preparation.json').read_text())
 if not all(q[k] for k in ('complete','normal_O2_g3','owner_diagnostics_empty','actual_Make_object_equals_qualified','strict_whole_image_prediction','all_function_addresses_fixed')) or q['guards']!=0 or q['guard_preimage_controls']!=0 or q['exclusions']!=0:raise ValueError('Plane coefficients private preparation failed')
 return rows

def audit(root,output):
 values=check_inputs(root,output,True)
 before=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(before,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
 b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys() or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Plane coefficients changed another linked body or address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Plane coefficients protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,
  target_words=57,reachable_words=57,frame=56,alignment_words=3,slot_words=60,
  strict_first_link_reproduced=True,guards=0,direct_C_match=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
