"""Complete bounded retail producer/clamp/void-consumer window; no full-parent claim."""
from pathlib import Path
from dataclasses import replace
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_effect_transition_150db9e0_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_effect_transition_150db9e0_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=target_packet.ROOT;WINDOW=0x15029750;RETURN=0x1502977C;END=0x15029BA4;OTHER=0x15029784;COMMAND=0x90000
def original():
 text=(o/'baseline/conker/asm/50D80.s').read_text();body=text.split('glabel func_150265CC\n',1)[1].split('endlabel func_150265CC',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',body);blob=bytes.fromhex(''.join(w for _,_,w in rows));at=int(rows[0][0],16);assert blob==g.rom()[at:at+len(blob)]and int(rows[0][2],16)==0x27BDF8B0
 window=[(int(a,16),int(v,16),int(w,16))for a,v,w in rows if WINDOW<=int(v,16)<OTHER];assert len(window)==13;assert [a for a,_,_ in window]==list(range(0x56C00,0x56C34,4));assert window[9]==(0x56C24,0x15029774,0x0D436E78);assert text.count('jal        func_150DB9E0')==1
 return [w for _,_,w in window],len(rows)
class Code(WindowCode):
 def __getitem__(self,pc):
  if pc==RETURN and self.owner.pending is not None:self.owner.child_return()
  if pc in self.ends:self.owner.boundary=pc
  return super().__getitem__(pc)
class Connected(g.Machine):
 def __init__(self,window,leaf,c,command,opcode=0x35,provider=False,poison=None):
  m=g.fixture(c);home=g.STACK+c.phase;g.put(m,home+0x764,c.actor);g.put(m,home+0x770,0x12340000|(c.channel&255));m.update({COMMAND+i:0 for i in range(8)});m[COMMAND+4]=command&255;code={}if provider else dict(zip(range(g.ENTRY,g.ENTRY+640,4),leaf));super().__init__(window,c,memory=m,entry=WINDOW,arguments=(),connected=code);self.r[16]=COMMAND;self.r[2]=opcode;self.pending=None;self.child_count=0;self.provider=provider;self.poison=poison;self.code=Code(self.code,self);self.code.ends={END,OTHER}
 def record_call(self,t):
  if t!=g.ENTRY:return super().record_call(t)
  args=tuple(map(g.u32,self.arguments(3)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.c=replace(self.c,actor=args[0],transition=args[1],channel=args[2]);self.pending=(g.reference(self.memory,self.c,home=self.r[29]),len(self.calls),len(self.observations));self.child_args=args
 def child_return(self):
  want,calls,obs=self.pending;actual=(g.public(self.memory,self.c),self.calls[calls:],self.observations[obs:],self.fcsr);assert actual==want,dict(components=[a==b for a,b in zip(actual,want)]);self.pending=None;self.child_count+=1
  if self.poison is not None:self.r[2]=self.poison
 def hook(self,t):
  if t!=g.ENTRY:return super().hook(t)
  assert self.provider;want,_,_=self.pending;memory,calls,obs,csr=want;self.memory.update(memory);self.calls.extend(calls);self.observations.extend(obs);self.fcsr=csr;self.pending=None;self.child_count+=1
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA6000000+i
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=0xDEADBEEF
 def complete(self):
  try:self.run();raise AssertionError('missing bounded caller exit')
  except WindowBoundary:pass
  assert self.pending is None and self.r[29]==g.STACK+self.c.phase and self.r[16]==COMMAND
  if self.child_count:assert self.boundary==END and self.r[2]==1
  else:assert self.boundary==OTHER
  return self
def observable(m):return g.public(m.memory,m.c),m.calls,m.observations,m.fcsr,m.r[2],m.boundary
def main():
 window,parentwords=original();leaves=[g.bound_blob(*g.payload(o/f,'func_150DB9E0'),g.symbols())for f in('original-target.o','selected-owner.o')];seen=set();count=children=0
 for actor,command,channel,mutation,private,phase,opcode in itertools.product((0,g.ACTOR),(-128,-1,0,1,2,127),(0,128,255),(0,1),(0,1),(0,8),(0x35,0x26)):
  c=g.Case(actor=actor,channel=channel,mutation=mutation,private=private,phase=phase);models=[Connected(window,leaf,c,command,opcode).complete()for leaf in leaves];counterpart=Connected(window,leaves[0],c,command,opcode,provider=True).complete();assert g.state(models[0])==g.state(models[1]);assert observable(models[0])==observable(counterpart);seen.update(x for x in models[0].visits if WINDOW<=x<OTHER);count+=1;children+=models[0].child_count
 for poison in(0,1,0xFFFFFFFF):
  m=Connected(window,leaves[0],g.Case(),0,poison=poison).complete();assert m.child_count==1 and m.r[2]==1
 controls=[]
 for name,index,word,command in [('wrong-transition-clamp',4,0x28410003,2),('wrong-return-consumer',12,0x24020000,0)]:
  changed=window[:];changed[index]=word
  if name=='wrong-transition-clamp':
   a=Connected(window,leaves[0],g.Case(),command).complete();z=Connected(changed,leaves[0],g.Case(),command).complete();assert observable(a)!=observable(z)
  else:
   m=Connected(changed,leaves[0],g.Case(),command)
   try:m.run();raise AssertionError('missing wrong consumer boundary')
   except WindowBoundary:pass
   assert m.pending is None and m.child_count==1 and m.r[2]==0
  controls.append(dict(name=name,complete_bounded_window=True,wrong_behavior_rejected=True))
 assert len(seen)==13
 q=dict(complete_original_parent_ASM_ROM_words_pinned=parentwords,parent_frame=0x750,qualified_window_words=13,window_entry=hex(WINDOW),branch_exits=[hex(END),hex(OTHER)],whole_parent_execution_not_claimed=True,whole_parent_production_match_not_claimed=True,actual_signed_command_clamp_owner_home764_and_unsigned_channel_home773=True,three_word_void_ABI=True,return_register_poison_cases=3,void_return_ignored_and_caller_result_one=True,cases_per_stream=count,connected_children_per_stream=children,streams=2,raw_and_original_child_full_private_state_equal=True,independent_semantic_leaf_provider_counterpart=True,provider_private_stack_identity_not_claimed=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
