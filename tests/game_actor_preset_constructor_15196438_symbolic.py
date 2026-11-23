"""Closed region proof: immutable preset reads, dead roles, byte-formal ABI."""
from pathlib import Path
from collections import Counter
import json,struct,sys
from tools.experiments import game_actor_preset_constructor_15196438_match as p
r=p.ROOT;o=p.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_actor_preset_constructor_15196438_guest as g
from tools.tests.game_actor_preset_constructor_15196438_normalizer import normalize
ARITIES={112:0,124:3,128:3,154:11,161:3,173:1,189:1}
CALLER_SAVED={1,2,3,*range(4,16),24,25,31}
RETURN_OBSERVABLE={2,*range(16,24),28,29,30,31}
def low(bits,value):
 if isinstance(value,int):return value&((1<<bits)-1)
 if isinstance(value,tuple)and value[0]in('signed','unsigned')and value[1]==bits:return value[2]
 if isinstance(value,tuple)and value[0]=='low'and value[1]==bits:return value
 return('low',bits,value)
def extend(bits,value,signed):
 value=low(bits,value)
 if isinstance(value,int):return((value^(1<<(bits-1)))-(1<<(bits-1)))&0xffffffff if signed else value
 return('signed'if signed else'unsigned',bits,value)
class Prefix:
 def __init__(self,words):
  self.words=words;self.r=[('initial-GPR',i)for i in range(32)];self.r[0]=0;self.r[2]=('preset-address',);self.r[29]=('private-frame',);self.f=[('initial-FPR',i)for i in range(32)];self.memory={};self.ro=[];self.private_reads=[]
 def instruction(self,i):
  w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;imm=((w&65535)^32768)-32768
  if op in(32,36,37,49):
   width={32:1,36:1,37:2,49:4}[op];address=(self.r[rs],imm)
   if rs==2:
    assert 0<=imm<96 and imm+width<=96;value=('preset-bits',imm,width);self.ro.append((imm,width,op==32))
   else:
    assert rs==29 and (address,width)in self.memory,(i,address,width);value=self.memory[address,width];self.private_reads.append((address,width))
   if op==49:self.f[rt]=value
   else:self.r[rt]=extend(width*8,value,op==32)
  elif op in(40,41):
   assert rs==29;self.memory[(self.r[rs],imm),1 if op==40 else 2]=low(8 if op==40 else 16,self.r[rt])
  elif op==9:
   assert rs==0;self.r[rt]=imm&0xffffffff
  elif w==0:pass
  else:raise AssertionError(('Unknown prefix instruction',i,hex(w)))
 def run(self):
  for i in range(61,94):self.instruction(i)
  return self
def reads_writes(w):
 op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63
 if not w:return set(),set()
 if op==0:
  if fn==8:return{rs},set()
  if fn==9:return{rs},{31}
  if fn in(0,2,3):return{rt},{rd}
  if fn in(33,35,37,42):return{rs,rt},{rd}
  raise AssertionError(('Unknown R operation',hex(w)))
 if op in(32,33,35,36,37):return{rs},{rt}
 if op==49:return{rs},set()
 if op in(40,41,43):return{rs,rt},set()
 if op==57:return{rs},set()
 if op==15:return set(),{rt}
 if op in(9,10,12):return{rs},{rt}
 if op in(4,5,20,21):return{rs,rt},set()
 if op in(1,6,7,22,23):return{rs},set()
 if op==3:return set(),{31}
 if op==17:
  assert rs==4;return{rt},set()
 raise AssertionError(('Unknown instruction',hex(w)))
def dead_after(words,start,registers):
 todo=[(start,frozenset(registers))];seen=set();checks=0
 def step(i,live):
  nonlocal checks
  uses,defines=reads_writes(words[i]);assert not(uses&live),('Old register read',i,uses&live);checks+=1;return live-defines
 while todo:
  pc,live=todo.pop()
  if not live or(pc,live)in seen:continue
  seen.add((pc,live));assert 0<=pc<196;w=words[pc];op=w>>26;fn=w&63
  live=step(pc,live)
  if op==3 or(op==0 and fn==9):
   live=step(pc+1,live);assert pc in ARITIES;assert not(live&set(range(4,4+min(4,ARITIES[pc])))),('Old register used as formal',pc);todo.append((pc+2,frozenset(live-CALLER_SAVED)))
  elif op in(1,4,5,6,7,20,21,22,23):
   # Conservative delay execution is stronger than necessary for likely
   # fallthrough. Both control destinations must kill before any use.
   live=step(pc+1,live);target=pc+1+(((w&65535)^32768)-32768);todo.extend(((target,frozenset(live)),(pc+2,frozenset(live))))
  elif op==0 and fn==8:
   live=step(pc+1,live);assert not(live&RETURN_OBSERVABLE),('Old role reaches ABI result',live)
  else:todo.append((pc+1,frozenset(live)))
 return checks
