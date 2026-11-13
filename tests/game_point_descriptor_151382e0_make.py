from pathlib import Path
import hashlib,inspect,json,shutil,sys
from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as out
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.experiments.game_point_descriptor_151382e0_match import sources as candidate_sources
q.out=out;q.p.out=out
guard=out/'proposed-guards.csv';shutil.copyfile(out/'durable-private-guards.csv',guard)
linker=out/'frozen/conker/build/conker.ld';linker.parent.mkdir(parents=True,exist_ok=True)
current=(root/'conker/build/conker.ld').read_bytes()
if linker.exists():assert linker.read_bytes()==current
else:linker.write_bytes(current)
sources={'game_161520':out/'durable-point-after.c','game/generated_17CAF0':out/'durable-helper-after.c','game_16EE20':out/'durable-effect-after.c','game_2062D0':out/'durable-trail-after.c'}
code=inspect.getsource(q.actual_make)
needle="replacements['retail_word_patches.us.csv']="
assert needle in code
code=code.replace(needle,"replacements['src/game/translation_units/161520_actor_point_effects.c']=(p.out/'durable-caller-after.c').relative_to(conker).as_posix();"+needle)
code=code.replace("assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)==1","assert sum('../ido/ido5.3_recomp/cc'in line for line in commands)>=4")
namespace=dict(q.actual_make.__globals__);exec(code,namespace);targets,commands=namespace['actual_make'](sources)
for owner in sources:
 old=root/'conker/build'/('src/'+owner+'.c.o');new=targets[owner];exclude=('func_151382E0',) if owner=='game_161520' else ()
 print(owner,'unchanged functions',same_functions(old,new,exclude),flush=True)
 before,after=sections(old),sections(new)
 changed=[name for name in before.keys()|after.keys() if before.get(name)!=after.get(name)]
 print('sections changed:',changed,flush=True)
elf=q.link(targets);old=(root/'conker/build/conker.us.elf').read_bytes();new=elf.read_bytes();rom=(root/'conker/conker.us.bin').read_bytes();truth=rom[0x165790:0x1658d4]
code=inspect.getsource(q.strict_image).replace("sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","sizes={'func_151382E0':324}")
namespace=dict(q.strict_image.__globals__);exec(code,namespace)
installed=candidate_sources()[1]
if installed:
 assert old==new, 'Installed and actual-Make shadow ELFs differ'
 report={'strict_exclusions':0,'installed_image_identical':True}
else:
 report=namespace['strict_image'](old,new,{'func_151382E0':truth})
before,_,oa=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');after,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert before.keys()==after.keys() and oa==na and {n for n in before if before[n]!=after[n]}==({'func_151382E0'} if not installed else set())
layout=audit_layout(elf,root/'conker');assert layout['exact'] and layout['different_bytes']==0
print(json.dumps(dict(commands=len(commands),all_functions=len(after),image=report,protected_data=layout),default=str),flush=True)
