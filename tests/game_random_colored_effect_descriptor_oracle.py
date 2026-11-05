"""Descriptor contract and connected original RNG, RGB selector and submitter."""
from dataclasses import dataclass
import itertools,math,struct
from tools.experiments import game_random_colored_effect_descriptor_match as source
from tools.experiments import game_random_colored_effect_descriptor_candidates as candidate
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
ACTOR,RANDOM,COLOR,SUBMIT,FACTORY=0x30000,0x150ADA20,0x151429E0,0x1518CA80,0x15167D84
SEED,TABLE,ASSET=0x800885B0,0x8008A160,0x8008CA4C
HELPERS=((COLOR,0x16FE90,31),(RANDOM,0xDAED0,18),(SUBMIT,0x1B9F30,138))
WORDS=(0,1,2,3,5,200,201,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF)
POSITIONS=((0xC1200000,0x3E800000,0x41A40000),(0xC7000080,0x80000000,0x46FFFF80),(0x7FC12345,0x7F800000,0xFF800000))
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
floating=lambda n:struct.unpack('>f',struct.pack('>I',u32(n)))[0]
bits=lambda f:struct.unpack('>I',struct.pack('>f',f))[0]

@dataclass(frozen=True)
class Case:
    randoms:tuple=(0,0,0,0,0,0,0)
    mode:int=0
    seed:int=0x123456789ABCDEF0
    position:int=0
    pattern:int=0
    mutation:int=0
    consumer:int=0
    phase:int=0
    actor:int=ACTOR

def symbols():return {'func_150ADA20':RANDOM,'func_151429E0':COLOR,'func_1518CA80':SUBMIT,'D_800885B0':SEED,'D_8008A160':TABLE,'D_8008CA4C':ASSET}
def packet(home):return home-0x50+0x1C
def data(m,p,n):return bytes(m[p+i]for i in range(n))

def fixture(rom,c=Case(),s=None):
    s=symbols()if s is None else s
    m={STACK+i:(i*17+165+c.pattern*31)&255 for i in range(-0x400,0x400)}
    m.update({c.actor+i:(i*29+123)&255 for i in range(0x180)})
    for i,value in enumerate(POSITIONS[c.position]):put(m,c.actor+0x34+i*4,value)
    m.update({s['D_8008A160']+i:(value if not c.pattern else (i*29+c.pattern*71)&255)for i,value in enumerate(rom[0x22EC20:0x22EC90])})
    put(m,s['D_800885B0'],c.seed,8);put(m,s['D_8008CA4C'],0x81234560);return m

def effect(m,c,s,number):
    if c.mutation&1 and number==0:
        for i,value in enumerate((0x7FC0ABCD,0x80000000,0x12345678)):put(m,c.actor+0x34+i*4,value)
    if c.mutation&2:
        for i in range(36,60):m[s['D_8008A160']+i]^=(number*13+17)&255

def consumer_packet(initial,payload,home,s):
    out=home-0x50-0x68+0x30;m=dict(initial)
    for off in range(52):m[0x70000+off]=payload[off]
    p=0x70000;alpha=read(m,p+0x2E,1)
    put(m,out,read(m,s['D_8008CA4C']));put(m,out+4,(half(read(m,p+0x1A,2))<<16)+half(read(m,p+0x1C,2)))
    put(m,out+8,0);put(m,out+12,0,2);put(m,out+14,0x100,2)
    for source_off,dest in((0x1E,0x16),(0x20,0x18),(0x22,0x20),(0x24,0x22),(0x16,0x24),(0x18,0x26),(0x26,0x28)):
        put(m,out+dest,read(m,p+source_off,2),2)
    for i,frac in enumerate((0x1C,0x1E,0x1D)):
        f=floating(read(m,p+i*4));put(m,out+0x10+i*2,math.trunc(f),2)
        put(m,out+frac,math.trunc(floating(bits(f*256.0))),1)
    put(m,out+0x1A,0,2);put(m,out+0x1F,9,1)
    for i in range(3):put(m,out+0x2C+i,read(m,p+0x28+i,1)*alpha>>8,1);put(m,out+0x30+i,read(m,p+0x2B+i,1)*alpha>>8,1)
    for source_off,dest in((0x30,0x2A),(0x31,0x2B),(0x2F,0x2F)):put(m,out+dest,read(m,p+source_off,1),1)
    put(m,out+0x34,1,2);return data(m,out,54)

