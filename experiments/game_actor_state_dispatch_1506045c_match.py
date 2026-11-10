"""Actual owner Make recipes and strict three-body image prediction, privately."""
import csv,hashlib,io,json,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
import os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-actor-state-dispatch-1506045C-match'
NAME='func_1506045C';SOURCE='conker/src/game_83300.c'
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_actor_state_dispatch_1506045c_manifest.json').read_text())
FROZEN=MANIFEST['frozen']
SOURCE_REFS={int(k):[tuple(v)for v in vs]for k,vs in MANIFEST['raw_refs'].items()}
p=sys.modules[__name__];b=p
DECL='\nextern u8 D_800CBFA8[];\ns32 func_15080738(s32 command);\ns32 func_15065A5C(struct127 *, u32, u32, f32, s32, s32, s32, s32, s32);\nvoid func_150642AC(struct127 *, u32, f32, s32, s32);\n'
SOURCE_BODY="/* Dispatch the actor's selected state, preserving the recursive overlay. */\nvoid func_1506045C(struct127 *actor, u32 buttons, u32 flags, f32 height, s32 secondary) {\n    s32 stunned;\n    s32 command;\n    s32 expired;\n    s32 force;\n    s32 result = 0;\n    s32 saved;\n    u8 *state;\n\n    if (D_800C35EA == 1) {\n        return;\n    }\n    force = 0;\n    state = (u8 *)actor->unk31C;\n    stunned = 0;\n    expired = 0;\n    if ((*(u16 *)(state + 0x72) != 0) && (secondary == 0)) {\n        if (D_800BE9E4 < *(u16 *)(state + 0x72)) {\n            *(u16 *)(state + 0x72) -= (u32)D_800BE9E4;\n        } else {\n            expired = 1;\n            *(u16 *)(state + 0x72) = 0;\n        }\n    }\n    state = (u8 *)actor->unk31C;\n    command = state[0x75] & ~0x80;\n    if ((state[0x7C] != 0) && (command == 0)) {\n        command = state[0x7C];\n    }\n    if ((D_800BE9F0 != 0x29) && (D_800BE9F0 != 0x2E) &&\n        (state[0x78] == 0) && (*(u16 *)D_800CC284 & 0x20) &&\n        func_15080738(command)) {\n        command = 0x1A;\n    }\n    state = (u8 *)actor->unk31C;\n    if (state[0x78] == 0x1A) {\n        command = 0x1A;\n    }\n    if (state[0x78] == 0x2A) {\n        command = 0x2A;\n    }\n    if ((actor->unk13C != 0) || (actor->unk137 != 0)) {\n        if (secondary == 0) {\n            command = 0;\n        } else {\n            force = 1;\n        }\n    }\n    if ((actor->unk65 != 0) && (secondary == 0)) {\n        switch (D_800CBFA8[actor->unk65 * sizeof(struct127)]) {\n            case 0x23:\n            case 0x8A: command = 0x1B; break;\n            case 0xC: command = 8; break;\n            case 0x28: command = 0; break;\n            default: command = 0xE; break;\n        }\n    }\n    if (state[0x17] != 0) {\n        command = 0x3C;\n    }\n    if ((secondary == 0) && (state[0x78] != 0) && (command != (state[0x78] & ~0x80))) {\n        saved = state[0x75];\n        state[0x75] = state[0x78];\n        func_1506045C(actor, buttons, flags, height, 1);\n        ((u8 *)actor->unk31C)[0x75] = saved;\n        ((u8 *)actor->unk31C)[0x78] = 0;\n    }\n    if (actor->stunned != 0) {\n        stunned = 1;\n        flags = 0;\n        buttons = 0;\n    }\n    state = (u8 *)actor->unk31C;\n    if ((command != 0) && (state[0x4E] == 0)) {\n        result = func_15065A5C(actor, buttons, flags, height, secondary,\n            command, stunned, expired, force);\n    }\n    state = (u8 *)actor->unk31C;\n    if ((state[0x7B] != 0) || (flags & 0x4000)) {\n        func_150642AC(actor, flags, height, force, result);\n    }\n}"

def proposal(old,selected):
 return old.replace(body(old,NAME),selected).replace('s32 func_1506045C();','void func_1506045C(struct127 *, u32, u32, f32, s32);').replace('/* Generated placeholder declarations. */',DECL+'\n/* Generated placeholder declarations. */',1)
