"""Relational block induction, including an explicit o32 argument-home contract."""
from pathlib import Path
import copy,json,sys
from tools.experiments import game_layout_slot_registration_15195aa8_match as p
r=p.ROOT;o=p.OUT
from tools.tests.game_group_record_pairs_15022024_symbolic import State as Base,atom,num,plus,scale,Z,eq,neg
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_layout_slot_registration_15195aa8_guest as g
CUTS=({25:'outer',47:'list',91:'primary',111:'secondary'},{25:'outer',47:'list',92:'primary',113:'secondary'})
HOME=0x90000;STATE_HOME=num(HOME+16)
class State(Base):
 def __init__(self,words,raw):
  super().__init__(words,0);self.raw=raw;self.namespace='entry';self.shadow=atom('ARG4');self.mem[STATE_HOME]=self.shadow
  for i in range(4):self.reg[4+i]=atom('ARG'+str(i))
 def private(self,a):return not a[2]and HOME-96<=a[1]<HOME
 def read(self,a,width,kind='u'):
  if self.private(a):assert a in self.mem,(a,width);return self.mem[a]
  if a==STATE_HOME:
   assert width==4;v=self.mem[a];self.events.append(('ABI-read',a,4,v));return v
  v=atom(self.namespace+'/read%02d/%d%s'%(len(self.events),width,kind));self.events.append(('read',a,width,kind,v));return v
 def write(self,a,v,width):
  if self.private(a):assert width==4;self.mem[a]=v
  elif a==STATE_HOME:self.mem[a]=v;self.events.append(('ABI-write',a,width,v))
  else:self.events.append(('write',a,width,v))
 def instruction(self,i):
  w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;sa=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if op==33:self.steps.append(i);self.reg[rt]=self.read(self.address(rs,imm),2,'s');return
  if op in(40,41):self.steps.append(i);self.write(self.address(rs,imm),('low',8 if op==40 else 16,self.reg[rt]),1 if op==40 else 2);return
  if op==10:self.steps.append(i);self.reg[rt]=('bool',('lt',self.reg[rs],num(imm)));return
  if op==0 and fn==3:self.steps.append(i);self.reg[rd]=atom('sra%d(%r)'%(sa,self.reg[rt]));return
  super().instruction(i)
  if self.raw and i in(61,74):assert self.reg[16]==Z;self.shadow=Z
 def call(self,i):
  w=self.words[i];target=(g.ENTRY&0xF0000000)|((w&0x3FFFFFF)<<2);name=next(n for n in g.ROLES if g.S[n]==target);self.instruction(i+1);args=tuple(self.reg[j]for j in range(4,8));self.events.append(('call',name,args));tag=self.namespace+'/call%02d/%s'%(len(self.events),name)
  if name==g.ROLES[0]:assert args[3]==num(HOME-16);self.mem[args[3]]=atom(tag+'/tile')
  for k in range(4):self.mem[plus(self.reg[29],num(4*k))]=atom(tag+'/outgoing%d'%k)
  for k in(1,2,3,*range(4,16),24,25):self.reg[k]=atom(tag+'/R%d'%k)
  self.reg[2]=atom(tag+'/return');self.reg[31]=num(g.ENTRY+4*(i+2));self.steps.extend([i]);self.pc=i+2
def paths(start):
 todo=[start];done=[]
 while todo:
  m=todo.pop();assert len(m.steps)<350
  if m.pc in CUTS[not m.raw]and m.steps:done.append((CUTS[not m.raw][m.pc],m));continue
  i=m.pc;w=m.words[i]
  # Raw C's public semantics are extended by the two explicitly specified
  # ABI home actions. They are never presented as literal raw instructions.
  if m.raw and i==21:m.shadow=m.read(STATE_HOME,4)
  if m.raw and i==131:m.write(STATE_HOME,m.shadow,4)
  if w==0x03E00008:
   assert m.reg[31]==m.initial[31];m.instruction(i+1);assert m.reg[16:24]==m.initial[16:24]and m.reg[28:]==m.initial[28:];done.append(('return',m));continue
  if w>>26==3:m.call(i);todo.append(m);continue
  c=m.condition(w)
  if c is not None:
   for take in(True,False):
    n=copy.deepcopy(m)
    if not n.constrain(c,take):continue
    n.steps.append(i)
    if take or w>>26 not in(20,21):n.instruction(i+1)
    n.pc=i+1+(((w&65535)^32768)-32768)if take else i+2;todo.append(n)
  else:m.instruction(i);m.pc+=1;todo.append(m)
 return done
