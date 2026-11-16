"""Both original indirect parents; production stub explicitly kept distinct."""
from dataclasses import replace
from pathlib import Path
import hashlib,importlib.util,itertools,json,re,struct,sys
from tools.tests import game_radial_dispatch_1514c2f0_oracle as radial
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_randomized_short_packet_151a0c0c_match as m
from tools.tests import game_randomized_short_packet_151a0c0c_oracle as g
r,o=m.ROOT,m.OUT
PARENTS={0x1514C2F0:(96,160,True),0x1514C470:(130,168,False),0x1514C678:(120,160,True),0x1514C858:(138,216,False)}
def original(entry,count):return list(struct.unpack_from('>'+str(count)+'I',(r/'conker/conker.us.bin').read_bytes(),entry-0x15000000+0x2D4B0))
class Connected(g.Machine):
 def __init__(self,words,c,pool,parent,count,step):
  self.parent=parent;self.frame=PARENTS[parent][1];self.case=c;self.home=g.old.STACK+c.phase;self.target=g.ENTRY;self.providers=g.S
  self.rng_i=self.rng_f=self.trig_i=self.submits=0;self.payloads=[];self.forwarded=[];self.starts=[];self.parent_sines=0
  self.childwords=len(words);m=g.initial(c,pool);g.old.put(m,radial.TABLE+16,g.ENTRY)
  if parent==0x1514C2F0:args=(0,0,g.bits(c.z),g.bits(2.0),250,step,count,4,c.style,g.bits(0.75),0x81234567,c.mode)
  elif parent==0x1514C470:args=(0,0,g.bits(c.z),g.bits(c.x+9.0),g.bits(c.y-7.0),g.bits(c.z+5.0),g.bits(float(count)),4,c.style,g.bits(0.75),0x81234567,c.mode)
  elif parent==0x1514C678:args=(0,0,g.bits(c.z),g.bits(2.0),250,step,count,4,c.style,g.bits(0.75),0x81234567,c.mode)
  else:args=(0,0,g.bits(c.z),g.bits(2.0),63,250,step,count,4,c.style,g.bits(0.75),0x81234567,c.mode)
  connected=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words))
  g.old.FactoryOracle.__init__(self,original(parent,PARENTS[parent][0]),m,c,entry=parent,s={},arguments=args,connected=connected)
  self.f[12]=g.bits(c.x);self.f[14]=g.bits(c.y);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,target):
  if target==g.ENTRY:
   args=tuple(self.arguments(15));self.forwarded.append(args);self.starts.append((self.rng_i,self.trig_i,self.rng_f));self.home=self.r[29]
   self.calls.append((target,args));self.events.append(('CALL',target,args));return
  return super().record_call(target)
 def hook(self,target):
  if target!=g.S['func_151423D8'] or g.ENTRY<=self.current_pc<g.ENTRY+4*self.childwords:return super().hook(target)
  angle=self.calls[-1][1][0];value=radial.sine(angle);self.parent_sines+=1
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.f[0]=value
def main():
 record=json.loads((m.FROZEN/'fingerprints.json').read_text())
 def immutable():
  m.check_inputs()
 immutable();rom=(r/'conker/conker.us.bin').read_bytes();elf=(r/'conker/build/conker.us.elf').read_bytes()
 all_words=list(struct.unpack('>'+str(len(rom)//4)+'I',rom[:len(rom)&~3]));jal=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF);jump=0x08000000|((g.ENTRY>>2)&0x3FFFFFF)
 assert [i*4 for i,v in enumerate(all_words)if v==g.ENTRY]==[0x22F4D0]
 assert not any(v in(jal,jump)for v in all_words)
 slot=elf_slot_offset(elf,0x8008AA10,4);assert struct.unpack_from('>I',elf,slot)[0]==g.ENTRY
 parent_state={}
 for entry,(count,frame,exact)in PARENTS.items():
  raw=struct.pack('>'+str(count)+'I',*original(entry,count));at=elf_slot_offset(elf,entry,len(raw));is_exact=elf[at:at+len(raw)]==raw;assert is_exact==exact
  parent_state[hex(entry)]=dict(words=count,production_byte_exact=exact,retail_execution_only=not exact)
 asm=(r/'conker/asm/176A00.s').read_text();refs=[]
 for match in re.finditer(r'glabel (func_[0-9A-F]+)\n(.*?)endlabel \1',asm,re.S):
  if 'D_8008AA00' in match[2]:refs.append(match[1])
 assert refs==['func_1514C2F0','func_1514C470','func_1514C678','func_1514C858'],refs
 programs=m.programs()
 cases=0;child_calls=0;seen={entry:set()for entry in PARENTS};layouts={}
 for entry,seed,style,mode,count,step in itertools.product(PARENTS,range(4),(0,1,2,15),(0,255),(0,1,2,3),(7,-128)):
  c=g.Case(seed=seed,mode=mode,style=style,phase=(seed%2)*8,x=1.25+seed,y=-2.5-seed,z=3.75+seed)
  baseline=None
  for label,(words,pool)in programs.items():
   q=Connected(words,c,pool,entry,count,step).run()
   assert len(q.forwarded)==q.submits==len(q.payloads)
   for index,(args,start,(packet,submit))in enumerate(zip(q.forwarded,q.starts,q.payloads)):
    assert args[0]=={0x1514C470:0,0x1514C2F0:1,0x1514C678:2,0x1514C858:3}[entry] and args[1]==index and args[11]==style and args[14]==mode
    child=replace(c,phase=c.phase-PARENTS[entry][1],x=g.floating(args[2]),y=g.floating(args[3]),z=g.floating(args[4]),heading=args[8])
    expected,calls=g.reference(child,*start);assert packet==expected,(hex(entry),label,index,'complete packet')
    integer_start=5*index+1 if entry in(0x1514C678,0x1514C858)else 4*index
    assert submit==calls[-1][1] and start==(integer_start,4*index,index)
   assert [q.r[i]for i in(*range(16,24),28,29,30,31)]==[q.before[i]for i in(*range(16,24),28,29,30,31)]
   assert q.f[20:]==q.before_f[20:]
   state=(q.calls,q.forwarded,q.payloads,q.rng_i,q.trig_i,q.rng_f,q.submits)
   if label=='retail':baseline=state;child_calls+=len(q.forwarded)
   else:assert state==baseline,(hex(entry),label,'connected transfer')
   seen[entry]|={pc for pc in q.visits if entry<=pc<entry+4*PARENTS[entry][0]}
  cases+=1
 immutable();report=dict(private_only=True,c_match_credit=0,cases_per_stream=cases,streams=len(programs),connected_child_calls_per_stream=child_calls,parents=parent_state,visited_parent_words={hex(k):len(v)for k,v in seen.items()},pointer_slots=['0x22F4D0'],direct_JAL_or_J=0,table_referencing_parents=refs,all15_callback_arguments_observed=True,full_packet_and_provider_order_equal=True,opaque_rng_sine_submission=True,production_state_matches_audited_inputs=len(record['inputs']))
 (o/'callers-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
