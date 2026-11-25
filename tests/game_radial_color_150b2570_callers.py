"""All four original registry parents plus independently bound extended sprite consumer."""
from dataclasses import replace
import hashlib,itertools,json,re,struct
from tools.experiments import game_radial_color_150b2570_match as p
from tools.tests import game_radial_color_150b2570_guest as g
PARENTS={0x1514c2f0:(96,160,True),0x1514c470:(130,168,False),0x1514c678:(120,160,True),0x1514c858:(138,216,False)}
TABLE,SINE,ALLOCATE,FACTORY=0x8008aa00,0x151423d8,0x15167a68,0x15130280
def original(entry,count,rom):return list(struct.unpack_from('>'+str(count)+'I',rom,entry-0x15000000+0x2d4b0))
class Connected(g.Oracle):
 def __init__(self,words,c,parent,count,step,rom,raw=False):
  self.parent=parent;self.initial_case=c;self.parent_randoms=0;self.forwarded=[];self.child_starts=[];memory=g.fixture(c)
  if raw:
   child=replace(c,phase=c.phase-PARENTS[parent][1]);old=dict(memory)
   for at,n in((g.floats(child),12),(g.pitchslot(child),2),(g.packet(child),60)):
    for i in range(n):memory[at+4+i]=old[at+i]
  for i in range(28):g.put(memory,TABLE+4*i,g.ENTRY if i==7 else 0)
  x,y,z=map(g.floating,c.coords)
  if parent in(0x1514c2f0,0x1514c678):arguments=(0,0,g.bits(z),g.bits(2.),250,step,count,7,9,g.bits(.75),0x81234567,c.slot)
  elif parent==0x1514c470:arguments=(0,0,g.bits(z),g.bits(x+9),g.bits(y-7),g.bits(z+5),g.bits(float(count)),7,9,g.bits(.75),0x81234567,c.slot)
  else:arguments=(0,0,g.bits(z),g.bits(2.),63,250,step,count,7,9,g.bits(.75),0x81234567,c.slot)
  code=dict(zip(range(g.ENTRY,g.ENTRY+460,4),words));g.Oracle.__init__(self,original(parent,PARENTS[parent][0],rom),c,entry=parent,memory=memory,arguments=arguments,connected=code,raw=raw);self.f[12]=c.coords[0];self.f[14]=c.coords[1];self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(15)));a,b,x,y,z,ox,oy,oz,angle,start,radius,style,extra,context,slot=args;self.forwarded.append(args);self.child_starts.append((self.r[29],self.fcsr));self.c=replace(self.initial_case,phase=self.r[29]-g.STACK,coords=(x,y,z),angle=angle,slot=slot,unused=(a,b,ox,oy,oz,start,radius,style,extra,context));self.counts={};self.calls.append((t,args));self.events.append(('CALL',t,args));return
  if t in(SINE,g.RNG)and not g.ENTRY<=self.current_pc<g.ENTRY+460:
   a=tuple(map(g.u32,self.arguments(1 if t==SINE else 0)));self.calls.append((t,a));self.events.append(('CALL',t,a));return
  super().record_call(t)
 def hook(self,t):
  if t in(SINE,g.RNG)and not g.ENTRY<=self.current_pc<g.ENTRY+460:
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
  if m.forwarded:assert g.canonical(raw_model)==g.canonical(m),(hex(parent),'raw stack-map caller')
  else:assert(g.public(raw_model.memory,c),raw_model.calls,raw_model.r,raw_model.f,raw_model.fcsr)==(g.public(m.memory,c),m.calls,m.r,m.f,m.fcsr)
  assert raw_model.forwarded==m.forwarded
  if count==2 and seed==0 and slot==255 and mode==7 and outcome==1:
   bad=list(programs[0]);assert bad[-5]==0x24020001;bad[-5]=0x24020000;wrong=Connected(bad,c,parent,count,step,rom).run();assert len(wrong.forwarded)<len(m.forwarded),(hex(parent),'ineffective return control');controls+=1;control_rows.append(dict(parent=hex(parent),step=step,good_calls=len(m.forwarded),bad_calls=len(wrong.forwarded)))
  cases+=1
 return dict(retail_parent_cases=cases,parent_programs=4,raw_stack_map_parent_cases=cases,connected_child_calls_per_stream=children,parents=summary,visited_parent_words={hex(a):len(v)for a,v in visits.items()},all15_callback_arguments_observed=True,return_zero_controls=control_rows,effective_return_controls=controls,whole_original_parents_under_opaque_providers=True)
