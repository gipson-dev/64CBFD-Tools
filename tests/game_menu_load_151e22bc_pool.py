"""Test the two adjacent retail jump tables without changing production files."""
from pathlib import Path
import json,struct,subprocess
from tools import pad_generated_object as pg
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable';conker=root/'conker';name='func_151E22BC'
symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
assert symbols['jtbl_800AB994']==0x800ab994 and symbols['jtbl_800AB9BC']==0x800ab9bc
def pad(obj,base,label,guards):
    asm=out/(label+'.s');compiled=out/(label+'.o')
    text=pg.emit_padded_assembly(obj,conker/'asm/20AE20.s',filename='generated_20AE20',
       word_patches_path=guards,rodata_symbol=base)
    asm.write_text(text)
    argv=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(compiled.relative_to(conker)),str(asm.relative_to(conker))]
    p=subprocess.run(argv,cwd=conker,capture_output=True,text=True);assert not p.returncode,p.stderr
    return compiled
before=pad(out/'before.o','jtbl_800AB9BC','before-padded',out/'baseline-guards.csv')
after=pad(out/'alias-00.o','jtbl_800AB994','shape-padded',out/'proposed-guards.csv')
_,fa,_=parse_object(before);_,fb,_=parse_object(after);assert fa.keys()==fb.keys()
changed=[]
for n in sorted(set(fa)-{name}):
    a=bound_blob(*payload(before,n),symbols);b=bound_blob(*payload(after,n),symbols)
    if a!=b:changed.append(n)
report={'neighbors':len(fa)-1,'changed_linked_neighbor_functions':changed,
        'old_pool_base':'0x800AB9BC','new_pool_base':'0x800AB994','pool_delta':40,
        'target_match_not_assessed_by_this_check':True,'production_mutated_by_check':False}
(out/'pool-rebase-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
assert not changed,changed
