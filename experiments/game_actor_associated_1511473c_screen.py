"""Reproduce the pre-install actor-associated updater qualification.

Requires the retained fingerprinted production baseline; it is not an installed
regression test and does not itself grant a match.
"""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-actor-associated-update-1511473c-screen'
manifest=out/'production-baseline/fingerprints.json'
if hashlib.sha256(manifest.read_bytes()).hexdigest()!='53b695908c11ed951d1b7787d8765e3c9e715f54aea7d32e5f9a02857a0463f0':raise ValueError('baseline manifest changed')
record=json.loads(manifest.read_text())
for name,want in record['inputs'].items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=want:raise ValueError('qualification input changed: '+name)
old='s32 func_1511473C() {\n    return 0;\n}'
candidate='extern f32 D_800A2F60;\nextern u8 D_800CC2D0[];\nextern u16 D_800CBDA0[];\n/* Update actor fields and a running halfword from an indexed record. */\nvoid func_1511473C(u8 *actor, s32 index) {\n    u32 value;\n    if (actor != 0 && index < D_800DBEF0) {\n        func_15114348(index, actor + 0x14, actor + 0x18, actor + 0x1c);\n        value = (u32)(*(f32 *)((u32)D_800DBEF4 + (u32)index * 0xa0 + 0x64) * D_800A2F60 + *(u16 *)(actor + 0x76));\n        *(u16 *)(actor + 0x76) = value;\n        if (actor[0x137] != 0 && (u32)index + 1 == D_800CBDA0[(s32)((u32)actor - (u32)D_800CC2D0) / 0x32c]) {\n            *(u16 *)(actor + 0x7a) = value;\n        }\n    }\n}'
owner=(root/'conker/src/game/generated_13D350.c').read_text();assert owner.count(old)==1
baseline,bd=compile_owner(root,out,owner,'baseline');selected,sd=compile_owner(root,out,owner.replace(old,candidate),'selected')
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
words=bound_blob(*payload(selected,'func_1511473C'),symbols);truth=struct.unpack_from('>91I',(root/'conker/conker.us.bin').read_bytes(),0x141bec)
assert len(words)==91 and sum(a==b for a,b in zip(words,truth))==58 and same_functions(baseline,selected,('func_1511473C',))==33 and normalized_pools(baseline)==normalized_pools(selected) and bd==sd==''
assert hashlib.sha256((out/'selected.c').read_bytes()).hexdigest()==record['source_after']
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
for name in ('guard','behavior','alias','global_mutation','extended','caller','native','controls','padder','image'):
 subprocess.run([sys.executable,'-m','tools.tests.game_actor_associated_1511473c_'+name],cwd=root,env=env,check=True)
assert hashlib.sha256((out/'proposed-guards.csv').read_bytes()).hexdigest()==record['guards_after']
print('actor associated private qualification passed; candidate remains uncredited',flush=True)
