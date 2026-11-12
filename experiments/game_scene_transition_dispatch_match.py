import os,sys,subprocess,hashlib,inspect,json,struct
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();root=ROOT;out=root/'conker/build/game-scene-transition-dispatch-match'
MANIFEST=json.loads(Path(__file__).with_name('game_scene_transition_dispatch_manifest.json').read_text());FROZEN=MANIFEST['frozen']
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
sha=lambda b:hashlib.sha256(b).hexdigest()

MUTABLE=('conker/src/game/generated_49BE0.c','conker/Makefile','conker/build/src/game/generated_49BE0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt','conker/retail_word_patches.us.csv','conker/asm/49BE0.s'}:
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

def main():
 q.p=SimpleNamespace(root=root,out=out)
 frozen,installed=freeze()
 name='conker/src/game/generated_49BE0.c';old=(out/'frozen'/name).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';text=MANIFEST['selected'].replace('void func_1501C730(s32 command', '/* Dispatch a scene transition using the original seven-entry table. */\nvoid func_1501C730(s32 command').replace('        case 0:\n            D_800D2132 = 0;', '        case 0:\n            /* Retains the retail switch range; IDO folds this repeated store. */\n            D_800D2132 = 0;')
 proposal=out/'proposal.c';proposal.write_bytes(text.replace('\n',nl).encode())
 make=(out/'frozen/conker/Makefile').read_bytes();line=b'$(BUILD_DIR)/$(SRC_DIR)/game/generated_49BE0.c.o: RETAIL_RODATA_SYMBOL := jtbl_800969A0_game';assert line not in make
 newmake=make+b'\n# Scene transitions retain their original seven-entry jump table.\n'+line+b'\n';makepath=out/'proposal.Makefile';makepath.write_bytes(newmake)
 (out/'proposed-guards.csv').write_bytes((out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
 code=inspect.getsource(q.actual_make).replace("args=['make','-n'", "args=['make','-f','build/game-scene-transition-dispatch-match/proposal.Makefile','-n'")
 assert code!=inspect.getsource(q.actual_make);scope=dict(q.actual_make.__globals__);exec(code,scope);targets,commands=scope['actual_make']({'game/generated_49BE0':proposal});obj=targets['game/generated_49BE0'];compact=Path(str(obj)+'.compact')
 before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,text,'independent-selected');assert diagnostic_rows(bd)==diagnostic_rows(ad)
 assert same_functions(before,after,('func_1501C730',))==0 and same_functions(compact,after)==1
 assert same_functions(out/'frozen/conker/build/src/game/generated_49BE0.c.o',obj,('func_1501C730',))==0
 assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(path):
  data,fs,rs=parse_object(path);a,n=fs['func_1501C730']['value'],fs['func_1501C730']['size'];return data[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}
 body,refs=payload(obj);(out/'candidate.o').write_bytes(after.read_bytes());(out/'candidate_source.c').write_text(MANIFEST['selected'])
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(body,refs,{nm:lookup[nm]for es in refs.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x49be0:0x49d08];assert struct.pack('>74I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes()
 code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_1501C730':296}");scope=dict(q.strict_image.__globals__);exec(code,scope);image=scope['strict_image'](baseline,actual,{'func_1501C730':truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys() and oa==na and {n for n in oldfunc if oldfunc[n]!=newfunc[n]}=={'func_1501C730'}
 data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
 assert freeze()[1]==installed
 report=dict(source_installed=installed,frozen_inputs=len(frozen),target='func_1501C730',raw_words=74,guards=0,table_anchor='jtbl_800969A0_game',actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes={'conker/src/game/generated_49BE0.c':sha(proposal.read_bytes()),'conker/Makefile':sha(makepath.read_bytes()),'conker/build/src/game/generated_49BE0.c.o':sha(obj.read_bytes()),'conker/build/conker.us.elf':sha(elf.read_bytes())})
 assert report['installed_hashes']==MANIFEST['qualification']['installed_hashes'] and image==MANIFEST['qualification']['image']
 (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True);return report

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
