"""Independent table provenance, protected targets and unchanged typed relay."""
from pathlib import Path
import os,struct
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
OFFSETS=(52,96,148,200,224,200,252,288)
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
def audit(before,after,original):
 old,new=map(normalized_pools,(before,after));a,x=old['.rodata'];b,y=new['.rodata'];assert a==bytes(48)and b==bytes(80);assert y[:9]==x and y[9:]==tuple((36+4*i,'func_1513137C',n)for i,n in enumerate(OFFSETS));assert old['.data']==new['.data']
 assert payload(before,'func_15131514')==payload(after,'func_15131514')and payload(before,'func_1513164C')==payload(after,'func_1513164C')
 raw,refs=payload(after,'func_1513137C');truth,truthrefs=payload(original,'func_1513137C');u,v=map(lambda b:list(struct.unpack('>102I',b)),(raw,truth));assert [i for i,(a,b)in enumerate(zip(u,v))if a!=b]==[10];assert(u[8],u[10],v[8],v[10])==(0x3c010000,0x8c2f0024,0x3c010000,0x8c2f0000)
 assert refs=={32:[('R_MIPS_HI16','.rodata')],40:[('R_MIPS_LO16','.rodata')]}and truthrefs=={32:[('R_MIPS_HI16','jtbl_800A3800')],40:[('R_MIPS_LO16','jtbl_800A3800')]}
 labels={n:v[1]for _,n,v,_ in symbol_rows(original.read_bytes())if n.startswith('.L')and n.endswith('_game_data')};assert sorted(labels.values())==sorted(set(OFFSETS))
 rom=(ROOT/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>8I',rom,0x2482c0)==tuple(0x1513137c+n for n in OFFSETS);assert struct.unpack_from('>9I',rom,0x2482e0)==tuple(0x15131514+n for _,_,n in x)
 return dict(raw_pool_bytes_before=48,raw_pool_bytes_after=80,old_nine_entry_table_unchanged=True,new_eight_entry_table_offset=36,target_offsets=list(OFFSETS),seven_original_interior_labels_verified=True,all_non_address_instruction_words_identical=True,existing_color_and_typed_relay_raw_fixed=True,instruction_order_patches=0,normalizer_imported=False)
