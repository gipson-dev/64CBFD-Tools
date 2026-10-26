"""Closed register and schedule fit for the retail-profile environment color scan."""
from pathlib import Path
import csv,hashlib,io,json,struct
FUNCTION,OWNER='func_15012ED8','generated_3FC60'
RAW_SHA='b8aa821e21f3b64eea16d2ea78a1f88e939d649686f932447b42a9ab6214ee4f'
BINDINGS={32:[('R_MIPS_HI16','D_800BE530')],36:[('R_MIPS_HI16','D_800BE550')],40:[('R_MIPS_HI16','D_800BE564')],44:[('R_MIPS_LO16','D_800BE564')],48:[('R_MIPS_LO16','D_800BE550')],52:[('R_MIPS_LO16','D_800BE530')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
def fields(w,rs=None,rt=None,rd=None):
 if rs is not None:w=(w&~(31<<21))|(rs<<21)
 if rt is not None:w=(w&~(31<<16))|(rt<<16)
 if rd is not None:w=(w&~(31<<11))|(rd<<11)
 return w
def normalized(raw,bindings):
 if len(raw)!=184 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Color scan raw body/bindings changed')
 w=list(struct.unpack('>46I',raw))
 if w[44:]!=[0x03E00008,0x00601025]or w[14]!=0x240C0003 or w[29]!=0x244E0001:raise ValueError('Color scan count producers changed')
 # Allocate the complete count lifetime to ABI V0 and the opcode/slot to V1.
 # The constant and address roles are closed translations over all uses.
 roles={2:3,3:2,7:6,8:7,10:8,11:10,12:11};f=[]
 for q in w:
  rs,rt,rd=(q>>21)&31,(q>>16)&31,(q>>11)&31
  f.append(fields(q,roles.get(rs,rs),roles.get(rt,rt),roles.get(rd,rd)if q>>26==0 else None))
 # Independent stop-constant, cursor and multiply-constant definitions move
 # around the opening read/branch. The exit remains word44, so its displacement
 # decreases by one when the branch moves from word6 to word7.
 g=f.copy();f[:9]=[g[1],g[0],g[2],g[7],g[3],g[4],g[5],(g[6]&0xFFFF0000)|0x24,g[14]]
 # Relocate complete independent HI/LO definitions, not their data accesses.
 for target,old in((9,8),(10,10),(11,9),(12,12),(13,11),(14,13)):f[target]=g[old]
 rel={target*4:list(bindings[old*4])for target,old in((9,8),(10,10),(11,9),(12,12),(13,11),(14,13))}
 # Translate each temporary over its entire live range.
 f[21]=fields(f[21],rd=12);f[22]=fields(f[22],rs=12)
 f[23]=fields(f[23],rt=14);f[24]=fields(f[24],rt=14)
 f[25]=fields(f[25],rd=13);f[26]=fields(f[26],rt=13)
 # Move capturedSlot+1 across only the green shift/store and final payload read.
 # Keep the three payload reads, all stores, and lookahead in their original order.
 plus=fields(f[29],rt=25)
 f[29],f[30],f[31],f[32]=f[30],f[31],fields(f[32],rt=14),plus
 f[33]=fields(f[33],rt=25);f[34]=fields(f[34],rt=14,rd=24);f[35]=fields(f[35],rt=24)
 f[39]=fields(f[39],rd=12);f[40]=fields(f[40],rt=12,rd=13);f[41]=fields(f[41],rt=13)
 # V0 already holds the count. Replace the now-dead return copy in JR's delay
 # slot by NOP; preserve the full 46-word extent and both branch targets.
 f[45]=0
 return struct.pack('>46I',*f),rel,f

def guard_bytes(before,raw,bindings):
 if sha(before)!=GUARD_SHA:raise ValueError('Color scan guard predecessor changed')
 fixed,rel,f=normalized(raw,bindings);a=struct.unpack('>46I',raw)
 reader=csv.DictReader(io.StringIO(before.decode()));schema=reader.fieldnames
 if any(row['function']==FUNCTION for row in reader):raise ValueError('Color scan guards already exist')
 out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=schema,lineterminator='\r\n'if before.endswith(b'\r\n')else'\n')
 spec=lambda rs:';'.join(t+':'+n for t,n in rs)or'-'
 for i,(old,new)in enumerate(zip(a,f)):
  omit=False;prior=bindings.get(i*4,[]);after=rel.get(i*4,[])
  if old==new and prior==after and not omit:continue
  note='Derive closed color-scan register lifetimes and independent address/arithmetic scheduling'
  if i==45:note='Replace redundant count return copy by NOP after allocating the complete count lifetime to V0'
  writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(4*i),expected='0x%08X'%old,replacement='0x%08X'%(old if omit else new),expected_relocations=spec(prior),replacement_relocations=spec(after),note=note,omit=str(omit).lower()))
 return before+out.getvalue().encode()

