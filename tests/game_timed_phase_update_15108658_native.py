"""Actual typed prefix C in native32, scalar reference and RNG mutation controls.

The native gate disables GCC tree sinking: the measured default O2 pass moves
the used-only-on-one-edge subtraction into that edge, removing an inexact flag.
This is a native instrumentation setting, not a change to the IDO/Make profile.
The explicit short-circuit source remains an effective failing control.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_timed_phase_update_15108658_match as p
from tools.tests import game_timed_phase_update_15108658_guest as g
o=p.OUT
from tools.experiments.game_remaining_donor_candidates import function_span
def main():
 source=p.MANIFEST['selected_source'];a,z=function_span(source,'func_15108658');body=source[a:z];lo=source.index('typedef struct {\n    f32 remaining;');hi=source.index('extern f32 D_800BE9A4',lo);types=source[lo:hi]
 header='typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;typedef float f32;\n'+types+'\nextern f32 D_800BE9A4,D_800A2460,D_800A2464;\nf32 func_150ADA68(void);\ns32 func_15108658(PhaseState15108658*,void*);\ntypedef char ABI[sizeof(void*)==4&&sizeof(PhaseState15108658)==188&&sizeof(f32)==4?1:-1];\n'
 offsets={'phaseFlags':28,'displayState':116,'phase':168,'phase.remaining':168,'phase.total':172,'phase.transitionWidth':176,'phase.edgeWidth':180,'phase.cooldown':184}
 for field,off in offsets.items():header+='typedef char offset_'+field.replace('.','_')+'[__builtin_offsetof(PhaseState15108658,'+field+')=='+str(off)+'?1:-1];\n'
 (o/'native-shared.h').write_text(header);rows=[]
 for c in g.cases():rows.append([g.bits(v)for v in(c.remaining,c.total,c.transition,c.edge,c.cooldown,c.delta,c.limit,c.rng)]+[c.mutation,c.fcsr])
 for i in(0,1,4,7):
  for word in(0x7fc12345,0xffc54321,0x7f800000,0xff800000):
   row=[g.bits(v)for v in(10.,20.,2.,1.,0.,.125,.25,.125)]+[0,0];row[i]=word;rows.append(row)
 encoded=',\n'.join('{'+','.join(hex(v)+'u'for v in row)+'}'for row in rows)
 harness=r'''
typedef struct{u32 prefix[8];PhaseState15108658 record;u8 scratch[16];u32 suffix[8];} Arena;
typedef struct{u32 csr,globals[3];u8 bytes[268];} Trace;
static Arena arena;static Trace trace,expectedTrace;static u32 ordinal,initialCSR;static const u32 *current;
static const u32 cases[][10]={CASES};
f32 D_800BE9A4,D_800A2460,D_800A2464;
typedef char ARENA[sizeof(Arena)==268&&sizeof(Trace)==284?1:-1];
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static u32 getCSR(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v));}
__attribute__((noinline,noclone))f32 func_150ADA68(void){u32 i;ordinal++;trace.csr=getCSR();trace.globals[0]=word(D_800BE9A4);trace.globals[1]=word(D_800A2460);trace.globals[2]=word(D_800A2464);for(i=0;i<268;i++)trace.bytes[i]=((u8*)&arena)[i];
 if(current[8]){arena.record.phase.remaining=real(0xc2b60000u);arena.record.phase.cooldown=real(0xc1880000u);D_800A2464=.75f;D_800BE9A4=2.0f;arena.scratch[0]=0x7e;}
 setCSR((initialCSR&~63u)|8u);return real(current[7]);}
__attribute__((noinline,noclone))static f32 sub(f32 a,f32 b){volatile f32 v=a-b;return v;}
static s32 reference(PhaseState15108658*p){f32 remaining=p->phase.remaining;f32 left=sub(p->phase.total,remaining);f32 cooldown;
 if(remaining<p->phase.edgeWidth||left<p->phase.edgeWidth)p->phaseFlags=0;
 else if(p->phase.remaining<p->phase.transitionWidth||left<p->phase.transitionWidth)p->phaseFlags=0x10000;
 else p->phaseFlags=0x20000;
 cooldown=p->phase.cooldown;
 if(cooldown!=0.0f){left=sub(11.0f,cooldown);if(cooldown<D_800A2460||left<D_800A2460){p->phaseFlags=0;p->displayState=-1;}else p->displayState=3;
  p->phase.cooldown=sub(p->phase.cooldown,D_800BE9A4);if(p->phase.cooldown<0.0f){p->phase.cooldown=0.0f;p->displayState=-1;}return 1;}
 p->phase.remaining=sub(p->phase.remaining,D_800BE9A4);if(p->phase.remaining<0.0f)return 0;
 if(p->phaseFlags==0x20000){f32 random=func_150ADA68();if(random<D_800A2464)p->phase.cooldown=11.0f;}return 1;}
static void reset(const u32*c,u32 row){u32 i;static const u32 modes[4]={0,3,2,1};current=c;for(i=0;i<268;i++)((u8*)&arena)[i]=(u8)(i*29+row*11+0x5a);
 arena.record.phase.remaining=real(c[0]);arena.record.phase.total=real(c[1]);arena.record.phase.transitionWidth=real(c[2]);arena.record.phase.edgeWidth=real(c[3]);arena.record.phase.cooldown=real(c[4]);D_800BE9A4=real(c[5]);D_800A2460=.25f;D_800A2464=real(c[6]);ordinal=0;initialCSR=0x1f80u|(modes[c[9]&3]<<13)|(1u<<(row%6));setCSR(initialCSR);}
static s32 fail(u32 row,u32 reason,u32 actual,u32 expected){u32 message[4]={row,reason,actual,expected},nr=4;__asm__ volatile("int $0x80":"+a"(nr):"b"(1),"c"(message),"d"(sizeof(message)):"memory");return 42;}
static s32 main(void){u32 row,i,expectedCSR,expectedCalls,globals[3],actualCSR;s32 result,actual;u8 bytes[268];
 for(row=0;row<sizeof(cases)/sizeof(cases[0]);row++){const u32*c=cases[row];reset(c,row);result=reference(&arena.record);expectedCSR=getCSR();expectedCalls=ordinal;expectedTrace=trace;for(i=0;i<268;i++)bytes[i]=((u8*)&arena)[i];globals[0]=word(D_800BE9A4);globals[1]=word(D_800A2460);globals[2]=word(D_800A2464);
  reset(c,row);actual=func_15108658(&arena.record,arena.scratch);actualCSR=getCSR();if(actual!=result)return fail(row,1,(u32)actual,(u32)result);if(ordinal!=expectedCalls)return fail(row,2,ordinal,expectedCalls);if(actualCSR!=expectedCSR)return fail(row,3,actualCSR,expectedCSR);
  for(i=0;i<268;i++)if(((u8*)&arena)[i]!=bytes[i])return fail(row,4+i,((u8*)&arena)[i],bytes[i]);
  if(word(D_800BE9A4)!=globals[0]||word(D_800A2460)!=globals[1]||word(D_800A2464)!=globals[2])return fail(row,272,0,1);
  if(ordinal)for(i=0;i<sizeof(Trace);i++)if(((u8*)&trace)[i]!=((u8*)&expectedTrace)[i])return fail(row,273+i,((u8*)&trace)[i],((u8*)&expectedTrace)[i]);
 }return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''.replace('CASES','\n'+encoded+'\n');(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 base=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fsignaling-nans','-fno-tree-sink','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Wno-unused-parameter']
 def run(name,function,opt,expected):
  f=o/(name+'.c');f.write_text('#include "native-shared.h"\n'+function+'\n');exe=o/(name+'.exe');cmd=[*base,opt,str(f),str(o/'native-harness.c'),'-o',str(exe)];p=subprocess.run(cmd,text=True,capture_output=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stdout,p.stderr);p=subprocess.run([str(exe)],capture_output=True);diagnostic=list(__import__('struct').unpack('<4I',p.stdout))if len(p.stdout)==16 else p.stdout.hex();(o/(name+'-execution.json')).write_text(json.dumps(dict(exit_code=p.returncode,diagnostic=diagnostic),indent=2)+'\n');assert p.returncode==expected,(name,p.returncode,diagnostic,rows[diagnostic[0]]if isinstance(diagnostic,list)else None);return dict(profile=opt,comparison_exit=p.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('phase-flag','record->phaseFlags = 0x10000;','record->phaseFlags = 0x20000;'),('remaining-gate','phase->remaining < 0.0f','phase->remaining <= 0.0f'),('display-state','record->displayState = -1;','record->displayState = -2;'),('reset-value','phase->cooldown = 11.0f;','phase->cooldown = 12.0f;'),('missing-RNG','func_150ADA68()','0.5f'),('invalid-return','return 0;','return 1;')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 old=p.MANIFEST['short_circuit_control_source'];lo,hi=function_span(old,'func_15108658');controls.append(dict(name='short-circuit-lost-subtraction',**run('control-short-circuit',old[lo:hi],'-O2',42)))
 q=dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),cases_per_profile=len(rows),profiles=profiles,translation_units=2,prefix_bytes=188,arena_bytes=268,all_retained_bytes_and_scratch_canaries_checked=True,all_four_rounding_modes_and_seeded_sticky_flags=True,full_RNG_arena_globals_and_MXCSR_snapshots_equal=True,legal_typed_prefix_and_disjoint_scratch=True,quiet_NaN_and_infinity_native_arguments_checked=True,MIPS_hardware_and_enabled_exceptions_not_qualified=True,strict_aliasing_UBSan_traps_and_LTO_type_errors=True,unused_scratch_parameter_warning_only_suppressed=True,native_only_tree_sinking_disabled_for_full_FENV_gate=True,default_GCC_O2_full_FENV_parity_not_claimed=True,production_IDO_profile_unchanged=True,effective_controls=controls,no_signal_or_trap_counted_as_control=True,source_installed=p.installed(),matching_credit=0)
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
