"""Independent bounded reference and actual retail init/wrapper execution.

Domain: finite coordinates within 2048, positive falloff 1/30, frame steps
0..30, palette group 0/1 with counts -1..7, disjoint private/public objects.
Byte intensity may alias owned record bytes. Packet coordinates/padding are
not read by providers; its initialized mutable fields persist between calls.
"""
from dataclasses import dataclass
from pathlib import Path
import json,math,random,struct
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.experiments.game_paired_ground_constructor_match import payload

from tools.experiments import game_list_draw_1517e4a8_recovery as source
ROOT=source.ROOT;OUT=source.OUT
ENTRY,INIT,SETUP,DRAW,WRAPPED=0x1517E4A8,0x1517EA4C,0x150950D4,0x15095A48,0x15095A90
NODE,CURSOR,OTHER,INTENSITY,DESC,PALETTE=0x30000,0x50000,0x60000,0x70000,0x800903AC,0x800A7250
WIDTH,HEIGHT,TICKS,TOUCHED,SCALEX,SCALEY=0x800BE620,0x800BE624,0x800BE9E4,0x800DDD60,0x800380A0,0x800380A4
COLORS=0x800D2DA8
TABLE=bytes.fromhex('804080ff804080204020202020200000')
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda v:((v&65535)^32768)-32768
def fadd(a,b):return bits(floating(a)+floating(b))
def fsub(a,b):return bits(floating(a)-floating(b))
def fmul(a,b):return bits(floating(a)*floating(b))
def fdiv(a,b):return bits(floating(a)/floating(b))
@dataclass(frozen=True)
class Case:
    seed:int;width:int;height:int;x:float;y:float;state:int;enabled:int;group:int;count:int
    falloff:int;strength:int;intensity:int;old_intensity:int;ticks:int;touched:int;mode:int;phase:int

def cases():
    rng=random.Random(0x1517E4A8)
    for i in range(1024):
        width=rng.choice((320,640,1280));height=rng.choice((240,480,720))
        if i%3==0:x=width*0.5+rng.choice((0,1.25,6,24,34,62));y=height*0.5+rng.choice((0,-6,7,24,25))
        else:
            x=rng.choice((-2001,-32,-0.0,0,1,1.999,2,17,width-2,width,1999.75,2000))
            y=rng.choice((-2001,-1,-0.0,0,17,height-0.25,height,1999.5,2000))
        yield Case(i,width,height,x,y,rng.choice((-32768,-1,0,1,175,32767)),rng.choice((0,1,2,255)),rng.randrange(2),
            rng.choice((-1,0,1,3,7)),rng.choice((1,30)),rng.choice((-1,0,1,255,256)),rng.randrange(5),rng.randrange(256),
            rng.choice((0,1,2,30)),rng.randrange(2),rng.randrange(4),8*(i&1))
    # Force the exact distance cutoff and both setup/loop branches.
    for mode in range(4):
        for count in(-1,0,1,3,7):
            for touched in(0,1):
                yield Case(1024+mode*20+count,320,240,1160,1120,32767,255,0,count,1,256,1,0,0,touched,mode,0)
                yield Case(1200+mode*20+count,640,480,344,264,100,255,1,count,1,256,1,176,1,touched,mode,8)

def intensity(c):return(0,INTENSITY,NODE+0x28,NODE+0x29,NODE+0x30)[c.intensity]
def fixture(c):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-768,256)}
    for base,size in((NODE,64),(CURSOR,0x800),(OTHER,0x800),(INTENSITY,4),(DESC,24),(PALETTE,16)):
        m.update({base+i:(i*19+0xB7)&255 for i in range(size)})
    for a,v in((NODE+12,bits(c.x)),(NODE+16,bits(c.y)),(WIDTH,c.width),(HEIGHT,c.height),(TICKS,c.ticks),(SCALEX,bits(1.0)),(SCALEY,bits(0.5))):put(m,a,v)
    put(m,NODE+40,c.state&65535,2);put(m,NODE+48,c.enabled,1);put(m,INTENSITY,c.old_intensity,1);put(m,TOUCHED,c.touched,1)
    for i in range(4):put(m,COLORS+i,0xA5,1)
    m.update({PALETTE+i:v for i,v in enumerate(TABLE)})
    return m

def public(m):return{a:v for a,v in m.items()if not STACK-768<=a<STACK+256}
def snapshot(m):
    return tuple(read(m,a,n)for a,n in((NODE+12,4),(NODE+16,4),(NODE+40,2),(NODE+48,1),(WIDTH,4),(HEIGHT,4),(TICKS,4),(TOUCHED,1),
        (SCALEX,4),(SCALEY,4),(COLORS,1),(COLORS+1,1),(COLORS+2,1),(COLORS+3,1),(INTENSITY,1)))
def packet_read(m,a):return[read(m,a+6,2),read(m,a+8,2),read(m,a+10,1),read(m,a+11,1),read(m,a+12,1),read(m,a+13,1),read(m,a+16,4)]
def packet_write(m,a,p):
    for at,n,v in zip((6,8,10,11,12,13,16),(2,2,1,1,1,1,4),p):put(m,a+at,v,n)

