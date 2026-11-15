"""Literal parent ABI, aligned entry census and guest-only private-stack aliases."""
import csv,io,itertools,json,struct
from tools.experiments import game_quaternion_matrix_1504a140_recovery as s
from tools.tests import game_quaternion_matrix_1504a140_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
START,END=0x150397e4,0x150397f0

class Caller(g.Oracle):
 def record_call(self,target):
  assert target==s.ENTRY;self.calls.append((target,tuple(self.arguments(2))))

def main():
 rom=(s.ROOT/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>3I',rom,0x66c94));assert window==[0x27a40098,0x0d412850,0x27a50220]
 programs=s.programs();count=0;controls=0
 quads=((1.,0.,0.,0.),(0.,1.,0.,0.),(1.,2.,-3.,4.),(0.,0.,0.,0.))
 def run(c,words,changed=None):
  initial,_=g.fixture(c);home=g.STACK+c.phase;args=(home+0x98,home+0x220)
  for i,v in enumerate(c.q):put(initial,args[0]+i*4,v)
  code=dict(zip(range(s.ENTRY,s.ENTRY+len(words)*4,4),words));code[END]=0;caller=window[:]
  if changed is not None:caller[changed]+=4
  m=Caller(caller,initial,c,args,START,connected=code);saved=(m.r[16:24],m.r[28:31],m.f[20:]);m.code=WindowCode(m.code,m);m.code.ends=(END,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Original parent continuation was not reached')
  assert g.public(m.memory,c.phase)==g.public(g.reference(initial,args,c.rule),c.phase)
  assert m.calls==[(s.ENTRY,args)] and (m.r[16:24],m.r[28:31],m.f[20:])==saved
 for q,phase,rule in itertools.product(quads,(0,8),('left','right')):
  c=g.Case(tuple(g.bits(v) for v in q),0,phase,rule)
  for words,_ in programs:run(c,words)
  count+=1
 for index in (0,2):
  try:run(g.Case(),programs[0][0],index)
  except AssertionError:controls+=1
  else:raise AssertionError('Incorrect caller pointer accepted')
 # Invalid callee-private aliases are a guest contract screen, not defined C
 # inputs. Preserve even the original response that corrupts its saved FPRs.
 private_cases=0;abi_corrupt=0
 for qoff,moff,phase in itertools.product((None,-64,-52),(None,-72,-64),(0,8)):
  if qoff is None and moff is None:continue
  c=g.Case(phase=phase);initial,args=g.fixture(c);home=g.STACK+phase;args=(args[0] if qoff is None else home+qoff,args[1] if moff is None else home+moff)
  for i,v in enumerate(c.q):put(initial,args[0]+i*4,v)
  states=[];failed=[]
  for words,entry in programs:
   m=g.Oracle(words,initial,c,args,entry)
   try:m.run();failed.append(False)
   except AssertionError:
    assert m.r[29]==home and entry+88*4 in m.visits and m.f[20:]!=m.saved_f;failed.append(True)
   states.append((m.r,m.f,m.memory,m.trace))
  assert states[0]==states[1] and failed[0]==failed[1];private_cases+=1;abi_corrupt+=failed[0]
 alignment=0
 for field,offset in itertools.product((0,1),(1,2,3)):
  c=g.Case();initial,args=g.fixture(c);args=list(args);args[field]+=offset;states=[]
  for words,entry in programs:
   m=g.Oracle(words,initial,c,tuple(args),entry)
   try:m.run()
   except g.AlignmentFault:pass
   else:raise AssertionError('Misalignment did not fault')
   states.append((m.r,m.f,m.memory,m.trace))
  assert states[0]==states[1];alignment+=1
 rows=list(csv.DictReader(io.StringIO((s.ROOT/'conker/retail_layout.us.txt').read_text())));end=max(int(r['end'],16) for r in rows if r['section']=='game')
 jal=0x0c000000|((s.ENTRY>>2)&0x3ffffff)
 calls=[0x2d4b0+i for i in range(0,end-0x15000000,4) if struct.unpack_from('>I',rom,0x2d4b0+i)[0]==jal]
 pointers=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==s.ENTRY]
 assert calls==[0x66c98] and not pointers
 report=dict(caller_cases=count,streams=2,window_words=3,direct_jal_rom=calls,literal_pointers=0,private_stack_guest_cases=private_cases,original_abi_corruption_cases=abi_corrupt,private_aliases_excluded_from_portable_c=True,alignment_faults=alignment,negative_controls=controls,complete_parent_not_claimed=True)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
