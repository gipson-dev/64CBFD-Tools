"""Packed object commands: direct semantic C and literal owner/image qualification."""
from pathlib import Path
import hashlib,json,struct,shlex,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1509F284','generated_CBDB0'
ENTRY,ROM,BODY,SIZE=0x1509F284,0xCC734,184,184
SOURCE='conker/src/game/generated_CBDB0.c'
OBJECT='conker/build/src/game/generated_CBDB0.c.o'
ASM='conker/asm/CBDB0.s'
BUILD='conker/build/game-packed-object-command-match'
RAW_SHA='60ae6ecf1656a8383435c541960b00e313c872d4457ce81c8b6635f5b243a5ac'
SNAPSHOT_SHA='5c1649ad644f85c2e4cf7b03b16edb268a4a218be7922508468347ab2e038729'
BEFORE_ELF_SHA='121a867bbdd91f4266d6976aa7596d9337eb61e52bc2b913f50db3fb79f315ea'
BINDINGS={64:[('R_MIPS_26','func_1509F660')],92:[('R_MIPS_26','func_1509F660')],148:[('R_MIPS_26','func_1509F77C')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
DECLARATIONS='''void func_1509F660(s32, s32);
/* Full-width call slots are narrowed inside this provider. */
s32 func_1509F77C(u32, s32, s32, s32, s32);
'''
SELECTED='''/* Decode the packed identifiers for the three recognized record commands. */
s32 func_1509F284(s32 unused, s32 command, u32 *record) {
    switch (command) {
        case 1:
            func_1509F660(record[2] & 0xFFF, 0);
            return 1;
        case 0:
            func_1509F660(record[2] & 0xFFF, 1);
            return 1;
        case 2:
            func_1509F77C((record[0] & 0xFFFF0000U) >> 16, record[2] & 0xFFF, record[3], record[4], record[5]);
            return 1;
    }
    return 0;
}'''

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Packed command raw body/bindings changed')
 return raw,bindings

def recovered_owner(before):
 stub='s32 func_1509F284() {\n    return 0;\n}'
 if before.count(stub)!=1:raise ValueError('Packed command placeholder changed')
 result=before.replace(stub,DECLARATIONS+'\n'+SELECTED,1)
 lo,hi=function_span(result,'func_1509F77C');provider=result[lo:hi]
 signature='s32 func_1509F77C(u16 arg0, s32 arg1, s16 arg2, s32 arg3, s32 arg4)'
 if not provider.startswith(signature)or provider.count('        arg0,')!=1 or provider.count('        arg2,')!=1:raise ValueError('Packed command provider predecessor changed')
 provider=provider.replace(signature,'s32 func_1509F77C(u32 arg0, s32 arg1, s32 arg2, s32 arg3, s32 arg4)',1).replace('        arg0,','        (u16) arg0,',1).replace('        arg2,','        (s16) arg2,',1)
 result=result[:lo]+provider+result[hi:]
 marker='// Matches retail directly from the explicit coordinate temporaries.\n'
 if result.count(marker)!=1:raise ValueError('Packed command provider comment changed')
 return result.replace(marker,marker+'/* Preserve full incoming words; narrow identifiers at the downstream call. */\n',1)

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Packed command snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  b=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(b)!=h:raise ValueError('Packed command frozen input changed: '+n)
  values[n]=b
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Packed command predecessor changed')
 return values

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for n,b in values.items():
  if(root/n).read_bytes()!=changes.get(n,b):raise ValueError('Packed command live input differs: '+n)
 return values

def original(root,output):
 from tools.tests.test_game_view_list_setup import ViewListSetupTests
 context=type('PackedCommandOriginal',(),dict(root=root,out=output))
 return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)

def qualify(root,output):
 values=check_inputs(root,output);proposed=recovered_owner(values[SOURCE].decode())
 if(output/'frozen-raw.json').exists():raise ValueError('Inspect completed raw execution; do not overwrite it')
 before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
 after,db=compile_owner(root,output,proposed,'after-owner')
 selected,dc=compile_owner(root,output,'#include <ultra64.h>\n'+DECLARATIONS+'\n'+SELECTED,'selected')
 if da or db or dc:raise ValueError('Packed command unexpected diagnostics: '+da+db+dc)
 raw,bindings=checked_payload(*payload(selected))
 if payload(after)!=(raw,bindings)or payload(original(root,output))!=(raw,bindings):raise ValueError('Packed command independent source/assembly differ')
 if same_functions(before,after,(FUNCTION,))!=16 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Packed command raw neighbors/pools changed')
 (output/'qualified-guards.csv').write_bytes(values['conker/retail_word_patches.us.csv'])
 for label,obj in(('before-assembled',before),('qualified-padded',after)):
  asm=output/(label+'.s');asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
 if(output/'before-assembled.o').read_bytes()!=values[OBJECT]:raise ValueError('Packed command baseline padder differs')
 (output/'before-padded.o').write_bytes(values[OBJECT]);(output/'proposed-owner.c').write_text(proposed)
 a,fa=link_owner(root,output,output/'before-padded.o',OWNER);b,fb=link_owner(root,output,output/'qualified-padded.o',OWNER);at=fb[FUNCTION]['value'];expected={n:dict(row)for n,row in fa.items()};expected[FUNCTION]['size']=SIZE
 if fa[FUNCTION]['size']!=12 or fb!=expected or a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]or b[at:at+SIZE]!=values['conker/conker.us.bin'][ROM:ROM+SIZE]:raise ValueError('Packed command padded body/address/extent changed')
 if same_functions(output/'before-padded.o',output/'qualified-padded.o',(FUNCTION,))!=16 or normalized_pools(output/'before-padded.o')!=normalized_pools(output/'qualified-padded.o'):raise ValueError('Packed command padded neighbors changed')
 frozen={n+suffix:sha((output/(n+suffix)).read_bytes())for n in('before-owner','after-owner','selected')for suffix in('.c','-processed.c','.o','-diagnostics.txt')};(output/'frozen-raw.json').write_text(json.dumps(frozen,indent=2)+'\n')
 q=dict(words=46,body_words=46,alignment_words=0,frame=40,guards=0,raw_words=46,raw_bindings=3,relocations=3,preserved_neighbors=16,provider_internal_narrowing_explicit=True,provider_body_byte_identical=True,compiler_only=True,shared_headers_unchanged=True)
 (output/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');return q

def make_shadow(root,output):
 check_inputs(root,output);conker=root/'conker';shadow=output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
 target=(shadow/'src/game/generated_CBDB0.c.o').relative_to(conker).as_posix();plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True);(output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
 for line in plan.stdout.replace(chr(92)+chr(10),'').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected packed command Make command: '+repr(args))
  args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a=='src/game/generated_CBDB0.c'else a for a in args];redirect=None
  if '>'in args:
   if args.count('>')!=1 or args[-2]!='>':raise ValueError('Packed command Make redirect changed')
   redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
  if p.returncode or p.stderr or(redirect is None and p.stdout):raise ValueError('Packed command Make failed: '+p.stdout+p.stderr)
  if redirect is not None:redirect.write_text(p.stdout)
  commands.append(args)
 actual=conker/target
 if len(commands)!=3 or '-O2'not in commands[0]or '-g3'not in commands[0]or any('-loopunroll'in x for x in commands[0]):raise ValueError('Packed command compiler profile changed')
 if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'))!=17 or actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Packed command Make object differs')
 q=dict(commands=3,normal_O2_g3=True,compact_functions_equal=17,complete_padded_object_equal=True,inherited_Make_warnings=plan.stderr);(output/'make-shadow.json').write_text(json.dumps(q,indent=2)+'\n');return q

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE:raise ValueError('Packed command strict predecessor changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[offset for offset,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
 if len(rows)!=1:raise ValueError('Packed command original symbol extent changed')
 struct.pack_into('>I',result,rows[0]+8,BODY);return bytes(result)

def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Packed command image differs from literal body/size prediction')

def predict(root,output):
 values=check_inputs(root,output);script=values['conker/build/conker.ld'].decode();old='build/src/game/generated_CBDB0.c.o'
 if script.count(old)!=1:raise ValueError('Packed command link owner changed')
 link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()));elf=output/'first-linked.elf'
 subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],cwd=root/'conker',check=True,capture_output=True)
 before,actual=values['conker/build/conker.us.elf'],elf.read_bytes();truth=values['conker/conker.us.bin'][ROM:ROM+SIZE];check_image(before,actual,truth);at=elf_slot_offset(before,ENTRY,SIZE);changed=sum(a!=b for a,b in zip(before,actual));code=sum(a!=b for a,b in zip(before[at:at+SIZE],truth))
 data=audit_layout(elf,root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Packed command private data differs')
 q=json.loads((output/'qualification.json').read_text());q.update(changed_bytes=changed,code_bytes=code,metadata_bytes=changed-code,strict_prediction_equal=True,prediction_differences=0,exclusions=0,ELF_SHA256=sha(actual),padded_SHA256=sha((output/'qualified-padded.o').read_bytes()),Make_plan_SHA256=sha((output/'make-shadow-plan.txt').read_bytes()),Make=json.loads((output/'make-shadow.json').read_text()),game_data=data)
 (output/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');return q

def audit(root,output):
 values=check_inputs(root,output,True);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE];check_image(values['conker/build/conker.us.elf'],(root/'conker/build/conker.us.elf').read_bytes(),truth)
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Packed command changed another linked body/address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Packed command protected data changed')
 q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

ARTIFACTS=('selected.o','before-owner.o','after-owner.o','before-padded.o','qualified-padded.o','proposed-owner.c','qualified-guards.csv','original-func_1509F284.o','first-linked.elf')
def freeze_prepared(output):
 if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect completed packed command artifact freeze')
 rows={n:sha((output/n).read_bytes())for n in ARTIFACTS};(output/'artifact-fingerprint.json').write_text(json.dumps(rows,indent=2)+'\n');return rows

def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Packed command artifact set changed')
 for n,h in rows.items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Packed command prepared artifact changed: '+n)
 for n,h in json.loads((output/'frozen-raw.json').read_text()).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Packed command raw execution changed: '+n)
 q=json.loads((output/'qualification.json').read_text())
 if sha((output/'make-shadow-plan.txt').read_bytes())!=q['Make_plan_SHA256']or(output/'make-shadow/src/game/generated_CBDB0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Packed command actual Make evidence changed')
 return rows
