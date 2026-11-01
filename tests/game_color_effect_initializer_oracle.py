"""Bounded public behavior, original helpers/callers and explicit unmatched access gap."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
r=o=None;F='func_15187EC0';ENTRY=0x15187EC0
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:(n&0x7FFFFFFF)-(n&0x80000000)
@dataclass(frozen=True)
class Case:
 count:int=0
 mode:int=1
 rate:int=0x3DCCCCCD
 colors:tuple=(0xABCD0080,0x765400FF,0x8765007F,0x12340001,0xFEFF0000,0x987600FF)
 phase:int=0
 seed:int=0

def cases():
 rows=[]
 for count,rate,phase,seed in itertools.product((-0x80000000,-0x40000000,-2,-1,0,1,2,3,4,5,6,0x7FFFFFFF),(0,0x80000000,0x3DCCCCCD,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345),(0,8),(0,1)):
  rows.append(Case(count,(0,1,0xFFFFFFFF,0x80000000)[(seed+count)%4],rate,phase=phase,seed=seed))
 for field,byte in itertools.product(range(6),range(256)):
  c=list(Case().colors);c[field]=0xA5A50000|byte;rows.append(Case(count=field%5,colors=tuple(c),phase=8*(field%2),seed=byte%2))
 for count,colors in itertools.product((-0x3FFFFFFB,-0x7FFFFFFB),((0xFF,0xFF,0xFF,0xFF,0,1),(0,0,0,0,1,255))):rows.append(Case(count=count,colors=colors))
 return rows

def fixture(c,s):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)}
 m.update({s['D_800DF700']+i:(i*29+c.seed*11+90)&255 for i in range(-128,256)})
 p=u32(s['D_800DF700']+c.count*36)
 if c.count<5:m.update({u32(p+i):(i*31+c.seed*7+0x59)&255 for i in range(-8,44)})
 put(m,s['D_800DF7B4'],u32(c.count))
 for i,v in enumerate(c.colors[2:]):put(m,home+16+4*i,v)
 return m

def public(m,c):
 home=STACK+c.phase;return{a:b for a,b in m.items()if not home-512<=a<home+512}

def reference(initial,c,s):
 m=dict(initial)
 if c.count>=5:return public(m,c),[],0xFFFFFFFF
 p=u32(s['D_800DF700']+c.count*36)
 for off,v in [(0,c.colors[0]),(1,c.colors[1]),(2,c.colors[2]),(3,c.colors[3]),(4,c.colors[4]),(5,c.colors[5]),(6,c.colors[0]),(7,c.colors[1]),(8,c.colors[2])]:m[p+off]=v&255
 put(m,p+16,c.mode);put(m,p+20,c.rate)
 for i in range(12):m[p+24+i]=0
 prior=read(m,s['D_800DF7B4']);put(m,s['D_800DF7B4'],u32(prior+1));return public(m,c),[(s['bzero'],(p+24,12))],prior

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,s,entry,connected):
  self.c,self.s=c,s
  super().__init__(words,initial,c,entry=entry,s={},connected=connected,arguments=(u32(c.mode),c.rate,c.colors[0],c.colors[1]))
 def record_call(self,t):
  assert t==self.s['bzero'],hex(t);self.calls.append((t,tuple(self.arguments(2))))
 def hook(self,t):
  assert t==self.s['bzero'];p,n=self.calls[-1][1];assert n==12
  for i in range(n):self.memory[p+i]=0
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011


def qualify(root,output):
 global r,o
 r,o=Path(root),Path(output)
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes();helper=rom[0x226F0:0x22790];at=elf_slot_offset(before,0x100226F0,160);assert before[at:at+160]==helper
 body=(r/'conker/asm/1B5370.s').read_text().split('glabel '+F+'\n')[1].split('endlabel '+F)[0];p=o/('original-'+F)
 p.with_suffix('.s').write_text('.include "macro.inc"\n.text\n.set noreorder\n.globl '+F+'\n'+F+':\n.type '+F+', @function\n'+body+'\n.size '+F+', . - '+F+'\n');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 layouts=[];done=0;seen=set();roots_per_layout=[]
 for layout,pool in enumerate((0x800DF700,0x80207FFC,0x80308004)):
  entry=ENTRY+layout*0x1000000;s=dict(D_800DF700=pool,D_800DF7B4=pool+180,bzero=(0x100226F0,0x17200000,0x1827FFFC)[layout]);roots=[]
  for label,obj in [('original',p.with_suffix('.o')),('private36',o/'screen2-10.o'),('private25',o/'screen17-1.o')]:
   dest=o/('guest-%d-%s'%(layout,label));dest.with_suffix('.ld').write_text('SECTIONS{.text 0x%X : SUBALIGN(4){*(.text)}}\n'%entry)
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(dest.with_suffix('.ld')),'-e',F,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(dest.with_suffix('.elf')),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   roots.append(struct.unpack('>52I',sections(dest.with_suffix('.elf'))['.text'][1][:208]))
  roots_per_layout.append((entry,s,roots));helper_code=dict(zip(range(s['bzero'],s['bzero']+160,4),struct.unpack('>40I',helper)))
  for c,connected in itertools.product(cases(),(False,True)):
   initial=fixture(c,s);expected,calls,answer=reference(initial,c,s)
   for index,root in enumerate(roots):
    m=Oracle(root,initial,c,s,entry,helper_code if connected else None);m.run();assert public(m.memory,c)==expected,(layout,c,connected,index,'memory');assert m.calls==calls,(c,m.calls,calls);assert m.r[2]==answer,(c,m.r[2],answer)
    assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24];done+=1
    if index==0:seen.update(m.visits)
  layouts.append(dict(layout=layout,cases=len(cases())*2,executions=len(cases())*6))
 assert set(range(ENTRY,ENTRY+208,4))<=seen
 # Sparse full-pool route: candidate early third-byte read is a known access gap.
 entry,s,roots=roots_per_layout[0];c=Case(count=5);initial=fixture(c,s);del initial[STACK+19];sparse=[]
 for index,root in enumerate(roots):
  m=Oracle(root,initial,c,s,entry,None)
  try:m.run();sparse.append('returns-minus-one')
  except (AssertionError,KeyError):
   assert index>0 and m.dispatched_word==0x93A4002B,(index,hex(m.dispatched_word));sparse.append('extra-third-byte-read')
 assert sparse==['returns-minus-one','extra-third-byte-read','extra-third-byte-read'],sparse
 q=dict(success=True,sparse_full_pool_access_gap=sparse,private_only=True,installed=False,matching_credit=0,cases=len(cases())*2*3,executions=done,layouts=layouts,original_words_covered=52,actual_bzero_slot_equal=True,original_40_word_bzero_connected=True,full_byte_arguments_and_poisons=True,mode_word_and_raw_float_bits=True,signed_negative_mapped_guest_counts=True,native_negative_index_claim=False,public_memory_result_call_order_equal=True,full_machine_equality_claim=False,access_order_equality_claim=False,private_codegen_differences=[36,25],counter_alias_wrap_cases=True)
 return q

from types import SimpleNamespace
RootOracle=Oracle
def callers(root,output):
 r,o=Path(root),Path(output)
 g=SimpleNamespace(F=F,ENTRY=ENTRY,sections=sections,STACK=STACK,Case=Case,fixture=fixture,reference=reference,Oracle=RootOracle,public=public)
 rom=(r/'conker/conker.us.bin').read_bytes();values=struct.unpack('>%dI'%(len(rom)//4),rom)
 refs=[i*4 for i,w in enumerate(values)if w==0x0C000000|((g.ENTRY>>2)&0x3FFFFFF)];assert refs==[0x370CC,0x37178,0x37478],refs
 census=dict(target=g.F,aligned_ROM_JALs=refs,aligned_ROM_Js=[i*4 for i,w in enumerate(values)if w==0x08000000|((g.ENTRY>>2)&0x3FFFFFF)],aligned_ROM_pointer_literals=[i*4 for i,w in enumerate(values)if w==g.ENTRY]);assert not census['aligned_ROM_Js']and not census['aligned_ROM_pointer_literals'];(o/'caller-census.json').write_text(json.dumps(census,indent=2)+'\n')
 FACTORY,COPY,ZERO,OUT=0x1516387C,0x10022EC0,0x100226F0,0x50000
 s=dict(D_800DF700=0x800DF700,D_800DF7B4=0x800DF7B4,bzero=ZERO)
 helpers={}
 for va,off,n in[(ZERO,0x226F0,40),(COPY,0x22EC0,11)]:helpers.update(zip(range(va,va+4*n,4),struct.unpack_from('>%dI'%n,rom,off)))
 roots=[]
 for name in ['original','private25']:roots.append(struct.unpack('>52I',g.sections(o/('guest-0-'+name+'.elf'))['.text'][1][:208]))
 parents=[(0x15009BD0,43,0,0,(0,0,0,220,220,255),0x42B40000),(0x15009C7C,43,0,0,(0,0,0,220,220,255),0x42480000),(0x15009F74,45,1,0x3DCCCCCD,(100,100,100,255,100,100),0x42700000)]
 class Oracle(g.Oracle):
  def record_call(self,t):
   if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(8))));return
   if t in(FACTORY,COPY):self.calls.append((t,tuple(self.arguments(8 if t==FACTORY else 3))));return
   return super().record_call(t)
  def hook(self,t):
   assert t==FACTORY;args=self.calls[-1][1];assert args==(self.owner,2,16,300,0,12,255,1),args
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=OUT if self.outcome else 0
 count=0;coverage={}
 for entry,n,mode,rate,colors,height in parents:
  words=struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0);seen=set()
  for current,phase,outcome,owner in itertools.product((-0x80000000,-1,0,4,5),(0,8),(0,1),(0,0x60000)):
   c=g.Case(count=current,mode=mode,rate=rate,colors=colors,phase=phase);initial=g.fixture(c,s);initial.update({OUT+i:(i*13+0xA5)&255 for i in range(64)})
   expected,calls,answer=g.reference(initial,c,s);home=g.STACK+phase;payload=home-16
   expected_calls=[(g.ENTRY,(mode,rate,*colors)),*calls,(FACTORY,(owner,2,16,300,0,12,255,1))]
   if outcome:
    expected_calls.append((COPY,(OUT+24,payload,12)))
    packet=struct.pack('>III',answer,0,height)
    for i,b in enumerate(packet):expected[OUT+24+i]=b
   for root in roots:
    code=dict(helpers);code.update(zip(range(g.ENTRY,g.ENTRY+208,4),root));m=Oracle(words,initial,c,s,entry,code);m.owner=owner;m.outcome=outcome;m.r[4]=owner;m.r[5]=0xA5A5A5A5;m.before=m.r[:];m.run()
    assert m.calls==expected_calls,(entry,c,m.calls,expected_calls);assert g.public(m.memory,c)==expected,(entry,c,'memory');assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24];seen.update(m.visits);count+=1
  assert set(range(entry,entry+4*n,4))<=seen;coverage[hex(entry)]=n
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=count//2,executions=count,all_three_static_callers=True,complete_parent_word_coverage=coverage,real_eight_slot_arguments_and_float_word=True,original_40_word_bzero_and_11_word_memcpy_connected=True,factory_outcomes_stubbed=True,factory_null_does_not_undo_pool_append=True,full_pool_failure_index_propagation=True,parent_void_return_not_claimed=True,public_memory_and_call_order_equal=True,full_machine_state_equality_claim=False)
 return q
