"""Literal helper homes and complete packets in retail, raw C and guarded C."""
import itertools,struct
from tools.tests import game_map_trail_emitter_151058b4_oracle as g
class Oracle(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.target_base=self.r[29]
  base=getattr(self,'target_base',g.STACK+self.case.phase)
  if t in(g.REAL,g.INTEGER):args=()
  elif t in(g.ENTRY,g.CHECK):args=(self.r[4],)
  elif t==g.SAMPLE:
   raw=self.arguments(5);assert raw[1:]==tuple(base+n for n in(-36,-28,-100,-104));args=(raw[0],0,0,0,0);self.private_arguments.append((t,raw[1:]))
  elif t==g.DIRECTION:
   raw=self.arguments(4);assert raw[3]==base-92;args=(*raw[:3],0);self.private_arguments.append((t,(raw[3],)))
  elif t==g.SPAWN:
   raw=self.arguments(6);assert raw[0]==base-36 and raw[2]==base-96;self.private_arguments.append((t,(raw[0],raw[2])))
   h=tuple(self.memory[raw[0]+i]for i in range(24));p=tuple(self.memory[raw[2]+i]for i in range(60));self.full_packets.append((h,p))
   data=(tuple(h[i]for i in g.HEADER_DEFINED),tuple(p[i]for i in g.PACKET_DEFINED));self.packets.append(data);args=(data[0],raw[1],data[1],*raw[3:])
  else:raise AssertionError(hex(t))
  self.calls.append((t,args));self.events.append(('CALL',t,args))
def check(truth,raw,normal):
 count=order=0;visits=[set(),set(),set()]
 for c in g.cases():
  initial=g.fixture(c);want=g.reference(initial,c);machines=[]
  for i,words in enumerate((truth,raw,normal)):
   m=Oracle(words,initial,c).run();assert(g.public(m.memory),m.calls,m.packets)==want;g.preserved(m,c);visits[i].update(m.visits);machines.append(m)
  a,b,n=machines
  assert all(a.private_arguments==v.private_arguments and a.full_packets==v.full_packets for v in(b,n)),(c,'private address or full packet')
  assert g.public_trace(a)==g.public_trace(n),(c,'guarded public access order')
  order+=g.public_trace(a)!=g.public_trace(b);count+=1
 assert all(len(v)==196 for v in visits)
 return dict(cases=count,streams=3,visited_words=[len(v)for v in visits],full_header_bytes=24,full_packet_bytes=60,private_arguments_physically_identical=True,padding_differences=0,raw_public_read_order_difference_cases=order,normalized_public_read_order_difference_cases=0,raw_frame=248,retail_frame=240)

def caller_checks(truth,raw,normal,root):
 rom=(root/'conker/conker.us.bin').read_bytes();wrapper=list(struct.unpack_from('>27I',rom,0x132CF8));count=0
 for c,command in itertools.product(list(g.cases())[::15],(0x38,0x39,0x37,0x138)):
  initial=g.fixture(c);want=g.reference(initial,c)if command&255==0x38 else(g.public(initial),[],[])
  final=dict(want[0]);final[g.RECORD+0x34]=(final[g.RECORD+0x34]|1)if command&255==0x38 else final[g.RECORD+0x34]&254 if command&255==0x39 else final[g.RECORD+0x34]
  machines=[]
  for words in(truth,raw,normal):
   linked=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words))
   m=Oracle(wrapper,initial,c,entry=0x15105848,connected=linked,arguments=(g.RECORD,0xDEADBEEF,command)).run()
   calls=([(g.ENTRY,(g.RECORD,)),*want[1]]if command&255==0x38 else[])
   assert(g.public(m.memory),m.calls,m.packets)==(final,calls,want[2]),(c,command,m.calls,calls)
   g.preserved(m,c);machines.append(m)
  assert all(machines[0].private_arguments==v.private_arguments and machines[0].full_packets==v.full_packets for v in machines[1:])
  assert g.public_trace(machines[0])==g.public_trace(machines[2]);count+=1
 return dict(cases=count,streams=3,original_wrapper_words=27,commands=[0x38,0x39,0x37,0x138],actual_wrapper_path=True,full_packets_and_physical_homes_identical=True)
