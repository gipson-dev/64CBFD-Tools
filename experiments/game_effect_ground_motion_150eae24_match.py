import os,sys,hashlib,json,struct,inspect
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150EAE24-match'
NAME='func_150EAE24';OWNER='game/generated_117490';SOURCE='conker/src/game/generated_117490.c';CALLER='conker/src/game_18D770.c';ENTRY=0x150EAE24;ROM=0x1182D4;SIZE=296;SLOT=300
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_effect_ground_motion_150eae24_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
BASE='s32 func_150EAE24(struct225 *record) {\n    u8 *actor = (u8 *)record;\n    f32 position[3];\n    EffectMotion *motion = (EffectMotion *)(actor + 0x18);\n    motion->x += motion->dx * D_800BE9A4;\n    motion->z += motion->dz * D_800BE9A4;\n    position[0] = motion->x;\n    position[1] = motion->height;\n    position[2] = motion->z;\n    record->unk14->unkE = (s32)motion->x;\n    record->unk14->unk12 = (s32)motion->z;\n    if (func_15046C80(position, 0, motion->queryHeight, &motion->result)) {\n        record->unk14->unk10 = (s32)motion->result.height;\n    } else {\n        record->unk14->unk10 = (s32)motion->height;\n    }\n    motion->remaining -= D_800BE9A4;\n    if (motion->remaining <= 0.0f) return 0;\n    return 1;\n}'
PREFIX='#include <ultra64.h>\n#include "structs.h"\n\nextern f32 D_800BE9A4;\ntypedef struct { f32 height; s16 vertices[9]; s16 pad16; u32 metadata; u8 flags; u8 state; u16 pad1e; s32 value; } HeightResult71820;\ns32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);\ntypedef struct { f32 x, z, dx, dz, height, queryHeight, remaining; HeightResult71820 result; } EffectMotion;\n\n'
CALLER_OLD='    if ((ret == 0) && (arg0->unkF != -1) && (D_8008B0F0[arg0->unkF]() == 0)) {'
CALLER_NEW='    /* The retail dispatcher passes the record to the selected callback. */\n    if ((ret == 0) && (arg0->unkF != -1) && (((s32 (*)(struct225 *))(void (*)(void))D_8008B0F0[arg0->unkF])(arg0) == 0)) {'
def payload(path):
 t,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return t[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}

def variant(old):
 source=old.replace('#include <ultra64.h>\n',PREFIX,1)
 source=source.replace(body(source,NAME),BASE)
 return source.replace('s32 func_150EAE24(struct225 *record) {','/* Advance a moving effect, update its position and query ground height. */\ns32 func_150EAE24(struct225 *record) {',1)
def caller_variant(old):
 assert old.count(CALLER_OLD)==1
 return old.replace(CALLER_OLD,CALLER_NEW,1)

from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150EAE24':296}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
code=inspect.getsource(q.actual_make).replace("==1\n return targets,commands", "==len(sources)\n return targets,commands");assert '==len(sources)' in code;scope2=dict(q.actual_make.__globals__);scope2['p']=p;exec(code,scope2);actual_make=scope2['actual_make']

MUTABLE=(SOURCE,CALLER,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_117490.c.o','conker/build/src/game_18D770.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption ground-motion input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen ground-motion input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown ground-motion source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed ground-motion qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed ground-motion result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Ground-motion source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)


def main():
 q.p=p
 frozen,installed=freeze()
 source=variant((out/'frozen'/SOURCE).read_text());(out/'selected-source.c').write_text(source);old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode())
 cold=(p.out/'frozen/conker/src/game_18D770.c').read_bytes();caller=caller_variant(cold.decode());(p.out/'caller-proposal.c').write_text(caller);ca,da=p.compile_owner(p.root,p.out,cold.decode(),'caller-same');(p.out/'caller-before.o').write_bytes(ca.read_bytes());cb,db=p.compile_owner(p.root,p.out,caller,'caller-same');(p.out/'caller-after.o').write_bytes(cb.read_bytes());assert diagnostic_rows(da)==diagnostic_rows(db); nl='\r\n' if b'\r\n' in cold else '\n';cp=p.out/'caller-install.c';cp.write_bytes(caller.replace('\n',nl).encode());(p.out/'proposed-guards.csv').write_bytes((p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
 targets,commands=actual_make({p.OWNER:proposal,'game_18D770':cp});obj=targets[p.OWNER];compact=Path(str(obj)+'.compact');co=targets['game_18D770'];cc=Path(str(co)+'.compact')
 before,bd=p.compile_owner(p.root,p.out,old.decode(),'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected');assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(p.NAME,))==10 and same_functions(compact,after)==11 and same_functions(p.out/'frozen/conker/build/src/game/generated_117490.c.o',obj,(p.NAME,))==10
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);assert p.payload(obj)==(raw,refs);lookup={v[1]:v[2][1] for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(raw,refs,{name:lookup[name] for es in refs.values() for _,name in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>74I',*words)==truth
 cbefore=(p.out/'caller-before.o');cafter=(p.out/'caller-after.o');assert same_functions(cbefore,cafter)==78 and same_functions(cc,cafter)==78 and same_functions(p.out/'frozen/conker/build/src/game_18D770.c.o',co)==78
 assert all(k=='.mdebug' for k in sections(cbefore).keys()|sections(cafter).keys() if sections(cbefore).get(k)!=sections(cafter).get(k));assert sections(cafter)['.reginfo']==sections(cc)['.reginfo']
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys() and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={name:sha(f.read_bytes()) for name,f in ((p.SOURCE,proposal),('conker/src/game_18D770.c',cp),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game/generated_117490.c.o',obj),('conker/build/src/game_18D770.c.o',co),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 r=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=74,alignment_words=1,frame=56,guards=0,non_target_neighbors=10,caller_functions_unchanged=78,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes);(p.out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True);return r

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from ground-motion workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
