"""Bounded original caller windows; private scalar semantics, not byte matching.

Windows begin from explicit seeded live-ins, not whole-routine reachability.
The third window receives A0 from the preceding branch delay slot as a fixture
live-in. Only the callee private frame is excluded from memory comparison;
caller stack locals and outgoing argument homes remain observable.
"""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,re,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_scalar_velocity_smoothing_oracle import ENTRY,corpus,reference,f32
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_four_head_lookup_match import payload
r=o=rom=None;OWNER=0x30000
windows=[('global_xyz','FDD70.s',0x150D0A3C,0x150D0AD4),('stack_fixed','15B5F0.s',0x1512E3C8,0x1512E43C),('stack_dynamic','15B5F0.s',0x1512E3F8,0x1512E43C)]
@dataclass(frozen=True)
class Case:phase:int=0
class Caller(FactoryOracle):
 def __init__(self,words,memory,phase,start,code,end):
  super().__init__(words,memory,Case(phase),entry=start,s={},arguments=(0,),connected=code)
  self.code=WindowCode(self.code,self);self.code.ends=(end,);self.entry_home=STACK+phase
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==50:self.condition=floating(self.f[w>>11&31])==floating(self.f[w>>16&31])
  else:super().execute(w)
 def record_call(self,t):
  assert t==ENTRY,hex(t)
  a=tuple(self.arguments(6));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):raise AssertionError(('Unowned helper',hex(t)))
def window(source,start,end):
 data=(r/'conker/asm'/source).read_bytes();rows={int(pc,16):(int(off,16),int(w,16))for off,pc,w in re.findall(rb'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',data)}
 result={}
 for pc in range(start,end,4):
  off,w=rows[pc];assert struct.unpack_from('>I',rom,off)[0]==w;result[pc]=w
 return result,hashlib.sha256(data).hexdigest()
def fixture(kind,row,phase):
 p,t,v,k,d,dt=row;home=STACK+phase
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,288)}
 m.update({OWNER-16+i:(i*29+0x59)&255 for i in range(0x820)})
 m.update({0x800888B0+i:(i*31+0x7B)&255 for i in range(0x50)})
 put(m,OWNER+0x7B4,bits(dt));put(m,home+16,bits(3));put(m,home+20,bits(2))
 args=[]
 if kind=='global_xyz':
  for i in range(3):
   pos=0x800888C0+4*i;vel=0x800888D8+4*i;target=0x800888CC+4*i
   put(m,pos,bits(f32(p+i*.5)));put(m,vel,bits(v));put(m,target,bits(f32(t-i*.25)))
   args.append((pos,read(m,target),vel,bits(4),bits(6),bits(dt)))
 else:
  put(m,home+0x48,bits(p));put(m,OWNER+0x25C,bits(v));put(m,OWNER+0x354,bits(2.5));put(m,OWNER+0x3B4,bits(k));put(m,OWNER+0x3B8,bits(d))
  args=[(home+0x48,bits(t),OWNER+0x25C,bits(5)if kind=='stack_fixed'else bits(k),bits(9)if kind=='stack_fixed'else bits(d),bits(dt))]
 expected=dict(m);snaps=[]
 for a in args:
  assert all(address%4==0 and not home-24<=address<home+24 for address in (a[0],a[2])),a
  put(expected,home+16,a[4]);put(expected,home+20,a[5]);expected,snap=reference(expected,a);snaps.append(snap)
 if kind!='global_xyz':
  out=f32(floating(read(expected,OWNER+0x354))+floating(read(expected,home+0x48)));put(expected,OWNER+0x2FC,bits(out));put(expected,OWNER+0x344,bits(f32(out-floating(read(expected,OWNER+0x354)))))
 return m,args,expected,snaps
def machine(kind,initial,row,phase,code,start,end,callee):
 connected=dict(code);connected.update(zip(range(ENTRY,ENTRY+len(callee)*4,4),callee));connected[end]=0
 body=[code[pc]for pc in range(start,end,4)]
 m=Caller(body,initial,phase,start,connected,end);m.r[16]=OWNER
 if kind=='global_xyz':m.r[2]=0x800888CC
 else:m.f[16]=bits(row[1]);m.r[4]=STACK+phase+0x48
 m.before=m.r[:];m.before_f=m.f[:]
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Caller boundary not reached')
 assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30))and m.f[20:]==m.before_f[20:]
 return m
def qualify(root,output,candidate="selected"):
 global r,o,rom
 r=Path(root).resolve();o=Path(output).resolve()
 if not o.is_relative_to(r/"conker/build"):raise ValueError("Caller output must stay inside consumer build")
 rom=(r/"conker/conker.us.bin").read_bytes()
 retail=list(struct.unpack_from('>54I',rom,0x76A60));raw,relocs=payload(o/(candidate+'.o'),'func_150495B0');assert not relocs
 selected=list(struct.unpack('>%dI'%(len(raw)//4),raw));assert len(selected)==55
 report=[];controls={};total=0
 for kind,source,start,end in windows:
  code,source_hash=window(source,start,end);calls=snaps=0;seen=set()
  for row,phase in itertools.product(corpus(),(0,8)):
   initial,args,expected,decisions=fixture(kind,row,phase);home=STACK+phase
   visible=lambda m:{a:v for a,v in m.items()if not home-24<=a<home}
   for label,callee in [('retail',retail),('private_c',selected)]:
    m=machine(kind,initial,row,phase,code,start,end,callee)
    assert m.calls==[(ENTRY,a)for a in args],(kind,label,m.calls,args)
    assert visible(m.memory)==visible(expected),(kind,label,row,phase,[(hex(a),m.memory.get(a),v)for a,v in expected.items()if not home-24<=a<home and m.memory.get(a)!=v][:12])
    seen.update(pc for pc in m.visits if start<=pc<end);total+=1
   calls+=len(args);snaps+=sum(decisions)
  for control in ('missing_dt_delay','wrong_damping_home'):
   altered=dict(code)
   for pc,w in altered.items():
    if w>>26==57 and w>>21&31==29 and (w&65535)==(20 if control=='missing_dt_delay'else 16):
     altered[pc]=0 if control=='missing_dt_delay'else (w&~65535)|24
   assert altered!=code
   killed=False
   for row in corpus()[:12]:
    initial,args,expected,_=fixture(kind,row,0);m=machine(kind,initial,row,0,altered,start,end,selected)
    addresses=[a[0]for a in args]+[a[2]for a in args]
    if any(read(m.memory,a)!=read(expected,a)for a in addresses):killed=True;break
   assert killed,(kind,control);controls[kind+':'+control]=True
  report.append(dict(name=kind,source=source,source_SHA256=source_hash,start=hex(start),end_exclusive=hex(end),original_window_words=len(code),reachable_window_words=len(seen),cases=len(corpus())*2,calls_per_program=calls,snap_calls=snaps,caller_stack_position=kind!='global_xyz',fifth_sixth_home_offsets=[16,20],stack_position_offset=72 if kind!='global_xyz'else None,all_root_pointers_outside_outgoing_homes=True,all_public_bytes_and_caller_locals_checked=True,original_and_private_c_equal=True))
 q=dict(success=True,private_only=True,installed=False,matching_credit=0,actual_caller_windows=3,actual_call_sites=5,window_executions=total,windows=report,controls=controls,full_caller_reachability_claimed=False,all_67_callers_qualified=False,hardware_FCSR_claimed=False,return_ABI_global_claimed=False,root_raw_SHA256=hashlib.sha256(raw).hexdigest())
 (o/'caller-qualification.json').write_text(json.dumps(q,indent=2)+'\n');return q
