"""Connected transaction and packet-builder execution with modeled SI providers."""
from pathlib import Path
from dataclasses import dataclass
import importlib.util,itertools,json
from tools.tests import game_controller_pak2_packet_guest as pkg
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
S=pkg.symbols;PIF=pkg.PIF;BUFFER=pkg.BUFFER;MQ=0x310000
names=('__osSiGetAccess','__osSiRelAccess','__osSiRawStartDma','osRecvMesg','__osContDataCrc','__osPfsGetStatus','__osContAddressCrc')
addr={name:S[name] for name in names}; by_addr={v:k for k,v in addr.items()}
@dataclass(frozen=True)
class Case:
 kind:str;channel:int;address:int;force:int;scenario:str;phase:int=0
def fixture(c):
 m=pkg.fixture(c);m.update({MQ+i:0 for i in range(64)});m.update({S['__osContLastCmd']+i:0xa5 for i in range(4)})
 put(m,STACK+16,c.force);return m
class Machine(pkg.Machine):
 def __init__(self,words,child,c,m):
  self.case=c;self.kind=c.kind;self.attempt=0
  entry=S['__osContRam'+c.kind.capitalize()+'2'];pentry=S['__osPackRam'+c.kind.capitalize()+'Data2']
  connected={pentry+4*i:w for i,w in enumerate(child)}
  FactoryOracle.__init__(self,words,m,c,entry=entry,s=S,arguments=(MQ,c.channel,c.address,BUFFER),connected=connected)
 def record_call(self,t):
  packet=S['__osPackRam'+self.kind.capitalize()+'Data2']
  if t==packet:n=3 if self.kind=='write' else 2
  else:n={'__osSiGetAccess':0,'__osSiRelAccess':0,'__osSiRawStartDma':2,'osRecvMesg':3,'__osContDataCrc':1,'__osPfsGetStatus':2,'__osContAddressCrc':1}[by_addr[t]]
  self.calls.append((t,tuple(self.arguments(n))))
 def hook(self,t):
  name=by_addr[t];a=self.calls[-1][1];value=0
  if name=='__osContAddressCrc':value=pkg.crc(a[0])
  elif name=='__osSiRawStartDma':
   assert a[1]==PIF
   if a[0]==0:
    self.attempt+=1
    packet=PIF+self.case.channel
    rx=0x80 if self.case.scenario=='noresponse' else 0x40 if self.case.scenario=='overrun' else 0
    self.memory[packet+2]=rx
    for i in range(32):self.memory[packet+6+i]=(i*7+0x29)&255
    bad=self.case.scenario in ('badcrc','status') or self.case.scenario=='retry' and self.attempt==1
    self.memory[packet+38]=0xa5 if bad else 0x5a
  elif name=='__osContDataCrc':value=0x5a
  elif name=='__osPfsGetStatus':value=7 if self.case.scenario=='status' else 0
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.r[2]=value
def main():
 count=0
 for kind in ('read','write'):
  name='__osContRam'+kind.capitalize()+'2';child='__osPackRam'+kind.capitalize()+'Data2';owner='generated_contram'+kind+'2'
  pairs=[]
  for parent_obj,child_obj in ((pkg.out/(name+'-retail.o'),pkg.out/(child+'-retail.o')),*[(pkg.out/(owner+'-'+suffix+'.o'),)*2 for suffix in ('after','generated','generic')]):
   pairs.append((bound_blob(*payload(parent_obj,name),S),bound_blob(*payload(child_obj,child),S)))
  for channel,address,force,scenario in itertools.product((0,1,3),(0,3,7),(0,1),('success','retry','badcrc','status','noresponse','overrun')):
   c=Case(kind,channel,address,force,scenario);initial=fixture(c);results=[]
   for w,ch in pairs:results.append(Machine(w,ch,c,initial.copy()).run())
   early=kind=='write' and force!=1 and 0<address<7
   attempts=0 if early else 4 if scenario in ('badcrc','overrun') else 2 if scenario=='retry' else 1
   ret=0 if early or scenario in ('success','retry') else 7 if scenario=='status' else 8 if scenario=='noresponse' else 4
   for m in results:
    assert m.r[2]==ret and m.attempt==attempts,(c,m.r[2],m.attempt)
    calls=[by_addr.get(t,'packet') for t,a in m.calls]
    assert calls.count('__osSiGetAccess')==(not early) and calls.count('__osSiRelAccess')==(not early)
    assert calls.count('__osSiRawStartDma')==(attempts+1 if attempts else 0)
    assert calls.count('osRecvMesg')==(attempts+1 if attempts else 0)
    assert calls.count('packet')==(not early)
    output=bytes(m.memory[BUFFER+i] for i in range(32));old=bytes(initial[BUFFER+i] for i in range(32))
    expected=bytes((i*7+0x29)&255 for i in range(32)) if kind=='read' and ret==0 and not early else old
    assert output==expected,(c,'output')
   assert all(m.calls==results[0].calls and m.memory==results[0].memory for m in results[1:]),c
   count+=1
 report={'cases':count,'streams':4,'connected_real_packet_builder':True,'si_dma_crc_status_modeled':True,'max_attempts':4}
 (pkg.out/'transaction-guest.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
if __name__=='__main__':main()
