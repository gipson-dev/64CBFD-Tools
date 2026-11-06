"""Six-word ABI and independent packed-coordinate single-wrap reference."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_packed_coordinates_candidates as candidate
from tools.experiments import game_packed_coordinates_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
u32=lambda x:x&0xFFFFFFFF
signed=lambda x:((x&0xFFFFFFFF)^0x80000000)-0x80000000
BANKS,COMMANDS=0x40000,0x50000
INDICES=(4,0x5E,0x60,0x62,0x64,0x6C,0x6E,0x70,0x72,0x4A,0x177,0x253,0x255,0x257,0x13B,0x20D)
@dataclass(frozen=True)
class Case:
    slot:int=1
    entry:int=5
    dx:int=-1
    dy:int=1
    bank:int=0
    absolute:int=0
    flag:int=1
    first:int=0xF2011007
    second:int=0xD301F03F
    phase:int=0
    alias:int=0

def symbols():return dict(D_800D19A0=0x800D19A0,D_800C4488=0x800C4488)
def args(c):return tuple(u32(v)for v in(c.slot,c.entry,c.dx,c.dy,c.bank,c.absolute))
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;home=STACK+c.phase;m={home+i:(i*17+165)&255 for i in range(-0x600,0x500)}
    slot=u32(c.slot);indices=sorted(set((0,1,2,slot)))
    for sl in indices:
        table=BANKS+(sl&3)*0x100;put(m,u32(s['D_800D19A0']+sl*4),c.flag if sl==slot else 0);put(m,u32(s['D_800C4488']+sl*4),table)
        for bank in sorted(set((0,1,u32(c.bank)))):
            commands=COMMANDS+(sl&3)*0x10000+(bank&3)*0x4000;put(m,u32(table+bank*4),commands)
            for index in sorted(set((*INDICES,0,1,2,c.entry-1,c.entry,c.entry+1))):
                p=u32(commands+index*8)
                for i in range(-8,16):m[u32(p+i)]=(p+i*13+77)&255
                put(m,p,(0xA5<<24)|((index*17&4095)<<12)|(index*31&4095));put(m,u32(p+4),0xE3000000|((index*11&4095)<<12)|(index*7&4095))
    p=u32(COMMANDS+(slot&3)*0x10000+(u32(c.bank)&3)*0x4000+c.entry*8)
    if c.alias==1:
        # Command points into the incoming dx/dy homes, written by the prologue.
        p=home+8;put(m,u32(BANKS+(slot&3)*0x100+u32(c.bank)*4),u32(p-c.entry*8))
    put(m,p,c.first);put(m,u32(p+4),c.second)
    if c.alias==2:put(m,home+8,c.flag)
    for i,v in enumerate(args(c)[4:]):put(m,home+16+4*i,v)
    return m

def axis(start,delta,extent,absolute):
    value=signed(u32(start+signed(delta)))
    # One signed correction, deliberately distinct from modulo or repeated wrap.
    return (u32(delta)if absolute else value+(extent if value<0 else 0)-(extent if value>extent else 0))&4095

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);trace=[];home=STACK+c.phase
    def load(p):
        p=u32(p);v=read(m,p);trace.append(('R',p,4,v));return v
    def store(p,v):
        p=u32(p);assert all(p+i in m for i in range(4));put(m,p,v);trace.append(('W',p,4,u32(v)))
    for i,v in enumerate(args(c)[1:4]):store(home+4+4*i,v)
    flag=load(s['D_800D19A0']+u32(c.slot)*4);bank=load(home+16)
    if not flag:return dict(memory=m,trace=trace)
    table=load(s['D_800C4488']+u32(c.slot)*4);entry=load(home+4);commands=load(table+u32(bank)*4);absolute=load(home+20);p=u32(commands+(entry<<3))
    size=load(p+4);dx=load(home+8);relative_dx=load(home+8);first=load(p);dy=load(home+12)
    x=axis((first>>12)&4095,dx if absolute else relative_dx,((size>>12)&4095)+2,absolute);y=axis(first&4095,dy,(size&4095)+2,absolute)
    store(p,(first&0xFF000000)|(x<<12)|y)
    return dict(memory=m,trace=trace)

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None):
        self.s=symbols()if s is None else s
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=args(c))
    def get(self,p,n):
        if self.own_instruction:assert p%n==0,('unaligned read',p,n)
        return super().get(p,n)
    def put(self,p,v,n):
        if self.recording and self.own_instruction:
            assert p%n==0,('unaligned write',p,n);assert all(p+i in self.memory for i in range(n)),('unmapped write',p,n)
        return super().put(p,v,n)
    def record_call(self,t):
        assert t==source.ENTRY
        a=tuple(u32(v)for v in self.arguments(6));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):raise AssertionError(('Unexpected packed provider',t))

def bound(obj,s,fitted=False):
    raw,bindings=source.function_blob(obj)
    if fitted:raw=source.normalized(raw,bindings,(candidate.ROOT/source.ROM_IMAGE).read_bytes()[source.ROM:source.ROM+source.SIZE])
    original=list(struct.unpack('>%dI'%(len(raw)//4),raw));words=original[:];pending={}
    for at,rows in sorted(bindings.items()):
        assert len(rows)==1;kind,name=rows[0];value=s[name];w=original[at//4]
        if kind=='R_MIPS_HI16':pending.setdefault(name,[]).append(at)
        else:
            assert kind=='R_MIPS_LO16';low=((w&65535)^32768)-32768
            for hi in pending.pop(name,()):
                addend=((original[hi//4]&65535)<<16)+low;words[hi//4]=(original[hi//4]&0xFFFF0000)|(((value+addend+32768)>>16)&65535)
            words[at//4]=(w&0xFFFF0000)|((value+low)&65535)
    assert not pending;return words

def cases():
    for extent,old,delta,absolute,phase in itertools.product((2,3,4096,4097),(0,1,4095),(-8195,-4097,-1,0,1,4096,4097,0x7FFFFFFF,-0x80000000),(0,1),(0,8)):
        size=((extent-2)<<12)|((4099-extent)&4095);first=0xA5000000|(old<<12)|((old*37+13)&4095)
        yield Case(dx=delta,dy=-delta if delta!=-0x80000000 else delta,first=first,second=size,absolute=absolute,phase=phase,bank=old&1)
    for flag,phase in itertools.product((0,-1,0x80000000),(0,8)):yield Case(flag=flag,phase=phase)
    for extent in(2,3,4096,4097):
        old=min(4095,extent-1);yield Case(dx=0,dy=extent-old,first=0xF2000000|old,second=(17<<12)|(extent-2))

def controls():
    b=candidate.SELECTED
    return dict(missing_gate=b.replace('if ((&D_800D19A0)[slot] == 0)','if (0)'),wrong_gate=b.replace(' == 0) {',' != 0) {',1),
      wrong_entry=b.replace('*entryHome * 2','(*entryHome + 1) * 2'),wrong_bank=b.replace('[slot][bank]','[slot][bank ^ 1]'),
      short_mask=b.replace('0xFFF','0x7FF'),wrong_extent=b.replace('+ 2;','+ 1;'),x_tie=b.replace('width < x','width <= x'),y_tie=b.replace('height < y','height <= y'),
      negative_sign=b.replace('x += width','x -= width').replace('y += height','y -= height'),wrong_mode=b.replace('absolute != 0','absolute == 0'),
      wrong_high=b.replace('0xFF000000','0xFE000000'),wrong_shift=b.replace('<< 12','<< 11'),wrong_word=b.replace('    command[0] = first |','    command[1] = first |'),
      missing_store=b.replace('    command[0] = first | ((x & 0xFFF) << 12);','    first |= ((x & 0xFFF) << 12);'),
      modulo=b.replace('    first = (first &','    x %= width;\n    y %= height;\n    first = (first &'))