from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
import shlex,subprocess
ENTRY,ROM,BODY,SIZE=0x15012ED8,0x40388,184,184
SOURCE='conker/src/game/generated_3FC60.c'
OBJECT='conker/build/src/game/generated_3FC60.c.o'
ASM='conker/asm/3FC60.s'
BUILD='conker/build/game-environment-color-scan-match'
SNAPSHOT_SHA='ee824bca194c02a014a266ddc7ebb6459d27987cdd7779a23be2d1087ce2220a'
BEFORE_ELF_SHA='becd3288b07199a88e81f31b68b5a8f1f5c94b60f68e2abee4386b2d008aa93d'
GUARD_SHA='33390a4db6e1bd4accdcf8fd11a4c6d7f29cd0780342cf84166bd9fd41f517b7'
DECLARATIONS="typedef struct { u8 red, green, blue; } EnvironmentColorBytes;\nextern EnvironmentColorBytes D_800BE530[];\nextern s16 D_800BE550[];\nextern u8 D_800BE564;\n"
SELECTED="/* Collect environment RGB values and command indices up to the end-list opcode. */\ns32 func_15012ED8(u32 *displayList) {\n    s32 index = 0;\n    s32 opcode = (s8)(displayList[0] >> 24);\n    u32 *cursor = displayList;\n    s32 slot;\n    u32 payload;\n\n    while (opcode != -33) {\n        if (opcode == -5) {\n            slot = D_800BE564;\n            D_800BE550[slot] = index;\n            D_800BE530[slot].red = cursor[1] >> 24;\n            D_800BE530[slot].green = cursor[1] >> 16;\n            payload = cursor[1];\n            D_800BE564 = slot + 1;\n            D_800BE530[slot].blue = payload >> 8;\n        }\n        index++;\n        cursor += 2;\n        opcode = (s8)(cursor[0] >> 24);\n    }\n    return index;\n}"

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):normalized(raw,bindings);return raw,bindings

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Color scan snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  b=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(b)!=h:raise ValueError('Color scan frozen input changed: '+n)
  values[n]=b
 if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Color scan predecessor changed')
 return values

def recovered_owner(before):
 stub='s32 func_15012ED8() {\n    return 0;\n}'
 if before.count(stub)!=1:raise ValueError('Color scan placeholder changed')
 return before.replace('#include <ultra64.h>','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED,1)

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':(output/'qualified-guards.csv').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
 for n,b in values.items():
  if(root/n).read_bytes()!=changes.get(n,b):raise ValueError('Color scan live input differs: '+n)
 return values

def original(root,output):
 from tools.tests.test_game_view_list_setup import ViewListSetupTests
 context=type('ColorOriginal',(),dict(root=root,out=output))
 return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)

