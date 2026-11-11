"""Actual-Make shadow and strict complete-image proof for the direct body."""
import csv,hashlib,inspect,json,struct
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150D317C-match'
NAME='func_150D317C';OWNER='game/generated_FFBA0';SOURCE='conker/src/game/generated_FFBA0.c';ENTRY=0x150D317C;ROM=0x10062C;SIZE=384
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_oscillation_callback_150d317c_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\nextern f32 D_800BE9A4;\nf32 func_15144B68(f32);\nf32 sinf(f32);\ntypedef struct {\n    f32 x;\n    f32 y;\n    f32 baseX;\n    f32 baseY;\n    f32 amplitudeX;\n    f32 amplitudeY;\n    f32 phaseX;\n    f32 phaseY;\n    f32 speedX;\n    f32 speedY;\n    f32 timer;\n    f32 opacityRate;\n} OscillationFFBA0;\ntypedef struct {\n    u8 pad00[0x5C];\n    u8 opacity;\n    u8 pad5D[0xB3];\n    OscillationFFBA0 motion;\n} OscillatingRecordFFBA0;\n\n\n'
BASE='s32 func_150D317C(OscillatingRecordFFBA0 *record) {\n    OscillationFFBA0 *motion;\n\n    record->motion.phaseX += record->motion.speedX * D_800BE9A4;\n    record->motion.phaseY += record->motion.speedY * D_800BE9A4;\n    motion = &record->motion;\n    motion->phaseX = func_15144B68(motion->phaseX);\n    motion->phaseY = func_15144B68(motion->phaseY);\n    motion->x = sinf(motion->phaseX) * motion->amplitudeX + motion->baseX;\n    motion->y = sinf(motion->phaseY) * motion->amplitudeY + motion->baseY;\n    motion->timer -= D_800BE9A4;\n    record->opacity = (u32)(motion->opacityRate * motion->timer);\n    if (motion->timer > 0.0f) return 1;\n    return 0;\n}'
def payload(path,name=NAME):
 text,fs,refs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return text[a:a+n],{i-a:v for i,v in refs.items()if a<=i<a+n}

def variant(old):
 text=old.replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+DECLS[:-1],1)
 return text.replace(body(text,NAME),'/* Update the record oscillation and report whether its timer remains positive. */\n'+BASE)

from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda data:hashlib.sha256(data).hexdigest()
p.OWNER='game/generated_FFBA0'
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150D317C':384}")
scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/build/src/game/generated_FFBA0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption oscillation-callback input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen oscillation-callback input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown oscillation-callback source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed oscillation-callback qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed oscillation-callback result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Oscillation-callback source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def main():
 q.p=p
 frozen,installed=freeze()
 source=p.variant((p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8'));(p.out/'selected-source.c').write_text(source);old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else'\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(p.out/'proposed-guards.csv').write_bytes((p.root/'conker/retail_word_patches.us.csv').read_bytes())
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=Path(str(obj)+'.compact');before,bd=p.compile_owner(p.root,p.out,old.decode(), 'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected');assert not bd and not ad
 assert same_functions(before,after,(p.NAME,))==5 and same_functions(compact,after)==6 and same_functions(p.out/'frozen/conker/build/src/game/generated_FFBA0.c.o',obj,(p.NAME,))==5
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);assert p.payload(obj)==(raw,refs);lookup={n:int(n.split('_')[1],16)if n.startswith(('func_','D_'))else 0x15047D60 for es in refs.values()for _,n in es};words=p.bound_blob(raw,refs,lookup);truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>96I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth});oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and {n for n in oldfunc if oldfunc[n]!=newfunc[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((p.SOURCE,proposal),('conker/build/src/game/generated_FFBA0.c.o',obj),('conker/build/conker.us.elf',elf))};assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 r=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=96,frame=32,guards=0,non_target_neighbors=5,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True);return r
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from bound callback workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
