"""Independent sequence-direction model and observable guest helper contract."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-next-1501FE68-match'
from tools.experiments import game_sequence_direction_1501fe68_match as p
from tools.experiments import game_sequence_direction_1501fe68_match as n
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_paired_float_approach_1505a250_oracle import bits,floating,rounded,canonical
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=p.ENTRY;F72=0x1501F72C;FFE=0x1501FFE8;ANGLE=0x150484A0
ROWS=(0x30000,0x31000);ALTROW=0x32000;RUNTIMES=(0x40000,0x41000);KEYS=0x50000;ALTKEYS=0x51000;OUTPUT=0x60000;ALTOUT=0x60100
NAMES=('D_800C35C8','D_800C3A50','D_800C3868','D_800969D8','D_800969DC','func_1501F72C','func_1501FFE8','func_150484A0')
SYMS={name:int(name.split('_')[1],16)for name in NAMES};u32=lambda x:x&0xFFFFFFFF
POINTS=tuple(bits(v)for v in(8.0,-2.0,15.0,-3.0,4.0,1.0))
MATRIX=tuple(bits(v)for v in(0.,1.,2.,3.,4.,5.,12.,7.,21.,9.,10.,11.))
@dataclass(frozen=True)
class Case:
 group:int=0
 index:int=0
 count:int=2
 percentage:int=0x42480000
 duration:int=0x41200000
 flag:int=0
 frame:int=0
 angle:int=0x3F000000
 scale:int=0x42652EE0
 mutation:int=0
 alias:int=0
 invalid:int=0
 phase:int=0
 seed:int=0
def output(c,s=SYMS):return (OUTPUT,s['D_800969DC'],KEYS,ROWS[c.group],STACK+c.phase+8,0)[c.alias]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
 for base,length in((s['D_800C35C8']-16,0x30),(s['D_800C3A50']-16,0x30),(s['D_800C3868']-16,0x120),(s['D_800969D8']-16,0x30),(ROWS[0],0x40),(ROWS[1],0x40),(ALTROW,0x40),(RUNTIMES[0],0x100),(RUNTIMES[1],0x100),(KEYS,0x50),(ALTKEYS,0x50),(OUTPUT,0x20),(ALTOUT,0x20)):
  m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(length)})
 for group in range(2):
  put(m,s['D_800C35C8']+4*group,ROWS[group]);put(m,s['D_800C3A50']+4*group,RUNTIMES[group])
  for index in range(2):put(m,s['D_800C3868']+120*group+4*index,KEYS)
 put(m,ROWS[c.group]+2*c.index,c.count,2);put(m,ALTROW+2*c.index,3,2);put(m,RUNTIMES[c.group]+64*c.index,c.duration);put(m,KEYS+8*c.frame+6,c.flag,2);put(m,ALTKEYS+8*c.frame+6,c.flag^1,2)
 put(m,s['D_800969D8'],0x3C23D70A);put(m,s['D_800969DC'],c.scale)
 if c.invalid:put(m,s['D_800C3A50']+4*c.group,0);put(m,s['D_800C3868']+120*c.group+4*c.index,0)
 return m
def public(m):return {a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def mul(a,b):return bits(rounded(floating(a)*floating(b)))
def sub(a,b):return bits(rounded(floating(a)-floating(b)))
def maybe(a,b):return a==b or (a&0x7F800000==0x7F800000 and a&0x7FFFFF and b&0x7F800000==0x7F800000 and b&0x7FFFFF)
def side_effect(m,c,stage,s=SYMS):
 if stage==F72:
  if c.mutation&1:put(m,s['D_800C35C8']+4*c.group,ALTROW);put(m,s['D_800C3868']+120*c.group+4*c.index,ALTKEYS)
  if c.mutation&2:put(m,s['D_800969DC'],0x40000000)
  if c.mutation&4:put(m,STACK+c.phase+8,ALTOUT)
  if c.mutation&16:put(m,STACK+c.phase,1);put(m,STACK+c.phase+12,1)
 if stage==ANGLE and c.mutation&8:put(m,s['D_800969DC'],0x3F000000)
def reference(initial,c,s=SYMS):
 m=dict(initial);home=STACK+c.phase;put(m,home+8,output(c,s));calls=[];p=floating(c.percentage)
 if read(m,read(m,s['D_800C35C8']+4*c.group)+2*c.index,2)<2:return m,calls,None
 put(m,home,c.index);put(m,home+12,c.group)
 if p>100.:p=100.
 if p<0.:p=0.
 tm=mul(mul(c.duration,bits(p)),read(m,s['D_800969D8']));calls.append((F72,(c.index,tm,c.group)));side_effect(m,c,F72,s)
 group=read(m,home+12);index=read(m,home);key=read(m,s['D_800C3868']+120*group+4*index);flag=read(m,key+8*c.frame+6,2)
 if flag:
  count=read(m,read(m,s['D_800C35C8']+4*c.group)+2*c.index,2);calls.append((FFE,(key,c.frame,count)));x=sub(MATRIX[6],MATRIX[3]);z=sub(MATRIX[8],MATRIX[5])
 else:x=sub(POINTS[0],POINTS[3]);z=sub(POINTS[2],POINTS[5])
 calls.append((ANGLE,(x,z)));side_effect(m,c,ANGLE,s);value=mul(c.angle,read(m,s['D_800969DC']));destination=read(m,home+8);put(m,destination,value);return m,calls,destination
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.c,self.s=c,s;super().__init__(ws,memory,c,entry=entry,s=s,arguments=(c.index,c.percentage,output(c,s),c.group),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.logical=[];self.private_arguments=[]
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(1,2,6,60):
   a,b=floating(self.f[fs]),floating(self.f[ft])
   if fn==1:self.f[fd]=bits(rounded(a-b))
   elif fn==2:self.f[fd]=bits(rounded(a*b))
   elif fn==6:self.f[fd]=self.f[fs]
   else:self.condition=a<b
  else:super().execute(w)
 def record_call(self,t):
  kind={self.s['func_1501F72C']:F72,self.s['func_1501FFE8']:FFE,self.s['func_150484A0']:ANGLE}.get(t)
  if kind==F72:
   a=tuple(self.arguments(5));self.logical.append((kind,(a[0],a[1],a[3])));self.private_arguments.append((kind,a[2],a[4]))
  elif kind==FFE:
   a=tuple(self.arguments(4));self.logical.append((kind,(a[1],a[2],a[3])));self.private_arguments.append((kind,a[0]))
  elif kind==ANGLE:a=(self.f[12],self.f[14]);self.logical.append((kind,a))
  else:raise AssertionError(('Unexpected call',hex(t)))
  self.calls.append((t,a))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];kind={self.s['func_1501F72C']:F72,self.s['func_1501FFE8']:FFE,self.s['func_150484A0']:ANGLE}[t]
  if kind==F72:
   for i,v in enumerate(POINTS):put(self.memory,a[2]+4*i,v)
   put(self.memory,a[4],c.frame);side_effect(self.memory,c,F72,self.s)
  elif kind==FFE:
   for i,v in enumerate(MATRIX):put(self.memory,a[0]+4*i,v)
  else:assert kind==ANGLE;side_effect(self.memory,c,ANGLE,self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=0x87654321
  if kind==ANGLE:self.f[0]=c.angle
def words(path,s=SYMS):
 raw,refs=p.payload(path,p.NAME);return bound_blob(raw,refs,s)
def check(m,c,s=SYMS):
 expected,calls,destination=reference(m.initial,c,s);actual=m.logical
 assert len(actual)==len(calls),(c,'calls',actual,calls)
 for (ta,aa),(tb,ab)in zip(actual,calls):assert ta==tb and len(aa)==len(ab)and all(maybe(a,b)for a,b in zip(aa,ab)),(c,'arguments',actual,calls)
 exp=public(expected);got=public(m.memory);assert exp.keys()==got.keys()
 changed=set(range(destination,destination+4))if calls else set()
 for a in exp:
  if a not in changed:assert exp[a]==got[a],(c,'memory',hex(a),exp[a],got[a])
 if calls:assert maybe(read(expected,destination),read(m.memory,destination)),(c,'output')
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],(c,'ABI')
def run(ws,c,s=SYMS):
 m=Oracle(ws,fixture(c,s),c,s);m.run();check(m,c,s);return m
def cases():
 values=(0,0x80000000,0xBF800000,0x3F800000,0x42C80000,0x42C80001,0x42C7FFFF,0x7F800000,0xFF800000,0x7FC12345)
 cs=[Case(group=g,index=i,count=count,percentage=v,flag=flag,frame=(i&1),alias=0)for g,i,count,v,flag in itertools.product(range(2),range(2),(0,1,2,3,65535),values,(0,1))]
 cs +=[Case(count=2,flag=flag,mutation=mut,alias=alias,percentage=v)for flag,mut,alias,v in itertools.product((0,1),(0,1,2,4,8,15),range(5),(0x3F800000,0x42C80000))]
 durations=(0,0x80000000,1,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
 cs +=[Case(count=2,duration=d,percentage=v,flag=flag)for d,v,flag in itertools.product(durations,(0,0x42480000,0x42C80000),(0,1))]
 cs +=[Case(count=2,flag=flag,mutation=mut,alias=alias)for flag,mut,alias in itertools.product((0,1),(16,31),(0,4))]
 cs +=[Case(count=count,alias=5,invalid=1)for count in(0,1)]
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 original=struct.unpack_from('>96I',(root/'conker/conker.us.bin').read_bytes(),p.ROM);raw,refs=p.payload(out/'selected.o',p.NAME);normal,rs=n.normalize(raw,refs);programs=(words(out/'selected.o'),bound_blob(normal,rs,SYMS),original);seen=set();pairs=0
 for c in cases():
  a,b,d=[run(ws,c)for ws in programs];assert public(a.memory)==public(d.memory),(c,'raw public');assert(b.memory,b.r,b.f,b.trace,b.calls,b.current_pc,b.delay_of)==(d.memory,d.r,d.f,d.trace,d.calls,d.current_pc,d.delay_of),(c,'complete');seen.update((pc-ENTRY)//4 for pc in b.visits if ENTRY<=pc<ENTRY+384);pairs+=1
 r=dict(cases=pairs,executions=pairs*3,coverage=len(seen),missing=[i for i in range(96)if i not in seen],normalized_original_complete_machine_pairs=pairs,raw_private_stack_not_compared=True,parameter_home_mutations_guest_only=True,invalid_output_only_in_inactive_branch=True,FCSR_and_hardware_not_qualified=True)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
