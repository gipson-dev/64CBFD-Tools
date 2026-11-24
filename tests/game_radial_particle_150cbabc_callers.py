"""All four original registry parents plus the matched factory/copy chain."""
from dataclasses import replace
import hashlib,itertools,json,re,struct
from tools.experiments import game_radial_particle_150cbabc_match as p
from tools.tests import game_radial_particle_150cbabc_guest as g
PARENTS={0x1514c2f0:(96,160,True),0x1514c470:(130,168,False),0x1514c678:(120,160,True),0x1514c858:(138,216,False)}
TABLE,SINE,ALLOCATE,FACTORY=0x8008aa00,0x151423d8,0x15167a68,0x15130280
def original(entry,count,rom):return list(struct.unpack_from('>'+str(count)+'I',rom,entry-0x15000000+0x2d4b0))
class Connected(g.Oracle):
 def __init__(self,words,c,parent,count,step,rom,raw=False):
  self.parent=parent;self.initial_case=c;self.parent_randoms=0;self.forwarded=[];self.child_starts=[];memory=g.fixture(c)
  if raw:
   child=replace(c,phase=c.phase-PARENTS[parent][1]);old=dict(memory)
   for source,n in((g.packet(child),112),(g.damping(child),4),(g.rngslot(child),4)):
    for i in range(n):memory[source+4+i]=old[source+i]
  for i in range(28):g.put(memory,TABLE+4*i,g.ENTRY if i==14 else 0)
  x,y,z=map(g.floating,c.coords)
  if parent in(0x1514c2f0,0x1514c678):arguments=(0,0,g.bits(z),g.bits(2.),250,step,count,14,9,g.bits(.75),0x81234567,c.slot)
  elif parent==0x1514c470:arguments=(0,0,g.bits(z),g.bits(x+9),g.bits(y-7),g.bits(z+5),g.bits(float(count)),14,9,g.bits(.75),0x81234567,c.slot)
  else:arguments=(0,0,g.bits(z),g.bits(2.),63,250,step,count,14,9,g.bits(.75),0x81234567,c.slot)
  code=dict(zip(range(g.ENTRY,g.ENTRY+548,4),words));g.Oracle.__init__(self,original(parent,PARENTS[parent][0],rom),c,entry=parent,memory=memory,arguments=arguments,connected=code,raw=raw);self.f[12]=c.coords[0];self.f[14]=c.coords[1];self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(15)));a,b,x,y,z,ox,oy,oz,angle,start,radius,style,extra,context,slot=args;self.forwarded.append(args);self.child_starts.append((self.r[29],self.fcsr));self.c=replace(self.initial_case,phase=self.r[29]-g.STACK,coords=(x,y,z),angle=angle,slot=slot,unused=(a,b,ox,oy,oz,start,radius,style,extra,context));self.counts={};self.calls.append((t,args));self.events.append(('CALL',t,args));return
  if t==SINE or(t==g.RNG and not g.ENTRY<=self.current_pc<g.ENTRY+548):
   a=tuple(map(g.u32,self.arguments(1 if t==SINE else 0)));self.calls.append((t,a));self.events.append(('CALL',t,a));return
  super().record_call(t)
 def hook(self,t):
  if t==SINE or(t==g.RNG and not g.ENTRY<=self.current_pc<g.ENTRY+548):
   g.put(self.memory,g.MARK,g.read(self.memory,g.MARK)+1)
   if t==SINE:value=g.bits(((self.calls[-1][1][0]&255)-128)/128.)
   else:self.parent_randoms+=1;value=(self.parent_randoms*17+self.initial_case.seed*7)&0xffffffff
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010
   if t==SINE:self.f[0]=value
   else:self.r[2]=value
   return
  super().hook(t)
