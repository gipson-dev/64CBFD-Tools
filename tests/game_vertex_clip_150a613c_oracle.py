"""Bounded binary32 transform model and custom-register instruction execution."""
from dataclasses import dataclass
from pathlib import Path
import csv,itertools,json,math,os,struct
from tools.experiments import game_vertex_clip_150a613c_restoration as s
from tools.experiments.game_paired_ground_constructor_match import payload

u32=lambda x:x&0xffffffff
signed=lambda x:((x&0xffffffff)^0x80000000)-0x80000000
def bits(x):return struct.unpack('>I',struct.pack('>f',x))[0]
def floating(x):return struct.unpack('>f',struct.pack('>I',x))[0]
def f32(x):return floating(bits(x))
RETURN=0xdead0000
class AccessBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
    xyz:tuple=(1,2,-3)
    matrix:tuple=(1.,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.)
    scales:tuple=(1.,1.)
    limits:tuple=(-1.,-100.)
    mask:int=255
    vertex:int=0x30000

def fixture(c):
    data=struct.pack('>3h',*c.xyz)
    return {u32(c.vertex+i):b for i,b in enumerate(data)}

def reference(c):
    x,y,z=map(float,c.xyz);m=c.matrix
    row=lambda col:f32(f32(f32(f32(x*m[col])+m[9+col])+f32(y*m[3+col]))+f32(z*m[6+col]))
    rawx=row(0);px=f32(rawx*c.scales[0]);py=f32(row(1)*c.scales[1]);depth=row(2)
    flag=0x10 if depth<=c.limits[1] else 0x20 if c.limits[0]<=depth else 0
    if not abs(px)<=-depth:flag|=2 if bits(rawx)&0x80000000 else 8
    if not abs(py)<=-depth:flag|=4 if bits(py)&0x80000000 else 1
    return tuple(map(bits,(px,py,depth))),flag,c.mask&flag

class Machine:
    def __init__(self,words,c,entry=s.ENTRY,connected=None):
        self.code=dict(zip(range(entry,entry+4*len(words),4),words));self.code.update(connected or {})
        self.r=[u32(0x91a00000+i*0x10101) for i in range(32)];self.r[0]=0;self.r[12]=c.vertex;self.r[18]=c.mask;self.r[31]=RETURN
        self.f=[bits(float(i+1)) for i in range(32)];self.f[16:20]=list(map(bits,(*c.scales,*c.limits)));self.f[20:32]=list(map(bits,c.matrix))
        self.memory=fixture(c);self.pc=entry;self.cc=False;self.cut=None;self.accesses=0;self.trace=[];self.visits=set();self.delay_of=None;self.current_pc=entry;self.calls=[]
        self.before=self.r[:];self.initial_f=self.f[:]
    def get(self,p,n):
        if self.accesses==self.cut:raise AccessBoundary
        self.accesses+=1;value=int.from_bytes(bytes(self.memory[u32(p+i)] for i in range(n)),'big');self.trace.append((p,n,value));return value
    def execute(self,w):
        op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63;imm=((w&65535)^32768)-32768
        if w==0:return
        if op==0:
            if fn==37:self.r[rd]=self.r[rs]|self.r[rt]
            elif fn==36:self.r[rd]=self.r[rs]&self.r[rt]
            elif fn==33:self.r[rd]=u32(self.r[rs]+self.r[rt])
            else:raise AssertionError(('SPECIAL',hex(w)))
        elif op==9:self.r[rt]=u32(self.r[rs]+imm)
        elif op==13:self.r[rt]=self.r[rs]|(w&65535)
        elif op in (33,35,37):
            value=self.get(u32(self.r[rs]+imm),4 if op==35 else 2);self.r[rt]=u32(((value^32768)-32768) if op==33 else value)
        elif op==17:
            fs=w>>11&31;ft=w>>16&31;fd=w>>6&31
            if rs==4:self.f[fs]=self.r[rt]
            elif rs==0:self.r[rt]=self.f[fs]
            elif rs==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])))
            elif rs==16:
                a,b=floating(self.f[fs]),floating(self.f[ft])
                if fn==0:self.f[fd]=bits(a+b)
                elif fn==2:self.f[fd]=bits(a*b)
                elif fn==5:self.f[fd]=self.f[fs]&0x7fffffff
                elif fn==6:self.f[fd]=self.f[fs]
                elif fn==7:self.f[fd]=self.f[fs]^0x80000000
                elif fn==54:self.cc=a<=b
                else:raise AssertionError(('FP',hex(w)))
            else:raise AssertionError(('COP1',hex(w)))
        else:raise AssertionError(('opcode',hex(w)))
        self.r[0]=0
    def step_instruction(self,pc,delay=None):
        self.current_pc=pc;self.delay_of=delay;self.visits.add(pc);self.execute(self.code[pc])
    def run(self,end=RETURN):
        for _ in range(512):
            if self.pc==end:return self
            pc=self.pc;w=self.code[pc];op=w>>26;rs=w>>21&31;rt=w>>16&31;imm=((w&65535)^32768)-32768
            self.current_pc=pc;self.delay_of=None;self.visits.add(pc)
            control=False;taken=False;likely=False;target=0
            if op==0 and w&63==8:control=True;taken=True;target=self.r[rs]
            elif op==3:
                control=True;taken=True;target=((pc+4)&0xf0000000)|((w&0x3ffffff)<<2);self.r[31]=pc+8;self.calls.append(target)
            elif op==17 and rs==8:control=True;taken=self.cc==bool(rt&1);likely=bool(rt&2);target=u32(pc+4+4*imm)
            elif op==1 and rt==2:control=True;taken=signed(self.r[rs])<0;likely=True;target=u32(pc+4+4*imm)
            if control:
                if taken or not likely:self.step_instruction(pc+4,pc)
                self.pc=target if taken else pc+8
            else:self.execute(w);self.pc=pc+4
        raise AssertionError('Instruction bound exceeded')

