"""Complete 7762-record guest scans with opaque allocator/DMA/free providers."""
from pathlib import Path
from dataclasses import dataclass
import json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,ALLOC,DMA,FREE,N=0x15003570,0x10003C40,0x10004514,0x10004074,7762
BUFFER=0x30000
u32=lambda v:v&0xFFFFFFFF
class CallBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
 pattern:int=0
 mutation:int=0
 alias:int=0
 phase:int=0
 fail:int=0
def buffer(c,s):return 0 if c.fail else BUFFER if c.alias==0 else s['D_80091D20']+0x20 if c.alias==1 else s['D_800B87A0']+0x80
def fixture(c,s):
 m={STACK+c.phase+i:(i*17+165)&255 for i in range(-512,512)}
 for base,size in ((BUFFER-16,64),(s['D_80091D20']-16,N*2+32),(s['D_800B87A0']-16,N*2+32)):m.update({base+i:(i*29+90)&255 for i in range(size)})
 for i in range(N):put(m,s['D_80091D20']+2*i,(0,1,2,0x8000,0xFFFF)[(i+c.pattern)%5],2);put(m,s['D_800B87A0']+2*i,0x7777,2)
 return m
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-512<=p<STACK+c.phase+512}
def dma_effect(m,c,s,i,destination,skip):
 value=u32(0xA5000000^(i*0x010203)^(c.pattern*0x778899))
 for j in range(16):m[destination+j]=0xCC
 put(m,destination+skip,value)
 if c.mutation==1:put(m,s['D_80091D20']+2*i,(i*17)&65535,2)
 if c.mutation==2 and i+1<N:put(m,s['D_80091D20']+2*(i+1),(i*29+0x8001)&65535,2)
 if c.mutation==3:put(m,s['D_800B87A0']+2*i,0x1234,2)
def reference(initial,c,s):
 m=dict(initial);cursor=s['D_1A37E0'];b=buffer(c,s);calls=[(ALLOC,(16,1,2,0))]
 for i in range(N):
  skip=cursor&1;cursor=u32(cursor-skip);calls.append((DMA,(cursor,b,16,1)))
  if c.fail:return public(m,c),calls
  dma_effect(m,c,s,i,b,skip)
  value=0
  for j in range(4):value=(value<<8)|m[b+skip+j]
  length=read(m,s['D_80091D20']+2*i,2)
  put(m,s['D_800B87A0']+2*i,value,2);cursor=u32(cursor+length+skip)
 calls.append((FREE,(b,)));return public(m,c),calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s,self.dmas=c,s,0;self.cursor=s['D_1A37E0']
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(0,))
 def record_call(self,t):
  counts={ALLOC:4,DMA:4,FREE:1,ENTRY:0};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a))
  if t==DMA and self.c.fail:raise CallBoundary
 def hook(self,t):
  if t==ALLOC:value=buffer(self.c,self.s)
  elif t==DMA:
   a=self.calls[-1][1];assert a[1:]==(buffer(self.c,self.s),16,1)and not(a[0]&1)
   # The synthetic ROM stream follows an independent logical cursor; it
   # never reads a compiler-selected register or the target's skip local.
   skip=self.cursor&1;assert a[0]==u32(self.cursor-skip);dma_effect(self.memory,self.c,self.s,self.dmas,a[1],skip);self.cursor=u32(self.cursor+read(self.memory,self.s['D_80091D20']+2*self.dmas,2));self.dmas+=1;value=u32(-123)
  else:assert t==FREE;value=0xDEADBEEF
  for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
 def run(self):
  # This narrow integer control loop uses the existing instruction executor.
  # A fixed 600k budget covers every record; the shared 50k limit is untouched.
  pc=self.entry
  for _ in range(600000):
   self.visits.add(pc);w=self.code[pc];op,rs,rt=w>>26,w>>21&31,w>>16&31
   if op in(4,5):
    take=(self.r[rs]==self.r[rt])==(op==4);self.visits.add(pc+4);self.execute(self.code[pc+4]);offset=((w&65535)^32768)-32768;pc=pc+4+offset*4 if take else pc+8
   elif op==3:
    t=((pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2);self.r[31]=pc+8;self.visits.add(pc+4);self.execute(self.code[pc+4]);self.record_call(t)
    if t in self.code:pc=t
    else:self.hook(t);pc+=8
   elif op==0 and w&63==8:
    t=self.r[rs];self.visits.add(pc+4);self.execute(self.code[pc+4])
    if t==0xDEAD0000:
     for reg in(*range(16,24),28,29,30,31):assert self.r[reg]==self.before[reg],('saved register',reg)
     assert self.f[20:]==self.saved_f;return self
    assert t in self.code;pc=t
   else:self.execute(w);pc+=4
  raise AssertionError('Complete metadata scan exceeded 600k bounded integer steps')
def state(m):return m.r,m.f,m.memory,m.trace,m.hi,m.lo,m.calls
def programs(output,layout):
 from tools.pad_generated_object import emit_padded_assembly
 from tools.experiments.game_four_head_lookup_match import payload
 o=Path(output);root=o.parents[2];q=json.loads((o/'private-layout-v10.json').read_text())['group_link_layouts'][layout];entry,s=q['entry'],q['symbols'];roots=[]
 raw=o/'public-fresh-selected.o'if(o/'public-fresh-selected.o').exists()else o/'selected-final.o'
 normalized=o/'public-normalized.o';assembly=normalized.with_suffix('.s');assembly.write_text(emit_padded_assembly(raw,o/'isolated-retail.s',filename='game_305D0',word_patches_path=o/'proposed-guards.csv'))
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(normalized),str(assembly)],capture_output=True,check=True)
 assert payload(normalized,'func_15003570')==payload(o/'original-func_15003570.o','func_15003570')
 for name,obj in(('original',o/'original-func_15003570.o'),('raw',raw),('normalized',normalized)):
  p=o/('public-layout-%d-%s'%(layout,name));p.with_suffix('.ld').write_text('SECTIONS{.text 0x%X:SUBALIGN(4){*(.text)}}\n'%entry)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_15003570',*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
  image=p.with_suffix('.elf').read_bytes();at=elf_slot_offset(image,entry,248);roots.append(struct.unpack_from('>62I',image,at))
  frozen=(o/('layout-%d-%s.elf'%(layout,name))).read_bytes();old_at=elf_slot_offset(frozen,entry,248);assert image[at:at+248]==frozen[old_at:old_at+248]
 assert roots[0]==roots[2];return entry,s,roots
