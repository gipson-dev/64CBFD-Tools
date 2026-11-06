"""Live ROM bounds, post-consumer big-endian steps and exact guest call ordering."""
from dataclasses import dataclass,replace
import itertools
from tools.experiments import game_asset_block_walker_candidates as source
from tools.tests.game_table_payload_spawn_oracle import Oracle as InstructionOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
MASK=0xFFFFFFFF
BUFFER,TABLE=0x30000,0x80082F80
ALLOC,COPY,CONSUME,FREE=0x10003C6C,0x10004514,0x15015A38,0x10004074
SYMS=dict(D_80082F80=TABLE,func_10003C6C=ALLOC,func_10004514=COPY,func_15015A38=CONSUME,func_10004074=FREE)
DESCS,PIXELS,DESC_TABLE,PIXEL_TABLE=0x90000,0xA0000,0x80085994,0x80085990

@dataclass(frozen=True)
class Case:
    selector:int=0
    steps:tuple=(16,24,32)
    tail:int=0
    size:int=-1
    copy_limit:int|None=None
    stop_after:int=0
    mutation:int=0
    base:int=BUFFER
    phase:int=0
    copy_error:bool=False
    poison:int=0xDEADBEEF
    consumer:bool=False
    width:int=9
    height:int=2
    run:int=4

def narrow(v):return ((v&65535)^32768)-32768
def size(c):return (sum(c.steps)+c.tail if c.size<0 else c.size)&MASK
def entry(c,s=SYMS):return (s['D_80082F80']+8*narrow(c.selector))&MASK
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}

def image(c):
    data=bytearray((i*13+89)&255 for i in range(0x2800));at=0
    for k,step in enumerate(c.steps):
        if at+16>len(data):break
        data[at:at+4]=bytes((0xFF if c.width==0 else c.width-1,0xFF if c.height==0 else c.height-1,0xA0+k,0x70+k))
        data[at+4:at+8]=(8 if c.mutation&4 else step).to_bytes(4,'big')
        if c.consumer:
            p=at+8
            for row in range(c.height):
                left=max(0,c.width-1)
                while left:
                    n=min(left,c.run);data[p]=((row+3)&15)<<4|(n-1);p+=1;left-=n
        at+=step
    return data

def fixture(c=Case(),s=SYMS):
    m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
    m.update({c.base+i:(i*13+89)&255 for i in range(-16,0x2810)})
    if c.copy_error:
        m.update({c.base+i:v for i,v in enumerate(image(c))})
    at=entry(c,s)
    for i in range(-4,12):m[(at+i)&MASK]=0xA5
    put(m,at,0x100000);put(m,(at+4)&MASK,(0x100000+size(c))&MASK)
    if c.consumer:
        for table,pointer in ((DESC_TABLE,DESCS),(PIXEL_TABLE,PIXELS)):
            address=(table+4*narrow(c.selector))&MASK
            for i in range(4):m[address+i]=0
            put(m,address,pointer)
        m.update({DESCS+i:0xA5 for i in range(128)})
        m.update({PIXELS+i:0xA5 for i in range(0x3000)})
    return m

def scratch(m,home):
    for i in range(4):put(m,home+4*i,0xB5000000+i)

def after_alloc(m,c,s,home):
    if c.mutation&1:
        p=entry(c,s);a=(read(m,p)+0x4000)&MASK;put(m,p,a);put(m,p+4,(a+size(c))&MASK)
    if c.mutation&16:put(m,home+0x38,0xABCDEF80)

def copy(m,c,s,home,args):
    if not c.copy_error:
        assert args[2]<=0x2800,args
        data=image(c)
        for i in range(args[2]):m[(args[1]+i)&MASK]=data[i]
    if c.copy_limit is not None:
        p=entry(c,s);start=(read(m,p)+0x100)&MASK;put(m,p,start);put(m,p+4,(start+c.copy_limit)&MASK)
    if c.mutation&16:put(m,home+0x38,0x12340001)

def texture(m,c,p,index):
    desc=read(m,DESC_TABLE+4*narrow(c.selector))+4*index
    width=(m[p]+1)&255;height=(m[p+1]+1)&255
    for i,v in enumerate((width,height,m[p+2],m[p+3])):m[desc+i]=v
    out=read(m,PIXEL_TABLE+4*narrow(c.selector))+224*index;stride=(width+7)&~7
    for x in range(width):m[out+x]=0
    source_at=p+8
    for y in range(1,height+1):
        x=0;swizzle=4 if y&1 else 0
        if width:m[out+y*stride+(x^swizzle)]=0;x=1
        while x<width:
            code=m[source_at];source_at+=1;n=(code&15)+1
            for j in range(n):m[out+y*stride+((x+j)^swizzle)]=code&0xF0
            x+=n
        while x<stride:m[out+y*stride+(x^swizzle)]=0;x+=1
    for x in range(stride):m[out+(height+1)*stride+x]=0

def consume(m,c,s,home,args,ordinal):
    p,index,selector=args
    assert selector==(narrow(c.selector)&MASK)
    if c.consumer:texture(m,c,p,index)
    if c.mutation&4:put(m,p+4,c.steps[min(ordinal,len(c.steps)-1)])
    if c.stop_after and ordinal+1>=c.stop_after:
        at=entry(c,s);put(m,at+4,(read(m,at)-c.base)&MASK)
    if c.mutation&16:put(m,home+0x38,0xFFFF7FFF)