def parents(rom,before):
 programs=g.streams();raw=g.bound_blob(*g.payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),g.symbols());summary={};cases=children=controls=0;visits={p:set()for p in PARENTS};control_rows=[]
 for parent,(n,frame,exact)in PARENTS.items():
  body=struct.pack('>'+str(n)+'I',*original(parent,n,rom));at=p.elf_slot_offset(before,parent,len(body));assert(before[at:at+len(body)]==body)==exact;summary[hex(parent)]=dict(words=n,frame=frame,production_byte_exact=exact,retail_execution_only=not exact)
 for parent,seed,slot,mode,count,step,outcome in itertools.product(PARENTS,range(2),(0,255),(0,7),(0,1,2),(7,-128),(0,1)):
  c=g.Case(seed=seed,phase=8*(seed&1),coords=tuple(map(g.bits,(1.25+seed,-2.5-seed,3.75+seed))),slot=slot,mode=mode,fcsr=(mode&1)*2+seed,outcome=outcome);baseline=None
  for label,body in enumerate(programs):
   m=Connected(body,c,parent,count,step,rom).run();assert m.r[29]==g.STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   for i,args in enumerate(m.forwarded):assert args[0]=={0x1514c2f0:1,0x1514c470:0,0x1514c678:2,0x1514c858:3}[parent]and args[1]==i and args[11]==9 and args[14]==slot and 0<=args[8]<=255,(hex(parent),args)
   state=(m.calls,m.forwarded,m.observations,g.public(m.memory,c),m.r,m.f,m.fcsr,m.hi,m.lo);visits[parent]|={pc for pc in m.visits if parent<=pc<parent+4*PARENTS[parent][0]}
   if baseline is None:baseline=state;children+=len(m.forwarded)
   else:assert state==baseline,(hex(parent),'normalized caller state')
  raw_model=Connected(raw,c,parent,count,step,rom,raw=True).run()
  if m.forwarded:assert g.canonical(raw_model)==g.canonical(m),(hex(parent),'raw stack-map caller')
  else:assert(g.public(raw_model.memory,c),raw_model.calls,raw_model.r,raw_model.f,raw_model.fcsr)==(g.public(m.memory,c),m.calls,m.r,m.f,m.fcsr)
  assert raw_model.forwarded==m.forwarded
  if count==2 and seed==0 and slot==255 and mode==7 and outcome==1:
   bad=list(programs[0]);assert bad[-5]==0x24020001;bad[-5]=0x24020000;wrong=Connected(bad,c,parent,count,step,rom).run();assert len(wrong.forwarded)<len(m.forwarded),(hex(parent),'ineffective return control');controls+=1;control_rows.append(dict(parent=hex(parent),step=step,good_calls=len(m.forwarded),bad_calls=len(wrong.forwarded)))
  cases+=1
 return dict(retail_parent_cases=cases,parent_programs=4,raw_stack_map_parent_cases=cases,connected_child_calls_per_stream=children,parents=summary,visited_parent_words={hex(a):len(v)for a,v in visits.items()},all15_callback_arguments_observed=True,return_zero_controls=control_rows,effective_return_controls=controls,whole_original_parents_under_opaque_providers=True)
