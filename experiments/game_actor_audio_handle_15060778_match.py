"""Private owner/guard/Make/image qualification; never installs production files."""
import csv,hashlib,io,json,shlex,struct,subprocess,sys
from pathlib import Path
import os
ROOT=Path(os.environ.get("CBFD_CONSUMER_ROOT",Path(__file__).resolve().parents[2])).resolve()
root=ROOT;base=root/'conker/build/game-actor-audio-15060778-match';out=base/'adoption';conker=root/'conker'
MANIFEST=json.loads(Path(__file__).with_name('game_actor_audio_handle_15060778_manifest.json').read_text())
FROZEN=MANIFEST['frozen']
from tools.experiments import game_actor_audio_handle_15060778_audit as audit
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_audio_handle_15060778_audit import function_payload,changes
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
sha=lambda b:hashlib.sha256(b).hexdigest()
TARGETS={'func_15060778':('game_83300',174,0x8DC28,0x15060778),'func_10010BE8':('init_EB00',164,0x10BE8,0x10010BE8),'func_10010FFC':('init_EB00',115,0x10FFC,0x10010FFC)}


def source_proposal():
 old={n:(out/'frozen'/n).read_bytes()for n in(audit.GAME,audit.INIT,audit.HEADER)}
 game,init,header=audit.proposal(*[old[n].decode().replace('\r\n','\n')for n in(audit.GAME,audit.INIT,audit.HEADER)])
 game=game.replace('                    func_1000F85C(handle, 8, arg2 + effect * 50);','                    /* Command 8 consumes the full sum, unlike the spatial helpers. */\n                    func_1000F85C(handle, 8, arg2 + effect * 50);')
 init=init.replace('u16 func_10010BE8(u16 arg0,','/* Reuse or allocate one of the sixteen generation-tagged sound slots. */\nu16 func_10010BE8(u16 arg0,',1)
 new={n:s.replace('\n','\r\n'if b'\r\n'in old[n]else'\n').encode()for n,s in zip((audit.GAME,audit.INIT,audit.HEADER),(game,init,header))}
 live={n:(root/n).read_bytes()for n in old}
 if live==old:installed=False
 elif live==new:installed=True
 else:raise ValueError('Mixed or unrecognized actor audio source/header state')
 return installed,new

def prepare_inputs():
 out.mkdir(parents=True,exist_ok=True)
 for name,wanted in FROZEN.items():
  p=out/'frozen'/name
  if not p.exists():
   data=(root/name).read_bytes()
   if sha(data)!=wanted:raise ValueError('Retained pre-adoption baseline required: '+name)
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  if sha(p.read_bytes())!=wanted:raise ValueError('Frozen actor audio input changed: '+name)
 (out/'freeze-inputs.json').write_text(json.dumps(FROZEN,indent=2)+'\n')
 installed,new=source_proposal()
 folder=base/'public-audit';folder.mkdir(parents=True,exist_ok=True)
 (folder/'original-functions.h').write_bytes((out/'frozen'/audit.HEADER).read_bytes())
 for directory in(out,folder):(directory/'proposed-functions.h').write_bytes(new[audit.HEADER])
 for name,label in((audit.GAME,'game'),(audit.INIT,'init')):
  original=(out/'frozen'/name).read_text().replace('#include "functions.h"','#include "original-functions.h"')
  obj,_=compile_owner(root,folder,original,label+'-before')
  proposal=new[name].decode().replace('\r\n','\n').replace('#include "functions.h"','#include "proposed-functions.h"')
  (out/(label+'-proposal.c')).write_text(proposal);(folder/(label+'-proposal.c')).write_text(proposal)
 return installed

