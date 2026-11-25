"""Execute the selected C through its typed 32-bit direct/callback interfaces."""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests import game_height_interpolation_151155c0_guest as g
from tools.experiments import game_height_interpolation_151155c0_match as p

def main():
 o=p.OUT;source=p.MANIFEST['selected_source'];a,z=function_span(source,'func_151155C0');body=source[a:z]
 a=source.index('typedef struct HeightState151155C0');z=source.index('/* Interpolate signed height',a);types=source[a:z]
 header='typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;\n'+types+'\ns32 func_151155C0(HeightState151155C0 *);\n'
 spans=[('retained00',0,18),('height',18,2),('retained14',20,36),('update',56,4),('packed',60,4),('retained40',64,15),('flags',79,1),('retained50',80,12),('delta',92,2),('retained5E',94,16),('disabled',110,1),('updateFlags',111,1),('retained70',112,12),('origin',124,4),('hold',128,4),('retained84',132,28)]
 assert sorted(at+i for _,at,n in spans for i in range(n))==list(range(160))
 for name,at,n in spans:header+=f'typedef char offset_{name}[__builtin_offsetof(HeightState151155C0,{name})=={at}?1:-1];\ntypedef char width_{name}[sizeof(((HeightState151155C0 *)0)->{name})=={n}?1:-1];\n'
 header+='typedef char exact_extent[sizeof(HeightState151155C0)==160?1:-1];\ntypedef char exact_int[sizeof(s32)==4&&sizeof(s16)==2&&sizeof(u8)==1&&sizeof(void*)==4?1:-1];\n'
 (o/'native-shared.h').write_text(header)
 rows=[c for c in g.cases()if c.divisor]
 rows += [g.Case(flags=f,current=50,origin=50,divisor=7,holdByte=f,rm=f&3)for f in range(256)]
 rows += [g.Case(hold=h,origin=0x80000000 if h&1 else 0x7fffffff,current=-32768,target=32767,divisor=d,holdByte=w,flags=255)for h in(-2147483648,-1,0,1,2147483647)for d in(1,2,255)for w in(0,1,127,255)]
 values=[]
 for c in rows:values.append('{'+','.join(hex(g.u32(v))+'u'for v in(c.current,c.origin,c.target,c.divisor,c.holdByte,c.hold,c.flags,c.seed,c.rm))+'}')
 harness=r'''
typedef struct {u32 height,origin,target,divisor,wait,hold,flags,seed,rm;} Case;
static const Case cases[]={CASES};
static struct {u32 prefix[8];HeightState151155C0 live;u32 suffix[8];} arena;
static u32 read32(const u8 *p){return p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);}
static s32 read16(const u8 *p){return (s16)(u16)(p[0]|((u16)p[1]<<8));}
static void put(u8 *p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(8*i));}
static u32 getCSR(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v));}
static s32 reference(u8 *p){s32 old=read16(p+18),height=old,origin=(s32)read32(p+124),hold=(s32)read32(p+128);u32 packed=read32(p+60);s32 target=(s16)packed,wait=(s32)(packed>>24)+1,candidate=(packed>>16)&255,step,inside=0;
 if(!origin){origin=old;put(p+124,(u32)origin,4);}
 step=(s32)((u32)target-(u32)origin)/candidate;
 if(!hold){candidate=(s32)((u32)height-(u32)step);
  if(origin==height){if(p[79]&4){hold=wait;put(p+128,(u32)hold,4);}}
  else{candidate=(s16)candidate;inside=origin<target?origin<candidate:candidate<origin;
   if(inside){height=candidate;put(p+18,(u32)height,2);hold=(s32)read32(p+128);}
   else{height=(s16)origin;put(p+18,(u32)origin,2);hold=-wait;put(p+128,(u32)hold,4);}
  }
 }
 if(hold>0){candidate=(s16)((u32)height+(u32)step);if(origin<target){if(candidate<target)inside=1;}else if(target<candidate)inside=1;
  hold--;if(inside){height=candidate;hold=wait;}else height=target;put(p+18,(u32)height,2);put(p+128,(u32)hold,4);
 }
 if(hold<0)put(p+128,(u32)(hold+1),4);
 put(p+92,(u32)height-(u32)old,2);return candidate;
}
static s32 main(void){u32 row,mode,i;u8 expected[224];s32 wanted,actual;u32 csr;
 for(row=0;row<sizeof(cases)/sizeof(cases[0]);row++)for(mode=0;mode<2;mode++){
  const Case *c=&cases[row];u8 *p=(u8 *)&arena;
  for(i=0;i<224;i++)p[i]=(u8)(i*29+c->seed*11+row);
  arena.live.height=(s16)c->height;arena.live.origin=(s32)c->origin;arena.live.hold=(s32)c->hold;
  arena.live.packed=(s32)((c->wait<<24)|(c->divisor<<16)|(c->target&65535));arena.live.flags=(u8)c->flags;
  arena.live.update=func_151155C0;for(i=0;i<224;i++)expected[i]=p[i];
  wanted=reference(expected+32);csr=0x1f80u|((c->rm&3)<<13)|(1u<<(row%6));setCSR(csr);
  if(mode){s32(*volatile callback)(HeightState151155C0 *)=arena.live.update;actual=callback(&arena.live);}else actual=func_151155C0(&arena.live);
  if(actual!=wanted||getCSR()!=csr)return 42;
  for(i=0;i<224;i++)if(p[i]!=expected[i])return 42;
 }
 return 0;
}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''.replace('CASES',','.join(values))
 (o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 base=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,function,opt,expected):
  f=o/(name+'.c');f.write_text('#include "native-shared.h"\n'+function+'\n');exe=o/(name+'.exe');cmd=[*base,opt,str(f),str(o/'native-harness.c'),'-o',str(exe)];p=subprocess.run(cmd,capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr);p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==expected,(name,p.returncode,p.stdout,p.stderr)
  return dict(comparison_exit=p.returncode,command=cmd,source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
 profiles={opt:run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')};controls=[]
 mutations=[('flag-bit','& 4) == 4','& 2) == 2'),('divisor','/ candidate;','/ (candidate + 1);'),('origin-sentinel','origin == 0','origin == 1'),('reverse-width','candidate = (s16)candidate;','candidate = (u16)candidate;'),('hold-length','& 255) + 1;','& 255) + 2;'),('delta-sign','(u32)record->height - (u32)previous','(u32)record->height + (u32)previous'),('return-value','return candidate;','return candidate ^ 1;')]
 for name,old,new in mutations:
  assert body.count(old)==1,(name,body.count(old));controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=2*len(rows),profiles=profiles,effective_controls=controls,translation_units=2,record_bytes=160,record_fields_pinned=len(spans),all_retained_bytes_and_canaries_checked=True,direct_and_typed_callback_calls=True,actual_return_candidate_or_divisor_checked=True,all256_flags_and_255_nonzero_divisors=True,all_four_rounding_modes_and_six_sticky_bits=True,signed16_and_signed32_boundaries=True,zero_divisor_excluded_from_portable_C=True,strict_aliasing_and_UBSan_trap=True,LTO_type_mismatch_errors=True,no_signal_or_trap_counted=True,source_installed=p.installed(),matching_credit=0)
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_controls')}),flush=True);return q
if __name__=='__main__':main()
