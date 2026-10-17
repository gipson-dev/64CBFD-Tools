"""Independent signed progress reference and scoped emitted DIV/BREAK execution."""
import itertools

from tools.experiments import game_color_progress as source
from tools.tests import game_color_state_submit_oracle as previous
from tools.tests import test_game_record_player_registration_match as registration
from tools.tests.game_sequence_event_scan_oracle import load_signed_byte

put,read,signed,STACK=previous.put,previous.read,previous.signed,previous.STACK
MASK,BASE,LENGTH=0xFFFFFFFF,previous.BASE,previous.LENGTH
GLOBALS={name:previous.GLOBALS[name] for name in ('busy','limits','ticks','modes')}
SYMBOLS=dict(zip(('D_800DDDC0','D_800DDE28','D_800DDDB0','D_800DDDAC'),GLOBALS.values()))
NAMES=tuple(GLOBALS)
TICKS=(0,1,-1,127,255,256,-256,8421504,8421505,0x7FFFFFFF,-0x80000000)
LIMITS=(0,1,-1,2,-2,255,256,0x7FFFFFFF,-0x80000000)
MODES=(-128,-1,0,1,127)
RENDER=0x1517F08C


def address(base,channel,width=1):return (base+channel*width)&MASK


def fixture(channel=0,ticks=0,duration=0,mode=0,busy=0,alias=0):
    g=dict(GLOBALS)
    if alias==1:g['ticks']=g['limits']
    elif alias==2:g['modes']=g['busy']
    elif alias==3:g['busy']=g['modes']
    elif alias==4:g['modes']=g['ticks']
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x200,0x100)}
    memory.update({BASE+i:(i*13+0xA5)&255 for i in range(LENGTH)})
    for name,value,width in (('ticks',ticks,4),('limits',duration,4),('modes',mode,1),('busy',busy,1)):
        at=address(g[name],channel,width)
        for i in range(-4,width+4):memory.setdefault((at+i)&MASK,(i*13+0xA5)&255)
        put(memory,at,value&((1<<(width*8))-1),width)
    return memory,(channel&MASK,),g


def cases():
    for channel,ticks,duration,mode,busy in itertools.product(range(4),TICKS,LIMITS,MODES,(0,1,255)):
        yield fixture(channel,ticks,duration,mode,busy)
    for alias,channel,ticks,duration,mode,busy in itertools.product(range(1,5),range(4),(-1,-0x80000000),(-1,0,1),(0,127),(0,255)):
        yield fixture(channel,ticks,duration,mode,busy,alias)
    for channel,ticks,duration,mode,busy in itertools.product((-1,0x10000,0x40000000,0x80000000),
            (-1,-0x80000000),(0,1,-1),(0,127),(0,255)):
        yield fixture(channel,ticks,duration,mode,busy)


def reference(memory,channel,g=GLOBALS):
    busy=read(memory,address(g['busy'],channel),1)
    if busy:return busy,None
    duration=signed(read(memory,address(g['limits'],channel,4)))
    value=255
    if duration:
        product=signed((read(memory,address(g['ticks'],channel,4))*255)&MASK)
        if product==-0x80000000 and duration==-1:return None,6
        value=abs(product)//abs(duration)
        if (product<0)!=(duration<0):value=-value
        value=min(value,255)
    if read(memory,address(g['modes'],channel),1)==0:value=(255-value)&MASK
    return value&MASK,None


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x200<=a<STACK+0x100}


class DivisionTrap(Exception):
    def __init__(self,code):self.code=code


class ProgressInstructions:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.hi=0x89ABCDEF

    def execute(self,word):
        op,fn,rs,rt=word>>26,word&63,word>>21&31,word>>16&31
        if op==32:load_signed_byte(self,word)
        elif op==0 and fn==26:
            left,right=signed(self.r[rs]),signed(self.r[rt])
            if not right:raise AssertionError('Zero-divisor guard is unreachable for stable inputs')
            value=(abs(left)//abs(right))*(-1 if (left<0)!=(right<0) else 1)
            self.lo=value&MASK;self.hi=(left-value*right)&MASK
        elif op==0 and fn==13:
            if word not in (0x0006000D,0x0007000D):raise AssertionError('Unknown compiler BREAK encoding')
            raise DivisionTrap(word>>16)
        else:super().execute(word)


class ProgressOracle(ProgressInstructions,previous.ColorOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,helpers=None):
        super().__init__(words,memory,args,phase,entry,helpers)

    def record_call(self,target):
        if target not in (source.ENTRY,RENDER):raise ValueError('Unknown progress caller')
        args=self.arguments(1 if target==source.ENTRY else 6)
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target!=RENDER:raise ValueError('Progress helper must execute, not be hooked')
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.r[2]=0x13579BDF


class RegistrationReference(registration.ConstructionReference):
    def call(self,role,args):
        result=super().call(role,args)
        if role=='func_1517EF00':
            result,trap=reference(self.memory,args[0])
            if trap:raise DivisionTrap(trap)
        return result


class RegistrationOracle(ProgressInstructions,registration.ConstructionOracle):
    pass
