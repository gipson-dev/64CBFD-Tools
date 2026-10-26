"""Owner-subtype factory callback: complete direct C and strict qualified image."""
from pathlib import Path
import hashlib,json,shlex,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION,OWNER='func_150DDED0','generated_108E90'
ENTRY,ROM,BODY,SIZE=0x150DDED0,0x10B380,184,184
SOURCE='conker/src/game/generated_108E90.c'
OBJECT='conker/build/src/game/generated_108E90.c.o'
ASM='conker/asm/108E90.s'
BUILD='conker/build/game-owner-subtype-factory-match'
SNAPSHOT_SHA='14383fe74663d246e5c74fec3c58d1dc40940e62777a0b4a85a29cf1f3a9c848'
BEFORE_ELF_SHA='042fc7049cfdd62471d10bcc580b06ab0b55c41fb175e2e85514028c346628ba'
RAW_SHA='0c5c1a22bcaf6e10eff1062d3339f60197eb5da65c42736913f1e9c8c2e4cb73'
BINDINGS={48:[('R_MIPS_26','func_151491F4')],160:[('R_MIPS_26','func_1516972C')]}
DECLARATIONS='u8 *func_151491F4(s16, s8, s8, u8, u8, s32, u8, s32);\nvoid func_1516972C(u8 *record);\n'
SELECTED="/* Create a short-lived record, then select its byte mode from the owner's subtype. */\nvoid func_150DDED0(u8 *owner) {\n    u8 *record;\n\n    record = func_151491F4(100, 2, -1, 1, 0, 1, 255, 0);\n    if (record != NULL) {\n        switch (owner[0x72]) {\n            case 0xFB: record[0x28] = 1; break;\n            case 0xFC: record[0x28] = 2; break;\n            case 0xFD: record[0x28] = 4; break;\n            case 0xFE: record[0x28] = 3; break;\n            default: func_1516972C(record); break;\n        }\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Subtype factory raw body/bindings changed')
 return raw,bindings

def snapshot(output):
 raw=(output/'input-snapshot.json').read_bytes()
 if sha(raw)!=SNAPSHOT_SHA:raise ValueError('Subtype factory snapshot changed')
 values={}
 for n,h in json.loads(raw)['INPUTS'].items():
  b=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(b)!=h:raise ValueError('Subtype factory frozen input changed: '+n)
  values[n]=b
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Subtype factory predecessor changed')
 return values

def recovered_owner(before):
 old='s32 func_150DDED0() {\n    return 0;\n}'
 if before.count(old)!=1:raise ValueError('Subtype factory placeholder changed')
 return before.replace('#include <ultra64.h>','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(old,SELECTED,1)

def check_inputs(root,output,installed=False):
 values=snapshot(output)
 changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes()}if installed else{}
 if installed:changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for n,b in values.items():
  if(root/n).read_bytes()!=changes.get(n,b):raise ValueError('Subtype factory live input differs: '+n)
 return values

def original(root,output):
 from tools.tests.test_game_view_list_setup import ViewListSetupTests
 context=type('SubtypeOriginal',(),dict(root=root,out=output))
 return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)

