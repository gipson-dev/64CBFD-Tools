"""Independent viewport/border model, live callback effects and TRUNC prefixes."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-next-151103C8-match'
from tools.tests.game_paired_float_approach_1505a250_oracle import Oracle as FloatOracle,bits,floating,rounded
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY,VIEWS,COMMANDS,FILL,SCISSOR,RECT=0x151103C8,0x30000,0x50000,0x15110544,0x1501A490,0x1501A6CC
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
class ConversionBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
 index:int=0
 mode:int=2
 width:int=292
 height:int=216
 view:tuple=(0x3F800000,0,0x43900000,0x43580000)
 colors:tuple=(255,128,1)
 mutation:int=0
 after:int=1
 returns:int=0
 alias:int=0
 homes:tuple=(0x3F800000,0x80000000,0x87654321)
 phase:int=0
 seed:int=0
def symbols():return {n:int(n.split('_')[1],16)for n in('D_80082FA0','D_80082FA4','D_800BE628','D_800DBEA8','D_800BE620','D_800BE624','func_15110544','func_1501A490','func_1501A6CC')}
def selected(c):return STACK+c.phase+4-0x24 if c.alias==2 else u32(VIEWS+u32(c.index)*0x180)
def cursor(c,s=None):return(s or symbols())['D_800BE620']if c.alias==1 else COMMANDS
def fixture(c,s=None):
 s=s or symbols();m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,768)}
 for a,n in((selected(c)-16,0x1A0),(COMMANDS-16,0x1010),(s['D_800BE620']-16,96),(s['D_80082FA0']-16,48),(s['D_800DBEA8']-4,12)):m.update({a+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 for n,v in(('D_80082FA0',c.mode),('D_80082FA4',c.index),('D_800BE620',c.width),('D_800BE624',c.height),('D_800BE628',u32(selected(c)-u32(c.index)*0x180))):put(m,s[n],v)
 for a,v in zip((0x2C,0x24,0x30,0x28),c.view):put(m,selected(c)+a,v)
 for i,v in enumerate(c.colors):put(m,s['D_800DBEA8']+i,v,1)
 return m
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+768}
def effect(m,c,s,t,args,ordinal):
 p=args[0];put(m,p,0xAB000000|ordinal);put(m,p+4,t)
 if c.mutation&1 and t==s['func_15110544']:put(m,s['D_80082FA0'],c.after);put(m,s['D_80082FA4'],0)
 if c.mutation&2 and t==s['func_1501A490']:put(m,s['D_800BE620'],17);put(m,s['D_800BE624'],u32(-15))
 if c.mutation&4 and t==s['func_1501A6CC']and ordinal==3:put(m,s['D_80082FA0'],c.after);put(m,s['D_800BE620'],u32(-31));put(m,s['D_800BE624'],33)
 if c.mutation&8:
  for i,v in enumerate((0,0,0)):put(m,s['D_800DBEA8']+i,v,1)
 return COMMANDS+0x200+ordinal*0x80 if c.returns else u32(p+{s['func_15110544']:40,s['func_1501A490']:16,s['func_1501A6CC']:8}[t])
def trunc(value):
 if not math.isfinite(value)or not -2147483648<=value<2147483648:raise ConversionBoundary
 return u32(math.trunc(value))
def reference(initial,c,s=None):
 s=s or symbols();m=dict(initial);calls=[];p=cursor(c,s)
 for i,v in enumerate(c.homes):put(m,STACK+c.phase+4+4*i,v)
 view=u32(read(m,s['D_800BE628'])+read(m,s['D_80082FA4'])*0x180)
 try:
  left=trunc(floating(read(m,view+0x2C)));top=trunc(floating(read(m,view+0x24)));bottom=trunc(floating(read(m,view+0x28)));right=trunc(rounded(floating(read(m,view+0x30))-1.))
 except ConversionBoundary:return m,calls,p,False
 def call(t,args):
  args=tuple(map(u32,args));calls.append((t,args));return effect(m,c,s,t,args,len(calls))
 p=call(s['func_15110544'],(p,left,top,right,bottom,*[read(m,s['D_800DBEA8']+i,1)for i in range(3)]))
 if read(m,s['D_80082FA0'])!=0 and read(m,s['D_80082FA4'])==0:
  put(m,p,0xE7000000);put(m,p+4,0);p=u32(p+8);p=call(s['func_1501A490'],(p,255,0,0,0,0));put(m,p,0xF7000000);put(m,p+4,0x00010001);p=u32(p+8)
  half=signed(read(m,s['D_800BE624']))>>1;p=call(s['func_1501A6CC'],(p,0,half-6,read(m,s['D_800BE620']),half+6))
  if read(m,s['D_80082FA0'])!=1:
   half=signed(read(m,s['D_800BE620']))>>1;p=call(s['func_1501A6CC'],(p,half-1,0,half+1,read(m,s['D_800BE624'])))
 return m,calls,p,True
class Oracle(FloatOracle):
 def __init__(self,ws,memory,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=s or symbols();self.prefix=None;FactoryOracle.__init__(self,ws,memory,c,entry=entry,arguments=(cursor(c,self.s),*c.homes),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,fs,fd,fn=w>>26,w>>21&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn==13:
   value=floating(self.f[fs])
   try:self.f[fd]=trunc(value)
   except ConversionBoundary:self.prefix=dict(pc=self.current_pc,operand=self.f[fs]);raise
  else:super().execute(w)
 def record_call(self,t):
  counts={self.s['func_15110544']:8,self.s['func_1501A490']:6,self.s['func_1501A6CC']:5,ENTRY:4};assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  ordinal=sum(a in(self.s['func_15110544'],self.s['func_1501A490'],self.s['func_1501A6CC'])for a,_ in self.calls);value=effect(self.memory,self.c,self.s,t,self.calls[-1][1],ordinal)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=value
def words(path,s=None):
 text,fs,rs=parse_object(path);a,n=fs['func_151103C8']['value'],fs['func_151103C8']['size'];return bound_blob(text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s or symbols())
def check(m,c,s=None):
 expected,calls,answer,valid=reference(m.initial,c,s);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory)==public(expected),(c,'public');assert valid==(m.prefix is None),(c,'conversion-domain')
 if valid:assert m.r[2]==answer and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],(c,'return-ABI')
 for i,v in enumerate(c.homes):assert read(m.memory,STACK+c.phase+4+4*i)==v,(c,'unused-float-home')
def run(ws,c,s=None):
 m=Oracle(ws,fixture(c,s),c,s=s)
 try:m.run()
 except ConversionBoundary:pass
 check(m,c,s);return m
def cases():
 cs=[Case(index=i,mode=mode,mutation=mu,after=a,returns=r)for i,mode,mu,a,r in itertools.product((0,1,3),(0,1,2,0xFFFFFFFF),(0,1,2,4,15),(0,1,2),(0,1))]
 for width,height in itertools.product((0,1,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF)):cs.append(Case(width=width,height=height))
 patterns=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x3FC00000,0xBFC00000,0x4EFFFFFF,0x4F000000,0xCF000000,0xCF000001,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC12345)
 for i,v in itertools.product(range(4),patterns):
  view=list(Case().view);view[i]=v;cs.append(Case(view=tuple(view)))
 for i in(0xFFFFFFFF,0x80000000,0x7FFFFFFF,0x10000000):cs.append(Case(index=i))
 for alias,mu,r in itertools.product((1,2),(0,15),(0,1)):cs.append(Case(alias=alias,mutation=mu,returns=r))
 for h in(0,0x80000000,0x7F800001,0xFFFFFFFF):cs.append(Case(homes=(h,h^0x12345678,h^0xFFFFFFFF)))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();truth=struct.unpack_from('>95I',(root/'conker/conker.us.bin').read_bytes(),0x13D878);raw=words(out/'selected.o');assert raw==list(truth);seen=set();invalid=0
 for c in cs:
  a,b=[run(ws,c)for ws in(raw,truth)];assert(a.memory,a.r,a.f,a.trace,a.calls,a.prefix)==(b.memory,b.r,b.f,b.trace,b.calls,b.prefix),(c,'machine');invalid+=a.prefix is not None;seen.update((pc-ENTRY)//4 for pc in a.visits if ENTRY<=pc<ENTRY+380)
 report=dict(cases=len(cs),executions=2*len(cs),coverage=len(seen),missing=[i for i in range(95)if i not in seen],complete_machine_and_trace_pairs=len(cs),invalid_conversion_prefixes=invalid,unused_float_homes_checked=True,sparse_word_indices_and_aliases_guest_only=True,FCSR_or_hardware_qualified=False);(out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
