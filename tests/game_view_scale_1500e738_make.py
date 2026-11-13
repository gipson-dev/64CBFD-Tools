from pathlib import Path
import inspect,json
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.experiments import game_view_scale_1500e738_match as screen
root,out=screen.ROOT,screen.OUT;q.out=out;q.p.out=out
linker=out/'frozen/conker/build/conker.ld';linker.parent.mkdir(parents=True,exist_ok=True);linker.write_bytes((root/'conker/build/conker.ld').read_bytes())
code=inspect.getsource(q.actual_make).replace("==1\n return targets,commands", "==2\n return targets,commands");assert code!=inspect.getsource(q.actual_make);scope=dict(q.actual_make.__globals__);exec(code,scope)
owner='game_3BA70';name='func_1500E738';targets,commands=scope['actual_make']({owner:out/'variant-case1_default.c'});newobj=targets[owner]
oldobj=root/'conker/build/src/game_3BA70.c.o';assert same_functions(oldobj,newobj,(name,))==5
before,after=sections(oldobj),sections(newobj);different=sorted(n for n in before.keys()|after.keys() if before.get(n)!=after.get(n));assert '.rodata' not in before and '.rodata' not in after
elf=q.link(targets);old=(root/'conker/build/conker.us.elf').read_bytes();new=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x3BBE8:0x3BD40]
code=inspect.getsource(q.strict_image).replace("sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","sizes={'func_1500E738':344}")
scope=dict(q.strict_image.__globals__);exec(code,scope)
if screen.sources()[1]:
 assert old==new,'Installed ELF differs from actual-Make shadow'
 image={'strict_exclusions':0,'installed_image_identical':True}
else:image=scope['strict_image'](old,new,{name:truth})
a,_,oa=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}==({name} if not screen.sources()[1] else set())
protected=audit_layout(elf,root/'conker');assert protected['exact'] and protected['different_bytes']==0
report={'commands':len(commands),'owner_sections':different,'compiler_rodata_rebound_and_not_emitted':True,'functions':len(b),'image':image,'protected':protected};(out/'make-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
