import os,sys,subprocess,hashlib,inspect,json,struct
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();root=ROOT;out=root/'conker/build/game-twin-vertex-match'
MANIFEST=json.loads(Path(__file__).with_name('game_twin_view_vertices_manifest.json').read_text());FROZEN=MANIFEST['frozen'];PINS=MANIFEST['pins'];SELECTED=MANIFEST['selected']
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_151AC810':476,'func_151DAE28':476}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
code=inspect.getsource(q.actual_make).replace("in line for line in commands)==1","in line for line in commands)==2");scope=dict(q.actual_make.__globals__);exec(code,scope);actual_make=scope['actual_make']

TARGETS=('151AC810','151DAE28');OWNERS=('1D92F0','2062D0');ASMS=('conker/asm/1D92F0.s','conker/asm/nonmatchings/game_2062D0/func_151DAE28.s')
def payload(path,name):
 data,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
def verify(target,raw,refs):
 pin=PINS[target];expected={int(k):[tuple(v) for v in values] for k,values in pin['refs'].items()}
 if len(raw)!=476 or sha(raw)!=pin['sha256'] or refs!=expected:raise ValueError('View-vertex callback body or relocations changed')
 return raw,refs
SOURCES=('conker/src/game/generated_1D92F0.c','conker/src/game_2062D0.c')
OBJECTS=('conker/build/src/game/generated_1D92F0.c.o','conker/build/src/game_2062D0.c.o')
MUTABLE=SOURCES+OBJECTS+('conker/retail_word_patches.us.csv','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}|set(ASMS):
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen input: '+n)
 states=[sha((root/n).read_bytes()) for n in SOURCES];old=[FROZEN[n] for n in SOURCES];new=[MANIFEST['qualification']['installed_hashes'][n] for n in SOURCES]
 if states==old:installed=False
 elif states==new:installed=True
 else:raise ValueError('Partial or unknown source state')
 allowed=dict(MANIFEST['qualification']['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Source state changed during qualification')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def assemble_original():
 for target,asm in zip(TARGETS,ASMS):
  name='func_'+target;whole=(out/'frozen'/asm).read_text();start='glabel '+name+'\n';end='endlabel '+name;targetcode=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/('original_'+target+'.s');src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+targetcode+'\n.size '+name+',.-'+name+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=SimpleNamespace(root=root,out=out)
 actual_make.__globals__["p"]=q.p
 frozen,installed=freeze()
 assemble_original()
 configs=(('151AC810','game/generated_1D92F0',0x1d9cc0,32),('151DAE28','game_2062D0',0x2082d8,61));sources={};source_text={};old_text={}
 for target,owner,offset,neighbors in configs:
  source='conker/src/'+owner+'.c';old=(out/'frozen'/source).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';text=SELECTED[target];(out/('variant_'+target+'_source.c')).write_text(text);proposal=out/('proposal_'+target+'.c');proposal.write_bytes(text.replace('\n',nl).encode());sources[owner]=proposal;source_text[owner]=text;old_text[owner]=old.decode()
 base=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();assert base.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(base)
 targets,commands=actual_make(sources);payloads={};hashes={}
 def payload(o,name):
  data,fs,rs=parse_object(o);a,n=fs[name]['value'],fs[name]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 for target,owner,offset,neighbors in configs:
  name='func_'+target;source='conker/src/'+owner+'.c';obj=targets[owner];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old_text[owner],'independent-before-'+target);after,ad=compile_owner(root,out,source_text[owner],'variant_'+target)
  assert diagnostic_rows(bd)==diagnostic_rows(ad);assert same_functions(before,after,(name,))==neighbors and same_functions(compact,after)==neighbors+1 and same_functions(out/'frozen'/('conker/build/src/'+owner+'.c.o'),obj,(name,))==neighbors
  assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
  raw,refs=payload(compact,name);original,origrefs=payload(out/('original_'+target+'.o'),name);fixed,freferences=payload(obj,name);assert (fixed,freferences)==(original,origrefs)==verify(target,raw,refs)
  words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[offset:offset+476];assert struct.pack('>119I',*words)==truth;payloads[name]=truth
  hashes[source]=sha(sources[owner].read_bytes());hashes['conker/build/src/'+owner+'.c.o']=sha(obj.read_bytes())
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,payloads)
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}==set(payloads)
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes['conker/retail_word_patches.us.csv']=sha((out/'proposed-guards.csv').read_bytes());hashes['conker/build/conker.us.elf']=sha(elf.read_bytes())
 assert hashes==MANIFEST['qualification']['installed_hashes'] and image==MANIFEST['qualification']['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),targets=list(payloads),raw_words_each=119,guards_each=0,inserted_words=0,non_target_neighbors=[32,61],actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
