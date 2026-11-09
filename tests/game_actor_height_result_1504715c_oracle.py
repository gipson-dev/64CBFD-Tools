"""Independent actor/result contract, aliases, raw truth and original helper."""
import json,math,struct,sys
from pathlib import Path
from dataclasses import dataclass,replace
from tools.experiments.game_actor_height_result_1504715c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_actor_direction_point_oracle import DirectionOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=0x1504715C;HELPER=0x15145C90;ACTOR=0x20000;OUTPUT=0x30000;ENTITIES=0x80000
SYMS={'D_800DBEF4':0x800DBEF4,'func_15145C90':HELPER}
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 flags:int=0x200000
 identity:int=1
 helper:int=0x100
 mutation:int=0xA4
 effects:int=0
 output_mode:int=0
 coordinates:tuple=(-12.75,-5.75,23.75)
 metadata:int=0x12345678
 entity_flags:int=0x80
 phase:int=0
 seed:int=0
def output(c):return(OUTPUT,ACTOR+0xF8,ACTOR+0x168,ACTOR+0x180,STACK+c.phase+128)[c.output_mode]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,512)}
 for base,n in((ACTOR,0x1A4),(OUTPUT-8,52)):m.update({base+i:(i*29+c.seed*11+0x59)&255 for i in range(n)})
 put(m,ACTOR+0x14,bits(c.coordinates[0]));put(m,ACTOR+0x180,bits(c.coordinates[1]));put(m,ACTOR+0x1C,bits(c.coordinates[2]));put(m,ACTOR+0xF8,c.flags);put(m,ACTOR+0x184,c.metadata);put(m,ACTOR+0x1A0,c.identity,2)
 for i in range(9):put(m,ACTOR+0x18C+2*i,i*137-1234,2)
 put(m,s['D_800DBEF4'],ENTITIES)
 if c.identity:m[ENTITIES+(c.identity-1)*160+0x6F]=c.entity_flags
 return m
def packet(m,p):return bytes(m[p+i]for i in range(36))
def effects(m,c,s):
 p=output(c)
 if c.effects&1:m[p+0x1C]=c.mutation
 if c.effects&2:put(m,ACTOR+0x1A0,0,2);put(m,s['D_800DBEF4'],0x12340000)
 if c.effects&4:m[p+0x1D]=9;put(m,p+0x20,0xFEEDFACE);put(m,p+0x18,0x89ABCDEF)
