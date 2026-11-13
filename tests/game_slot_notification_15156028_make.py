from pathlib import Path
import inspect,json,shutil,sys
from tools.experiments.game_slot_notification_15156028_match import ROOT as root, OUT as out
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.experiments.game_slot_notification_15156028_match import sources as candidate_sources
q.out=out;q.p.out=out;shutil.copyfile(out/'durable-guards.csv',out/'proposed-guards.csv')
linker=out/'frozen/conker/build/conker.ld';linker.parent.mkdir(parents=True,exist_ok=True);current=(root/'conker/build/conker.ld').read_bytes()
if linker.exists():assert linker.read_bytes()==current
else:linker.write_bytes(current)
owner='game/generated_182C30';targets,commands=q.actual_make({owner:out/'durable-after.c'});oldobj=root/'conker/build/src/game/generated_182C30.c.o';newobj=targets[owner]
assert same_functions(oldobj,newobj,('func_15156028',))==8
before,after=sections(oldobj),sections(newobj);print('owner changed sections:',[n for n in before.keys()|after.keys() if before.get(n)!=after.get(n)],flush=True)
elf=q.link(targets);old=(root/'conker/build/conker.us.elf').read_bytes();new=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x1834d8:0x183638]
code=inspect.getsource(q.strict_image).replace("sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","sizes={'func_15156028':352}");scope=dict(q.strict_image.__globals__);exec(code,scope);installed=candidate_sources()[1]
if installed:
 assert old==new, 'Installed ELF differs from actual-Make shadow'
 report={'strict_exclusions':0,'installed_image_identical':True}
else:report=scope['strict_image'](old,new,{'func_15156028':truth})
a,_,oa=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}==({'func_15156028'} if not installed else set())
protected=audit_layout(elf,root/'conker');assert protected['exact'] and protected['different_bytes']==0
print(json.dumps({'commands':len(commands),'functions':len(b),'image':report,'protected':protected}),flush=True)
