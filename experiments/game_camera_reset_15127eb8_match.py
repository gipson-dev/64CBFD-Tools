"""Private actual-Make and strict complete-image qualification."""
import hashlib,inspect,json,struct
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-15127EB8-match'
NAME='func_15127EB8';OWNER='game_14FF90';SOURCE='conker/src/game_14FF90.c';ENTRY=0x15127EB8;ROM=0x155368;SIZE=308
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_camera_reset_15127eb8_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='void func_151C9ED4(struct108 *);'
BASE='void func_15127EB8(struct108 *camera) {\n    struct127 *actor;\n    struct127 *original;\n    func_151239CC(camera, 1);\n    camera->unk3D4->unk197 = 0;\n    func_151C9ED4(camera);\n    camera->unk19C = 0.0f;\n    camera->unk1A0 = 0.0f;\n    camera->unk1A4 = 0.0f;\n    camera->unk1A8 = 0.0f;\n    func_1510B32C(camera->unk23D, 0.0f, 0.0f, 1.0f);\n    *(f32 *)((u8 *)D_800BE628 + camera->unk23D * 0x180 + 0x84) = 1.0f;\n    func_150627D4(camera->unk3D0);\n    D_800DBFF4[camera->unk23D] = 2;\n    original = camera->unk3D0;\n    if (original->unk65 != 0) actor = &D_800CC2D0[original->unk65 - 1];\n    else actor = original;\n    ((u8 *)actor)[0x2FC] &= ~(1 << camera->unk23D);\n    actor->unk74 &= ~(1 << camera->unk23D);\n    camera->unk23C = 1;\n}'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def variant(old):
 source=old.replace('#include "variables.h"','#include "variables.h"\n'+DECLS,1)
 source=source.replace(body(source,NAME),'/* Reset camera state and release the selected actor slot. */\n'+BASE)
 a=source.index('// NON-MATCHING: not too far away\n// void func_15127EB8')
 b=source.index('\nvoid func_15127FEC',a)
 return source[:a]+source[b:]


from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda b:hashlib.sha256(b).hexdigest();
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_15127EB8':308}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game_14FF90.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption camera-reset input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen camera-reset input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown camera-reset source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed camera-reset qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed camera-reset result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Camera-reset source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)

def main():
 q.p=p
 frozen,installed=freeze()
 source=variant((out/'frozen'/SOURCE).read_text());(out/'selected-source.c').write_text(source)
 old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(p.out/'proposed-guards.csv').write_bytes((p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=Path(str(obj)+'.compact');before,bd=p.compile_owner(p.root,p.out,old.decode(),'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected');assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(p.NAME,))==44 and same_functions(compact,after)==45 and same_functions(p.out/'frozen/conker/build/src/game_14FF90.c.o',obj,(p.NAME,))==44;assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);assert p.payload(obj)==(raw,refs);lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{name:lookup[name]for es in refs.values()for _,name in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>77I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth});oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys() and oa==na and {n for n in oldfunc if oldfunc[n]!=newfunc[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((p.SOURCE,proposal),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game_14FF90.c.o',obj),('conker/build/conker.us.elf',elf))};assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=77,frame=32,guards=0,non_target_neighbors=44,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError('Consumer differs from camera-reset workspace')
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=='__main__':prepare()
