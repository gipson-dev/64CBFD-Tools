from pathlib import Path
import struct,sys
from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as out
from tools.tests import game_angular_trail_factory_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
lookup={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
def words(path):
 raw,refs=payload(path,'func_15153F18');return bound_blob(raw,refs,{n:lookup[n] for rows in refs.values() for _,n in rows})
truth=struct.unpack_from('>168I',(root/'conker/conker.us.bin').read_bytes(),g.ROM);padded=words(out/'durable-helper-padded.o');raw=words(out/'durable-helper-after.o');assert tuple(padded)==truth
symbols={name:lookup[name] for name in ('func_150ADA20','func_150ADA68','func_15143794','func_151DA6F8','D_800A6000')}
cases=0
for i in range(256):
 c=g.Case(seed=i%8,mutation=(i//8)%8,phase=(i%2)*8,channel=i);initial=g.fixture(c,symbols);expected=g.reference(initial,c,symbols)
 a,b,d=[g.Machine(code,initial,c,g.ENTRY,symbols).run() for code in (truth,padded,raw)]
 assert g.full_state(a)==g.full_state(b) and g.semantic_state(a)==g.semantic_state(d),c
 mem,calls,packets,integers,reals,submits=expected
 assert g.public(a.memory,c)==g.public(mem,c) and g.normalize_calls(a)==g.normalize_expected(calls,symbols)
 assert g.normalize_payloads(a.payloads)==g.normalize_payloads(packets) and (a.rng_i,a.rng_f,a.submits)==(integers,reals,submits)
 cases+=1
print('trail helper:',cases,'guest cases against independent reference; retail/padded state and raw public behavior agree')
