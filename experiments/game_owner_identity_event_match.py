"""Owner identity-event: semantic C, one checked comparison guard and literal owner/image qualification."""
from pathlib import Path
import csv,hashlib,io,json,re,struct,shlex,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_151D08F0','generated_1FA770'
ENTRY,ROM,BODY,SIZE=0x151D08F0,0x1FDDA0,184,184
SOURCE='conker/src/game/generated_1FA770.c'
OBJECT='conker/build/src/game/generated_1FA770.c.o'
ASM='conker/asm/1FA770.s'
BUILD='conker/build/game-owner-identity-event-match'
RAW_SHA='4bcf1eced66a0a3fea23f9f60bd95cd4d88ff99b88bd2544fe074885f3432c64'
SNAPSHOT_SHA='255adfea31e3db98afff876dfc7c878c39b6dca99768eee6c6b6817fe811e13f'
BEFORE_ELF_SHA='a091b59b96890ff5f280310170a13db9f13df2106734eeaad900aa8001f69e40'
BINDINGS={80:[('R_MIPS_26','func_1516972C')]}
CALLER_SOURCE='conker/src/game/done/game_1765E0.c'
CALLER_OBJECT='conker/build/src/game/done/game_1765E0.c.o'
PARENT,TABLE,TABLE_ROM=0x15149434,0x8008A8D8,0x22F398
GUARD_SHA='891b71a4ce720398088375d01c6857e2ef542a1d9e3cd6923b2e8a825be3371b'
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS='void func_1516972C(struct102 *);\n'
ISOLATED_DECLARATIONS=DECLARATIONS
SELECTED="/* Release the owner or retarget its embedded source/identity pair. */\nvoid func_151D08F0(struct260 *record, s32 eventAddress, u8 command) {\n    u8 *owner = (u8 *)record;\n    u8 *event = (u8 *)eventAddress;\n    u8 *state = owner + 0x28;\n    s32 value = command;\n    if (command == 0 || value == 0x18) {\n        value = *(s32 *)event;\n        if (value == *(s32 *)state || state[4] == event[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    } else if (value == 0x2D) {\n        s32 current = *(s32 *)state;\n        value = *(s32 *)event;\n        if (value == current) {\n            *(s32 *)state = *(s32 *)(event + 4);\n            state[4] = event[9];\n        } else if (*(s32 *)(event + 4) == current) {\n            *(s32 *)state = value;\n            state[4] = event[8];\n        }\n    }\n}"

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner identity-event raw body/bindings changed')
 return raw,bindings

GUARDS={148:(0x548A0005,0x55440005)}
def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);result=bytearray(raw)
 expected,replacement=GUARDS[148]
 if expected>>26!=21 or replacement>>26!=21 or expected&0xFC00FFFF!=replacement&0xFC00FFFF or (expected>>21&31,expected>>16&31)!=(replacement>>16&31,replacement>>21&31):raise ValueError('Owner identity-event comparison commutation changed')
 for at,(expected,replacement)in GUARDS.items():
  if struct.unpack_from('>I',result,at)[0]!=expected:raise ValueError('Owner identity-event comparison guard changed')
  struct.pack_into('>I',result,at,replacement)
 return bytes(result),bindings

def guarded_manifest(before,raw,bindings):
 normalized_payload(raw,bindings)
 if sha(before)!=GUARD_SHA:raise ValueError('Owner identity-event guard history changed')
 rows=list(csv.DictReader(io.StringIO(before.decode())))
 if any(row['function']==FUNCTION for row in rows):raise ValueError('Owner identity-event already has guards')
 if not before.endswith(bytes([10])):raise ValueError('Owner identity-event guard manifest terminator changed')
 stream=io.StringIO(newline='');fields=next(csv.reader(io.StringIO(before.decode())));writer=csv.DictWriter(stream,fields,lineterminator=chr(10))
 for at,(expected,replacement)in GUARDS.items():writer.writerow(dict(filename=OWNER,function=FUNCTION,offset=hex(at),expected=hex(expected),replacement=hex(replacement),expected_relocations='-',replacement_relocations='-',note='Normalize commutative embedded-identity branch operand order',insert_after='',insert_after_relocations='',omit='false'))
 return before+stream.getvalue().encode()

def recovered_owner(before):
 stub='s32 func_151D08F0() {\n    return 0;\n}'
 if before.count(stub)!=1:raise ValueError('Owner identity-event placeholder changed')
 opening='#include <ultra64.h>'
 if before.count(opening)!=1 or '#include "structs.h"'in before:raise ValueError('Owner identity-event includes changed')
 result=before.replace(opening,opening+'\n#include "structs.h"\n'+DECLARATIONS.rstrip(),1).replace(stub,SELECTED,1)
 old='func_1516972C(*(s32 volatile *)(temp_a1 + 0xA8));'
 if result.count(old)!=1:raise ValueError('Owner identity-event existing provider call changed')
 return result.replace(old,'func_1516972C((struct102 *)*(s32 volatile *)(temp_a1 + 0xA8));',1)

