"""Private actual-Make and strict whole-image initializer qualification."""
import hashlib,inspect,json,struct
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-1500FE30-match'
NAME='func_1500FE30';OWNER='game/generated_3D2E0';SOURCE='conker/src/game/generated_3D2E0.c';ENTRY=0x1500FE30;ROM=0x3D2E0;SIZE=364
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_table_initializer_1500fe30_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\ntypedef struct { u8 group; u8 pad1; s8 marker; u8 pad3; s16 choice; s16 previous; s16 next; } Entry10;\nextern Entry10 *D_800BE4E0;\nvoid *allocate_memory(s32,s32,s32,s32);\nu32 func_150ADA20(void);\nvoid func_150C851C(s32);\n'
BASE='void func_1500FE30(void) {\n    s32 i;\n    D_800BE4E0 = allocate_memory(100, 1, 0, 0);\n    bzero(D_800BE4E0, 100);\n    for (i = 0; i < 10; i++) {\n        D_800BE4E0[i].group = i / 5;\n        D_800BE4E0[i].marker = -1;\n        D_800BE4E0[i].choice = func_150ADA20() % 5;\n    }\n    func_150C851C(100);\n    D_800BE4E0[0].previous = D_800BE4E0[0].next;\n    D_800BE4E0[1].previous = D_800BE4E0[1].next;\n    for (i = 2; i < 10; i += 4) {\n        D_800BE4E0[i].previous = D_800BE4E0[i].next;\n        D_800BE4E0[i + 1].previous = D_800BE4E0[i + 1].next;\n        D_800BE4E0[i + 2].previous = D_800BE4E0[i + 2].next;\n        D_800BE4E0[i + 3].previous = D_800BE4E0[i + 3].next;\n    }\n}'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}

def variant(old):
 source=old.replace('#include <ultra64.h>','#include <ultra64.h>\n'+DECLS,1)
 source=source.replace(body(source,NAME),BASE)
 stale='/* Non-matching placeholders for the text-only asm slice asm/3D2E0.s. */\n'
 assert source.count(stale)==1
 source=source.replace(stale,'',1)
 return source.replace('void func_1500FE30(void) {','/* Initialize ten table entries and sync their previous values. */\nvoid func_1500FE30(void) {',1)

from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_1500FE30':364}")
scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_3D2E0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption table-initializer input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen table-initializer input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown table-initializer source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed table-initializer qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed table-initializer result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Table-initializer source state changed during validation')
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
 assert same_functions(before,after,(p.NAME,))==2 and same_functions(compact,after)==3 and same_functions(p.out/'frozen/conker/build/src/game/generated_3D2E0.c.o',obj,(p.NAME,))==2
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);assert p.payload(obj)==(raw,refs)
 lookup={v[1]:v[2][1] for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())}
 words=p.bound_blob(raw,refs,{name:lookup[name] for es in refs.values() for _,name in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>91I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
 assert oldfunc.keys()==newfunc.keys() and oa==na and {n for n in oldfunc if oldfunc[n]!=newfunc[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes()) for n,f in ((p.SOURCE,proposal),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game/generated_3D2E0.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=91,frame=48,guards=0,non_target_neighbors=2,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError('Consumer differs from table-initializer workspace')
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=='__main__':prepare()
