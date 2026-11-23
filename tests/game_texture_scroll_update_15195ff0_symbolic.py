"""Induction over the leaf's loops with ordered fresh symbolic memory reads."""
from pathlib import Path
import copy,json,sys
from tools.experiments import game_texture_scroll_update_15195ff0_match as p
r=p.ROOT;o=p.OUT
from tools.tests.game_group_record_pairs_15022024_symbolic import State as Base,atom,num,plus,scale,Z,eq,neg
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_texture_scroll_update_15195ff0_guest as g
HOME=0x90000
CUTS=({'outer':18,'tile':47,'update':70,'primary':109,'primary-inner':115,'secondary-start':131,'secondary':138,'secondary-inner':144,'association-start':160,'association':164,'association-inner':170,'next-link':180,'next-record':188},{'outer':18,'tile':47,'update':70,'primary':111,'primary-inner':119,'secondary-start':134,'secondary':141,'secondary-inner':149,'association-start':164,'association':168,'association-inner':174,'next-link':184,'next-record':193})
def expression(op,*args):
 return atom(op+repr(args))
def lt(a,b):
 if not a[2]and not b[2]:return g.s32(a[1])<g.s32(b[1])
 return('lt',a,b)
def bit_or(a,b):
 if a==Z:return b
 if b==Z:return a
 if not a[2]and not b[2]:return num(a[1]|b[1])
 return expression('or',*sorted((a,b),key=repr))
class State(Base):
 def __init__(self,words,raw):
  super().__init__(words,0);self.raw=raw;self.namespace='entry'
  for k in range(4):self.reg[4+k]=atom('ARG'+str(k))
 def saved(self,a):return not a[2]and HOME-124<=a[1]<=HOME-108
 def read(self,a,width,kind='u'):
  if self.saved(a):assert width==4 and a in self.mem,(a,width);return self.mem[a]
  v=atom(self.namespace+'/read%02d/%d%s'%(len(self.events),width,kind));self.events.append(('read',a,width,kind,v));return v
 def write(self,a,v,width):
  if self.saved(a):assert width==4;self.mem[a]=v
  else:self.events.append(('write',a,width,v))
 def instruction(self,i):
  w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;sa=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if op in(32,33):self.steps.append(i);self.reg[rt]=self.read(self.address(rs,imm),1 if op==32 else 2,'s');return
  if op==41:self.steps.append(i);self.write(self.address(rs,imm),expression('low16',self.reg[rt]),2);return
  if op==12:
   self.steps.append(i);a=self.reg[rs];self.reg[rt]=num(a[1]&(w&65535))if not a[2]else expression('and',a,w&65535);return
  if op==10:self.steps.append(i);self.reg[rt]=('bool',lt(self.reg[rs],num(imm)));return
  if op==0 and fn in(3,35,37,25,42):
   self.steps.append(i)
   if fn==3:
    a=self.reg[rt];self.reg[rd]=num(g.s32(a[1])>>sa)if not a[2]else expression('sra',a,sa)
   elif fn==35:self.reg[rd]=plus(self.reg[rs],scale(self.reg[rt],-1))
   elif fn==37:self.reg[rd]=bit_or(self.reg[rs],self.reg[rt])
   elif fn==25:self.lo=expression('mul-low',*sorted((self.reg[rs],self.reg[rt]),key=repr))
   elif fn==42:self.reg[rd]=('bool',lt(self.reg[rs],self.reg[rt]))
   self.reg[0]=Z;return
  super().instruction(i)
 def condition(self,w):
  op=w>>26;rs=w>>21&31;rt=w>>16&31
  if op==1:
   assert rt in(0,1);v=lt(self.reg[rs],Z);return v if rt==0 else neg(v)
  if op in(6,7):v=lt(Z,self.reg[rs]);return neg(v)if op==6 else v
  return super().condition(w)
