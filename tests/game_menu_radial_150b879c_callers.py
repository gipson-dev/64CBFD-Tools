"""Complete retail radial dispatcher and connected real factory/copy bodies."""
import itertools,json,struct
from tools.experiments import game_menu_radial_150b879c_match as s
from tools.tests import game_menu_radial_150b879c_oracle as o
from tools.tests import game_radial_dispatch_1514c2f0_oracle as d
from tools.match_progress import load_elf_functions
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

def programs(state):
 one,_=s.pad_both(state)
 return((state['retail_words'],False),(state['raw_words'],True),(o.words(one),False))

def run(state):
 entry=0x1514C2F0;parent=struct.unpack_from('>96I',state['rom'],0x1797A0)
 live,_,_=load_elf_functions(str(s.FROZEN/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(live['func_1514C2F0'])==parent
 elf=(s.FROZEN/'conker/build/conker.us.elf').read_bytes();table=struct.unpack_from('>28I',elf,elf_slot_offset(elf,d.TABLE,112));assert table[25]==o.ENTRY
 selector=table.index(o.ENTRY);assert selector==25
 frame=-(((parent[0]&65535)^32768)-32768);assert frame>0
 class Connected(o.Oracle):
  def __init__(self,body,c,raw,initial):
   self.c=c;self.cc=o.Case();self.raw=raw;self.obs=[];self.i=self.j=0;self.homes=[];self.callback_count=0;self.sin_count=0
   args=(0,0,c.z,c.radius,c.start,c.step,c.count,selector,c.arg8,c.arg9,c.arg10,c.arg11)
   connected=dict(zip(range(o.ENTRY,o.ENTRY+568,4),body))
   d.FactoryOracle.__init__(self,parent,initial,c,entry=entry,arguments=args,connected=connected)
   self.f[12]=c.x;self.f[14]=c.y;self.home=o.STACK+c.phase-frame;self.fcsr=self.initial_fcsr=0
   self.before=self.r[:];self.before_f=self.f[:]
  def record_call(self,t):
   if t==d.SINE:self.calls.append((t,tuple(map(o.g.u32,self.arguments(1)))))
   elif t==o.ENTRY:
    a=tuple(map(o.g.u32,self.arguments(15)));self.calls.append((t,a));self.home=self.r[29];self.i=self.j=0;self.callback_count+=1
    self.cc=o.Case(actor=a[0],mode=a[1],phase=self.c.phase,angle=a[8],slot=a[14],success=self.c.fail,mutation=self.c.mutation,randoms=(a[8],a[8]*7,a[8]&1,(a[8]>>1)&1))
   else:super().record_call(t)
   self.homes.append(self.home)
  def hook(self,t):
   if t!=d.SINE:return super().hook(t)
   value=d.sine(self.calls[-1][1][0]);self.sin_count+=1
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=value
 def expected(initial,c,h,active):
  memory=dict(initial);calls=[];obs=[];angle=c.start&255
  for i in range(max(0,c.count)):
   quarter=d.sine((angle-64)&255);sample=d.sine(angle);calls.extend(((d.SINE,((angle-64)&255,)),(d.SINE,(angle,))))
   if active:
    point=(d.addmul(c.x,c.radius,quarter),c.y,d.addmul(c.z,c.radius,sample))
    a=(1,i,*point,c.x,c.y,c.z,angle,c.start&255,c.radius,c.arg8,c.arg9,c.arg10,c.arg11&255);calls.append((o.ENTRY,a))
    for off,value in((16,point[2]),(32,angle),(56,c.arg11)):o.put(memory,h+off,value)
    case=o.Case(actor=1,mode=i,phase=c.phase,angle=angle,slot=c.arg11,success=c.fail,mutation=c.mutation,randoms=(angle,angle*7,angle&1,(angle>>1)&1))
    memory,extra,observations=o.evaluate(memory,case,h,tuple(o.g.floating(v)for v in point));calls.extend(extra);obs.extend(observations)
   angle=(angle+c.step)&255
  return o.public(memory),calls,obs
 count=0;visits=set()
 cases=[(angle,n,step,success,mutation,1)for angle,n,step,success,mutation in itertools.product((0,128,255),(-1,0,1,3),(-128,7),(0,1),range(4))]
 cases +=[(angle,2,127,1,0,0)for angle in(0,128,255)]
 for index,(angle,n,step,success,mutation,active)in enumerate(cases):
  c=d.Case(start=angle,count=n,step=step,selector=selector,fail=success,mutation=mutation,phase=(index&1)*8,arg11=0x33)
  initial=o.fixture(o.Case(phase=c.phase));o.put(initial,d.TABLE+selector*4,o.ENTRY if active else 0);home=o.STACK+c.phase-frame;want=expected(initial,c,home,active)
  for body,raw in programs(state):
   m=Connected(body,c,raw,o.mapped(initial,home,raw)).run()
   calls=[o.calls_normalized([(t,a)],h,raw)[0]for(t,a),h in zip(m.calls,m.homes)]
   assert(o.public(m.memory),calls,m.obs)==want,(c,raw,calls,want[1])
   assert m.callback_count==(max(0,n)if active else 0)and m.sin_count==2*max(0,n)
   assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   visits.update(pc for pc in m.visits if entry<=pc<entry+384)
  count+=1
 missing=[(pc-entry)//4 for pc in range(entry,entry+384,4)if pc not in visits]
 report=dict(passes=True,cases=count,programs=3,complete_dispatcher_words_visited=len(visits),unvisited_dispatcher_words=missing,table_index=selector,all15_arguments_checked=True,allocation_failure_keeps_loop_running=True)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report

def factory(state):
 helper,allocate=0x15130280,0x15167a68;rom=state['rom'];live,_,_=load_elf_functions(str(s.FROZEN/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');connected={};seen={}
 for name,entry,off,n in(('func_15130374',o.FACTORY,0x15d824,18),('func_15130280',helper,0x15d730,61),('memcpy',o.COPY,0x22ec0,11)):
  ws=struct.unpack_from('>%dI'%n,rom,off);assert tuple(live[name])==ws,name;connected.update(zip(range(entry,entry+n*4,4),ws));seen[name]=(entry,n,set())
 class Connected(o.Oracle):
  def __init__(self,code,c,raw):super().__init__(code,c,raw);self.code.update(connected)
  def record_call(self,t):
   if t in(helper,allocate):self.calls.append((t,tuple(map(o.g.u32,self.arguments(6)))))
   else:super().record_call(t)
  def hook(self,t):
   if t==allocate:
    for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
    for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
    self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=o.OUTPUT if self.cc.success else 0
   else:super().hook(t)
 count=0
 for angle,success,mutation,phase in itertools.product((0,1,127,128,255),(0,1),range(4),(0,8)):
  c=o.Case(angle=angle,slot=0x33,success=success,mutation=mutation,phase=phase,randoms=(angle,angle*7,angle&1,(angle>>1)&1));want,calls,obs=o.evaluate(o.fixture(c),c);at=next(i for i,(t,_)in enumerate(calls)if t==o.FACTORY);h=o.STACK+phase;dsc=h-120;slot=0xfe if mutation&2 else c.slot
  extra=[(helper,(dsc,1,0,4,slot,1)),(allocate,(0x52,1,0xac,1,slot,1))]
  if success:extra.append((o.COPY,(o.OUTPUT+0x10,dsc,112)))
  calls=calls[:at+1]+extra+calls[at+1:]
  for body,raw in programs(state):
   m=Connected(body,c,raw).run();normalized=[]
   for t,args in m.calls:
    if t==helper and raw:args=(args[0]-4,*args[1:])
    normalized.extend(o.calls_normalized([(t,args)],h,raw))
   assert(o.public(m.memory),normalized,m.obs)==(o.public(want),calls,obs),(c,raw,normalized,calls)
   assert m.r[2]==1
   for _,(entry,n,visited)in seen.items():visited.update(pc for pc in m.visits if entry<=pc<entry+n*4)
  count+=1
 report=dict(passes=True,cases=count,programs=3,words={name:len(value[2])for name,value in seen.items()},allocation='modeled',source='complete retail functions checked against frozen production ELF')
 (s.OUT/'factory-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