def effect(m,c,target,args,ordinal,packet=None):
    commands=args[0]
    if target==INIT:
        for i,(w0,w1)in enumerate(((0xE7000000,0),(0xFCFFB3FF,0xFF65FEFF),(0xEF002C0F,0x00504344))):put(m,commands+i*8,w0);put(m,commands+i*8+4,w1)
        return commands+24
    if target==SETUP:
        assert args[1:]==(DESC,0,0,0,0,2,256,256,3),args
        put(m,commands,0xCE000000|ordinal);put(m,commands+4,0x12345678)
        if c.mode==1:
            put(m,NODE+12,fadd(read(m,NODE+12),bits(0.25)));put(m,NODE+16,fsub(read(m,NODE+16),bits(0.5)))
            put(m,NODE+40,97,2);put(m,NODE+48,255,1);put(m,SCALEX,bits(1.25));put(m,SCALEY,bits(0.75))
            put(m,WIDTH,1280);put(m,HEIGHT,720);put(m,TICKS,7);put(m,COLORS,17,1)
        return commands+8
    assert target==DRAW and packet is not None
    put(m,commands,0xCB000000|ordinal);put(m,commands+4,args[2]^args[3])
    if c.mode==2:
        put(m,NODE+12,fadd(read(m,NODE+12),bits(1.0)));put(m,NODE+16,fsub(read(m,NODE+16),bits(2.0)))
        put(m,NODE+40,0xFFF9,2);put(m,NODE+48,0,1);put(m,SCALEX,fadd(read(m,SCALEX),bits(0.25)));put(m,SCALEY,fmul(read(m,SCALEY),bits(0.5)))
        packet[3]=(packet[3]+1)&255;packet[4]=(packet[4]+2)&255;packet[5]^=16;packet[6]=DESC+12
    if c.mode==3:put(m,TOUCHED,0,1);put(m,COLORS+1,ordinal&255,1)
    return (OTHER+ordinal*16 if c.mode==3 else commands+8*(1+(c.seed+ordinal)%2))

def reference(initial,c):
    m=dict(initial);trace=[];cursor=CURSOR;packet=None
    cx=fsub(read(m,NODE+12),fmul(bits(float(signed(read(m,WIDTH)))),bits(0.5)))
    cy=fsub(read(m,NODE+16),fmul(bits(float(signed(read(m,HEIGHT)))),bits(0.5)))
    ix,iy=math.trunc(floating(cx)),math.trunc(floating(cy));distance=(ix*ix+iy*iy)*c.falloff//10
    ptr=intensity(c)
    if ptr:
        desired=(120-distance)*176//120 if c.strength!=-1 and distance<120 else 0
        value=read(m,ptr,1);step=read(m,TICKS)*5
        value=desired if abs(desired-value)<step else value+step if value<desired else value-step
        put(m,ptr,value&255,1)
    x,y=floating(read(m,NODE+12)),floating(read(m,NODE+16))
    desired=0 if x<2.0 or x>=signed(read(m,WIDTH))-2 or y<0.0 or y>=signed(read(m,HEIGHT)) or c.strength==-1 else (1760000//(distance+10000)*c.strength)//256
    value=half(read(m,NODE+40,2));step=read(m,TICKS)*10
    value=desired if abs(desired-value)<step else value-step if desired<value else value+step
    put(m,NODE+40,value&65535,2)
    def call(target,args):
        nonlocal cursor
        state=tuple(packet)if target==DRAW else()
        trace.append((target,args,snapshot(m),state));cursor=effect(m,c,target,args,len(trace),packet)
    if distance<200000 and half(read(m,NODE+40,2))>0 and abs(floating(read(m,NODE+12)))<2000 and abs(floating(read(m,NODE+16)))<2000:
        for i in range(3):put(m,COLORS+i,255,1)
        packet=[0,0,0,0,0,0,DESC]
        if not read(m,TOUCHED,1):
            call(INIT,(cursor,));call(SETUP,(cursor,DESC,0,0,0,0,2,256,256,3));put(m,TOUCHED,1,1)
        alpha=(half(read(m,NODE+40,2))*read(m,NODE+48,1))>>8
        for index in range(max(c.count,0)):
            sample=TABLE[c.group*7+index];factor=bits(float(2+index*2))
            x=fsub(read(m,NODE+12),fdiv(fmul(cx,factor),bits(5.0)))
            y=fadd(fsub(read(m,NODE+16),fdiv(fmul(cy,factor),bits(5.0))),fmul(bits(float(sample)),bits(0.015625)))
            packet[0]=math.trunc(floating(fdiv(fmul(bits(float(sample<<12)),read(m,SCALEX)),bits(255.0))))&65535
            packet[1]=math.trunc(floating(fdiv(fmul(bits(float(sample<<12)),read(m,SCALEY)),bits(255.0))))&65535
            packet[2]=alpha&255;put(m,COLORS+3,0,1)
            call(DRAW,(cursor,0xF0010000,x,y));put(m,cursor,0xE7000000);put(m,cursor+4,0);cursor+=8
    return m,trace,cursor

class DrawOracle(TimingOracle):
    def __init__(self,words,memory,c,connected):
        self.case=c;self.trace=[];self.packet_address=None;self.boundary_private=[];self.frame=-signed(words[0]&65535|0xFFFF0000)
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=(CURSOR,NODE,c.group,c.count&0xFFFFFFFF,c.falloff,c.strength&0xFFFFFFFF,intensity(c)),connected=connected)
    def execute(self,w):
        op,rs,rd,fd,fn=w>>26,w>>21&31,w>>11&31,w>>6&31,w&63
        if op==17 and rs==16 and fn==5:self.f[fd]=self.f[rd]&0x7FFFFFFF
        else:super().execute(w)
    def record_call(self,target):
        if target==WRAPPED:
            args=tuple(self.arguments(9));assert args[4:]==(bits(4096.0),0,0,0,0),args
            return
        assert target in(INIT,SETUP,DRAW),hex(target)
        args=tuple(self.arguments({INIT:1,SETUP:10,DRAW:4}[target]));p=()
        if target==DRAW:
            if self.packet_address is None:self.packet_address=args[1]
            assert args[1]==self.packet_address
            p=tuple(packet_read(self.memory,args[1]));args=(args[0],0xF0010000,*args[2:])
        self.boundary_private.append(tuple(self.memory[STACK+self.case.phase-184+i]for i in range(212)))
        self.trace.append((target,args,snapshot(self.memory),p));self.calls.append((target,args))
    def hook(self,target):
        assert target in(SETUP,WRAPPED),hex(target)
        logical=DRAW if target==WRAPPED else target
        args=self.trace[-1][1];p=packet_read(self.memory,self.packet_address)if logical==DRAW else None
        answer=effect(self.memory,self.case,logical,args,len(self.trace),p)
        if p is not None:packet_write(self.memory,self.packet_address,p)
        for i in range(10 if target==SETUP else 9):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=answer;self.hi=self.lo=0xA5000010

