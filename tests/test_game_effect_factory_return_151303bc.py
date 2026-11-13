"""Test the pointer-return ABI of the 12-word factory wrapper."""
import itertools,subprocess,unittest
from dataclasses import dataclass
from tools.experiments import game_effect_factory_return_151303bc as packet
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY=0x151303bc;INNER=0x15130374
@dataclass(frozen=True)
class Case:
 phase:int=0;arg0:int=0;selector:int=0;size:int=0;answer:int=0
class Machine(FactoryOracle):
 def __init__(self,ws,c):
  self.c=c;memory={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-512,512)}
  super().__init__(ws,memory,c,entry=ENTRY,s={},arguments=(c.arg0,c.selector,c.size))
 def record_call(self,t):
  assert t==INNER;self.calls.append((t,tuple(self.arguments(5))))
 def hook(self,t):
  assert t==INNER
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.r[2]=self.c.answer

def words(path):
 raw,refs=packet.payload(path);return bound_blob(raw,refs,{'func_15130374':INNER})
def native():
 src=packet.MANIFEST['selected_source'];fn=body(src,packet.NAME)
 source='#include <ultra64.h>\nvoid *func_15130374(void *, u8, s32, u8, s32);\n'+fn.replace(packet.NAME+'(','selected(',1)
 source+='''
 static u32 selector,size,answer,broken;
 void *func_15130374(void *p,u8 s,s32 n,u8 a,s32 b){if((u32)p!=0x30000u||s!=(u8)selector||(u32)n!=size||a!=255||b!=0)broken=1;return (void*)answer;}
 static void *wrong(void *p,u8 s,s32 n){func_15130374(p,s,n,255,0);return (void*)0;}
 typedef void *(*Routine)(void *,u8,s32);
 static int check(Routine f){u32 i,j,k;u32 values[4]={0,1,0x80000000u,0xffffffffu};for(i=0;i<4;i++)for(j=0;j<4;j++)for(k=0;k<4;k++){selector=values[i];size=values[j];answer=values[k];broken=0;if((u32)f((void*)0x30000u,(u8)selector,(s32)size)!=answer||broken)return 1;}return 0;}
 static int run(void){if(check(selected))return 1;if(!check(wrong))return 2;return 0;}
 '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 file=packet.OUT/'native.c';file.write_text(source)
 for opt in ('-O0','-O2','-O3'):
  exe=packet.OUT/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(file),'-o',str(exe)],cwd=packet.ROOT,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr)
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0,(opt,r.returncode,r.stderr)
 return {'profiles':3,'cases_per_profile':64,'effective_negative_controls':1}
class EffectFactoryReturnTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_abi(self):
  ws=[words(self.state[k]) for k in ('before','after','retail','generated','generic')];self.assertTrue(all(x==ws[0] for x in ws))
  count=0
  for phase,selector,size,answer in itertools.product((0,8),(0,1,0x100,0x123456ff),(0,1,0x80000000,0xffffffff),(0,1,0x80000000,0xffffffff)):
   c=Case(phase,0x30000,selector,size,answer)
   for w in ws:
    m=Machine(w,c).run();self.assertEqual(m.calls,[(INNER,(c.arg0,c.selector&255,c.size,255,0))]);self.assertEqual(m.r[2],answer)
   count+=1
  self.assertEqual(count,128)
 def test_native_c_return(self):self.assertEqual(native(),{'profiles':3,'cases_per_profile':64,'effective_negative_controls':1})
if __name__=='__main__':unittest.main()
