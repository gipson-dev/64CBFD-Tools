"""Independent fourteen-argument contract and connected original MIPS helpers."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_threshold_random_effect_candidates as candidate
from tools.experiments import game_threshold_random_effect_match as source
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_random_selector_outputs_match import next_seed,SEEDS
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ACTOR,OTHER,THIRD,OUTPUT,ASSET=0x30000,0x31000,0x32000,0x70000,0x50000
RANDOM,SUBMIT,FACTORY,ALLOCATE,TRANSFORM,RELEASE=0x150ADA20,0x15171D4C,0x15171CA0,0x15167A68,0x15172B20,0x1516972C
WORDS=(0,1,2,3,359,360,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF)
u32=lambda x:x&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
bits=lambda x:struct.unpack('>I',struct.pack('>f',x))[0]
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
def symbols():return dict(func_150ADA20=RANDOM,func_15171D4C=SUBMIT,D_800885B0=0x800885B0,D_8008CA4C=0x8008CA4C)
@dataclass(frozen=True)
class Case:
    value:int=768
    scale:int=255
    point:tuple=(-32768,32767,-1)
    randoms:tuple=(0xFFFFFFFF,0x80000000)
    mutation:int=0
    connected:bool=False
    consumer:int=0
    seed:int=0x123456789ABCDEF0
    phase:int=0
    actor:int=ACTOR
    redirect:int=0

def fixture(c=Case(),s=None):
    s=symbols()if s is None else s
    m={STACK+i:(i*17+165)&255 for i in range(-0x500,0x400)}
    for j,base in enumerate((c.actor,OTHER,THIRD)):
        m.update({base+i:(i*29+j*31+123)&255 for i in range(0x100)})
        put(m,base+0x14,c.value,2)
        for i,v in enumerate(c.point):put(m,base+0x18+2*i,v+j,2)
        m[base+0x25]=(c.scale+j*31)&255;m[base+0x0C]=(17+j*19)&255;m[base+1]=(0x80+j*23)&255
    put(m,s['D_800885B0'],c.seed,8);put(m,s['D_8008CA4C'],ASSET)
    for slot in range(32,35):put(m,s['D_8008CA4C']+slot*4,ASSET)
    put(m,0x8008CA2C,source.ENTRY)
    m.update({ASSET+i:(i*13+37)&255 for i in range(16)});put(m,ASSET+6,13,2)
    m.update({OUTPUT+i:0xA5 for i in range(0x80)});return m

def effect(m,c,number,home):
    # Snapshot byte 0x25 after draw one; read position/trailing fields after draw two.
    if c.mutation&(1<<number):
        p=c.actor
        m[p+0x25]=(200,17)[number];put(m,p+0x14,0xFFFF,2)
        for i,v in enumerate(((32767,-32768,123),(-101,202,-303))[number]):put(m,p+0x18+2*i,v,2)
        m[p+0x0C]=(0x90,0x55)[number];m[p+1]=(0x80,0xFF)[number]
    if c.redirect&(1<<number):put(m,home,(OTHER,THIRD)[number])

def reference(initial,c=Case(),s=None,home=None):
    s=symbols()if s is None else s;home=STACK+c.phase if home is None else home
    m=dict(initial);calls=[];count=0;record=c.actor
    if half(read(m,record+0x14,2))<768:return dict(memory=m,calls=calls,number=0,seed=c.seed,submission=None)
    seed=read(m,s['D_800885B0'],8)
    def random():
        nonlocal count,seed,record
        calls.append((s['func_150ADA20'],()));effect(m,c,count,home)
        value=next_seed(seed)if c.connected else c.randoms[count]
        if c.connected:seed=value;put(m,s['D_800885B0'],value,8)
        if c.redirect&(1<<count):record=(OTHER,THIRD)[count]
        count+=1;return u32(value)
    variant=random()%3;scale=read(m,record+0x25,1);angle=random()%360
    point=tuple(half(read(m,record+0x18+2*i,2))for i in range(3))
    submission=(bits(float(point[0])),bits(float(point[1]-10)),bits(float(point[2])),100,0,variant+32,bits(float(angle)),0,scale*25//255+25,0,256,0,read(m,record+0x0C,1),read(m,record+1,1))
    calls.append((s['func_15171D4C'],submission))
    if c.consumer:
        factory=(100,0,variant+32,0,256,0,submission[12],submission[13]);calls.append((FACTORY,factory))
        calls.append((ALLOCATE,(15,submission[13],96,1,submission[12],1)))
        if c.consumer>=2:
            for offset,value,size in((0x50,100,2),(0x52,0,2),(0x54,256,2),(0x56,0,2),(0x58,variant+32,1),(0x59,0,1),*[(offset,0,2)for offset in(0x16,0x26,0x36,0x46)]):put(m,OUTPUT+offset,value,size)
            calls.append((TRANSFORM,(OUTPUT+0x10,*submission[:3],submission[6],0,submission[8],13)))
            if c.consumer==3:calls.append((RELEASE,(OUTPUT,)))
    return dict(memory=m,calls=calls,number=count,seed=seed,submission=submission)

class Oracle(RngInstructions):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.number=0;self.submissions=[]
        FactoryOracle.__init__(self,words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.actor,)if arguments is None else arguments)
    def execute(self,word):
        if word>>26==17 and word>>21&31==0:
            # MFC1 really replaces its GPR, including a prior 64-bit RNG temporary.
            before=self.r[:];destination=word>>16&31;FactoryOracle.execute(self,word)
            for i,value in enumerate(before):
                if i!=destination and value>0xFFFFFFFF:self.r[i]=value
        else:super().execute(word)
    def record_call(self,t):
        if t==self.s['func_15171D4C']:
            args=(self.f[12],self.f[14],u32(self.r[6]),u32(self.r[7]),*[read(self.memory,self.r[29]+0x10+i*4)for i in range(10)])
            self.submissions.append(args)
        else:
            counts={source.ENTRY:1,self.s['func_150ADA20']:0,FACTORY:8,ALLOCATE:6,TRANSFORM:8,RELEASE:1}
            assert t in counts,('unowned call',hex(t));args=tuple(map(u32,self.arguments(counts[t])))
        self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==self.s['func_150ADA20']:effect(self.memory,self.case,self.number,self.target_home);self.number+=1
    def hook(self,t):
        if t==self.s['func_150ADA20']:value=self.case.randoms[self.number-1]
        elif t==self.s['func_15171D4C']:value=0x87654321
        elif t==ALLOCATE:value=OUTPUT if self.case.consumer>=2 else 0
        elif t==TRANSFORM:value=int(self.case.consumer==2)
        else:assert t==RELEASE;value=0x81234567
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def public(m):return {p:v for p,v in m.items()if not STACK-0x500<=p<STACK+0x400}
def bound(obj,s,fitted=False):
    raw,bindings=source.function_blob(obj)
    if fitted:raw=source.normalized(raw,bindings,(candidate.ROOT/source.ROM_IMAGE).read_bytes()[source.ROM:source.ROM+272])
    words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for at,rows in bindings.items():
        assert len(rows)==1 and rows[0][0]=='R_MIPS_26'
        words[at//4]=(words[at//4]&0xFC000000)|((s[rows[0][1]]>>2)&0x3FFFFFF)
    return words
def helper_code(rom,c):
    code={}
    for entry,off,n,enabled in((RANDOM,0xDAED0,18,c.connected),(SUBMIT,0x19F1FC,110,bool(c.consumer)),(FACTORY,0x19F150,43,bool(c.consumer))):
        if enabled:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,off)))
    return code
def cases():
    for value,mutation,phase in itertools.product((-32768,-1,0,767,768,769,32767),range(4),(0,8)):
        yield Case(value=value,mutation=mutation,phase=phase)
    for residue,phase in itertools.product(range(360),(0,8)):
        yield Case(scale=residue%256,randoms=(residue%3,residue),point=(residue-180,180-residue,residue),phase=phase)
    for scale,phase in itertools.product(range(256),(0,8)):yield Case(scale=scale,randoms=(2,359),phase=phase)
    for first,second,phase in itertools.product(WORDS,WORDS,(0,8)):yield Case(randoms=(first,second),phase=phase)
    for seed,consumer,phase in itertools.product(SEEDS,range(4),(0,8)):yield Case(connected=True,seed=seed,consumer=consumer,phase=phase)
    for redirect,phase in itertools.product(range(1,4),(0,8)):yield Case(redirect=redirect,phase=phase)
def controls():
    b=candidate.SELECTED
    signed=b.replace('(u32)func_150ADA20()','func_150ADA20()').replace('% 3u','% 3').replace('% 360u','% 360')
    return dict(threshold=b.replace('>= 0x300','> 0x300'),unsigned_gate=b.replace('*(s16 *)(record + 0x14)','*(u16 *)(record + 0x14)'),
      signed_mod=signed,wrong_variant=b.replace('% 3u','% 2u'),wrong_angle=b.replace('% 360u','% 359u'),
      late_scale=b.replace('    s32 scale;\n','').replace('        scale = record[0x25];\n','').replace('0, scale * 25','0, (s32)record[0x25] * 25'),
      early_scale=b.replace('        scale = record[0x25];\n','').replace('        variant =','        scale = record[0x25];\n        variant ='),
      no_y_offset=b.replace('record + 0x1A) - 10','record + 0x1A) - 0'),
      wrong_scale=b.replace('scale * 25 / 255 + 25','scale * 25 / 256 + 25'),
      wrong_flags=b.replace('+ 25, 0, 256, 0','+ 25, 1, 256, 0'),
      wrong_tail=b.replace('record[0x0C], record[1]','record[1], record[0x0C]'))
