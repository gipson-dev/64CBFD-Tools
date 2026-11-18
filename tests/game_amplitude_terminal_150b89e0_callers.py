"""Full terrain-event caller and the other genuine dispatch window connected to C."""
import itertools,json,struct
from tools.experiments import game_amplitude_terminal_150b89e0_screen as s
from tools.tests import game_amplitude_terminal_150b89e0_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
TABLE=0x80089934;PARENT,MOVE,QUERY,ATTACHED=0x15133894,0x151337C0,0x15046C80,0x70000

def inputs(c,flags,selector,attachment):
 m=o.fixture(c);o.put(m,o.ACTOR+0x60,flags);m[o.ACTOR+0x73]=selector;o.put(m,o.ACTOR+0x130,0 if attachment<0 else ATTACHED)
 m.update({ATTACHED+i:0 for i in range(0x80)})
 if attachment>=0:m[ATTACHED+0x4f]=attachment
 o.put(m,TABLE,0);o.put(m,TABLE+4,o.ENTRY);return m

def run(state):
 elf=(s.FROZEN/'conker/build/conker.us.elf').read_bytes();assert struct.unpack_from('>I',elf,elf_slot_offset(elf,TABLE+4,4))[0]==o.ENTRY
 parent=struct.unpack_from('>80I',state['rom'],0x160D44);live,_,_=load_elf_functions(str(s.FROZEN/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(live['func_15133894'])==parent
 class Connected(o.Oracle):
  def __init__(self,body,c,flags,selector,cross,query,attachment):
   self.cc=c;self.i=self.j=0;self.obs=[];self.cross=cross;self.query=query;initial=inputs(c,flags,selector,attachment)
   o.g.Oracle.__init__(self,parent,initial,c,entry=PARENT,connected=dict(zip(range(o.ENTRY,o.ENTRY+1380,4),body)));self.r[4]=o.ACTOR;self.before=self.r[:];self.before_f=self.f[:];self.home=o.STACK+c.phase-80
  def record_call(self,t):
   if t in(MOVE,QUERY,o.ENTRY):
    n={MOVE:1,QUERY:4,o.ENTRY:6}[t];a=tuple(map(o.g.u32,self.arguments(n)));self.calls.append((t,a))
    if t==o.ENTRY:self.home=self.r[29]
    elif t==QUERY:self.obs.append(('query',o.g.packet(self.memory,a[0],12)))
   else:super().record_call(t)
  def hook(self,t):
   if t==MOVE:o.put(self.memory,o.ACTOR+0x3c,o.add(o.read(self.memory,o.ACTOR+0x3c),o.g.bits(-2. if self.cross else 2.)));answer=1
   elif t==QUERY:o.put(self.memory,o.ACTOR+0x110,o.g.bits(7.5));answer=self.query
   else:return super().hook(t)
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=answer
 def expected(c,flags,selector,cross,query,attachment):
  memory=inputs(c,flags,selector,attachment);old=tuple(o.read(memory,o.ACTOR+i)for i in(0x38,0x3c,0x40));o.put(memory,o.ACTOR+0x3c,o.add(old[1],o.g.bits(-2. if cross else 2.)));calls=[(MOVE,(o.ACTOR,))];obs=[];answer=1;home=o.STACK+c.phase-80
  if flags&1 and selector and cross:
   point=(old[0],o.add(o.read(memory,o.ACTOR+0x10),old[1]),old[2]);q=home+0x34
   for i,value in enumerate(point):o.put(memory,q+4*i,value)
   depth=o.add(o.read(memory,o.ACTOR+0x3c),o.read(memory,o.ACTOR+0x10)^0x80000000)
   calls.append((QUERY,(q,0,depth,o.ACTOR+0x110)));obs.append(('query',o.g.packet(memory,q,12)));o.put(memory,o.ACTOR+0x110,o.g.bits(7.5))
   if query and not(attachment>=0 and attachment&0x60==0x40):
    args=(o.ACTOR,*old,o.read(memory,o.ACTOR+0x110),o.ACTOR+0x114);calls.append((o.ENTRY,args));target_home=home
    for i,v in enumerate(args[1:],1):o.put(memory,target_home+4*i,v)
    public,extra,observed,answer=o.reference(memory,c,target_home);calls.extend(extra);obs.extend(observed);return public,calls,obs,answer
  return o.public(memory),calls,obs,answer
 visits=set();count=0
 for index,(amplitude,flags,selector,cross,query,attachment,success,mutation)in enumerate(itertools.product((o.g.bits(15.),o.g.bits(20.),o.g.bits(60.)),(0,1),(0,1),(0,1),(0,1),(-1,0,0x40,0x60),(0,1),(0,3,12))):
  c=o.Case(amplitude=amplitude,success=success,mutation=mutation,phase=(index&1)*8);want=expected(c,flags,selector,cross,query,attachment)
  for body in(state['retail_words'],state['raw_words']):
   m=Connected(body,c,flags,selector,cross,query,attachment).run();assert(o.public(m.memory),m.calls,m.obs,m.r[2])==want,(c,flags,selector,cross,query,attachment,m.calls,want[1])
   assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   visits.update(pc for pc in m.visits if PARENT<=pc<PARENT+320)
  count+=1
 report=dict(passes=True,cases=count,programs=2,complete_parent_words_visited=len(visits),table_index=1,all6_arguments_checked=True,terrain_and_motion_providers_modeled=True,source_installed=False,c_match_credit=0)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report

def other_window(state):
 start,positive,negative=0x15132FE0,0x15133028,0x151332C8;code=struct.unpack_from('>18I',state['rom'],0x160490);count=0
 class Connected(o.Oracle):
  def __init__(self,body,c,selector):
   self.cc=c;self.i=self.j=0;self.obs=[];initial=inputs(c,1,selector,-1);h=o.STACK+c.phase
   for i,value in enumerate((o.g.bits(2.25),o.g.bits(6.25),o.g.bits(4.75))):o.put(initial,h+0x374+4*i,value)
   o.put(initial,o.ACTOR+0x110,o.g.bits(-6.5))
   o.g.Oracle.__init__(self,code,initial,c,entry=start,connected=dict(zip(range(o.ENTRY,o.ENTRY+1380,4),body)));self.r[2]=selector;self.r[4]=self.r[16]=o.ACTOR;self.home=h
   self.code[positive]=self.code[negative]=0;self.code=WindowCode(self.code,self);self.code.ends=(positive,negative)
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,tuple(map(o.g.u32,self.arguments(6)))))
   else:super().record_call(t)
 for amplitude,success,mutation,selector,phase in itertools.product((o.g.bits(15.),o.g.bits(20.),o.g.bits(60.)),(0,1),range(4),(0,1),(0,8)):
  c=o.Case(amplitude=amplitude,success=success,mutation=mutation,phase=phase);initial=inputs(c,1,selector,-1);o.put(initial,o.ACTOR+0x110,o.g.bits(-6.5));want,calls,obs,answer=o.reference(initial,c);args=(o.ACTOR,o.g.bits(2.25),o.g.bits(6.25),o.g.bits(4.75),o.g.bits(-6.5),o.ACTOR+0x114)
  for body in(state['retail_words'],state['raw_words']):
   m=Connected(body,c,selector)
   try:m.run();raise AssertionError('dispatch window failed to stop')
   except WindowBoundary:pass
   if selector:assert(o.public(m.memory),m.calls,m.obs)==(want,[(o.ENTRY,args)]+calls,obs)
   else:assert m.calls==[]and m.obs==[]and o.public(m.memory)==o.public(initial)
   assert m.r[29]==o.STACK+phase
  count+=1
 report=dict(passes=True,cases=count,programs=2,window='0x15132FE0..0x15133028 / early return0x151332C8',complete_parent_not_claimed=True,source_installed=False,c_match_credit=0)
 (s.OUT/'other-caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
