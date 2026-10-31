"""Fixed floating argument packet, original empty stub, and bounded guest ABI."""
from pathlib import Path
import itertools,json,struct,subprocess
from tools.experiments import game_effect_debug_packet_alt_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD
STUB,CONSTANT=0x151A11CC,0x800A8D24
SYMS=dict(D_800A8D24=CONSTANT,func_151A11CC=STUB)
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,1,0x80000001,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345)

def fixture(phase=0,tone=0x4001374C,flags=0x80000001,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 put(m,s['D_800A8D24'],tone);put(m,STACK+phase+16,flags)
 return m

def expected(x,y,z,variant,flags,tone):
 return (x,y,z,0x43230000,tone,160,75,1055,1270,1,tone,135,68,1055,1270,2,1,tone,70,66,1055,1270,7,65,4,1,variant&255,flags&0xFFFFFFFF)

class Oracle(TimingOracle):
 def __init__(self,words,memory,values=(0,0x80000000,1,255),phase=0,entry=source.ENTRY,s=SYMS,connected=None,fault=None):
  self.s,self.trace=s,[]
  super().__init__(words,memory,phase=phase,entry=entry,arguments=(0xBABA0000,0xCCCC1111,values[2],values[3]),connected=connected)
  self.f[12],self.f[14]=values[:2];self.root_fault=fault
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  assert t==self.s['func_151A11CC'],hex(t)
  args=(self.f[12],self.f[14],self.r[6],self.r[7],*(self.get(self.r[29]+4*i,4) for i in range(4,28)))
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t==self.s['func_151A11CC']
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def linked(obj,label,entry=source.ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>58I',sections(p.with_suffix('.elf'))['.text'][1][:232]))

def final_state(m):return m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.calls

def guest_suite():
 count=cuts=delaycuts=0;seen=set();raw_checks=0
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else dict(D_800A8D24=0x81007FFC+j*0x10000,func_151A11CC=entry+0x10000)
  images=[linked(o/n,'packet-rebase-%d-%d'%(j,k),entry,s)for k,n in enumerate(('original-func_151A0F28.o','qualified-padded.o','make-shadow/src/game/generated_1CC440.c.o','selected-final.o'))]
  assert images[0]==images[1]==images[2]
  for pattern,variant,flags,phase in itertools.product(range(12),(0,1,127,128,255,0x12345680,0xFFFFFFFF),(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,8)):
   x,y,z=(FLOATS[(pattern+i)%12]for i in range(3));tone=FLOATS[(pattern+5)%12];initial=fixture(phase,tone,flags,s);values=(x,y,z,variant)
   models=[Oracle(w,initial,values,phase,entry,s).run()for w in (images[0],images[1],images[3])]
   assert models[0].calls==[(s['func_151A11CC'],expected(x,y,z,variant,flags,tone))]
   assert complete(models[0])==complete(models[1]) and models[0].trace==models[1].trace
   assert final_state(models[0])==final_state(models[2]);seen.update(models[0].visits);count+=1;raw_checks+=1
  if j==0:
   for variant in range(256):
    initial=fixture();values=(0x7FA12345,0x80000000,1,0xABCD0000|variant);models=[Oracle(w,initial,values).run()for w in (images[0],images[1],images[3])]
    assert complete(models[0])==complete(models[1]) and final_state(models[0])==final_state(models[2])
    assert models[0].calls==[(STUB,expected(*values,0x80000001,0x4001374C))];count+=1;raw_checks+=1
   for phase in (0,8):
    initial=fixture(phase);good=Oracle(images[0],initial,phase=phase).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in images[:2]:
      model=Oracle(w,initial,phase=phase,fault=cut)
      try:model.run()
      except faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective packet access-prefix control')
      models.append(model)
     a,b=models;assert complete(a)==complete(b) and a.trace==b.trace and (a.current_pc,a.delay_of,a.root_accesses)==(b.current_pc,b.delay_of,b.root_accesses)
     cuts+=1;delaycuts+=a.delay_of is not None
   initial=fixture();bad=dict(initial)
   for i in range(4):bad.pop(CONSTANT+i)
   failed=[]
   for w in (images[0],images[1],images[3]):
    m=Oracle(w,bad)
    try:m.run()
    except AssertionError as error:assert error.args[0][0]=='unmapped read',error
    else:raise AssertionError('Ineffective unmapped-constant control')
    failed.append(m)
   assert complete(failed[0])==complete(failed[1]) and failed[0].memory!=failed[2].memory
 assert len(seen)==58*3
 return dict(cases=count,executions=count*3,visited_words=58,independent_rebases=3,all_three_normalized_images_equal=True,raw_final_state_cases=raw_checks,all256_variants=True,float_bits_including_signaling_NaN=True,all28_arguments_checked=True,fault_cuts=cuts,delay_fault_cuts=delaycuts,raw_fault_order_claim=False,effective_raw_fault_order_difference_controls=1)

def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes();stub=list(struct.unpack_from('>6I',rom,0x1CE67C));assert stub==list(struct.unpack_from('>6I',elf,source.elf_slot_offset(elf,STUB,24)))
 assert source.function_payload(o/'after-owner.o','func_151A11CC')==source.function_payload(o/'before-owner.o','func_151A11CC')
 connected=dict(zip(range(STUB,STUB+24,4),stub));images=[linked(o/n,'packet-connected-%d'%i)for i,n in enumerate(('original-func_151A0F28.o','qualified-padded.o','selected-final.o'))];count=0;seen=set()
 for pattern,variant,flags,phase in itertools.product(range(12),(0,255,0x12345680),(0,0xFFFFFFFF),(0,8)):
  values=(*[FLOATS[(pattern+i)%12]for i in range(3)],variant);tone=FLOATS[(pattern+3)%12];initial=fixture(phase,tone,flags)
  models=[Oracle(w,initial,values,phase,connected=connected).run()for w in images];a,b,raw=models
  assert complete(a)==complete(b) and a.trace==b.trace and final_state(a)==final_state(raw)
  args=expected(*values,flags,tone);assert a.calls==[(STUB,args)]
  sp=STACK+phase-120
  for i,v in enumerate(args):assert read(a.memory,sp+i*4)==v
  # The original empty helper homes the first two floats and a2/a3, then returns.
  assert a.f[12]==values[0] and a.f[14]==values[1]
  for at,v in initial.items():
   if not sp<=at<STACK+phase+16:assert a.memory[at]==v
  seen.update(a.visits);count+=1
 assert len(seen&set(connected))==6
 return dict(cases=count,executions=count*3,original_helper_words=6,visited_helper_words=6,all28_arguments_and_homes=True,original_empty_stub_preserved=True,raw_final_state_equal=True,whole_memory_fences=True,gameplay_or_hardware_claim=False)

def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom)
 def sites(va):return [hex(i*4)for i,w in enumerate(ws)if w==0x0C000000|(va>>2&0x3FFFFFF)]
 assert sites(source.ENTRY)==[] and not any(w==source.ENTRY for w in ws)
 helpers=sites(STUB);assert helpers==['0x1ce3c0','0x1ce4a8','0x1ce664'] and not any(w==STUB for w in ws)
 # All helper slots use the same first-four register homes; widening its unused
 # fixed signature changes no emitted instructions, bindings, data or callers.
 for name in ('before-owner.o','after-owner.o','qualified-padded.o','make-shadow/src/game/generated_1CC440.c.o'):
  body,rs=source.function_payload(o/name,'func_151A11CC');assert not rs and struct.unpack('>6I',body)==(0xE7AC0000,0xE7AE0004,0xAFA60008,0xAFA7000C,0x03E00008,0)
 return dict(root_aligned_JAL_sites=[],root_aligned_literal_pointers=0,helper_aligned_JAL_sites=helpers,helper_aligned_literal_pointers=0,compatible_full28_argument_signature=True,helper_six_words_preserved_in_four_objects=True,unreachability_claim=False,complete_indirect_reference_claim=False)

def controls():
 b=source.SELECTED
 changes={'x_y':('x, y, value','y, x, value'),'wrong_z':('x, y, value','x, y, x'),'wrong_scale':('163.0f','162.0f'),'wrong_tone':('163.0f, D_800A8D24','163.0f, 0.0f'),'constant160':('160, 75','159, 75'),'constant75':('160, 75','160, 74'),'kind2':('1270, 2, 1','1270, 3, 1'),'constant135':('135, 68','134, 68'),'constant70':('70, 66','71, 66'),'constant7':('1270, 7, 65','1270, 6, 65'),'variant0':('1, variant, flags','1, 0, flags'),'flags':('variant, flags)','variant, flags ^ 1)')}
 out={n:b.replace(a,z)for n,(a,z)in changes.items()};assert all(v!=b for v in out.values());return out

def native_harness():
 types=source.HEADERS.split('void func_151A11CC(',1)[1].split(')',1)[0].split(', ')
 signature='void func_151A11CC('+', '.join(t+' a'+str(i)for i,t in enumerate(types))+')'
 floats={0,1,2,3,4,10,17}
 t=source.HEADERS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(f32)==4&&sizeof(s32)==4)?1:-1];
