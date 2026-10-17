"""Independent live-limit/FP reference, real progress chain and sequence gate."""
import itertools

from tools.experiments import game_color_channel_aggregate as source
from tools.tests import game_color_progress_oracle as progress
from tools.tests.game_animation_timeline_oracle import floating

put,read,signed,STACK=progress.put,progress.read,progress.signed,progress.STACK
BASE,LENGTH,MASK=progress.BASE,progress.LENGTH,0xFFFFFFFF
GLOBALS=dict(limit=0x80082FA0,states=0x800DDDC8,progress=progress.source.ENTRY)
SYMBOLS=dict(zip(('D_80082FA0','D_800DDDC8','func_1517EF00'),GLOBALS.values()))
RETURNS=((0,0,0,0),(1,1,1,1),(-1,-1,-1,-1),(0,1,-1,255),
    (-0x80000000,0x7FFFFFFF,0,-1),(255,0,255,0),(1,-1,1,-1))
FLOATS=((0,)*4,(0x3F800000,)*4,(0xBF800000,)*4,(0x7FC12345,)*4,
    (1,)*4,(0x7F800000,)*4,(0x80000000,)*4,(0x3F800000,0xBF800000,0x7FC12345,1),
    (0xFF800000,0x80000001,0x7F7FFFFF,0))
ACTUAL=(
    ((0,0,0,0),)*4,((0,0,1,0),)*4,((-1,1,1,0),)*4,
    ((0,0,0,0),(-1,1,1,0),(0,0,1,0),(0,0,0,255)),
    ((-1,1,0,0),)*4,((-0x80000000,1,1,0),)*4,
    ((-0x80000000,-1,1,0),)*4,((0,0,0,1),(0,0,0,255),(0,0,0,0),(0,0,1,0)),
    ((2,1,1,0),)*4)
CALLER,CALLER_ROM=0x151E8214,0x2156C4
SCRIPT=(('timer',0x800E0A90,4),('stage',0x800E0B94,1),('fade',0x8008FDCC,2),
    ('left',0x8008FD8C,1),('right',0x8008FD90,1),('flag',0x8008FDA4,1),
    ('state',0x800E0A80,2),('command',0x800D2E43,1))


def fixture(limit=0,pattern=0,fp=0,action=0,alias=0,actual=False):
    memory,_,_=progress.fixture();g=dict(GLOBALS)
    if alias==1:g['limit']=g['states']
    elif alias==2:g['states']=progress.GLOBALS['ticks']
    for i,value in enumerate(FLOATS[fp]):put(memory,g['states']+i*4,value)
    for channel in range(4):
        ticks,duration,mode,busy=ACTUAL[pattern][channel] if actual else (0,0,0,0)
        for name,value,width in (('ticks',ticks,4),('limits',duration,4),('modes',mode,1),('busy',busy,1)):
            put(memory,progress.GLOBALS[name]+channel*width,value&((1<<(width*8))-1),width)
    for i in range(-8,12):memory.setdefault(g['limit']+i,(i*13+0xA5)&255)
    put(memory,g['limit'],limit&MASK)
    return memory,dict(pattern=pattern,action=action,actual=actual),g


def cases():
    for limit,pattern,fp,action in itertools.product((-2,-1,0,1,3),range(7),range(9),range(6)):
        yield fixture(limit,pattern,fp,action)
    for alias,limit,pattern,fp,action in itertools.product((1,2),(0,1,3),(0,2,3),(0,1,3),(0,1,2,4,5)):
        yield fixture(limit,pattern,fp,action,alias)
    for limit,pattern,fp in itertools.product((-2,-1,0,1,3),range(len(ACTUAL)),range(9)):
        yield fixture(limit,pattern,fp,actual=True)
    for limit,action in itertools.product((-0x80000000,0x7FFFFFFF),(1,4,5)):
        yield fixture(limit,4,3,action)