def live_inputs(installed):
 _,new=source_proposal();metadata=[];outputs={}
 desired={n:sha(b)for n,b in new.items()}
 desired.update({'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256'],'conker/build/src/game_83300.c.o':MANIFEST['Game_object_sha256'],'conker/build/conker.us.elf':MANIFEST['ELF_sha256']})
 for n,h in FROZEN.items():
  now=(root/n).read_bytes();actual=sha(now)
  if actual==h:continue
  if installed and n in desired:
   if actual!=desired[n]:raise ValueError('Installed actor audio file changed: '+n)
  elif installed and n=='conker/build/conker.us.bin':outputs[n]=actual
  elif installed and n.endswith('.o'):
   before=sections(out/'frozen'/n);after=sections(root/n)
   if before.keys()!=after.keys()or any(before[k]!=after[k]for k in before if k!='.mdebug'):raise ValueError('Dependent object changed outside debug metadata: '+n)
   metadata.append(dict(path=n,before=h,after=actual,only_section='.mdebug'))
  else:raise ValueError('Unexpected actor audio qualification input change: '+n)
 if installed:
  for n,h in desired.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed actor audio result incomplete: '+n)
 return dict(metadata_only_objects=metadata,production_output_sha256=outputs)

def prepare(consumer=ROOT):
 global root,base,out,conker
 root=Path(consumer).resolve();base=root/'conker/build/game-actor-audio-15060778-match';out=base/'adoption';conker=root/'conker'
 installed=prepare_inputs();report=main(installed)
 for owner,label in(('game_83300','game'),('init_EB00','init')):
  source=out/('make-shadow/src/'+owner+'.c.o.compact');destination=base/('public-audit/'+label+'-proposal.o');destination.write_bytes(source.read_bytes())
 return report


def run(args,cwd=conker):
 p=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stdout+p.stderr)
 return p

def assemble(text,label):
 p=out/(label+'.s');p.write_text(text);q=p.with_suffix('.o');run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(q),str(p)]);return q

def emit(raw,refs,name,label):
 s='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,symbol in refs.get(i*4,[]):s+='.reloc ., '+kind+', '+symbol+'\n'
  s+='.word 0x%08X\n'%w
 return assemble(s+'.size '+name+',.-'+name+'\n',label)

