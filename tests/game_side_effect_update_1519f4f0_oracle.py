"""Independent ordered ring model and complete MIPS guest executions."""
from dataclasses import dataclass,replace
from pathlib import Path
from functools import lru_cache
import itertools,json,struct,hashlib
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as BaseCase
from tools.tests import game_perpendicular_offset_1519ef90_oracle as base
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments import game_side_effect_update_1519f4f0_match as source
r,o,ENTRY=source.ROOT,source.OUT,source.ENTRY;QUERY=0x15045800;EFFECT,PACKET,RECORDS,ALT=0x30000,0x60000,0x50000,0x70000
s8=lambda v:((v&255)^128)-128
s16=lambda v:((v&65535)^32768)-32768
@lru_cache(None)
def symbols():return {x[1]:x[2][1] for x in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())}
@dataclass(frozen=True)
class Case:
 cap:int=5;head:int=0;tail:int=4;count:int=4;kind:int=6;tick:int=1;scale:int=0x3F000000
 pattern:int=0;hit:int=1;effects:int=0;phase:int=0;alias:int=0;rule:str='left'
def addresses(c):
 return (EFFECT,PACKET,RECORDS) if c.alias==0 else (EFFECT,PACKET,symbols()['D_800BE9A4']-36*2) if c.alias==1 else (EFFECT,PACKET,symbols()['D_800BE9A4']-36*2-4) if c.alias==2 else (EFFECT,PACKET,PACKET-72)
def fixture(c):
 e,p,a=addresses(c);m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for start,n in ((e,160),(p,80),(a,36*c.cap),(ALT,512)):
  assert start+n<=STACK+c.phase-512 or start>=STACK+c.phase+512,('public fixture overlaps stack window',hex(start),n)
 for at,n in ((e,0xA0),(p,80),(a-32,36*c.cap+64),(ALT,512)):
  for i in range(n):m.setdefault(at+i,(i*13+0x53)&255)
 m[e+0x25]=c.cap;m[e+0x2C]=c.count&255;m[e+0x2D]=c.head&255;m[e+0x2E]=c.tail&255
 put(m,e+0x94,a);put(m,e+0x98,p);m[p+4]=c.kind
 put(m,p+0x34,25,2);put(m,p+0x3C,bits(1.));put(m,p+0x46,0x7FFF,2);put(m,p+0x48,6,2)
 for i in range(c.cap):
  at=a+36*i
  x,z,h,life,alpha,delay,vx,vz=(float(i+1),-float(i+1),5.,100,255,2,.25,-.5)
  if c.pattern==1:life=(-1,0,32767,1,20)[i%5]
  elif c.pattern==2:alpha=(-32768,0,1,25,32767)[i%5];delay=0
  elif c.pattern==3:x=(100001. if i&1 else -100001.);z=0.
  elif c.pattern==4:x=0.;z=100001.
  elif c.pattern==5:life=32767;alpha=32767;delay=32767
  elif c.pattern==6:x=base.floating(0x7FC12345);z=base.floating(0x7F800000)
  for off,v in ((0,bits(x)),(4,bits(z)),(8,bits(h)),(12,bits(.25*i)),(28,bits(vx)),(32,bits(vz))):put(m,at+off,v)
  for off,v in ((16,alpha),(18,delay),(20,1),(24,life)):put(m,at+off,v,2)
 for name,v in (('D_800BE9E4',c.tick),('D_800BE9A4',c.scale),('D_800A8CF0',bits(100000.))):put(m,symbols()[name],v)
 # Object header aliases are screened only when initialization retained the ABI pointers.
 assert read(m,e+0x94)==a and read(m,e+0x98)==p and 0<=s8(m[e+0x2D])<c.cap and 0<=s8(m[e+0x2E])<c.cap
 return m
def public(m,c):return {a:v for a,v in m.items() if not STACK+c.phase-512<=a<STACK+c.phase+512}
def query(m,c,ordinal,point,out):
 e,p,a=addresses(c)
 # Every byte of the complete public result can be changed, including on miss.
 for i in range(36):m[out+i]=(ordinal*31+i*7+0xA5)&255
 put(m,out,bits(20.25+ordinal))
 if c.effects&1:
  put(m,symbols()['D_800BE9E4'],ordinal+2);put(m,symbols()['D_800BE9A4'],bits(.25*(ordinal+1)))
  put(m,p+0x34,3,2);put(m,p+0x3C,bits(2.));put(m,p+0x48,-7,2)
 if c.effects&2:put(m,e+0x94,ALT);put(m,e+0x98,ALT+0x100)
 if c.effects&4 and ordinal==0:m[e+0x2D]=(c.head+1)%c.cap;m[e+0x2C]=(m[e+0x2C]+1)&255
 # A write to the bound must not replace the root's cached threshold.
 if c.effects&8:put(m,symbols()['D_800A8CF0'],0)
 for i in range(12):m[point+i]^=0x5A
 return c.hit if c.hit in (0,1) else ordinal&1
