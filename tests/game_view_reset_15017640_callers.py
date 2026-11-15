"""Original caller, unused-result proof, aligned bzero and SDK wrapper windows."""
import itertools,json,struct
from tools.experiments import game_view_reset_15017640_match as s
from tools.tests import game_view_reset_15017640_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put,read
START,END,NEXT,KILL=0x15008130,0x15008138,0x1501cc3c,0x1501cc9c

def uses(w):
 op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
 if not w:return set(),set()
 if op==0:
  if fn in (0,2,3):return {rt},{rd}
  if fn in (33,35,36,37,42,43):return {rs,rt},{rd}
  if fn==8:return {rs},set()
 if op==15:return set(),{rt}
 if op in (9,10,11,12,13,32,33,35,36,37):return {rs},{rt}
 if op in (40,41,43):return {rs,rt},set()
 if op in (4,5):return {rs,rt},set()
 if op in (2,3):return set(),{31} if op==3 else set()
 raise AssertionError(('Unmodeled result-use word',hex(w)))

def result_proof(rom,forward=False,remove_kill=False):
 queue=[(END,[])];paths=[]
 def word(pc):return struct.unpack_from('>I',rom,pc-0x15000000+0x2d4b0)[0]
 while queue:
  pc,path=queue.pop();assert len(path)<60 and (pc==END or NEXT<=pc<0x1501ccb8),hex(pc)
  w=word(pc)
  if forward and pc==END:w=0x00402025
  if remove_kill and pc==KILL:w=(w&~(31<<11))|(3<<11)
  rd,wr=uses(w);assert 2 not in rd,('Reads old V0',hex(pc))
  path=path+[pc]
  if 2 in wr:assert pc==KILL;paths.append(path);continue
  if w>>26 in (2,3):
   delay=word(pc+4);rd,wr=uses(delay);assert 2 not in rd|wr
   target=((pc+4)&0xf0000000)|((w&0x3ffffff)<<2);queue.append((target,path+[pc+4]))
  elif w>>26 in (4,5):
   rd,wr=uses(word(pc+4));assert 2 not in rd|wr
   target=pc+4+(((w&65535)^32768)-32768)*4
   same=(w>>21&31)==(w>>16&31)
   ends=((target,) if w>>26==4 else (pc+8,)) if same else (target,pc+8)
   for end in ends:queue.append((end,path+[pc+4]))
  else:queue.append((pc+4,path))
 assert len(paths)==4,len(paths)
 return dict(paths=len(paths),instruction_counts=sorted(map(len,paths)),first_kill=hex(KILL),old_v0_not_read=True)

class CallerOracle(g.Oracle):
 def record_call(self,t):
  if t==s.ENTRY:self.calls.append((t,()))
  else:super().record_call(t)

