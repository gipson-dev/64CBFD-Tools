"""Actual-Make shadow and strict complete-image proof for the direct body."""
import csv,hashlib,inspect,json,struct
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150DDFAC-match'
NAME='func_150DDFAC';OWNER='game/generated_108E90';SOURCE='conker/src/game/generated_108E90.c';ENTRY=0x150DDFAC;ROM=0x10B45C;SIZE=384
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_effect_callback_150ddfac_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\ntypedef struct {\n    s32 flags;\n    s16 lifetime;\n    u8 kind;\n    u8 pad7;\n    s32 value8, valueC;\n    u8 value10, value11, value12, value13, value14, value15;\n    u8 pad16[2];\n    s32 resource;\n    u8 pad1C[12];\n} EffectDescriptor108E90;\ntypedef struct { f32 x, y, z; u8 padC[8]; } EffectPosition108E90;\nf32 func_150ADA68(void);\ns32 func_150ADA20(void);\nstruct210 *func_1513C73C(s32, u8, u8, s32, f32, f32, f32, f32, f32, u8, u8, s32, u8, s32);\n\n\n'
BASE='s32 func_150DDFAC(u8 *actor, f32 previousX, f32 previousY, f32 previousZ, f32 height, void *parameter) {\n    u8 *payload = *(u8 **)(actor + 0x98);\n    EffectPosition108E90 *positions = *(EffectPosition108E90 **)(actor + 0x94);\n    EffectDescriptor108E90 descriptor;\n    f32 range = func_150ADA68() * 70.0f + 10.0f;\n    s32 third, second, first;\n\n    payload[0x20] = 4;\n    switch (func_150ADA20() & 1) {\n        case 0: descriptor.kind = 29; break;\n        case 1: descriptor.kind = 30; break;\n    }\n    descriptor.value8 = 0;\n    descriptor.valueC = 0;\n    descriptor.flags = 17;\n    descriptor.lifetime = 100;\n    descriptor.value10 = 255;\n    descriptor.value11 = 255;\n    descriptor.value12 = 0;\n    descriptor.value13 = 0;\n    descriptor.value14 = 0;\n    descriptor.value15 = 255;\n    descriptor.resource = 0x30002;\n    first = func_150ADA20();\n    second = func_150ADA20();\n    third = func_150ADA20();\n    func_1513C73C((s32)&descriptor, 5, 0, (s32)parameter,\n                 positions[*(s8 *)(actor + 0x2D)].x, height,\n                 positions[*(s8 *)(actor + 0x2D)].z, range, range,\n                 first & 255, (third & 1) + (second & 1), 0,\n                 actor[0x0C], actor[1]);\n    return 1;\n}'
def payload(path,name=NAME):
 text,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def variant(old):
 text=old.replace('#include "structs.h"\n','#include "structs.h"\n'+DECLS[:-1],1)
 return text.replace(body(text,NAME),'/* Build and submit an effect for the selected actor position. */\n'+BASE)

from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda data:hashlib.sha256(data).hexdigest()
p.OWNER='game/generated_108E90'
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150DDFAC':384}")
scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/build/src/game/generated_108E90.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption effect-callback input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen effect-callback input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown effect-callback source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed effect-callback qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed effect-callback result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Effect-callback source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def main():
 q.p=p
 frozen,installed=freeze()
 source=p.variant((p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8'));(p.out/'selected-source.c').write_text(source);old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else'\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(p.out/'proposed-guards.csv').write_bytes((p.root/'conker/retail_word_patches.us.csv').read_bytes())
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=Path(str(obj)+'.compact');before,bd=p.compile_owner(p.root,p.out,old.decode(), 'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected');assert not bd and not ad
 assert same_functions(before,after,(p.NAME,))==11 and same_functions(compact,after)==12 and same_functions(p.out/'frozen/conker/build/src/game/generated_108E90.c.o',obj,(p.NAME,))==11
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);assert p.payload(obj)==(raw,refs);lookup={n:int(n.split('_')[1],16)if n.startswith(('func_','D_'))else 0x15047D60 for es in refs.values()for _,n in es};words=p.bound_blob(raw,refs,lookup);truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>96I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth});oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and {n for n in oldfunc if oldfunc[n]!=newfunc[n]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((p.SOURCE,proposal),('conker/build/src/game/generated_108E90.c.o',obj),('conker/build/conker.us.elf',elf))};assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 r=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=96,frame=144,guards=0,non_target_neighbors=11,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True);return r
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from bound effect workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