def qualify(root,output):
 o=Path(output);count=cases=0;seen=set();specs=[(0,Case()),(0,Case(pattern=1,mutation=1,phase=8)),(0,Case(pattern=2,mutation=2,alias=1)),(0,Case(pattern=3,mutation=3,alias=2,phase=8)),(1,Case(pattern=4,mutation=1)),(2,Case(pattern=2,mutation=2))]
 for layout,c in specs:
  entry,s,roots=programs(o,layout);initial=fixture(c,s);expected,calls=reference(initial,c,s);models=[]
  for name,words in zip(('original','raw','normalized'),roots):
   m=Oracle(words,initial,c,s,entry);m.run();assert public(m.memory,c)==expected and m.calls==calls,(layout,c,name);assert m.dmas==N
   models.append(m);seen.update(pc-layout*0x1000000 for pc in m.visits);count+=1
  assert state(models[0])==state(models[2]);assert state(models[0])==state(models[1]),('Raw final state',layout,c);cases+=1
  print('Full metadata scan',layout,c,'passed all three roots',flush=True)
 assert set(range(ENTRY,ENTRY+248,4))<=seen
 # First-iteration access cuts avoid reexecuting the complete scan per cut.
 entry,s,roots=programs(o,0);prefixes=0
 for cut in range(38):
  pair=[]
  for words in(roots[0],roots[2]):
   m=Oracle(words,fixture(Case(),s),Case(),s,entry);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError('Access cut did not fire')
   pair.append(m)
  assert state(pair[0])==state(pair[1]);prefixes+=1
 c=Case(fail=1);initial=fixture(c,s);expected,calls=reference(initial,c,s);null_count=0
 for words in roots:
  m=Oracle(words,initial,c,s,entry)
  try:m.run()
  except CallBoundary:pass
  else:raise AssertionError('Null allocation first-DMA prefix not reached')
  assert public(m.memory,c)==expected and m.calls==calls;null_count+=1
 return dict(success=True,private_only=True,matching_credit=0,full_scan_cases=cases,full_scan_executions=count,records_per_scan=N,covered_words=62,normalized_complete_state_and_trace_equal=True,raw_final_state_equal=True,buffer_aliases_length_and_extent=True,live_DMA_mutations=True,independent_group_layouts=3,access_prefix_pairs=prefixes,null_allocation_prefix_executions=null_count,no_graceful_null_failure_claim=True,allocator_DMA_free_implementations_stubbed=True)
def callers(root,output):
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 root,o=Path(root),Path(output);rom=(root/'conker/conker.us.bin').read_bytes();found=[];jumps=[];pointers=[]
 for at in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,at)[0]
  if w>>26 in(2,3)and((w&0x3FFFFFF)<<2)==(ENTRY&0xFFFFFFF):(found if w>>26==3 else jumps).append(at)
  if w==ENTRY:pointers.append(at)
 assert found==[0x34D58]and not jumps and not pointers
 window,end,next_helper,flag=0x150078A8,0x150078BC,0x10008180,0x800BEAAB
 words=struct.unpack_from('>5I',rom,0x34D58);assert words==(0x0D400D5C,0,0x3C01800C,0x0C002060,0xA020EAAB)
 original=rom[0x2D4B0+0x7830:0x2D4B0+0x7830+496];before=(o/'before-conker_build_conker.us.elf').read_bytes();at=elf_slot_offset(before,0x15007830,496);assert before[at:at+496]==original
 class Caller(Oracle):
  def record_call(self,t):
   if t==next_helper:self.calls.append((t,()));return
   return super().record_call(t)
  def hook(self,t):
   if t==next_helper:super().hook(FREE);self.r[2]=0x87654321;return
   return super().hook(t)
 entry,s,roots=programs(o,0);count=0;seen=set()
 for c in(Case(),Case(pattern=3,mutation=1,alias=2,phase=8)):
  initial=fixture(c,s);initial[flag]=0xA5;expected,calls=reference(initial,c,s);expected[flag]=0;calls=[(ENTRY,()),*calls,(next_helper,())];models=[]
  for words_root in roots:
   code=dict(zip(range(ENTRY,ENTRY+248,4),words_root));code[end]=0;m=Caller(words,initial,c,s,window,code);m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Startup continuation endpoint not reached')
   assert public(m.memory,c)==expected and m.calls==calls;assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24];seen.update(m.visits);models.append(m);count+=1
  assert state(models[0])==state(models[1])==state(models[2])
 assert set(range(window,window+20,4))<=seen
 return dict(success=True,cases=2,executions=count,aligned_JAL_ROM=found,window_words=5,all_window_words_executed=True,retained_startup_124_words_equal_original=True,full_startup_execution_claim=False,root_return_not_consumed_in_window=True,real_following_flag_store=True,next_helper_stubbed=True)
