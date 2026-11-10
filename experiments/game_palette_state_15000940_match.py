"""Owner-linked effect constructor source, direct owner and strict full-image qualification."""
import csv,hashlib,io,json,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
import os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-15000940-match'
NAME='func_15000940';OWNER='game_2DDF0';SOURCE='conker/src/game_2DDF0.c';ENTRY=0x15000940;ROM=0x2DDF0;SIZE=380;SLOT=384
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_palette_state_15000940_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\nextern u16 D_800D9E70[];\nextern u8 D_800D9E88[], D_800D9E98[], D_800D9EA8[];\nextern u8 D_800D9EB4[], D_800D9EB8[];\nextern u8 D_800D9EB7, D_800D9EC4;\nextern u8 D_800A2CE8[], D_800A2CEC[], D_800A2D04[];\n'
BASE='/* Initialize four palette-state rows from the selected RGB presets. */\nvoid func_15000940(s32 unused) {\n    u8 *selectors;\n    u8 *first;\n    u8 *second;\n    u8 *third;\n    u16 *zeroHalf;\n    u8 *firstOut;\n    u8 *secondOut;\n    u8 *thirdOut;\n    u8 *zeroByte;\n    u8 *common;\n    u16 *halfCursor;\n    u8 *firstCursor;\n    u8 *firstSource;\n    u8 *secondCursor;\n    u8 *secondSource;\n    u8 *thirdSource;\n    u8 *thirdCursor;\n    u8 *zeroCursor;\n    u8 thirdValue;\n    u8 firstValue;\n    u8 secondValue;\n\n    selectors = D_800A2CD0[D_800B0DF0->unk29];\n    first = &D_800A2CE8[selectors[0] * 3];\n    second = &D_800A2CEC[selectors[1] * 3];\n    third = &D_800A2D04[selectors[2] * 3];\n    zeroHalf = D_800D9E70;\n    firstOut = D_800D9E88;\n    secondOut = D_800D9E98;\n    thirdOut = D_800D9EA8;\n    zeroByte = D_800D9EB8;\n\n    do {\n        common = D_800D9EB4;\n        halfCursor = zeroHalf;\n        firstCursor = firstOut;\n        firstSource = first;\n        secondCursor = secondOut;\n        secondSource = second;\n        thirdSource = third;\n        thirdCursor = thirdOut;\n        zeroCursor = zeroByte;\n\n        do {\n            thirdValue = *thirdSource++;\n            firstValue = *firstSource++;\n            secondValue = *secondSource++;\n\n            *halfCursor++ = 0;\n            *zeroCursor++ = 0;\n            *common++ = thirdValue;\n            *thirdCursor++ = thirdValue;\n            *firstCursor++ = firstValue;\n            *secondCursor++ = secondValue;\n        } while (common != &D_800D9EB7);\n        zeroByte += 3;\n        zeroHalf += 3;\n        firstOut += 3;\n        secondOut += 3;\n        thirdOut += 3;\n    } while (zeroByte != &D_800D9EC4);\n}'
def proposal(old,selected):
 return old.replace('#include "variables.h"','#include "variables.h"\n'+DECLS).replace('s32 func_15000940();','void func_15000940(s32);').replace('// loops...\n','').replace('/* Non-matching C placeholders for asm/nonmatchings/game_2DDF0/func_15000940.s. */\n','').replace(body(old,NAME),selected)

def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}


"""Closed register-role and pointer-update scheduling normalization.

Every input instruction is retained exactly once. Only GPR fields, two branch
displacements, and five equivalent post-increment memory offsets may change.
The relocated end-address pairs move to the invariant setup. No retail words
are stored or loaded here; the independent original is a test oracle only.
"""
import hashlib,json,struct

