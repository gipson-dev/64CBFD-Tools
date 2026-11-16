"""Original 64-word emission-loop window, actual callbacks and optional factory chain."""
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import game_inverse_motion_151a4638_connected as cmod
g=cmod.g;O=g.O;R=g.R
WINDOW,END,NOOP,TABLE=0x15134528,0x15134628,0x151348F0,0x80089A70
ROM=cmod.ROM;ELF=cmod.ELF;words=list(struct.unpack('>64I',ROM[0x1619D8:0x161AD8]));nop=list(struct.unpack('>6I',ROM[0x161DA0:0x161DB8]));table=ROM[0x22E530:0x22E560]
for entry,raw in((WINDOW,struct.pack('>64I',*words)),(NOOP,struct.pack('>6I',*nop)),(TABLE,table)):
 at=cmod.elf_slot_offset(ELF,entry,len(raw));assert ELF[at:at+len(raw)]==raw
assert struct.unpack_from('>II',table)==(NOOP,g.ENTRY)

class Machine(cmod.Machine):
 def __init__(self,body,m,c,connected):
  code=dict(cmod.HELPERS)if connected else{};code.update(zip(range(g.ENTRY,g.ENTRY+4*len(body),4),body));code.update(zip(range(NOOP,NOOP+24,4),nop));code[END]=0
  g.base.Machine.__init__(self,words,m,c,connected=code,entry=WINDOW,args=(g.E,0,0));self.ri=0;self.homes=[];self.forwardings=[];self.allocations=[];self.callbacks=[];self.deep=connected
  a=g.inputs(c);self.r[16]=g.E;self.f[28]=g.bits(1.0);self.f[30]=a[3];self.f[14]=a[4];self.f[16]=a[5];self.f[2]=g.read(m,g.E+0x50)
  self.code=WindowCode(self.code,self);self.code.ends=(END,)
 def record_call(self,t):
  if t in(g.ENTRY,NOOP):
   self.callbacks.append((t,(self.f[12],self.f[14],self.r[6],self.r[7],self.get(self.r[29]+16,4),self.get(self.r[29]+20,4),self.get(self.r[29]+24,4))))
   if t==g.ENTRY:self.ri=0
   return
  if self.deep:return super().record_call(t)
  return g.Machine.record_call(self,t)
 def hook(self,t):return super().hook(t)if self.deep else g.Machine.hook(self,t)

def main(label='v37'):
 streams=g.programs([label]);visited=set();n=0;routes=set()
 for kind,pending,seed,success,deep,phase in itertools.product((0,1,'null'),(0.,1.,2.,3.5),(0,1,2,3,128,255),(0,1),(False,True),(0,8)):
  c=g.Case(seed=seed,flips=seed%4,success=success,phase=phase);initial=g.fixture(c);home=g.STACK+phase;a=g.inputs(c)
  for i,v in enumerate(table):initial[TABLE+i]=v
  initial[g.E+0x3B]=0 if kind==0 else 1
  if kind=='null':g.put(initial,TABLE+4,0)
  g.put(initial,g.E+0x30,g.bits(2.25));g.put(initial,g.E+0x50,g.bits(pending))
  for off,v in zip((0xA4,0xA8,0xAC),a[:3]):g.put(initial,home+off,v)
  expected=dict(initial);calls=[];callbacks=[];remaining=g.bits(pending);radius=g.bits(2.25);r=c.sample;twice=g.fp(radius,radius,'add','left')
  while g.floating(remaining)>1.0:
   calls.append((g.REAL,(),b''))
   if kind!='null':
    calls.extend([(g.REAL,(),b'')]*3)
    point=[]
    for p,v in zip(a[:3],a[3:]):
     value=g.fp(g.fp(g.fp(p,g.fp(v,r,'mul','left'),'add','left'),radius,'add','left'),g.fp(r,twice,'mul','left'),'sub','left');point.append(value)
    args=(*point,*a[3:],g.E);callbacks.append((NOOP if kind==0 else g.ENTRY,args))
    if kind==1:
     expected,child,answer,ops=g.reference(expected,c,values=args[:6])
     if deep and success:
      packet=next(row[2]for row in child if row[0]==g.FACTORY);child.insert(-1,(g.COPY,(g.OUT+16,'packet',112),packet))
      for i,value in enumerate(packet):expected[g.OUT+16+i]=value
      expected[g.OUT+0x9C]=0
     calls.extend(child)
   remaining=g.fp(remaining,g.bits(1.0),'sub','left');g.put(expected,g.E+0x50,remaining)
  states={}
  for name,body in streams.items():
   q=Machine(body,initial,c,deep)
   try:q.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller window boundary not reached')
   assert(g.public(q.memory),q.calls,q.callbacks)==(g.public(expected),calls,callbacks),(name,kind,pending,seed,success,deep,phase,'caller transfer')
   assert q.r[29]==home and q.r[16]==g.E and q.r[17]==TABLE and q.f[28]==g.bits(1.0)and q.f[30]==a[3]
   states[name]=q.fp_ops;visited.update(pc for pc in q.visits if WINDOW<=pc<END)
  assert len({repr(v)for v in states.values()})==1,'caller FP order'
  routes.add('counter-gated'if pending<=1 else'null-slot-synthetic'if kind=='null'else'no-op-callback'if kind==0 else'constructor-callback')
  n+=1
 assert len(visited)==64,(len(visited),sorted(hex(x)for x in set(range(WINDOW,END,4))-visited))
 report=dict(cases_per_stream=n,streams=len(streams),original_parent_words=261,parent_full_body_unchanged=True,qualified_window_words=64,window_words_visited=len(visited),window='0x15134528..0x15134628',all_seven_arguments_and_ignored_return=True,repeated_emissions_and_noop_callback=True,opaque_and_connected_factory=True,synthetic_NULL_lookup_is_not_retail_data=True,upstream_parent_gates_and_transforms_outside_window=True,routes=sorted(routes),source_installed=False,c_match_credit=0)
 (O/'callers-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else'v37')
