"""Original registry parents, factory wrapper and descriptor-copy primitive."""
from dataclasses import replace
import hashlib,itertools,json,re,struct
from tools.experiments import game_tuned_extended_150b3188_match as p
from tools.tests import game_tuned_extended_150b3188_guest as g
PARENTS={0x1514c2f0:(96,160,True),0x1514c470:(130,168,False),0x1514c678:(120,160,True),0x1514c858:(138,216,False)}
TABLE,SINE,RNG=0x8008aa00,0x151423d8,0x150ada20
def original(entry,count,rom):return list(struct.unpack_from('>'+str(count)+'I',rom,entry-0x15000000+0x2d4b0))
class Connected(g.Oracle):
 def __init__(self,words,c,parent,count,step,rom,raw=False):
  self.parent=parent;self.initial_case=c;self.parent_randoms=0;self.forwarded=[];self.child_starts=[];memory=g.fixture(c)
  for i in range(28):g.put(memory,TABLE+4*i,g.ENTRY if i==10 else 0)
  x,y,z=map(g.floating,c.coords)
  if parent in(0x1514c2f0,0x1514c678):arguments=(0,0,g.bits(z),g.bits(2.),250,step,count,10,9,g.bits(.75),0x60000,c.slot)
  elif parent==0x1514c470:arguments=(0,0,g.bits(z),g.bits(x+9),g.bits(y-7),g.bits(z+5),g.bits(float(count)),10,9,g.bits(.75),0x60000,c.slot)
  else:arguments=(0,0,g.bits(z),g.bits(2.),63,250,step,count,10,9,g.bits(.75),0x60000,c.slot)
  code=dict(zip(range(g.ENTRY,g.ENTRY+1316,4),words));g.Oracle.__init__(self,original(parent,PARENTS[parent][0],rom),c,entry=parent,memory=memory,arguments=arguments,connected=code,raw=raw);self.f[12]=c.coords[0];self.f[14]=c.coords[1];self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(15)));a,b,x,y,z,ox,oy,oz,angle,start,radius,style,extra,context,slot=args;self.forwarded.append(args);self.child_starts.append((self.r[29],self.fcsr));self.c=replace(self.initial_case,phase=self.r[29]-g.STACK,coords=(x,y,z),angle=angle,start=start,radius=radius,extra=extra,slot=slot,unused=(a,b,ox,oy,oz,style,context));self.counts={};self.calls.append((t,args));self.events.append(('CALL',t,args));return
  if t in(SINE,RNG)and not g.ENTRY<=self.current_pc<g.ENTRY+1316:
   a=tuple(map(g.u32,self.arguments(1 if t==SINE else 0)));self.calls.append((t,a));self.events.append(('CALL',t,a));return
  super().record_call(t)
 def hook(self,t):
  if t in(SINE,RNG)and not g.ENTRY<=self.current_pc<g.ENTRY+1316:
   g.put(self.memory,g.MARK,g.read(self.memory,g.MARK)+1)
   if t==SINE:value=g.bits(((self.calls[-1][1][0]&255)-128)/128.)
   else:self.parent_randoms+=1;value=(self.parent_randoms*17+self.initial_case.seed*7)&0xffffffff
   for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
   for reg in(1,2,3,*range(4,16),8,25):self.r[reg]=0xa5000000+reg
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
  if m.forwarded:assert g.canonical(raw_model)==g.canonical(m),(hex(parent),'raw identical-memory caller')
  else:assert(g.public(raw_model.memory,c),raw_model.calls,raw_model.r,raw_model.f,raw_model.fcsr)==(g.public(m.memory,c),m.calls,m.r,m.f,m.fcsr)
  assert raw_model.forwarded==m.forwarded
  if count==2 and seed==0 and slot==255 and mode==7 and outcome==1:
   bad=list(programs[0]);indices=[i for i,v in enumerate(bad)if v==0x24020001];assert len(indices)==1;bad[indices[0]]=0x24020000;wrong=Connected(bad,c,parent,count,step,rom).run();assert len(wrong.forwarded)<len(m.forwarded),(hex(parent),'ineffective return control');controls+=1;control_rows.append(dict(parent=hex(parent),step=step,good_calls=len(m.forwarded),bad_calls=len(wrong.forwarded)))
  cases+=1
 return dict(retail_parent_cases=cases,parent_programs=4,raw_identical_parent_cases=cases,connected_child_calls_per_stream=children,parents=summary,visited_parent_words={hex(a):len(v)for a,v in visits.items()},all15_callback_arguments_observed=True,return_zero_controls=control_rows,effective_return_controls=controls,whole_original_parents_under_opaque_providers=True)