PIN=MANIFEST['raw_pin']
ORDER=list(range(39))+[77,62,39,40,65,79,45,44,43,42,41]+list(range(46,56))+[56,57,58,64,70,73,68,74,69,67,72,71,59,60,61,63,66,75,76,78,80,81,82,83,84]+list(range(85,95))
assert sorted(ORDER)==list(range(95))
# Field overrides belong to the recovered roles at each original raw position.
# Values are architectural GPR numbers, never replacement instructions.
FIELDS={
12:{16:24},13:{21:24,16:24},14:{16:10},15:{16:3},16:{16:4},17:{16:10,11:15},18:{21:15,16:10,11:15},19:{21:15,16:24,11:12},20:{21:12,16:25},21:{21:12,16:24},22:{16:15},23:{16:25,11:14},24:{21:15,16:15},25:{21:14,16:25,11:14},26:{21:14,16:15,11:7},27:{16:24,11:25},28:{21:12,16:15},29:{16:14},30:{21:25,16:24,11:25},31:{21:14,16:14},32:{21:25,16:14,11:8},33:{16:25},34:{16:15,11:24},35:{21:25,16:25},36:{16:5},37:{16:6},38:{16:2},39:{21:24,16:15,11:24},40:{21:24,16:25,11:9},41:{21:3,16:3},42:{21:4,16:4},43:{21:5,16:5},44:{21:6,16:6},45:{21:2,16:2},46:{16:18},47:{21:18,16:18},48:{21:3},49:{21:4},50:{21:7},51:{21:5},52:{21:8},53:{21:9,11:19},54:{21:6,11:20},55:{21:2,11:21},56:{21:19,16:25},57:{16:14},58:{16:15},60:{21:21},61:{21:18,16:25},62:{16:22},63:{21:20,16:25},64:{21:18,16:18},65:{21:22,16:22},66:{16:14},67:{21:19,16:19},71:{21:21,16:21},72:{21:20,16:20},75:{21:18,16:22},76:{16:15},77:{16:23},78:{21:2,16:2},79:{21:23,16:23},80:{21:3,16:3},81:{21:4,16:4},82:{21:5,16:5},83:{21:2,16:23},84:{21:6,16:6}}
OFFSETS={59:-2,60:-1,61:-1,63:-1,66:-1}

