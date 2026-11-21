"""Original instruction evidence for the transition's noncanonical return paths."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,os,struct,sys
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=Path(os.environ.get('CBFD_AUDIT_OUTPUT',root/'conker/build/camera-transition-return-audit'))
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_trig_match import operation as fp
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
@dataclass(frozen=True)
class Case:phase:int=0
def run():
 out.mkdir(parents=True,exist_ok=True)
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(root/'conker/build/conker.us.elf').read_bytes()
 CAMERA=0x30000;LERP=0x15048720;ANGLE=0x15048A70
 helpers={};receipts=[]
 for entry,n in((LERP,14),(ANGLE,24)):
  at=entry-0x15000000+0x2D4B0;raw=rom[at:at+4*n];p=elf_slot_offset(elf,entry,4*n);assert elf[p:p+4*n]==raw
  words=struct.unpack('>%dI'%n,raw);writers=set()
  for w in words:
   op,fn,rt,rd=w>>26,w&63,w>>16&31,w>>11&31
   if op in(9,13,15,35):writers.add(rt)
   elif op==3:writers.add(31)
   elif op==0 and fn in(33,35,37):writers.add(rd)
   elif op==0:assert fn in(0,8),hex(w)
   elif op==17:assert (w>>21&31)in(4,8,16),hex(w)
   else:assert op in(4,43,49,57),hex(w)
  assert 2 not in writers,(hex(entry),writers)
  helpers[entry]=words;receipts.append({'entry':hex(entry),'words':n,'original_equals_current':True,'GPR_write_set':sorted(writers),'V0_written':False,'raw_sha256':hashlib.sha256(raw).hexdigest()})
 class FloatHelper(FactoryOracle):
  def __init__(self,seed,factor,start,target,angle_words=None):
   memory={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
   super().__init__(helpers[LERP],memory,Case(),entry=LERP,s={},arguments=(0,),connected=dict(zip(range(ANGLE,ANGLE+96,4),helpers[ANGLE]if angle_words is None else angle_words)))
   self.r[2]=seed;self.r[6]=target;self.f[12]=factor;self.f[14]=start
  def record_call(self,t):
   assert t==ANGLE;args=(self.f[12],self.f[14]);self.calls.append((t,args));self.events.append(('CALL',t,args))
  def hook(self,t):raise AssertionError(('unconnected helper',hex(t)))
 cases=0
 for seed,factor,start,target in itertools.product((0x50000,0x51004,0x80048000),(0.,.25,1.),(-181.,0.,180.,181.,720.),(-181.,0.,180.,181.)):
  f,a,b=map(bits,(factor,start,target));m=FloatHelper(seed,f,a,b).run();delta=fp(a,b,'sub')
  if floating(delta)>180.:a=fp(a,bits(360.),'sub')
  elif floating(delta)<=-180.:b=fp(b,bits(360.),'sub')
  expected=fp(bits(start),fp(fp(b,a,'sub'),f,'mul'),'add')
  assert m.r[2]==seed and m.f[0]==expected and m.r[29]==STACK,(seed,factor,start,target,m.r[2],m.f[0],expected)
  cases+=1
 START,END=0x15128348,0x151283A0
 words=struct.unpack_from('>%dI'%((END-START)//4),rom,START-0x15000000+0x2D4B0)
 tail_cases=0
 for done,seed,remaining,ticks in itertools.product((0,1),(0x50000,0x51004,0x80048000),(0,1,32767,32768,65535),(0,1,0x7FFFFFFF,0xFFFFFFFF)):
  memory={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
  memory.update({CAMERA+i:(i*29+0x35)&255 for i in range(0xA00)})
  put(memory,STACK+0x28,done);put(memory,CAMERA+0x840,remaining,2);put(memory,0x800BE9E4,ticks);put(memory,0x800A35A8,0x4479C000)
  expected=dict(memory)
  if done:
   put(expected,CAMERA+0x834,0,2);put(expected,CAMERA+0x7F4,0,2);put(expected,CAMERA+0x84,read(expected,CAMERA+0x84)|8);put(expected,CAMERA+0x820,read(expected,0x800A35A8));answer=seed
  else:
   value=((remaining-ticks)&65535);value=0 if value&0x8000 else value;put(expected,CAMERA+0x840,value,2);answer=1
  m=FactoryOracle(words,dict(memory),Case(),entry=START,s={},arguments=(0,),connected={END:0})
  m.r[16]=CAMERA;m.r[17]=CAMERA+0x7F4;m.r[2]=seed;m.code=WindowCode(m.code,m);m.code.ends=(END,)
  try:m.run();raise AssertionError('missing tail boundary')
  except WindowBoundary:pass
  assert m.memory==expected and m.r[2]==answer,(done,hex(seed),remaining,ticks,hex(m.r[2]),hex(answer))
  tail_cases+=1
 changed=list(helpers[ANGLE]);assert changed[-1]==0;changed[-1]=0x00001025
 control=FloatHelper(0x50000,bits(.25),bits(181.),bits(0.),changed).run()
 assert control.r[2]==0,'The clobbered-return control was ineffective'
 call=struct.unpack_from('>4I',rom,0x15128568-0x15000000+0x2D4B0)
 assert call==(0x0D44A00C,0x02002025,0x50400004,0x8E02002C)
 r={'helpers':receipts,'connected_float_helper_cases':cases,'original_tail_window_cases':tail_cases,'effective_controls':['angle-helper-clobbered-V0'],
  'tail_start':hex(START),'tail_end':hex(END),'caller_start':'0x15128568','caller_words':[f'{w:08x}'for w in call],
  'measured_returns':{'forced_counter_or_zero_state':0,'active_noncomplete':1,'completed_transition':'V0 retains the primary-actor pointer from 0x15128204 through both final angle helpers','unrecognized_state':'V0 retains the loaded unsigned state'},
  'inference':'The observed return values are not a canonical Boolean ABI. Missing-return controls are diagnostic only and do not establish the original C source. Defined C has not matched this whole function.',
  'scope':'Original completion tail and actual original/current angle helpers; no complete transition/caller/native/gameplay acceptance.',
  'source_installed':False,'matching_credit':0}
 (out/'return-ABI-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
 return r

if __name__=='__main__':run()
