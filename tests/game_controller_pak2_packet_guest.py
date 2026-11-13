"""Private independent request-packet model; models address CRC as a provider."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_effect_position_payload import complete

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-controller-pak2-durable'
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
PIF=symbols['__osPfsPifRam'];CRC=symbols['__osContAddressCrc'];BUFFER=0x300000
@dataclass(frozen=True)
class Case:
    kind:str;channel:int;address:int;phase:int=0
def crc(value):
    value &= 65535;v=0
    for _ in range(16):
        xor=21 if v&16 else 0
        v=(((v<<1)&255)|(1 if value&1024 else 0))^xor
        value=(value<<1)&65535
    return v&31
def fixture(c):
    m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
    for base,size in ((PIF-8,144),(BUFFER-8,64)):
        m.update({base+i:(i*29+0x35)&255 for i in range(size)})
    return m
class Machine(FactoryOracle):
    def __init__(self,w,c,m):
        self.kind=c.kind
        entry=symbols['__osPackRam'+c.kind.capitalize()+'Data2']
        super().__init__(w,m,c,entry=entry,s=symbols,arguments=(c.channel&0xffffffff,c.address,BUFFER))
    def execute(self,word):
        op,rs,rt=word>>26,word>>21&31,word>>16&31
        if op not in (34,38,42,46):return super().execute(word)
        self.own_instruction=True;self.dispatched_word=word
        try:
            at=(self.r[rs]+(((word&65535)^32768)-32768))&0xffffffff;k=at&3;n=4-k if op in (34,42) else k+1
            if op==34:self.r[rt]=(self.get(at,n)<<((4-n)*8))|(self.r[rt]&((1<<((4-n)*8))-1))
            elif op==38:self.r[rt]=(self.r[rt]&~((1<<(n*8))-1))|self.get(at-n+1,n)
            elif op==42:self.put(at,self.r[rt]>>((4-n)*8),n)
            else:self.put(at-n+1,self.r[rt]&((1<<(n*8))-1),n)
            self.r[0]=0
        finally:self.own_instruction=False
    def record_call(self,t):
        assert t==CRC;self.calls.append((t,tuple(self.arguments(1))))
    def hook(self,t):
        v=crc(self.calls[-1][1][0])
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.r[2]=v
def reference(m,c):
    m=dict(m); data=[m[BUFFER+i] for i in range(32)] if c.kind=='write' else [255]*32
    for i in range(64):m[PIF+i]=0
    put(m,PIF+60,1)
    offset=max(c.channel,0);header=[255,35 if c.kind=='write' else 3,1 if c.kind=='write' else 33,3 if c.kind=='write' else 2]
    addr=((c.address&65535)<<5|crc(c.address))&65535
    packet=header+[addr>>8,addr&255]+data+[255,m[STACK-5]]
    for i,value in enumerate(packet):m[PIF+offset+i]=value
    m[PIF+offset+40]=254
    return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512}
def main():
    cases=cuts=0
    for kind in ('read','write'):
        name='__osPackRam'+kind.capitalize()+'Data2';owner='generated_contram'+kind+'2'
        paths=(out/(name+'-retail.o'),out/(owner+'-after.o'),out/(owner+'-generated.o'),out/(owner+'-generic.o'))
        programs=[bound_blob(*payload(p,name),symbols) for p in paths]
        assert all(p==programs[0] for p in programs)
        for channel,address in itertools.product((-1,0,1,2,3,7,20),(0,1,6,7,0x1234,0xffff,0x12345678)):
            c=Case(kind,channel,address);initial=fixture(c);expected=reference(initial,c)
            for program in programs:
                result=Machine(program,c,initial.copy()).run()
                public={a:b for a,b in result.memory.items() if not STACK-512<=a<STACK+512}
                assert public==expected,(c,[(hex(a),public.get(a),expected.get(a)) for a in expected if public.get(a)!=expected.get(a)][:8])
                assert result.calls==[(CRC,(address&65535,))],(c,result.calls)
            cases+=1
        c=Case(kind,3,0x1234);initial=fixture(c)
        good=Machine(programs[0],c,initial.copy()).run()
        for cut in range(good.all_accesses):
            results=[]
            for program in programs:
                m=Machine(program,c,initial.copy());m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('ineffective cut',c,cut))
                results.append(m)
            for m in results[1:]:assert complete(m)==complete(results[0]) and m.trace==results[0].trace,(c,cut)
            cuts+=1
    report={'cases':cases,'fault_prefixes':cuts,'streams':4,'modeled_crc_provider':True,'retail_padding_byte_preserved':True}
    (out/'packet-guest.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
if __name__=='__main__':main()