def normalize(raw,refs):
 wanted={int(k):[tuple(x)for x in v]for k,v in PIN['refs'].items()}
 if len(raw)!=380 or hashlib.sha256(raw).hexdigest()!=PIN['sha256']or refs!=wanted:raise ValueError('Palette initializer raw words or bindings changed')
 ws=list(struct.unpack('>95I',raw));mapped=list(ws)
 for i,fields in FIELDS.items():
  for shift,reg in fields.items():mapped[i]=(mapped[i]&~(31<<shift))|(reg<<shift)
 for i,off in OFFSETS.items():
  assert ws[i]>>26 in(40,41)and ws[i]&65535==0
  mapped[i]=(mapped[i]&~65535)|(off&65535)
 positions={old:new for new,old in enumerate(ORDER)}
 for i,target in((75,56),(83,46)):
  assert ws[i]>>26==5 and i+1+((ws[i]&65535)^32768)-32768==target
  mapped[i]=(mapped[i]&~65535)|((positions[target]-positions[i]-1)&65535)
 normal=[mapped[i]for i in ORDER];newrefs={4*positions[at//4]:v for at,v in refs.items()}
 assert all((mapped[i]>>26,mapped[i]&63 if mapped[i]>>26==0 else None)==(ws[i]>>26,ws[i]&63 if ws[i]>>26==0 else None)for i in range(95))
 return struct.pack('>95I',*normal),newrefs

def rows(raw,refs):
 normal,rs=normalize(raw,refs);result=[]
 for i,(a,b)in enumerate(zip(struct.unpack('>95I',raw),struct.unpack('>95I',normal))):
  at=4*i
  if a==b and refs.get(at,[])==rs.get(at,[]):continue
  uses=lambda es:';'.join(k+':'+n for k,n in es)or'-'
  result.append(dict(filename='game_2DDF0',function='func_15000940',offset='0x%X'%at,expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=uses(refs.get(at,[])),replacement_relocations=uses(rs.get(at,[])),note='Normalize closed palette cursor register roles, invariant end addresses and equivalent pointer-update schedule',insert_after='',insert_after_relocations='',omit='false'))
 return result


from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
parse_object=p.parse_object
sha=lambda data:hashlib.sha256(data).hexdigest()
from unittest.mock import patch
base_compile_owner=p.compile_owner
def compile_selected(root,out,source,label):
 original=subprocess.run
 def run(argv,*a,**kw):
  if isinstance(argv,list)and str(argv[0]).endswith('/ido/ido5.3_recomp/cc'):
   argv=list(argv);at=argv.index('-mips2');argv[at:at]=['-Wo,-loopunroll,0','-Wo,-no_const_in_reg']
  return original(argv,*a,**kw)
 with patch('subprocess.run',side_effect=run):return base_compile_owner(root,out,source,label)
MUTABLE=('conker/src/game_2DDF0.c','conker/build/src/game_2DDF0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin','conker/retail_word_patches.us.csv','conker/Makefile')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption palette-state input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen palette-state input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown palette-state source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed palette-state qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed palette-state result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Palette-state source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def proposals():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');source=p.proposal(old,p.BASE)
 source=source.replace('/* Generated placeholder declarations. */\n','').replace('/* End generated placeholder declarations. */\n','')
 nl='\r\n'if b'\r\n'in(p.out/'frozen'/p.SOURCE).read_bytes()else'\n';(p.out/'game-proposal.c').write_bytes(source.replace('\n',nl).encode());(p.out/'selected-source.c').write_bytes((p.out/'game-proposal.c').read_bytes())
 (p.out/'selected-body.c').write_text(p.BASE);recipe,_=compile_selected(p.root,p.out,source,'recipe-input');before=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n');writer.writerows(rows(*p.payload(recipe)));(p.out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())
 make=(p.out/'frozen/conker/Makefile').read_bytes();newline=b'\r\n'if b'\r\n'in make else b'\n';addition='\n# Palette-state initializer: preserve both loops and direct address constants.\nifeq ($(VERSION),us)\n$(BUILD_DIR)/$(SRC_DIR)/game_2DDF0.c.o: CFLAGS += -Wo,-loopunroll,0 -Wo,-no_const_in_reg\nendif\n';(p.out/'make-proposal.mk').write_bytes(make+addition.replace('\n',newline.decode()).encode());return {p.OWNER:p.out/'game-proposal.c'}

def actual_make(sources):
 conker=p.root/'conker';shadow=p.out/'make-shadow';targets={owner:shadow/('src/'+owner+'.c.o')for owner in sources}
 for f in targets.values():f.parent.mkdir(parents=True,exist_ok=True)
 args=['make','-f',(p.out/'make-proposal.mk').relative_to(conker).as_posix(),'-n','-B','-o','Makefile','-o','retail_word_patches.us.csv','BUILD_DIR='+shadow.relative_to(conker).as_posix(),*[f.relative_to(conker).as_posix()for f in targets.values()]]
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
 expected=bytearray(before);sizes={'func_15000940':380};old=symbol_rows(before);new=symbol_rows(actual);counts=Counter(r[1]for r in old);lookup={r[1]:r for r in old if counts[r[1]]==1}
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
 frozen,installed=freeze();sources=proposals();targets,commands=actual_make(sources);path=targets[p.OWNER];raw=Path(str(path)+'.compact')
 before,old_diagnostics=compile_selected(p.root,p.out,(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8'),'independent-before');after,new_diagnostics=compile_selected(p.root,p.out,sources[p.OWNER].read_text(encoding='utf-8'),'independent-proposed')
 assert same_functions(before,after,(p.NAME,))==0 and same_functions(raw,after)==1
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(raw)
 assert sections(after)['.reginfo']==sections(raw)['.reginfo']
 (p.out/'reginfo.json').write_text(json.dumps({label:sections(obj)['.reginfo'][1].hex()for label,obj in [('before',before),('after',after),('actual-Make',raw)]},indent=2)+'\n')
 assert p.diagnostic_rows(old_diagnostics)==p.diagnostic_rows(new_diagnostics)
 (p.out/'selected.o').write_bytes(after.read_bytes())
 payload,refs=p.payload(raw);normal,normal_refs=normalize(payload,refs);assert p.payload(path)==(normal,normal_refs)
 assert len(parse_object(path)[0])==384 and parse_object(path)[0][-4:]==b'\0'*4
 ws=p.bound_blob(normal,normal_refs,{n:int(n[2:],16)for es in normal_refs.values()for _,n in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>95I',*ws)==truth
 oldguards=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();newguards=(p.out/'proposed-guards.csv').read_bytes();assert newguards.startswith(oldguards);assert list(csv.DictReader(io.StringIO(newguards.decode())))[-73:]==rows(payload,refs)
 elf=link(targets);original=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(original,actual,{p.NAME:truth})
 old,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in old if old[n]!=new[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 hashes={n:sha(f.read_bytes())for n,f in[(p.SOURCE,sources[p.OWNER]),('conker/Makefile',p.out/'make-proposal.mk'),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game_2DDF0.c.o',path),('conker/build/conker.us.elf',elf)]};live_inputs(installed)
 assert hashes==MANIFEST['installed_hashes']and image==MANIFEST['image']
 report=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=95,slot_words=96,frame=40,guards=73,non_target_neighbors=0,actual_Make_commands=len(commands),diagnostics=sum(p.diagnostic_rows(new_diagnostics).values()),functions=len(new),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from bound palette workspace")
 return main()

if __name__=="__main__":prepare()