def paths(start):
 todo=[start];done=[];cuts={v:k for k,v in CUTS[not start.raw].items()}
 while todo:
  m=todo.pop();assert len(m.steps)<240,(m.namespace,m.pc)
  if m.pc in cuts and m.steps:done.append((cuts[m.pc],m));continue
  i=m.pc;w=m.words[i]
  if w==0x03E00008:
   m.steps.append(i);m.instruction(i+1);assert m.reg[16:24]==m.initial[16:24]and m.reg[28:]==m.initial[28:];done.append(('return',m));continue
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
COMMON={'primary':(7,16),'secondary':(16,17),'record':(6,6),'gate':(8,8),'delta':(9,9),'opcode':(5,7),'sentinel':(4,4)}
PHASE={'u':(10,12),'v':(11,13),'width':(12,10),'height':(13,11)}
def mapping(kind):
 fields={}
 if kind=='outer':fields={'u':(10,12)}
 if kind in('tile','update'):fields=PHASE.copy()
 if kind=='tile':fields.update(tileU=(17,18),tileV=(20,19),level=(2,3),cursor=(18,2),maskedU=(25,25))
 if kind in('primary','secondary','primary-inner','secondary-inner'):
  fields.update(slot=(3,10),indices=(10,11),counts=(11,12))
 if kind in('primary','secondary'):fields.update(index=(13,2),count=(14,25)if kind=='primary'else(24,14))
 if kind in('primary-inner','secondary-inner'):fields.update(level=(2,3),cursor=(18,2),output=(17,13),word=(15,15)if kind=='primary-inner'else(25,24))
 if kind in('association','association-inner','next-link'):fields['link']=(10,11)
 if kind=='association':fields['count']=(15,14)
 if kind=='association-inner':fields.update(level=(2,3),cursor=(18,2),offset=(3,10),base=(25,24))
 return fields
def roles(m,kind):
 if kind=='return':return()
 values={name:m.reg[regs[not m.raw]]for name,regs in(COMMON|mapping(kind)).items()}
 if kind in('tile','update'):assert m.reg[3 if m.raw else 5]==Z
 if not m.raw and kind in('primary','primary-inner','secondary-start'):assert m.reg[18]==m.reg[6]
 if kind in('primary-inner','secondary-inner')and m.raw:values['slot']=plus(values['slot'],num(2))
 return tuple(sorted(values.items()))
def signature(kind,m):return(kind,tuple(sorted(m.conditions.items(),key=repr)),tuple(m.events),roles(m,kind),tuple(sorted(m.mem.items(),key=repr)))
def compare(a,b):
 left=sorted([signature(k,m)for k,m in a],key=repr);right=sorted([signature(k,m)for k,m in b],key=repr)
 if left!=right:
  (o/'symbolic-mismatch.txt').write_text(repr(left)+'\n\n'+repr(right));raise AssertionError(('Symbolic block mismatch',len(a),len(b)))
def seed(m,kind):
 m=copy.deepcopy(m);m.conditions={};m.events=[];m.steps=[];m.namespace=kind
 for name,regs in(COMMON|mapping(kind)).items():m.reg[regs[not m.raw]]=atom(kind+'/'+name)
 for name,value in(('gate',g.S['D_800BEAC0']),('delta',g.S['D_800BE9E4']),('opcode',0xF2000000),('sentinel',0xFFFFFFFF)):m.reg[COMMON[name][not m.raw]]=num(value)
 if kind in('outer','tile','update'):m.reg[3 if m.raw else 5]=Z
 if not m.raw and kind in('primary','primary-inner','secondary-start'):m.reg[18]=m.reg[6]
 if kind in('primary-inner','secondary-inner')and m.raw:m.reg[3]=plus(atom(kind+'/slot'),num(-2))
 return m
def proof(write=True,words=None):
 ws=words or[bound_blob(*payload(o/path,'func_15195FF0'),g.S)for path in('selected-final/candidate.o','original-target.o')]
 entry=[paths(State(w,k==0))for k,w in enumerate(ws)];compare(*entry);pending={'outer':[next(m for k,m in es if k=='outer')for es in entry]};done={};covered=[set().union(*(set(m.steps)for k,m in es))for es in entry]
 while pending:
  kind,pair=pending.popitem()
  if kind in done:continue
  outcomes=[paths(seed(m,kind))for m in pair];compare(*outcomes);done[kind]=len(outcomes[0])
  for n,es in enumerate(outcomes):covered[n].update(set().union(*(set(m.steps)for k,m in es)))
  for next_kind in {k for k,m in outcomes[0]}-{'return'}-set(done):pending[next_kind]=[next(m for k,m in es if k==next_kind)for es in outcomes]
 assert set(done)==set(CUTS[0]);assert covered==[set(range(197)),set(range(202))],[[i for i in range(len(ws[n]))if i not in v]for n,v in enumerate(covered)]
 q=dict(entry_paths=len(entry[0]),inductive_block_paths=dict(sorted(done.items())),source_words_covered=197,retail_words_covered=202,ordered_symbolic_reads_writes_equal=True,all_normal_returns_preserve_saved_registers=True,scope='32-bit modular GPRs; signed shifts, signed loads, mask/OR and low-word multiply explicit. Fresh ordered reads cover arbitrary public aliases outside saved private frame. Five copied address/cursor/branch operations follow the live role invariants. Private/fault states are separate literal guest gates.',source_installed=p.installed(),matching_credit=0)
 if write:(o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n')
 return q
