"""Actual typed 32-bit C, independent scalar FP reference and provider boundaries."""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests import game_local_vector_transform_15117da4_guest as g
from tools.experiments import game_local_vector_transform_15117da4_match as p
def main():
 o=p.OUT;source=p.MANIFEST['selected_source'];a,z=function_span(source,'func_15117DA4');body=source[a:z];a=source.rfind('typedef struct {',0,a);z=source.index('} TransformState15117DA4;',a)+len('} TransformState15117DA4;');types=source[a:z]
 header='''typedef unsigned char u8;typedef short s16;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;typedef float f32;
'''+types+'''
extern s32 D_800BE9F0;extern f32 D_800A2FF4,D_800A2FF8,D_800A2FFC;
u8 *func_151149AC(u32);void func_1511F31C(u8 *);f32 sinf(f32);f32 cosf(f32);
void func_15117DA4(TransformState15117DA4 *,f32,f32,f32,f32[3]);
typedef char ABI[sizeof(void*)==4&&sizeof(s32)==4&&sizeof(s16)==2&&sizeof(f32)==4&&sizeof(TransformState15117DA4)==88?1:-1];
'''
 spans=[('angleX',0,4),('angleY',4,4),('retained08',8,8),('position',16,6),('retained16',22,62),('type',84,2),('retained56',86,2)]
 for name,at,n in spans:header+=f'typedef char offset_{name}[__builtin_offsetof(TransformState15117DA4,{name})=={at}?1:-1];\ntypedef char width_{name}[sizeof(((TransformState15117DA4*)0)->{name})=={n}?1:-1];\n'
 (o/'native-shared.h').write_text(header);cases=g.cases();cases=[c for c in cases if not c.home_mutation]
 for word in(0x7fc12345,0xffc54321,0x7f800000,0xff800000):cases.append(g.Case(angles=(word,g.bits(.5)),kind=0x8005))
 encoded=[]
 for c in cases:
  cell=lambda v:hex(g.u32(v))+'u'
  array=lambda a:'{'+','.join(map(cell,a))+'}'
  encoded.append('{'+','.join([cell(c.kind),cell(c.category),array(c.values),array(c.angles),array(c.position),array(c.trig),cell(c.mode),cell(c.fcsr),cell(c.seed)])+'}')
 harness=r'''
typedef struct{u32 kind,category,values[3],angles[2],position[3],trig[4],mode,csr,seed;} Case;
static const Case cases[]={CASES};
static struct{u32 prefix[8];TransformState15117DA4 first,second;f32 output[3];u32 suffix[8];} arena;
s32 D_800BE9F0;f32 D_800A2FF4,D_800A2FF8,D_800A2FFC;
static const Case *current;static u32 ordinal,trigIndex,bad,initialCSR;
typedef struct{u32 id,arg,csr,globals[4];u8 bytes[252];} Trace;
static Trace actualTrace[6],expectedTrace[6];
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static u32 getCSR(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v));}
static void effect(u32 id,u32 arg){u32 i;Trace *t;if(ordinal>=6){bad=1;return;}t=&actualTrace[ordinal];t->id=id;t->arg=arg;t->csr=getCSR();t->globals[0]=(u32)D_800BE9F0;t->globals[1]=word(D_800A2FF4);t->globals[2]=word(D_800A2FF8);t->globals[3]=word(D_800A2FFC);for(i=0;i<252;i++)t->bytes[i]=((u8*)&arena)[i];ordinal++;
 if(current->mode&1){TransformState15117DA4*p=ordinal&1?&arena.first:&arena.second;p->angleX=3.25f+(f32)ordinal;p->angleY=-4.5f-(f32)ordinal;p->position[0]=(s16)(-300+(s32)ordinal);p->position[1]=(s16)(700-(s32)ordinal);p->position[2]=(s16)(-800+(s32)ordinal);}
 if(current->mode&2)for(i=0;i<3;i++)arena.output[i]=(f32)(i+1)*0.125f+(f32)ordinal;
 if(current->mode&4){D_800A2FF4=1.0f+(f32)ordinal;D_800A2FF8=.125f+(f32)ordinal/16.0f;D_800A2FFC=.25f+(f32)ordinal/32.0f;D_800BE9F0=(s32)0x87654321u;}
 setCSR((initialCSR&~63u)|(1u<<(ordinal%5)));
}
__attribute__((noinline,noclone))u8*func_151149AC(u32 value){effect(1,value);return(u8*)&arena.second;}
__attribute__((noinline,noclone))void func_1511F31C(u8 *object){effect(2,(u32)object);}
__attribute__((noinline,noclone))f32 sinf(f32 angle){effect(3,word(angle));return real(current->trig[trigIndex++]);}
__attribute__((noinline,noclone))f32 cosf(f32 angle){effect(4,word(angle));return real(current->trig[trigIndex++]);}
__attribute__((noinline,noclone))static f32 add(f32 a,f32 b){volatile f32 v=a+b;return v;}
__attribute__((noinline,noclone))static f32 sub(f32 a,f32 b){volatile f32 v=a-b;return v;}
__attribute__((noinline,noclone))static f32 mul(f32 a,f32 b){volatile f32 v=a*b;return v;}
__attribute__((noinline,noclone))static f32 cvt(s16 a){volatile f32 v=(f32)a;return v;}
static void reference(TransformState15117DA4*p,f32 x,f32 y,f32 z,f32*out){f32 angle,s,c,yc,zs,ys,zc,nx,xc,ns,rx,ry,rz,tx;
 if(p->type==0x8006&&D_800BE9F0==53){p=(TransformState15117DA4*)func_151149AC(253);func_1511F31C((u8*)p);x=0.0f;y=D_800A2FF4;z=0.0f;}
 angle=mul(p->angleX,D_800A2FF8);s=sinf(angle);c=cosf(angle);yc=mul(y,c);zs=mul(z,s);out[0]=x;ys=mul(y,s);zc=mul(z,c);out[1]=sub(yc,zs);out[2]=add(ys,zc);
 angle=mul(p->angleY,D_800A2FFC);s=sinf(angle);c=cosf(angle);z=out[2];x=out[0];zs=mul(z,s);nx=real(word(x)^0x80000000u);xc=mul(x,c);zc=mul(z,c);ns=mul(nx,s);out[0]=add(zs,xc);rz=add(zc,ns);rx=out[0];ry=out[1];out[2]=rz;
 tx=cvt(p->position[0]);rx=add(rx,tx);rz=out[2];out[0]=rx;out[1]=add(ry,cvt(p->position[1]));out[2]=add(rz,cvt(p->position[2]));
}
static void reset(const Case*c){u32 i;current=c;for(i=0;i<252;i++)((u8*)&arena)[i]=(u8)(i*29+c->seed*11+0x5a);arena.first.angleX=arena.second.angleX=real(c->angles[0]);arena.first.angleY=arena.second.angleY=real(c->angles[1]);for(i=0;i<3;i++)arena.first.position[i]=arena.second.position[i]=(s16)c->position[i];arena.first.type=arena.second.type=(u16)c->kind;D_800BE9F0=(s32)c->category;D_800A2FF4=7.5f;D_800A2FF8=.25f;D_800A2FFC=.5f;ordinal=trigIndex=bad=0;initialCSR=0x1f80u|((c->csr&3)<<13)|(1u<<(c->seed%6));setCSR(initialCSR);}
static s32 main(void){u32 row,i,n,expectedCSR,expectedGlobals[4];u8 expectedArena[252];
 for(row=0;row<sizeof(cases)/sizeof(cases[0]);row++){const Case*c=&cases[row];reset(c);reference(&arena.first,real(c->values[0]),real(c->values[1]),real(c->values[2]),arena.output);expectedCSR=getCSR();if(bad||trigIndex!=4)return 42;n=ordinal;for(i=0;i<n;i++)expectedTrace[i]=actualTrace[i];for(i=0;i<252;i++)expectedArena[i]=((u8*)&arena)[i];expectedGlobals[0]=(u32)D_800BE9F0;expectedGlobals[1]=word(D_800A2FF4);expectedGlobals[2]=word(D_800A2FF8);expectedGlobals[3]=word(D_800A2FFC);
  reset(c);func_15117DA4(&arena.first,real(c->values[0]),real(c->values[1]),real(c->values[2]),arena.output);if(bad||ordinal!=n||trigIndex!=4||getCSR()!=expectedCSR)return 42;for(i=0;i<252;i++)if(((u8*)&arena)[i]!=expectedArena[i])return 42;for(i=0;i<n*sizeof(Trace);i++)if(((u8*)actualTrace)[i]!=((u8*)expectedTrace)[i])return 42;if((u32)D_800BE9F0!=expectedGlobals[0]||word(D_800A2FF4)!=expectedGlobals[1]||word(D_800A2FF8)!=expectedGlobals[2]||word(D_800A2FFC)!=expectedGlobals[3])return 42;
 }
 return 0;
}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''.replace('CASES','\n'+',\n'.join(encoded)+'\n');(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 base=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fsignaling-nans','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,function,opt,expected):
  f=o/(name+'.c');f.write_text('#include "native-shared.h"\n'+function+'\n');exe=o/(name+'.exe');cmd=[*base,opt,str(f),str(o/'native-harness.c'),'-o',str(exe)];p=subprocess.run(cmd,capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr[-1500:]);p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==expected,(name,p.returncode,p.stdout,p.stderr)
  return dict(command=cmd,comparison_exit=p.returncode,source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
 profiles={opt:run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')};controls=[]
 for name,old,new in [('type-gate','record->type == 0x8006','record->type == 0x8005'),('lookup-selector','func_151149AC(0xFD)','func_151149AC(0xFC)'),('angle-coefficient','record->angleX * D_800A2FF8','record->angleX * D_800A2FFC'),('first-rotation-sign','y * cosine - z * sine','y * cosine + z * sine'),('second-rotation-sign','(-oldX) * sine','oldX * sine'),('translation-axis','record->position[0]','record->position[1]'),('first-trig-provider','sine = sinf(angle);','sine = cosf(angle);')]:
  assert body.count(old)==(2 if name=='first-trig-provider'else 1),name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new,1),'-O2',42)))
 q=dict(cases_per_profile=len(cases),profiles=profiles,effective_controls=controls,translation_units=2,record_fields_pinned=len(spans),record_bytes=88,output_bytes=12,arena_bytes=252,all_retained_bytes_and_canaries_checked=True,all_four_rounding_modes_and_provider_sticky_flags=True,full_provider_arguments_arena_constants_and_MXCSR_snapshots_equal=True,legal_disjoint_record_and_output_storage=True,quiet_NaN_and_infinity_angle_arguments_checked=True,trig_provider_internals_and_MIPS_hardware_FPU_not_qualified=True,guest_home_mutations_excluded_from_native=True,strict_aliasing_UBSan_trap_LTO_type_errors=True,no_signal_or_trap_counted=True,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_controls')}),flush=True);return q
if __name__=='__main__':main()