def caller(program,c,changed=False):
 words,_=program;rom=(s.ROOT/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>2I',rom,0x355e0))
 assert window==[0x0d405d90,0]
 if changed:window[0]=0x0c000000|(((s.ENTRY+4)>>2)&0x3ffffff)
 code=dict(zip(range(s.ENTRY,s.ENTRY+len(words)*4,4),words));code[END]=0
 initial=g.fixture(c);want,calls,states=g.reference(initial,c);m=CallerOracle(window,initial,c,START);m.code.update(code)
 saved=(m.r[16:24],m.r[29],m.f[20:]);m.code=WindowCode(m.code,m);m.code.ends=(END,)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Caller did not return to original continuation')
 assert(g.public(m.memory),m.calls,m.snapshots)==(want,[(s.ENTRY,())]+calls,states)
 assert(m.r[16:24],m.r[29],m.f[20:])==saved

class Connected(g.Oracle):
 def __init__(self,words,memory,c,entry,connected,targets):
  # Add exact original helper instructions to the existing executor.
  super().__init__(words,memory,c,entry);self.code.update(connected);self.sdk=[];self.targets=targets
 def record_call(self,t):
  if t in (g.ZERO,g.PERSPECTIVE):
   super().record_call(t)
   if t==g.ZERO:
    # Effects outside the clear region may occur at the opaque boundary. The
    # actual original bzero, rather than the hook, must clear every scratch byte.
    if self.case.mode&1:put(self.memory,g.FAR,0x43af4000)
    if self.case.mode&2:
     put(self.memory,0x800d242c,0xc0200000);put(self.memory,0x800d2414,0xc0000000)
     self.memory[0x800d24ad]=0x67;self.memory[0x800d2458]=0xe1
  else:
   assert t in self.targets,hex(t);n=7 if t==self.targets[0] else 2;args=tuple(self.arguments(n));self.sdk.append((t,args))
 def hook(self,t):
  assert t in self.targets
  args=self.sdk[-1][1]
  if t==self.targets[0]:
   expected=self.calls[-1][1];assert args[1:]==expected[1:] and self.r[29]<=args[0]<=self.target_home-40-64
   self.temp=args[0]
   for i in range(16):
    value=int.from_bytes(bytes((4*i+j)*11+self.case.seed+0x37&255 for j in range(4)),'big');put(self.memory,self.temp+i*4,value)
   put(self.memory,args[1],0x7fa5,2)
  else:
   assert args==(self.temp,0x800d23d0)
   for i in range(16):
    expected=int.from_bytes(bytes((4*i+j)*11+self.case.seed+0x37&255 for j in range(4)),'big');assert read(self.memory,self.temp+i*4)==expected
   g.effect(self.memory,self.case,True)
  for i in range(7 if t==self.targets[0] else 4):put(self.memory,self.r[29]+i*4,0xb5000000+i)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)]

def main():
 rom=(s.ROOT/'conker/conker.us.bin').read_bytes();programs=s.programs();proof=result_proof(rom);controls=0
 for args in ((True,False),(False,True)):
  try:result_proof(rom,*args)
  except AssertionError:controls+=1
  else:raise AssertionError('Ineffective old-result control')
 caller_count=0
 for xyz,mode,phase in itertools.product(((-32768,0,32767),(32767,-1,255),(1,2,3)),range(8),(0,8)):
  c=g.Case(xyz,mode=mode,phase=phase)
  for program in programs:caller(program,c)
  caller_count+=1
 try:caller(programs[0],g.Case(),True)
 except AssertionError:controls+=1
 else:raise AssertionError('Ineffective caller target control')
 wrapper=list(struct.unpack_from('>23I',rom,g.PERSPECTIVE-0x15000000+0x2d4b0));zero=list(struct.unpack_from('>40I',rom,0x226f0))
 targets=tuple(((g.PERSPECTIVE&0xf0000000)|((w&0x3ffffff)<<2)) for w in wrapper if w>>26==3);assert len(targets)==2 and targets[0]==0x15047f00
 helpers=dict(zip(range(g.PERSPECTIVE,g.PERSPECTIVE+92,4),wrapper));helpers.update(zip(range(g.ZERO,g.ZERO+160,4),zero))
 connected_count=0
 for mode,phase in itertools.product(range(8),(0,8)):
  c=g.Case(mode=mode,phase=phase)
  for words,entry in programs:
   initial=g.fixture(c);m=Connected(words,initial,c,entry,helpers,targets);m.run();g.compare(m,g.reference(initial,c));assert len(m.sdk)==2
  connected_count+=1
 bad=dict(helpers);bad[g.ZERO+0x38]=0 # One original unrolled zero store.
 initial=g.fixture(g.Case());m=Connected(programs[0][0],initial,g.Case(),s.ENTRY,bad,targets);m.run()
 try:g.compare(m,g.reference(initial,g.Case()))
 except AssertionError:controls+=1
 else:raise AssertionError('Original-zero control did not affect state')
 report=dict(caller_cases=caller_count,streams=3,caller_words=2,result_use_proof=proof,connected_cases=connected_count,original_bzero_words=40,original_projection_wrapper_words=23,bounded_inner_sdk_targets=[hex(t) for t in targets],effective_controls=controls,complete_parents_and_projection_math_not_claimed=True)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
