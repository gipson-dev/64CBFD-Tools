"""Category color mode: direct C, local typed ABI, unchanged owner neighbors."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import function_span,compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_151645C4','game_18D770'
ENTRY,ROM,BODY,SIZE=0x151645C4,0x191A74,432,444
SOURCE='conker/src/game_18D770.c'
OBJECT='conker/build/src/game_18D770.c.o'
ASM='conker/asm/nonmatchings/game_18D770/func_151645C4.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-category-color-mode-151645C4-match'
RAW_SHA='e14dca38ada0746ef210213b37e52f0c0a9844ab64e86b450791d02735e625b4'
TRUTH_SHA='64d23951e86cbb9d6fcaa19150ba80be58e8f2e64dcde498874ca2b04631b751'
BEFORE_ELF_SHA='9623b373b626ff6207c2b5daea4449bec9dfa74a6c7a74762d864a3a487c8e16'
BINDINGS={20: [('R_MIPS_HI16', 'D_800DCDD0')], 28: [('R_MIPS_LO16', 'D_800DCDD0')], 32: [('R_MIPS_HI16', 'D_800BE9F0')], 36: [('R_MIPS_LO16', 'D_800BE9F0')], 96: [('R_MIPS_26', 'func_1511172C')], 112: [('R_MIPS_26', 'func_1515F170')], 120: [('R_MIPS_26', 'func_1511172C')], 136: [('R_MIPS_HI16', 'D_800DCD20')], 168: [('R_MIPS_LO16', 'D_800DCD20')], 128: [('R_MIPS_HI16', 'D_800886F0')], 132: [('R_MIPS_LO16', 'D_800886F0')], 140: [('R_MIPS_HI16', 'D_800B0DF0')], 164: [('R_MIPS_LO16', 'D_800B0DF0')], 144: [('R_MIPS_HI16', 'D_800886F4')], 160: [('R_MIPS_LO16', 'D_800886F4')], 224: [('R_MIPS_HI16', 'D_800BE9F0')], 228: [('R_MIPS_LO16', 'D_800BE9F0')], 296: [('R_MIPS_26', 'func_1515F170')], 304: [('R_MIPS_26', 'func_1511172C')], 320: [('R_MIPS_HI16', 'D_800DCD20')], 344: [('R_MIPS_LO16', 'D_800DCD20')], 312: [('R_MIPS_HI16', 'D_800886F8')], 316: [('R_MIPS_LO16', 'D_800886F8')], 324: [('R_MIPS_HI16', 'D_800B0DF0')], 340: [('R_MIPS_LO16', 'D_800B0DF0')], 392: [('R_MIPS_26', 'func_1511172C')], 408: [('R_MIPS_26', 'func_1511172C')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct100 D_800886F0, D_800886F4, D_800886F8;\nextern struct100 D_800DCD20;\nextern struct104 *D_800B0DF0;\nextern u8 D_800DCDD0;\nextern s32 D_800BE9F0;\nvoid func_1511172C(s32 mode);\nvoid func_1515F170(s32 category, u8 enabled);\n#define CATEGORY_MODE_TINT (*(struct100 *)&D_800DCD20)\n'
DECLARATIONS='extern struct100 D_800886F0, D_800886F4, D_800886F8;\nvoid func_1511172C(s32 mode);\nvoid func_1515F170(s32 category, u8 enabled);\n/* The shared legacy declaration is a pointer; this slot contains inline RGB bytes. */\n#define CATEGORY_MODE_TINT (*(struct100 *)&D_800DCD20)\n'
SELECTED='/* Apply the category-specific mode transition and restore the matching colors. */\nvoid func_151645C4(u8 enabled) {\n    D_800DCDD0 = enabled;\n    if (enabled) {\n        switch (D_800BE9F0) {\n            case 0xB:\n                func_1511172C(4);\n                return;\n\n            case 6:\n                func_1515F170(10, 1);\n                func_1511172C(4);\n                /* fall through */\n            case 0x39:\n                CATEGORY_MODE_TINT.unk0 = D_800886F0.unk0;\n                CATEGORY_MODE_TINT.unk1 = D_800886F0.unk1;\n                CATEGORY_MODE_TINT.unk2 = D_800886F0.unk2;\n                D_800B0DF0->unk5 = D_800886F4.unk0;\n                D_800B0DF0->unk6 = D_800886F4.unk1;\n                D_800B0DF0->unk7 = D_800886F4.unk2;\n                break;\n            case 7:\n            case 0xC:\n                break;\n            default:\n                return;\n        }\n    } else {\n        switch (D_800BE9F0) {\n            case 6:\n                func_1515F170(10, 0);\n                /* fall through */\n            case 7:\n            case 0xC:\n            case 0x39:\n                func_1511172C(6);\n                CATEGORY_MODE_TINT.unk0 = D_800886F8.unk0;\n                CATEGORY_MODE_TINT.unk1 = D_800886F8.unk1;\n                CATEGORY_MODE_TINT.unk2 = D_800886F8.unk2;\n                D_800B0DF0->unk5 = 0xFF;\n                D_800B0DF0->unk6 = 0xFF;\n                D_800B0DF0->unk7 = 0xFF;\n                break;\n            case 0xB:\n                func_1511172C(6);\n                return;\n            case 0x29:\n                func_1511172C(1);\n                break;\n            default:\n                return;\n        }\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Category color mode payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_151645C4() {\n    return 0;\n}':raise ValueError('Category mode placeholder changed')
 result=before[:a]+SELECTED.rstrip()+before[b:]
 result=result.replace('s32 func_151645C4();','void func_151645C4(u8 enabled);',1)
 result=result.replace('#include "variables.h"','#include "variables.h"\n\n'+DECLARATIONS,1)
 return result.replace('// loop\n/* Non-matching C placeholders for asm/nonmatchings/game_18D770/func_151645C4.s. */\n','',1)
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
 if a!=b:raise ValueError('Category mode owner diagnostics changed')
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)
# Closed BFD hash-order collision; preserve every named symbol field and string.
METADATA_PAIR=(0x2BFD34,('D_800886F4','D_800AB494'))
def reorder_metadata(before,result):
 first,names=METADATA_PAIR;rows={p:(name,fields,start)for p,name,fields,start in symbol_rows(before)}
 group=[rows[first+16*i]for i in range(2)]
 if tuple(name for name,_,_ in group)!=names:raise ValueError('Category mode metadata pair changed')
 strings=b''.join(name.encode()+b'\0'for name in names);start=group[0][2]
 if before[start:start+len(strings)]!=strings:raise ValueError('Category mode metadata strings changed')
 offset=0;name_offset=group[0][1][0]
 for slot,index in enumerate((1,0)):
  name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
 if offset!=len(strings):raise ValueError('Category mode metadata extent changed')
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Category mode predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Category mode predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 reorder_metadata(before,result)
 return bytes(result)


SNAPSHOT_SHA='04ffc3a1f51a41e9b738981d248a69e734caf35a36e98191d3a5f555e93280b9'
PREPARED_SHA='5b26f427169e7149d09ac8971ff86cce13eda7beb23d3d5cb710c0473ca31306'
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_151645C4.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_18D770.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'mode-return-return-struct.o', 'cached-object-negative.o', 'caller-census.json')
def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Category color mode input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Category color mode frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Category color mode preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Category color mode evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Category color mode prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==77 and q['guards']==q['exclusions']==0):raise ValueError('Category color mode preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Category color mode literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Category color mode named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Category color mode live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Category color mode linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Category color mode protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=108,frame=24,alignment_words=3,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
