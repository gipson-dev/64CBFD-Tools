"""All four original registry parents plus independently bound extended sprite consumer."""
from dataclasses import replace
import hashlib,itertools,json,re,struct
from tools.experiments import game_radial_sprite_150cdf10_match as p
from tools.tests import game_radial_sprite_150cdf10_guest as g
PARENTS={0x1514c2f0:(96,160,True),0x1514c470:(130,168,False),0x1514c678:(120,160,True),0x1514c858:(138,216,False)}
TABLE,SINE,ALLOCATE,FACTORY=0x8008aa00,0x151423d8,0x15167a68,0x15130280
def original(entry,count,rom):return list(struct.unpack_from('>'+str(count)+'I',rom,entry-0x15000000+0x2d4b0))
class Connected(g.Oracle):
 def __init__(self,words,c,parent,count,step,rom,raw=False):
  self.parent=parent;self.initial_case=c;self.parent_randoms=0;self.forwarded=[];self.child_starts=[];memory=g.fixture(c)
  if raw:
   child=replace(c,phase=c.phase-PARENTS[parent][1]);old=dict(memory)
   for i in range(124):memory[g.packet(child,True)+i]=old[g.packet(child)+i]
  for i in range(28):g.put(memory,TABLE+4*i,g.ENTRY if i==24 else 0)
  x,y,z=map(g.floating,c.coords)
  if parent in(0x1514c2f0,0x1514c678):arguments=(0,0,g.bits(z),g.bits(2.),250,step,count,24,9,g.bits(.75),0x81234567,c.slot)
  elif parent==0x1514c470:arguments=(0,0,g.bits(z),g.bits(x+9),g.bits(y-7),g.bits(z+5),g.bits(float(count)),24,9,g.bits(.75),0x81234567,c.slot)
  else:arguments=(0,0,g.bits(z),g.bits(2.),63,250,step,count,24,9,g.bits(.75),0x81234567,c.slot)
  code=dict(zip(range(g.ENTRY,g.ENTRY+568,4),words));g.Oracle.__init__(self,original(parent,PARENTS[parent][0],rom),c,entry=parent,memory=memory,arguments=arguments,connected=code,raw=raw);self.f[12]=c.coords[0];self.f[14]=c.coords[1];self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(15)));a,b,x,y,z,ox,oy,oz,angle,start,radius,style,extra,context,slot=args;self.forwarded.append(args);self.child_starts.append((self.r[29],self.fcsr));self.c=replace(self.initial_case,phase=self.r[29]-g.STACK,coords=(x,y,z),angle=angle,slot=slot,unused=(a,b,ox,oy,oz,start,radius,style,extra,context));self.counts={};self.calls.append((t,args));self.events.append(('CALL',t,args));return
  if t==SINE or(t==g.RNG and not g.ENTRY<=self.current_pc<g.ENTRY+568):
   a=tuple(map(g.u32,self.arguments(1 if t==SINE else 0)));self.calls.append((t,a));self.events.append(('CALL',t,a));return
  super().record_call(t)
 def hook(self,t):
  if t==SINE or(t==g.RNG and not g.ENTRY<=self.current_pc<g.ENTRY+568):
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
 asm=(p.OUT/'baseline/conker/asm/15F680.s').read_text();symbols={n:v[1]for _,n,v,_ in p.symbol_rows(before)};helpers=[]
 for name,entry,romat,size in [('func_1513264C',0x1513264c,0x15fafc,1024),('func_15132A4C',0x15132a4c,0x15fefc,60)]:
  fragment='glabel '+name+asm.split('glabel '+name,1)[1].split('endlabel '+name,1)[0]+'endlabel '+name+'\n';target=p.OUT/(name+'-retail.o');p.assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'.size '+name+',.-'+name+'\n',target);data,refs=g.payload(target,name)
  for pairs in refs.values():
   for _,label in pairs:
    if label.startswith(('D_','func_')):symbols[label]=int(label.split('_',1)[1],16)
  linked=g.bound_blob(data,refs,symbols);pristine=rom[romat:romat+size];assert linked==list(struct.unpack('>'+str(size//4)+'I',pristine));at=p.elf_slot_offset(before,entry,size);helpers.append(dict(function=name,words=size//4,sha256=hashlib.sha256(pristine).hexdigest(),matches_live_ELF=before[at:at+size]==pristine))
 assert helpers[0]['matches_live_ELF']is False and helpers[1]['matches_live_ELF']is True
 assert rom[0x15fd74:0x15fd7c]==bytes.fromhex('0c008bb02406007c')
 return dict(descriptor_copy_bytes=124,original_helpers=helpers,retail_consumer_independently_bound=True,live_consumer_remains_unmatched=True,helpers_internals_contracted=True,helper_matching_credit=0)

def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0c000000|((g.ENTRY>>2)&0x3ffffff);jump=0x08000000|((g.ENTRY>>2)&0x3ffffff);sites=[];pointers=[]
 for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
  if word in(jal,jump):sites.append(i*4)
  if word==g.ENTRY:pointers.append(i*4)
 assert not sites and pointers==[0x22f520],(sites,pointers)
 before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();assert tuple(int.from_bytes(before[p.elf_slot_offset(before,a,4):p.elf_slot_offset(before,a,4)+4],'big')for a in g.CONSTANTS)==g.VALUES;at=p.elf_slot_offset(before,0x8008aa60,4);assert before[at:at+4]==g.ENTRY.to_bytes(4,'big')
 asm=(p.OUT/'baseline/conker/asm/176A00.s').read_text();refs=[m[1]for m in re.finditer(r'glabel (func_[0-9A-F]+)\n(.*?)endlabel \1',asm,re.S)if'D_8008AA00'in m[2]];assert refs==['func_1514C2F0','func_1514C470','func_1514C678','func_1514C858']
 q=dict(pristine_ROM_sha256=hashlib.sha256(rom).hexdigest(),entire_pristine_aligned_ROM_scanned=True,entry_JALs=sites,entry_pointers=[hex(v)for v in pointers],qualified_entry_pointer='0x8008aa60',additional_static_entry_references=0,table_referencing_parents=refs,**parents(rom,before),**factory(rom,before),source_installed=p.installed(),matching_credit=0);(p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