def factory(rom,before):
 from tools.patch_generated_slice_ld import load_game_data_layout
 import hashlib,struct
 helpers=[];programs={};symbols={n:v[1]for _,n,v,_ in p.symbol_rows(before)}
 for name,entry,count,path in [('func_15156190',0x15156190,126,'conker/asm/183640.s'),('func_15156388',0x15156388,12,'conker/asm/183640.s'),('func_151423D8',0x151423d8,27,'conker/asm/nonmatchings/game_16EE20/func_151423D8.s'),('func_151429E0',0x151429e0,31,'conker/asm/nonmatchings/game_16EE20/func_151429E0.s')]:
  asm=(p.OUT/'baseline'/path).read_text();fragment='glabel '+name+asm.split('glabel '+name,1)[1].split('endlabel '+name,1)[0]+'endlabel '+name+'\n';target=p.OUT/(name+'-retail.o');p.assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'.size '+name+',.-'+name+'\n',target);data,refs=g.payload(target,name)
  for pairs in refs.values():
   for _,label in pairs:
    if label.startswith(('D_','func_')):symbols[label]=int(label.split('_',1)[1],16)
  linked=g.bound_blob(data,refs,symbols);atrom=entry-0x15000000+0x2d4b0;pristine=rom[atrom:atrom+count*4];assert linked==list(struct.unpack('>'+str(count)+'I',pristine));at=p.elf_slot_offset(before,entry,len(pristine));helpers.append(dict(function=name,words=count,sha256=hashlib.sha256(pristine).hexdigest(),matches_live_ELF=before[at:at+len(pristine)]==pristine));programs[entry]=linked
 assert [v['matches_live_ELF']for v in helpers]==[False,True,True,True]
 start,base,end,_=load_game_data_layout(p.ROOT/'conker');pins=[]
 for address,expected in [(0x8009f900,struct.pack('>6I',*g.VALUES)),(0x8009a220,struct.pack('>65I',*g.TRIG)),(0x8008a1c0,bytes(g.PALETTE))]:
  at=p.elf_slot_offset(before,address,len(expected));assert before[at:at+len(expected)]==rom[start+address-base:start+address-base+len(expected)]==expected;pins.append(dict(address=hex(address),bytes=len(expected),sha256=hashlib.sha256(expected).hexdigest()))
 descriptor_reads=set()
 for w in programs[0x15156190]:
  if w>>21&31==16 and w>>26 in(35,36,33,37,49):
   size={35:4,36:1,33:2,37:2,49:4}[w>>26];at=w&65535;descriptor_reads.update(range(at,at+size))
 assert descriptor_reads==set(g.KNOWN)
 angle_visits=set();color_visits=set();angle_cases=color_cases=0
 for angle in range(256):
  c=g.Case();memory=g.fixture(c)
  for i,v in enumerate(g.TRIG):g.put(memory,0x8009a220+4*i,v)
  m=g.Oracle(programs[g.ANGLE],c,entry=g.ANGLE,memory=memory,arguments=(0xabcd0000|angle,)).run();assert m.f[0]==g.angle_value(angle);angle_visits|=set(m.visits);angle_cases+=1
 for draw in(0,1,2,3,4,0xffffffff):
  c=g.Case(rng=(draw,));memory=g.fixture(c)
  for i,v in enumerate(g.PALETTE):g.put(memory,0x8008a1c0+i,v,1)
  destinations=(g.OUTPUT+0x80,g.OUTPUT+0x81,g.OUTPUT+0x82)
  m=g.Oracle(programs[g.COLOR],c,entry=g.COLOR,memory=memory,arguments=(8,*destinations)).run();assert bytes(m.memory[a]for a in destinations)==bytes(g.PALETTE[3*(draw&3):3*(draw&3)+3]);color_visits|=set(m.visits);color_cases+=1
 assert angle_visits==set(range(g.ANGLE,g.ANGLE+108,4));assert set(range(g.COLOR,g.COLOR+124,4))<=color_visits
 return dict(original_helpers=helpers,read_only_data_pins=pins,constructor_descriptor_read_bytes=len(descriptor_reads),descriptor_holes_not_read=True,constructor_internals_contracted=True,unused_wrapper_binding_only=True,angle_helper_cases=angle_cases,angle_helper_words_executed=27,color_helper_cases=color_cases,color_helper_words_executed=31,color_internal_RNG_explicitly_executed=True,live_constructor_remains_unmatched=True,helper_matching_credit=0)


def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0c000000|((g.ENTRY>>2)&0x3ffffff);jump=0x08000000|((g.ENTRY>>2)&0x3ffffff);sites=[];pointers=[]
 for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
  if word in(jal,jump):sites.append(i*4)
  if word==g.ENTRY:pointers.append(i*4)
 assert not sites and pointers==[0x22f4dc],(sites,pointers)
 before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();assert tuple(int.from_bytes(before[p.elf_slot_offset(before,a,4):p.elf_slot_offset(before,a,4)+4],'big')for a in g.CONSTANTS)==g.VALUES;at=p.elf_slot_offset(before,0x8008aa1c,4);assert before[at:at+4]==g.ENTRY.to_bytes(4,'big')
 asm=(p.OUT/'baseline/conker/asm/176A00.s').read_text();refs=[m[1]for m in re.finditer(r'glabel (func_[0-9A-F]+)\n(.*?)endlabel \1',asm,re.S)if'D_8008AA00'in m[2]];assert refs==['func_1514C2F0','func_1514C470','func_1514C678','func_1514C858']
 q=dict(pristine_ROM_sha256=hashlib.sha256(rom).hexdigest(),entire_pristine_aligned_ROM_scanned=True,entry_JALs=sites,entry_pointers=[hex(v)for v in pointers],qualified_entry_pointer='0x8008aa1c',additional_static_entry_references=0,table_referencing_parents=refs,**parents(rom,before),**factory(rom,before),source_installed=p.installed(),matching_credit=0);(p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
