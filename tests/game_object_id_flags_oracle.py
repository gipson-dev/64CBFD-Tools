"""Independent ID-priority reference and ordered guest memory observations."""
from dataclasses import dataclass
from functools import lru_cache
import struct
from tools.experiments import game_object_id_flags_candidates as candidate
from tools.experiments import game_object_id_flags_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

CALLER,CONSUMER=0x150627D4,0x15039CC8
@dataclass(frozen=True)
class Case:
    identity:int=233
    flags:int=128
    state:int=1
    dataset:int=0
    owner:int=0x30000
    phase:int=0
    effect:int=0

def symbols(base=source.TABLE):
    return dict(D_8009877C=base,D_8009877E=base+2,D_80098780=base+4,D_80098830=base+180,D_80098836=base+186)

@lru_cache(maxsize=2)
def table(dataset=0):
    b=(candidate.ROOT/source.ROM_IMAGE).read_bytes()[source.TABLE_ROM:source.TABLE_ROM+source.TABLE_SIZE]
    values=list(struct.unpack('>94H',b))
    if dataset:
        values[:4]=[0x8001,0xFFFF,0x8002,0x8000]
        values[90:93]=[0x8000,0x8003,0x8004]
    return tuple(values)

def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-0x600,0x400)}
    m.update({c.owner+i:(i*29+123)&255 for i in range(-16,0x33C)})
    base=s['D_8009877C'];m.update({base+i:(i*31+117)&255 for i in range(-16,204)})
    for i,v in enumerate(table(c.dataset)):put(m,base+2*i,v,2)
    put(m,c.owner,c.state);put(m,c.owner+0x84,c.identity,2);put(m,c.owner+0x2FB,c.flags,1);put(m,c.owner+0x324,0)
    return m

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);trace=[]
    def load(p,n):
        v=read(m,p,n);trace.append(('R',p,n,v));return v
    def flag(mask):
        p=c.owner+0x2FB;v=load(p,1)|mask;put(m,p,v,1);trace.append(('W',p,1,v))
    if load(c.owner,4)==1:
        identity=load(c.owner+0x84,2)
        for p in range(s['D_80098830'],s['D_80098836'],2):
            if identity==load(p,2):flag(2);return m,trace
        for p in(s['D_8009877C'],s['D_8009877E'],*range(s['D_80098780'],s['D_80098780']+176,2)):
            if identity==load(p,2):flag(1);break
    return m,trace

def public(m):return{p:v for p,v in m.items()if not STACK-0x600<=p<STACK+0x400}

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None):
        self.s=symbols()if s is None else s
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.owner,))
    def get(self,p,n):
        if self.own_instruction:assert p%n==0,('unaligned read',p,n)
        return super().get(p,n)
    def record_call(self,t):
        assert t in(source.ENTRY,CONSUMER),hex(t)
        a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==CONSUMER:self.observations.append((a[0],read(self.memory,a[0]+0x2FB,1)))
    def hook(self,t):
        assert t==CONSUMER
        p=self.calls[-1][1][0];self.memory[p+0x2FB]|=self.case.effect
        # Opaque consumer effects must survive the wrapper's return.
        if self.case.effect:put(self.memory,p+0x84,0xBEEF,2)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.hi,self.lo=0xA5000010,0xA5000011

def bound(obj,s,fitted=False):
    raw,bindings=source.function_blob(obj)
    if fitted:
        raw=source.normalized(raw,bindings,(candidate.ROOT/source.ROM_IMAGE).read_bytes()[source.ROM:source.ROM+source.SIZE]);bindings=source.fitted_bindings()
    original=list(struct.unpack('>%dI'%(len(raw)//4),raw));words=original[:];pending={}
    for at,rows in sorted(bindings.items()):
        assert len(rows)==1;kind,name=rows[0];value=s[name];w=original[at//4]
        if kind=='R_MIPS_HI16':pending.setdefault(name,[]).append(at)
        else:
            assert kind=='R_MIPS_LO16';low=((w&65535)^32768)-32768
            # A compiler control can share a resolved HI across later LOs.
            for hi in pending.pop(name,()):
                addend=((original[hi//4]&65535)<<16)+low;words[hi//4]=(original[hi//4]&0xFFFF0000)|(((value+addend+32768)>>16)&65535)
            words[at//4]=(w&0xFFFF0000)|((value+low)&65535)
    assert not pending
    return words

def cases():
    for dataset in(0,1):
        for identity in sorted(set(table(dataset)+(0,0xFF,0x100,0x7FFF,0x8000,0xFFFF))):
            for flags in(0,3,128,255):yield Case(identity,flags,dataset=dataset)
        for state in(0,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
            for identity in(0,233,0x8000,0xFFFF):yield Case(identity,255,state,dataset)

def controls():
    b=candidate.SELECTED
    return dict(wrong_state=b.replace('!= 1','!= 2'),primary_mask=b.replace('|= 2','|= 1'),secondary_mask=b.replace('|= 1','|= 2'),
      assignment=b.replace('|=','= '),primary_short=b.replace('end = D_80098836','end = D_80098836 - 1'),primary_long=b.replace('cursor < (u32)end','cursor <= (u32)end'),
      lower_short=b.replace('index < 88','index < 87'),lower_start=b.replace('index = 0','index = 1'),
      scalar_first=b.replace('identity == D_8009877C','identity == 0x10000'),scalar_second=b.replace('identity == D_8009877E','identity == 0x10000'),
      signed_identity=b.replace('identity = object->unk84.uh','identity = (s16)object->unk84.uh'),truncate_identity=b.replace('identity = object->unk84.uh','identity = (u8)object->unk84.uh'),
      primary_priority=b.replace('object->unk2FB |= 2;\n            return;','object->unk2FB |= 2;'))
