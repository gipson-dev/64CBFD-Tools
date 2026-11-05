"""Independent live-global protocol and instruction model for the mode dispatcher."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_live_mode_dispatch_candidates as candidate
from tools.experiments import game_live_mode_dispatch_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_character_effect_pair import WindowCode as BaseWindowCode,WindowBoundary
CMD,RENDER,LEAF=0x15042D78,0x151E6964,0x151DE8E8
HANDLERS=(0x151DDC20,0x151DE81C,LEAF,0x151DE8F0,0x151E4E64,0x151E4264,0x151E43DC,0x151E4EE8,0x151E82B8,0x151E83E8,0x151E4DD8,0x151DE6D4)
WIDTHS=dict(D_800E0B94=1,D_800E0B95=1,D_800E0BDC=1,D_800BE930=2,D_800E0B9A=2,D_800E0A90=4,D_800BE9E4=4,D_8008FE28=1,D_8003C8E0=4,D_800CBD74=1,D_800BE615=1)
u32=lambda v:v&0xFFFFFFFF
def symbols():return dict({name:int(name[2:],16)for name in WIDTHS},D_8008FDEC=0x8008FDEC,func_15042D78=CMD,func_151E6964=RENDER)
@dataclass(frozen=True)
class Case:
    mode:int=0
    countdown:int=0
    buttons:int=0xA55A
    timer:int=0xFFFFFFFE
    ticks:int=3
    after_command:int=-1
    after_render:int=-1
    after_callback:int=-1
    mutation:int=0
    table_change:bool=False
    command_real:bool=False
    leaf:bool=False
    caller_after:int=-1
    phase:int=0
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+i:(i*17+165)&255 for i in range(-0x400,0x400)}
    values=dict(D_800E0B94=c.mode,D_800E0B95=0xD3,D_800E0BDC=0x31,D_800BE930=c.buttons,D_800E0B9A=0x5A5A,D_800E0A90=c.timer,D_800BE9E4=c.ticks,D_8008FE28=c.countdown,D_8003C8E0=0x87654321,D_800CBD74=0x42,D_800BE615=0)
    # Actual table has twelve entries, followed nearby by the countdown byte.
    # Rebased fixtures may provide 256 disjoint slots without extending that physical table.
    for i in range(12 if s['D_8008FDEC']==0x8008FDEC else 256):put(m,s['D_8008FDEC']+4*i,HANDLERS[i%12])
    for name,value in values.items():put(m,s[name],value,WIDTHS[name])
    return m
def snapshot(m,s):return tuple(read(m,s[n],z)for n,z in WIDTHS.items())
def effect(m,c,s,phase):
    mode=(c.after_command,c.after_render,c.after_callback)[phase]
    if mode>=0:put(m,s['D_800E0B94'],mode,1)
    if c.mutation&(1<<phase):
        put(m,s['D_800E0A90'],(0x80000000,0xFFFFFFFE,0x7FFFFFFF)[phase]);put(m,s['D_800BE9E4'],(0xFFFFFFFF,3,0x80000001)[phase])
        if phase==0:put(m,s['D_8008FE28'],255,1);put(m,s['D_800BE930'],0x8001,2)
        else:put(m,s['D_800E0B9A'],(0x4321,0x8765)[phase-1],2);put(m,s['D_800E0BDC'],0x30+phase,1)
    if phase==1 and c.table_change:
        mode=read(m,s['D_800E0B94'],1);put(m,s['D_8008FDEC']+mode*4,HANDLERS[(mode+1)%12])
    if phase==2 and c.caller_after>=0:put(m,s['D_800BE615'],c.caller_after,1)
def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[];observations=[];previous=read(m,s['D_800E0B94'],1)
    def call(t,args,phase):
        calls.append((t,args));observations.append((t,snapshot(m,s)));effect(m,c,s,phase)
    put(m,s['D_8003C8E0'],0x08000000);put(m,s['D_800E0BDC'],255,1)
    call(s['func_15042D78'],(0x81,),0);put(m,s['D_800CBD74'],0x81,1)
    put(m,s['D_800E0B9A'],read(m,s['D_800BE930'],2),2)
    count=read(m,s['D_8008FE28'],1)
    if count:put(m,s['D_8008FE28'],count-1,1);put(m,s['D_800E0B9A'],0,2)
    mode=read(m,s['D_800E0B94'],1);call(s['func_151E6964'],(2 if mode==0 else 4 if mode==8 else 1,),1)
    mode=read(m,s['D_800E0B94'],1);target=read(m,s['D_8008FDEC']+mode*4)
    assert target in HANDLERS,('unowned callback',hex(target));call(target,(),2)
    mode=read(m,s['D_800E0B94'],1)
    if mode!=7:
        put(m,s['D_800E0A90'],read(m,s['D_800E0A90'])+read(m,s['D_800BE9E4']))
        if mode!=previous:put(m,s['D_800E0B95'],previous,1);put(m,s['D_800E0A90'],0)
    put(m,s['D_8003C8E0'],0)
    return dict(memory=m,calls=calls,observations=observations)
class WindowCode(BaseWindowCode):
    def __getitem__(self,pc):
        if pc in self.ends:self.owner.current_pc=pc;self.owner.delay_of=None;raise WindowBoundary
        return super().__getitem__(pc)
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None):
        self.s=symbols()if s is None else s;self.observations=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=())
    def record_call(self,t):
        if t==source.ENTRY:a=()
        elif t in(self.s['func_15042D78'],self.s['func_151E6964']):a=tuple(map(u32,self.arguments(1)))
        else:assert t in HANDLERS,('unowned callback',hex(t));a=()
        self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t!=source.ENTRY:
            self.observations.append((t,snapshot(self.memory,self.s)))
            effect(self.memory,self.case,self.s,0 if t==self.s['func_15042D78']else 1 if t==self.s['func_151E6964']else 2)
    def hook(self,t):
        if t==self.s['func_15042D78']:put(self.memory,self.s['D_800CBD74'],self.r[4]&255,1)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x87654321
def public(m):return {p:v for p,v in m.items()if not STACK-0x400<=p<STACK+0x400}
def helper_code(rom,c):
    code={}
    for entry,offset,n,enabled in((CMD,0x70228,7,c.command_real),(LEAF,0x20BD98,2,c.leaf)):
        if enabled:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code
def bound(obj,s):
    raw,bindings=source.function_blob(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for at,rows in bindings.items():
        word=words[at//4]
        for kind,name in rows:
            value=s[name]
            if kind=='R_MIPS_26':word=(word&0xFC000000)|((value>>2)&0x3FFFFFF)
            elif kind=='R_MIPS_HI16':word=(word&0xFFFF0000)|(((value+0x8000)>>16)&65535)
            elif kind=='R_MIPS_LO16':word=(word&0xFFFF0000)|(value&65535)
            else:raise AssertionError(kind)
        words[at//4]=word
    return words
def cases():
    for mode,count,phase in itertools.product(range(12),(0,1,2,127,128,255),(0,8)):yield Case(mode=mode,countdown=count,phase=phase)
    for initial,after_command,after_render,after_callback,phase in itertools.product((0,7,8,11),(0,8,11),(0,7,8,11),(0,7,8,11),(0,8)):
        yield Case(mode=initial,after_command=after_command,after_render=after_render,after_callback=after_callback,phase=phase,table_change=after_render==8)
    for field in('mode','countdown'):
        for value,phase in itertools.product(range(12)if field=='mode'else range(256),(0,8)):yield Case(**{field:value},phase=phase)
    for mode,timer,ticks,phase in itertools.product((0,7,8),(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,0x80000000,0xFFFFFFFF),(0,8)):
        yield Case(mode=mode,timer=timer,ticks=ticks,phase=phase)
    for mutation,mode,phase in itertools.product(range(8),(0,7,8,11),(0,8)):yield Case(mode=mode,mutation=mutation,table_change=True,phase=phase)
    for mode,phase in itertools.product(range(12),(0,8)):yield Case(mode=mode,command_real=True,phase=phase)
    for phase in(0,8):yield Case(mode=2,leaf=True,command_real=True,phase=phase)
def controls():
    b=candidate.SELECTED
    return dict(late_previous=b.replace('u8 previous = D_800E0B94;','u8 previous;').replace('    D_800E0B9A = D_800BE930;','    previous = D_800E0B94;\n    D_800E0B9A = D_800BE930;'),
      positive_countdown=b.replace('D_8008FE28 != 0','D_8008FE28 > 0'),
      preserve_last_count=b.replace('        D_800E0B9A = 0;','        if (D_8008FE28 != 0) D_800E0B9A = 0;'),
      wrong_zero_mode=b.replace('func_151E6964(2)','func_151E6964(1)'),
      wrong_eight_mode=b.replace('func_151E6964(4)','func_151E6964(2)'),
      stale_callback=b.replace('D_8008FDEC[D_800E0B94]()','D_8008FDEC[previous]()'),
      entry_mode_seven=b.replace('if (D_800E0B94 != 7)','if (previous != 7)'),
      late_previous_store=b.replace('D_800E0B95 = previous','D_800E0B95 = D_800E0B94'),
      missing_transition_reset=b.replace('            D_800E0A90 = 0;',''),
      wrong_timer=b.replace('(u32)D_800E0A90 + (u32)D_800BE9E4','(u32)D_800E0A90 + 1u'),
      missing_end_flag=b.replace('    D_8003C8E0 = 0;',''),
      wrong_begin_flag=b.replace('0x08000000','0x04000000'))
