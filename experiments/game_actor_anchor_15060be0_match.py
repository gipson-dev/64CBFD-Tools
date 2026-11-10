"""Private actor anchor source, guarded owner and strict full-image qualification."""
import csv,hashlib,io,json,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
import os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-actor-anchor-15060BE0-match'
NAME='func_15060BE0';SOURCE='conker/src/game_83300.c';ENTRY=0x15060BE0;ROM=0x8E090;SIZE=372
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_actor_anchor_15060be0_manifest.json').read_text())
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
BASE='/* Update the actor anchor from its selected transform, or its own position. */\nvoid func_15060BE0(struct127 *actor) {\n    s32 updated = 0;\n    struct124 *model;\n    f32 *transform;\n    f32 x;\n    f32 z;\n    f32 y;\n    f32 length;\n    f32 direction_x;\n    f32 direction_y;\n    f32 direction_z;\n\n    if ((actor->id != 0xFF) && (actor->unk1D4 != NULL) && (D_800C3E90 == 0)) {\n        model = D_800D1C90[actor->id];\n        /* Metadata +0x27 selects a 0x40-byte matrix; +0x14 is signed distance. */\n        transform = ((f32 (*)[16])actor->unk1D4)[((u8 *)model)[0x27]];\n        /* The radial distance becomes the Y component after normalization. */\n        y = *(s16 *)model->pad14 * actor->y_scale;\n        if (y != 0.0f) {\n            direction_x = transform[4];\n            direction_y = transform[5];\n            direction_z = transform[6];\n            length = sqrtf(direction_x * direction_x + direction_y * direction_y + direction_z * direction_z);\n            if (length != 0.0f) {\n                length = y / length;\n            }\n            x = direction_x * length;\n            y = direction_y * length;\n            z = direction_z * length;\n        } else {\n            z = y = x = 0.0f;\n        }\n        /* Reserved actor bytes 0x1BC..0x1C1 contain three signed coordinates. */\n        ((s16 *)&actor->pad1BC)[0] = (s16)(s32)(transform[12] + x);\n        ((s16 *)&actor->pad1BC)[1] = (s16)(s32)(transform[13] + y);\n        *(s16 *)&actor->pad1C0 = (s16)(s32)(transform[14] + z);\n        updated = 1;\n    }\n    if (updated == 0) {\n        ((s16 *)&actor->pad1BC)[0] = (s16)(s32)actor->x_position;\n        ((s16 *)&actor->pad1BC)[1] = (s16)(s32)actor->y_position;\n        *(s16 *)&actor->pad1C0 = (s16)(s32)actor->z_position;\n    }\n}\n'
def proposal(old,selected):
 return old.replace('s32 func_15060BE0();','void func_15060BE0(struct127 *);').replace('#include "variables.h"','#include "variables.h"\n\nextern u8 D_800C3E90;').replace(body(old,NAME),selected)
