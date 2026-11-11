"""Owner-linked effect constructor source, direct owner and strict full-image qualification."""
import csv,hashlib,io,json,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
import os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-1501FE68-match'
NAME='func_1501FE68';OWNER='game/generated_49D30';SOURCE='conker/src/game/generated_49D30.c';ENTRY=0x1501FE68;ROM=0x4D318;SIZE=384
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_sequence_direction_1501fe68_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\nextern f32 D_800969D8, D_800969DC;\nf32 func_150484A0(f32, f32);\ns32 func_1501FFE8(f32 (*)[3], u8 *, s32, s32);\ntypedef struct {\n    u8 pad00[6];\n    u16 flag;\n} SequenceFrameKey49D30;\n'
F72='s32 func_1501F72C(s32 index, f32 time, f32 (*points)[3], s32 group, s32 *frame) {\n    return 0;\n}'
FFE='s32 func_1501FFE8(f32 (*matrix)[3], u8 *keys, s32 frame, s32 count) {\n    return 0;\n}'
BASE='/* Write the sequence direction at a clamped percentage, when two keys exist. */\nvoid func_1501FE68(s32 index, f32 percentage, f32 *output, s32 group) {\n    s32 frame;\n    f32 points[2][3];\n    f32 matrix[4][3];\n    f32 time;\n    f32 x;\n    f32 z;\n\n    if (D_800C35C8[group][index] >= 2) {\n        if (percentage > 100.0f) {\n            percentage = 100.0f;\n        }\n        if (percentage < 0.0f) {\n            percentage = 0.0f;\n        }\n        time = D_800C3A50[group][index].duration * percentage * D_800969D8;\n        func_1501F72C(index, time, points, group, &frame);\n        if (((SequenceFrameKey49D30 *)D_800C3868[group][index])[frame].flag == 0) {\n            x = points[0][0] - points[1][0];\n            z = points[0][2] - points[1][2];\n        } else {\n            func_1501FFE8(matrix, D_800C3868[group][index], frame, D_800C35C8[group][index]);\n            x = matrix[2][0] - matrix[1][0];\n            z = matrix[2][2] - matrix[1][2];\n        }\n        *output = func_150484A0(x, z) * D_800969DC;\n    }\n}'
def variant(old,active):
 s=old.replace('#include <PR/sched.h>','#include <PR/sched.h>\n'+DECLS)
 assert s.count('    u8 pad00[4];\n    u32 *items;')==1
 s=s.replace('    u8 pad00[4];\n    u32 *items;','    f32 duration;\n    u32 *items;')
 s=s.replace(body(s,'func_1501F72C'),F72).replace(body(s,'func_1501FFE8'),FFE)
 if active:s=s.replace(body(s,NAME),BASE)
 return s

def payload(path,name):
 text,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}


"""Pin and normalize eight private frame-index/matrix stack offsets."""
import hashlib,json,struct
PIN=MANIFEST['raw_pin']
# The frame word moves from SP+0x84 to +0x60; the 48-byte matrix moves from
# SP+0x3C to +0x30. The 24-byte points array and all saved locations stay fixed.
ROLES={37:(0x84,0x60),57:(0x84,0x60),74:(0x3C,0x30),75:(0x84,0x60),79:(0x54,0x48),80:(0x48,0x3C),81:(0x5C,0x50),82:(0x50,0x44)}
def normalize(raw,refs):
 expected={int(k):[tuple(x)for x in v]for k,v in PIN['refs'].items()}
 if len(raw)!=384 or hashlib.sha256(raw).hexdigest()!=PIN['sha256']or refs!=expected:raise ValueError('Sequence-direction raw body or bindings changed')
 ws=list(struct.unpack('>96I',raw));assert ws[0]==0x27BDFF78 and ws[93:]==[0x27BD0088,0x03E00008,0]
 for index,(old,new)in ROLES.items():
  w=ws[index];assert w&65535==old and (w>>21)&31==29 and w>>26 in(9,35,49)
  ws[index]=(w&0xFFFF0000)|new
 assert (0x30,0x60,0x64,0x6C,0x84,0x88)==(48,96,100,108,132,136)
 return struct.pack('>96I',*ws),dict(refs)