def reference(initial,c):
 m=initial.copy();e,_,_=addresses(c);p=read(m,e+0x98);a=read(m,e+0x94);calls=[];fp=[]
 def op(x,y,k):fp.append((k,x,y));return base.fp(x,y,k,c.rule)
 def absolute(x):fp.append(('abs',x));return x&0x7FFFFFFF
 def less(x,y):fp.append(('lt',x,y));return floating(x)<floating(y)
 if s8(m[e+0x2C])<2 and m[p+4]&1:return m,0,calls,fp
 cursor=s8(m[e+0x2E]);head=lambda:s8(m[e+0x2D]);loops=0
 if cursor!=head():
  limit=read(m,symbols()['D_800A8CF0'])
  while True:
   loops+=1;assert loops<300,('reference loop',c,cursor,head())
   cursor-=1
   if cursor<0:cursor=m[e+0x25]-1
   at=(a+36*cursor)&0xFFFFFFFF;expired=False
   put(m,at+24,s16(read(m,at+24,2))-read(m,symbols()['D_800BE9E4']),2)
   if s16(read(m,at+24,2))<0:expired=True
   delay=s16(read(m,at+18,2));put(m,at+20,255,2)
   if delay>0:put(m,at+18,delay-read(m,symbols()['D_800BE9E4']),2)
   else:put(m,at+16,s16(read(m,at+16,2))-s16(read(m,p+52,2))*read(m,symbols()['D_800BE9E4']),2)
   for dst,src,scale in ((12,p+60,symbols()['D_800BE9A4']),(0,at+28,symbols()['D_800BE9A4']),(4,at+32,symbols()['D_800BE9A4'])):
    product=op(read(m,src),read(m,scale),'mul');put(m,at+dst,op(read(m,at+dst),product,'add'))
   point=STACK+c.phase-0x20
   put(m,point,read(m,at));put(m,point+4,op(read(m,at+8),bits(30.),'add'));put(m,point+8,read(m,at+4))
   if less(limit,absolute(read(m,point))) or less(limit,absolute(read(m,point+8))):expired=True
   else:
    bottom=op(read(m,at+8),bits(30.),'sub');args=(point,0,bottom,e+0x60);snap=bytes(m[point+i] for i in range(12));calls.append((QUERY,args,snap))
    hit=query(m,c,len(calls)-1,point,e+0x60)
    if hit:put(m,at+8,read(m,e+0x60))
    else:expired=True
   if s16(read(m,at+16,2))<0:expired=True
   if expired:
    inner=0
    while cursor!=head():
     inner+=1;assert inner<300
     m[e+0x2D]=(head()+1)&255
     if head()==m[e+0x25]:m[e+0x2D]=0
     m[e+0x2C]=(m[e+0x2C]-1)&255
    put(m,(a+36*head()+16)&0xFFFFFFFF,0,2)
   if cursor==head():break
 put(m,p+70,s16(read(m,p+70,2))+s16(read(m,p+72,2))*read(m,symbols()['D_800BE9E4']),2)
 if s8(m[e+0x2C])>0:
  at=(a+36*head())&0xFFFFFFFF
  for out,src in ((0,0),(4,8),(8,4)):put(m,e+0x54+out,read(m,at+src))
 else:
  for out in (0,4,8):put(m,e+0x54+out,0)
 return m,1,calls,fp
