"""Private decoder semantics; deliberately grants no installation or match credit."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_visibility_bitplane_150a6760_screen as packet
r,o=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x150A6760;STREAM=0x30000;CURSORS=0x42000;TREE=0x43020;NODES=0x50000
S={name:v[1]for _,name,v,_ in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())if name}
signed=lambda x:((x&65535)^32768)-32768
def cases():
 return list(itertools.product((0,1,7,11,15,31),(0,1,7,8,9,17),range(3),(0,7),range(2)))
def fixture(c):
 plane,count,kind,remaining,links=c;seed=sum((i+1)*v for i,v in enumerate(c));index=(-2,0,3)[seed%3];offset=(0,1,0x8001)[seed%3]
 m={STACK+i:(i*17+seed)&255 for i in range(-64,128)}
 for n,v in(('D_800BE5D0',STREAM),('D_800BE5D4',CURSORS),('D_800BE5D8',TREE),('D_800DBE48',NODES if count else 0)):put(m,S[n],v)
 put(m,S['D_800DBE30']+plane*2,index,2);put(m,CURSORS+index*4,offset,2);put(m,CURSORS+index*4+2,remaining,2)
 for j in range(32):m[STREAM+offset+j]=(j*73+seed*11+0x5A)&255
 for j in range(-32,64):m[TREE+j]=0
 def node(at,value,left=0,right=0):
  for delta,v in((0,value),(2,left),(4,right)):put(m,TREE+at+delta,v,2)
 if kind==0:node(0,0x7FFF)
 elif kind==1:node(0,-1,-16,16);node(-16,0x55);node(16,0xAA)
 else:
  node(0,-1,-16,16);node(-16,-2,-32,32);node(16,-3,32,48);node(-32,0);node(32,0x7FFF);node(48,0xA5)
 order=list(range(count))
 # Alternate the lowest and highest unvisited physical records.
 if links:
  order=[];lo,hi=0,count-1
  while lo<=hi:
   order.append(lo);lo+=1
   if lo<=hi:order.append(hi);hi-=1
 for j in range(17*16):m[NODES+j]=(j*29+seed*13+0x31)&255
 for pos,physical in enumerate(order):
  p=NODES+physical*16;nxt=0 if pos==count-1 else (order[pos+1]-physical)*16
  primary=nxt if not links or pos%2==0 else 0
  alternate=nxt if links and pos%2 else (16 if nxt else 0)
  put(m,p+12,primary,2);put(m,p+4,alternate,2)
 return m,(plane,),dict(index=index,offset=offset,seed=seed,order=order)
def reference(initial,args):
 m=initial.copy();plane=args[0];trace=[]
 def get(p,n=4,sgn=False):
  v=read(m,p,n);trace.append(('R',p,n,v));return signed(v)if sgn else v
 def store(p,v):put(m,p,v,2);trace.append(('W',p,2,v&65535))
 stream=get(S['D_800BE5D0'])
 if not stream:return m,trace
 clear=~(1<<plane)&0xFFFFFFFF;output=get(S['D_800DBE48']);bit=0
 entry=get(S['D_800DBE30']+2*plane,2,True)*4+get(S['D_800BE5D4'])
 stream+=get(entry,2);remaining=get(entry+2,2,True);current=get(stream,1);tree=get(S['D_800BE5D8'])
 symbol=0;iterations=0
 while output:
  if bit==0:
   cursor=tree
   while True:
    symbol=get(cursor,2,True)
    if symbol>=0:break
    if remaining==0:stream+=1;current=get(stream,1);remaining=7
    else:remaining-=1
    cursor=tree+get(cursor+(4 if(current>>remaining)&1 else 2),2,True)
  value=(get(output,2,True)&clear)|(((symbol>>bit)&1)<<plane);store(output,value)
  bit=(bit+1)%8;nextOffset=get(output+12,2,True);alternate=get(output+4,2,True)
  delta=nextOffset or alternate
  if not delta:break
  output+=delta;iterations+=1;assert iterations<40
 return m,trace
def public(m):return {a:b for a,b in m.items()if not STACK-64<=a<STACK+128}
class DecoderOracle(FactoryOracle):
 def execute(self,word):
  fn=word&63;rs=word>>21&31;rt=word>>16&31;rd=word>>11&31
  if word>>26==0 and fn in(4,6,7,0x27):
   shift=self.r[rs]&31;value=self.r[rt]&0xFFFFFFFF
   if fn==4:value<<=shift
   elif fn==6:value>>=shift
   elif fn==7:value=((value^0x80000000)-0x80000000)>>shift
   else:value=~(self.r[rs]|value)
   self.r[rd]=value&0xFFFFFFFF;self.r[0]=0
  else:super().execute(word)
def machine(words,m,args):return DecoderOracle(words,m.copy(),Case(),entry=ENTRY,s={},arguments=args).run()
def accesses(m):return [e for e in m.trace if not STACK-64<=e[1]<STACK+128]
def main():
 retail=list(struct.unpack_from('>64I',(r/'conker/conker.us.bin').read_bytes(),0xD3C10));programs={'retail':retail}
 for label in('initial','loop','initialized'):programs[label]=bound_blob(*payload(o/label/'candidate.o','func_150A6760'),S)
 traces={n:0 for n in programs};visits=set();rows=cases()
 for case in rows:
  initial,args,_=fixture(case);expected,events=reference(initial,args)
  for name,words in programs.items():
   m=machine(words,initial,args);assert public(m.memory)==public(expected),(name,case)
   traces[name]+=accesses(m)!=events
   if name=='retail':visits.update(m.visits)
 assert traces['retail']==0,traces
 early=[]
 for plane in(0,31):
  m={};put(m,S['D_800BE5D0'],0)
  for name,words in programs.items():
   actual=machine(words,m,(plane,));assert public(actual.memory)==m and accesses(actual)==[('R',S['D_800BE5D0'],4,0)],name
  early.append(plane)
 controls={}
 for name,old,new in(('unsigned-plane-map',0x84420000,0x94420000),('wrong-byte-boundary',0x240D0007,0x240D0006),('wrong-link-precedence',0x8522000C,0x85220004)):
  assert retail.count(old)==1,(name,hex(old));ws=retail.copy();ws[ws.index(old)]=new;caught=0
  for case in rows:
   initial,args,_=fixture(case);expected,_=reference(initial,args)
   try:caught+=public(machine(ws,initial,args).memory)!=public(expected)
   except (AssertionError,KeyError):caught+=1
   if caught:break
  assert caught,name;controls[name]=caught
 q=dict(cases_per_stream=len(rows),streams=list(programs),retail_access_trace_equal=True,candidate_access_trace_differences=traces,null_stream_early_return_planes=early,retail_unexecuted_words=[i for i in range(64)if ENTRY+4*i not in visits],effective_controls=controls,source_installed=False,matching_credit=0,limits='Bounded allocated trees and finite relative node chains. No full caller, private-state, fault-prefix, hardware or gameplay acceptance.')
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