def qualify(root,output):
 values=check_inputs(root,output)
 before,after=output/'before-retail.o',output/'after-retail.o'
 profile=json.loads((output/'retail-profile.json').read_text())
 if profile['before-retail']['padded_equal_baseline'] is not True or any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-retail','after-retail')):raise ValueError('Color scan retail compilation failed')
 raw,bindings=checked_payload(*payload(after))
 if (output/'before-retail.c').read_bytes()!=values[SOURCE] or (output/'after-retail.c').read_text()!=recovered_owner(values[SOURCE].decode()):raise ValueError('Color scan retail raw source changed')
 original_path=output/'original-func_15012ED8.o'
 if not original_path.exists():original_path=original(root,output)
 fixed,rs,_=normalized(raw,bindings)
 if payload(original_path)!=(fixed,rs):raise ValueError('Color scan original bytes/bindings differ')
 neighbors=same_functions(before,after,(FUNCTION,))
 if neighbors!=3 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Color scan raw neighbors/pools changed')
 guards=guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings);(output/'qualified-guards.csv').write_bytes(guards)
 for label,obj,manifest in(('before-assembled',before,root/'conker/retail_word_patches.us.csv'),('qualified-padded',after,output/'qualified-guards.csv')):
  asm=output/(label+'.s');padded=asm.with_suffix('.o');asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=manifest,filename=OWNER))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(padded),str(asm)],check=True,capture_output=True)
 if(output/'before-assembled.o').read_bytes()!=values[OBJECT]:raise ValueError('Color scan baseline actual padder differs')
 (output/'before-padded.o').write_bytes(values[OBJECT]);(output/'proposed-owner.c').write_text(recovered_owner(values[SOURCE].decode()))
 a,fa=link_owner(root,output,output/'before-padded.o',OWNER);b,fb=link_owner(root,output,output/'qualified-padded.o',OWNER);at=fb[FUNCTION]['value'];expected={n:dict(info)for n,info in fa.items()};expected[FUNCTION]['size']=SIZE
 if fa[FUNCTION]['size']!=8 or fb!=expected or a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]or b[at:at+SIZE]!=values['conker/conker.us.bin'][ROM:ROM+SIZE]:raise ValueError('Color scan padded body/address/extent changed')
 if same_functions(output/'before-padded.o',output/'qualified-padded.o',(FUNCTION,))!=3 or normalized_pools(output/'before-padded.o')!=normalized_pools(output/'qualified-padded.o'):raise ValueError('Color scan padded neighbors changed')
 frozen={str(p.relative_to(output)):sha(p.read_bytes())for n in('before-retail','after-retail')for suffix in('.c','-processed.c','.o','-diagnostics.txt')for p in[output/(n+suffix)]}
 (output/'frozen-raw.json').write_text(json.dumps(frozen,indent=2)+'\n')
 report=dict(words=46,raw_words=46,frame=0,guards=sum(1 for row in csv.DictReader(io.StringIO(guards.decode()))if row['function']==FUNCTION),omitted_return_copies=0,relocations=6,preserved_neighbors=3,compiler_only=False,count_return_preserved=True,shared_headers_unchanged=True)
 (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def make_shadow(root,output):
 check_inputs(root,output);conker=root/'conker';shadow=output/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
 target=(shadow/'src/game/generated_3FC60.c.o').relative_to(conker).as_posix()
 plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
 (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
 for line in plan.stdout.replace(chr(92)+chr(10),'').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected color scan Make command: '+repr(args))
  args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a=='src/game/generated_3FC60.c'else (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
  redirect=None
  if '>'in args:
   if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown color scan Make redirect')
   redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
  if p.returncode or p.stderr or(p.stdout and redirect is None):raise ValueError('Color scan Make command failed: '+p.stdout+p.stderr)
  if redirect is not None:redirect.write_text(p.stdout)
  commands.append(args)
 actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
 if len(compilers)!=1 or '-O2'not in compilers[0]or '-g3'in compilers[0]or any('-loopunroll'in f for f in compilers[0]):raise ValueError('Color scan Make profile changed')
 if same_functions(output/'after-retail.o',Path(str(actual)+'.compact'))!=4 or normalized_pools(output/'after-retail.o')!=normalized_pools(Path(str(actual)+'.compact')):raise ValueError('Color scan Make raw owner differs')
 if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Color scan Make padded object bytes differ')
 report=dict(commands=len(commands),normal_retail_O2=True,compact_functions_equal=4,complete_padded_object_equal=True,inherited_Make_warnings=plan.stderr)
 (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report

def reorder_metadata(image):
 # Two pre-existing linker serialization cycles; named definitions stay fixed.
 result=bytearray(image);entries={n:(at,fields,string)for at,n,fields,string in symbol_rows(image)}
 for names in(('func_150BABE0','D_8009EF78'),('D_800991CC','D_8009E6DC')):
  group=[entries[n]for n in names];start,string_at=group[0][0],group[0][2];base=string_at-group[0][1][0]
  if any(row[0]!=start+i*16 or row[2]-row[1][0]!=base for i,row in enumerate(group)):raise ValueError('Color scan metadata cycle changed')
  literal=b''.join(n.encode()+b'\0'for n in names)
  if image[string_at:string_at+len(literal)]!=literal:raise ValueError('Color scan metadata strings changed')
  for i,n in enumerate(names[1:]+names[:1]):
   fields=list(entries[n][1]);fields[0]=string_at-base;struct.pack_into('>IIIBBH',result,start+i*16,*fields);literal=n.encode()+b'\0';result[string_at:string_at+len(literal)]=literal;string_at+=len(literal)
 canonical=lambda data:sorted((n,fields[1:])for _,n,fields,_ in symbol_rows(data))
 if canonical(image)!=canonical(result):raise ValueError('Color scan named metadata definitions changed')
 return bytes(result)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE:raise ValueError('Color scan strict predecessor changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[offset for offset,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,8)and fields[3]&15==2]
 if len(rows)!=1:raise ValueError('Color scan original symbol extent changed')
 struct.pack_into('>I',result,rows[0]+8,SIZE)
 return reorder_metadata(bytes(result))

def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Color scan image differs from complete body/size prediction')

def audit(root,output):
 values=check_inputs(root,output,True);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 check_image(values['conker/build/conker.us.elf'],(root/'conker/build/conker.us.elf').read_bytes(),truth)
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Color scan changed another linked body/address')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Color scan protected Game data changed')
 report=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report


ARTIFACTS=('before-retail.o','after-retail.o','before-padded.o','qualified-padded.o','proposed-owner.c','qualified-guards.csv','original-func_15012ED8.o','first-linked.elf')
def freeze_prepared(output):
 if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect completed color scan artifact freeze')
 rows={n:sha((output/n).read_bytes())for n in ARTIFACTS};(output/'artifact-fingerprint.json').write_text(json.dumps(rows,indent=2)+'\n');return rows

def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Color scan artifact set changed')
 for n,h in rows.items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Color scan prepared artifact changed: '+n)
 for n,h in json.loads((output/'frozen-raw.json').read_text()).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Color scan raw execution changed: '+n)
 q=json.loads((output/'qualification.json').read_text())
 if sha((output/'make-shadow-plan.txt').read_bytes())!=q['Make_plan_SHA256']:raise ValueError('Color scan Make plan changed')
 if(output/'make-shadow/src/game/generated_3FC60.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Color scan Make output changed')
 return rows