def make_plan():
 shadow=out/'make-shadow';(shadow/'src').mkdir(parents=True,exist_ok=True)
 (shadow/'src/proposed-functions.h').write_bytes((out/'proposed-functions.h').read_bytes())
 targets={owner:shadow/('src/'+owner+'.c.o')for owner in('game_83300','init_EB00')}
 args=['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),*[p.relative_to(conker).as_posix()for p in targets.values()]]
 p=run(args);(out/'actual-Make-plan.txt').write_text(p.stdout+p.stderr);commands=[]
 replacements={'src/game_83300.c':(out/'game-proposal.c').relative_to(conker).as_posix(),'src/init_EB00.c':(out/'init-proposal.c').relative_to(conker).as_posix(),'retail_word_patches.us.csv':(out/'proposed-guards.csv').relative_to(conker).as_posix()}
 for line in p.stdout.replace('\\\n','').splitlines():
  a=shlex.split(line)
  if not a or a[0]=='rm':continue
  assert a[0]in('python3','../ido/ido5.3_recomp/cc','mips-linux-gnu-as'),a
  a=[replacements.get(v,v)for v in a];commands.append(a)
 return targets,commands,p.stderr

def command(args):
 a=list(args);redirect=None
 if '>'in a:
  assert a[-2]=='>'and a.count('>')==1;redirect=(conker/a[-1]).resolve();redirect.relative_to(out.resolve());a=a[:-2]
 p=run(a)
 if redirect is not None:redirect.write_text(p.stdout)
 return p

def row(owner,name,i,word,refs,newword,newrefs):
 spec=lambda rs:';'.join('%s:%s'%r for r in rs)or'-'
 return dict(filename=owner,function=name,offset='0x%03X'%(i*4),expected='0x%08X'%word,replacement='0x%08X'%newword,expected_relocations=spec(refs),replacement_relocations=spec(newrefs),note='Normalize actor audio private spill homes'if owner=='game_83300'else'Preserve accepted Init sound body after narrow-handle API recovery',insert_after='',insert_after_relocations='',omit='false')

def guard_proposal(compacts):
 old=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();records=list(csv.DictReader(io.StringIO(old.decode())));fields=list(records[0]);newline='\r\n'if b'\r\n'in old else'\n';groups={};derivation={}
 for name,(owner,n,rom,entry)in TARGETS.items():
  raw,refs=function_payload(parse_object(compacts[owner]),name);ws=list(struct.unpack('>%dI'%n,raw));assert len(raw)==n*4
  if owner=='game_83300':
   normal=list(ws);nrefs=dict(refs);indices=[38,39,43,44,93,95,96,98];homes={0x40:0x44,0x48:0x54}
   for i in indices:assert ws[i]>>26 in(35,43)and ws[i]>>21&31==29;normal[i]=(ws[i]&0xFFFF0000)|homes[ws[i]&65535]
  else:
   # Compose the checked source refinement with the previously accepted output.
   # No words are read from the ROM to construct the normalization.
   reference=out/('frozen/conker/build/src/'+owner+'.c.o');oldraw,nrefs=function_payload(parse_object(reference),name);normal=list(struct.unpack('>%dI'%n,oldraw))
  rows=[row(owner,name,i,w,refs.get(4*i,[]),normal[i],nrefs.get(4*i,[]))for i,w in enumerate(ws)if w!=normal[i]or refs.get(4*i,[])!=nrefs.get(4*i,[])]
  groups[name]=rows;derivation[name]=dict(raw_sha256=sha(raw),raw_words=n,normal_sha256=sha(struct.pack('>%dI'%n,*normal)),source_refs=refs,normal_refs=nrefs,rows=rows,old_guard_count=sum(r['function']==name and r['filename']==owner for r in records))
 seen=set();result=[]
 for line in old.decode().splitlines(keepends=True):
  cols=next(csv.reader([line]));name=cols[1]
  if name in groups and cols[0]=='init_EB00':
   if name not in seen:
    s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields,lineterminator=newline);w.writerows(groups[name]);result.append(s.getvalue());seen.add(name)
  else:result.append(line)
 assert seen=={'func_10010BE8','func_10010FFC'}
 s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields,lineterminator=newline);w.writerows(groups['func_15060778']);result.append(s.getvalue());proposal=''.join(result).encode();(out/'proposed-guards.csv').write_bytes(proposal)
 untouched=lambda rs:[r for r in rs if r['function']not in TARGETS]
 assert untouched(records)==untouched(list(csv.DictReader(io.StringIO(proposal.decode()))))
 assert json.loads(json.dumps(derivation))==MANIFEST['normalization'],'Audio normalization derivation changed'
 (out/'derivation.json').write_text(json.dumps(derivation,indent=2)+'\n');return derivation

def independent(name,compact,rows):
 owner,n,rom,entry=TARGETS[name];raw,refs=function_payload(parse_object(compact),name);obj=emit(raw,refs,name,name+'-raw');guards=out/(name+'-guards.csv')
 with guards.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 layout_lines=(out/'frozen/conker/retail_layout.us.txt').read_text().splitlines();selected=[l for l in layout_lines[1:]if l.split(',')[1:3]==[owner,name]];assert len(selected)==1;layout=out/(name+'-layout.csv');layout.write_text(layout_lines[0]+'\n'+selected[0]+'\n')
 asm=root/('conker/asm/nonmatchings/'+owner+'/'+name+'.s')
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,owner,word_patches_path=guards),name+'-generic')
 b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename=owner,word_patches_path=guards),name+'-generated')
 assert function_payload(parse_object(a),name)==function_payload(parse_object(b),name)
 return a

