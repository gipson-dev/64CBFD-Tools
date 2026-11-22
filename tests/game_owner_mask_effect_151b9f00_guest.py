"""Owner masks, signed pointer-index division and dynamic copied tail."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
from tools.experiments import game_owner_mask_effect_151b9f00_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_camera_state_flags_151236d0_guest import static_reachable
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

ENTRY,SIZE,BASE,FLAGS,MODE=0x151B9F00,388,0x800CC2D0,0x800E0BCE,0x8008FD90
OUTPUT,MARK,FACTORY,COPY=0x50000,0x60000,0x1513B5E0,0x10022EC0
SYMS=dict(D_800CC2D0=BASE,D_800E0BCE=FLAGS,D_8008FD90=MODE,func_1513B5E0=FACTORY,memcpy=COPY)
u32=lambda value:value&0xFFFFFFFF

@dataclass(frozen=True)
class Case:
    delta:int=0
    mode:int=4
    flag:int=1
    priority:int=255
    outcome:int=1
    mutation:int=0
    tail:int=16
    null:int=0
    phase:int=0

def owner(case):return 0 if case.null else u32(BASE+case.delta)
def fixture(case):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-512,256)}
    for base,length in ((owner(case),96),(OUTPUT,512),(FLAGS-4,16),(MODE,4),(MARK,4)):
        memory.update({u32(base+i):(i*13+0x35)&255 for i in range(length)})
    if owner(case):memory[u32(owner(case)+0x3B)]=0x87
    memory[MODE]=case.mode&255
    for i in range(-4,12):memory[FLAGS+i]=case.flag&255
    return memory
def data(memory,address,count):return bytes(memory[u32(address+i)]for i in range(count))
def public(memory):return {a:b for a,b in memory.items()if not STACK-512<=a<STACK+256}
def effect(memory,case):
    put(memory,MARK,0x13579BDF)
    if case.mutation:
        memory[u32(owner(case)+0x3B)]^=0x55
        memory[MODE]=0
        memory[FLAGS]=memory[FLAGS+1]=0

def reference(initial,case,home=None,arguments=None):
    memory=dict(initial);home=STACK+case.phase if home is None else home
    p,priority,context=(owner(case),u32(case.priority),0x13579BDF)if arguments is None else arguments
    calls=[];observations=[]
    if not p:return public(memory),calls,0,observations
    header=home-72;descriptor=home-64
    put(memory,header,p);memory[header+4]=memory[u32(p+0x3B)]
    for at,value in ((0,2),(1,255),(2,3),(0x38,2),(0x39,255),(0x24,0),(0x25,0)):
        memory[descriptor+at]=value
    put(memory,descriptor+4,300,2)
    for at,value in ((8,1),(12,0x200205),(16,0x60600),(20,1),(24,54),(28,128),(32,32),(48,9),(52,429)):
        put(memory,descriptor+at,value)
    delta=((u32(p-BASE)^0x80000000)-0x80000000)
    index=abs(delta)//812*(-1 if delta<0 else 1)
    if index<2 and memory[FLAGS+index]:
        if memory[MODE]==2:memory[descriptor+0x39]=253
        elif memory[MODE]==4:memory[descriptor+0x39]=251 if index==0 else 247
    factory_args=(descriptor,1,8,priority&255,context)
    calls.append((FACTORY,factory_args));observations.append(('descriptor',data(memory,descriptor,60)))
    effect(memory,case);answer=OUTPUT if case.outcome else 0
    if answer:
        put(memory,answer+0x50,case.tail)
        destination=u32(answer+case.tail+0xF8);calls.append((COPY,(destination,header,8)))
        snapshot=data(memory,header,8);observations.append(('copy',snapshot))
        for i,value in enumerate(snapshot):memory[destination+i]=value
    return public(memory),calls,answer,observations

class Machine(FactoryOracle):
    def __init__(self,words,case,memory):
        self.c=case;self.observations=[]
        super().__init__(words,memory,case,entry=ENTRY,s=SYMS,arguments=(owner(case),u32(case.priority),0x13579BDF))
    def record_call(self,target):
        count={FACTORY:5,COPY:3}[target]
        args=tuple(self.arguments(count));self.calls.append((target,args));self.events.append(('CALL',target,args))
        self.observations.append(('descriptor',data(self.memory,args[0],60))if target==FACTORY else('copy',data(self.memory,args[1],args[2])))
    def hook(self,target):
        args=self.calls[-1][1]
        if target==FACTORY:
            effect(self.memory,self.c);result=OUTPUT if self.c.outcome else 0
            if result:put(self.memory,result+0x50,self.c.tail)
        else:
            snapshot=data(self.memory,args[1],args[2])
            for i,value in enumerate(snapshot):self.memory[u32(args[0]+i)]=value
            result=args[0]
        for i in range(5 if target==FACTORY else 4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for register in(1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(result)

def programs():
    paths=(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/generated_1E73B0.c.o')
    return[bound_blob(*payload(path,'func_151B9F00'),SYMS)for path in paths]
def state(machine):return(machine.memory,machine.r,machine.f,machine.hi,machine.lo,machine.condition,machine.trace,machine.calls,machine.observations,machine.current_pc,machine.delay_of)
def corpus():
    for mode in range(256):yield Case(mode=mode,delta=812*(mode%2),priority=mode)
    for delta,mode,flag,priority,outcome,mutation,tail,phase in itertools.product((-812,-1,0,1,811,812,1624,2436),(0,2,4,255),(0,255),(0,0x12340080,255),(0,1),(0,1),(0,32),(0,8)):
        yield Case(delta=delta,mode=mode,flag=flag,priority=priority,outcome=outcome,mutation=mutation,tail=tail,phase=phase)
    for priority in(0,255,0xFFFFFF80):yield Case(null=1,priority=priority)
def compare(streams,case):
    initial=fixture(case);wanted=reference(initial,case);machines=[]
    for words in streams:
        machine=Machine(words,case,dict(initial)).run()
        assert(public(machine.memory),machine.calls,machine.r[2],machine.observations)==wanted,('model',case)
        assert machine.r[29]==STACK+case.phase
        for register in(*range(16,24),30):assert machine.r[register]==machine.before[register]
        machines.append(machine)
    assert state(machines[0])==state(machines[1])==state(machines[2]),case
    return machines[0]
def run():
    streams=programs();assert streams[0]==streams[2]and streams[1]!=streams[0]
    coverage=set();count=0
    for case in corpus():
        machine=compare(streams,case);count+=1
        coverage.update((p-ENTRY)//4 for p in machine.visits if ENTRY<=p<ENTRY+SIZE)
    assert coverage==static_reachable(streams[0]),sorted(static_reachable(streams[0])-coverage)
    faults=0
    for case in(Case(),Case(delta=-812,mode=4),Case(null=1),Case(outcome=0,mutation=1)):
        full=compare(streams,case)
        for cut in range(full.all_accesses):
            states=[]
            for words in(streams[0],streams[2]):
                machine=Machine(words,case,fixture(case));machine.cut=cut
                try:machine.run();raise AssertionError('Missing access cut')
                except AccessBoundary:pass
                states.append(state(machine))
            assert states[0]==states[1];faults+=1
    report=dict(cases_per_stream=count,streams=['retail','raw C','normalized padded'],covered_words=len(coverage),unreachable_words=sorted(set(range(97))-coverage),complete_end_memory_registers_calls_and_accesses_equal=True,normalized_fault_prefixes=faults,fault_scope='Retail and normalized output. Raw scheduling deliberately differs at intermediate arithmetic states.',source_installed=packet.installed(),matching_credit=0)
    (out/'guest-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
if __name__=='__main__':run()
