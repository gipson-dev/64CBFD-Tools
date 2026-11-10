"""Direct actor-slot sector search, actual Make and complete-image gate."""
import csv,hashlib,io,json,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
import os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-slot-sector-search-1505DDA8-match'
NAME='func_1505DDA8';SOURCE='conker/src/game_83300.c';ENTRY=0x1505DDA8;ROM=0x8B258;SIZE=360
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_slot_sector_search_1505dda8_manifest.json').read_text())
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
BASE='/* Find the first active actor slot inside the scaled radius and heading sector. */\ns8 func_1505DDA8(struct127 *actor, u8 unused, u16 angle_range, f32 scale) {\n    u8 slot;\n    u16 heading;\n    f32 horizontal_squared;\n    f32 height;\n    f32 radius;\n\n    for (slot = 0; slot <= D_80082FA0; slot++) {\n        if (D_800CC2D0[slot].interaction_state == 0) {\n            continue;\n        }\n        radius = actor->xz_velocity * scale * 0.5f;\n        if (func_1505DF10(actor, slot, &heading, &horizontal_squared, &height, 0) < radius * radius) {\n            if ((u16)(actor->unk76 - heading + angle_range / 2) < angle_range) {\n                return (s8)slot;\n            }\n        }\n    }\n    return -1;\n}'
DECL='f32 func_1505DF10(struct127 *, u8, u16 *, f32 *, f32 *, s32);'
def proposal(old,selected):
 return old.replace('s32 func_1505DDA8();','s8 func_1505DDA8(struct127 *, u8, u16, f32);').replace('s32 func_1505DF10();',DECL).replace(body(old,NAME),selected)
def payload(path):
 t,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return t[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
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
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption slot-sector input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen slot-sector input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown slot-sector source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed slot-sector qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed slot-sector result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Float-pair source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def proposals():
 old=(p.out/'frozen'/p.SOURCE).read_text();source=p.proposal(old,p.BASE).replace('/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_1505DDA8.s. */\n','')
 nl='\r\n'if b'\r\n'in(p.out/'frozen'/p.SOURCE).read_bytes()else'\n';(p.out/'game-proposal.c').write_bytes(source.replace('\n',nl).encode());(p.out/'selected-source.c').write_bytes((p.out/'game-proposal.c').read_bytes());(p.out/'proposed-guards.csv').write_bytes((p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
 (p.out/'selected-body.c').write_text(BASE)
 assert sha((out/'game-proposal.c').read_bytes())==MANIFEST['installed_hashes'][SOURCE]
 return {'game_83300':p.out/'game-proposal.c'}
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
 conker=p.root/'conker';script=(p.out/'frozen/conker/build/conker.ld').read_text()
 for owner,f in targets.items():
  name='build/src/'+owner+'.c.o';assert script.count(name)==1;script=script.replace(name,f.relative_to(conker).as_posix())
 path=p.out/'qualified-image.ld';path.write_text(script);elf=p.out/'qualified-image.elf'
 argv=['mips-linux-gnu-ld','-T',path.relative_to(conker).as_posix(),*[a for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')for a in('-T',n)],'--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(conker).as_posix()]
 subprocess.run(argv,cwd=conker,capture_output=True,check=True);return elf

def strict_image(before,actual,payloads):
 truth=payloads[NAME]
 if sha(before)!=FROZEN['conker/build/conker.us.elf']or len(truth)!=360 or sha(truth)!=MANIFEST['truth_sha256']:raise ValueError('Changed direct slot-sector image inputs')
 expected=bytearray(before);at=elf_slot_offset(before,ENTRY,360);expected[at:at+360]=truth
 rows=[r for r in symbol_rows(before)if r[1]==NAME];assert len(rows)==1 and rows[0][2][2]==12
 struct.pack_into('>I',expected,rows[0][0]+8,360)
 if bytes(expected)!=actual:raise ValueError('Full slot-sector image differs beyond the declared body and symbol size')
 return dict(changed_bytes=sum(a!=b for a,b in zip(before,actual)),metadata_groups=[],strict_exclusions=0)
def main():
 frozen,installed=freeze();sources=proposals();targets,commands=actual_make(sources);path=targets['game_83300'];raw=Path(str(path)+'.compact')
 before,old_diagnostics=p.compile_owner(p.root,p.out,(p.out/'frozen'/p.SOURCE).read_text(),'independent-before')
 after,new_diagnostics=p.compile_owner(p.root,p.out,sources['game_83300'].read_text(),'independent-proposed')
 assert same_functions(before,after,(p.NAME,))==88 and same_functions(raw,after)==89
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(raw)
 assert sections(before)['.reginfo']==sections(after)['.reginfo']==sections(raw)['.reginfo']
 assert p.diagnostic_rows(old_diagnostics)==p.diagnostic_rows(new_diagnostics)
 (p.out/'selected.o').write_bytes(after.read_bytes())
 assert same_functions(p.out/'frozen/conker/build/src/game_83300.c.o',path,(p.NAME,))==88
 payload,refs=p.payload(raw);assert sha(payload)=='2cf85beab984bd928109f18e69537a656b5abee363fc8f83e79973b972cfc2e8'and refs=={72:[('R_MIPS_HI16','D_80082FA0')],76:[('R_MIPS_LO16','D_80082FA0')],96:[('R_MIPS_HI16','D_800CC2D0')],104:[('R_MIPS_LO16','D_800CC2D0')],180:[('R_MIPS_26','func_1505DF10')],272:[('R_MIPS_HI16','D_80082FA0')],276:[('R_MIPS_LO16','D_80082FA0')]}
 assert p.payload(path)==(payload,refs)
 ws=p.bound_blob(payload,refs,{'D_80082FA0':0x80082FA0,'D_800CC2D0':0x800CC2D0,'func_1505DF10':0x1505DF10});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>90I',*ws)==truth
 elf=link(targets);original=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(original,actual,{p.NAME:truth})
 old,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in old if old[n]!=new[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 assert(p.out/'proposed-guards.csv').read_bytes()==(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes()
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in[(p.SOURCE,sources['game_83300']),('conker/build/src/game_83300.c.o',path),('conker/build/conker.us.elf',elf)]}
 assert hashes==MANIFEST['installed_hashes']and image==MANIFEST['image']
 report=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=90,frame=112,guards=0,non_target_neighbors=88,actual_Make_commands=len(commands),diagnostics=sum(p.diagnostic_rows(new_diagnostics).values()),functions=len(new),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer root differs from the bound slot-sector workspace")
 return main()

if __name__=="__main__":prepare()