def link(targets,label):
 script=(out/'frozen/conker/build/conker.ld').read_text()
 for owner,path in targets.items():
  name='build/src/'+owner+'.c.o';assert script.count(name)==1;script=script.replace(name,path.relative_to(conker).as_posix())
 ld=out/(label+'.ld');ld.write_text(script);elf=out/(label+'.elf')
 run(['mips-linux-gnu-ld','-T',ld.relative_to(conker).as_posix(),*[v for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')for v in('-T',n)],'--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(conker).as_posix()]);return elf

def strict_image(before,actual,truth):
 if len(truth)!=696 or sha(before)!=FROZEN['conker/build/conker.us.elf']or sha(truth)!=MANIFEST['truth_game_sha256']:raise ValueError('Frozen audio image inputs changed')
 expected=bytearray(before);at=elf_slot_offset(before,0x15060778,696);expected[at:at+696]=truth
 syms=[r for r in symbol_rows(before)if r[1]=='func_15060778'];assert len(syms)==1 and syms[0][2][2]==684;struct.pack_into('>I',expected,syms[0][0]+8,696)
 if bytes(expected)!=actual:raise ValueError('Strict audio whole-image prediction differs')
 return sum(a!=b for a,b in zip(before,actual))

def main(installed=False):
 frozen=json.loads((out/'freeze-inputs.json').read_text())
 input_audit=live_inputs(installed)
 targets,commands,warnings=make_plan();compacts={owner:Path(str(p)+'.compact')for owner,p in targets.items()};logs=[]
 for a in commands:
  if a[0]=='mips-linux-gnu-as'or a[0]=='python3'and 'pad_c_object.py'in a[1]:continue
  p=command(a);logs.append(dict(args=a,stdout=p.stdout,stderr=p.stderr))
 derivation=guard_proposal(compacts)
 for a in commands:
  if a[0]=='mips-linux-gnu-as'or a[0]=='python3'and 'pad_c_object.py'in a[1]:p=command(a);assert not p.stdout and not p.stderr
 assert len(commands)==9 and len([a for a in commands if a[0]=='../ido/ido5.3_recomp/cc'])==3
 for log in logs:
  if log['args'][0]=='../ido/ido5.3_recomp/cc':
   owner='game'if 'game_83300'in log['args'][log['args'].index('-o')+1]else'init';wanted=diagnostic_rows((base/('public-audit/'+owner+'-before-diagnostics.txt')).read_text());assert diagnostic_rows(log['stderr'])==wanted and '-O2'in log['args']and'-g3'in log['args']
 (out/'actual-Make-commands.json').write_text(json.dumps(logs,indent=2)+'\n')
 for name,(owner,n,rom,entry)in TARGETS.items():
  p=independent(name,compacts[owner],derivation[name]['rows']);assert function_payload(parse_object(p),name)==function_payload(parse_object(targets[owner]),name)
 assert targets['init_EB00'].read_bytes()==(out/'frozen/conker/build/src/init_EB00.c.o').read_bytes(),'Init padded owner changed'
 assert same_functions(out/'frozen/conker/build/src/game_83300.c.o',targets['game_83300'],('func_15060778',))==88
 assert same_functions(base/'public-audit/game-before.o',compacts['game_83300'],('func_15060778',))==88
 assert changes(parse_object(base/'public-audit/init-before.o'),parse_object(compacts['init_EB00']))==['func_10010BE8','func_10010FFC']
 for owner in targets:
  old=out/('frozen/conker/build/src/'+owner+'.c.o');new=targets[owner];assert normalized_pools(old)==normalized_pools(new)and sections(old)['.reginfo']==sections(new)['.reginfo']
 elf=link(targets,'qualified-image');before=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x8DC28:0x8DEE0];strict_image(before,actual,truth)
 old,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');new,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert old.keys()==new.keys()and oa==na and{n for n in new if old[n]!=new[n]}=={'func_15060778'}
 protected=audit_layout(elf,conker);assert protected['exact']and protected['different_bytes']==0
 report=dict(source_installed=installed,input_audit=input_audit,frozen_inputs=len(frozen),raw_game_neighbors=88,raw_init_equal_neighbors=52,Init_object_byte_identical=True,padded_game_neighbors=88,all_addresses_fixed=True,functions=len(new),image_changed_bytes=sum(a!=b for a,b in zip(before,actual)),strict_unexplained_bytes=0,guards={n:len(d['rows'])for n,d in derivation.items()},Make_commands=len(commands),Make_warnings=warnings,ELF_sha256=sha(actual),protected_data=protected)
 assert sha(actual)==MANIFEST['ELF_sha256']and sha(targets['game_83300'].read_bytes())==MANIFEST['Game_object_sha256']and sha((out/'proposed-guards.csv').read_bytes())==MANIFEST['guards_sha256']
 live_inputs(installed)
 (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report

if __name__=='__main__':prepare()
