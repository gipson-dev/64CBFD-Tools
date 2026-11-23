"""Complete direct-match renderer with actual mode helper and bounded matrix provider."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_indexed_matrix_renderer_15168c4c_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_renderer_15168118_guest as g
ENTRY=0x15168C4C;MATRIX=0x15043D90;MODE=0x15142FBC
STATE=g.STATE;OUTPUT=g.OUTPUT;STACK=g.STACK
@dataclass(frozen=True)
class Case(g.Case):
 mode:int=1
 combine:int=0
 alpha:int=255
 tile:int=0
 buffer:int=0
 effect:int=0
 cache_match:bool=False
 pattern:int=0
 home_word:int=0xA1B2C3D4
def words(name):
 inventory=json.loads((o/'inventory.json').read_text())['functions'][name];rom=(r/'conker/conker.us.bin').read_bytes();return list(struct.unpack_from('>%dI'%inventory['words'],rom,int(inventory['ROM'],16)))
def fixture(c):
 m=g.fixture(c)
 for i in range(-16,256):m[STATE+i]=(i*17+c.pattern*19+0xA5)&255
 for i in range(-16,512):m[OUTPUT+i]=(i*13+c.pattern*23+0x5A)&255
 values=(0,0x80000000,0x3F800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x00800000,1,0x3F000001)
 for i,off in enumerate((0x90,0x94,0x98,0x9C,0xA0,0xA4,0xC0,0xC4,0xC8)):g.put(m,STATE+off,values[(i+c.pattern)%len(values)])
 g.put(m,STATE+0xD0,0x80123400+c.pattern*8);m[STATE+0xE5]=c.alpha;m[STATE+0xE6]=c.tile;m[STATE+0xEC]=c.mode;m[STATE+0xED]=c.combine
 m[g.SYMS['D_800BE9C0']]=c.buffer
 for name in('D_800DD1C0','D_800DD1C2','D_800DD1C4','D_800DD1C6'):g.put(m,g.SYMS[name],0xA5A5,2)
 actual_mode=c.mode
 if c.effect&2:actual_mode=2 if c.mode==1 else 1
 low={1:0x552230,2:0x504A50}.get(actual_mode,c.home_word)
 for name,value in(('D_800DD218',0x8ACA0),('D_800DD21C',low)):g.put(m,g.SYMS[name],value if c.cache_match else 0xDEADBEEF)
 g.put(m,STACK+c.phase-8,c.home_word)
 return m
def matrix_arguments(m,state=STATE):
 return(state+0x10+64*m[g.SYMS['D_800BE9C0']],*[g.get(m,state+off)for off in(0x9C,0xA0,0xA4,0xC0,0xC4,0xC8,0x90,0x94,0x98)])
def matrix_contract(m,c,a,state=STATE):
 # Argument transport and post-call live reads, not an emulation of rotation/FCSR.
 for i in range(16):g.put(m,a[0]+i*4,0x4D000000^a[1+i%9]^(i*0x01010101))
 if c.effect&1:m[g.SYMS['D_800BE9C0']]^=1
 if c.effect&2:
  m[state+0xE5]^=0x5A;m[state+0xE6]^=0x3F;m[state+0xEC]=2 if m[state+0xEC]==1 else 1
 if c.effect&4:m[state+0xED]=int(m[state+0xED]!=1);g.put(m,state+0xD0,0x80123458)
 if c.effect&8:
  for name in('D_800DD1C0','D_800DD1C2','D_800DD1C4','D_800DD1C6'):g.put(m,g.SYMS[name],0x4321,2)
def reference(initial,c,state=STATE,output=OUTPUT,home_word=None):
 m=dict(initial);log=[];a=matrix_arguments(m,state);log.append(('matrix',a));matrix_contract(m,c,a,state)
 def command(w0,w1):
  nonlocal output
  g.put(m,output,w0);g.put(m,output+4,w1);output+=8
 command(0xE7000000,0);command(0xFA000000,m[state+0xE5]);g.put(m,g.SYMS['D_800DD1C6'],m[state+0xE5],2)
 g.put(m,g.SYMS['D_800DD1C4'],0,2);g.put(m,g.SYMS['D_800DD1C2'],g.get(m,g.SYMS['D_800DD1C4'],2),2);g.put(m,g.SYMS['D_800DD1C0'],g.get(m,g.SYMS['D_800DD1C2'],2),2)
 command(0xFB000000,0);command(0xF2002000|m[state+0xE6],0x0007E0FE)
 mode={1:0x552230,2:0x504A50}.get(m[state+0xEC],c.home_word if home_word is None else home_word)
 log.append(('mode',(output,0x8ACA0,mode,'sync')))
 if g.get(m,g.SYMS['D_800DD218'])!=0x8ACA0 or g.get(m,g.SYMS['D_800DD21C'])!=mode:
  command(0xEF08ACAF,mode);g.put(m,g.SYMS['D_800DD218'],0x8ACA0);g.put(m,g.SYMS['D_800DD21C'],mode)
 if m[state+0xED]==1:command(0xFC123824,0xFF73FFFF)
 command(0xDA380003,state+0x10+64*m[g.SYMS['D_800BE9C0']]);command(0xDE000000,g.get(m,state+0xD0))
 return m,log,output
class Oracle(g.Oracle):
 def __init__(self,ws,m,c,entry=ENTRY,connected=None,arguments=None):
  mode=g.bound_blob(*g.payload(o/'baseline/conker/build/src/game_16EE20.c.o','func_15142FBC'),g.SYMS)
  code={MODE+i*4:w for i,w in enumerate(mode)};code.update(connected or{})
  super().__init__(ws,m,c,entry=entry,connected=code,arguments=(OUTPUT,STATE,g.u32(c.view))if arguments is None else arguments);self.log=[];self.active=STATE
 def record_call(self,t):
  if t==MATRIX:
   a=tuple(map(g.u32,self.arguments(10)));self.calls.append((t,a));self.log.append(('matrix',a));return
  if t==MODE:
   a=tuple(map(g.u32,self.arguments(4)));assert g.get(self.memory,a[3],1)==0,('Nonzero sync at mode call',a)
   self.calls.append((t,a));self.log.append(('mode',(*a[:3],'sync')));return
  raise AssertionError(('Unknown renderer helper',hex(t)))
 def clobber(self,value=0xDEADBEEF):
  for i in range(4):g.put(self.memory,self.r[29]+i*4,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=g.u32(value)
 def hook(self,t):
  assert t==MATRIX;matrix_contract(self.memory,self.case,self.calls[-1][1],self.active);self.clobber()
def cases():
 result=[Case(mode=mode,combine=combine,alpha=alpha,tile=tile,buffer=buffer,cache_match=cache,pattern=(alpha+tile+mode)%9)for mode,combine,alpha,tile,buffer,cache in itertools.product((1,2),(0,1,2),(0,1,127,255),(0,1,127,255),(0,1),(False,True))]
 result +=[Case(mode=mode,combine=combine,buffer=buffer,effect=effect,pattern=pattern,view=view,phase=phase)for mode,combine,buffer,effect,pattern,view,phase in itertools.product((1,2),(0,1),(0,1),(1,2,4,8,15),(0,4,8),(-32768,32767),(0,8))]
 return result
def main():
 paths={'raw':'selected-final/candidate.o','retail':'original-target.o'}
 if(o/'qualified-owner/game_1944C0.c.o').exists():paths['padded']='qualified-owner/game_1944C0.c.o'
 streams={n:g.bound_blob(*g.payload(o/p,'func_15168C4C'),g.SYMS)for n,p in paths.items()};assert all(ws==words('func_15168C4C')for ws in streams.values())
 coverage=set();rows=cases()
 for c in rows:
  initial=fixture(c);expected,log,value=reference(initial,c)
  for name,ws in streams.items():
   m=Oracle(ws,initial,c).run();assert(g.public(m.memory),m.log,m.r[2])==(g.public(expected),log,value),(name,c,m.log,log,m.r[2],value);coverage.update(m.visits)
 residue_cases=0
 for mode,seed,phase in itertools.product((0,3,127,255),(0,0x00552230,0x00504A50,0xA1B2C3D4),(0,8)):
  c=Case(mode=mode,home_word=seed,phase=phase,combine=1);initial=fixture(c);expected,log,value=reference(initial,c)
  for name,ws in streams.items():
   m=Oracle(ws,initial,c).run();assert(g.public(m.memory),m.log,m.r[2])==(g.public(expected),log,value),(name,c,m.log,log);coverage.update(m.visits)
  residue_cases+=1
 report=dict(streams=list(streams),direct_122_word_and_named_binding_identity=True,cases_per_stream=len(rows),guest_private_residue_cases_per_stream=residue_cases,unexecuted_words=[i for i in range(122)if ENTRY+i*4 not in coverage],complete_actual_mode_helper_words=34,source_installed=packet.installed(),matching_credit=0,limits='Complete original/direct C/padded renderer and actual34-word mode helper; matrix provider is bounded argument/state transport, not rotation arithmetic/FCSR. Native C defined-mode claims are restricted to1/2; other modes preserve actual guest SP60 residue, including mode0 emitted upstream.')
 (o/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