def reference(initial,c=Case(),s=SYMS,home=None,saved=None):
    m=dict(initial);home=STACK+c.phase-0x38 if home is None else home
    saved=saved or {r:0xA0000000+r for r in (16,17,18,19,20,31)}
    for off,r in ((0x20,16),(0x24,17),(0x28,18),(0x2C,19),(0x30,20),(0x34,31)):put(m,home+off,saved[r])
    put(m,home+0x38,c.selector&MASK);put(m,home+0x10,0)
    calls=[(s['func_10003C6C'],(0x2800,1,2,1,0))];after_alloc(m,c,s,home);scratch(m,home)
    at=entry(c,s);start=read(m,at);end=read(m,at+4)
    args=(start,c.base,(end-start)&MASK,1);calls.append((s['func_10004514'],args));copy(m,c,s,home,args);scratch(m,home)
    cursor=c.base;index=0
    while ((cursor+15)&MASK)<((c.base+read(m,at+4)-read(m,at))&MASK):
        if index>24:raise AssertionError(('Unbounded asset fixture',c,index,hex(cursor)))
        args=(cursor,index,narrow(c.selector)&MASK);calls.append((s['func_15015A38'],args));consume(m,c,s,home,args,index);scratch(m,home)
        amount=read(m,cursor+4);cursor=(cursor+amount)&MASK;index+=1
    calls.append((s['func_10004074'],(c.base,)));scratch(m,home)
    return m,calls,cursor,index

class Oracle(InstructionOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected=None):
        self.c,self.s=c,s;self.home=STACK+c.phase-0x38;self.ordinal=0
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.selector,),connected=connected)
        self.before_f=self.f[:]
    def execute(self,word):
        if word>>26==0 and word&63==38:
            # The original consumer swizzles odd texture rows with integer XOR.
            self.dispatched_word=word;rs,rt,rd=word>>21&31,word>>16&31,word>>11&31
            self.r[rd]=self.r[rs]^self.r[rt];self.r[0]=0
        else:super().execute(word)
    def record_call(self,t):
        counts={source.ENTRY:1,self.s['func_10003C6C']:5,self.s['func_10004514']:4,self.s['func_15015A38']:3,self.s['func_10004074']:1}
        if t not in counts:raise AssertionError(('Unknown asset provider',hex(t)))
        args=tuple(self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        a=self.calls[-1][1];value=self.c.poison
        if t==self.s['func_10003C6C']:after_alloc(self.memory,self.c,self.s,self.home);value=self.c.base
        elif t==self.s['func_10004514']:copy(self.memory,self.c,self.s,self.home,a)
        elif t==self.s['func_15015A38']:
            if self.ordinal>24:raise AssertionError('Asset fixture exceeded consumer bound')
            consume(self.memory,self.c,self.s,self.home,a,self.ordinal);self.ordinal+=1
        elif t==self.s['func_10004074']:assert a==(self.c.base,)
        else:raise AssertionError(('Unbounded asset provider',hex(t)))
        scratch(self.memory,self.r[29])
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value&MASK

def cases():
    selectors=(0,1,0xFFFF,0x7FFF,0x8000,0x10000,0x1234FFFF,0xFFFF0001,0x80000000,0x7FFFFFFF)
    for selector,steps,tail,mutation,phase in itertools.product(selectors,((),(16,),(16,16),(16,24,32),(255,256)),(0,1,15),(0,1,4,16,21),(0,8)):
        yield Case(selector=selector,steps=steps,tail=tail,mutation=mutation,phase=phase)
    for field,byte in itertools.product(range(4),range(256)):
        shift=24-8*field;value=(16&~(255<<shift))|(byte<<shift)
        yield Case(steps=(value,),size=16,stop_after=1,phase=8*(byte&1))
    for limit,mutation,phase in itertools.product((0,15,16,17,31,32,48,72),(0,4,16),(0,8)):
        yield Case(copy_limit=limit,mutation=mutation,phase=phase)
    for base,limit,phase in itertools.product((0,0xFFFF0000),(0,15,16),(0,8)):
        yield Case(base=base,steps=(16,),size=16,copy_limit=limit,phase=phase)
    for amount in (0x7FFFFFFF,0x80000000,0xFFFFFFFF):
        yield Case(size=amount,copy_error=True,stop_after=1)
    yield Case(steps=(),base=0)

def controls():
    b=source.SELECTED
    changes={
        'unsigned_selector':('[selector]','[(u16)selector]'),
        'wrong_allocation':('0x2800, 1, 2, 1, 0','0x27F0, 1, 2, 1, 0'),
        'wrong_copy_size':('(u32)D_80082F80[selector].end - (u32)D_80082F80[selector].start, 1','(u32)D_80082F80[selector].end - (u32)D_80082F80[selector].start - 1, 1'),
        'nonblocking_copy':('selector].start, 1);','selector].start, 0);'),
        'wrong_boundary':('+ 15 <','+ 16 <'),
        'signed_limit':('(u32)cursor + 15 < (u32)base + D_80082F80[selector].end - D_80082F80[selector].start','(s32)((u32)cursor + 15) < (s32)((u32)base + D_80082F80[selector].end - D_80082F80[selector].start)'),
        'wrong_index':('index = 0','index = 1'),
        'wrong_selector_argument':('cursor, index, selector','cursor, index, selector + 1'),
        'little_endian_step':('((u32)cursor[5] << 16) +\n                           ((u32)cursor[6] << 8) + (u32)cursor[7] + ((u32)cursor[4] << 24)','((u32)cursor[5] << 8) +\n                           ((u32)cursor[6] << 16) + (u32)cursor[4] + ((u32)cursor[7] << 24)'),
        'skip_consumer':('            func_15015A38(cursor, index, selector);',''),
        'skip_free':('    func_10004074(base);',''),
        'free_cursor':('func_10004074(base)','func_10004074(cursor)')}
    result={n:b.replace(a,z) for n,(a,z) in changes.items()}
    if any(v==b for v in result.values()):raise ValueError('Ineffective asset walker control')
    return result
