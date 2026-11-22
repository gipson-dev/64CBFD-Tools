"""Connect both original RNGs, the original effect factory and original memcpy."""
from pathlib import Path
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_randomized_map_particle_emitter_150ec6b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
SEED=0x800885B0;FACTOR=0x8009F740;ALLOCATE=0x15167A68
PROVIDERS=((g.FRNG,0xDAF18,25),(g.RNG,0xDAED0,18),(g.FACTORY,0x15D730,61),(g.COPY,0x22EC0,11))
@lru_cache(maxsize=1)
def inputs():
    rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();code={}
    for target,offset,n in PROVIDERS:
        blob=rom[offset:offset+4*n];at=elf_slot_offset(elf,target,4*n);assert elf[at:at+4*n]==blob
        code.update(zip(range(target,target+4*n,4),struct.unpack('>%dI'%n,blob)))
    factor=struct.unpack_from('>I',elf,elf_slot_offset(elf,FACTOR,4))[0];assert factor==0x37800080
    return code,factor
class Connected(g.Oracle):
    def __init__(self,words,c,seed):
        code,factor=inputs();super().__init__(words,c,connected=code)
        g.put(self.memory,SEED,seed,8);g.put(self.memory,FACTOR,factor)
        self.initial=dict(self.memory);self.seeds=[];self.leaves=[];self.internal_copies=[]
    def execute(self,w):
        op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        inside=g.RNG<=self.current_pc<g.RNG+72 or g.FRNG<=self.current_pc<g.FRNG+100
        if op in(55,63):
            prior=self.own_instruction;self.own_instruction=True
            try:
                at=g.u32(self.r[rs]+((w&65535)^32768)-32768);assert at%8==0
                if op==55:self.r[rt]=self.get(at,8)
                else:self.put(at,self.r[rt],8)
            finally:self.own_instruction=prior
        elif op==0 and fn in(56,58,60,62,63):
            value=self.r[rt]&((1<<64)-1)
            if fn in(56,60):value<<=sh+(32 if fn==60 else 0)
            elif fn in(58,62):value>>=sh+(32 if fn==62 else 0)
            else:value=(value if value<1<<63 else value-(1<<64))>>(sh+32)
            self.r[rd]=value&((1<<64)-1)
        elif op==0 and fn in(37,38)and inside:
            self.r[rd]=(self.r[rs]|self.r[rt])if fn==37 else(self.r[rs]^self.r[rt])
        elif op==0 and fn==27:
            left,right=self.r[rs]&0xFFFFFFFF,self.r[rt]&0xFFFFFFFF;assert right
            self.lo,self.hi=left//right,left%right
        else:
            before=self.r[:];super().execute(w)
            if inside:
                dest=rt if op in(9,12,13,15,35)else rd if op==0 else None
                for i,value in enumerate(before):
                    if i!=dest and value>0xFFFFFFFF:self.r[i]=value
        self.r[0]=0
    def record_call(self,target):
        if target==ALLOCATE:
            self.leaves.append(tuple(map(g.u32,self.arguments(6))));return
        if target==g.COPY and self.arguments(3)[2]==112:
            self.internal_copies.append(tuple(map(g.u32,self.arguments(3))));return
        super().record_call(target)
        if target in(g.RNG,g.FRNG):self.seeds.append(g.read(self.memory,SEED,8))
    def hook(self,target):
        assert target==ALLOCATE
        ordinal=self.counts[g.FACTORY];args=self.calls[-1][1]
        assert self.leaves[-1]==(43,args[5],184,1,args[4],1)
        self.clobber(g.OUTPUT+192*(ordinal-1)if self.c.allocation_mask&(1<<(ordinal-1))else 0)
def draws(seed,rm):
    pattern=(g.FRNG,)+(g.RNG,g.RNG,g.FRNG,g.FRNG,g.FRNG,g.RNG,g.RNG,g.RNG,g.RNG,g.FRNG)*8
    floats=[];integers=[];flags=[];value=seed
    for target in pattern:
        value=next_seed(value)
        if target==g.RNG:integers.append(value&0xFFFFFFFF)
        else:
            draw,status=g.fp.arithmetic(g.bits(float(value&65535)),0x37800080,2,rm)
            floats.append(draw);flags.append(status)
    return tuple(floats),tuple(integers),tuple(flags)
def main():
    rom=(root/'conker/conker.us.bin').read_bytes()
    streams=(json.loads((out/'early-payload/words.json').read_text()),list(struct.unpack_from('>238I',rom,0x119B60)))
    count=0;visits=set()
    for seed,accumulator,step,mask,phase,rm in itertools.product(SEEDS,(0.,2.25,4.25),(0.,.25),(0,0x55,0xFF),(0,8),range(4)):
        floats,integers,flags=draws(seed,rm)
        c=g.Case(accumulator=g.bits(accumulator),timestep=g.bits(step),float_draws=floats,integer_draws=integers,float_flags=flags,allocation_mask=mask,phase=phase,fcsr=rm)
        pair=[]
        for words in streams:
            m=Connected(words,c,seed).run();expected,calls,obs,fcsr=g.reference(m.initial,c)
            value=seed;seeds=[]
            for target,args in calls:
                if target in(g.RNG,g.FRNG):seeds.append(value);value=next_seed(value)
            g.put(expected,SEED,value,8)
            assert m.calls==calls and m.observations==obs,(c,'connected call boundary')
            assert g.public(m.memory)==g.public(expected),(c,'connected memory')
            assert m.fcsr==fcsr and m.seeds==seeds,(c,'connected FCSR/seed')
            assert len(m.internal_copies)==sum(target==g.COPY for target,args in calls)
            pair.append((g.public(m.memory),m.calls,m.observations,m.fcsr));visits.update(m.visits)
        assert pair[0]==pair[1];count+=1
    coverage={hex(target):sum(target+4*i in visits for i in range(n))for target,offset,n in PROVIDERS}
    assert coverage[hex(g.FRNG)]==25 and coverage[hex(g.RNG)]==18 and coverage[hex(g.COPY)]==11
    r={'cases_per_stream':count,'streams':2,'provider_executed_words':coverage,'original_factory_kind':0,
       'other_factory_modes_unqualified':True,'allocation_leaf_contracted':True,'independent_64bit_seed_reference':True,
       'factory_total_bytes':184,'definition_copy_bytes':112,'extra_copy_bytes':16,
       'source_installed':packet.installed(),'matching_credit':0}
    (out/'connected.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