def qualify(root,output):
 values=snapshot(output)
 for n,b in values.items():
  if(root/n).read_bytes()!=b:raise ValueError('Subtype factory preflight differs: '+n)
 before,after,selected=[output/n for n in('before-owner.o','after-owner.o','selected.o')]
 reused=json.loads((output/'reused-private-execution.json').read_text())
 if reused['focused_snapshot_SHA256']!=SNAPSHOT_SHA or reused['compiler_profile']!=['-O2','-g3','-mips2','-o32']:raise ValueError('Subtype factory reused raw profile changed')
 raw,bindings=checked_payload(*payload(selected));truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 if payload(after)!=(raw,bindings)or payload(original(root,output))!=(raw,bindings):raise ValueError('Subtype factory full owner/original differs')
 linked,functions=link_owner(root,output,selected,OWNER);at=functions[FUNCTION]['value']
 if linked[at:at+SIZE]!=truth:raise ValueError('Subtype factory linked isolated body differs')
 neighbors=same_functions(before,after,(FUNCTION,))
 if neighbors!=11 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Subtype factory raw neighbors/pools changed')
 if (output/'proposed-owner.c').read_bytes()!=recovered_owner(values[SOURCE].decode()).encode():raise ValueError('Subtype factory recovered owner changed')
 assembly=output/'qualified-padded.s';obj=assembly.with_suffix('.o')
 if obj.exists():raise ValueError('Inspect completed subtype factory padding execution')
 assembly.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER))
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(assembly)],check=True,capture_output=True)
 old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
 expected={n:dict(info)for n,info in fa.items()}
 if expected[FUNCTION]['size']!=12:raise ValueError('Subtype factory predecessor extent changed')
 expected[FUNCTION]['size']=SIZE;at=fb[FUNCTION]['value'];slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
 if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]:raise ValueError('Subtype factory predecessor slot changed')
 if b[at:at+SIZE]!=truth or expected!=fb or a[:at]!=b[:at]or a[at+SIZE:]!=b[at+SIZE:]:raise ValueError('Subtype factory padded body/address/extent differs')
 if same_functions(old,obj,(FUNCTION,))!=neighbors or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Subtype factory padded neighbors changed')
 report=dict(words=46,frame=40,differences=0,relocations=2,new_guards=0,alignment_words=0,raw_SHA256=sha(raw),preserved_neighbors=11,compiler_only=True,private_raw_executions_reused_via_identity=True,shared_headers_and_guard_CSV_unchanged=True,target_size_before=12,target_size_after=SIZE)
 (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def make_shadow(root,output):
 check_inputs(root,output);conker=root/'conker';shadow=output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
 target=(shadow/'src/game/generated_108E90.c.o').relative_to(conker).as_posix()
 plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
 (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
 for line in plan.stdout.replace(chr(92)+chr(10),'').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected subtype factory Make command: '+repr(args))
  args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a=='src/game/generated_108E90.c'else a for a in args]
  redirect=None
  if '>'in args:
   if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown subtype factory Make redirect')
   redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
  if p.returncode or p.stderr or(p.stdout and redirect is None):raise ValueError('Subtype factory Make command failed: '+p.stdout+p.stderr)
  if redirect is not None:redirect.write_text(p.stdout)
  commands.append(args)
 actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
 if len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3'))or any('-loopunroll'in f for f in compilers[0]):raise ValueError('Subtype factory Make profile changed')
 if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'))!=12 or normalized_pools(output/'after-owner.o')!=normalized_pools(Path(str(actual)+'.compact')):raise ValueError('Subtype factory Make raw owner differs')
 if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Subtype factory Make padded object bytes differ')
 report=dict(commands=len(commands),normal_O2_g3=True,compact_functions_equal=12,complete_padded_object_equal=True,inherited_Make_warnings=plan.stderr)
 (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE:raise ValueError('Subtype factory strict predecessor changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[offset for offset,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
 if len(rows)!=1:raise ValueError('Subtype factory original symbol extent changed')
 struct.pack_into('>I',result,rows[0]+8,SIZE)
 return bytes(result)

def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Subtype factory image differs from complete body/size prediction')

def audit(root,output):
 values=check_inputs(root,output,True);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 check_image(values['conker/build/conker.us.elf'],(root/'conker/build/conker.us.elf').read_bytes(),truth)
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Subtype factory changed another linked body/address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Subtype factory protected Game data changed')
 report=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report

ARTIFACTS=('before-owner.o','after-owner.o','selected.o','before-padded.o','qualified-padded.o','proposed-owner.c','original-func_150DDED0.o','first-linked.elf')
def freeze_prepared(output):
 if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect completed subtype factory artifact freeze')
 rows={n:sha((output/n).read_bytes())for n in ARTIFACTS}
 (output/'artifact-fingerprint.json').write_text(json.dumps(rows,indent=2)+'\n');return rows

def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Subtype factory artifact set changed')
 for n,h in rows.items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Subtype factory prepared artifact changed: '+n)
 q=json.loads((output/'qualification.json').read_text())
 if sha((output/'make-shadow-plan.txt').read_bytes())!=q['Make_plan_SHA256']:raise ValueError('Subtype factory Make execution plan changed')
 if (output/'make-shadow/src/game/generated_108E90.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Subtype factory actual Make output changed')
 for n,h in json.loads((output/'reused-private-execution.json').read_text())['private_files'].items():
  if sha((output/'reused-private'/n).read_bytes())!=h:raise ValueError('Subtype factory private raw history changed: '+n)
 return rows
