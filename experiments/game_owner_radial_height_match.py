"""Owner radial-height: semantic C, two checked spill guards and literal owner/image qualification."""
from pathlib import Path
import csv,hashlib,io,json,struct,shlex,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_151A8F6C','generated_1D4E00'
ENTRY,ROM,BODY,SIZE=0x151A8F6C,0x1D641C,184,184
SOURCE='conker/src/game/generated_1D4E00.c'
OBJECT='conker/build/src/game/generated_1D4E00.c.o'
ASM='conker/asm/1D4E00.s'
BUILD='conker/build/game-owner-radial-height-match'
RAW_SHA='351a23424f0d56cb3b356ab9b938cc68bf507b6fe7969e53552fa819ca4beebc'
SNAPSHOT_SHA='ab008dbf9214aa4e52821bafd4f71f16a99c2567985d3100348c7ffe5b7dadab'
BEFORE_ELF_SHA='93b75e6065f9e162c33df5549b84b80b4c431f51ada713570d1eec77b2d9cabf'
BINDINGS={28:[('R_MIPS_26','func_150ADA20')],36:[('R_MIPS_26','func_150ADA68')],92:[('R_MIPS_26','func_15143874')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
DECLARATIONS="s32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_15143874(s16, f32, f32 *, f32 *);\n"
ISOLATED_DECLARATIONS=DECLARATIONS
SELECTED="/* Build a random horizontal offset and return the owner height values. */\nvoid func_151A8F6C(u8 *owner, f32 *vector, f32 *out0, f32 *out1) {\n    f32 *state = (f32 *)(owner + 0x28);\n    s32 code = func_150ADA20();\n    func_15143874((s16)(code & 0xFF), state[8] * func_150ADA68(), vector, vector + 2);\n    vector[0] += state[4];\n    vector[2] += state[6];\n    vector[1] = state[5];\n    *out0 = state[5];\n    *out1 = state[7];\n}"

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner radial-height raw body/bindings changed')
 return raw,bindings

GUARDS={40:(0xAFA20028,0xAFA20024),48:(0x8FA40028,0x8FA40024)}
def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);result=bytearray(raw)
 for at,(expected,replacement)in GUARDS.items():
  if struct.unpack_from('>I',result,at)[0]!=expected:raise ValueError('Owner radial-height stack guard changed')
  struct.pack_into('>I',result,at,replacement)
 return bytes(result),bindings

def guarded_manifest(before,raw,bindings):
 normalized_payload(raw,bindings);rows=list(csv.DictReader(io.StringIO(before.decode())))
 if any(row['function']==FUNCTION for row in rows):raise ValueError('Owner radial-height already has guards')
 if not before.endswith(bytes([10])):raise ValueError('Owner radial-height guard manifest terminator changed')
 stream=io.StringIO(newline='');fields=next(csv.reader(io.StringIO(before.decode())));writer=csv.DictWriter(stream,fields,lineterminator=chr(10))
 for at,(expected,replacement)in GUARDS.items():writer.writerow(dict(filename=OWNER,function=FUNCTION,offset=hex(at),expected=hex(expected),replacement=hex(replacement),expected_relocations='-',replacement_relocations='-',note='Normalize closed random-point integer temporary stack slot',insert_after='',insert_after_relocations='',omit='false'))
 return before+stream.getvalue().encode()

def recovered_owner(before):
 stub='s32 func_151A8F6C() {\n    return 0;\n}'
 if before.count(stub)!=1:raise ValueError('Owner radial-height placeholder changed')
 return before.replace(stub,DECLARATIONS+'\n'+SELECTED,1)


def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner radial-height snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  b=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(b)!=h:raise ValueError('Owner radial-height frozen input changed: '+n)
  values[n]=b
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner radial-height predecessor changed')
 return values

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={'conker/retail_word_patches.us.csv':(output/'qualified-guards.csv').read_bytes(),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for n,b in values.items():
  if(root/n).read_bytes()!=changes.get(n,b):raise ValueError('Owner radial-height live input differs: '+n)
 return values

def original(root,output):
 from tools.tests.test_game_view_list_setup import ViewListSetupTests
 context=type('ActorStateOriginal',(),dict(root=root,out=output))
 return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)

def qualify(root,output):
 values=check_inputs(root,output);proposed=recovered_owner(values[SOURCE].decode())
 if(output/'frozen-raw.json').exists():raise ValueError('Inspect completed raw execution; do not overwrite it')
 before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
 after,db=compile_owner(root,output,proposed,'after-owner')
 selected,dc=compile_owner(root,output,'#include <ultra64.h>\n'+ISOLATED_DECLARATIONS+'\n'+SELECTED,'selected')
 if da or db or dc:raise ValueError('Owner radial-height unexpected diagnostics: '+da+db+dc)
 raw,bindings=checked_payload(*payload(selected))
 if payload(after)!=(raw,bindings)or payload(original(root,output))!=normalized_payload(raw,bindings):raise ValueError('Owner radial-height independent source/assembly differ')
 if same_functions(before,after,(FUNCTION,))!=22 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Owner radial-height raw neighbors/pools changed')
 (output/'qualified-guards.csv').write_bytes(guarded_manifest(values['conker/retail_word_patches.us.csv'],raw,bindings))
 for label,obj in(('before-assembled',before),('qualified-padded',after)):
  asm=output/(label+'.s');asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=(root/'conker/retail_word_patches.us.csv'if label=='before-assembled'else output/'qualified-guards.csv'),filename=OWNER))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
 if(output/'before-assembled.o').read_bytes()!=values[OBJECT]:raise ValueError('Owner radial-height baseline padder differs')
 (output/'before-padded.o').write_bytes(values[OBJECT]);(output/'proposed-owner.c').write_text(proposed)
 a,fa=link_owner(root,output,output/'before-padded.o',OWNER);b,fb=link_owner(root,output,output/'qualified-padded.o',OWNER);at=fb[FUNCTION]['value'];expected={n:dict(row)for n,row in fa.items()};expected[FUNCTION]['size']=SIZE
 if fa[FUNCTION]['size']!=12 or fb!=expected or a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]or b[at:at+SIZE]!=values['conker/conker.us.bin'][ROM:ROM+SIZE]:raise ValueError('Owner radial-height padded body/address/extent changed')
 if same_functions(output/'before-padded.o',output/'qualified-padded.o',(FUNCTION,))!=22 or normalized_pools(output/'before-padded.o')!=normalized_pools(output/'qualified-padded.o'):raise ValueError('Owner radial-height padded neighbors changed')
 frozen={n+suffix:sha((output/(n+suffix)).read_bytes())for n in('before-owner','after-owner','selected')for suffix in('.c','-processed.c','.o','-diagnostics.txt')};(output/'frozen-raw.json').write_text(json.dumps(frozen,indent=2)+'\n')
 q=dict(words=46,body_words=46,alignment_words=0,frame=48,guards=2,raw_words=46,raw_bindings=3,relocations=3,preserved_neighbors=22,PRNG_assembly_unchanged=True,void_output_interface=True,compiler_only=False,shared_headers_unchanged=True)
 (output/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');return q

def make_shadow(root,output):
 check_inputs(root,output);conker=root/'conker';shadow=output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
 target=(shadow/'src/game/generated_1D4E00.c.o').relative_to(conker).as_posix();plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True);(output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
 for line in plan.stdout.replace(chr(92)+chr(10),'').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected owner radial-height Make command: '+repr(args))
  args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a=='src/game/generated_1D4E00.c'else (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args];redirect=None
  if '>'in args:
   if args.count('>')!=1 or args[-2]!='>':raise ValueError('Owner radial-height Make redirect changed')
   redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
  if p.returncode or p.stderr or(redirect is None and p.stdout):raise ValueError('Owner radial-height Make failed: '+p.stdout+p.stderr)
  if redirect is not None:redirect.write_text(p.stdout)
  commands.append(args)
 actual=conker/target
 if len(commands)!=3 or '-O2'not in commands[0]or '-g3'not in commands[0]or any('-loopunroll'in x for x in commands[0]):raise ValueError('Owner radial-height compiler profile changed')
 if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'))!=23 or actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner radial-height Make object differs')
 q=dict(commands=3,normal_O2_g3=True,compact_functions_equal=23,complete_padded_object_equal=True,inherited_Make_warnings=plan.stderr);(output/'make-shadow.json').write_text(json.dumps(q,indent=2)+'\n');return q

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!='9602dd4d3cd3d8f7f3af3b00626a12dab9617d83b1539dfe470e6eb257366871':raise ValueError('Owner radial-height strict predecessor changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[offset for offset,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
 if len(rows)!=1:raise ValueError('Owner radial-height original symbol extent changed')
 struct.pack_into('>I',result,rows[0]+8,BODY);return bytes(result)

def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Owner radial-height image differs from literal body/size prediction')

def predict(root,output):
 values=check_inputs(root,output);script=values['conker/build/conker.ld'].decode();old='build/src/game/generated_1D4E00.c.o'
 if script.count(old)!=1:raise ValueError('Owner radial-height link owner changed')
 link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()));elf=output/'first-linked.elf'
 subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],cwd=root/'conker',check=True,capture_output=True)
 before,actual=values['conker/build/conker.us.elf'],elf.read_bytes();truth=values['conker/conker.us.bin'][ROM:ROM+SIZE];check_image(before,actual,truth);at=elf_slot_offset(before,ENTRY,SIZE);changed=sum(a!=b for a,b in zip(before,actual));code=sum(a!=b for a,b in zip(before[at:at+SIZE],truth))
 data=audit_layout(elf,root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner radial-height private data differs')
 q=json.loads((output/'qualification.json').read_text());q.update(changed_bytes=changed,code_bytes=code,metadata_bytes=changed-code,strict_prediction_equal=True,prediction_differences=0,exclusions=0,ELF_SHA256=sha(actual),padded_SHA256=sha((output/'qualified-padded.o').read_bytes()),Make_plan_SHA256=sha((output/'make-shadow-plan.txt').read_bytes()),Make=json.loads((output/'make-shadow.json').read_text()),game_data=data)
 (output/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');return q

def audit(root,output):
 values=check_inputs(root,output,True);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE];check_image(values['conker/build/conker.us.elf'],(root/'conker/build/conker.us.elf').read_bytes(),truth)
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner radial-height changed another linked body/address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner radial-height protected data changed')
 q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

ARTIFACTS=('selected.o','before-owner.o','after-owner.o','before-padded.o','qualified-padded.o','proposed-owner.c','qualified-guards.csv','original-func_151A8F6C.o','first-linked.elf')
def freeze_prepared(output):
 if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect completed owner radial-height artifact freeze')
 rows={n:sha((output/n).read_bytes())for n in ARTIFACTS};(output/'artifact-fingerprint.json').write_text(json.dumps(rows,indent=2)+'\n');return rows

def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Owner radial-height artifact set changed')
 for n,h in rows.items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Owner radial-height prepared artifact changed: '+n)
 for n,h in json.loads((output/'frozen-raw.json').read_text()).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Owner radial-height raw execution changed: '+n)
 q=json.loads((output/'qualification.json').read_text())
 if sha((output/'make-shadow-plan.txt').read_bytes())!=q['Make_plan_SHA256']or(output/'make-shadow/src/game/generated_1D4E00.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner radial-height actual Make evidence changed')
 return rows