def roles(m,kind):
 if kind=='return':return(m.reg[2],m.mem[STATE_HOME])
 regs=(30,21,23,22,17,18)if m.raw else(30,20,23,21,16,17)
 values=tuple(m.reg[x]for x in regs)+(m.shadow if m.raw else m.reg[22],)
 if kind=='list':values+=(m.reg[20 if m.raw else 19],m.reg[19 if m.raw else 18],m.reg[6])
 if kind in('primary','secondary'):values+=(m.reg[20 if m.raw else 19],m.reg[16 if m.raw else 2]);assert(m.shadow if m.raw else m.reg[22])==Z
 if kind=='outer':assert m.reg[4]==m.reg[30]
 return values
def signature(kind,m):return(kind,tuple(sorted(m.conditions.items(),key=repr)),tuple(m.events),roles(m,kind),tuple(sorted(m.mem.items(),key=repr)))
def compare(a,b):
 left=sorted([signature(k,m)for k,m in a],key=repr);right=sorted([signature(k,m)for k,m in b],key=repr)
 if left!=right:(o/'symbolic-mismatch.txt').write_text(repr(left)+'\n\n'+repr(right));raise AssertionError('Symbolic block mismatch')
def seed(m,kind):
 m=copy.deepcopy(m);m.conditions={};m.events=[];m.steps=[];m.namespace=kind
 mapping={'display':(30,30),'asset':(21,20),'mode':(23,23),'search':(22,21),'record':(17,16),'index':(20,19),'size':(19,18),'slot':(16,2),'scale':(6,6)}
 live=['display','asset','mode','search','record']
 if kind=='list':live+=['index','size','scale']
 if kind in('primary','secondary'):live+=['index','slot']
 for name in live:m.reg[mapping[name][not m.raw]]=atom(kind+'/'+name)
 m.reg[18 if m.raw else 17]=num(0xFFFFFFFF)
 state=Z if kind in('primary','secondary')else atom(kind+'/state');m.shadow=state
 if not m.raw:m.reg[22]=state
 if kind=='outer':m.reg[4]=m.reg[30]
 # Both streams have the same literal frame and saved-register addresses.
 # Independent symbolic tile data and preserved incoming formal home values
 # cover arbitrary provider returns/public side effects under the o32 ABI.
 m.mem[num(HOME-16)]=atom(kind+'/tile');m.mem[STATE_HOME]=atom('ARG4')
 return m
def proof(write=True,words=None):
 ws=words or[bound_blob(*payload(o/path,'func_15195AA8'),g.S)for path in('selected-final/candidate.o','original-target.o')];entry=[paths(State(w,i==0))for i,w in enumerate(ws)];compare(*entry);assert[len(x)for x in entry]==[3,3];pending={'outer':[next(m for k,m in es if k=='outer')for es in entry]};done={};samples={}
 while pending:
  kind,pair=pending.popitem()
  if kind in done:continue
  outcomes=[paths(seed(m,kind))for m in pair];compare(*outcomes);done[kind]=len(outcomes[0]);samples[kind]=outcomes
  for next_kind in {k for k,m in outcomes[0]}-{'return'}-set(done):
   pending[next_kind]=[next(m for k,m in es if k==next_kind)for es in outcomes]
 assert set(done)=={'outer','list','primary','secondary'}
 q=dict(entry_paths=3,inductive_block_paths={k:done[k]for k in('outer','list','primary','secondary')},public_effects_and_four_argument_helper_calls_equal=True,explicit_ABI_home_contract='Read incoming SP+0x10 once on nonnull path; preserve until successful binding clears it, then write back on normal common exit only.',callee_saved_registers_and_frame_preserved=True,limits='32-bit modular GPR expressions; signed LH/SRA modeled symbolically. ABI providers may mutate public data, preserve saved registers and private frame/argument home. Private-frame aliases and faults are separately literal guest gates.',source_installed=p.installed(),matching_credit=0)
 if write:(o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n')
 return q
