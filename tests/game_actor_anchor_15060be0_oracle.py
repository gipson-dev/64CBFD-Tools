"""Independent anchor model; invalid conversions stop at an unclaimed prefix."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-anchor-15060BE0-match'
from tools.tests.game_paired_float_approach_1505a250_oracle import Oracle as FloatOracle,bits,floating,rounded,divide
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_anchor_15060be0_match import normalize,fp_roles,TEMP
ENTRY=0x15060BE0;ACTOR=0x30000;META=0x50000;BUFFER=0x60000;TABLE=0x800D1C90;DISABLE=0x800C3E90
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
class InvalidConversionPrefix(Exception):pass
@dataclass(frozen=True)
class Case:
 identity:int=0
 present:int=1
 disabled:int=0
 distance:int=10
 scale:int=0x3F800000
 index:int=0
 direction:tuple=(0x40400000,0x40800000,0)
 origin:tuple=(0x41240000,0xC1A40000,0x3F400000)
 position:tuple=(0x3FC00000,0xC0200000,0x40600000)
 alias:int=0
 sparse:bool=False
 phase:int=0
 seed:int=0
def symbols():return dict(D_800C3E90=DISABLE,D_800D1C90=TABLE)
def locations(c):
 selected=(BUFFER+c.index*64,ACTOR+0x18C,ACTOR+0x188,ACTOR+0x184,BUFFER+c.index*64,ACTOR+4)[c.alias]
 meta=ACTOR+0x1A8 if c.alias==4 else META
 return meta,selected,selected-c.index*64
def fixture(c,s=None):
 s=s or symbols();meta,selected,base=locations(c);m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)}
 for a,n in((ACTOR-16,844),(meta-16,76),(selected-16,96)):m.update({a+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 m[ACTOR+4]=c.identity&255;put(m,ACTOR+0x1D4,base if c.present else 0);put(m,ACTOR+0x150,c.scale)
 for j,v in enumerate(c.position):put(m,ACTOR+0x14+j*4,v)
 for j in range(256):put(m,s['D_800D1C90']+4*j,meta)
 m[s['D_800C3E90']]=c.disabled&255;put(m,meta+0x14,c.distance,2);m[meta+0x27]=c.index&255
 for a,vs in((selected+0x10,c.direction),(selected+0x30,c.origin)):
  for j,v in enumerate(vs):put(m,a+j*4,v)
 # Overlapping fixture regions are a single byte-addressed object; restore
 # the required input pointer after seeding every aliased matrix byte.
 put(m,ACTOR+0x1D4,base if c.present else 0);m[ACTOR+4]=c.identity&255
 if c.sparse:
  wanted=set(range(STACK-256,STACK+512))|set(range(ACTOR,ACTOR+812))
  if c.identity!=255 and c.present:wanted.add(s['D_800C3E90'])
  m={a:v for a,v in m.items()if a in wanted}
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+512}
def truncable(v):return math.isfinite(v)and -2147483648.<=v<2147483648.
def reference(initial,c,s=None):
 s=s or symbols();m=dict(initial);valid=False;values=[]
 if m[ACTOR+4]!=255 and read(m,ACTOR+0x1D4)!=0 and m[s['D_800C3E90']]==0:
  meta=read(m,s['D_800D1C90']+4*m[ACTOR+4]);matrix=read(m,ACTOR+0x1D4)+m[meta+0x27]*64;distance=((read(m,meta+0x14,2)^32768)-32768);offset=rounded(float(distance)*floating(read(m,ACTOR+0x150)))
  if offset!=0.0:
   d=[floating(read(m,matrix+0x10+4*j))for j in range(3)];length=rounded(math.sqrt(rounded(rounded(rounded(d[0]*d[0])+rounded(d[1]*d[1]))+rounded(d[2]*d[2]))));factor=divide(offset,length)if length!=0.0 else length;delta=[rounded(v*factor)for v in d]
  else:delta=[0.,0.,0.]
  valid=True
  for j,v in enumerate(delta):
   value=rounded(floating(read(m,matrix+0x30+4*j))+v);values.append(value)
   if not truncable(value):return m,False,j,valid,values
   put(m,ACTOR+0x1BC+2*j,math.trunc(value),2)
 else:
  values=[floating(read(m,ACTOR+0x14+4*j))for j in range(3)]
  for j,value in enumerate(values):
   if not truncable(value):return m,False,j,valid,values
  # Retail schedules all three fallback conversions before its first store.
  for j,value in enumerate(values):
   put(m,ACTOR+0x1BC+2*j,math.trunc(value),2)
 return m,True,None,valid,values
class Oracle(FloatOracle):
 def __init__(self,ws,memory,c,entry=ENTRY):
  self.c=c;FactoryOracle.__init__(self,ws,memory,c,entry=entry,arguments=(ACTOR,));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:];self.defined_temps=set();self.prefix=None;self.track_roles=True
 def execute(self,w):
  op,fmt,fs,fd,fn=w>>26,w>>21&31,w>>11&31,w>>6&31,w&63;i=(self.current_pc-self.entry)//4
  if i in(57,79):self.defined_temps=set()
  if op==17 and fmt==16 and fn==13:
   value=floating(self.f[fs])
   if not truncable(value):self.prefix=dict(word=i,operand=self.f[fs]);raise InvalidConversionPrefix
   self.f[fd]=u32(math.trunc(value))
  elif op==17 and fmt==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])))
  else:super().execute(w)
  if self.track_roles and(57<=i<77 or 79<=i<91):self.defined_temps|=fp_roles(w)[1]&set(TEMP)
 def record_call(self,t):raise AssertionError(('Leaf made a call',hex(t)))
 def hook(self,t):raise AssertionError(('Leaf used a helper',hex(t)))
def words(path,normalized=False,s=None):
 t,fs,rs=parse_object(path);a,n=fs['func_15060BE0']['value'],fs['func_15060BE0']['size'];raw=t[a:a+n];refs={i-a:v for i,v in rs.items()if a<=i<a+n}
 if normalized:raw,refs=normalize(raw,refs)
 return bound_blob(raw,refs,s or symbols())
def run(ws,c,s=None,entry=ENTRY):
 m=Oracle(ws,fixture(c,s),c,entry)
 try:m.run()
 except InvalidConversionPrefix:pass
 expected,normal,axis,updated,_=reference(m.initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert normal==(m.prefix is None),(c,'conversion-domain');assert not m.calls and m.f[20:]==m.before_f[20:]
 if normal:assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.r[2]==int(updated),(c,'saved/flag')
 return m
def cases():
 cs=[Case(identity=i,present=p,disabled=d,distance=n,index=k)for i,p,d,n,k in itertools.product((0,1,186,187,254,255),(0,1),(0,1,255),(-32768,0,1,32767),(0,8,255))]
 for i in range(256):cs.append(Case(identity=i,index=i))
 patterns=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x3F000000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC12345,0x4EFFFFFF,0x4F000000,0xCF000000,0xCF000001)
 for value in patterns:
  cs.append(Case(scale=value));cs.append(Case(scale=value,distance=0,direction=(0,0,0)))
  for j in range(3):
   for field in('direction','origin','position'):
    vs=list(getattr(Case(),field));vs[j]=value;cs.append(replace(Case(identity=255 if field=='position'else 0),**{field:tuple(vs)}))
 for alias,n,k in itertools.product(range(1,6),(-1,0,1,32767),(0,3,255)):cs.append(Case(alias=alias,distance=n,index=k))
 for p in((0,0,0),(0x80000000,0x80000000,0x80000000),(1,1,1),(0x7F7FFFFF,0x7F7FFFFF,0x7F7FFFFF)):
  for n in(0,1,-1):cs.append(Case(direction=p,distance=n))
 cs.extend((Case(identity=255,sparse=True),Case(present=0,sparse=True),Case(disabled=1,sparse=True)))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();raw=words(out/'selected.o');normalized=words(out/'selected.o',True);retail=struct.unpack_from('>93I',(root/'conker/conker.us.bin').read_bytes(),0x8E090);assert list(retail)==normalized;seen=set();prefixes=normal=0
 for c in cs:
  a,b,d=[run(ws,c)for ws in(raw,normalized,retail)]
  assert(a.memory,a.r,a.trace,a.prefix)==(b.memory,b.r,b.trace,b.prefix),(c,'raw/normalized-public-state')
  assert all(a.f[k]==b.f[TEMP[k]]for k in a.defined_temps),(c,'closed-FP-cycle');assert all(a.f[k]==b.f[k]for k in set(range(32))-set(TEMP)),(c,'other-FP-state')
  assert(b.memory,b.r,b.f,b.trace,b.prefix,b.condition)==(d.memory,d.r,d.f,d.trace,d.prefix,d.condition),(c,'complete-retail-state');seen.update((pc-ENTRY)//4 for pc in b.visits if ENTRY<=pc<ENTRY+372);prefixes+=b.prefix is not None;normal+=b.prefix is None
 result=dict(cases=len(cs),executions=3*len(cs),normal_returns=normal,invalid_conversion_prefix_cases=prefixes,complete_normalized_retail_pairs=len(cs),raw_normalized_relational_pairs=len(cs),coverage=len(seen),missing=[i for i in range(93)if i not in seen],partial_store_prefixes_preserved=True,invalid_conversion_results_or_FCSR_qualified=False)
 (out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
