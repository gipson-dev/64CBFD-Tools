"""Private numeric/ABI packet screen with the complete original retail callee."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,itertools,json,struct
from tools.tests import game_short_packet_factory_oracle as old
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_scaled_argument_packet_151a1010_recovery as m
r,o,ENTRY,CALLEE,CONST=m.ROOT,m.OUT,m.ENTRY,m.CALLEE,m.CONST
bits,floating=old.old.bits,old.old.floating
@dataclass(frozen=True)
class Case:
 span:int=32
 scale:float=1.0
 rate:float=1.0
 variant:int=0
 flags:int=0x87654321
 phase:int=0
 x:float=1.25
 y:float=-2.5
 value:float=3.75
def original(entry,n):return list(struct.unpack_from('>'+str(n)+'I',(r/'conker/conker.us.bin').read_bytes(),entry-0x15000000+0x2D4B0))
class Machine(old.Machine):
 def __init__(self,words,c):
  self.case=c;self.calls_seen=[];m={old.STACK+c.phase+i:0xCD for i in range(-1024,512)};old.put(m,CONST,0x44BB8000)
  connected=dict(zip(range(CALLEE,CALLEE+24,4),original(CALLEE,6)))
  old.FactoryOracle.__init__(self,words,m,c,entry=ENTRY,s={},arguments=(0,0,bits(c.value),old.u32(c.span),bits(c.scale),bits(c.rate),0x12340000|c.variant,c.flags),connected=connected)
  self.f[12]=bits(c.x);self.f[14]=bits(c.y);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,target):
  assert target==CALLEE
  args=(self.f[12],self.f[14],self.r[6],self.r[7],*tuple(self.get(self.r[29]+4*i,4)for i in range(4,28)))
  self.calls_seen.append(args);self.calls.append((target,args))
 def hook(self,target):raise AssertionError(('retail callee should execute directly',hex(target)))
def reference(c):
 short=lambda n:((n&65535)^32768)-32768
 product=lambda k,v:bits(float(k)*floating(bits(v)))
 n16=lambda k,v:old.u32(short(int(floating(product(k,v)))))
 n32=lambda k,v:old.u32(int(floating(product(k,v))))
 adjusted=short(short(c.span)-32);clamped=max(1,adjusted)
 a,b,d,e=n16(70,c.rate),n16(30,c.rate),n16(1500,c.scale),n16(100,c.scale)
 return (bits(c.x),bits(c.y),bits(c.value),product(250,c.scale),bits(1.0),a,b,d,e,18,bits(1.0),n32(90,c.rate),n32(20,c.rate),d,e,old.u32(clamped),16,bits(1.0),a,b,d,e,n32(15,c.scale),n32(10,c.scale),18,old.u32(adjusted+16),c.variant&255,old.u32(c.flags))
def main():
 record=json.loads((o/'production-baseline/fingerprints.json').read_text())
 def immutable():
  for n,h in record['inputs'].items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n
 immutable();programs=m.programs()
 elf=(r/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,CALLEE,24);assert list(struct.unpack_from('>6I',elf,at))==original(CALLEE,6)
 spans=(-32768,-32767,-1,0,1,15,16,31,32,33,63,64,32735,32736,32767,0x12340020,0xFFFF8020)
 factors=((0.0,-0.0),(1.0,1.0),(-1.0,2.0),(0.125,0.75),(22.0,819.5),(100.0,512.25),(5000.0,2048.5),(-5000.0,-2048.5))
 cases=[Case(span=a,scale=b,rate=c,variant=v,phase=8*(i%2),flags=0x87650000|i)for i,(a,(b,c),v)in enumerate(itertools.product(spans,factors,(0,255)))]
 cases += [Case(span=spans[i%len(spans)],scale=factors[i%len(factors)][0],rate=factors[i%len(factors)][1],variant=i,flags=old.u32(i*0x1020304))for i in range(256)]
 seen={name:set()for name in programs}
 for i,c in enumerate(cases):
  expected=reference(c)
  for label,words in programs.items():
   q=Machine(words,c).run();assert q.calls_seen==[expected],(i,label,[(n,hex(a),hex(b))for n,(a,b)in enumerate(zip(q.calls_seen[0],expected))if a!=b])
   assert [q.r[n]for n in(*range(16,24),28,29,30,31)]==[q.before[n]for n in(*range(16,24),28,29,30,31)] and q.f[20:]==q.before_f[20:]
   seen[label].update(q.visits)
 immutable();report=dict(private_only=True,c_match_credit=0,cases_per_stream=len(cases),streams=3,all28_outgoing_arguments=True,real_retail_callee_words=6,callee_production_exact=True,all256_variant_bytes=True,signed16_wrap_and_clamp_boundaries=True,full32_vs_narrow16_float_outputs=True,visited_target_words={label:len([pc for pc in values if ENTRY<=pc<ENTRY+4*len(programs[label])])for label,values in seen.items()},return_type_void_is_still_hypothesis=True,ordered_FP_checked_separately=True,native_checked_separately=True,production_inputs_unchanged=len(record['inputs']))
 (o/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
