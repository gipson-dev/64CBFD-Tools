"""Independent bounded model and guest fixtures for the motion table."""
from pathlib import Path
import itertools,json,os,struct
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-motion-table-150c8350-screen'
s={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
entry=0x150c8350;table=0x30000
truth=list(struct.unpack_from('>105I',(root/'conker/conker.us.bin').read_bytes(),0xf5800))
rawfile=Path(os.environ.get('MOTION_TABLE_RAW_OBJECT',out/'selected.o'))
guardfile=Path(os.environ.get('MOTION_TABLE_GUARD_OBJECT',out/'guarded.o'))
programs={'retail':truth,'raw':bound_blob(*payload(rawfile,'func_150C8350'),s),'guarded':bound_blob(*payload(guardfile,'func_150C8350'),s)}
assert programs['guarded']==truth

def signed(x,n):return ((x&((1<<n)-1))^(1<<(n-1)))-(1<<(n-1))
def fixture(pattern,ticks,half,seed):
 m={STACK+i:(i*17+seed*11+0xa5)&255 for i in range(-256,128)};m.update({table+i:(i*19+seed*7+0x59)&255 for i in range(100)});put(m,s['D_800BE4E0'],table);put(m,s['D_800BE9E4'],ticks);m[s['D_800BE9A0']]=half
 triples=((0,0,0,0),(-32768,-1,-128,-32768),(32767,32767,127,32767),(1280,-16,1,256),(-1,16,-1,-256),(1279,-200,2,200),(10,300,-3,100),(300,100,4,300))
 for i in range(10):
  pos,cur,direction,target=triples[(pattern+i*seed)%len(triples)];m[table+i*10+2]=direction&255;put(m,table+i*10+4,pos&65535,2);put(m,table+i*10+6,cur&65535,2);put(m,table+i*10+8,target&65535,2)
 return m
def model(initial):
 m=initial.copy()
 def ptr(i):return (read(m,s['D_800BE4E0'])+10*i)&0xffffffff
 def h(p):return signed(read(m,p,2),16)
 for i in range(10):
  p=ptr(i);current=h(p+6);target=h(p+8)
  if current!=target:
   if current<0:target=-target
   difference=target-current;step=signed(read(m,s['D_800BE9E4'])<<4,32)
   value=target if abs(difference)<step else signed(current+(step*(-1 if difference<0 else 1)),32)
   put(m,p+6,value&65535,2);p=ptr(i);current=h(p+6)
  direction=signed(m[p+2],8);half=m[s['D_800BE9A0']];position=h(p+4)
  put(m,p+4,(position+current*direction*half)&65535,2);p=ptr(i);position=h(p+4)
  if position>=0x500:
   put(m,p+4,(position-0x500)&65535,2);p=ptr(i);put(m,p+4,(0x500-h(p+4))&65535,2);p=ptr(i);m[p+2]=(-signed(m[p+2],8))&255;p=ptr(i)
   if h(p+4)>=0x500:put(m,p+4,0x4ff,2)
  elif position<0:
   put(m,p+4,(-position)&65535,2);p=ptr(i);m[p+2]=(-signed(m[p+2],8))&255;p=ptr(i)
   if h(p+4)<0:put(m,p+4,0,2)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+128}
def accesses(m):return [v for v in m.trace if not STACK-256<=v[1]<STACK+128]