def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;home=STACK+c.phase if home is None else home;p=packet(home);m=dict(initial);calls=[];snapshots=[];number=0
    def call(target,args=()):calls.append((target,tuple(map(u32,args))));snapshots.append((target,data(m,p,52)))
    def random():
        nonlocal number
        call(s['func_150ADA20']);effect(m,c,s,number)
        if c.mode==2:
            value=next_seed(read(m,s['D_800885B0'],8));put(m,s['D_800885B0'],value,8)
        else:value=c.randoms[number]
        number+=1;return u32(value)
    for i in range(3):put(m,p+i*4,read(m,c.actor+0x34+i*4))
    put(m,p+0x16,0,2);put(m,p+0x18,0,2);shared=random()%6+8
    put(m,p+0x1A,shared,2);put(m,p+0x1E,0,2);put(m,p+0x20,0,2);put(m,p+0x1C,shared,2)
    put(m,p+0x22,random()%201+100,2);put(m,p+0x24,random()%5+3,2);put(m,p+0x26,600,2)
    for selector,at in((3,0x28),(4,0x2B)):
        call(s['func_151429E0'],(selector,p+at,p+at+1,p+at+2))
        row=s['D_8008A160']+selector*12+(random()&3)*3 if c.mode else None
        for i in range(3):put(m,p+at+i,read(m,row+i,1)if row is not None else(selector*17+i*31)&255,1)
    put(m,p+0x2E,255,1);put(m,p+0x2F,random()%65+92,1);put(m,p+0x30,random()%3+1,1);put(m,p+0x31,0,1)
    call(s['func_1518CA80'],(p,1));payload=data(m,p,52)
    if c.consumer:call(FACTORY,(home-0x50-0x68+0x30,0,0,0xFFFFFFFF,255,1))
    return dict(descriptor=payload,calls=calls,snapshots=snapshots[:len(snapshots)-(1 if c.consumer else 0)],randoms=number,seed=read(m,s['D_800885B0'],8),actor=data(m,c.actor+0x34,12),
        consumer=consumer_packet(initial,payload,home,s)if c.consumer else None)

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.number=0;self.descriptors=[];self.factory_packets=[];self.snapshots=[]
        self.unmap_prefix=False
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.actor,)if arguments is None else arguments)
    def execute(self,word):
        op,rs,rt,rd,shift,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63;mask=(1<<64)-1
        if op in(55,63)or op==0 and fn in(37,38,56,58,60,62,63,27):
            prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=word
            try:
                if op in(55,63):
                    p=u32(self.r[rs]+half(word));assert p%8==0
                    if op==55:self.r[rt]=self.get(p,8)
                    else:self.put(p,self.r[rt],8)
                elif fn==27:
                    a,b=u32(self.r[rs]),u32(self.r[rt]);assert b;self.lo,self.hi=a//b,a%b
                else:
                    value=self.r[rt]&mask
                    if fn in(37,38):value=self.r[rs]|self.r[rt]if fn==37 else self.r[rs]^self.r[rt]
                    elif fn in(56,60):value<<=shift+(32 if fn==60 else 0)
                    elif fn in(58,62):value>>=shift+(32 if fn==62 else 0)
                    else:value=(value if value<1<<63 else value-(1<<64))>>(shift+32)
                    self.r[rd]=value&mask
                self.r[0]=0
            finally:self.own_instruction=prior
        else:
            before=self.r[:];super().execute(word)
            destination=rt if op in(9,12,13,15,32,33,35,36,37)else rd if op==0 and fn in(0,2,3,33,35,36,42,43,16,18)else None
            for i,value in enumerate(before):
                if i!=destination and value>0xFFFFFFFF:self.r[i]=value
    def record_call(self,target):
        counts={source.ENTRY:1,self.s['func_150ADA20']:0,self.s['func_151429E0']:4,self.s['func_1518CA80']:2,FACTORY:6}
        if target not in counts:raise AssertionError(('Unexpected descriptor call',hex(target)))
        args=tuple(map(u32,self.arguments(counts[target])));self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target not in(source.ENTRY,FACTORY):self.snapshots.append((target,data(self.memory,packet(self.target_home),52)))
        if target==self.s['func_150ADA20']:effect(self.memory,self.case,self.s,self.number);self.number+=1
        if target==self.s['func_1518CA80']:
            self.descriptors.append(data(self.memory,args[0],52))
            if self.unmap_prefix:
                for off in(*range(12,22),50,51):self.memory.pop(args[0]+off)
        if target==FACTORY:self.factory_packets.append(data(self.memory,args[0],54))
    def hook(self,target):
        if target==self.s['func_150ADA20']:value=self.case.randoms[self.number-1]
        elif target==self.s['func_151429E0']:
            a=self.calls[-1][1]
            for i,p in enumerate(a[1:]):self.put(p,(a[0]*17+i*31)&255,1)
            value=0x81234567
        elif target in(self.s['func_1518CA80'],FACTORY):value=0x87654321
        else:raise AssertionError(('Unbounded descriptor provider',hex(target)))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def helper_code(rom,c):
    result={}
    for entry,offset,n in HELPERS:
        if entry==RANDOM and c.mode!=2 or entry==COLOR and not c.mode or entry==SUBMIT and not c.consumer:continue
        result.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return result

