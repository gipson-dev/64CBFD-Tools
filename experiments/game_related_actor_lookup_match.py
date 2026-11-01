"""Ordinal actor-link lookup: exact indexed C and complete owner/image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15072208','game_981E0'
ENTRY,ROM,BODY,SIZE=0x15072208,0x9F6B8,232,232
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
ASM='conker/asm/nonmatchings/game_981E0/func_15072208.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-related-actor-lookup-15072208-match'
RAW_SHA='979ea9947a5c569243ceeac2837e3e1e11a1422b1323f19adebc0b4e34e7b4db'
TRUTH_SHA='b218e6350a540eb26a28ac5cfed60e1141b0c2a9fb3b49e689414d76021a58a9'
BEFORE_ELF_SHA='be164b26d56a087c8d3bf4b58048def90a9040ff95f60ecadd8baaa7f16ead2f'
BINDINGS={4: [('R_MIPS_HI16', 'D_800CC2D0')], 8: [('R_MIPS_LO16', 'D_800CC2D0')], 24: [('R_MIPS_HI16', 'D_800CC2D0')], 28: [('R_MIPS_LO16', 'D_800CC2D0')], 64: [('R_MIPS_HI16', 'D_800CC2D0')], 76: [('R_MIPS_LO16', 'D_800CC2D0')], 68: [('R_MIPS_HI16', 'D_800CC2D0')], 72: [('R_MIPS_LO16', 'D_800CC2D0')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct127 D_800CC2D0[26];\n\n'
SELECTED="/* Return the zero-based ordinal match for the owner's one-based actor link.\n * Slot 25 is the pool sentinel; only slots 0 through 24 are searched. */\nstruct127 *func_15072208(struct127 *owner, s32 ordinal) {\n    s32 ownerIndex;\n    s32 matchIndex;\n    s32 slot;\n\n    ownerIndex = owner - D_800CC2D0 + 1;\n    matchIndex = 0;\n    for (slot = 0; slot < 25; slot++) {\n        if (D_800CC2D0[slot].unk65 == ownerIndex) {\n            if (matchIndex == ordinal) {\n                return &D_800CC2D0[slot];\n            }\n            matchIndex++;\n        }\n    }\n    return NULL;\n}\n"

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Related actor lookup payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='/* Non-matching C placeholders for asm/nonmatchings/game_981E0/func_15072208.s. */\nstruct127 * func_15072208(struct127 *arg0, s32 arg1) {\n    return 0;\n}'
 if before.count(old)!=1:raise ValueError('Related actor lookup placeholder changed')
 return before.replace(old,SELECTED.rstrip(),1)

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
 if a!=b:raise ValueError('Related actor lookup owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Related actor lookup predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,20):raise ValueError('Related actor lookup predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)


SNAPSHOT_SHA='05cbea39bc3eb97ad88ef30216c9c3ac0364f8a5ab172daf10e04185247031d9'
PREPARED_SHA='bf6c925a7450faa17cd07892eb09516b8492dd00091e5acabedbb40a4b66dcfb'
NEIGHBORS=327
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_15072208.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_981E0.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Related actor lookup input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Related actor lookup frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Related actor lookup preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Related actor lookup evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Related actor lookup prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==q['exclusions']==0):raise ValueError('Related actor lookup preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Related actor lookup literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Related actor lookup named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Related actor lookup live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Related actor lookup linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Related actor lookup protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,frame=0,alignment_words=0,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
