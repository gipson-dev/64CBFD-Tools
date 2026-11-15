"""View reset public-state, provider snapshots and signed-default qualification."""
from dataclasses import dataclass
from pathlib import Path
import csv,io,itertools,json,os,struct
from tools.experiments import game_view_reset_15017640_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

BSS,COUNT,CONFIG,FAR=0x800d23b0,504,0x8009dcb0,0x800968b0
ZERO,PERSPECTIVE=0x100226f0,0x15048134
signed16=lambda n:((n&65535)^32768)-32768
bits=lambda v:struct.unpack('>I',struct.pack('>f',v))[0]
@dataclass(frozen=True)
class Case:
 defaults:tuple=(-32768,0,32767)
 far:int=0x461c4000
 mode:int=0
 seed:int=0
 phase:int=0

def fixture(c):
 m={STACK+i:(i*17+c.seed+0xa5)&255 for i in range(-256,256)}
 for base,n in ((BSS,COUNT),(CONFIG,16),(FAR-4,12)):
  for i in range(n):m[base+i]=(i*29+c.seed*13+0x5a)&255
 for i,v in enumerate(c.defaults):put(m,CONFIG+4+i*2,v,2)
 put(m,FAR,c.far);return m

def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+256}
def snapshot(m):return bytes(m[a+i] for a,n in ((BSS,COUNT),(CONFIG,16),(FAR-4,12)) for i in range(n))

def effect(m,c,last=False):
 if last:
  for i in range(64):m[0x800d23d0+i]=(i*11+c.seed+0x37)&255
  put(m,0x800d2454,0x7fa5,2)
  if c.mode&4:m[0x800d24bd]=0x71;put(m,0x800d2588,0xdeadbeef)
 else:
  for i in range(0xc0):m[0x800d24c8+i]=0
  if c.mode&1:put(m,FAR,0x43af4000)
  if c.mode&2:
   put(m,0x800d242c,0xc0200000);put(m,0x800d2414,0xc0000000)
   m[0x800d24ad]=0x67;m[0x800d2458]=0xe1

def reference(initial,c):
 m=dict(initial);m[0x800d2458]=0;put(m,0x800d2588,0)
 for i in range(3):put(m,0x800d2438+i*4,0);put(m,0x800d2428+i*4,bits(float(signed16(read(m,CONFIG+4+i*2,2)))))
 for a in (0x800d2444,0x800d245c,0x800d24c0):put(m,a,0)
 for i in range(6):put(m,0x800d2410+i*4,0x3f800000);m[0x800d246d+i*16]=0
 states=[snapshot(m)];calls=[(ZERO,(0x800d24c8,0xc0))];effect(m,c)
 states.append(snapshot(m));calls.append((PERSPECTIVE,(0x800d23d0,0x800d2454,bits(50),bits(60.6),bits(53),read(m,FAR),bits(1))))
 effect(m,c,True);return public(m),calls,states

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry):
  super().__init__(words,memory,c,entry=entry,arguments=(0x12345678,0x87654321,0x80000000,0xffffffff))
  self.snapshots=[]
 def record_call(self,t):
  assert t in (ZERO,PERSPECTIVE),hex(t)
  args=tuple(self.arguments(2 if t==ZERO else 7));self.calls.append((t,args));self.snapshots.append(snapshot(self.memory))
 def hook(self,t):
  effect(self.memory,self.case,t==PERSPECTIVE)
  for i in range(4 if t==ZERO else 7):put(self.memory,self.r[29]+i*4,0xb5000000+i)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def corpus():
 for n,xyz in enumerate(itertools.product((-32768,-1,0,1,255,32767),repeat=3)):
  for mode,phase in itertools.product(range(8),(0,8)):
   yield Case(xyz,(0,0x80000000,0x3f800000,0x461c4000,0x7f800001)[n%5],mode,n&255,phase)

def compare(machine,want):
 expected,calls,states=want
 assert(public(machine.memory),machine.calls,machine.snapshots)==(expected,calls,states)

def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD;programs=source.programs(root);cases=0;seen=[set() for _ in programs]
 for c in corpus():
  initial=fixture(c);want=reference(initial,c)
  for i,(words,entry) in enumerate(programs):
   machine=Oracle(words,initial,c,entry);machine.run();compare(machine,want);seen[i].update(machine.visits)
  cases+=1
 assert all(len(v)==82 for v in seen)
 rom=(root/'conker/conker.us.bin').read_bytes();rows=list(csv.DictReader(io.StringIO((root/'conker/retail_layout.us.txt').read_text())));end=max(int(r['end'],16) for r in rows if r['section']=='game')
 jal=0x0c000000|((source.ENTRY>>2)&0x3ffffff);calls=[0x2d4b0+i for i in range(0,end-0x15000000,4) if struct.unpack_from('>I',rom,0x2d4b0+i)[0]==jal]
 pointers=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
 report=dict(cases=cases,streams=len(programs),observed_words=[len(v) for v in seen],jal_rom_sites=calls,literal_pointer_rom_sites=pointers,provider_snapshots_per_case=2,private=True,c_match_credit=0,complete_callers_and_sdk_execution_open=True)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
