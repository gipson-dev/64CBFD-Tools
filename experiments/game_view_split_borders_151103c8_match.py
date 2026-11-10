"""Private actor-slot allocation source, direct owner and strict full-image qualification."""
import csv,hashlib,io,json,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
import os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-151103C8-match'
NAME='func_151103C8';OWNER='game/generated_13D350';SOURCE='conker/src/game/generated_13D350.c';ENTRY=0x151103C8;ROM=0x13D878;SIZE=380
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_view_split_borders_151103c8_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\nextern s32 D_80082FA0, D_80082FA4;\ns32 func_1501A490(Gfx *, s16, s32, s32, s32, s32);\nGfx *func_1501A6CC(Gfx *, s32, s32, s32, s32);\nGfx *func_15110544(Gfx *, s32, s32, s32, s32, u8, u8, u8);\n'
BASE='/* Fill the selected view and append the active split-screen dividers. */\nGfx *func_151103C8(Gfx *commands, f32 unusedX, f32 unusedY, f32 unusedZ) {\n    Record13D350 *view = (Record13D350 *)((u32)D_800BE628 + (u32)D_80082FA4 * 0x180);\n\n    commands = func_15110544(commands, (s32)view->left, (s32)view->top,\n        (s32)(view->right - 1.0f), (s32)view->bottom,\n        D_800DBEA8[0], D_800DBEA8[1], D_800DBEA8[2]);\n    if (D_80082FA0 != 0 && D_80082FA4 == 0) {\n        gDPPipeSync(commands++);\n        commands = (Gfx *)func_1501A490(commands, 0xFF, 0, 0, 0, 0);\n        gDPSetFillColor(commands++, 0x00010001);\n        commands = func_1501A6CC(commands, 0, (D_800BE624 >> 1) - 6,\n            D_800BE620, (D_800BE624 >> 1) + 6);\n        if (D_80082FA0 != 1) {\n            commands = func_1501A6CC(commands, (D_800BE620 >> 1) - 1, 0,\n                (D_800BE620 >> 1) + 1, D_800BE624);\n        }\n    }\n    return commands;\n}'
def proposal(old,selected):
 return old.replace('#include <ultra64.h>','#include <ultra64.h>\n'+DECLS).replace('u8 pad0[0xBC];','u8 pad0[0x24];\n    f32 top, bottom, left, right;\n    u8 pad34[0x88];').replace(body(old,NAME),selected)

