import os,sys,subprocess,hashlib,inspect,json,struct
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();root=ROOT;out=root/'conker/build/game-animated-packet-match'
MANIFEST=json.loads(Path(__file__).with_name('game_animated_packet_renderer_manifest.json').read_text());FROZEN=MANIFEST['frozen']
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_15167C58':300}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']

MUTABLE=('conker/src/game_1944C0.c','conker/retail_word_patches.us.csv','conker/build/src/game_1944C0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt','conker/asm/nonmatchings/game_1944C0/func_15167C58.s'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen input: '+n)
 current=sha((root/MUTABLE[0]).read_bytes());old=FROZEN[MUTABLE[0]];new=MANIFEST['qualification']['installed_hashes'][MUTABLE[0]]
 if current==old:installed=False
 elif current==new:installed=True
 else:raise ValueError('Unknown source state')
 allowed=dict(MANIFEST['qualification']['installed_hashes']);allowed[MUTABLE[-1]]=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed result incomplete: '+n)
 return FROZEN,installed
def assemble_original():
 name='func_15167C58';whole=(out/'frozen/conker/asm/nonmatchings/game_1944C0/func_15167C58.s').read_text();start='glabel '+name+'\n';end='endlabel '+name;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';(out/'original_target.s').write_text(target);src=out/'original.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+name+',.-'+name+'\n')
 r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(src.with_suffix('.o')),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=SimpleNamespace(root=root,out=out)
 frozen,installed=freeze();assemble_original();(out/'normalization_screen.json').write_text(json.dumps(MANIFEST['pin']))
 name='conker/src/game_1944C0.c';old=(out/'frozen'/name).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';text=MANIFEST['selected'];(out/'candidate_source.c').write_text(text);proposal=out/'proposal.c';proposal.write_bytes(text.replace('\n',nl).encode())
 base=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();lines=MANIFEST['guards'].splitlines(keepends=True);assert base.endswith(b'\n') and len(lines)==43;(out/'proposed-guards.csv').write_bytes(base+''.join(lines[1:]).encode())
 targets,commands=q.actual_make({'game_1944C0':proposal});obj=targets['game_1944C0'];compact=Path(str(obj)+'.compact')
 before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,text,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad)
 assert same_functions(before,after,('func_15167C58',))==41 and same_functions(compact,after)==42
 assert same_functions(out/'frozen/conker/build/src/game_1944C0.c.o',obj,('func_15167C58',))==41
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(path,name):
  data,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 target='func_15167C58';original=payload(out/'original.o',target);fixed=payload(obj,target);raw,rawrefs=payload(compact,target);assert fixed==original and sha(raw)==MANIFEST['pin']['raw_sha256']
 body,refs=fixed;lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(body,refs,{nm:lookup[nm]for es in refs.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x195108:0x195234];assert struct.pack('>75I',*words)==truth;payloads={target:truth}
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,payloads)
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and {n for n in oldfunc if oldfunc[n]!=newfunc[n]}=={target}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 assert freeze()[1]==installed
 hashes={name:sha(proposal.read_bytes()),'conker/retail_word_patches.us.csv':sha((out/'proposed-guards.csv').read_bytes()),'conker/build/src/game_1944C0.c.o':sha(obj.read_bytes()),'conker/build/conker.us.elf':sha(elf.read_bytes())}
 (out/'candidate.o').write_bytes(after.read_bytes());assert hashes==MANIFEST['qualification']['installed_hashes'] and image==MANIFEST['qualification']['image']
 report=dict(source_installed=installed,frozen_inputs=len(frozen),target=target,raw_words=75,guards=42,non_target_neighbors=41,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True);return report

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
