"""Complete original127-word record dispatcher with the actual leaf attached."""
from pathlib import Path
from dataclasses import dataclass
from unittest.mock import patch
import hashlib,itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.tests import game_height_interpolation_151155c0_guest as g
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.patch_generated_slice_ld import load_game_data_layout
from tools.experiments import game_height_interpolation_151155c0_match as p
o=p.OUT;r=Path.cwd();PARENT=0x15113e54;COUNT,SKIP,BASE,GROUPCOUNT,GROUPBASE=0x800dbef0,0x800dbf98,0x800dbef4,0x80087380,0x800d23c0;RECORDS=0x30000;GROUPS=0x90000;SIZE=160
assert abs(GROUPS-g.STACK)>1024 and abs(RECORDS-g.STACK)>1024
@dataclass(frozen=True)
class Case:
 count:int=1
 skip:int=0
 groups:int=0
 pattern:int=0
 gate:int=0
 seed:int=0
 phase:int=0
 rm:int=0
 argument:int=0x87654321
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def fixture(c):
 m=g.fixture(g.Case(seed=c.seed,phase=c.phase));m.update({GROUPS+i:(i*19+c.seed*13+0x33)&255 for i in range(3*24+32)})
 for i in range(6):
  p=RECORDS+SIZE*i
  for j in range(SIZE):m[p+j]=(i*31+j*29+c.seed)&255
  target=(300,-300,0,32767,-32768,100)[i];origin=(50,-50,0,1,-1,100)[i];height=(100,-100,0,32767,-32768,100)[i]
  for at,v,n in [(0x12,height,2),(0x38,g.ENTRY,4),(0x3c,((c.seed&255)<<24)|((1+i*50)<<16)|(target&65535),4),(0x5a,100+i,2),(0x5c,200+i,2),(0x5e,300+i,2),(0x7c,origin,4),(0x80,(0,1,-1,3,-3,0)[i],4)]:g.put(m,p+at,v,n)
  m[p+0x4f]=(0,4,255,128)[(i+c.seed)%4];m[p+0x6e]=int(c.gate==1 and i%2==0);m[p+0x6f]=0x40 if not(c.gate==2 and i%2==0)else 0
 for k in range(3):
  p=GROUPS+k*24;patterns=[[],[0],[1,2],[0,1,2],[3,3,4],[4,1,5],[0,1,2,3],[5,4,3,2,1,0]];entries=patterns[(c.pattern+k)%len(patterns)];g.put(m,p+2,len(entries),2)
  for i,index in enumerate(entries):g.put(m,p+8+2*i,((1 if c.gate==3 and i%2==1 else 2)<<12)|index,2)
  if not entries:g.put(m,p+8,0x2000,2)
  if c.pattern==7 and k==1:g.put(m,p+8,0x1000,2)
 for a,v in [(COUNT,c.count),(SKIP,c.skip),(BASE,RECORDS),(GROUPCOUNT,c.groups),(GROUPBASE,GROUPS)]:g.put(m,a,v,4)
 return m
def child_case(m,p,c):
 packed=g.read(m,p+0x3c);return g.Case(current=g.read(m,p+0x12,2),origin=g.read(m,p+0x7c),target=packed&65535,divisor=packed>>16&255,holdByte=packed>>24,hold=g.read(m,p+0x80),flags=m[p+0x4f],phase=c.phase,seed=c.seed,rm=c.rm)
def reference(initial,c):
 m=dict(initial);calls=[];cached=(0,0,0,0)
 def active(p):return m[p+0x6f]&0x40==0x40 and m[p+0x6e]==0
 def call(p):
  nonlocal m
  calls.append((g.ENTRY,(p,)));cc=child_case(m,p,c)
  with patch.object(g,'POINT',p):m,_=g.reference(m,cc)
 n=g.s32(g.u32(c.count-c.skip))
 for i in range(max(n,0)):
  p=RECORDS+SIZE*i
  if active(p):call(p)
 for k in range(max(g.s32(c.groups),0)):
  base=GROUPS+k*24
  if g.read(m,base+8,2)>>12!=2:continue
  length=g.read(m,base+2,2)
  for i in range(length):
   token=g.read(m,base+8+2*i,2)
   if token>>12!=2:continue
   p=RECORDS+SIZE*(token&4095)
   if active(p):
    if i:
     for at,v,size in zip((0x5a,0x5c,0x5e,0x80),cached,(2,2,2,4)):g.put(m,p+at,v,size)
    call(p)
   if i==0:cached=tuple(g.read(m,p+at,size)for at,size in[(0x5a,2),(0x5c,2),(0x5e,2),(0x80,4)])
 return m,calls