def bound(obj,s):
    raw,bindings=source.function_blob(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for at,rows in bindings.items():
        if len(rows)!=1 or rows[0][0]!='R_MIPS_26':raise ValueError('Descriptor call binding changed')
        words[at//4]=(words[at//4]&0xFC000000)|((s[rows[0][1]]>>2)&0x3FFFFFF)
    return words

def cases():
    for mode,i,phase,mutation in itertools.product((0,1),range(201),(0,8),(0,1)):
        values=(i,i%201,i%5,i%65,i%3,0,0)if not mode else(i,i%201,i%5,i%4,(i+1)%4,i%65,i%3)
        yield Case(values,mode,position=i%3,pattern=i%2,mutation=mutation,phase=phase)
    for mode,field,value,phase in itertools.product((0,1),range(5),WORDS,(0,8)):
        values=[0]*7;values[field if not mode else(0,1,2,5,6)[field]]=value
        yield Case(tuple(values),mode,position=2,phase=phase)
    for seed,position,phase in itertools.product(SEEDS,(0,1),(0,8)):yield Case(mode=2,seed=seed,position=position,pattern=position,consumer=1,phase=phase)
    for i,phase in itertools.product(range(16),(0,8)):
        yield Case(tuple((i+j*17)&255 for j in range(7)),1,position=i%2,consumer=1,phase=phase)
        yield Case(tuple((i+j*31)&255 for j in range(7)),1,position=i%3,mutation=2,phase=phase)

def controls():
    b=candidate.SELECTED;copy='    descriptor.position = *(EffectPosition176A00 *)(actor + 0x34);\n'
    signed=b.replace('(u32)func_150ADA20()','func_150ADA20()')
    for divisor in(6,201,5,65,3):signed=signed.replace(f'% {divisor}u',f'% {divisor}')
    return dict(signed_mod=signed,position=b.replace('actor + 0x34','actor + 0x38'),
        late_copy=b.replace(copy,'').replace('    func_1518CA80(&descriptor, 1);',copy+'    func_1518CA80(&descriptor, 1);'),
        repeated_random=b.replace('descriptor.value1A = descriptor.value1C = (u32)func_150ADA20() % 6u + 8;',
            'descriptor.value1A = (u32)func_150ADA20() % 6u + 8;\n    descriptor.value1C = (u32)func_150ADA20() % 6u + 8;'),
        first_color=b.replace('func_151429E0(3,','func_151429E0(4,'),second_color=b.replace('func_151429E0(4,','func_151429E0(3,'),
        fixed_value=b.replace('value26 = 600','value26 = 601'),alpha=b.replace('alpha = 255','alpha = 254'),
        range65=b.replace('% 65u','% 64u'),range3=b.replace('% 3u','% 2u'),flags=b.replace('flags = 0','flags = 1'),
        retained=b.replace(copy,copy+'    descriptor.retained0C[0] = 0;\n'),result=b.replace('    return 0;','    return 1;'))