def verify(m,c):
    values,flag,mask=reference(c)
    assert tuple(m.f[13:16])==values,(c,tuple(map(hex,m.f[13:16])),tuple(map(hex,values)))
    assert m.r[11]==flag and m.r[18]==mask,(c,m.r[11],flag)
    assert m.memory==fixture(c) and m.r[29]==m.before[29]
    assert all(m.r[i]==m.before[i] for i in range(32) if i not in (1,8,9,11,18)),c
    assert all(m.f[i]==m.initial_f[i] for i in range(32) if i not in (0,1,2,3,10,11,13,14,15)),c
def state(m):return (m.r,m.f,m.memory,m.cc,m.pc,m.current_pc,m.delay_of,m.trace,m.calls)

def corpus():
    matrices=((1.,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.),(.5,-.25,1.,1.,.5,-.5,-.5,1.,.25,2.,-3.,-7.),(-1.,0.,0.,0.,-1.,0.,0.,0.,-1.,-0.,0.,-0.))
    for xyz,k,scales in itertools.product(itertools.product((-32768,-101,-1,0,1,100,32767),repeat=3),range(3),((1.,1.),(-1.,.5))):
        yield Case(xyz=xyz,matrix=matrices[k],scales=scales,mask=(0,0xaa,255,0xffffffff)[(xyz[0]+k)%4])
    for depth,x,y in itertools.product((-101,-100,-99,-2,-1,0,1),(-101,-100,-1,0,1,100,101),(-101,0,101)):
        yield Case(xyz=(x,y,depth),vertex=(0x80007ffc,0xfffffffc)[x&1])

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/s.BUILD;rom=(root/'conker/conker.us.bin').read_bytes()
    programs=[list(struct.unpack('>53I',payload(out/f,s.FUNCTION)[0])) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[1]==programs[2]
    seen=set();count=0;rows=list(corpus())
    for c in rows:
        ms=[Machine(p,c).run() for p in programs]
        for m in ms:verify(m,c);seen|=m.visits
        assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
    assert len(seen)==53,(len(seen),sorted(set(range(s.ENTRY,s.ENTRY+212,4))-seen))
    prefixes=0
    for c,cut in itertools.product((Case(),rows[0],rows[-1]),range(3)):
        ms=[]
        for p in programs:
            m=Machine(p,c);m.cut=cut
            try:m.run()
            except AccessBoundary:pass
            else:raise AssertionError('Access cut did not fire')
            ms.append(m)
        assert state(ms[0])==state(ms[1])==state(ms[2]);prefixes+=1
    layout=list(csv.DictReader((root/'conker/retail_layout.us.txt').open()));end=max(int(x['end'],16) for x in layout if x['section']=='game');jal=0xc000000|((s.ENTRY>>2)&0x3ffffff)
    sites=[i for i in range(0x2d4b0,end-0x15000000+0x2d4b0,4) if struct.unpack_from('>I',rom,i)[0]==jal]
    assert sites==[0xd31c0,0xd31d8,0xd31f0,0xd34a8,0xd34c4,0xd34e0],sites
    pointers=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==s.ENTRY];assert not pointers,pointers
    callers=0
    for site,c in itertools.product(sites,rows[::137]):
        pc=site-0x2d4b0+0x15000000;window=struct.unpack_from('>2I',rom,site);machines=[]
        for p in programs:
            m=Machine(window,c,pc,dict(zip(range(s.ENTRY,s.ENTRY+212,4),p)))
            # The authentic delay slot loads the caller's vertex pointer.
            m.r[17]=0x40000;m.r[28]=0x10000 if site>=0xd34a8 else 0
            offset=window[1]&65535
            if window[1]>>26==35:
                value=c.vertex
                for i,b in enumerate(struct.pack('>I',value)):m.memory[m.r[17]+offset+i]=b
            else:m.r[12]=u32(c.vertex-m.r[28])
            expected_memory=dict(m.memory);m.run(pc+8);assert m.calls==[s.ENTRY] and m.memory==expected_memory
            values,flag,mask=reference(c);assert tuple(m.f[13:16])==values and (m.r[11],m.r[18])==(flag,mask)
            machines.append(m)
        assert state(machines[0])==state(machines[1])==state(machines[2]);callers+=1
    controls=(('unsigned_x',0,programs[0][0]+0x10000000),('wrong_depth_bit',21,0x240b0040),('omit_mask_update',52,0),('wrong_x_scale',32,programs[0][32]^(1<<16)),('wrong_positive_x_bit',45,0x356b0001))
    killed=[]
    for label,index,word in controls:
        p=programs[0][:];p[index]=word
        for c in rows[::13]:
            try:verify(Machine(p,c).run(),c)
            except (AssertionError,KeyError):killed.append(label);break
        else:raise AssertionError(('Ineffective control',label))
    report=dict(cases=count,streams=3,observed_words=len(seen),fired_access_prefixes=prefixes,caller_windows=6,caller_cases=callers,jal_rom_sites=sites,literal_pointers=0,negative_controls=killed,native_c_not_applicable=True,hardware_FCSR_and_full_parents_uncredited=True)
    (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