class Connected(g.Machine):
 def __init__(self,words,c,parent):
  self.parent_case=c;code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));FactoryOracle.__init__(self,parent,fixture(c),c,entry=PARENT,arguments=(c.argument,),connected=code);self.fcsr=c.rm;self.before_f=self.f[:];self.initial=dict(self.memory)
 def record_call(self,t):
  assert t==g.ENTRY,hex(t);args=tuple(map(g.u32,self.arguments(1)));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):raise AssertionError('Unconnected child')
def verify(m,c):
 expected,calls=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);home=g.STACK+c.phase
 public=lambda d:{a:v for a,v in d.items()if not home-512<=a<home+256}
 assert public(m.memory)==public(expected),(c,'memory',{hex(a):(v,expected.get(a))for a,v in public(m.memory).items()if expected.get(a)!=v})
 assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f==m.before_f and m.fcsr==c.rm and m.r[2]==g.u32(c.groups)
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();parent=list(struct.unpack_from('>127I',rom,0x141304));asm=(o/'baseline/conker/asm/13D350.s').read_text();body=asm.split('glabel func_15113E54',1)[1].split('endlabel func_15113E54',1)[0];import re
 original=bytes.fromhex(''.join(re.findall(r'/\* [0-9A-F]+ [0-9A-F]+ ([0-9A-F]{8}) \*/',body)));assert original==rom[0x141304:0x141500]and len(original)==508
 start,base,_,_=load_game_data_layout(r/'conker');table=rom[0x22d8a0:0x22d8ac];assert table==g.ENTRY.to_bytes(4,'big')+bytes(8);at=elf_slot_offset(elf,0x80088de0,12);assert elf[at:at+12]==table
 programs=[list(struct.unpack('>103I',g.payload(o/f,'func_151155C0')[0]))for f in ['original-target.o','selected-final/owner-candidate.o']];corpus=[Case(count=count,groups=groups,pattern=pattern,gate=gate,seed=(pattern+gate)&7,phase=(pattern&1)*8,rm=pattern&3)for count,groups,pattern,gate in itertools.product((-1,0,1,2,4),(-1,0,1,2,3),range(8),range(4))];corpus +=[Case(count=0x80000000,skip=0x7fffffff),Case(count=0,skip=1),Case(count=4,skip=3,groups=1,pattern=3)];seen=set();children=0
 for c in corpus:
  models=[]
  for words in programs:
   m=Connected(words,c,parent)
   try:m.run()
   except Exception as error:raise AssertionError((c,hex(m.current_pc),m.r[16:24],str(error)))from error
   verify(m,c);models.append(m)
  a=models[0];assert all(m.memory==a.memory and m.f==a.f and m.fcsr==a.fcsr and(m.hi,m.lo)==(a.hi,a.lo)and m.calls==a.calls for m in models[1:]);seen|={p for p in a.visits if PARENT<=p<PARENT+508};children+=len(a.calls)
 controls=[]
 for name,old,new,c in [('record-active-bit',0x33280040,0x33280020,Case()),('group-index-mask',0x30580fff,0x30580ffe,Case(count=0,groups=1,pattern=2))]:
  bad=list(parent);assert bad.count(old)==1;bad[bad.index(old)]=new;m=Connected(programs[0],c,bad).run();assert m.r[29]==m.before[29]
  try:verify(m,c)
  except AssertionError:controls.append(dict(name=name,supported_complete_parent_execution=True,rejected=True))
  else:raise AssertionError('Ineffective caller control')
 q=dict(original_parent_words=127,parent_frame=64,complete_original_parent_ASM_equal_ROM=True,parent_SHA256=hashlib.sha256(original).hexdigest(),cases_per_stream=len(corpus),streams=2,connected_children_per_stream=children,visited_parent_words=len(seen),unvisited_parent_indices=[i for i in range(127)if PARENT+4*i not in seen],callback_table_selector=28,callback_column=0,table_entry_pinned_ROM_and_frozen_ELF=True,record_stride=160,one_pointer_argument_and_discarded_return=True,empty_direct_and_grouped_paths=True,disabled_inactive_wrong_type_and_wrapping_count_paths=True,first_physical_entry_cache_and_cross_group_retention=True,full_saved_register_and_return_state=True,full_parent_frame_bytes_equal_across_streams=True,HI_LO_and_FPR_FCSR_equal_across_streams=True,all_installed_callbacks_are_actual_target_in_this_scope=True,other_callback_internals_and_initializer_execution_not_qualified=True,parent_C_remains_stub_unmatched_and_uncredited=True,effective_controls=controls,source_installed=p.installed(),matching_credit=0)
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
