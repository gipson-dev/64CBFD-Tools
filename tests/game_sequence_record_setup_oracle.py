"""Independent record-group reference with bounded providers and deterministic arenas."""
import itertools

from tools.experiments import game_sequence_record_setup as source
from tools.tests import game_sequence_state_reset_oracle as reset

put, read, signed, STACK = reset.put, reset.read, reset.signed, reset.STACK
MASK = 0xFFFFFFFF
ALLOC, ZERO, REQUEST, RESET, LOAD = 0x10003C40, reset.ZERO, 0x1501C730, 0x1501D044, 0x1501D1D4
SUM, COUNTER, MAXIMUM, FINALIZE, PROCESS = 0x1501CFF8, 0x1501CDC0, 0x1501CE54, 0x15022BA4, 0x15020388
HEADER, BUNDLE, ALT_HEADER, ALT_BUNDLE, ALT_RUNTIME, PAYLOAD, HEAP = 0x60000, 0x61000, 0x62000, 0x63000, 0x64000, 0x70000, 0x100000
ENABLED, FALLBACK, PREFERRED, AUXILIARY, RUNTIME = 0x800C35C8, 0x800C35D0, 0x800C35D8, 0x800C35E0, 0x800C3A50
COUNTS, RESOURCE, STATUS = 0x800C363A, 0x800C3668, 0x800C35EA
TAIL = ((0x15022234,1),(0x15022248,1),(0x1501E81C,2),(0x150242F8,2),
    (0x1501EC38,1),(0x15022848,1),(0x15022754,1),(0x15022528,1),(0x15020EC4,1),(0x1501DAAC,1))
ARITIES = {ALLOC:4,ZERO:2,REQUEST:5,RESET:1,LOAD:3,SUM:1,COUNTER:1,MAXIMUM:1,FINALIZE:1,PROCESS:2,
    0x150238D0:0,**dict(TAIL),**{0x151FF000+i*4:4 for i in range(4)}}
WORD_PATTERNS = ((8,0,16), (0x80008,7,24), (0x80000000,8,0), (0xFFFFFFFF,0,0))
SNAPSHOT_LANES = [(base+i*4,4) for base in (RESOURCE,ENABLED,FALLBACK,PREFERRED,AUXILIARY,RUNTIME,0x800C35F0,0x800C3958)
    for i in range(2)] + [(base+i,1) for base in (STATUS,COUNTS) for i in range(2)] + [
    (0x800C35C4,1),(0x800C35C5,1),(0x800C3C90,1),(0x800C3C94,4),(0x800C3D50,4),(0x800C3638,1),
    (BUNDLE,4),*( (HEADER+i*2,2) for i in range(4))]


def snapshot(memory): return tuple(read(memory,at,width) for at,width in SNAPSHOT_LANES)


def public(memory): return {a:v for a,v in memory.items() if not STACK - 0x600 <= a < STACK + 0x100}


def fixture(slot=0, state=0, gate=0, scene=37, fail=0, counts=(2,3,1,2), pattern=0, mode=0, total=3, hook=1, sequence=6):
    m = reset.fixture(slot)
    m.update({STACK+i:0xA5 for i in range(-0x600,0x100)})
    for base, length in ((HEADER,8),(BUNDLE,512),(ALT_HEADER,8),(ALT_BUNDLE,512),(ALT_RUNTIME,256),
            (0x800BE9F0,16),(0x800840FC,16),(0x800DBFF0,16)):
        m.update({base+i:0xA5 for i in range(length)})
    for p,n in ((HEADER,counts),(ALT_HEADER,(1,0,0,0))):
        for i,v in enumerate(n): put(m,p+i*2,v,2)
    for base,header in ((BUNDLE,HEADER),(ALT_BUNDLE,ALT_HEADER)):
        put(m,base,header);put(m,base+4,8)
        for i in range(1,64):
            put(m,base+i*8,PAYLOAD+i*256);put(m,base+i*8+4,WORD_PATTERNS[pattern][(i-1)%3])
    for i in range(4):put(m,0x800840FC+i*4,0x151FF000+i*4)
    put(m,0x800BE9F0,37);put(m,STATUS+slot,state,1);put(m,0x800C35C4,gate,1)
    args=(scene & MASK,sequence & MASK,slot,hook,0x12345678)
    return m,args,dict(fail=fail,mode=mode,total=total & MASK)