def effects(channel,action,g):
    if action==1 and channel==0:return ((g['limit'],MASK),)
    if action==2 and channel==0:return ((g['limit'],3),)
    if action==3:return ((g['states']+channel*4,0xBF800000 if channel&1 else 0x3F800000),)
    if action==4 and channel<2:return ((g['limit'],1 if channel==0 else MASK),)
    if action==5:return ((g['states']+channel*4,0),(g['limit'],3 if channel==0 else 0))
    return ()


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x200<=a<STACK+0x100}


class Reference:
    def __init__(self,memory,config,g):self.memory,self.config,self.g,self.calls=dict(memory),config,g,[]

    def run(self):
        active=-1;channel=0
        while channel<=signed(read(self.memory,self.g['limit'])):
            assert channel<4,'Fixture exceeds bounded array domain'
            self.calls.append((self.g['progress'],(channel,)))
            if self.config['actual']:
                value,trap=progress.reference(self.memory,channel)
                if trap:raise progress.DivisionTrap(trap)
            else:
                value=RETURNS[self.config['pattern']][channel]&MASK
                for address,bits in effects(channel,self.config['action'],self.g):put(self.memory,address,bits)
            if signed(value)>0 or floating(read(self.memory,self.g['states']+channel*4))>0.0:active+=1
            channel+=1
        return int(active==signed(read(self.memory,self.g['limit'])))


def script_fixture(limit=0,pattern=0,fp=0,stage=7,timer=0):
    memory,config,g=fixture(limit,pattern,fp,actual=True)
    for _,at,width in SCRIPT:
        for i in range(-4,width+4):memory.setdefault(at+i,0xA5)
        put(memory,at,0xA5A5A5A5&((1<<(width*8))-1),width)
    put(memory,dict((n,a) for n,a,_ in SCRIPT)['stage'],stage,1)
    put(memory,dict((n,a) for n,a,_ in SCRIPT)['timer'],timer&MASK)
    return memory,config,g


def script_cases():
    for limit,pattern,fp,stage,timer in itertools.product((-2,-1,0,1,3),range(len(ACTUAL)),
            (0,1,3,7),(7,8),(-1,0,160,161,0x7FFFFFFF)):
        yield script_fixture(limit,pattern,fp,stage,timer)


class ScriptReference(Reference):
    def run(self):
        fields={n:(a,w) for n,a,w in SCRIPT}
        if read(self.memory,fields['stage'][0],1)==8:return
        self.calls.append((source.ENTRY,()))
        if not super().run():put(self.memory,fields['timer'][0],0)
        if signed(read(self.memory,fields['timer'][0]))>=161:
            for name,value in (('fade',0),('stage',8),('left',1),('right',1),('flag',0),
                    ('state',65534),('timer',0),('command',1)):
                at,width=fields[name];put(self.memory,at,value,width)


class AggregateOracle(progress.ProgressInstructions,progress.previous.ColorOracle):
    def __init__(self,words,memory,config,g,phase=0,entry=source.ENTRY,helpers=None):
        super().__init__(words,memory,(0x12345678,),phase,entry,helpers)
        self.config,self.globals=config,g;self.role_observations=[]

    def record_call(self,target):
        if target==source.ENTRY:args=()
        elif target==self.globals['progress']:
            args=self.arguments(1);stack=self.r[29]
            self.role_observations.append(dict(channel=self.r[16],active=self.r[17],limit=self.r[18],
                states=self.r[19],f20=self.f[20],stack=stack,
                saved_pair=read(self.memory,stack+0x10,8),saved_gprs=tuple(read(self.memory,stack+p) for p in (0x1C,0x20,0x24,0x28,0x2C))))
        else:raise ValueError('Unknown aggregate call target')
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target!=self.globals['progress'] or self.config['actual']:
            raise ValueError('Actual aggregate/progress helper must execute')
        channel=self.calls[-1][1][0]
        if not 0<=channel<4:raise ValueError('Opaque channel is outside fixture domain')
        value=RETURNS[self.config['pattern']][channel]&MASK
        for address,bits in effects(channel,self.config['action'],self.globals):self.put(address,bits,4)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.lo,self.hi=0xA5000010,0xA5000011
        self.r[2]=value