def rename(w,m):
 op=w>>26;shifts=(21,16,11)if op==0 else(21,)if op in(49,57)else(21,16)
 for shift in shifts:w=(w&~(31<<shift))|(m.get(w>>shift&31,w>>shift&31)<<shift)
 return w
def proof(write=True,words=None):
 ws=words or[g.bound_blob(*payload(o/path,'func_15196438'),g.S)for path in('selected-final/candidate.o','original-target.o')];a,b=ws;assert len(a)==len(b)==196
 prefix=[Prefix(w).run()for w in ws];left,right=prefix;assert left.memory==right.memory and left.f==right.f;assert Counter(left.ro)==Counter(right.ro);assert left.private_reads==right.private_reads
 for k in range(32):
  if k!=10:assert left.r[k]==right.r[k],('Live prefix role',k)
 assert left.r[10]!=right.r[10];dead_prefix=[dead_after(w,94,{10})for w in ws]
 # No branch or call enters the reordered straight-line field block.
 for i,w in enumerate(a):
  if w>>26 in(1,4,5,6,7,20,21,22,23):assert not 61<=i+1+(((w&65535)^32768)-32768)<=93
  if 61<=i<=93:assert w>>26!=3 and not(w>>26==0 and w&63==9)
 assert a[2]==b[2]==0xAFA60100 and a[134]==0x8FAB0100 and b[134]==0x93AB0103
 assert[(i,reads_writes(a[i])[0])for i in range(135,154)if 11 in reads_writes(a[i])[0]]==[(153,{29,11})]
 assert a[153]==b[153]==0xAFAB0024 and a[154]==b[154]==(0x0C000000|((g.ALLOCATE>>2)&0x3FFFFFF))
 # Low byte of a big-endian word is address+3. The actual allocator uses
 # LBU frame0x38+incomingWord9(0x24)+3, not a full-word channel read.
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x174F30)[0]==0x27BDFFC8;assert struct.unpack_from('>I',rom,0x174F74)[0]==0x93B9005F
 channel=('arbitrary-current-argument2-word',);assert low(8,channel)==low(8,extend(8,channel,False))
 # Within this block the pointer and selector have an injective allocation
 # 7->3 and 3->5. Incoming R5 is dead, and callbacks have one argument.
 for i in range(163,181):assert rename(a[i],{7:3,3:5})==b[i],('Role transform',i)
 assert ARITIES[173]==1;dead_roles=[dead_after(w,181,{3,5,7})for w in ws]
 assert not any(5 in reads_writes(a[i])[0]for i in range(163,181)if i!=173)
 covered=set(range(61,94))|{134}|set(range(163,181));identity=set(range(196))-covered
 assert all(a[i]==b[i]for i in identity);assert len(covered|identity)==196
 q=dict(source_and_retail_words_covered=196,unchanged_words=len(identity),reordered_prefix_instructions=33,private_field_writes_equal=len(left.memory),immutable_preset_read_multiset_equal=True,live_prefix_registers_equal_except_proven_dead_T2=True,prefix_dead_role_checks=dead_prefix,closed_pointer_selector_region_words=18,post_region_dead_role_checks=dead_roles,byte_formal_ABI_contract='Word134 reads current incoming argument2; allocation consumes only its unsigned low byte. LBU +3 restores retail zero-extension of the complete outgoing o32 word9. No claim that the raw full outgoing word is identical.',real_allocator_byte_load_proved=True,source_installed=p.installed(),matching_credit=0,limits='Read-only preset table and private frame are disjoint in the ordinary ABI. Prefix has no calls or branches; helpers may change public data afterward and preserve saved state/private inputs except designated outputs. Private alias/fault observations are literal normalized guest gates, not portable native initialized-gap claims.')
 if write:(o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n')
 return q