def payload(path):
 t,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return t[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
def normalize(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=MANIFEST['raw_sha256']or refs!=SOURCE_REFS:raise ValueError('Stale dispatcher words or bindings')
 ws=list(struct.unpack('>199I',raw));assert ws[131]==0x10A0001B;ws[131]=0x1100001B;return struct.pack('>199I',*ws),dict(refs)
def row():
 return dict(filename='game_83300',function=NAME,offset='0x20C',expected='0x10A0001B',replacement='0x1100001B',expected_relocations='-',replacement_relocations='-',note='Use the identical preserved overlay-byte register at the recursive gate',insert_after='',insert_after_relocations='',omit='false')
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_actor_audio_handle_15060778_audit import function_payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda data:hashlib.sha256(data).hexdigest()
MUTABLE=('conker/src/game_83300.c','conker/src/game/generated_90840.c','conker/retail_word_patches.us.csv','conker/build/src/game_83300.c.o','conker/build/src/game/generated_90840.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption dispatcher input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen dispatcher input: '+n)
 pair=('conker/src/game_83300.c','conker/src/game/generated_90840.c')
 live={n:sha((root/n).read_bytes())for n in pair}
 if live=={n:FROZEN[n]for n in pair}:installed=False
 elif live=={n:MANIFEST['installed_hashes'][n]for n in pair}:installed=True
 else:raise ValueError('Mixed or unknown dispatcher source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed dispatcher qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed dispatcher result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Dispatcher source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def proposals():
 old=(p.out/'frozen/conker/src/game_83300.c').read_text();candidate=p.proposal(old,SOURCE_BODY).replace('void func_150642AC(struct127 *, u32, f32, s32, s32);','s32 func_150642AC(struct127 *, u32, f32, s32, s32);')
 candidate=candidate.replace('/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_1506045C.s. */\n','').replace('extern u8 D_800CBFA8[];','/* Original base for the one-based actor-slot ID lookup. */\nextern u8 D_800CBFA8[];')
 callee=(out/'frozen/conker/src/game/generated_90840.c').read_text().replace('s32 func_150642AC() {','s32 func_150642AC(struct127 *actor, u32 flags, f32 height, s32 force, s32 result) {').replace('s32 func_15065A5C() {','s32 func_15065A5C(struct127 *actor, u32 buttons, u32 flags, f32 height, s32 secondary, s32 command, s32 stunned, s32 expired, s32 force) {')
 for name in ('func_150642AC','func_15065A5C'):callee=callee.replace('s32 '+name+'(', '/* Unrecovered body; preserve its typed actor-state dispatch arguments. */\ns32 '+name+'(',1)
 for target,text,original in [('game-proposal.c',candidate,'conker/src/game_83300.c'),('helper-proposal.c',callee,'conker/src/game/generated_90840.c')]:
  nl='\r\n'if b'\r\n'in(p.out/'frozen'/original).read_bytes()else'\n';(p.out/target).write_bytes(text.replace('\n',nl).encode())
 oldguards=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(oldguards.decode())));nl='\r\n'if b'\r\n'in oldguards else'\n';s=io.StringIO(newline='');writer=csv.DictWriter(s,fieldnames=fields,lineterminator=nl);writer.writerow(b.row());guards=oldguards+s.getvalue().encode();assert guards.startswith(oldguards)
 (p.out/'proposed-guards.csv').write_bytes(guards)
 (out/'selected-source.c').write_bytes((out/'game-proposal.c').read_bytes())
 for n,path in [(SOURCE,out/'game-proposal.c'),('conker/src/game/generated_90840.c',out/'helper-proposal.c'),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv')]:assert sha(path.read_bytes())==MANIFEST['installed_hashes'][n],n
 return {'game_83300':p.out/'game-proposal.c','game/generated_90840':p.out/'helper-proposal.c'}
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
 assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==2
 return targets,commands
def link(targets):
 conker=p.root/'conker';script=(p.out/'frozen/conker/build/conker.ld').read_text()
 for owner,f in targets.items():
  name='build/src/'+owner+'.c.o';assert script.count(name)==1;script=script.replace(name,f.relative_to(conker).as_posix())
 path=p.out/'qualified-image.ld';path.write_text(script);elf=p.out/'qualified-image.elf'
 argv=['mips-linux-gnu-ld','-T',path.relative_to(conker).as_posix(),*[a for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')for a in('-T',n)],'--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(conker).as_posix()]
 subprocess.run(argv,cwd=conker,capture_output=True,check=True);return elf
def strict_image(before,actual,payloads,groups=None):
 expected=bytearray(before);sizes={'func_1506045C':796,'func_150642AC':28,'func_15065A5C':28};old=symbol_rows(before);new=symbol_rows(actual);counts=Counter(r[1]for r in old);lookup={r[1]:r for r in old if counts[r[1]]==1}
 assert len(old)==len(new)and all(n in lookup for n in sizes)
 assert Counter((r[1],r[2][1],sizes.get(r[1],r[2][2]),*r[2][3:])for r in old)==Counter((r[1],*r[2][1:])for r in new),'Named ELF definition changed'
 for name,payload in payloads.items():
  r=lookup[name];assert r[2][2]==12 and len(payload)==sizes[name]
  at=elf_slot_offset(before,r[2][1],len(payload));expected[at:at+len(payload)]=payload;struct.pack_into('>I',expected,r[0]+8,len(payload))
 if groups is None:groups=MANIFEST['image']['metadata_groups']
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
  diffs=[i for i,(a,b)in enumerate(zip(expected,actual))if a!=b];raise ValueError(('Strict dispatcher image has unexplained differences',len(diffs),diffs[:20],len(expected),len(actual)))
 return dict(changed_bytes=sum(a!=b for a,b in zip(before,actual)),metadata_groups=groups,strict_exclusions=0)
def main():
 frozen,installed=freeze();sources=proposals();targets,commands=actual_make(sources)
 for owner,source in sources.items():
  raw=Path(str(targets[owner])+'.compact');assert raw.exists(),str(raw)
  before_source=(out/'frozen'/('conker/src/'+owner+'.c')).read_text()
  label='game'if owner=='game_83300'else'helper'
  before,old_diagnostics=compile_owner(root,out,before_source,'independent-before-'+label)
  after,new_diagnostics=compile_owner(root,out,source.read_text(),'independent-proposed-'+label)
  excluded=(NAME,)if label=='game'else('func_150642AC','func_15065A5C')
  assert same_functions(before,after,excluded)==(88 if label=='game'else 17)
  assert same_functions(raw,after)==len(parse_object(after)[1])
  assert normalized_pools(before)==normalized_pools(after)==normalized_pools(raw)
  assert sections(before)['.reginfo']==sections(after)['.reginfo']==sections(raw)['.reginfo']
  assert diagnostic_rows(old_diagnostics)==diagnostic_rows(new_diagnostics)
  if label=='game':(out/'selected.o').write_bytes(after.read_bytes())
  assert normalized_pools(out/'frozen'/('conker/build/src/'+owner+'.c.o'))==normalized_pools(targets[owner])
 assert same_functions(p.out/'frozen/conker/build/src/game_83300.c.o',targets['game_83300'],(p.NAME,))==88
 assert same_functions(p.out/'frozen/conker/build/src/game/generated_90840.c.o',targets['game/generated_90840'],('func_150642AC','func_15065A5C'))==17
 raw,refs=p.payload(Path(str(targets['game_83300'])+'.compact'));normal,nrefs=b.normalize(raw,refs);assert p.payload(targets['game_83300'])==(normal,nrefs)
 assert g_bound(normal,nrefs)==list(struct.unpack_from('>199I',(p.root/'conker/conker.us.bin').read_bytes(),0x8D90C))
 payloads={p.NAME:struct.pack('>199I',*g_bound(normal,nrefs))}
 for name in ('func_150642AC','func_15065A5C'):
  raw,refs=function_payload(parse_object(targets['game/generated_90840']),name);assert not refs and struct.unpack('>7I',raw)==(0xAFA40000,0xAFA50004,0xAFA60008,0xAFA7000C,0x00001025,0x03E00008,0)
  payloads[name]=raw
 elf=link(targets);before=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(before,actual,payloads)
 old,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in new if old[n]!=new[n]}==set(payloads)
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 installed_hashes={n:sha(path.read_bytes())for n,path in[(p.SOURCE,sources['game_83300']),('conker/src/game/generated_90840.c',sources['game/generated_90840']),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game_83300.c.o',targets['game_83300']),('conker/build/src/game/generated_90840.c.o',targets['game/generated_90840']),('conker/build/conker.us.elf',elf)]}
 assert installed_hashes==MANIFEST['installed_hashes'];assert image==MANIFEST['image'];live_inputs(installed)
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=199,frame=80,guards=1,non_target_Game_neighbors=88,unchanged_helper_neighbors=17,actual_Make_commands=len(commands),functions=len(new),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=installed_hashes)
 (p.out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
def g_bound(raw,refs):return p.bound_blob(raw,refs,{n:int(n.split('_')[1],16)for vs in refs.values()for _,n in vs})
parse_object=p.parse_object
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer root differs from the bound dispatcher workspace")
 return main()

if __name__=="__main__":prepare()
