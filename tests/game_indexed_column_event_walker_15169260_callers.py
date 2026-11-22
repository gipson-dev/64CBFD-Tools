"""Complete retail/current array wrapper and actual two-word descriptor input."""
from pathlib import Path
from dataclasses import replace
import csv,itertools,json,struct,sys
from tools.experiments import game_indexed_column_event_walker_15169260_match as packet
root,out=packet.ROOT,packet.OUT
import guest as q
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
ROOT_CALLER=0x151494E0;INPUT=0x800A5770
class CallerOracle(q.Oracle):
 def record_call(self,t):
  if t==q.ENTRY:
   assert tuple(self.arguments(4))==q.args(self.case,self.syms),'Array-wrapper arguments differ'
   self.root_calls+=1;self.root_initial=dict(self.memory);return
  super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();before=(out/'baseline/conker/build/conker.us.elf').read_bytes();after=(out/'image-qualification/linked.elf').read_bytes()
 rows=list(csv.DictReader((root/'conker/progress.csv').open()));row=next(r for r in rows if r['function']=='func_151494E0');length=int(row['length']);offset=ROOT_CALLER-0x15000000+0x2D4B0
 at=elf_slot_offset(before,ROOT_CALLER,length);truth=rom[offset:offset+length];assert before[at:at+length]==after[at:at+length]==truth
 symbols={n:r for _,n,r,_ in symbol_rows(before)if n};body_size=symbols['func_151494E0'][2];assert body_size<=length
 caller=list(struct.unpack('>%dI'%(length//4),truth));frame=(-caller[0])&65535;assert frame and frame<=64
 array_at=elf_slot_offset(before,INPUT,8);pair=struct.unpack_from('>2I',before,array_at);assert all(v<104 for v in pair)
 jal=0x0C000000|(q.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(q.ENTRY>>2&0x3FFFFFF);direct=[];pointers=[];jumps=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  if w==jal:direct.append(4*i)
  if w==q.ENTRY:pointers.append(4*i)
  if w==jump:jumps.append(4*i)
 sites=[]
 for off in direct:
  va=0x15000000+off-0x2D4B0;sites.append(dict(ROM='0x%X'%off,VA='0x%X'%va,owners=[r['function']for r in rows if r['section']=='game'and int(r['offset'])<=va<int(r['offset'])+int(r['length'])]))
 paths=[out/'sdk-frame-last/candidate.o',out/'qualified-owner/game_1944C0.c.o',out/'original-target.o'];helpers=q.helper_code();seen=set()
 def machine(ws,c,broken=None):
  memory=q.fixture(c)
  for i,v in enumerate(pair):q.put(memory,INPUT+4*i,v)
  words=list(caller)
  if broken=='byte':
   indices=[i for i,w in enumerate(words)if w>>26==12 and w&65535==255];assert len(indices)==1;i=indices[0];w=words[i]
   words[i]=((w>>21&31)<<21)|((w>>16&31)<<11)|0x25
  if broken=='count':
   indices=[i for i,w in enumerate(words)if w>>26==9 and w>>21&31==0 and w>>16&31==5 and w&65535==2];assert len(indices)==1;words[indices[0]]^=3
  connected=dict(zip(range(q.ENTRY,q.ENTRY+4*len(ws),4),ws))
  if c.real_helpers:connected.update(helpers)
  m=CallerOracle.__new__(CallerOracle);FactoryOracle.__init__(m,words,memory,replace(c,phase=c.phase&8),entry=ROOT_CALLER,s=q.SYMS,connected=connected,arguments=(q.payload(c),0xABCD0000|(c.opcode&255)))
  m.case=c;m.target_home=q.STACK+c.phase;m.r[29]=m.target_home+frame;m.ws=ws;m.initial=dict(m.memory);m.before=m.r[:];m.before_f=m.f[:];m.observations=[];m.state=dict(fired=False);m.bound_helpers=connected;m.root_calls=0;m.root_initial=None;return m
 cases=[replace(q.Case(),columns=pair,count=2,list_override=INPUT,opcode=op,pattern=p,mode=mode,phase=phase,real_helpers=real)for op,p,mode,phase,real in itertools.product((1,15,16),range(3),(0,1,2,4,8,16,64,128),(0,8),(False,True))]
 cases +=[replace(q.Case(),columns=pair,count=2,list_override=INPUT,opcode=op)for op in range(256)]
 for path in paths:
  ws=q.words(path)
  for c in cases:
   m=machine(ws,c);m.run();assert m.root_calls==1;want,calls,obs=q.reference(m.root_initial,c)
   assert(q.g.public(m.memory),m.calls,m.observations)==(q.g.public(want),calls,obs),c
   assert all(m.memory[a]==want[a]for a in m.root_initial if m.target_home<=a<m.target_home+frame+32),('Caller homes',c)
   assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   assert q.read(m.memory,m.target_home+frame+4)==0xABCD0000|(c.opcode&255)
   seen.update(m.visits)
 for broken in('byte','count'):
  m=machine(q.words(paths[0]),cases[0],broken)
  try:m.run()
  except AssertionError:pass
  else:raise AssertionError('Ineffective caller '+broken+' control')
 assert {ROOT_CALLER+4*i for i in range(body_size//4)}<=seen
 r=dict(cases_per_stream=len(cases),streams=3,complete_caller_body_words=body_size//4,caller_slot_words=length//4,caller_frame=frame,
  actual_two_word_input=[int(x)for x in pair],original_current_private_image_caller_equal=True,all_opcode_bytes_and_wide_input_narrowing=True,
  effective_caller_controls=['missing-byte-mask','wrong-array-count'],direct_JAL_sites=sites,aligned_pointer_literals=['0x%X'%i for i in pointers],direct_jumps=['0x%X'%i for i in jumps],
  other_full_parents_not_executed=True,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
