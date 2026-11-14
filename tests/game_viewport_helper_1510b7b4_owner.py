from pathlib import Path
import re,struct,hashlib,json
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows,same_functions
from tools.tests.game_owner_pool import normalized_pools
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-viewport-helper-shape-screen';ownerpath=root/'conker/src/game/generated_138520.c';owner=ownerpath.read_text();pattern=r'Gfx \*func_1510B7B4\([^;{}]+\) \{\n.*?\n\}';old=re.search(pattern,owner,re.S).group(0);candidate=old.replace('*(u16 *) (D_800BE628 + arg1 * 0x180 + 0xB8)', '*(u16 *)(((u8 (*)[0x180])D_800BE628)[arg1] + 0xB8)').replace('(u32) D_800BE628 + arg1 * 0x180 +', '(u32) D_800BE628 + (((u32)arg1 * 3U) << 7) +');assert candidate!=old;assert owner.count(old)==1
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};truth=struct.unpack_from('>105I',(root/'conker/conker.us.bin').read_bytes(),0x138c64)
b,bd=compile_owner(root,out,owner,'owner-baseline');a,ad=compile_owner(root,out,owner.replace(old,candidate),'owner-candidate');ws=bound_blob(*payload(a,'func_1510B7B4'),symbols);neighbors=same_functions(b,a,('func_1510B7B4',));assert len(ws)==105 and sum(x==y for x,y in zip(ws,truth))==81 and neighbors==13 and normalized_pools(b)==normalized_pools(a) and bd==ad=='';print(json.dumps({'words':len(ws),'same':sum(a==b for a,b in zip(ws,truth)),'neighbors':neighbors,'pool':normalized_pools(b)==normalized_pools(a),'diagnostics':bd==ad,'owner_hash':hashlib.sha256(ownerpath.read_bytes()).hexdigest()}),flush=True)
