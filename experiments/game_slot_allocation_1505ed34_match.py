"""Private actor-slot allocation source, direct owner and strict full-image qualification."""
import csv,hashlib,io,json,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
import os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-slot-allocation-1505ED34-match'
NAME='func_1505ED34';SOURCE='conker/src/game_83300.c';ENTRY=0x1505ED34;ROM=0x8C1E4;SIZE=380
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_slot_allocation_1505ed34_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
BASE='/* Allocate an actor, recycling eligible entries before using reserved slot 25. */\nu8 *func_1505ED34(void) {\n    s32 index;\n    struct127 *actor;\n\n    for (index = 0, actor = D_800CC2D0; index < 25 && actor->interaction_state != 0; index++, actor++) {\n    }\n    if (index == 25) {\n        for (actor = D_800CC2D0, index = 0; index < 25 && (actor->interaction_state != 0x27 || actor->unk1D4 != NULL); index++, actor++) {\n        }\n        if (index != 25 && actor->interaction_state != 0) {\n            func_15060F28(actor, 0);\n        }\n    }\n    if (index == 25) {\n        for (actor = D_800CC2D0, index = 0; index < 25 && actor->interaction_state != 0x27; index++, actor++) {\n        }\n        if (index != 25 && actor->interaction_state != 0) {\n            func_15060F28(actor, 0);\n        }\n    }\n    if (index == 25 && actor->interaction_state != 0) {\n        func_15060F28(actor, 0);\n    }\n    func_1505F188(actor);\n    return (u8 *)actor;\n}'
def proposal(old, selected):
    marker = '/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_1505ED34.s. */\n'
    return old.replace('s32 func_1505ED34();', 'u8 *func_1505ED34(void);').replace(marker, '').replace(body(old, NAME), selected)

def payload(path):
    text, fs, rs = parse_object(path)
    start, size = fs[NAME]['value'], fs[NAME]['size']
    return text[start:start + size], {i-start:v for i,v in rs.items() if start <= i < start+size}

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
parse_object=p.parse_object
sha=lambda data:hashlib.sha256(data).hexdigest()
MUTABLE=('conker/src/game_83300.c','conker/build/src/game_83300.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin','conker/retail_word_patches.us.csv')
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
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');source=p.proposal(old,p.BASE)
 nl='\r\n'if b'\r\n'in(p.out/'frozen'/p.SOURCE).read_bytes()else'\n';(p.out/'game-proposal.c').write_bytes(source.replace('\n',nl).encode());(p.out/'selected-source.c').write_bytes((p.out/'game-proposal.c').read_bytes())
 (p.out/'proposed-guards.csv').write_bytes((p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes());(p.out/'selected-body.c').write_text(p.BASE);return {'game_83300':p.out/'game-proposal.c'}

def actual_make(sources):
 conker=p.root/'conker';shadow=p.out/'make-shadow';targets={owner:shadow/('src/'+owner+'.c.o')for owner in sources}
 for f in targets.values():f.parent.mkdir(parents=True,exist_ok=True)
 args=['make','-n','-B','-o','Makefile','-o','retail_word_patches.us.csv','BUILD_DIR='+shadow.relative_to(conker).as_posix(),*[f.relative_to(conker).as_posix()for f in targets.values()]]
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
def main():
 frozen,installed=freeze();sources=proposals();targets,commands=actual_make(sources);path=targets['game_83300'];raw=Path(str(path)+'.compact')
 before,old_diagnostics=p.compile_owner(p.root,p.out,(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8'),'independent-before');after,new_diagnostics=p.compile_owner(p.root,p.out,sources['game_83300'].read_text(encoding='utf-8'),'independent-proposed')
 assert same_functions(before,after,(p.NAME,))==88 and same_functions(raw,after)==89
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(raw)
 assert sections(before)['.reginfo']==sections(after)['.reginfo']==sections(raw)['.reginfo']
 assert p.diagnostic_rows(old_diagnostics)==p.diagnostic_rows(new_diagnostics)
 (p.out/'selected.o').write_bytes(after.read_bytes())
 assert same_functions(p.out/'frozen/conker/build/src/game_83300.c.o',path,(p.NAME,))==88
 payload,refs=p.payload(raw);assert p.payload(path)==(payload,refs)
 ws=p.bound_blob(payload,refs,{n:int(n.split('_')[1],16) for es in refs.values() for _,n in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>95I',*ws)==truth
 oldguards=list(csv.DictReader(io.StringIO((p.out/'frozen/conker/retail_word_patches.us.csv').read_text(encoding='utf-8'))));newguards=list(csv.DictReader(io.StringIO((p.out/'proposed-guards.csv').read_text(encoding='utf-8'))));assert newguards==oldguards and (p.out/'proposed-guards.csv').read_bytes()==(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes()
 elf=link(targets);original=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(original,actual,{p.NAME:truth})
 old,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in old if old[n]!=new[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 hashes={n:sha(f.read_bytes())for n,f in[(p.SOURCE,sources['game_83300']),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game_83300.c.o',path),('conker/build/conker.us.elf',elf)]};live_inputs(installed)
 assert hashes==MANIFEST['installed_hashes']and image==MANIFEST['image']
 report=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=95,frame=32,guards=0,non_target_neighbors=88,actual_Make_commands=len(commands),diagnostics=sum(p.diagnostic_rows(new_diagnostics).values()),functions=len(new),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from bound allocation workspace")
 return main()

if __name__=="__main__":prepare()
