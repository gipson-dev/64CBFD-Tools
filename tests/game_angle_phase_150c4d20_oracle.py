"""Independent rounded angular spring model and emitted-MIPS qualification."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-angle-phase-150C4D20-match'
from tools.tests.game_paired_float_approach_1505a250_oracle import Oracle as FloatOracle,bits,floating,rounded,canonical
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.experiments.game_angle_phase_150c4d20_match import normalize
ENTRY,RECORD,SOUND,TRIG=0x150C4D20,0x30000,0x10010F88,0x15048A40
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768
class InvalidConversionPrefix(Exception):pass
@dataclass(frozen=True)
class Case:
 angle:int=0x43340000
 velocity:int=0x3F800000
 timer:int=255
 ticks:int=1
 flags:int=4
 coords:tuple=(0x8000,0x7FFF,0xFFFF)
 result:int=0x3F000000
 mutation:int=0
 alias:int=0
 phase:int=0
 seed:int=0
def symbols():return dict(D_800BE9E4=0x800BE9E4,D_800A03F0=0x800A03F0,D_800A03F4=0x800A03F4,D_800A03F8=0x800A03F8,func_10010F88=SOUND,func_15048A40=TRIG)
def record(c,s=None):
 s=s or symbols();return(RECORD,s['D_800BE9E4']-0x7C,s['D_800A03F0'],s['D_800A03F4']-0x60)[c.alias]
def fixture(c,s=None):
 s=s or symbols();p=record(c,s);m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)}
 m.update({p+i:(i*29+c.seed*11+90)&255 for i in range(0xA0)})
 for at,v in((0,c.angle),(0x60,c.velocity),(0x7C,c.timer)):put(m,p+at,v)
 for i,v in enumerate(c.coords):put(m,p+0x10+2*i,v,2)
 m[p+0x4F]=c.flags&255
 for n,v in(('D_800BE9E4',c.ticks),('D_800A03F0',bits(.009)),('D_800A03F4',bits(.1)),('D_800A03F8',bits(.8))):put(m,s[n],v)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+512}
def effect(m,c,s,t):
 p=record(c,s);mask=c.mutation
 if mask&1:
  put(m,p,bits(-90. if t==s['func_10010F88']else 400.));put(m,p+0x60,bits(123.));put(m,p+0x7C,0x12345678);m[p+0x4F]^=4
 if mask&2:
  put(m,s['D_800BE9E4'],123);put(m,s['D_800A03F0'],bits(.02));put(m,s['D_800A03F4'],bits(.25));put(m,s['D_800A03F8'],bits(.5))
def reference(initial,c,s=None):
 s=s or symbols();m=dict(initial);p=record(c,s);calls=[];angle=floating(read(m,p));velocity=floating(read(m,p+0x60))
 if angle>180.:angle=rounded(angle-360.)
 phase=u32(read(m,p+0x7C)+read(m,s['D_800BE9E4']));phasef=rounded(float(signed(phase)))
 velocity=rounded(velocity-rounded(angle*floating(read(m,s['D_800A03F0']))))
 if phasef>=256.:
  value=rounded(phasef-256.)
  if not math.isfinite(value)or not -2147483648<=value<2147483648:return m,calls,False
  phase=u32(math.trunc(value));args=(15,0x55F0,0,0,0,*[u32(half(read(m,p+0x10+2*i,2)))for i in range(3)],500,1000);calls.append((s['func_10010F88'],args));effect(m,c,s,s['func_10010F88'])
 put(m,p+0x7C,phase);calls.append((s['func_15048A40'],(phase&255,)));effect(m,c,s,s['func_15048A40'])
 scale=floating(read(m,s['D_800A03F4']));velocity=rounded(velocity+rounded(floating(c.result)*scale))
 if m[p+0x4F]&4==4:velocity=rounded(velocity+scale)
 velocity=rounded(velocity*floating(read(m,s['D_800A03F8'])));angle=rounded(floating(read(m,p))+velocity)
 put(m,p+0x60,bits(velocity));put(m,p,bits(angle));angle=floating(read(m,p))
 if angle<0.:put(m,p,bits(rounded(angle+360.)))
 elif angle>=360.:put(m,p,bits(rounded(angle-360.)))
 return m,calls,True
class Oracle(FloatOracle):
 def __init__(self,ws,memory,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=s or symbols();self.prefix=None;FactoryOracle.__init__(self,ws,memory,c,entry=entry,arguments=(record(c,self.s),),connected=connected);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,fs,fd,fn=w>>26,w>>21&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])))
  elif op==17 and fmt==16 and fn==13:
   value=floating(self.f[fs])
   if not math.isfinite(value)or not -2147483648<=value<2147483648:self.prefix=dict(pc=self.current_pc,operand=self.f[fs]);raise InvalidConversionPrefix
   self.f[fd]=u32(math.trunc(value))
  else:super().execute(w)
 def record_call(self,t):
  assert t in(self.s['func_10010F88'],self.s['func_15048A40'],ENTRY),hex(t);args=tuple(map(u32,self.arguments(10 if t==self.s['func_10010F88']else 1)));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  effect(self.memory,self.c,self.s,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xA5000002
  if t==self.s['func_15048A40']:self.f[0]=self.c.result
def words(path,normalized=False,s=None):
 text,fs,rs=parse_object(path);a,n=fs['func_150C4D20']['value'],fs['func_150C4D20']['size'];raw=text[a:a+n];refs={i-a:v for i,v in rs.items()if a<=i<a+n}
 if normalized:raw,refs=normalize(raw,refs)
 return bound_blob(raw,refs,s or symbols())
def check(m,c,s=None):
 s=s or symbols();expected,calls,normal=reference(m.initial,c,s);p=record(c,s);assert m.calls==calls,(c,'calls',m.calls,calls);assert normal==(m.prefix is None),(c,'conversion')
 actual=public(m.memory);wanted=public(expected)
 for a in(p,p+0x60):
  assert canonical(read(actual,a))==canonical(read(wanted,a)),(c,'float',hex(a),hex(read(actual,a)),hex(read(wanted,a)))
  for j in range(4):actual.pop(a+j);wanted.pop(a+j)
 assert actual==wanted,(c,'public')
 if normal:assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],(c,'saved')
def run(ws,c,s=None):
 m=Oracle(ws,fixture(c,s),c,s=s)
 try:m.run()
 except InvalidConversionPrefix:pass
 check(m,c,s);return m
def cases():
 cs=[Case(angle=bits(a),velocity=bits(v),timer=t,ticks=k,flags=f,mutation=mu)for a,v,t,k,f,mu in itertools.product((-720.,-1.,0.,180.,181.,360.,720.),(-100.,0.,100.),(0,255,256),(0,1),(0,4),(0,3))]
 patterns=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC12345)
 for field,value in itertools.product(('angle','velocity','result'),patterns):cs.append(replace(Case(),**{field:value}))
 for timer,ticks in itertools.product((0x7FFFFE00,0x7FFFFF00,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0xFFFFFF00),(0,1,255,0x7FFFFFFF,0x80000000,0xFFFFFFFF)):cs.append(Case(timer=timer,ticks=ticks))
 for alias,mu in itertools.product((1,2,3),range(4)):cs.append(Case(alias=alias,mutation=mu))
 for i in range(256):cs.append(Case(timer=i,flags=i,result=bits((i-128)/64.)))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();truth=struct.unpack_from('>95I',(root/'conker/conker.us.bin').read_bytes(),0xF21D0);raw=words(out/'selected.o');normal=words(out/'selected.o',True);assert normal==list(truth);seen=set();invalid=0
 for c in cs:
  a,b,d=[run(ws,c)for ws in(raw,normal,truth)];invalid+=a.prefix is not None
  assert(a.memory,a.r,a.f,a.calls)==(b.memory,b.r,b.f,b.calls),(c,'raw-normal-final')
  assert(b.memory,b.r,b.f,b.trace,b.calls,b.prefix)==(d.memory,d.r,d.f,d.trace,d.calls,d.prefix),(c,'retail-machine')
  seen.update((pc-ENTRY)//4 for pc in b.visits if ENTRY<=pc<ENTRY+380)
 result=dict(cases=len(cs),executions=len(cs)*3,invalid_conversion_prefixes=invalid,coverage=len(seen),missing=[i for i in range(95)if i not in seen],raw_normal_final_pairs=len(cs),normalized_retail_machine_trace_pairs=len(cs),helpers_are_effectful_ABI_models=True,FCSR_or_hardware_qualified=False);(out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