def diagnostics(text):
 return re.sub(r'(cfe: Warning [0-9]+: )[^,]+, line [0-9]+:',lambda m:m.group(1)+'SOURCE:',text)


def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner identity-event snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  b=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(b)!=h:raise ValueError('Owner identity-event frozen input changed: '+n)
  values[n]=b
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner identity-event predecessor changed')
 return values

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={'conker/retail_word_patches.us.csv':(output/'qualified-guards.csv').read_bytes(),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for n,b in values.items():
  if(root/n).read_bytes()!=changes.get(n,b):raise ValueError('Owner identity-event live input differs: '+n)
 return values

def original(root,output):
 from tools.tests.test_game_view_list_setup import ViewListSetupTests
 context=type('OwnerIdentityOriginal',(),dict(root=root,out=output))
 return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)

def qualify(root,output):
 values=check_inputs(root,output);proposed=recovered_owner(values[SOURCE].decode())
 if(output/'frozen-raw.json').exists():raise ValueError('Inspect completed raw execution; do not overwrite it')
 before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
 after,db=compile_owner(root,output,proposed,'after-owner')
 selected,dc=compile_owner(root,output,HEADERS+ISOLATED_DECLARATIONS+'\n'+SELECTED,'selected')
 if da.count('cfe: Warning 712:')!=8 or db.count('cfe: Warning 712:')!=8 or diagnostics(da)!=diagnostics(db) or dc:raise ValueError('Owner identity-event diagnostics changed: '+da+db+dc)
 raw,bindings=checked_payload(*payload(selected))
 if payload(after)!=(raw,bindings)or payload(original(root,output))!=normalized_payload(raw,bindings):raise ValueError('Owner identity-event independent source/assembly differ')
 if same_functions(before,after,(FUNCTION,))!=51 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Owner identity-event raw neighbors/pools changed')
 (output/'qualified-guards.csv').write_bytes(guarded_manifest(values['conker/retail_word_patches.us.csv'],raw,bindings))
 for label,obj in(('before-assembled',before),('qualified-padded',after)):
  asm=output/(label+'.s');asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=(root/'conker/retail_word_patches.us.csv'if label=='before-assembled'else output/'qualified-guards.csv'),filename=OWNER))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
 if(output/'before-assembled.o').read_bytes()!=values[OBJECT]:raise ValueError('Owner identity-event baseline padder differs')
 (output/'before-padded.o').write_bytes(values[OBJECT]);(output/'proposed-owner.c').write_text(proposed)
 a,fa=link_owner(root,output,output/'before-padded.o',OWNER);b,fb=link_owner(root,output,output/'qualified-padded.o',OWNER);at=fb[FUNCTION]['value'];expected={n:dict(row)for n,row in fa.items()};expected[FUNCTION]['size']=SIZE
 if fa[FUNCTION]['size']!=12 or fb!=expected or a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]or b[at:at+SIZE]!=values['conker/conker.us.bin'][ROM:ROM+SIZE]:raise ValueError('Owner identity-event padded body/address/extent changed')
 if same_functions(output/'before-padded.o',output/'qualified-padded.o',(FUNCTION,))!=51 or normalized_pools(output/'before-padded.o')!=normalized_pools(output/'qualified-padded.o'):raise ValueError('Owner identity-event padded neighbors changed')
 frozen={n+suffix:sha((output/(n+suffix)).read_bytes())for n in('before-owner','after-owner','selected')for suffix in('.c','-processed.c','.o','-diagnostics.txt')};(output/'frozen-raw.json').write_text(json.dumps(frozen,indent=2)+'\n')
 old=values['conker/build/conker.us.elf'];rom=values['conker/conker.us.bin']
 if old[elf_slot_offset(old,PARENT,92):][:92]!=rom[0x1768E4:0x176940] or old[elf_slot_offset(old,TABLE,296):][:296]!=rom[TABLE_ROM:TABLE_ROM+296]:raise ValueError('Owner identity-event retained caller/registry changed')
 if struct.unpack_from('>I',rom,TABLE_ROM+49*4)[0]!=ENTRY:raise ValueError('Owner identity-event registry slot changed')
 q=dict(words=46,body_words=46,alignment_words=0,frame=24,guards=1,raw_words=46,raw_bindings=1,relocations=1,preserved_neighbors=51,compiler_only=False,shared_headers_unchanged=True,canonical_ABI='void(struct260*,s32,u8)',provider_ABI='void(struct102*)',existing_generated_caller_cast_word_neutral=True,inherited_warning_712_count=8,target_diagnostics_empty=True,owner_diagnostics_unchanged=True)
 (output/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');return q

def make_shadow(root,output):
 check_inputs(root,output);conker=root/'conker';shadow=output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
 target=(shadow/'src/game/generated_1FA770.c.o').relative_to(conker).as_posix();plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True);(output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
 for line in plan.stdout.replace(chr(92)+chr(10),'').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected owner identity-event Make command: '+repr(args))
  args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a=='src/game/generated_1FA770.c'else (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args];redirect=None
  if '>'in args:
   if args.count('>')!=1 or args[-2]!='>':raise ValueError('Owner identity-event Make redirect changed')
   redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
  expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
  if p.returncode or diagnostics(p.stderr)!=diagnostics(expected) or(redirect is None and p.stdout):raise ValueError('Owner identity-event Make failed: '+p.stdout+p.stderr)
  if redirect is not None:redirect.write_text(p.stdout)
  commands.append(args)
 actual=conker/target
 if len(commands)!=3 or '-O2'not in commands[0]or '-g3'not in commands[0]or any('-loopunroll'in x for x in commands[0]):raise ValueError('Owner identity-event compiler profile changed')
 if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'))!=52 or actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner identity-event Make object differs')
 q=dict(commands=3,normal_O2_g3=True,compact_functions_equal=52,complete_padded_object_equal=True,inherited_Make_warnings=plan.stderr);(output/'make-shadow.json').write_text(json.dumps(q,indent=2)+'\n');return q

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!='2b6062abe47481f9908bcc10a3d15254878817a53aa4a79339e1cc0a87903e27':raise ValueError('Owner identity-event strict predecessor changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[offset for offset,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
 if len(rows)!=1:raise ValueError('Owner identity-event original symbol extent changed')
 struct.pack_into('>I',result,rows[0]+8,BODY);return bytes(result)

def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Owner identity-event image differs from literal body/size prediction')

def predict(root,output):
 values=check_inputs(root,output);script=values['conker/build/conker.ld'].decode();old='build/src/game/generated_1FA770.c.o'
 if script.count(old)!=1:raise ValueError('Owner identity-event link owner changed')
 link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()));elf=output/'first-linked.elf'
 subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],cwd=root/'conker',check=True,capture_output=True)
 before,actual=values['conker/build/conker.us.elf'],elf.read_bytes();truth=values['conker/conker.us.bin'][ROM:ROM+SIZE];check_image(before,actual,truth);at=elf_slot_offset(before,ENTRY,SIZE);changed=sum(a!=b for a,b in zip(before,actual));code=sum(a!=b for a,b in zip(before[at:at+SIZE],truth))
 data=audit_layout(elf,root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner identity-event private data differs')
 q=json.loads((output/'qualification.json').read_text());q.update(changed_bytes=changed,code_bytes=code,metadata_bytes=changed-code,strict_prediction_equal=True,prediction_differences=0,exclusions=0,ELF_SHA256=sha(actual),padded_SHA256=sha((output/'qualified-padded.o').read_bytes()),Make_plan_SHA256=sha((output/'make-shadow-plan.txt').read_bytes()),Make=json.loads((output/'make-shadow.json').read_text()),game_data=data)
 (output/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');return q

def audit(root,output):
 values=check_inputs(root,output,True);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE];check_image(values['conker/build/conker.us.elf'],(root/'conker/build/conker.us.elf').read_bytes(),truth)
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner identity-event changed another linked body/address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner identity-event protected data changed')
 q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

ARTIFACTS=('selected.o','before-owner.o','after-owner.o','before-padded.o','qualified-padded.o','proposed-owner.c','qualified-guards.csv','original-func_151D08F0.o','first-linked.elf')
def freeze_prepared(output):
 if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect completed owner identity-event artifact freeze')
 rows={n:sha((output/n).read_bytes())for n in ARTIFACTS};(output/'artifact-fingerprint.json').write_text(json.dumps(rows,indent=2)+'\n');return rows

def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Owner identity-event artifact set changed')
 for n,h in rows.items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Owner identity-event prepared artifact changed: '+n)
 for n,h in json.loads((output/'frozen-raw.json').read_text()).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Owner identity-event raw execution changed: '+n)
 q=json.loads((output/'qualification.json').read_text())
 if sha((output/'make-shadow-plan.txt').read_bytes())!=q['Make_plan_SHA256']or(output/'make-shadow/src/game/generated_1FA770.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner identity-event actual Make evidence changed')
 return rows
