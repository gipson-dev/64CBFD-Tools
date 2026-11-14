"""Uncredited real-Make and independent strict whole-ELF screen."""
from pathlib import Path
import hashlib,inspect,json,os,shutil
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-height-emitter-150e971c-durable';q.out=q.p.out=out
fingerprints={'conker.ld':'6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5',
              'conker.us.elf':'2efc0f036d1106ada19a8fc43da944c462029547123c1b249976dfa79cc02e33'}
frozen=out/'frozen/conker/build';frozen.mkdir(parents=True,exist_ok=True)
for name,digest in fingerprints.items():
 dest=frozen/name
 if not dest.exists():shutil.copyfile(root/'conker/build'/name,dest)
 if hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:raise ValueError('Frozen input changed: '+name)
 if hashlib.sha256((root/'conker/build'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Live input changed: '+name)
assert hashlib.sha256((root/'conker/build/src/game/generated_113D60.c.o').read_bytes()).hexdigest()=='6d1e875d68fed15b0ccfa1489cae85db122be7a9a584b5457d8b80b530c680b6'
targets,commands=q.actual_make({'game/generated_113D60':out/'snapshot.c'})
target=targets['game/generated_113D60'];base=root/'conker/build/src/game/generated_113D60.c.o'
assert same_functions(base,target,('func_150E971C',))==28
elf=q.link(targets);before=(frozen/'conker.us.elf').read_bytes();after=elf.read_bytes();truth=(root/'conker/conker.us.bin').read_bytes()[0x116bcc:0x116d38]
code=inspect.getsource(q.strict_image);needle="sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}";assert code.count(needle)==1
scope=dict(q.strict_image.__globals__);exec(code.replace(needle,"sizes={'func_150E971C':364}"),scope)
image=scope['strict_image'](before,after,{'func_150E971C':truth});assert image=={'changed_bytes':270,'metadata_groups':[],'strict_exclusions':0}
a,_,oa=load_elf_functions(str(frozen/'conker.us.elf'),'mips-linux-gnu-objdump');b,_,ob=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
assert a.keys()==b.keys() and oa==ob and {n for n in a if a[n]!=b[n]}=={'func_150E971C'}
data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
report={'commands':len(commands),'owner_neighbors':28,'functions':len(a),'all_addresses_fixed':True,'image':image,'protected_data':data,'uncredited':True}
(out/'image-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
