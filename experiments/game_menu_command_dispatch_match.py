"""Menu command dispatch guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_150B6BC0','generated_E4070'
ENTRY,ROM,BODY,SIZE=0x150B6BC0,0xE4070,208,208
SOURCE='conker/src/game/generated_E4070.c'
OBJECT='conker/build/src/game/generated_E4070.c.o'
ASM='conker/asm/E4070.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-menu-command-dispatch-150B6BC0-match'
RAW_SHA='3139f4c4d33bd2d975d765d43964060a508346d400fbd1e86892c4efb3223ef3'
TRUTH_SHA='2b971ba24d5680b21c35bd003b6376db1fbc9ea4cd75e865ddf4aa8280da0b09'
BEFORE_ELF_SHA='4f536ba38e824b7487c0dbe0483303c7770732fc0354053c92e0e378f304133c'
BINDINGS={12: [('R_MIPS_HI16', 'D_800D9890')], 16: [('R_MIPS_LO16', 'D_800D9890')], 36: [('R_MIPS_HI16', '.rodata')], 44: [('R_MIPS_LO16', '.rodata')], 56: [('R_MIPS_26', 'func_150B6C90')], 72: [('R_MIPS_26', 'func_150B6D34')], 88: [('R_MIPS_26', 'func_150B6D78')], 104: [('R_MIPS_26', 'func_150B7484')], 120: [('R_MIPS_26', 'func_150B7560')], 136: [('R_MIPS_26', 'func_150B765C')], 152: [('R_MIPS_26', 'func_150B77A8')], 168: [('R_MIPS_26', 'func_150B768C')], 184: [('R_MIPS_26', 'func_150B791C')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[]
HEADERS='#include <ultra64.h>\nextern u8 D_800D9890;\nvoid func_150B6C90(void);\nvoid func_150B6D34(void);\nvoid func_150B6D78(void);\nvoid func_150B7484(void);\ns32 func_150B7560(void);\ns32 func_150B765C(void);\ns32 func_150B768C(void);\ns32 func_150B77A8(void);\ns32 func_150B791C(void);\n'
SELECTED='/* Run one pending menu command; state 3 and out-of-range states are idle. */\nvoid func_150B6BC0(s32 unusedView) {\n    switch (D_800D9890) {\n    case 1:\n        func_150B6C90();\n        break;\n    case 2:\n        func_150B6D34();\n        break;\n    case 4:\n        func_150B6D78();\n        break;\n    case 5:\n        func_150B7484();\n        break;\n    case 6:\n        func_150B7560();\n        break;\n    case 7:\n        func_150B765C();\n        break;\n    case 8:\n        func_150B77A8();\n        break;\n    case 9:\n        func_150B768C();\n        break;\n    case 10:\n        func_150B791C();\n        break;\n    default: break;\n    }\n}\n'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Menu command dispatch payload/bindings changed')
 return raw,bindings
RODATA_SYMBOL='jtbl_8009FD00_game'
TABLE_OFFSETS=(56,72,192,88,104,120,136,152,168,184)

def recovered_owner(before):
 old='s32 func_150B6BC0() {\n    return 0;\n}'
 if before.count(old)!=1:raise ValueError('Menu dispatcher placeholder changed')
 declarations='\n'.join(HEADERS.splitlines()[2:])+'\n\n'
 return before.replace(old,declarations+SELECTED.rstrip(),1)

def proposed_guards(before):return before

def proposed_makefile(before):
 old='$(BUILD_DIR)/$(SRC_DIR)/game/generated_E4070.c.o: OPT_FLAGS := -O2 -g3 -Wo,-loopunroll,0'
 if before.count(old)!=1 or 'RETAIL_RODATA_SYMBOL := jtbl_8009FD00_game' in before:raise ValueError('Menu owner Make profile changed')
 newline='\r\n'if'\r\n'in before else'\n'
 return before.replace(old,old+newline+'$(BUILD_DIR)/$(SRC_DIR)/game/generated_E4070.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009FD00_game',1)

def check_owner_pools(before,after):
 old,new=normalized_pools(before),normalized_pools(after)
 expected=(bytes(48),tuple((4*i,FUNCTION,at)for i,at in enumerate(TABLE_OFFSETS)))
 if old['.rodata']is not None or new['.rodata']!=expected or old['.data']!=new['.data']:raise ValueError(('Dispatcher pool geometry changed',old,new))
 return dict(compiler_table_bytes=48,entries=10,table_offsets=list(TABLE_OFFSETS),two_padding_words_zero=True,only_new_pool_is_verified_table=True)

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
 if a!=b:raise ValueError(('Menu owner diagnostics changed',a-b,b-a))
 return dict(before=sum(a.values()),after=sum(b.values()),removed=0)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Menu command dispatch predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Menu command dispatch predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 return bytes(result)

SNAPSHOT_SHA='03395b58a328a12893de9a0527a2635351f9b6d3f398c22e20bb70451b8ac691'
PREPARED_SHA='8ff423837024d1a1566c985b06be08effadb134a7f372278aa8cec17f9983d69'
NEIGHBORS=20
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_150B6BC0.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_E4070.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv','proposed-Makefile','pool-audit.json')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Menu command dispatch input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Menu command dispatch frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Menu command dispatch preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Menu command dispatch evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Menu command dispatch prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==0 and q['exclusions']==0):raise ValueError('Menu command dispatch preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Menu command dispatch literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Menu command dispatch named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/Makefile']=proposed_makefile(values['conker/Makefile'].decode()).encode()
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Menu command dispatch live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Menu command dispatch linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Menu command dispatch protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=24,alignment_words=0,guards=0,direct_C_match=True,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