def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
parse_object=p.parse_object
sha=lambda data:hashlib.sha256(data).hexdigest()
MUTABLE=('conker/src/game/generated_13D350.c','conker/build/src/game/generated_13D350.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin','conker/retail_word_patches.us.csv')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption view-borders input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen view-borders input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown view-borders source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed view-borders qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed view-borders result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('View-borders source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def proposals():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');source=p.proposal(old,p.BASE)
 nl='\r\n'if b'\r\n'in(p.out/'frozen'/p.SOURCE).read_bytes()else'\n';(p.out/'game-proposal.c').write_bytes(source.replace('\n',nl).encode());(p.out/'selected-source.c').write_bytes((p.out/'game-proposal.c').read_bytes())
 (p.out/'proposed-guards.csv').write_bytes((p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes());(p.out/'selected-body.c').write_text(p.BASE);return {'game/generated_13D350':p.out/'game-proposal.c'}

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

def strict_image(before,actual,payloads,groups=None):
 expected=bytearray(before);sizes={'func_151103C8':380};old=symbol_rows(before);new=symbol_rows(actual);counts=Counter(r[1]for r in old);lookup={r[1]:r for r in old if counts[r[1]]==1}
 assert len(old)==len(new)and all(n in lookup for n in sizes)
 assert Counter((r[1],r[2][1],sizes.get(r[1],r[2][2]),*r[2][3:])for r in old)==Counter((r[1],*r[2][1:])for r in new),'Named ELF definition changed'
 for name,payload in payloads.items():
  r=lookup[name];assert r[2][2]==12 and len(payload)==sizes[name]
  at=elf_slot_offset(before,r[2][1],len(payload));expected[at:at+len(payload)]=payload;struct.pack_into('>I',expected,r[0]+8,len(payload))
 if groups is None:
  changed=[i for i in range(len(old))if old[i][1]!=new[i][1]];runs=[]
  for i in changed:
   if not runs or i!=runs[-1][-1]+1:runs.append([i])
   else:runs[-1].append(i)
  groups=[([old[i][1]for i in run],[new[i][1]for i in run])for run in runs]
 for oldnames,newnames in groups:
  assert len(oldnames)==len(set(oldnames))and set(oldnames)==set(newnames)
  entries=[lookup[n]for n in oldnames];slots=[r[0]for r in entries];starts=[r[3]for r in entries]
  assert slots==list(range(slots[0],slots[0]+16*len(slots),16))
  assert all(starts[i+1]==starts[i]+len(oldnames[i])+1 for i in range(len(starts)-1))
  base=starts[0]-entries[0][2][0];position=starts[0]
  for slot,name in zip(slots,newnames):
   record=bytearray(before[lookup[name][0]:lookup[name][0]+16]);struct.pack_into('>I',record,0,position-base)
   if name in sizes:struct.pack_into('>I',record,8,sizes[name])
   expected[slot:slot+16]=record;label=name.encode()+b'\0';expected[position:position+len(label)]=label;position+=len(label)
  assert position==starts[-1]+len(oldnames[-1])+1
 if bytes(expected)!=actual:
  diffs=[i for i,(a,b)in enumerate(zip(expected,actual))if a!=b];raise ValueError(('Strict slot-sector image has unexplained differences',len(diffs),diffs[:20],len(expected),len(actual)))
 return dict(changed_bytes=sum(a!=b for a,b in zip(before,actual)),metadata_groups=[[list(a),list(b)]for a,b in groups],strict_exclusions=0)

def main():
 frozen,installed=freeze();sources=proposals();targets,commands=actual_make(sources);path=targets['game/generated_13D350'];raw=Path(str(path)+'.compact')
 before,old_diagnostics=p.compile_owner(p.root,p.out,(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8'),'independent-before');after,new_diagnostics=p.compile_owner(p.root,p.out,sources['game/generated_13D350'].read_text(encoding='utf-8'),'independent-proposed')
 assert same_functions(before,after,(p.NAME,))==33 and same_functions(raw,after)==34
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(raw)
 assert sections(after)['.reginfo']==sections(raw)['.reginfo']
 (p.out/'reginfo.json').write_text(json.dumps({label:sections(obj)['.reginfo'][1].hex()for label,obj in [('before',before),('after',after),('actual-Make',raw)]},indent=2)+'\n')
 assert p.diagnostic_rows(old_diagnostics)==p.diagnostic_rows(new_diagnostics)
 (p.out/'selected.o').write_bytes(after.read_bytes())
 assert same_functions(p.out/'frozen/conker/build/src/game/generated_13D350.c.o',path,(p.NAME,))==33
 payload,refs=p.payload(raw);assert p.payload(path)==(payload,refs)
 ws=p.bound_blob(payload,refs,{n:int(n.split('_')[1],16) for es in refs.values() for _,n in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>95I',*ws)==truth
 oldguards=list(csv.DictReader(io.StringIO((p.out/'frozen/conker/retail_word_patches.us.csv').read_text(encoding='utf-8'))));newguards=list(csv.DictReader(io.StringIO((p.out/'proposed-guards.csv').read_text(encoding='utf-8'))));assert newguards==oldguards and (p.out/'proposed-guards.csv').read_bytes()==(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes()
 elf=link(targets);original=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(original,actual,{p.NAME:truth})
 old,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in old if old[n]!=new[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 hashes={n:sha(f.read_bytes())for n,f in[(p.SOURCE,sources['game/generated_13D350']),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game/generated_13D350.c.o',path),('conker/build/conker.us.elf',elf)]};live_inputs(installed)
 assert hashes==MANIFEST['installed_hashes']and image==MANIFEST['image']
 report=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=95,frame=40,guards=0,non_target_neighbors=33,actual_Make_commands=len(commands),diagnostics=sum(p.diagnostic_rows(new_diagnostics).values()),functions=len(new),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from bound view-borders workspace")
 return main()

if __name__=="__main__":prepare()