class Machine(base.Oracle):
 def __init__(self,w,m,c,entry=ENTRY,arguments=None,connected=None):
  self.c=c;self.fp_ops=[]
  FactoryOracle.__init__(self,w,m,BaseCase(phase=c.phase),entry=entry,s={},arguments=(addresses(c)[0],) if arguments is None else arguments,connected=connected);self.root_words=w
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in (0,1,2,5,60):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;x,y=self.f[fs],self.f[ft]
   if fn in (0,1,2):k=('add','sub','mul')[fn];self.fp_ops.append((k,x,y));self.f[fd]=base.fp(x,y,k,self.c.rule)
   elif fn==5:self.fp_ops.append(('abs',x));self.f[fd]=x&0x7FFFFFFF
   else:self.fp_ops.append(('lt',x,y));self.condition=floating(x)<floating(y)
   return
  return FactoryOracle.execute(self,w)
 def record_call(self,t):
  assert t==QUERY,hex(t);a=tuple(self.arguments(4));self.calls.append((t,a,bytes(self.memory[a[0]+i] for i in range(12))))
 def hook(self,t):
  a=self.calls[-1][1];answer=query(self.memory,self.c,len(self.calls)-1,a[0],a[3])
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in (1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer
def programs():return source.programs()

def cases():
 for cap in (1,2,5,10):
  for head,tail,count,kind,pattern,tick,hit,effects in itertools.product((0,cap-1),(0,cap-1),(0,1,2,cap),(6,7),(0,1,2,3,4,5),(0,1,32767),(0,1,2),(0,1,2,4,8,15)):
   if (head+tail+count+kind+pattern+tick+hit+effects)%11:continue
   yield Case(cap=cap,head=head,tail=tail,count=count,kind=kind,pattern=pattern,tick=tick,hit=hit,effects=effects)
 for tick in (-2147483648,-1,2147483647):
  for pattern in range(6):yield Case(tick=tick,pattern=pattern)
 for alias,effects,hit in itertools.product((1,2,3),(0,1,2,4,8,15),(0,1,2)):yield Case(alias=alias,effects=effects,hit=hit)
 for rule,effects,mode in itertools.product(('left','right'),(0,1,8,15),(0,1,2)):yield Case(pattern=6,rule=rule,effects=effects,hit=mode)
 for count,kind in itertools.product((-128,-1,127),(6,7)):yield Case(count=count,kind=kind,pattern=1)
 for cap in (127,128):yield Case(cap=cap,head=126,tail=125,count=127,pattern=1)

def boundaries(streams):
 from tools.tests import test_game_actor_burst_consumer_match as faults
 count=0
 for c in (Case(count=1,kind=7),Case(cap=2,tail=1,count=1),Case(cap=2,tail=1,count=1,pattern=1,effects=15)):
  total=Machine(streams['retail'],fixture(c),c).run().all_accesses
  for cut in range(total):
   states=[]
   for label in ('retail','guarded'):
    q=Machine(streams[label],fixture(c),c);q.cut=cut
    try:q.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    states.append((q.memory,q.r,q.f,q.calls,q.trace,q.current_pc));count+=1
   assert states[0]==states[1],('emitted prefix',c,cut)
 return count

def controls(streams):
 result=[]
 for label,word,mask,c in (('gate',0x29C10002,1,Case(count=2,kind=7)),('life',0xA62B0018,2,Case()),('height-span',0x3C0141F0,1,Case()),('position-home',0x27A40058,4,Case())):
  w=streams['retail'][:];assert w.count(word)==1;w[w.index(word)]^=mask
  try:check(w,c)
  except (AssertionError,KeyError):result.append(label)
  else:raise AssertionError(('ineffective semantic control',label))
 return result
def check(words,c):
 m=fixture(c);expected,value,calls,fp=reference(m,c);q=Machine(words,m,c).run()
 assert (public(q.memory,c),q.r[2],q.calls,q.fp_ops)==(public(expected,c),value,calls,fp),('guest',c,'return',q.r[2],value,'calls',q.calls,calls,'memory',[(hex(k),expected.get(k),q.memory.get(k)) for k in expected if public(expected,c).get(k)!=public(q.memory,c).get(k)][:8],'fp',q.fp_ops,fp)
 return q
def main():
 paths=(source.SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1CC440.c.o','conker/build/conker.us.elf')
 fingerprint=lambda:{name:hashlib.sha256((r/name).read_bytes()).hexdigest() for name in paths}
 before=fingerprint()
 p=programs();count=0;seen={k:set() for k in p}
 for c in cases():
  for label,w in p.items():
   try:seen[label]|=check(w,c).visits
   except (AssertionError,KeyError) as error:raise AssertionError(('case failed',label,c)) from error
  count+=1
 from tools.tests.game_side_effect_update_1519f4f0_proof import dominance
 reachable=dominance(p['retail'])
 assert all({4*i for i in range(192) if ENTRY+4*i in v}==reachable for v in seen.values())
 report=dict(cases_per_stream=count,streams=len(p),visited_root_words={k:sum(ENTRY+4*i in v for i in range(len(p[k]))) for k,v in seen.items()},all_reachable_words_visited=True,
             emitted_prefix_cuts=boundaries(p),raw_fault_identity=False,effective_controls=controls(p),production_unchanged=before==fingerprint(),
             source_installed=(r/source.SOURCE).read_text()==source.recover((o/'production-baseline'/source.SOURCE).read_text()),behavioral_evidence_only=True)
 assert report['production_unchanged']
 (o/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
