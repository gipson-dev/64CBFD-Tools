"""Semantic event dispatch, preserved switch pool and strict full-image qualification."""
import csv,hashlib,io,json,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
import os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-event-dispatch-1509D780-match'
NAME='func_1509D780';OWNER='game/generated_C9EC0';SOURCE='conker/src/game/generated_C9EC0.c';ENTRY=0x1509D780;ROM=0xCAC30;SIZE=380
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_event_dispatch_1509d780_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\nstruct struct127;\nextern u8 D_800D9920;\ns32 func_150EB8C4(void);\nvoid func_150F9720(u8);\nvoid func_151616D0(u8, u8, s32);\nstruct struct127 *func_1505EEF4(s32);\ns32 func_150F6DB0(u8 *);\nvoid func_151CD394(s32);\nvoid func_150E35DC(s32);\nvoid func_150B3DD0(void);\ns32 func_150C5C9C(s32);\nvoid func_150C522C(void);\nvoid func_151D2718(s32);\n'
def compile_owner(root,out,source,name):
 assert '#pragma GLOBAL_ASM'not in source
 path=out/(name+'.c');obj=out/(name+'.o');path.write_text(source)
 includes=['.','include','include/2.0L','include/2.0L/PR','include/libc','src/libultra/os','src/libultra/audio','src/libultra/io']
 args=[str(root/'ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-woff','649,838',*[flag for n in includes for flag in('-I',n)],'-O2','-g3','-Wo,-loopunroll,0','-mips2','-o32','-o',obj.relative_to(root/'conker').as_posix(),path.relative_to(root/'conker').as_posix()]
 result=subprocess.run(args,cwd=root/'conker',capture_output=True,text=True);diagnostics=result.stdout+result.stderr;(out/(name+'-diagnostics.txt')).write_text(diagnostics);assert result.returncode==0,diagnostics
 return obj,diagnostics

BASE='/* Dispatch script actions; only the null-actor return explicitly defines a C result. */\ns32 func_1509D780(s32 command, u8 *record) {\n    struct struct127 *actor;\n\n    switch (command) {\n        case 41:\n            func_150EB8C4();\n            break;\n        case 39:\n            func_150F9720(record[7]);\n            break;\n        case 38:\n            func_151616D0(0x29, 0x18, 0);\n            break;\n        case 36:\n            actor = func_1505EEF4(*(u32 *)(record + 4) & 0xFFF);\n            if (actor != NULL) {\n                func_150F6DB0((u8 *)actor);\n            }\n            break;\n        case 26:\n            func_151616D0(0x26, 0x18, 0);\n            break;\n        case 18:\n            func_151CD394(*(s32 *)(record + 4));\n            break;\n        case 2:\n            D_800D9920 = 0;\n            break;\n        case 4:\n        case 5:\n        case 6:\n            func_150E35DC(command >> 6);\n            break;\n        case 8:\n            func_150B3DD0();\n            break;\n        case 9:\n            actor = func_1505EEF4(*(u32 *)(record + 4) & 0xFFF);\n            if (actor == NULL) {\n                return 0;\n            }\n            func_150C5C9C((s32)actor);\n            break;\n        case 10:\n            func_150C522C();\n            break;\n        case 19:\n            func_151D2718(*(s16 *)(record + 6));\n            break;\n        case 21:\n            func_151616D0(0x20, 0x18, 0);\n            break;\n        case 22:\n            func_151616D0(0x23, 0x28, 0);\n            func_151616D0(0x24, 0x28, 0);\n            break;\n    }\n}'
def proposal(old,selected):return old.replace('#include <ultra64.h>','#include <ultra64.h>\n'+DECLS).replace(body(old,NAME),selected)

def payload(path):
 t,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return t[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
parse_object=p.parse_object
sha=lambda data:hashlib.sha256(data).hexdigest()
MUTABLE=('conker/Makefile','conker/src/game/generated_C9EC0.c','conker/build/src/game/generated_C9EC0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin','conker/retail_word_patches.us.csv')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption slot-allocation input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen slot-allocation input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown slot-allocation source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed slot-allocation qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed slot-allocation result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Slot-allocation source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def proposals():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');source=p.proposal(old,p.BASE);nl='\r\n'if b'\r\n'in(p.out/'frozen'/p.SOURCE).read_bytes()else'\n';(p.out/'game-proposal.c').write_bytes(source.replace('\n',nl).encode());(p.out/'selected-source.c').write_bytes((p.out/'game-proposal.c').read_bytes());(p.out/'selected-body.c').write_text(p.BASE)
 before=(p.out/'frozen/conker/Makefile').read_text(encoding='utf-8');needle='$(BUILD_DIR)/$(SRC_DIR)/game/generated_C9EC0.c.o: OPT_FLAGS := -O2 -g3 -Wo,-loopunroll,0';assert before.count(needle)==1;line='$(BUILD_DIR)/$(SRC_DIR)/game/generated_C9EC0.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009F1AC_game';assert line not in before;make=before.replace(needle,needle+'\n'+line);nl='\r\n'if b'\r\n'in(p.out/'frozen/conker/Makefile').read_bytes()else'\n';(p.out/'proposed-Makefile').write_bytes(make.replace('\n',nl).encode())
 (p.out/'proposed-guards.csv').write_bytes((p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
 asm=(p.out/'frozen/conker/asm/C9EC0.s').read_text(encoding='utf-8');start=asm.index('glabel func_1509D780'+chr(10));end=asm.index('endlabel func_1509D780',start)+len('endlabel func_1509D780');reference=asm[start:end]+chr(10)
 reference_path=p.out/'original-target.s'
 if reference_path.exists():assert reference_path.read_text(encoding='utf-8')==reference
 reference_path.write_text(reference,encoding='utf-8');return {p.OWNER:p.out/'game-proposal.c'}

def actual_make(sources):
 conker=p.root/'conker';shadow=p.out/'make-shadow';targets={owner:shadow/('src/'+owner+'.c.o')for owner in sources}
 for f in targets.values():f.parent.mkdir(parents=True,exist_ok=True)
 args=['make','-f',(p.out/'proposed-Makefile').relative_to(conker).as_posix(),'-n','-B','-o','Makefile','-o','retail_word_patches.us.csv','BUILD_DIR='+shadow.relative_to(conker).as_posix(),*[f.relative_to(conker).as_posix()for f in targets.values()]]
 plan=subprocess.run(args,cwd=conker,capture_output=True,text=True,check=True);commands=[];logs=[]
 (p.out/'actual-Make-plan.txt').write_text(plan.stdout)
 for line in plan.stdout.replace('\\\n',' ').splitlines():
  if not line.strip()or line.startswith('make['):continue
  parts=shlex.split(line)
  if parts[0]=='rm':
   assert parts[1]=='-f'and all((conker/a).resolve().is_relative_to(shadow.resolve())for a in parts[2:]);continue
  assert parts[0]in('python3','../ido/ido5.3_recomp/cc','mips-linux-gnu-as'),parts
  replacements={'src/'+owner+'.c':source.relative_to(conker).as_posix()for owner,source in sources.items()};replacements['retail_word_patches.us.csv']=(p.out/'proposed-guards.csv').relative_to(conker).as_posix();parts=[replacements.get(a,a)for a in parts];line=shlex.join(parts)
  if '>'in parts:
   i=parts.index('>');assert i==len(parts)-2;argv,target=parts[:i],parts[-1];r=subprocess.run(argv,cwd=conker,capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(argv,r.stdout,r.stderr);(conker/target).write_text(r.stdout)
  else:
   argv=parts;r=subprocess.run(argv,cwd=conker,capture_output=True,text=True);assert r.returncode==0,(argv,r.stdout,r.stderr)
  commands.append(line);logs.append(dict(command=line,argv=argv,redirect=parts[-1]if '>'in parts else None,stdout=''if '>'in parts else r.stdout,stderr=r.stderr))
 (p.out/'actual-Make.json').write_text(json.dumps(dict(commands=commands,warnings=plan.stderr,logs=logs),indent=2)+'\n')
 assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==1
 return targets,commands

def link(targets):
 conker=p.root/'conker';script=(p.out/'frozen/conker/build/conker.ld').read_text(encoding='utf-8')
 for owner,f in targets.items():
  name='build/src/'+owner+'.c.o';assert script.count(name)==1;script=script.replace(name,f.relative_to(conker).as_posix())
 path=p.out/'qualified-image.ld';path.write_text(script);elf=p.out/'qualified-image.elf'
 argv=['mips-linux-gnu-ld','-T',path.relative_to(conker).as_posix(),*[a for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')for a in('-T',n)],'--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(conker).as_posix()]
 subprocess.run(argv,cwd=conker,capture_output=True,check=True);return elf

def strict_image(before,actual,payloads):
 truth=payloads[NAME]
 if sha(before)!=FROZEN['conker/build/conker.us.elf']or len(truth)!=380 or sha(truth)!=MANIFEST['truth_sha256']:raise ValueError('Changed direct slot-allocation image inputs')
 expected=bytearray(before);at=elf_slot_offset(before,ENTRY,380);expected[at:at+380]=truth
 symbol=[v for v in symbol_rows(before)if v[1]==NAME];assert len(symbol)==1 and symbol[0][2][2]==12;struct.pack_into('>I',expected,symbol[0][0]+8,380)
 if bytes(expected)!=actual:raise ValueError('Allocation image differs beyond body and symbol size')
 return dict(changed_bytes=sum(a!=b for a,b in zip(before,actual)),metadata_groups=[],strict_exclusions=0)
def check_pool(before,after):
 old,new=normalized_pools(before),normalized_pools(after);assert old=={'.rodata':None,'.data':None}and new['.data']is None
 raw,owners=new['.rodata'];assert len(raw)==160 and not any(raw)and len(owners)==40
 data=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(data,0x8009F1AC,160);truth=struct.unpack_from('>40I',data,at);assert all(offset==4*i and name==p.NAME and p.ENTRY+delta==truth[i]for i,(offset,name,delta)in enumerate(owners))
 return dict(entries=40,bytes=160,retail_address=0x8009F1AC,all_targets_exact=True,other_pools_unchanged=True)

def main():
 frozen,installed=freeze();sources=proposals();targets,commands=actual_make(sources);path=targets[p.OWNER];raw=Path(str(path)+'.compact')
 before,old_diagnostics=p.compile_owner(p.root,p.out,(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8'),'independent-before');after,new_diagnostics=p.compile_owner(p.root,p.out,sources[p.OWNER].read_text(encoding='utf-8'),'independent-proposed')
 assert same_functions(before,after,(p.NAME,))==18 and same_functions(raw,after)==19
 assert normalized_pools(after)==normalized_pools(raw);pool_proof=check_pool(before,after)
 assert sections(before)['.reginfo']==sections(after)['.reginfo']==sections(raw)['.reginfo']
 assert p.diagnostic_rows(old_diagnostics)==p.diagnostic_rows(new_diagnostics)
 (p.out/'selected.o').write_bytes(after.read_bytes())
 assert same_functions(p.out/'frozen/conker/build/src/game/generated_C9EC0.c.o',path,(p.NAME,))==18
 payload,refs=p.payload(raw);padded_refs={i:[(k,'jtbl_8009F1AC_game'if n=='.rodata'else n)for k,n in es]for i,es in refs.items()};assert p.payload(path)==(payload,padded_refs)
 ws=p.bound_blob(payload,refs,{n:(0x8009F1AC if n=='.rodata'else int(n.split('_')[1],16))for es in refs.values()for _,n in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>95I',*ws)==truth
 oldguards=list(csv.DictReader(io.StringIO((p.out/'frozen/conker/retail_word_patches.us.csv').read_text(encoding='utf-8'))));newguards=list(csv.DictReader(io.StringIO((p.out/'proposed-guards.csv').read_text(encoding='utf-8'))));assert newguards==oldguards and (p.out/'proposed-guards.csv').read_bytes()==(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes()
 elf=link(targets);original=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(original,actual,{p.NAME:truth})
 old,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in old if old[n]!=new[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 hashes={n:sha(f.read_bytes())for n,f in[(p.SOURCE,sources[p.OWNER]),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/Makefile',p.out/'proposed-Makefile'),('conker/build/src/game/generated_C9EC0.c.o',path),('conker/build/conker.us.elf',elf)]};live_inputs(installed)
 assert hashes==MANIFEST['installed_hashes']and image==MANIFEST['image']
 report=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=95,frame=24,guards=0,non_target_neighbors=18,switch_pool=pool_proof,actual_Make_commands=len(commands),diagnostics=sum(p.diagnostic_rows(new_diagnostics).values()),functions=len(new),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from bound allocation workspace")
 return main()

if __name__=="__main__":prepare()