def factory(rom,before):
 code={};helpers=[]
 for name,entry,off,n in [('func_15130374',g.SUBMIT,0x15d824,18),('func_15130280',FACTORY,0x15d730,61),('memcpy',g.COPY,0x22ec0,11)]:
  raw=rom[off:off+4*n];at=p.elf_slot_offset(before,entry,len(raw));assert before[at:at+len(raw)]==raw;ws=struct.unpack('>'+str(n)+'I',raw);code.update(zip(range(entry,entry+4*n,4),ws));helpers.append(dict(function=name,words=n,sha256=hashlib.sha256(raw).hexdigest()))
 class Chain(g.Oracle):
  def __init__(self,body,c):self.chain_calls=[];super().__init__(body,c,connected=code)
  def record_call(self,t):
   if t==FACTORY:self.chain_calls.append((t,tuple(map(g.u32,self.arguments(6)))));return
   if t==ALLOCATE:
    self.chain_calls.append((t,tuple(map(g.u32,self.arguments(6)))));return
   super().record_call(t)
  def hook(self,t):
   if t!=ALLOCATE:return super().hook(t)
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
   self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=g.OUTPUT if self.c.outcome else 0
 cases=0;visited={a:set()for a in(g.SUBMIT,FACTORY,g.COPY)}
 for mode,outcome,phase in itertools.product((0,3),(0,1),(0,8)):
  c=g.Case(mode=mode,outcome=outcome,phase=phase);baseline=None
  for body in g.streams():
   m=Chain(body,c).run();assert m.r[2]==1 and m.r[29]==g.STACK+phase
   assert m.chain_calls==[(FACTORY,(g.packet(c),1,0,4,c.slot&255,1)),(ALLOCATE,(0x52,1,0xac,1,c.slot&255,1))]
   if outcome:assert g.data(m.memory,g.OUTPUT+0x10,112)==g.data(m.memory,g.packet(c),112)and g.data(m.memory,g.OUTPUT+0xa8,4)==g.data(m.memory,g.damping(c),4)
   state=(m.memory,m.calls,m.chain_calls,m.r,m.f,m.fcsr,m.hi,m.lo)
   if baseline is None:baseline=state
   else:assert state==baseline
   for entry,_,off,n in [(g.SUBMIT,'',0,18),(FACTORY,'',0,61),(g.COPY,'',0,11)]:visited[entry]|={pc for pc in m.visits if entry<=pc<entry+4*n}
  cases+=1
 excluded=set(range(0x151302b4,0x151302cc,4))|set(range(0x15130328,0x15130360,4))
 assert visited[g.SUBMIT]==set(range(g.SUBMIT,g.SUBMIT+72,4))and visited[g.COPY]==set(range(g.COPY,g.COPY+44,4))and visited[FACTORY]==set(range(FACTORY,FACTORY+244,4))-excluded
 return dict(connected_factory_cases=cases,original_helpers=helpers,helper_words_executed={hex(a):len(v)for a,v in visited.items()},all70_target_reachable_helper_words_executed=True,other_factory_modes_and_optional_state_path_excluded=True,allocation_opaque=True,descriptor_copy_bytes=112,extra_payload_bytes=4,helper_matching_credit=0)
def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0c000000|((g.ENTRY>>2)&0x3ffffff);jump=0x08000000|((g.ENTRY>>2)&0x3ffffff);sites=[];pointers=[]
 for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
  if word in(jal,jump):sites.append(i*4)
  if word==g.ENTRY:pointers.append(i*4)
 assert not sites and pointers==[0x22f4f8],(sites,pointers)
 before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();assert tuple(int.from_bytes(before[p.elf_slot_offset(before,a,4):p.elf_slot_offset(before,a,4)+4],'big')for a in g.CONSTANTS)==g.VALUES;at=p.elf_slot_offset(before,0x8008aa38,4);assert before[at:at+4]==g.ENTRY.to_bytes(4,'big')
 asm=(p.OUT/'baseline/conker/asm/176A00.s').read_text();refs=[m[1]for m in re.finditer(r'glabel (func_[0-9A-F]+)\n(.*?)endlabel \1',asm,re.S)if'D_8008AA00'in m[2]];assert refs==['func_1514C2F0','func_1514C470','func_1514C678','func_1514C858']
 q=dict(pristine_ROM_sha256=hashlib.sha256(rom).hexdigest(),entire_pristine_aligned_ROM_scanned=True,entry_JALs=sites,entry_pointers=[hex(v)for v in pointers],qualified_entry_pointer='0x8008aa38',additional_static_entry_references=0,table_referencing_parents=refs,**parents(rom,before),**factory(rom,before),source_installed=p.installed(),matching_credit=0);(p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
