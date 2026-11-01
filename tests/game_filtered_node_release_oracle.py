"""Bounded guest state, access prefixes and original helper/wrapper qualification."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from types import SimpleNamespace
r=o=None
F='func_15030310';ENTRY=0x15030310;ACTOR,NODES,ALT,MARK=0x30000,0x50000,0x60000,0x70000;STRIDE=0x80
@dataclass(frozen=True)
class Case:
 key:int=1
 filter:int=7
 skip:int=255
 length:int=4
 pattern:int=0
 mode:int=0
 phase:int=0
def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for base,size in((ACTOR,96),(NODES,6*STRIDE),(ALT,0x5C),(MARK,4),(s['D_800C3EE0'],4)):m.update({base+i:(i*29+90)&255 for i in range(size)})
 m[ACTOR+0x3B]=c.key;put(m,s['D_800C3EE0'],NODES if c.length else 0);put(m,MARK,0)
 for j in range(6):
  p=NODES+j*STRIDE;m[p]=(c.key if c.pattern==0 or(c.pattern==1 and j%2==0)or(c.pattern==2 and j<2)else c.key^1);m[p+6]=(c.filter+(1 if c.pattern==1 and j%3==0 else 0))&255
  put(m,p+0x54,p+STRIDE if j+1<c.length else 0);put(m,p+0x58,p-STRIDE if j else 0)
 return m
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-512<=a<STACK+c.phase}
def release(m,c,p,s):
 nxt,prev=read(m,p+0x54),read(m,p+0x58)
 if read(m,s['D_800C3EE0'])==p:put(m,s['D_800C3EE0'],nxt)
 if prev:put(m,prev+0x54,nxt)
 if nxt:put(m,nxt+0x58,prev)
 m[p]=0xEE;put(m,p+0x54,0);put(m,p+0x58,0);put(m,MARK,(read(m,MARK)+1)&0xFFFFFFFF)
 if c.mode&1:m[ACTOR+0x3B]^=1
 if c.mode&2:put(m,s['D_800C3EE0'],ALT)
def reference(initial,c,s):
 m=dict(initial);calls=[];skip=c.skip&0xFFFFFFFF;done=0
 if m[ACTOR+0x3B]==0:return public(m,c),calls,done
 current=read(m,s['D_800C3EE0']);steps=0
 while current:
  steps+=1;assert steps<=6;next_node=read(m,current+0x54)
  if m[ACTOR+0x3B]==m[current]and c.filter==m[current+6]:
   if skip!=255 and skip!=0:skip=(skip-1)&0xFFFFFFFF
   else:
    calls.append((s['func_15030158'],(current,0)));release(m,c,current,s);done=1
    if skip==0:break
  current=next_node
 return public(m,c),calls,done
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;super().__init__(words,memory,c,entry=entry,s={},arguments=(ACTOR,c.filter&0xFFFFFFFF,c.skip&0xFFFFFFFF),connected=connected)
 def record_call(self,t):
  assert t==self.s['func_15030158'],hex(t);self.calls.append((t,tuple(self.arguments(2))))
 def hook(self,t):
  p,immediate=self.calls[-1][1];assert immediate==0;release(self.memory,self.c,p,self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def programs(layout):
 entry=ENTRY+layout*0x1000000;s=dict(D_800C3EE0=(0x800C3EE0,0x80107FFC,0x80208004)[layout],func_15030158=(0x15030158,0x17200000,0x1827FFFC)[layout]);roots=[]
 for label,obj in(('original',o/('original-'+F+'.o')),('private',o/'selected-final.o')):
  p=o/('guest-%d-%s'%(layout,label));p.with_suffix('.ld').write_text('SECTIONS{.text 0x%X : SUBALIGN(4){*(.text)}}\n'%entry);q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr;roots.append(struct.unpack('>53I',sections(p.with_suffix('.elf'))['.text'][1][:212]))
 assert roots[0]==roots[1];return entry,s,roots
def cases():return [Case(*v)for v in itertools.product((0,1,255),(7,255,-1,256),(0,1,2,255,256,0xFFFFFFFF,0x80000000),(0,1,4),(0,1,2),(0,1,2,3),(0,8))]

def qualify(root,output):
 global r,o
 r,o=Path(root),Path(output)
 done=0;seen=set()
 for layout in range(3):
  entry,s,roots=programs(layout)
  for c in cases():
   initial=fixture(c,s);expected,calls,answer=reference(initial,c,s);models=[]
   for root in roots:
    m=Oracle(root,initial,c,s,entry);m.run();assert public(m.memory,c)==expected,(layout,c,'memory');assert m.calls==calls,(layout,c,m.calls,calls);assert m.r[2]==answer;(models.append(m));seen.update(m.visits);done+=1
   assert (models[0].r,models[0].f,models[0].memory,models[0].trace,models[0].hi,models[0].lo)==(models[1].r,models[1].f,models[1].memory,models[1].trace,models[1].hi,models[1].lo)
  assert set(range(entry,entry+212,4))<=seen
 entry,s,roots=programs(0);pairs=0
 for c in(Case(),Case(key=0),Case(length=0),Case(skip=0,mode=3),Case(skip=256,pattern=1,mode=3)):
  full=Oracle(roots[0],fixture(c,s),c,s,entry);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for root in roots:
    m=Oracle(root,fixture(c,s),c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access cut')
    models.append(m)
   assert(models[0].memory,models[0].trace)==(models[1].memory,models[1].trace);pairs+=1
 # Zero actor key must not read the list-head word.
 c=Case(key=0);initial=fixture(c,s)
 for i in range(4):del initial[s['D_800C3EE0']+i]
 for root in roots:m=Oracle(root,initial,c,s,entry);m.run();assert m.r[2]==0 and not m.calls
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=len(cases())*3,executions=done,independent_GNU_link_layouts=3,retail_words_covered=53,complete_public_memory_and_calls=True,original_private_full_machine_and_access_state_equal=True,cached_next_survives_poisoned_released_node=True,live_actor_key_reload=True,initial_head_captured=True,full_s32_filter=True,unsigned_countdown_and_FF_transition=True,helper_clobbers_saved_state_preserved=True,access_prefix_pairs=pairs,access_prefix_executions=pairs*2,full_fault_register_equivalence_claim=False,zero_key_without_head_mapping_executions=2)
 return q

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
_base_fixture, _base_oracle = fixture, Oracle
def helper_context(root,output):
 global r,o
 r,o=Path(root),Path(output)
 g=SimpleNamespace(r=r,F=F,ENTRY=ENTRY,ACTOR=ACTOR,NODES=NODES,ALT=ALT,MARK=MARK,STRIDE=STRIDE,Case=Case,fixture=_base_fixture,public=public,put=put,read=read,Oracle=_base_oracle,programs=programs)
 r=g.r;rom=(r/'conker/conker.us.bin').read_bytes();entry,s,roots=g.programs(0);HELPER=s['func_15030158'];CLEAN,FREE,DEFER,DETACH,TYPE=0x15031C14,0x10004074,0x100043B4,0x1503F7B8,0x1518CA04
 helper=rom[0x5D608:0x5D7A0];assert len(helper)==408;before=(o/'before-conker_build_conker.us.elf').read_bytes();at=elf_slot_offset(before,HELPER,408);assert before[at:at+408]==helper
 connected=dict(zip(range(HELPER,HELPER+408,4),struct.unpack('>102I',helper)))
 def fixture(c,mask):
  m=g.fixture(c,s)
  for j in range(6):
   p=g.NODES+j*g.STRIDE;m[p+9]=bool(mask&1);m[p+8]=bool(mask&2)
   for off,bit in((0x34,4),(0x44,8),(0x48,16),(0x4C,32),(0x50,64)):g.put(m,p+off,0x90000+j*0x100+off if mask&bit else 0)
   g.put(m,p+0x28,0x90000+j*0x100+0x28);g.put(m,p+0x2C,0x90000+j*0x100+0x2C)
  return m
 def cleanup(m,c):
  if c.mode&1:m[g.ACTOR+0x3B]^=1
  if c.mode&2:g.put(m,s['D_800C3EE0'],g.ALT)
 def poison(m,p):m[p]=0xEE;g.put(m,p+0x54,0);g.put(m,p+0x58,0);g.put(m,g.MARK,(g.read(m,g.MARK)+1)&0xFFFFFFFF)
 def unlink(m,p):
  nxt,prev=g.read(m,p+0x54),g.read(m,p+0x58)
  if g.read(m,s['D_800C3EE0'])==p:g.put(m,s['D_800C3EE0'],nxt)
  if prev:g.put(m,prev+0x54,nxt)
  if nxt:g.put(m,nxt+0x58,prev)
 def reference(initial,c):
  m=dict(initial);calls=[];skip=c.skip;answer=0;current=g.read(m,s['D_800C3EE0'])if m[g.ACTOR+59]else 0
  while current:
   nxt=g.read(m,current+84)
   if m[g.ACTOR+59]==m[current]and c.filter==m[current+6]:
    if skip!=255 and skip!=0:skip=(skip-1)&0xFFFFFFFF
    else:
     p=current;calls.extend(((HELPER,(p,0)),(CLEAN,(p,))));cleanup(m,c)
     if m[p+9]:
      if m[p+8]:calls.extend(((DEFER,(g.read(m,p+40),4)),(DEFER,(g.read(m,p+44),4))))
      if g.read(m,p+72):calls.append((DETACH,(g.read(m,p+72),)))
      calls.append((TYPE,(m[p+1],)))
     for off,fn in((52,DEFER),(68,FREE),(76,DEFER),(80,DEFER)):
      if g.read(m,p+off):calls.append((fn,(g.read(m,p+off),4)if fn==DEFER else(g.read(m,p+off),)))
     unlink(m,p);calls.append((FREE,(p,)));poison(m,p);answer=1
     if skip==0:break
   current=nxt
  return g.public(m,c),calls,answer
 class Oracle(g.Oracle):
  def record_call(self,t):
   if t==HELPER:return super().record_call(t)
   assert t in(CLEAN,FREE,DEFER,DETACH,TYPE),hex(t);self.calls.append((t,tuple(self.arguments(2 if t==DEFER else 1))))
  def hook(self,t):
   p=self.calls[-1][1][0]
   if t==CLEAN:cleanup(self.memory,self.c)
   elif t==FREE and g.NODES<=p<g.NODES+6*g.STRIDE and(p-g.NODES)%g.STRIDE==0:poison(self.memory,p)
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

 return SimpleNamespace(**dict(locals(),r=r))

def helper(root,output):
 h=helper_context(root,output)
 g=h.g;s=h.s;entry=h.entry;roots=h.roots;HELPER=h.HELPER;connected=h.connected;Oracle=h.Oracle;fixture=h.fixture;reference=h.reference
 done=0;seen=set()
 for pattern,mode,skip,mask in itertools.product((0,1,2),(0,1,2,3),(0,255,256),(0,1,2,3,63,255,85,170)):
  c=g.Case(pattern=pattern,mode=mode,skip=skip);initial=fixture(c,mask);expected,calls,answer=reference(initial,c);models=[]
  for root in roots:
   m=Oracle(root,initial,c,s,entry,connected);m.run();assert g.public(m.memory,c)==expected,(c,mask,'memory');assert m.calls==calls,(c,mask,m.calls,calls);assert m.r[2]==answer;models.append(m);seen.update(m.visits);done+=1
  assert(models[0].r,models[0].f,models[0].memory,models[0].trace,models[0].hi,models[0].lo)==(models[1].r,models[1].f,models[1].memory,models[1].trace,models[1].hi,models[1].lo)
 missing=sorted(set(range(HELPER,HELPER+408,4))-seen)
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=done//2,executions=done,original_and_retained_helper_slot_bytes_equal=True,helper_words=102,helper_words_executed=102-len(missing),unexecuted_helper_PCs=[hex(v)for v in missing],all_deferred_cleanup_branches_qualified=True,immediate_zero_only=True,lower_cleanup_and_resource_functions_stubbed=True,original_unlink_head_prev_next_updates=True,cleanup_actor_key_and_head_mutations=True,freed_node_next_poisoned=True,complete_public_memory_calls_and_model_state_equal=True)
 return q

def callers(root,output):
 h=helper_context(root,output)
 g=h.g;r=h.r
 values=struct.unpack('>%dI'%(len(h.rom)//4),h.rom);refs=[i*4 for i,w in enumerate(values)if w==0x0C000000|((g.ENTRY>>2)&0x3FFFFFF)];assert refs==[0x5D7A8]
 census=dict(target=g.F,aligned_ROM_JALs=refs,aligned_ROM_Js=[i*4 for i,w in enumerate(values)if w==0x08000000|((g.ENTRY>>2)&0x3FFFFFF)],aligned_ROM_pointer_literals=[i*4 for i,w in enumerate(values)if w==g.ENTRY],original_wrapper='func_150302F0',original_wrapper_words=8);assert not census['aligned_ROM_Js']and not census['aligned_ROM_pointer_literals'];(o/'caller-census.json').write_text(json.dumps(census,indent=2)+'\n')
 start=0x150302F0;words=struct.unpack_from('>8I',h.rom,0x5D7A0);assert words[2]==0x0C000000|((g.ENTRY>>2)&0x3FFFFFF)and words[3]==0x240600FF
 (o/'original-wrapper.bin').write_bytes(struct.pack('>8I',*words));count=0;seen=set()
 class Oracle(h.Oracle):
  def record_call(self,t):
   if t==g.ENTRY:self.boundaries.append(tuple(self.arguments(3)));return
   return super().record_call(t)
 for key,filter,length,pattern,mode,phase,poison in itertools.product((0,1,255),(7,255,-1,256),(0,4),(0,1),(0,3),(0,8),(0,1,255,0xFFFFFFFF)):
  c=g.Case(key,filter,255,length,pattern,mode,phase);initial=h.fixture(c,255);expected,calls,answer=h.reference(initial,c);models=[]
  for root in h.roots:
   code=dict(h.connected);code.update(zip(range(g.ENTRY,g.ENTRY+212,4),root));m=Oracle(words,initial,c,h.s,start,code);m.r[6]=poison;m.before=m.r[:];m.boundaries=[];m.run()
   assert m.boundaries==[(g.ACTOR,filter&0xFFFFFFFF,255)];assert m.calls==calls and g.public(m.memory,c)==expected and m.r[2]==answer;(models.append(m));seen.update(m.visits);count+=1
  assert(models[0].r,models[0].f,models[0].memory,models[0].trace,models[0].hi,models[0].lo)==(models[1].r,models[1].f,models[1].memory,models[1].trace,models[1].hi,models[1].lo)
 assert set(range(start,start+32,4))<=seen
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,cases=count//2,executions=count,original_wrapper_words=8,all_wrapper_words_covered=True,all_static_direct_call_sites=1,original_wrapper_and_102_word_helper_connected=True,full_width_filter_forwarded=True,incoming_counter_poisons=4,wrapper_forces_FF_sentinel=True,complete_public_memory_calls_and_model_state_equal=True,wrapper_C_void_result_not_claimed=True)
 return q
