"""Reproduce the frozen pre-install owner-chain constructor qualification."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-owner-chain-create-150c0ac0-screen';manifest=out/'production-baseline/fingerprints.json'
if hashlib.sha256(manifest.read_bytes()).hexdigest()!='53d26efb54938aa3db8ee597b00de47b5af4ed35287884031339571f76817231':raise ValueError('baseline manifest changed')
record=json.loads(manifest.read_text())
for name,want in record['inputs'].items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=want:raise ValueError('qualification input changed: '+name)
old='s32 func_150C0AC0() {\n    return 0;\n}'
candidate='void *func_15167A68(s32, s32, s32, s32, u8, u8);\nvoid *memcpy(void *, const void *, u32);\n/* Allocate an owner record and initialize its free-entry chain. */\nu8 *func_150C0AC0(u8 *descriptor, u8 slot, s32 context) {\n    /* Retain the allocation size and result in the retail stack order. */\n    struct { s32 size; u8 *result; } allocation;\n    u8 *position;\n    s16 index;\n    allocation.size = *(s16 *)(descriptor + 0x14) * 8 + 0x48;\n    if (!(descriptor[0x18] & 2)) {\n        if (!*(u32 **)(descriptor + 8)) return 0;\n        if (!**(u32 **)(descriptor + 8)) return 0;\n    }\n    allocation.result = func_15167A68(0x25, context, allocation.size, 1, slot, 1);\n    if (!allocation.result) return 0;\n    memcpy(allocation.result + 0x18, descriptor, 0x1c);\n    *(u8 **)(allocation.result + 0x40) = allocation.result + 0x48;\n    if (descriptor[0x18] & 2) {\n        position = *(u8 **)(allocation.result + 0x18);\n        *(f32 *)(allocation.result + 0x34) = *(f32 *)position;\n        *(f32 *)(allocation.result + 0x38) = *(f32 *)(position + 8);\n    } else {\n        position = *(u8 **)(allocation.result + 0x20);\n        *(f32 *)(allocation.result + 0x34) = *(f32 *)(position + 0x14);\n        *(f32 *)(allocation.result + 0x38) = *(f32 *)(position + 0x1c);\n    }\n    *(f32 *)(allocation.result + 0x3c) = 0.0f;\n    *(s16 *)(allocation.result + 0x44) = -1;\n    *(s16 *)(allocation.result + 0x46) = 0;\n    for (index = 0; index < *(s16 *)(descriptor + 0x14) - 1; index++) {\n        *(s16 *)(*(u8 **)(allocation.result + 0x40) + index * 8 + 4) = index + 1;\n    }\n    *(s16 *)(*(u8 **)(allocation.result + 0x40) + *(s16 *)(descriptor + 0x14) * 8 - 4) = -1;\n    *(s32 *)(allocation.result + 0x10) = 1;\n    *(s32 *)(allocation.result + 0x14) = 0;\n    return allocation.result;\n}'
owner=(root/'conker/src/game/generated_EDE60.c').read_text();assert owner.count(old)==1
baseline,bd=compile_owner(root,out,owner,'baseline');selected,sd=compile_owner(root,out,owner.replace(old,candidate),'selected')
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
words=bound_blob(*payload(selected,'func_150C0AC0'),symbols);truth=struct.unpack_from('>94I',(root/'conker/conker.us.bin').read_bytes(),0xedf70)
assert len(words)==94 and tuple(words)==truth and same_functions(baseline,selected,('func_150C0AC0',))==6 and normalized_pools(baseline)==normalized_pools(selected)
assert bd.replace('baseline.c','owner.c')==sd.replace('selected.c','owner.c')
assert hashlib.sha256((out/'selected.c').read_bytes()).hexdigest()==record['source_after']
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
for name in ('guard','behavior','alias','stack_alias','memcpy_connected','fault','caller','native','controls','padder','image'):
 subprocess.run([sys.executable,'-m','tools.tests.game_owner_chain_create_150c0ac0_'+name],cwd=root,env=env,check=True)
assert hashlib.sha256((out/'proposed-guards.csv').read_bytes()).hexdigest()==record['guards_after']
print('owner chain private qualification passed; candidate remains uncredited',flush=True)