def rows(raw,refs):
 normal,bindings=normalize(raw,refs);result=[]
 for i,(a,b)in enumerate(zip(struct.unpack('>96I',raw),struct.unpack('>96I',normal))):
  if a==b:continue
  assert not refs.get(4*i)and not bindings.get(4*i)
  result.append(dict(filename='generated_49D30',function=p.NAME,offset='0x%X'%(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Preserve the sequence frame-index and matrix local stack positions',insert_after='',insert_after_relocations='',omit='false'))
 assert len(result)==8;return result

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
parse_object=p.parse_object
sha=lambda data:hashlib.sha256(data).hexdigest()
import inspect
namespace=dict(p.compile_owner.__globals__);exec(inspect.getsource(p.compile_owner).replace('*flags,','*[f for f in flags if not f.startswith("-Wo,")],',1),namespace)
def compile_selected(root,out,source,label):return namespace['compile_owner'](root,out,source,label,('-O2','-g3','-Wo,-loopunroll,0'))
MUTABLE=('conker/src/game/generated_49D30.c','conker/build/src/game/generated_49D30.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin','conker/retail_word_patches.us.csv')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption sequence-direction input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen sequence-direction input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown sequence-direction source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed sequence-direction qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed sequence-direction result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Sequence-direction source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def proposals():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');source=p.variant(old,True)
 nl='\r\n'if b'\r\n'in(p.out/'frozen'/p.SOURCE).read_bytes()else'\n';(p.out/'game-proposal.c').write_bytes(source.replace('\n',nl).encode());(p.out/'selected-source.c').write_bytes((p.out/'game-proposal.c').read_bytes())
 (p.out/'selected-body.c').write_text(p.BASE);recipe,_=compile_selected(p.root,p.out,source,'recipe-input');before=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n');writer.writerows(rows(*p.payload(recipe,p.NAME)));(p.out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode());return {p.OWNER:p.out/'game-proposal.c'}

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
 expected=bytearray(before);sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28};old=symbol_rows(before);new=symbol_rows(actual);counts=Counter(r[1]for r in old);lookup={r[1]:r for r in old if counts[r[1]]==1}
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
 before,old_diagnostics=compile_selected(p.root,p.out,(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8'),'independent-before');after,new_diagnostics=compile_selected(p.root,p.out,sources[p.OWNER].read_text(encoding='utf-8'),'independent-proposed');changed=('func_1501F72C',p.NAME,'func_1501FFE8')
 assert same_functions(before,after,changed)==54 and same_functions(raw,after)==57
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(raw)
 assert sections(after)['.reginfo']==sections(raw)['.reginfo']
 (p.out/'reginfo.json').write_text(json.dumps({label:sections(obj)['.reginfo'][1].hex()for label,obj in [('before',before),('after',after),('actual-Make',raw)]},indent=2)+'\n')
 assert p.diagnostic_rows(old_diagnostics)==p.diagnostic_rows(new_diagnostics)
 (p.out/'selected.o').write_bytes(after.read_bytes());assert same_functions(p.out/'frozen/conker/build/src/game/generated_49D30.c.o',path,changed)==54
 payload,refs=p.payload(raw,p.NAME);normal,nrefs=normalize(payload,refs);assert p.payload(path,p.NAME)==(normal,nrefs)
 ws=p.bound_blob(normal,nrefs,{n:int(n.split('_')[1],16)for es in nrefs.values()for _,n in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>96I',*ws)==truth
 payloads={p.NAME:truth}
 for name in changed:
  if name==p.NAME:continue
  new,refs=p.payload(path,name);assert len(p.payload(before,name)[0])==12 and len(new)==28 and not refs and p.payload(raw,name)==(new,refs);payloads[name]=new
 oldguards=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();newguards=(p.out/'proposed-guards.csv').read_bytes();assert newguards.startswith(oldguards);assert list(csv.DictReader(io.StringIO(newguards.decode())))[-8:]==rows(payload,refs if False else p.payload(raw,p.NAME)[1])
 elf=link(targets);original=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(original,actual,payloads)
 old,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in old if old[n]!=new[n]}==set(changed)
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 hashes={n:sha(f.read_bytes())for n,f in[(p.SOURCE,sources[p.OWNER]),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game/generated_49D30.c.o',path),('conker/build/conker.us.elf',elf)]};live_inputs(installed)
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 report=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=96,frame=136,guards=8,non_target_neighbors=54,typed_placeholder_helpers=2,actual_Make_commands=len(commands),diagnostics=sum(p.diagnostic_rows(new_diagnostics).values()),functions=len(new),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from bound sequence workspace")
 return main()

if __name__=="__main__":prepare()