def cases():
    for slot,state,gate,scene in itertools.product((0,1),(0,1,2,255),(0,1,128),(37,0x12345678)):
        yield fixture(slot,state,gate,scene,mode=1)
    for slot,counts,mode,hook in itertools.product((0,1),((0,0,0,0),(1,0,0,0),(2,3,1,2),(3,1,3,1)),(0,2,4,8,16,32,63),(0,1,3)):
        yield fixture(slot,counts=counts,mode=mode,hook=hook)
    for slot,pattern,total in itertools.product((0,1),(1,2,3),(0,0x1234FFFF,0x80000001)):
        yield fixture(slot,counts=(1,1,1,1),pattern=pattern,total=total)
    for slot in (0,1):
        yield fixture(slot,fail=1);yield fixture(slot,state=2)
        yield fixture(slot,scene=0x12345678,sequence=0x7FFFFFFF,mode=1)
        yield fixture(slot,counts=(0,65535,65535,0),mode=64,hook=0)


class Providers:
    def __init__(self,memory,args,config):
        self.memory=dict(memory);self.args=args;self.config=config;self.calls=[];self.allocations=[];self.used=0
        self.numbers={};self.fired=[];self.snapshots=[];self.results=[];self.kind='opaque'

    def call(self,target,*args):
        args=tuple(n & MASK for n in args);self.calls.append((target,args))
        ordinal=self.numbers.get(target,0);self.numbers[target]=ordinal+1
        slot=self.args[2];mode=self.config['mode'];m=self.memory;result=0
        if target==ALLOC:
            size,tag,pool,flags=args
            if tag!=1 or pool or flags or size>0x100000:raise ValueError('Allocation outside the bounded research fixture')
            result=HEAP+((self.used+31)&~15);end=result-HEAP+size
            for at in range(result-16,result+size+16):m.setdefault(at,0xA5)
            self.used=end+16;self.allocations.append((result,size,self.kind))
            if ordinal==0 and mode&2:
                put(m,RESOURCE+slot*4,ALT_BUNDLE);put(m,BUNDLE,ALT_HEADER);self.fired.append('cached-bundle-header')
            if self.kind in ('items','scratch') and mode&4:
                put(m,RUNTIME+slot*4,ALT_RUNTIME);self.fired.append('runtime-reload')
            if mode&64 and self.kind in ('fallback','preferred'):
                put(m,HEADER+(2 if self.kind=='fallback' else 4),0,2);self.fired.append('wide-capacity')
        elif target==ZERO:
            address,size=args
            if size>0x20000 or not all(address+i in m for i in range(size)):raise ValueError('Unbounded bzero')
            for i in range(size):m[address+i]=0
        elif target==REQUEST:
            if mode&1:put(m,STATUS+slot,0 if read(m,STATUS+slot,1) else 2,1);self.fired.append('live-request-status')
        elif target==RESET:
            m,_,_=reset.reference(m,slot);self.memory=m
        elif target==LOAD:
            result=0 if self.config['fail'] else BUNDLE;put(m,RESOURCE+slot*4,result)
        elif target==SUM:result=self.config['total']
        elif target==FINALIZE and mode&8:
            put(m,COUNTS+slot,2,1);self.fired.append('late-count')
        elif target==PROCESS and ordinal==0 and mode&16:
            put(m,COUNTS+slot,1,1);self.fired.append('live-loop-count')
        elif target==0x15022248 and mode&32:
            put(m,COUNTS+slot,0,1);self.fired.append('empty-after-helper')
        elif 0x151FF000<=target<0x151FF010:
            if mode&8:put(m,COUNTS+slot,0,1);self.fired.append('hook-count')
        elif target not in ARITIES:raise ValueError('Unknown record setup provider: %X'%target)
        self.snapshots.append(snapshot(self.memory));self.results.append(result & MASK);return result & MASK