def angle_leaf(rom,before):
 from tools.patch_generated_slice_ld import load_game_data_layout
 start,base,end,_=load_game_data_layout(p.ROOT/'conker');address=0x8009a220;data=struct.pack('>65I',*g.TRIG);at=p.elf_slot_offset(before,address,len(data));assert before[at:at+len(data)]==rom[start+address-base:start+address-base+len(data)]==data
 words=original(g.ANGLE,27,rom);body=struct.pack('>27I',*words);at=p.elf_slot_offset(before,g.ANGLE,len(body));assert before[at:at+len(body)]==body;visits=set()
 for angle in range(256):
  c=g.Case();memory=g.fixture(c)
  for i,v in enumerate(g.TRIG):g.put(memory,address+4*i,v)
  m=g.Oracle(words,c,entry=g.ANGLE,memory=memory,arguments=(0xabcd0000|angle,)).run();assert m.f[0]==g.angle_value(angle);visits|=set(m.visits)
 assert visits==set(range(g.ANGLE,g.ANGLE+108,4))
 return dict(angle_helper_cases=256,angle_helper_words_executed=27,angle_helper_matches_live_ELF=True,angle_table_bytes=260,angle_table_sha256=hashlib.sha256(data).hexdigest())
def factory(rom,before):
 backend=0x1513264c;copy=0x10022ec0;words=original(g.SUBMIT,15,rom);body=struct.pack('>15I',*words);at=p.elf_slot_offset(before,g.SUBMIT,60);assert before[at:at+60]==body
 connected=dict(zip(range(g.SUBMIT,g.SUBMIT+60,4),words));copy_words=list(struct.unpack_from('>11I',rom,0x22ec0));at=p.elf_slot_offset(before,copy,44);assert before[at:at+44]==struct.pack('>11I',*copy_words)
 copy_code=dict(zip(range(copy,copy+44,4),copy_words));connected.update(copy_code)
 class Wrapped(g.Oracle):
  def record_call(self,t):
   if t==backend:
    a=tuple(map(g.u32,self.arguments(7)));assert a==(g.descriptor(self.c),3,255,0,4,self.c.slot&255,0);self.calls.append((t,a));self.events.append(('CALL',t,a))
   else:super().record_call(t)
  def hook(self,t):
   assert t!=g.SUBMIT
   return super().hook(g.SUBMIT if t==backend else t)
 class Copy(g.FactoryOracle):
  def record_call(self,t):raise AssertionError('Copy leaf call')
  def hook(self,t):raise AssertionError('Copy leaf provider')
 factory_visits=set();copy_visits=set();cases=0
 programs=[*g.streams(),g.bound_blob(*g.payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),g.symbols())]
 for outcome,mode,phase,slot in itertools.product((0,1),(0,7),(0,8),(0,255)):
  c=g.Case(outcome=outcome,mode=mode,phase=phase,slot=slot);initial=g.fixture(c);wanted,calls,obs,fcsr=g.reference(initial,c);models=[]
  for ws in programs:
   m=Wrapped(ws,c,connected=connected).run();expanded=[]
   for call in calls:
    expanded.append(call)
    if call[0]==g.SUBMIT:expanded.append((backend,(g.descriptor(c),3,255,0,4,slot,0)))
   assert m.calls==expanded
   assert g.public(m.memory,c)==g.public(wanted,c)and g.records(m.memory,c)==g.records(wanted,c)
   assert m.r[2]==1 and m.r[29]==g.STACK+phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   factory_visits|={pc for pc in m.visits if g.SUBMIT<=pc<g.SUBMIT+60};copy_visits|={pc for pc in m.visits if pc in copy_code};models.append(m)
  assert all(g.state(m)==g.state(models[0])for m in models[1:])
  memory=dict(models[0].memory);dest=g.OUTPUT+16;expected=dict(memory)
  for i,v in enumerate(g.records(memory,c)):expected[dest+i]=v
  m=Copy(copy_words,memory,c,entry=copy,arguments=(dest,g.descriptor(c),124)).run()
  assert g.public(m.memory,c)==g.public(expected,c)and g.records(m.memory,c)==g.records(expected,c)and m.r[2]==dest
  copy_visits|=set(m.visits);cases+=1
 assert factory_visits==set(range(g.SUBMIT,g.SUBMIT+60,4))and copy_visits==set(range(copy,copy+44,4))
 source=(p.OUT/'baseline/conker/src/game/generated_15F680.c').read_text();assert 'memcpy(result + 0x10, descriptor, 0x7C);'in source
 return dict(original_factory_wrapper_cases=cases,original_factory_wrapper_words_executed=15,factory_wrapper_matches_live_ELF=True,all_seven_backend_arguments_checked=True,backend_internals_contracted=True,backend_remains_unmatched=True,original_copy_cases=cases,original_copy_words_executed=11,copy_matches_live_ELF=True,descriptor_copy_bytes=124,unspecified_bytes_copied_in_guest=12,helper_matching_credit=0)

