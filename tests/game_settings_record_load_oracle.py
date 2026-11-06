"""Settings load protocol, byte aliases and the original code-integrity helper."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_settings_record_load_candidates as candidate
from tools.experiments import game_settings_record_load_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_save_defaults_oracle import WindowCode,WindowBoundary
READ,INIT,CHECK,PRECHECK=0x151DD3A0,0x151DD9E4,0x151E7EF8,0x151E7E9C
CODE_START,CODE_END,TASK,MARK=0x151DDC20,0x151DE7D4,0x10003330,0x60000
CODE_ROM=0x20B0D0
def symbols():return dict(D_800BE900=0x800BE900,D_800BE358=0x800BE358,D_800BE35A=0x800BE35A,D_800E0BE0=0x800E0BE0,D_800E0BFC=0x800E0BFC,D_8008FE30=0x8008FE30,func_151DD3A0=READ,func_151DD9E4=INIT,func_151E7EF8=CHECK)
@dataclass(frozen=True)
class Case:
    pattern:int=0
    saved:int=0
    valid:bool=True
    readmode:int=0
    effects:int=0
    phase:int=0
    connected:bool=False
    bad_code:bool=False
def packet(c):
    b=bytearray((i*31+c.pattern*71+17)&255 for i in range(32));value=(0xCC+sum(b[i]<<(i&3)for i in range(2,30)))&65535
    struct.pack_into('>H',b,0,value if c.valid else value^1);return bytes(b)
def fixture(c=Case(),s=None,rom=None):
    s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-0x600,0x400)}
    for p,n in((s['D_800BE358']-16,192),(s['D_800E0BE0']-16,96),(s['D_8008FE30']-4,16),(MARK,16)):
        m.update({(p+i)&0xFFFFFFFF:(i*29+c.pattern*71+123)&255 for i in range(n)})
    m[s['D_800E0BE0']+16]=c.saved;m[s['D_8008FE30']]=0xE2
    for i in range(3):put(m,MARK+4*i,0)
    put(m,TASK,0x11223344)
    if c.connected:
        assert rom is not None
        b=rom[CODE_ROM:CODE_ROM+CODE_END-CODE_START];assert len(b)==CODE_END-CODE_START
        assert sum(struct.unpack('>%dI'%(len(b)//4),b))&0xFFFFFFFF==0xBFC924E3
        m.update({CODE_START+i:v for i,v in enumerate(b)})
        if c.bad_code:m[CODE_START]^=1
    return m
def effect(m,c,s,phase):
    if phase==0:
        for i,v in enumerate(packet(c)):m[s['D_800BE358']+i]=v
        if c.readmode&1:m[s['D_800E0BE0']+16]=c.saved^0x55
        if c.readmode&2:m[s['D_800BE358']+23]^=0x55
        if c.readmode&4:m[s['D_8008FE30']]=0x64
    elif phase==1 and c.effects&1:m[s['D_800E0BE0']+16]^=0xA5;m[s['D_8008FE30']]=0x71
    elif phase==2 and c.effects&2:m[s['D_800E0BE0']]^=0x5A;m[s['D_8008FE30']]=0x72
    put(m,MARK+phase*4,0xA5000000+phase)
def observation(m,s):return bytes(m[s['D_800E0BE0']+i]for i in range(28))+bytes((m[s['D_8008FE30']],))
def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[(s['func_151DD3A0'],(s['D_800BE900'],0,s['D_800BE358'],32))];observations=[];trace=[];effect(m,c,s,0)
    def load(p,n=1):
        v=read(m,p,n);trace.append(('R',p,n,v));return v
    def store(p,v):
        assert p in m;put(m,p,v,1);trace.append(('W',p,1,v&255))
    checksum=0xCC
    for index in range(2,30):checksum=(checksum+(load(s['D_800BE35A']+index-2)<<(index&3)))&65535
    valid=load(s['D_800BE358'],2)==checksum;saved=load(s['D_800E0BE0']+16)
    count=s['D_800E0BFC']-s['D_800E0BE0'];assert 0<count<=128 and count%4==0
    for i in range(0,count,4):
        values=[load(s['D_800BE358']+2+i+j)for j in range(4)]if valid else[255]*4
        for j,v in enumerate(values):store(s['D_800E0BE0']+i+j,v)
    store(s['D_800E0BE0']+16,saved)
    for phase,name in((1,'func_151DD9E4'),(2,'func_151E7EF8')):
        target=s[name];calls.append((target,()));observations.append((target,observation(m,s)))
        if phase==2 and c.connected:calls.append((PRECHECK,()));observations.append((PRECHECK,observation(m,s)))
        effect(m,c,s,phase)
        if phase==2 and c.connected:
            value=sum(read(m,p)for p in range(CODE_START,CODE_END,4))&0xFFFFFFFF
            if value!=0xBFC924E3:put(m,TASK,0)
    store(s['D_8008FE30'],1)
    return dict(memory=m,calls=calls,observations=observations,trace=trace,valid=valid)
def public(m):return{p:v for p,v in m.items()if not STACK-0x600<=p<STACK+0x400}
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None):
        self.s=symbols()if s is None else s
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=())
    def record_call(self,t):
        assert t in(source.ENTRY,PRECHECK,self.s['func_151DD3A0'],self.s['func_151DD9E4'],self.s['func_151E7EF8']),hex(t)
        a=tuple(self.arguments(4))if t==self.s['func_151DD3A0']else();self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t in(PRECHECK,self.s['func_151DD9E4'],self.s['func_151E7EF8']):self.observations.append((t,observation(self.memory,self.s)))
    def hook(self,t):
        if t==self.s['func_151DD3A0']:
            assert self.calls[-1][1]==(self.s['D_800BE900'],0,self.s['D_800BE358'],32);phase=0
        else:
            assert t in(PRECHECK,self.s['func_151DD9E4'],self.s['func_151E7EF8']);phase=1 if t==self.s['func_151DD9E4']else 2
        effect(self.memory,self.case,self.s,phase)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x87654321
def helper_code(rom,c):return dict(zip(range(CHECK,CHECK+104,4),struct.unpack_from('>26I',rom,0x2153A8)))if c.connected else{}
def bound(obj,s,fitted=False):
    raw,bindings=source.function_blob(obj)
    if fitted:raw=source.normalized(raw,bindings,(candidate.ROOT/source.ROM_IMAGE).read_bytes()[source.ROM:source.ROM+source.SIZE]);bindings=source.RETAIL_BINDINGS
    original=list(struct.unpack('>%dI'%(len(raw)//4),raw));words=original[:];pending={}
    for at,rows in sorted(bindings.items()):
        assert len(rows)==1;kind,name=rows[0];value=s[name];w=original[at//4]
        if kind=='R_MIPS_HI16':pending.setdefault(name,[]).append(at)
        elif kind=='R_MIPS_LO16':
            low=((w&65535)^32768)-32768;assert name in pending,(name,at)
            for hi in pending.pop(name):
                addend=((original[hi//4]&65535)<<16)+low;words[hi//4]=(original[hi//4]&0xFFFF0000)|(((value+addend+32768)>>16)&65535)
            words[at//4]=(w&0xFFFF0000)|((value+low)&65535)
        else:
            assert kind=='R_MIPS_26';words[at//4]=(w&0xFC000000)|(((value+((w&0x3FFFFFF)<<2))>>2)&0x3FFFFFF)
    assert not pending,pending
    return words
def cases():
    for saved in range(256):yield Case(saved=saved,valid=bool(saved&1),effects=saved%4,readmode=saved%8,pattern=saved%4,phase=8*(saved%2))
    for pattern,saved,valid,readmode,effects,phase in itertools.product(range(4),(0,127,128,255),(False,True),(0,1,2,4),(0,3),(0,8)):yield Case(pattern,saved,valid,readmode,effects,phase)
def controls():
    b=candidate.SELECTED
    return dict(seed=b.replace('checksum = 0xCC','checksum = 0xCD'),weight=b.replace('index++ & 3','index++ & 7'),short_checksum=b.replace('index < 30','index < 29'),long_checksum=b.replace('index < 30','index < 31'),
      read_channel=b.replace('&D_800BE900, 0,','&D_800BE900, 1,'),read_length=b.replace('D_800BE358, 32','D_800BE358, 31'),mismatch_fill=b.replace('= -1;','= 0;'),reversed_check=b.replace('checksum != *(u16 *)','checksum == *(u16 *)'),
      wrong_copy=b.replace('record[2]','record[1]').replace('record[3]','record[2]').replace('record[4]','record[3]').replace('record[5]','record[4]'),
      short_payload=b.replace('(u32)D_800E0BFC','(u32)(D_800E0BFC - 4)'),wrong_restore=b.replace('settings[16] = saved;','settings[16] = saved ^ 1;'),
      late_snapshot=b.replace('    saved = settings[16];\n','').replace('    settings[16] = saved;','    saved = settings[16];\n    settings[16] = saved;'),
      missing_init=b.replace('    func_151DD9E4();\n',''),swapped_helpers=b.replace('    func_151DD9E4();\n    func_151E7EF8();','    func_151E7EF8();\n    func_151DD9E4();'),
      missing_flag=b.replace('    D_8008FE30 = 1;','    D_8008FE30 = 0;'),early_flag=b.replace('    D_8008FE30 = 1;','').replace('    func_151DD9E4();','    D_8008FE30 = 1;\n    func_151DD9E4();'))
