"""Actor random effect: direct C, original callback ABI and closed ELF image proof."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct,subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1506FD30','game_981E0'
ENTRY,ROM,BODY,SIZE=0x1506FD30,0x9D1E0,192,192
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
ASM='conker/asm/nonmatchings/game_981E0/func_1506FD30.s'
BUILD='conker/build/game-actor-random-effect-match'
RAW_SHA='3ebf61c79d401f6769991bb63497cc2dbff682b24f177e01afa12c61ac99f594'
SNAPSHOT_SHA='ed3d5626b6f833b768211dba44610d8e58c18b4973561f18079b009a74e123fa'
BEFORE_ELF_SHA='9515b096c6de81fdf23abe68a1dd470de2b1280d1d009116fa7540997ad83477'
TRUTH_SHA='83493fca2ce6d26cf36f2e09ab8055481d93fc98457dbf8f91773802e749d501'
ACTOR,PARAMETER,RNG,EMITTER,FACTORY,TABLE,SELECTOR=0x800D154C,0x80099EA0,0x150ADA68,0x150E2EA4,0x150E1AB0,0x80086150,0x800D1580
BINDINGS={12:[('R_MIPS_26','func_150ADA68')],20:[('R_MIPS_HI16','D_80099EA0')],24:[('R_MIPS_LO16','D_80099EA0')],40:[('R_MIPS_HI16','D_800D154C')],44:[('R_MIPS_LO16','D_800D154C')],168:[('R_MIPS_26','func_150E2EA4')]}
HEADERS="#include <ultra64.h>\n#include \"functions.h\"\n#include \"variables.h\"\n"
DECLARATIONS='extern f32 D_80099EA0;\n\n'
SELECTED="/* Submit the current actor effect with its randomized scalar. */\nvoid func_1506FD30(s32 arg0) {\n    f32 random = func_150ADA68();\n    f32 zero = 0.0;\n\n    func_150E2EA4(D_800D154C, D_800D154C->unique_id, 1, -1,\n        0.0f, zero, D_80099EA0, 0.0f, zero, 414.0f,\n        3, 3, 5, 20.0f, random * 10.0f + 40.0f, 1, 50.0f);\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()
def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor random effect body or bindings changed')
 return raw,bindings
def recovered_owner(before):
 stub='s32 func_1506FD30() {\n    return 0;\n}'
 if before.count(stub)!=1 or before.count('s32 func_1506FD30();')!=1:raise ValueError('Actor random effect placeholder changed')
 return before.replace(stub,SELECTED,1).replace('s32 func_1506FD30();','void func_1506FD30(s32 arg0);',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_981E0/func_1506FD30.s. */','extern f32 D_80099EA0;',1)
def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor random effect snapshot changed')
 values={}
 for n,wanted in json.loads(data)['INPUTS'].items():
  b=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(b)!=wanted:raise ValueError('Actor random effect frozen input changed: '+n)
  values[n]=b
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor random effect predecessor changed')
 return values
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for n,b in values.items():
  if(root/n).read_bytes()!=changes.get(n,b):raise ValueError('Actor random effect live input differs: '+n)
 return values
def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor random effect strict predecessor changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[p for p,n,f,_ in symbol_rows(before)if n==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
 if len(rows)!=1:raise ValueError('Actor random effect original extent changed')
 struct.pack_into('>I',result,rows[0]+8,BODY)
 names=('D_80099EA0','func_150D0E90','D_800AB1B4');order=('func_150D0E90','D_800AB1B4','D_80099EA0');records={n:(p,tuple(f))for p,n,f,_ in symbol_rows(before)if n in names}
 if set(records)!=set(names):raise ValueError('Actor random effect metadata names changed')
 positions=[records[n][0]for n in names]
 if positions!=list(range(positions[0],positions[0]+48,16)):raise ValueError('Actor random effect metadata record geometry changed')
 section_offset=struct.unpack_from('>I',before,32)[0];step,count=struct.unpack_from('>HH',before,46);sections=[struct.unpack_from('>10I',before,section_offset+i*step)for i in range(count)];symtab=next(s for s in sections if s[1]==2);strings=sections[symtab[6]];start=records[names[0]][1][0];cursor=start
 for n in names:
  if records[n][1][0]!=cursor:raise ValueError('Actor random effect string geometry changed')
  cursor+=len(n)+1
 old_strings=b''.join(n.encode()+b'\0'for n in names);new_strings=b''.join(n.encode()+b'\0'for n in order)
 if len(old_strings)!=36 or len(new_strings)!=36 or before[strings[4]+start:strings[4]+start+36]!=old_strings:raise ValueError('Actor random effect original strings changed')
 result[strings[4]+start:strings[4]+start+36]=new_strings;cursor=start
 for pos,n in zip(positions,order):
  f=records[n][1];struct.pack_into('>IIIBBH',result,pos,cursor,*f[1:]);cursor+=len(n)+1
 return bytes(result)
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Actor random effect image differs from body, size and three-name prediction')
 expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
 if expected!=observed:raise ValueError('Actor random effect named ELF definitions changed')
def normalized_diagnostics(text):return re.sub(r'cfe: Warning ([0-9]+): [^,\n]+, line [0-9]+:',r'cfe: Warning \1: <source>, line <n>:',text)
ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1506FD30.o','first-linked.elf')
EVIDENCE=('before-owner.c','before-owner-processed.c','before-owner.o','before-owner-diagnostics.txt','after-owner.c','after-owner-processed.c','after-owner.o','after-owner-diagnostics.txt','selected.c','selected-processed.c','selected.o','selected-diagnostics.txt','selected-input.c','actual-Make-plan.txt','Make-commands.json','actual-Make-diagnostics.txt','make-shadow/src/game_981E0.c.o','make-shadow/src/game_981E0.c.o.compact','make-shadow/src/game_981E0.c.o.padded.s','preparation.json')
def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Actor random effect artifact set changed')
 for n,h in rows.items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Actor random effect artifact changed: '+n)
 for n,h in json.loads((output/'frozen-raw.json').read_text()).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Actor random effect raw evidence changed: '+n)
 extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
 if set(extra)!=set(EVIDENCE):raise ValueError('Actor random effect evidence set changed')
 for n,h in extra.items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Actor random effect Make/evidence changed: '+n)
 if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected actor random effect diagnostics')
 diagnostics=[normalized_diagnostics((output/n).read_text())for n in('before-owner-diagnostics.txt','after-owner-diagnostics.txt','actual-Make-diagnostics.txt')]
 if len(set(diagnostics))!=1:raise ValueError('Actor random effect inherited diagnostic provenance changed')
 if(output/'make-shadow/src/game_981E0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor random effect actual Make object differs')
 q=json.loads((output/'preparation.json').read_text())
 if not q['complete']or(q['guards'],q['exclusions'],q['matching_credit'],q['changed_bytes'],q['code_bytes'],q['metadata_bytes'])!=(0,0,0,199,152,47):raise ValueError('Actor random effect private preparation changed')
 return dict(rows,**extra)
def audit(root,output):
 values=check_inputs(root,output,True);before=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(before,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor random effect changed another linked body or address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor random effect protected data changed')
 q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=80,bindings=6,guards=0,strict_first_link_reproduced=True,closed_three_name_serialization_changes=46,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
