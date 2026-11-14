"""Reproduce the pre-install pointer-list validator qualification.

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
out=root/'conker/build/game-pointer-list-validation-15114f44-screen'
manifest=out/'production-baseline/fingerprints.json'
if hashlib.sha256(manifest.read_bytes()).hexdigest()!='00f6d7c8f8c605fc8c64f348032568c85e6c6219b4b4e47adf0c1c71c78b40c5':raise ValueError('baseline manifest changed')
record=json.loads(manifest.read_text())
for name,want in record['inputs'].items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=want:raise ValueError('qualification input changed: '+name)
old='s32 func_15114F44() {\n    return 0;\n}'
candidate='extern u32 *D_800DBDD8[];\nextern s32 D_800DBE18[];\nextern s32 D_800DBE20[];\nextern s32 D_8003C8E0, D_800DBF9C, D_800DBFA0, D_800DBFA4;\nvoid func_150AD770(void);\n/* Check two pointer lists in selected modes and publish the supplied values. */\nvoid func_15114F44(s32 a, s32 b, s32 c) {\n    s32 *counts;\n    u32 **lists;\n    s32 count, index;\n    u32 *entry, x, y, z;\n    if (D_800BE9F0 == 0x12 || D_800BE9F0 == 0x36 || D_800BE9F0 == 0x13) {\n        lists = D_800DBDD8;\n        counts = D_800DBE18;\n        do {\n            count = *counts;\n            entry = *lists;\n            for (index = 0; index < count; index++, entry += 3) {\n                x = entry[0];\n                if ((x & 0xF0000000) != 0x80000000 ||\n                    ((y = entry[1]) & 0xF0000000) != 0x80000000 ||\n                    ((z = entry[2]) & 0xF0000000) != 0x80000000 ||\n                    (x & 3) || (y & 3) || (z & 3)) {\n                    D_8003C8E0 = 0x0C00005A;\n                    func_150AD770();\n                    count = *counts;\n                }\n            }\n            counts++;\n            lists++;\n        } while ((u32)counts != (u32)D_800DBE20);\n        D_800DBF9C = a;\n        D_800DBFA0 = b;\n        D_800DBFA4 = c;\n    }\n}'
owner=(root/'conker/src/game/generated_13D350.c').read_text();assert owner.count(old)==1
baseline,bd=compile_owner(root,out,owner,'baseline');selected,sd=compile_owner(root,out,owner.replace(old,candidate),'selected')
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
words=bound_blob(*payload(selected,'func_15114F44'),symbols);truth=struct.unpack_from('>89I',(root/'conker/conker.us.bin').read_bytes(),0x1423f4)
assert len(words)==89 and sum(a==b for a,b in zip(words,truth))==82 and same_functions(baseline,selected,('func_15114F44',))==33 and normalized_pools(baseline)==normalized_pools(selected) and bd==sd==''
assert hashlib.sha256((out/'selected.c').read_bytes()).hexdigest()==record['source_after']
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
for name in ('guard','behavior','alias_fault','gate','caller','native','controls','padder','image'):
 subprocess.run([sys.executable,'-m','tools.tests.game_pointer_list_15114f44_'+name],cwd=root,env=env,check=True)
assert hashlib.sha256((out/'proposed-guards.csv').read_bytes()).hexdigest()==record['guards_after']
print('pointer list private qualification passed; candidate remains uncredited',flush=True)
