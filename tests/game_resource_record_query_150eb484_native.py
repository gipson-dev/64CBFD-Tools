"""Native32 recovered C, real forwarding gate, typed providers and full observers."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_resource_record_query_150eb484_match as packet
o=packet.OUT
def main():
 source=(o/'selected-owner.c').read_text();lo,hi=function_span(source,'func_150EB484');body=source[lo:hi]
 pre=source[source.index('typedef struct {'):source.index('s32 func_150EB484(f32 *,')]
 header='typedef unsigned char u8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;\n#define NULL ((void*)0)\n'+pre+'\ns32 func_150EB484(f32*,f32*,f32*);\ns32 actual_gate(u8*,f32*,f32*,f32*);\ns32 func_150A3504(u8*,f32*,f32*,f32*);\ntypedef char ABI[sizeof(void*)==4&&sizeof(GeneratedCDE80Record)==52&&__builtin_offsetof(GeneratedCDE80Record,field18)==24?1:-1];\n'
 (o/'native-shared.h').write_text(header)
 gate=(o/'selected-gate-owner.c').read_text();a,z=function_span(gate,'func_150A34B0');(o/'native-gate.c').write_text('#include "native-shared.h"\n'+gate[a:z].replace('func_150A34B0','actual_gate')+'\n')
 harness=r'''
typedef struct{u8 pad[744];s32 selected;}Context;
typedef struct{u32 prefix[4];GeneratedCDE80Record a[80],b[80];Context context;f32 v[3][3];u32 suffix[4];}Arena;
typedef struct{u32 t,a[4],base,selected,v[9],digest;}Event;
static Arena arena;static Event events[16],expectedEvents[16];static u32 count,checks,hit,mode,ctx,answer,alias,gateMode,error;
GeneratedCDE80Record *D_800D3098;
s32 D_80088AA0[4]={1,2,4,3};s32 D_80088AB0[8]={45,46,47,48,49,50,51,52};
__asm__(".globl D_80088AD0\n.set D_80088AD0,D_80088AB0+32");
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static u32 digest(void){u32 i,h=2166136261u;for(i=0;i<sizeof(Arena);i++)h=(h^((u8*)&arena)[i])*16777619u;return h;}
static void event(u32 t,u32 a,u32 b,u32 c,u32 d){u32 i;Event*e=&events[count++];e->t=t;e->a[0]=a;e->a[1]=b;e->a[2]=c;e->a[3]=d;e->base=(u32)D_800D3098;e->selected=(u32)arena.context.selected;e->digest=digest();for(i=0;i<9;i++)e->v[i]=word(arena.v[i/3][i%3]);}
static void effects(u32 t,f32*out){u32 i;if(mode&1)D_800D3098=D_800D3098==arena.a?arena.b:arena.a;if(mode&2){arena.context.selected=(s32)(0x87654321u^checks);if(out)for(i=0;i<3;i++)out[i]=real(0x41000000u+i*0x800000u+checks);}if((mode&4)&&t==2){D_800D3098=arena.b;arena.context.selected=(s32)0xfedcba98u;}}
u8 *func_15083E90(u8 n){event(0,n,0,0,0);effects(0,NULL);return ctx?(u8*)&arena.context:NULL;}
s32 func_150A3504(u8*record,f32*start,f32*end,f32*out){Event*e=&events[count-1];if(e->a[0]!=(u32)record||e->a[1]!=(u32)start||e->a[2]!=(u32)end||e->a[3]!=(u32)out)error=1;return checks==hit?(s32)answer:0;}
s32 func_150A34B0(u8*record,f32*start,f32*end,f32*out){s32 v;event(1,(u32)record,(u32)start,(u32)end,(u32)out);effects(1,out);v=actual_gate(record,start,end,out);checks++;return v;}
void func_150A2864(u32 index,s32 state){event(2,index,(u32)state,0,0);effects(2,NULL);}
s32 func_150EBC80(u8*record,u8 effect,s32 active){event(3,(u32)record,effect,(u32)active,0);effects(3,NULL);return (s32)0xdeadbeefu;}
static s32 reference(f32*start,f32*end,f32*out){u8*p=func_15083E90(9);u32 i,index;if(p){for(i=0;i<4;i++){index=(u32)D_80088AA0[i];if(func_150A34B0((u8*)&D_800D3098[index],start,end,out)){func_150A2864(index,1);((Context*)p)->selected=(s32)(i+1);func_150EBC80((u8*)&D_800D3098[index],255,1);return 1;}}for(i=0;i<8;i++){index=(u32)D_80088AB0[i];if(func_150A34B0((u8*)&D_800D3098[index],start,end,out))return 1;}}else{if(func_150A34B0((u8*)&D_800D3098[76],start,end,out))D_800D3098[76].field18=1;}return 0;}
static void reset(void){u32 i,j;for(i=0;i<sizeof(Arena);i++)((u8*)&arena)[i]=(u8)(i*29+0x5a);for(i=0;i<80;i++){arena.a[i].disabled=arena.b[i].disabled=gateMode==1?1:gateMode==2?2:0;arena.a[i].flags=arena.b[i].flags=(u8)(gateMode==3?3:gateMode==4?0xfc:0);}for(i=0;i<3;i++)for(j=0;j<3;j++)arena.v[i][j]=(f32)(1+i*3+j);D_800D3098=arena.a;count=checks=error=0;}
static s32 fail(u32 row,u32 why){u32 v[4]={row,why,count,checks},nr=4;__asm__ volatile("int $0x80":"+a"(nr):"b"(1),"c"(v),"d"(sizeof(v)):"memory");return 42;}
static s32 main(void){u32 row=0,i,expectedCount,expectedError,base;Arena expected;s32 wanted,actual;f32 *start,*end,*out;
 for(ctx=0;ctx<2;ctx++)for(hit=0;hit<14;hit++)for(mode=0;mode<8;mode++)for(alias=0;alias<4;alias++)for(gateMode=0;gateMode<5;gateMode++){
 answer=(row&1)?0x80000000u:0xffffffffu;reset();start=arena.v[0];end=arena.v[1];out=arena.v[2];if(alias==1)out=start;if(alias==2)out=end;if(alias==3)start=end=out=arena.v[0];wanted=reference(start,end,out);for(i=0;i<sizeof(Arena);i++)((u8*)&expected)[i]=((u8*)&arena)[i];expectedCount=count;expectedError=error;base=(u32)D_800D3098;for(i=0;i<count*sizeof(Event);i++)((u8*)expectedEvents)[i]=((u8*)events)[i];
 reset();actual=func_150EB484(start,end,out);if(actual!=wanted||count!=expectedCount||error!=expectedError||error||(u32)D_800D3098!=base)return fail(row,1);
 for(i=0;i<sizeof(Arena);i++)if(((u8*)&arena)[i]!=((u8*)&expected)[i])return fail(row,2+i);
 for(i=0;i<count*sizeof(Event);i++)if(((u8*)events)[i]!=((u8*)expectedEvents)[i])return fail(row,3+sizeof(Arena)+i);row++;
 }return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''
 (o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 base=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,function,opt,expected):
  f=o/(name+'.c');f.write_text('#include "native-shared.h"\n'+function+'\n');exe=o/(name+'.exe');cmd=[*base,opt,str(f),str(o/'native-gate.c'),str(o/'native-harness.c'),'-o',str(exe)];p=subprocess.run(cmd,text=True,capture_output=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stdout,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=45);diagnostic=list(struct.unpack('<4I',p.stdout))if len(p.stdout)==16 else p.stdout.hex();q=dict(profile=opt,exit_code=p.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());(o/(name+'-execution.json')).write_text(json.dumps(q,indent=2)+'\n');assert p.returncode==expected,(name,q);return q
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in ('O0','O2','O3')];controls=[]
 for name,old,new in [('fallback-result','D_800D3098[76].field18 = 1;','D_800D3098[76].field18 = 1; return 1;'),('selection-index','i + 1;','i + 2;'),('missing-status','func_150A2864(index, 1);','func_150A2864(index, 2);'),('wrong-effect','255, 1);','254, 1);'),('wrong-output','start, end, output','start, end, start'),('short-priority','i < 4','i < 3'),('short-secondary','cursor != (s32 *)&D_80088AD0','cursor != D_80088AB0 + 7')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new,1)if name=='wrong-output'else body.replace(old,new),'-O2',42)))
 cached=body.replace('    u8 *context;','    u8 *context;\n    GeneratedCDE80Record *cached = D_800D3098;').replace('func_150EBC80((u8 *)&D_800D3098[index], 255, 1);','func_150EBC80((u8 *)&cached[index], 255, 1);');assert cached!=body
 controls.append(dict(name='cached-base-across-providers',**run('control-cached-base',cached,'-O2',42)))
 q=dict(cases_per_profile=2*14*8*4*5,profiles=profiles,translation_units=3,actual_gate_body=True,record_size=52,context_selected_offset=744,full_arena_bytes=80*52*2+748+36+32,all_arena_bytes_and_full_provider_event_snapshots_equal=True,strict_aliasing_UBSan_traps_LTO_type_errors=True,typed_geometry_and_effect_provider_contracts_only=True,all_gate_disabled_and_low_flag_bit_cases=True,effective_controls=controls,source_installed=packet.installed(),matching_credit=0)
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
