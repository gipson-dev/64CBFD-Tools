from pathlib import Path
import inspect,json
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.experiments import game_cache_expiry_1517abb0_match as screen
root,out=screen.ROOT,screen.OUT;q.out=out;q.p.out=out
linker=out/'frozen/conker/build/conker.ld';linker.parent.mkdir(parents=True,exist_ok=True);linker.write_bytes((root/'conker/build/conker.ld').read_bytes())
owner='game/generated_1A8060';name='func_1517ABB0';targets,commands=q.actual_make({owner:out/'variant-split.c'});newobj=targets[owner]
assert same_functions(root/'conker/build/src/game/generated_1A8060.c.o',newobj,(name,))==1
elf=q.link(targets);old=(root/'conker/build/conker.us.elf').read_bytes();new=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x1A8060:0x1A81B0]
code=inspect.getsource(q.strict_image).replace("sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","sizes={'func_1517ABB0':336}")
scope=dict(q.strict_image.__globals__);exec(code,scope)
if screen.sources()[1]:
 assert old==new,'Installed ELF differs from actual-Make shadow'
 image={'strict_exclusions':0,'installed_image_identical':True}
else:image=scope['strict_image'](old,new,{name:truth})
a,_,oa=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}==({name} if not screen.sources()[1] else set())
protected=audit_layout(elf,root/'conker');assert protected['exact'] and protected['different_bytes']==0
report={'commands':len(commands),'functions':len(b),'image':image,'protected':protected}
(out/'make-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
