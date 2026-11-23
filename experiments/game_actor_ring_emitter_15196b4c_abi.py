"""Independent ABI-only source recovery; unrecovered stubs earn no match credit."""
import hashlib,json
from tools.experiments import game_actor_ring_emitter_15196b4c_match as p
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_paired_ground_constructor_match import payload
r,o=p.ROOT,p.OUT
def recover(s):
 for name in p.MANIFEST['helper_names']:
  old='s32 '+name+'() {\n    return 0;\n}';assert s.count(old)==1
  s=s.replace(old,'/* Unrecovered sub-emitter body; only its observed two-pointer void ABI is restored. */\nvoid '+name+'(u8 *owner, f32 *point) {\n}')
 return s
def main():
 assert recover(p.MANIFEST['old_source'])==p.MANIFEST['abi_source'];where=o/'ABI-qualified';where.mkdir(exist_ok=True);before,bd=compile_owner(r,where,p.MANIFEST['old_source'],'before');after,ad=compile_owner(r,where,p.MANIFEST['abi_source'],'candidate');helpers=p.MANIFEST['helper_names'];assert same_functions(before,after,helpers)==67;assert same_functions(after,o/'selected-final/candidate.o',(p.FUNCTION,))==68;assert normalized_pools(before)==normalized_pools(after)==normalized_pools(o/'selected-final/candidate.o');assert diagnostic_rows(bd)==diagnostic_rows(ad);rows=[]
 for name in helpers:
  a,ar=payload(before,name);b,br=payload(after,name);assert not ar and not br and len(a)==12 and len(b)==16
  # g3's unused named parameter homes are compiler-generated ABI stores.
  # These four bodies are still placeholders, never normalized to retail.
  expected=bytes.fromhex('afa40000afa5000403e0000800000000');assert b==expected,(name,b.hex())
  rows.append(dict(function=name,old_words=3,new_words=4,new_code_hex=b.hex(),new_sha256=hashlib.sha256(b).hexdigest(),retail_byte_exact=False,additional_matching_credit=0))
 parent_name='conker/build/src/game/generated_174BF0.c.o';parent=o/'baseline'/parent_name
 if not parent.is_file():parent=r/parent_name
 assert hashlib.sha256(parent.read_bytes()).hexdigest()==p.MANIFEST['inputs'][parent_name];raw,refs=payload(parent,'func_15147740')
 from tools.experiments.game_actor_state_tick_integration import symbol_rows
 from tools.experiments.game_path_heading_turn_roles import bound_blob
 S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};rom=(r/'conker/conker.us.bin').read_bytes();assert bytes.fromhex(''.join(f'{w:08x}'for w in bound_blob(raw,refs,S)))==rom[0x174BF0:0x174D80]
 q=dict(helper_ABI_only=rows,all_67_ABI_reference_nonhelpers_fixed=True,all_68_candidate_nonparent_functions_equal_ABI_reference=True,other_66_neighbors_and_pools_fixed=True,diagnostics_equal=True,parent_100_words_literal_byte_exact=True,source_installed=p.installed(),matching_credit=0);(o/'ABI-qualified.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
