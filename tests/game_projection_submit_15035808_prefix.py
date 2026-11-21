"""Independent instruction-driven QUERY/distance transfer screen.

FP operations and status transitions are uninterpreted ordered effects. The
screen reports differences; it does not normalize streams or claim adoption.
Public reads are stable only until the opaque QUERY call. All 256 private and
incoming bytes are compared, including early-return argument-home stores.
"""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
import json,struct
from tools.tests import game_projection_submit_15035808_oracle as fixture
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_growth_curve_151a1fb4_proof as g
e=g.e
OUT=recovery.OUT

class State(g.State):
    def __init__(self):
        super().__init__('shared')
        self.r[4:8]=[('ARG',i)for i in range(4)]
        for i in range(4,10):self.store(('STACK',4*i),4,('ARG',i))
    def load(self,address,size,pool=b''):
        if e.tagged(address,'STACK'):
            off=address[1];assert size in(1,2,4)and off%size==0
            assert -216<=off and off+size<=40
            return g.join([self.mem.get(off+i,('PRIVATE_BYTE',off+i))for i in range(size)])
        e.plain(address);self.read_set[self.epoch,address,size]+=1
        return ('LOAD',address,size,self.epoch)
    def store(self,address,size,value):
        if e.tagged(address,'STACK'):
            off=address[1];assert size in(1,2,4)and off%size==0 and -216<=off and off+size<=40
            for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
        else:super().store(address,size,value)
    def frame(self):return tuple(self.load(('STACK',off),1)for off in range(-216,40))

class Program(g.Program):
    def __init__(self,words,terms):
        super().__init__(words,terms);self.entry=fixture.ENTRY
    def call(self,s,target):
        assert target in(fixture.QUERY,fixture.DISTANCE,fixture.QUEUE),hex(target)
        n=fixture.COUNTS[target];args=tuple(s.r[4:4+n]);ordinal=sum(s.calls.values());s.calls[target]+=1
        s.trace.append(('CALL',target,args,s.fcsr))
        s.epoch+=1
        for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
        for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
        for i in range(4):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
        s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',ordinal)
        s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)

def call_end(words,target):
    matches=[i*4+8 for i,w in enumerate(words)if w>>26==3 and (((fixture.ENTRY+i*4+4)&0xf0000000)|((w&0x3ffffff)<<2))==target]
    assert matches;return matches[0]

def run():
    original=struct.unpack_from('>345I',(ROOT/'conker/conker.us.bin').read_bytes(),0x62cb8)
    streams={'vector':OUT/'index-alias-shapes/ordinary-late.o',
        'integer':OUT/'refine-shapes/integer-deltas.o',
        'continued':OUT/'transfer-shapes/continued.o',
        'selected':recovery.WHERE/'candidate.o',
        'normalized':OUT/'private-normal-form.bin',
        'retained-matrix':recovery.WHERE/'candidate.o'}
    report={}
    for name,path in streams.items():
        if path.suffix=='.bin':raw=struct.unpack('>%dI'%(path.stat().st_size//4),path.read_bytes())
        else:
            raw,refs=payload(path,'func_15035808');raw=fixture.bind(raw,refs)
        terms=g.Terms()
        paths={};programs={}
        for side,words in(('raw',raw),('retail',original)):
            program=Program(words,terms);programs[side]=program
            paths[side]=program.paths(0,{call_end(words,fixture.QUEUE):'first-queue-return',-4:'return'},State())
        same=paths['raw'].keys()==paths['retail'].keys()
        r=dict(raw_paths=len(paths['raw']),retail_paths=len(paths['retail']),same_path_predicates=same,
            ordered_fp_differences=[],call_argument_differences=[],private_frame_differences=[])
        if same:
            for number,key in enumerate(paths['raw']):
                a,b=paths['raw'][key],paths['retail'][key]
                fp=lambda s:[v for v in s.trace if v[0]=='FP']
                calls=lambda s:[v for v in s.trace if v[0]=='CALL']
                if fp(a)!=fp(b):r['ordered_fp_differences'].append(dict(path=number,end=key[0],raw_operations=len(fp(a)),retail_operations=len(fp(b))))
                if calls(a)!=calls(b):r['call_argument_differences'].append(dict(path=number,end=key[0]))
                offsets=[i-216 for i,(x,y)in enumerate(zip(a.frame(),b.frame()))if x!=y]
                if offsets:r['private_frame_differences'].append(dict(path=number,end=key[0],offsets=offsets))
        else:
            r['only_raw']=[repr(k)[:1600]for k in paths['raw'].keys()-paths['retail'].keys()]
            r['only_retail']=[repr(k)[:1600]for k in paths['retail'].keys()-paths['raw'].keys()]
        r.update(ordered_FP_and_FCSR_observed=True,all_256_private_incoming_bytes_observed=True,matching_credit=0)
        report[name]=r
    (OUT/'prefix-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return report
