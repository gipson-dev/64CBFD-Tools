"""Execute the actual owner Make recipe and independently audit the linked image."""
import inspect,json,shutil
from tools.experiments import game_script_node_acquire_1509b5ac_match as source
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions

root,out=source.ROOT,source.OUT
q.out=out;q.p.out=out
linker=out/'frozen/conker/build/conker.ld';linker.parent.mkdir(parents=True,exist_ok=True)
current=(root/'conker/build/conker.ld').read_bytes()
if linker.exists():assert linker.read_bytes()==current
else:linker.write_bytes(current)
targets,commands=q.actual_make({source.OWNER:out/'durable-after.c'})
oldobj=root/'conker/build/src/game_C8950.c.o';newobj=targets[source.OWNER]
assert same_functions(oldobj,newobj,(source.NAME,))==16
assert source.payload(newobj,source.NAME)==source.payload(out/'durable-retail.o',source.NAME)
elf=q.link(targets);old=(root/'conker/build/conker.us.elf').read_bytes();new=elf.read_bytes()
truth=(root/'conker/conker.us.bin').read_bytes()[0xC8A5C:0xC8BB4]
code=inspect.getsource(q.strict_image).replace("sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","sizes={'func_1509B5AC':344}").replace("r[2][2]==12", "r[2][2]==20")
scope=dict(q.strict_image.__globals__);exec(code,scope)
if source.sources()[1]:
 assert old==new,'Installed ELF differs from actual-Make shadow'
 report={'strict_exclusions':0,'installed_image_identical':True}
else:report=scope['strict_image'](old,new,{source.NAME:truth})
a,_,oa=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}==({source.NAME} if not source.sources()[1] else set())
protected=audit_layout(elf,root/'conker');assert protected['exact'] and protected['different_bytes']==0
print(json.dumps({'commands':len(commands),'functions':len(b),'image':report,'protected':protected}),flush=True)