def getter(rom,before):
 words=original(g.TWEAK,7,rom);blob=struct.pack('>7I',*words);at=p.elf_slot_offset(before,g.TWEAK,28);assert before[at:at+28]==blob
 visits=set();cases=0
 for i,default,phase in itertools.product(range(9),(0,1,0xffffffff,0x80000000,0x7fffffff,0x01000001),(0,8)):
  low,high,_,line=g.TWEAK_META[i];args=(i+6,g.LABELS[2*i],g.u32(low),high,default,g.LABELS[2*i+1],line)
  m=g.Oracle(words,g.Case(phase=phase),entry=g.TWEAK,memory=g.fixture(g.Case(phase=phase)),arguments=args).run()
  assert m.r[2]==default and m.r[29]==g.STACK+phase and not m.calls
  visits|=set(m.visits);cases+=1
 assert visits==set(range(g.TWEAK,g.TWEAK+28,4))
 return dict(original_tweak_cases=cases,original_tweak_words_executed=7,tweak_matches_frozen_ELF=True,seventh_argument_present_and_fifth_returned=True)

def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();jal=0xc000000|((g.ENTRY>>2)&0x3ffffff);jump=0x8000000|((g.ENTRY>>2)&0x3ffffff);sites=[];pointers=[]
 for i,(v,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
  if v in(jal,jump):sites.append(i*4)
  if v==g.ENTRY:pointers.append(i*4)
 assert not sites and pointers==[0x22f4e8]
 before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();at=p.elf_slot_offset(before,0x8008aa28,4);assert before[at:at+4]==g.ENTRY.to_bytes(4,'big')
 from tools.patch_generated_slice_ld import load_game_data_layout
 start,base,end,_=load_game_data_layout(p.ROOT/'conker');data=struct.pack('>6I',*g.VALUES);at=p.elf_slot_offset(before,g.CONSTANTS[0],24);assert before[at:at+24]==rom[start+g.CONSTANTS[0]-base:start+g.CONSTANTS[0]-base+24]==data
 asm=(p.OUT/'baseline/conker/asm/176A00.s').read_text();refs=[m[1]for m in re.finditer(r'glabel (func_[0-9A-F]+)\n(.*?)endlabel \1',asm,re.S)if'D_8008AA00'in m[2]];assert refs==['func_1514C2F0','func_1514C470','func_1514C678','func_1514C858']
 q=dict(pristine_ROM_sha256=hashlib.sha256(rom).hexdigest(),entire_pristine_aligned_ROM_scanned=True,entry_JALs=sites,entry_pointers=[hex(v)for v in pointers],qualified_entry_pointer='0x8008aa28',additional_static_entry_references=0,table_referencing_parents=refs,coefficient_bytes=24,coefficient_sha256=hashlib.sha256(data).hexdigest(),**parents(rom,before),**angle_leaf(rom,before),**getter(rom,before),**factory(rom,before),source_installed=p.installed(),matching_credit=0)
 (p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