def reference(initial,c,s=SYMS,connected=False):
 m=dict(initial);p=output(c);put(m,p,read(m,ACTOR+0x180))
 if read(m,ACTOR+0xF8)&0x200000:
  x,y,z=(math.trunc(floating(read(m,ACTOR+at)))for at in(0x14,0x180,0x1C))
  for at,value in((0,x+1000),(3,x-1000),(2,z+1000),(6,x+1000),(8,z-1000),(1,y),(4,y),(7,y),(5,z)):put(m,p+4+2*at,value,2)
 else:
  for at in range(0,16,4):put(m,p+4+at,read(m,ACTOR+0x18C+at))
  put(m,p+20,read(m,ACTOR+0x19C,2),2)
 metadata=read(m,ACTOR+0x184);m[p+28]=6;put(m,p+24,metadata);identity=read(m,ACTOR+0x1A0,2);calls=[];observations=[]
 if identity:
  m[p+29]=2;index=identity-1;put(m,p+32,u32(read(m,s['D_800DBEF4'])+index*160));calls.append((s['func_15145C90'],(index,)));observations.append(packet(m,p))
  if connected:value=(m[read(m,s['D_800DBEF4'])+index*160+0x6F]>>7)&1
  else:value=u32(c.helper);effects(m,c,s)
  m[p+28]|=int(value!=0)
 else:m[p+29]=1;put(m,p+32,0);m[p+28]|=1
 return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  super().__init__(ws,memory,c,entry=entry,s=s,connected=connected,arguments=(output(c),ACTOR));self.before=self.r[:];self.before_f=self.f[:];self.initial=dict(self.memory);self.observations=[]
 def execute(self,w):
  if w>>26 in(34,38,42,46):return DirectionOracle.execute(self,w)
  return super().execute(w)
 def record_call(self,t):
  assert t==self.syms['func_15145C90'];a=tuple(self.arguments(1));self.calls.append((t,a));self.observations.append(packet(self.memory,output(self.case)));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;effects(self.memory,c,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(c.helper);self.hi,self.lo=0xA5000010,0xA5000011
def words(path,s=SYMS):
 t,fs,rs=parse_object(path);f=fs['func_1504715C'];a,n=f['value'],f['size'];return bound_blob(t[a:a+n],{p-a:v for p,v in rs.items()if a<=p<a+n},s)
def public(m):return{p:v for p,v in m.items()if not STACK-512<=p<STACK+512}
def check(m,c,s=SYMS,connected=False):
 expected,calls,observations=reference(m.initial,c,s,connected);assert(public(m.memory),m.calls,m.observations)==(public(expected),calls,observations),('Public contract',c)
 assert packet(m.memory,output(c))==packet(expected,output(c)),('Output packet',c)
 allowed=set(range(output(c),output(c)+36));home=m.before[29]
 assert all(m.memory[p]==v for p,v in m.initial.items()if home+4<=p<home+256 and p not in allowed),'Caller storage beyond writable first home changed'
 if calls:assert read(m.memory,home)==output(c)
 assert m.r[29]==home and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
def cases():
 result=[replace(Case(),mutation=flag,helper=value,effects=7,flags=0x200000 if flag&1 else 0,identity=1 if flag&2 else 65535,seed=flag%3,phase=(flag&1)*8)for flag in range(256)for value in(0,1,0x100,0xFFFFFFFF)]
 result.extend(replace(Case(),flags=1<<bit,identity=identity)for bit in range(32)for identity in(0,1,65535))
 coords=((-0.0,0.0,0.0),(-12.75,-5.75,23.75),(32767.75,-32769.75,-32768.75),(65535.5,-65536.5,-65535.5),(1000000.0,-2147483648.0,-1000000.0))
 for mode in range(5):
  for pos in coords:
   for identity in(0,1,32768,65535):
    for flags in(0,0x200000,0xFFFFFFFF):
     if mode==3 and not flags&0x200000:continue
     result.append(replace(Case(),coordinates=pos,output_mode=mode,identity=identity,flags=flags,effects=7,phase=8))
 return result
def original_helper(s=SYMS):
 data=(root/'conker/conker.us.bin').read_bytes();ws=list(struct.unpack_from('>16I',data,HELPER-0x15000000+0x2D4B0))
 image=(root/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(image,HELPER,64);assert image[at:at+64]==struct.pack('>16I',*ws),'Production helper differs from the original helper being executed'
 # Only the helper's two data-address relocations are rebased; its code address
 # follows the separately selected call symbol.
 code=bytearray(struct.pack('>16I',*ws));refs={}
 for i,w in enumerate(ws):
  if w>>26==15 and w&65535==0x800E:refs[i*4]=[('R_MIPS_HI16','D_800DBEF4')];struct.pack_into('>I',code,i*4,w&0xFFFF0000)
  elif w>>26==35 and w&65535==0xBEF4:refs[i*4]=[('R_MIPS_LO16','D_800DBEF4')];struct.pack_into('>I',code,i*4,w&0xFFFF0000)
 assert len(refs)==2
 rebound=bound_blob(bytes(code),refs,s);return dict(zip(range(s['func_15145C90'],s['func_15145C90']+64,4),rebound))
def main():
 paths={'raw':out/'qualified-owner.o','normalized':out/'qualified-padded.o','retail':out/'retail-reference.o'};counts={};coverage={};connected=0;rebase=0;helper_code=original_helper()
 for label,p in paths.items():
  ws=words(p);seen=set()
  for c in cases():m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  counts[label]=len(cases());coverage[label]=sorted((pc-ENTRY)//4 for pc in seen if ENTRY<=pc<ENTRY+len(ws)*4)
  assert len(coverage[label])==len(ws)-1 and set(range(len(ws)))-set(coverage[label])=={33 if label=='raw'else 34}
  for flag in range(256):
   c=replace(Case(),entity_flags=flag,identity=1 if flag&1 else 65535,flags=0x200000 if flag&2 else 0,effects=0,phase=(flag&1)*8);m=Oracle(ws,fixture(c),c,connected=helper_code);m.run();check(m,c,connected=True);connected+=1
 for low in(0,0x7FFF,0x8000,0xFFFF):
  s={'D_800DBEF4':0x80300000+low,'func_15145C90':0x15200000};s['D_800DBEF4']&=~3
  for label,p in paths.items():
   for phase in(0,8):
    c=replace(Case(),effects=7,phase=phase);m=Oracle(words(p,s),fixture(c,s),c,entry=ENTRY+0x4000,s=s);m.run();check(m,c,s);rebase+=1
 report=dict(cases_per_body=counts,total=sum(counts.values()),root_reachable_words={k:len(v)for k,v in coverage.items()},unreachable_duplicate_load=1,original_helper_cases=connected,independent_rebases=rebase,helper_raw_truth_values=[0,1,256,0xFFFFFFFF],all_256_post_helper_flag_bytes=True,partial_stored_structure_overlap_qualified=False,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