def payload(path):
 t,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return t[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
"""Closed FP temporary renaming and equivalent positive-zero initialization."""
import hashlib,struct
SHA='05d15471760e6fb827162caafe3ea9f8504875105bb05eeb39f4d19ac4ac3d0c'
REFS={28:[('R_MIPS_HI16','D_800C3E90')],40:[('R_MIPS_LO16','D_800C3E90')],56:[('R_MIPS_HI16','D_800D1C90')],64:[('R_MIPS_LO16','D_800D1C90')]}
TEMP={4:10,6:4,8:6,10:8}
def fp_roles(w):
 op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
 if op==49:return set(),{ft}
 if op==57:return{ft},set()
 if op!=17:return set(),set()
 if fmt==0:return{fs},set()
 if fmt==4:return set(),{fs}
 assert fmt==16,(hex(w),fmt)
 if fn in(0,1,2,3):return{fs,ft},{fd}
 if fn in(4,5,6,7,13,32):return{fs},{fd}
 if fn in(50,60,62):return{fs,ft},set()
 raise ValueError(('Unqualified FP operation',hex(w)))
def renamed(w):
 op,fmt=w>>26,w>>21&31;fields=[]
 if op in(49,57):fields=[16]
 elif op==17:
  if fmt in(0,4):fields=[11]
  elif fmt==16:fields=[16,11,6]
  else:raise ValueError('Unknown float format')
 for shift in fields:
  reg=w>>shift&31
  if reg in TEMP:w=(w&~(31<<shift))|(TEMP[reg]<<shift)
 return w
def proof(ws):
 assert len(ws)==93 and ws[0]==0x27BDFFE8 and ws[91:]==[0x03E00008,0x27BD0018]
 assert all(w>>26!=3 and not(w>>26==0 and w&63==9)for w in ws)
 assert ws[28]==0x45030019 and ws[29]==0x44804000 and ws[51]==0x10000005 and ws[52]==0xE7A60004
 assert ws[53:57]==[0x44804000,0x44800000,0x44801000,0xE7A80004]
 closures=[]
 for begin,end in((57,77),(79,91)):
  defined=set()
  for i in range(begin,end):
   reads,writes=fp_roles(ws[i]);assert (reads&set(TEMP))<=defined,(i,reads,defined);defined|=writes&set(TEMP)
  assert defined==set(TEMP),(begin,defined);closures.append(dict(first=begin,last=end-1,all_temporary_reads_dominated=True,all_four_temporaries_defined=True))
 assert ws[77]==0x1440000D and ws[78]==0
 return dict(frame=24,zero_branch=28,zero_delay=29,unreachable_duplicate_zero=53,zero_block=[54,55,56],positive_zero_only=True,relative_memory_access_order_preserved=True,FP_temporary_cycle=TEMP,closed_regions=closures,no_calls=True,production_stack_offsets_changed=False)
def normalize(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=SHA or refs!=REFS:raise ValueError('Stale actor-anchor words or bindings')
 ws=list(struct.unpack('>93I',raw));proof(ws);normal=list(ws)
 normal[29]=normal[53]=0x44800000
 normal[54:57]=[0,0xE7A00004,0x46000086]
 for i in range(57,93):normal[i]=renamed(normal[i])
 assert sum(a!=b for a,b in zip(ws,normal))==27
 return struct.pack('>93I',*normal),dict(refs)
def rows(raw,refs):
 normal,_=normalize(raw,refs);result=[]
 for i,(a,b)in enumerate(zip(struct.unpack('>93I',raw),struct.unpack('>93I',normal))):
  if a!=b:result.append(dict(filename='game_83300',function='func_15060BE0',offset='0x%X'%(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Preserve equivalent positive-zero initialization and a closed FP temporary-register cycle',insert_after='',insert_after_relocations='',omit='false'))
 assert len(result)==27;return result
def checked_rows(actual,raw,refs):
 if actual!=rows(raw,refs):raise ValueError('Changed actor-anchor normalization rows')
 return actual

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
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption actor-anchor input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen actor-anchor input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown actor-anchor source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed actor-anchor qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed actor-anchor result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Float-pair source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def proposals():
 old=(p.out/'frozen'/p.SOURCE).read_text();source=p.proposal(old,p.BASE).replace('s32 func_15060BE0(struct127 *);','void func_15060BE0(struct127 *);').replace('/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_15060BE0.s. */\n','')
 nl='\r\n'if b'\r\n'in(p.out/'frozen'/p.SOURCE).read_bytes()else'\n';(p.out/'game-proposal.c').write_bytes(source.replace('\n',nl).encode());(p.out/'selected-source.c').write_bytes((p.out/'game-proposal.c').read_bytes())
 before=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();oldrows=list(csv.DictReader(io.StringIO(before.decode())));assert not any(r['function']==p.NAME for r in oldrows);fields=next(csv.reader(io.StringIO(before.decode())));nl='\r\n'if b'\r\n'in before else'\n';stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator=nl);writer.writerows(MANIFEST['guard_rows']);(p.out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode());(p.out/'selected-body.c').write_text(BASE);assert sha((p.out/'game-proposal.c').read_bytes())==MANIFEST['installed_hashes'][SOURCE];return {'game_83300':p.out/'game-proposal.c'}
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
 if sha(before)!=FROZEN['conker/build/conker.us.elf']or len(truth)!=372 or sha(truth)!=MANIFEST['truth_sha256']:raise ValueError('Changed guarded actor-anchor image inputs')
 expected=bytearray(before);at=elf_slot_offset(before,ENTRY,372);expected[at:at+372]=truth
 symbol=[v for v in symbol_rows(before)if v[1]==NAME];assert len(symbol)==1 and symbol[0][2][2]==12;struct.pack_into('>I',expected,symbol[0][0]+8,372)
 if bytes(expected)!=actual:raise ValueError('Actor-anchor image differs beyond body and symbol size')
 return dict(changed_bytes=sum(a!=b for a,b in zip(before,actual)),metadata_groups=[],strict_exclusions=0)
def main():
 frozen,installed=freeze();sources=proposals();targets,commands=actual_make(sources);path=targets['game_83300'];raw=Path(str(path)+'.compact')
 before,old_diagnostics=p.compile_owner(p.root,p.out,(p.out/'frozen'/p.SOURCE).read_text(),'independent-before');after,new_diagnostics=p.compile_owner(p.root,p.out,sources['game_83300'].read_text(),'independent-proposed')
 assert same_functions(before,after,(p.NAME,))==88 and same_functions(raw,after)==89
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(raw)
 assert sections(before)['.reginfo']==sections(after)['.reginfo']==sections(raw)['.reginfo']
 assert p.diagnostic_rows(old_diagnostics)==p.diagnostic_rows(new_diagnostics)
 (p.out/'selected.o').write_bytes(after.read_bytes())
 assert same_functions(p.out/'frozen/conker/build/src/game_83300.c.o',path,(p.NAME,))==88
 payload,refs=p.payload(raw);normal,nrefs=normalize(payload,refs);assert p.payload(path)==(normal,nrefs)
 ws=p.bound_blob(normal,nrefs,{'D_800C3E90':0x800C3E90,'D_800D1C90':0x800D1C90});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>93I',*ws)==truth
 oldguards=list(csv.DictReader(io.StringIO((p.out/'frozen/conker/retail_word_patches.us.csv').read_text())));newguards=list(csv.DictReader(io.StringIO((p.out/'proposed-guards.csv').read_text())));assert newguards[:len(oldguards)]==oldguards and newguards[len(oldguards):]==rows(payload,refs)
 elf=link(targets);original=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(original,actual,{p.NAME:truth})
 old,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in old if old[n]!=new[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 hashes={n:sha(f.read_bytes())for n,f in[(p.SOURCE,sources['game_83300']),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game_83300.c.o',path),('conker/build/conker.us.elf',elf)]};live_inputs(installed)
 assert hashes==MANIFEST['installed_hashes']and image==MANIFEST['image']and rows(payload,refs)==MANIFEST['guard_rows']
 report=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=93,frame=24,guards=27,non_target_neighbors=88,actual_Make_commands=len(commands),diagnostics=sum(p.diagnostic_rows(new_diagnostics).values()),functions=len(new),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer root differs from bound anchor workspace")
 return main()

if __name__=="__main__":prepare()