class Reference(Providers):
    def get(self,p,n=4):return read(self.memory,p,n)
    def put(self,p,v,n=4):put(self.memory,p,v&((1<<(n*8))-1),n)
    def allocate(self,size,kind):
        self.kind=kind;return self.call(ALLOC,size,1,0,0)
    def run(self):
        scene,sequence,slot,hook,parameter=self.args;slot_offset=slot*4;status=STATUS+slot
        state=self.get(status,1)
        if state==1 or self.get(0x800C35C4,1):return self
        self.put(0x800C3C90,hook,1);self.put(0x800C3C94,parameter)
        if scene!=self.get(0x800BE9F0):
            self.put(0x800C35C4,sequence+1,1);self.call(REQUEST,1,scene,0,0,0)
            self.put(0x800C35C5,0 if self.get(status,1) else 1,1);return self
        self.put(0x800C35E8+slot,sequence,1)
        if state!=2:self.put(0x800C35A8,self.get(0x800BE9F0),1);self.put(0x800C3C98,sequence,1)
        self.call(RESET,slot)
        if not self.call(LOAD,scene,sequence,slot):return self
        bundle=self.get(RESOURCE+slot_offset);header=self.get(bundle)
        en,fall,pref,aux,rt=(p+slot_offset for p in (ENABLED,FALLBACK,PREFERRED,AUXILIARY,RUNTIME))
        count=lambda field:self.get(header+field*2,2)
        self.put(en,self.allocate(count(0)*2,'enabled'))
        i=0
        while i<count(0):self.put(self.get(en)+i*2,self.get(bundle+(i+1)*8+4)>>3,2);i+=1
        size=max(count(1),count(0))*2;allocated=self.allocate(size,'fallback');self.put(fall,allocated);self.call(ZERO,allocated,size)
        size=max(count(2),count(0))*2;allocated=self.allocate(size,'preferred');self.put(pref,allocated);self.call(ZERO,allocated,size)
        self.put(aux,self.allocate(count(3)*4,'auxiliary'));self.put(rt,self.allocate(count(0)*64,'runtime'))
        i=0
        while i<count(0):
            entries=self.get(self.get(en)+i*2,2)
            if entries:
                allocated=self.allocate(entries*4,'items');self.put(self.get(rt)+i*64+4,allocated)
                allocated=self.allocate(0x194,'scratch');self.put(self.get(rt)+i*64+0x38,allocated)
            i+=1
        self.put(0x800C3958+slot_offset,self.allocate(count(0)*68,'records68'))
        i=0
        while i<count(0):
            allocated=self.allocate(16,'record16');self.put(0x800C3960+slot*120+i*4,allocated);i+=1
        i=0
        while i<count(0):
            for p in (pref,fall,en):self.put(self.get(p)+i*2,0,2)
            i+=1
        self.put(COUNTS+slot,count(0),1);cursor=1;i=0
        while i<count(0):
            self.put(self.get(en)+i*2,self.get(bundle+(i+1)*8+4)>>3,2)
            self.put(0x800C3868+slot*120+i*4,self.get(bundle+(i+1)*8));cursor+=1;i+=1
        self.put(0x800C35F0+slot_offset,self.get(bundle+cursor*8));cursor+=count(0)
        for field,cell,table in ((1,fall,0x800C3778),(2,pref,0x800C3688)):
            i=0
            while i<count(field):
                self.put(self.get(cell)+i*2,self.get(bundle+cursor*8+4)>>3,2)
                self.put(table+slot*120+i*4,self.get(bundle+cursor*8));cursor+=1;i+=1
        i=0
        while i<count(3):self.put(self.get(aux)+i*4,self.get(bundle+(cursor+i)*8));i+=1
        if hook:self.call(self.get(0x800840FC+hook*4),scene,sequence,slot,parameter)
        total=self.call(SUM,slot)&65535;self.put(0x800C3C9A,total,2)
        self.put(0x800C3D50,self.allocate(total*12,'output12'));self.put(0x800C35B0+slot_offset,0)
        for target in (COUNTER,MAXIMUM,FINALIZE):self.call(target,slot)
        i=0
        while i<self.get(COUNTS+slot,1):self.call(PROCESS,i,slot);i+=1
        self.call(0x150238D0);self.put(status,1,1);self.put(0x800C3638,1,1)
        self.call(0x15022234,slot);self.call(0x15022248,slot)
        if not self.get(COUNTS+slot,1):self.call(0x1501E81C,0,slot)
        self.call(0x150242F8,1,slot)
        for target in (0x1501EC38,0x15022848,0x15022754,0x15022528,0x15020EC4):self.call(target,slot)
        self.put(0x800DBFF4,4,1);self.call(0x1501DAAC,slot);return self


class SetupOracle(reset.machine.InitializeOracle):
    def __init__(self,words,memory,args,config,plan,phase=0,entry=source.ENTRY,helpers=None):
        super().__init__(words,memory,args,helpers or {},phase,entry=entry)
        self.provider=Providers(self.memory,args,config);self.provider.memory=self.memory;self.plan=plan

    def record_call(self,target):
        packet=self.arguments(ARITIES[target]);self.calls.append((target,packet));self.events.append(('CALL',target,packet))

    def hook(self,target):
        packet=self.calls[-1][1]
        if target==ALLOC:
            number=len(self.provider.allocations)
            if number>=len(self.plan):raise ValueError('Extra allocation')
            self.provider.kind=self.plan[number][2]
        result=self.provider.call(target,*packet);self.memory=self.provider.memory
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result
