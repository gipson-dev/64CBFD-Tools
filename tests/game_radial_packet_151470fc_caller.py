"""Retail radial dispatcher call window connected to the callback body."""
import itertools,struct
from tools.experiments import game_radial_packet_151470fc_match as match
from tools.tests import game_radial_packet_151470fc_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def run(state):
 one,_=match.pad_both(state);bodies=(state['retail_words'],state['raw_words'],o.words(one));rom=state['rom'];entry,end=0x1514c3c4,0x1514c404;parent=struct.unpack_from('>16I',rom,0x179874);count=0
 class Connected(o.Oracle):
  def __init__(self,initial,c,body):
   self.cc=c;self.obs=[];self.i=self.j=0;connected=dict(zip(range(o.ENTRY,o.ENTRY+540,4),body));o.g.Oracle.__init__(self,parent,initial,c,entry=entry,connected=connected);self.home=o.STACK+c.phase
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,tuple(map(o.g.u32,self.arguments(15)))));self.home=self.r[29]
   else:super().record_call(t)
 for angle,success,mutation,phase in itertools.product((0,1,127,128,255),(0,1),(0,1,2,4),(0,8)):
  c=o.Case(actor=1,mode=7,angle=angle,slot=0x33,success=success,mutation=mutation,phase=phase,randoms=(angle,angle*7,angle*11,angle&1,(angle>>1)&1));initial=o.fixture(c);want,calls,obs=o.reference(initial,c)
  for body in bodies:
   m=Connected(initial,c,body);m.r[2]=o.ENTRY;m.r[4]=1;m.r[5]=7;m.r[7]=o.g.bits(-2.5);m.r[18]=angle;m.r[20]=8;m.r[22]=9;m.r[23]=10;m.r[30]=0x33
   for r,v in ((2,3.75),(6,1.25),(22,2.),(24,-2.5),(26,0.),(28,3.75),(30,4.)):m.f[r]=o.g.bits(v)
   m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('window did not stop')
   except WindowBoundary:pass
   args=m.calls[0];assert args[0]==o.ENTRY and args[1][0:5]==(1,7,o.g.bits(1.25),o.g.bits(-2.5),o.g.bits(3.75)) and args[1][8]==angle and args[1][14]==0x33,args
   assert o.public(m.memory)==want and m.calls[1:]==calls and m.obs==obs,(c,m.calls,calls)
   assert m.r[2]==1
  count+=1
 return dict(cases=count,programs=3,window='0x1514C3C4..0x1514C404',table='D_8008AA00[22]',return_controls_loop=True)


def factory(state):
 from tools.match_progress import load_elf_functions
 helper,allocate=0x15130280,0x15167a68;rom=state['rom'];live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');connected={};seen={}
 for name,entry,off,count in (('func_15130374',o.FACTORY,0x15d824,18),('func_15130280',helper,0x15d730,61),('memcpy',o.COPY,0x22ec0,11)):
  ws=struct.unpack_from('>%dI'%count,rom,off);assert tuple(live[name])==ws,name;connected.update(zip(range(entry,entry+count*4,4),ws));seen[name]=(entry,count,set())
 one,_=match.pad_both(state);bodies=(state['retail_words'],state['raw_words'],o.words(one));count=0
 class Connected(o.Oracle):
  def __init__(self,code,c):super().__init__(code,c);self.code.update(connected)
  def record_call(self,t):
   if t in (helper,allocate):self.calls.append((t,tuple(map(o.g.u32,self.arguments(6)))))
   else:super().record_call(t)
  def hook(self,t):
   if t==allocate:
    for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
    for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
    self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=o.OUTPUT if self.cc.success else 0
   else:super().hook(t)
 for angle,success,mutation,phase in itertools.product((0,1,127,128,255),(0,1),(0,1,2,3),(0,8)):
  c=o.Case(angle=angle,slot=0x33,success=success,mutation=mutation,phase=phase,randoms=(angle,angle*7,angle*11,angle&1,(angle>>1)&1));want,calls,obs=o.reference(o.fixture(c),c);at=next(i for i,(t,_) in enumerate(calls) if t==o.FACTORY);d=o.STACK+phase-0x70;slot=0xfe if mutation&2 else c.slot
  extra=[(helper,(d,1,0,4,slot,1)),(allocate,(0x52,1,0xac,1,slot,1))]
  if success:extra.append((o.COPY,(o.OUTPUT+0x10,d,112)))
  calls=calls[:at+1]+extra+calls[at+1:]
  for body in bodies:
   m=Connected(body,c).run();assert (o.public(m.memory),m.calls,m.obs)==(want,calls,obs),(c,m.calls,calls);assert m.r[2]==1
   for _,(entry,n,visited) in seen.items():visited.update(pc for pc in m.visits if entry<=pc<entry+n*4)
  count+=1
 return dict(cases=count,programs=3,words={name:len(value[2]) for name,value in seen.items()},allocation='modeled',source='retail functions checked against live ELF')