static u32 wanted[28],actual[28],calls,error;
f32 D_800A8D24;
static u32 word(f32 v){u32 w;__builtin_memcpy(&w,&v,4);return w;}
static f32 real(u32 v){f32 f;__builtin_memcpy(&f,&v,4);return f;}
'''+signature+'{u32 i;calls++;\n'
 for i in range(28):t+='actual[%d]=%s;\n'%(i,'word(a%d)'%i if i in floats else '(u32)a%d'%i)
 t+='for(i=0;i<28;i++)if(actual[i]!=wanted[i])error=1;}\n'
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,name)+'\n'
 t+=r'''
typedef void(*Submit)(f32,f32,f32,u8,s32);
static const u32 bits[]={0,0x80000000u,0x3F800000u,0xC0200000u,1,0x80000001u,0x7F7FFFFFu,0xFF7FFFFFu,0x7F800000u,0xFF800000u,0x7FC12345u};
static int check(Submit fn){u32 n,p,i;for(n=0;n<65536;n++)for(p=0;p<11;p++){
 u32 x=bits[p],y=bits[(p+1)%11],z=bits[(p+2)%11],tone=bits[(p+5)%11],flags=n*0x1020304u^0x80000001u;
 u32 expected[]={x,y,z,0x43230000u,tone,160,75,1055,1270,1,tone,135,68,1055,1270,2,1,tone,70,66,1055,1270,7,65,4,1,n&255,flags};
 for(i=0;i<28;i++){wanted[i]=expected[i];actual[i]=0xA5A50000u+i;}calls=error=0;D_800A8D24=real(tone);
 fn(real(x),real(y),real(z),(u8)n,(s32)flags);
 if(error||calls!=1||word(D_800A8D24)!=tone)return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(%s))return %d;\n'%(name,20+i)
 return t+'return 0;}\n'+START

def native_suite():
 unit=o/'native-debug-packet.c';unit.write_text(native_harness())
 for opt in ('O0','O2','O3'):
  exe=o/('native-debug-packet-'+opt);q=subprocess.run([*native_command('-'+opt,True),'-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==0,(opt,q.returncode,q.stderr)
 return dict(profiles=['O0','O2','O3'],positive_cases_each=720896,effective_controls=12,UBSan_trapping=True,all65536_variant_inputs=True,all256_narrow_variants=True,eleven_float_patterns=True,all28_arguments_checked=True,original_empty_callee_separately_guest_checked=True,signaling_NaN_native_claim=False)
