"""Independent cache model, retained output and live loader mutations, privately."""
import itertools,json,struct
from tools.experiments import game_resource_cache_15016850_candidates as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
CACHE,COUNT,TABLE,LIST,ALT,MARK=0x800BE590,0x800D2100,0x800D20FC,0x30000,0x50000,0x70000
IDS,HANDLES,LENGTH,HELPER=CACHE+8,CACHE+24,0x500,0x1502B7F0
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def fixture(sequence,response=0,mode=0,phase=0,count=None,alias=False):
    count=len(sequence)if count is None else count;n=max(8,count);m={STACK+i:(i*17+0x41)&255 for i in range(-512,512)}
    for p,size in((CACHE,LENGTH),(LIST,n*48),(ALT,n*48),(COUNT,1),(TABLE,4),(MARK,4)):
        for i in range(size):m[p+i]=0xa5
    for i in range(n):
        m[LIST+i*48+4]=sequence[i%len(sequence)]if sequence else 200
        m[ALT+i*48+4]=sequence[-1-i%len(sequence)]if sequence else 201
    for i in range(8):put(m,IDS+2*i,0xa500+i,2);put(m,HANDLES+4*i,0x90000000+i)
    put(m,TABLE,CACHE+4 if alias else LIST);put(m,COUNT,count,1)
    return m,(response,mode,phase,n)

def snapshot(m,args):
    response,mode,phase,n=args
    return(data(m,CACHE,LENGTH),data(m,LIST,n*48),data(m,ALT,n*48),read(m,COUNT,1),read(m,TABLE))

def effect(m,args,number,resource,output):
    response,mode,phase,n=args;write=True;value=0x60000+resource*16
    if response==1:value=0 if resource&1 else value
    elif response==2:write=number==1
    elif response==3:write=bool(number&1);value=0
    if write:put(m,output,value)
    if mode&1 and number==1:put(m,COUNT,min(n,6),1)
    if mode&2:put(m,TABLE,ALT if number&1 else LIST)
    if mode&4:put(m,CACHE,2,1);put(m,IDS,0x1201,2)
    if mode&8:m[read(m,TABLE)+4]^=0x55
    put(m,MARK,number)

def model(initial,args):
    m=dict(initial);home=STACK+args[2];output=home-16;put(m,CACHE,0,1);put(m,output,0);limit=read(m,COUNT,1);offset=0;calls=[];observations=[]
    while offset<limit*48:
        assert offset<256*48
        resource=read(m,read(m,TABLE)+offset+4,1);found=any(resource==read(m,IDS+i*2,2)for i in range(read(m,CACHE,1)))
        if not found:
            if resource<187:
                packet=(output,2,18,resource);calls.append((HELPER,packet));observations.append(snapshot(m,args))
                effect(m,args,len(calls),resource,output);limit=read(m,COUNT,1)
            value=read(m,output)
            if value:
                index=read(m,CACHE,1);put(m,HANDLES+index*4,value);put(m,IDS+index*2,resource,2);put(m,CACHE,(index+1)&255,1)
        offset+=48
    return m,calls,observations

def corpus():
    sequences=((),(1,),(1,1),(1,187),(187,1,188,1),(1,2,3,4,5),(186,187,255,186),(255,254),(1,2,1,3,1))
    for seq,response,mode,phase in itertools.product(sequences,range(4),range(16),(0,8)):
        yield(*fixture(seq,response,mode,phase),True)
    for count in range(256):yield(*fixture((1,),2,0,count=count),False)
    for mode,phase in itertools.product(range(16),(0,8)):yield(*fixture((1,187,2),2,mode,phase,alias=True),False)

class Oracle(FactoryOracle):
    def __init__(self,w,initial,args,entry=source.ENTRY,connected=None):
        self.cache_args=args;self.cache_observations=[]
        super().__init__(w,initial,Case(phase=args[2]),entry=entry,connected=connected,arguments=())
    def record_call(self,t):
        if t==source.ENTRY:return
        assert t==HELPER;packet=tuple(self.arguments(4));assert packet[0]==self.target_home-16
        self.calls.append((t,packet));self.events.append(('CALL',t,packet));self.cache_observations.append(snapshot(self.memory,self.cache_args))
    def hook(self,t):
        assert t==HELPER;packet=self.calls[-1][1];effect(self.memory,self.cache_args,len(self.calls),packet[3],packet[0])
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=0x87654321

def main():
    programs=[source.bound(*payload(source.OUT/n,source.NAME))for n in('retail.o','selected.o')];rows=list(corpus());seen=set();unchanged=0
    for initial,args,native in rows:
        want,calls,obs=model(initial,args)
        for w in programs:
            m=Oracle(w,initial,args).run();assert(public(m.memory),m.calls,m.cache_observations)==(public(want),calls,obs),args
        seen.update(Oracle(programs[0],initial,args).run().visits);unchanged+=not calls
    controls=[]
    for pc,old,new in((0x38,0xafa00050,0xafa10050),(0x24,0xafb1001c,0xafb0001c),(0xd4,0x02003825,0x00003825)):
        # The saved-register control is checked through the machine's return ABI.
        changed=programs[0][:];assert changed[pc//4]==old;changed[pc//4]=new;killed=False
        for initial,args,native in rows:
            want,calls,obs=model(initial,args)
            try:m=Oracle(changed,initial,args).run()
            except AssertionError:
                if pc!=0x24:raise
                killed=True;break
            if(public(m.memory),m.calls,m.cache_observations)!=(public(want),calls,obs):killed=True;break
        assert killed,hex(pc);controls.append(hex(pc))
    report=dict(cases=len(rows),streams=2,visited_retail_words=len(seen),cache_bytes=LENGTH,record_stride=48,all_count_bytes=256,alias_cases=32,public_and_helper_snapshots=True,effective_controls=controls,zero_helper_cases=unchanged,private=True,raw_fault_order_claimed=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
