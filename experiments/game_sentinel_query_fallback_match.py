"""Sentinel query wrapper: complete semantic C and a closed opening schedule."""
from pathlib import Path
import csv,hashlib,io,json,struct,shlex,subprocess,re
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1503B708','generated_64120'
ENTRY,ROM,BODY,SIZE=0x1503B708,0x68BB8,180,184
SOURCE='conker/src/game/generated_64120.c'
OBJECT='conker/build/src/game/generated_64120.c.o'
ASM='conker/asm/64120.s'
BUILD='conker/build/game-sentinel-query-fallback-match'
RAW_SHA='310a95d9d824641bddb8a92a30f5a584f11dda7f1751039a931ac801de92906a'
SNAPSHOT_SHA='89db83782b041760600faf44194405686c6382b87aeec3d51be14c58bad4eb8a'
BEFORE_ELF_SHA='59d3bd429e7ccdbb3b4be813f439298240f4e5f2bda288c5d6bd931d7af8ca5a'
GUARD_SHA='b06636974e4c3ffd95e072a36c960c688d22845bbea0dcc164429ce252e568f8'
BINDINGS={8:[('R_MIPS_HI16','D_800C3FD0')],12:[('R_MIPS_LO16','D_800C3FD0')],36:[('R_MIPS_HI16','D_800986EC')],40:[('R_MIPS_LO16','D_800986EC')],44:[('R_MIPS_HI16','func_15037880')],48:[('R_MIPS_LO16','func_15037880')],124:[('R_MIPS_HI16','func_150380C0')],128:[('R_MIPS_LO16','func_150380C0')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
DECLARATIONS='extern f32 D_800986EC;\nextern f32 D_800C3FD0[];\n\n/* Typed call views retain the recovered ABI while provider bodies remain placeholders. */\ntypedef s32 (*SentinelPrimaryQuery)(s32, f32 *);\ntypedef s32 (*SentinelFallbackQuery)(f32 *, s32, s32, s32, f32, s32, f32 *, s32, s32, s32, s32);\n'
PRIMARY_SIGNATURE='s32 func_15037880(s32 playerIndex, f32 *output)'
FALLBACK_SIGNATURE='s32 func_150380C0(f32 *output, s32 arg1, s32 arg2, s32 playerIndex, f32 arg4, s32 arg5, f32 *distance, s32 arg7, s32 arg8, s32 arg9, s32 arg10)'
SELECTED='''/* Initialize both sentinels and use the fallback only if the primary query declines. */
void func_1503B708(f32 *output, s32 arg1, s32 arg2, s32 playerIndex, f32 arg4, s32 arg5, f32 *distance, s32 arg7, s32 arg8, s32 arg9, s32 arg10) {
    f32 sentinel = D_800986EC;

    output[0] = sentinel;
    output[1] = sentinel;
    output[2] = sentinel;
    D_800C3FD0[0] = sentinel;
    D_800C3FD0[1] = sentinel;
    D_800C3FD0[2] = sentinel;
    if (((SentinelPrimaryQuery) func_15037880)(playerIndex, output) == 0) {
        ((SentinelFallbackQuery) func_150380C0)(output, arg1, arg2, playerIndex, arg4, arg5, distance, arg7, arg8, arg9, arg10);
    }
}'''

def payload(obj):return function_payload(obj,FUNCTION)
def fields(w,rt):return(w&~(31<<16))|(rt<<16)
def normalized(raw,bindings):
 if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Sentinel query raw body/bindings changed')
 w=list(struct.unpack('>49I',raw));omitted={11,12,31,32};used=[i for i in range(49)if i not in omitted];inverse={old:new for new,old in enumerate(used)};compact=[w[i]for i in used]
 # Both call addresses are fixed, complete HI16/LO16 pairs consumed only by
 # JALR T9. Fold each static pair to its original direct JAL and retain one
 # R_MIPS_26 binding. This removes four address-construction instructions.
 if(w[11],w[12],w[20],w[31],w[32],w[42])!=(0x3C190000,0x27390000,0x0320F809,0x3C190000,0x27390000,0x0320F809):raise ValueError('Sentinel fixed-call lifetimes changed')
 compact[18]=compact[38]=3<<26
 rel={inverse[at//4]*4:list(rows)for at,rows in bindings.items()if at//4 not in omitted}
 rel[72]=[('R_MIPS_26','func_15037880')];rel[152]=[('R_MIPS_26','func_150380C0')]
 # Recompute the one branch spanning the removed fallback address pair.
 imm=w[22]&65535;target=23+(imm if imm<32768 else imm-65536);delta=inverse[target]-(inverse[22]+1)
 compact[20]=(compact[20]&0xFFFF0000)|(delta&65535)
 # Reuse T9 for fallback argument eight after removing its call-address lifetime.
 # Translate each of the three complete load/store lifetimes together.
 for load,store,reg in((26,36,25),(27,37,8),(28,39,9)):compact[load]=fields(compact[load],reg);compact[store]=fields(compact[store],reg)
 # Restore the common sentinel before argument homing, all six ordered stores,
 # the late player-home read and A1 setup in the first JAL delay slot.
 order=list(range(45));order[:20]=[0,1,2,9,10,3,4,5,6,7,8,11,12,13,16,17,19,14,18,15]
 fitted=[compact[i]for i in order];position={old:new for new,old in enumerate(order)};final_rel={position[at//4]*4:rows for at,rows in rel.items()}
 patches={used[i]:(fitted[i],final_rel.get(4*i,[]))for i in range(45)}
 return struct.pack('>45I',*fitted),final_rel,dict(omitted=omitted,patches=patches)

def checked_payload(raw,bindings):normalized(raw,bindings);return raw,bindings

def guard_bytes(before,raw,bindings):
 if sha(before)!=GUARD_SHA:raise ValueError('Sentinel query guard predecessor changed')
 fixed,rel,plan=normalized(raw,bindings);w=struct.unpack('>49I',raw);reader=csv.DictReader(io.StringIO(before.decode()));schema=reader.fieldnames
 if any(row['function']==FUNCTION for row in reader):raise ValueError('Sentinel query guards already exist')
 out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=schema,lineterminator='\r\n'if before.endswith(b'\r\n')else'\n');spec=lambda rs:';'.join(t+':'+n for t,n in rs)or'-'
 for i,old in enumerate(w):
  omit=i in plan['omitted'];new,after=(old,[])if omit else plan['patches'][i];prior=bindings.get(i*4,[])
  if old==new and prior==after and not omit:continue
  note='Derive fixed direct calls and closed argument lifetimes with the original sentinel/home/store schedule'
  if omit:note='Fold fixed function address construction into the original relocation-aware direct JAL'
  writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(4*i),expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations=spec(prior),replacement_relocations=spec(after),note=note,omit=str(omit).lower()))
 return before+out.getvalue().encode()

def recovered_owner(before):
 stub='s32 func_1503B708() {\n    return 0;\n}'
 if before.count(stub)!=1:raise ValueError('Sentinel query placeholder changed')
 result=before.replace('#include <ultra64.h>','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED,1)
 return result

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Sentinel query snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  b=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(b)!=h:raise ValueError('Sentinel query frozen input changed: '+n)
  values[n]=b
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Sentinel query predecessor changed')
 return values


def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':(output/'qualified-guards.csv').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for n,b in values.items():
  if(root/n).read_bytes()!=changes.get(n,b):raise ValueError('Sentinel query live input differs: '+n)
 return values

def original(root,output):
 from tools.tests.test_game_view_list_setup import ViewListSetupTests
 context=type('SentinelOriginal',(),dict(root=root,out=output))
 return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def normalized_diagnostics(value):
 result=re.sub(r'build/[^,\n]+, line [0-9]+','<owner>, line <line>',value)
 expected='cfe: Warning 712: <owner>, line <line>: illegal combination of pointer and integer\n     *(void **) (arg0 + 0x324) = allocate_memory(0x48, 1, 0, 0);\n ------------------------------^\n'
 if result!=expected:raise ValueError('Unexpected sentinel owner diagnostic: '+value)
 return result

def qualify(root,output):
 values=check_inputs(root,output)
 before,after=output/'before-owner.o',output/'after-view-owner.o'
 reuse=json.loads((output/'final-raw-execution.json').read_text())
 if reuse['snapshot_SHA256']!=SNAPSHOT_SHA or reuse['flags']!=['-O2','-g3']:raise ValueError('Sentinel raw reuse provenance changed')
 for n,h in reuse['files'].items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Sentinel immutable raw execution changed: '+n)
 if(output/'before-owner.c').read_bytes()!=values[SOURCE]or(output/'after-view-owner.c').read_text()!=recovered_owner(values[SOURCE].decode()):raise ValueError('Sentinel reused source changed')
 da=(output/'before-owner-diagnostics.txt').read_text();db=(output/'after-view-owner-diagnostics.txt').read_text()
 if normalized_diagnostics(da)!=normalized_diagnostics(db):raise ValueError('Sentinel query diagnostics changed')
 if payload(after)!=payload(output/'selected.o'):raise ValueError('Sentinel isolated/full-owner body differs')
 raw,bindings=checked_payload(*payload(after));fixed,rel,_=normalized(raw,bindings)
 orig=original(root,output)
 if payload(orig)!=(fixed,rel):raise ValueError('Sentinel query original bytes/bindings differ')
 if same_functions(before,after,(FUNCTION,))!=18 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Sentinel raw neighbors/pools changed')
 guards=guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings);(output/'qualified-guards.csv').write_bytes(guards)
 for label,obj,manifest in(('before-assembled',before,root/'conker/retail_word_patches.us.csv'),('qualified-padded',after,output/'qualified-guards.csv')):
  asm=output/(label+'.s');asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=manifest,filename=OWNER))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
 if(output/'before-assembled.o').read_bytes()!=values[OBJECT]:raise ValueError('Sentinel baseline actual padder differs')
 (output/'before-padded.o').write_bytes(values[OBJECT]);(output/'proposed-owner.c').write_text(recovered_owner(values[SOURCE].decode()))
 a,fa=link_owner(root,output,output/'before-padded.o',OWNER);b,fb=link_owner(root,output,output/'qualified-padded.o',OWNER);at=fb[FUNCTION]['value'];expected={n:dict(info)for n,info in fa.items()};expected[FUNCTION]['size']=BODY
 if fa[FUNCTION]['size']!=12 or fb!=expected or a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]or b[at:at+SIZE]!=values['conker/conker.us.bin'][ROM:ROM+SIZE]:raise ValueError('Sentinel padded body/address/extent changed')
 if same_functions(output/'before-padded.o',output/'qualified-padded.o',(FUNCTION,))!=18 or normalized_pools(output/'before-padded.o')!=normalized_pools(output/'qualified-padded.o'):raise ValueError('Sentinel padded neighbors changed')
 frozen={str(p.relative_to(output)):sha(p.read_bytes())for n in('before-owner','after-view-owner')for suffix in('.c','-processed.c','.o','-diagnostics.txt')for p in[output/(n+suffix)]};(output/'frozen-raw.json').write_text(json.dumps(frozen,indent=2)+'\n')
 report=dict(words=46,body_words=45,alignment_words=1,frame=64,guards=sum(1 for row in csv.DictReader(io.StringIO(guards.decode()))if row['function']==FUNCTION),inserted_words=0,omitted_words=4,raw_words=49,raw_bindings=8,relocations=6,preserved_neighbors=18,typed_call_views=True,provider_bodies_unchanged=True,compiler_only=False,void_output_interface=True,shared_headers_unchanged=True)
 (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def make_shadow(root,output):
 check_inputs(root,output);conker=root/'conker';shadow=output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
 target=(shadow/'src/game/generated_64120.c.o').relative_to(conker).as_posix()
 plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
 (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
 for line in plan.stdout.replace(chr(92)+chr(10),'').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected color scan Make command: '+repr(args))
  args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a=='src/game/generated_64120.c'else (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
  redirect=None
  if '>'in args:
   if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown color scan Make redirect')
   redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
  if p.returncode or(p.stdout and redirect is None):raise ValueError('Sentinel query Make command failed: '+p.stdout+p.stderr)
  if args[0]=='../ido/ido5.3_recomp/cc':
   if normalized_diagnostics(p.stderr)!=normalized_diagnostics((output/'after-view-owner-diagnostics.txt').read_text()):raise ValueError('Sentinel Make diagnostics changed')
   (output/'make-shadow-compiler.log').write_text(p.stderr)
  elif p.stderr:raise ValueError('Sentinel non-compiler diagnostics: '+p.stderr)
  if redirect is not None:redirect.write_text(p.stdout)
  commands.append(args)
 actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
 if len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3'))or any('-loopunroll'in f for f in compilers[0]):raise ValueError('Sentinel query Make profile changed')
 if same_functions(output/'after-view-owner.o',Path(str(actual)+'.compact'))!=19 or normalized_pools(output/'after-view-owner.o')!=normalized_pools(Path(str(actual)+'.compact')):raise ValueError('Sentinel query Make raw owner differs')
 if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Sentinel query Make padded object bytes differ')
 report=dict(commands=len(commands),normal_O2_g3=True,compact_functions_equal=19,complete_padded_object_equal=True,inherited_Make_warnings=plan.stderr)
 (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE:raise ValueError('Sentinel query strict predecessor changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[offset for offset,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
 if len(rows)!=1:raise ValueError('Sentinel query original symbol extent changed')
 struct.pack_into('>I',result,rows[0]+8,BODY)
 return bytes(result)

def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Sentinel query image differs from complete body/size prediction')

def audit(root,output):
 values=check_inputs(root,output,True);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 check_image(values['conker/build/conker.us.elf'],(root/'conker/build/conker.us.elf').read_bytes(),truth)
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Sentinel query changed another linked body/address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Sentinel query protected Game data changed')
 report=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report


ARTIFACTS=('selected.o','before-owner.o','after-view-owner.o','before-padded.o','qualified-padded.o','proposed-owner.c','qualified-guards.csv','original-func_1503B708.o','first-linked.elf')
def freeze_prepared(output):
 if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect completed color scan artifact freeze')
 rows={n:sha((output/n).read_bytes())for n in ARTIFACTS};(output/'artifact-fingerprint.json').write_text(json.dumps(rows,indent=2)+'\n');return rows

def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Sentinel query artifact set changed')
 for n,h in rows.items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Sentinel query prepared artifact changed: '+n)
 for n,h in json.loads((output/'frozen-raw.json').read_text()).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Sentinel query raw execution changed: '+n)
 q=json.loads((output/'qualification.json').read_text())
 if sha((output/'make-shadow-plan.txt').read_bytes())!=q['Make_plan_SHA256']:raise ValueError('Sentinel query Make plan changed')
 if(output/'make-shadow/src/game/generated_64120.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Sentinel query Make output changed')
 return rows