def run(words=None):
    if words is None:
        raw,refs=payload(OUT/'qualified-screen/candidate.o','func_1517E4A8');words=bind(raw,refs)
    rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=struct.unpack_from('>361I',rom,0x1AB958)
    connected={INIT+4*i:w for i,w in enumerate(struct.unpack_from('>24I',rom,0x1ABEFC))}
    connected.update({DRAW+4*i:w for i,w in enumerate(struct.unpack_from('>18I',rom,0xC2EF8))})
    seen=[set(),set()];private=0;first=None;packets=set();count=0;calls=0;boundary_count=0
    for c in cases():
        initial=fixture(c);want,trace,cursor=reference(initial,c);models=[]
        for side,code in enumerate((words,truth)):
            model=DrawOracle(code,initial,c,connected).run()
            assert model.trace==trace,(c,side,'trace',model.trace,trace)
            assert model.r[2]==cursor,(c,side,'cursor',hex(model.r[2]),hex(cursor))
            assert public(model.memory)==public(want),(c,side,'public',[hex(a)for a in public(want)if model.memory.get(a)!=want[a]][:10])
            seen[side].update(pc for pc in model.visits if ENTRY<=pc<ENTRY+len(code)*4)
            if model.packet_address is not None:packets.add((side,model.packet_address-(STACK+c.phase)))
            models.append(model)
        ignored={160+i for i in range(4)}|{176+i for i in range(4)}
        assert len(models[0].boundary_private)==len(models[1].boundary_private)
        for a,b in zip(models[0].boundary_private,models[1].boundary_private):
            assert{i for i,(x,y)in enumerate(zip(a,b))if x!=y}<=ignored,(c,'unrelated private call state')
            boundary_count+=1
        differing={a for a in initial if models[0].memory[a]!=models[1].memory[a]}
        assert{a-(STACK+c.phase-184)for a in differing}<=ignored,(c,'unrelated private exit state')
        same=models[0].memory==models[1].memory;private+=same
        if not same and first is None:first=dict(seed=c.seed,differences=[hex(a-(STACK+c.phase))for a in initial if models[0].memory[a]!=models[1].memory[a]][:32])
        count+=1;calls+=len(trace)
    r=dict(cases=count,calls=calls,visited_words=[len(s)for s in seen],complete_private_equal_cases=private,first_private_difference=first,
        packet_offsets=sorted(packets),private_call_boundaries=boundary_count,private_difference_only_unpassed_counter_homes=True,
        raw_unvisited_indices=[i for i in range(len(words))if ENTRY+i*4 not in seen[0]],
        retail_unvisited_indices=[i for i in range(len(truth))if ENTRY+i*4 not in seen[1]],
        original_init_and_draw_wrapper_connected=True,public_and_calls_and_return_equal=True,matching_credit=0)
    (OUT/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':run()
