"""Compare every raw/retail public access-fault prefix without PC/register claims."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_randomized_map_particle_emitter_150ec6b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
    raw=json.loads((out/'early-payload/words.json').read_text())
    retail=list(struct.unpack_from('>238I',(root/'conker/conker.us.bin').read_bytes(),0x119B60))
    count=0;rows=[]
    for case in(g.Case(accumulator=g.bits(0.),timestep=0),g.Case(accumulator=g.bits(2.25),mode=3,phase=8),
                g.Case(accumulator=g.bits(4.25),mode=8,allocation_mask=0),g.Case(accumulator=g.bits(4.25),mode=4)):
        full=[g.check(words,case)for words in(raw,retail)];assert full[0].all_accesses==full[1].all_accesses
        for cut in range(full[0].all_accesses):
            pair=[]
            for words in(raw,retail):
                m=g.Oracle(words,case);m.cut=cut
                try:m.run();raise AssertionError('Missing access cut')
                except AccessBoundary:pass
                pair.append((g.public(m.memory),m.calls,m.observations,m.fcsr,m.all_accesses))
            assert pair[0]==pair[1],(case,cut,'public prefix differs');count+=1
        rows.append({'case':str(case),'accesses':full[0].all_accesses})
    r={'access_fault_pairs':count,'cases':rows,'raw_public_memory_calls_and_FCSR_prefix_equal':True,
       'raw_PC_or_volatile_register_identity_claimed':False,'source_installed':packet.installed(),'matching_credit':0}
    (out/'faults.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='cases'}),flush=True)
    return r
