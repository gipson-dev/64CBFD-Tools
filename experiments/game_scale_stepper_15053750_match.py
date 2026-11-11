"""Private actual-Make and strict whole-image qualification after freeze."""
import hashlib,inspect,json,struct
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-15053750-match'
NAME='func_15053750';OWNER='game_77AD0';SOURCE='conker/src/game_77AD0.c';ENTRY=0x15053750;ROM=0x80c00;SIZE=324
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_scale_stepper_15053750_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
BASE='void func_15053750(struct127 *actor) {\n    f32 difference;\n    s32 direction;\n    difference = actor->unk154 - actor->xz_scale;\n    if (difference != 0.0f) {\n        if (fabsf(difference) < actor->unk15C) {\n            func_15062BDC(actor, actor->unk154, actor->y_scale);\n        } else {\n            direction = difference < 0.0f ? -1 : 1;\n            func_15062BDC(actor, (f32)direction * actor->unk15C + actor->xz_scale, actor->y_scale);\n        }\n    }\n    difference = actor->unk158 - actor->y_scale;\n    if (difference != 0.0f) {\n        if (fabsf(difference) < actor->unk15C) {\n            func_15062BDC(actor, actor->xz_scale, actor->unk158);\n        } else {\n            direction = difference < 0.0f ? -1 : 1;\n            func_15062BDC(actor, actor->xz_scale, (f32)direction * actor->unk15C + actor->y_scale);\n        }\n    }\n}'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}

def variant(old):
 source=old.replace('s32 func_15053750();','void func_15053750();',1)
 source=source.replace(body(source,NAME),BASE)
 stale='// ???\n/* Non-matching C placeholders for asm/nonmatchings/game_77AD0/func_15053750.s. */\n'
 assert source.count(stale)==1
 return source.replace(stale,'/* Step actor scales toward their targets using bounded increments. */\n')

from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_15053750':324}")
scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game_77AD0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption scale-stepper input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen scale-stepper input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown scale-stepper source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed scale-stepper qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed scale-stepper result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Scale-stepper source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)

def main():
 q.p=p
 frozen,installed=freeze()
 source=variant((out/'frozen'/SOURCE).read_text());(out/'selected-source.c').write_text(source)
 old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode())
 (p.out/'proposed-guards.csv').write_bytes((p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=Path(str(obj)+'.compact')
 before,bd=p.compile_owner(p.root,p.out,old.decode(),'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(p.NAME,))==57 and same_functions(compact,after)==58 and same_functions(p.out/'frozen/conker/build/src/game_77AD0.c.o',obj,(p.NAME,))==57
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);assert p.payload(obj)==(raw,refs)
 lookup={v[1]:v[2][1] for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())}
 words=p.bound_blob(raw,refs,{name:lookup[name] for es in refs.values() for _,name in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>81I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
 assert oldfunc.keys()==newfunc.keys() and oa==na and {n for n in oldfunc if oldfunc[n]!=newfunc[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes()) for n,f in ((p.SOURCE,proposal),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game_77AD0.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=81,frame=24,guards=0,non_target_neighbors=57,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError('Consumer differs from scale-stepper workspace')
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=='__main__':prepare()
