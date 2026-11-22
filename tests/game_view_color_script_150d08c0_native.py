"""SDK32 view layout and defined float-to-unsigned C behavior under strict aliases."""
from pathlib import Path
import itertools,json,subprocess,sys
from tools.experiments import game_view_color_script_150d08c0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_view_color_script_150d08c0_guest as g
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
selected=packet.MANIFEST['selected_source'];a,b=function_span(selected,'func_150D08C0');BODY=selected[a:b]
PRE=r'''#include <ultra64.h>
#include "structs.h"
#define OFF __builtin_offsetof
typedef char view_layout[sizeof(void*)==4&&sizeof(struct108)==0x9A0&&OFF(struct108,unk84)==0x84&&OFF(struct108,unk7B4)==0x7B4?1:-1];
f32 D_800888C0,D_800888C4,D_800888C8,D_800888CC,D_800888D0,D_800888D4,D_800888D8,D_800888DC,D_800888E0;
s32 func_1509BE40(s32,...);void func_1509BFB0(s32,s32,s32,...);void func_150495B0(f32*,f32,f32*,f32,f32,f32);
'''
HARNESS=r'''
typedef union{u32 word;f32 number;} FloatBits;
static struct108 view;
static u32 rowIndex,stepIndex,queryIndex,smoothIndex,submitIndex,bad;
static void check(int yes){if(!yes)bad=1;}
static u32 raw(f32 v){FloatBits x;x.number=v;return x.word;}
static f32 number(u32 v){FloatBits x;x.word=v;return x.number;}
static f32 *pointer(u32 i){switch(i){case 0:return &D_800888C0;case 1:return &D_800888C4;case 2:return &D_800888C8;case 3:return &D_800888CC;case 4:return &D_800888D0;case 5:return &D_800888D4;case 6:return &D_800888D8;case 7:return &D_800888DC;default:return &D_800888E0;}}
static u32 address(f32 *p){u32 i;for(i=0;i<9;i++)if(p==pointer(i))return 0x800888C0u+4*i;bad=1;return 0;}
static void compare(const u32 wanted[11]){u32 i;check((u32)view.unk84==wanted[0]&&raw(view.unk7B4)==wanted[1]);for(i=0;i<9;i++)check(raw(*pointer(i))==wanted[2+i]);}
static void call(u32 t,const u32 *args,u32 n){
 const Row*r=&rows[rowIndex];u32 i;check(stepIndex<r->stepCount);if(bad)return;
 const Step*s=&steps[r->stepStart+stepIndex++];check(s->target==t);compare(s->before);for(i=0;i<n;i++)check(args[i]==s->args[i]);
}
s32 func_1509BE40(s32 count,...){
 __builtin_va_list va;u32 args[4],selector,index;const Row*r=&rows[rowIndex];
 __builtin_va_start(va,count);args[0]=(u32)count;args[1]=__builtin_va_arg(va,u32);args[2]=__builtin_va_arg(va,u32);args[3]=__builtin_va_arg(va,u32);__builtin_va_end(va);
 call(0x1509BE40,args,4);++queryIndex;
 if((r->mode&1)&&queryIndex==1)view.unk84^=(s32)0xF0F0FFFFu;
 selector=args[1];index=selector==0x403D?0:selector==0x4043?1:selector==0x4044?2:3;
 return (s32)r->replies[index];
}
void func_150495B0(f32*p,f32 target,f32*v,f32 strength,f32 damping,f32 dt){
 const Row*r=&rows[rowIndex];u32 args[6]={address(p),raw(target),address(v),raw(strength),raw(damping),raw(dt)};
 call(0x150495B0,args,6);++smoothIndex;check(smoothIndex<=3);if(bad)return;
 *p=number(r->colors[smoothIndex-1]);*v=(f32)smoothIndex;
 if(r->mode&2){view.unk7B4=.25f*(f32)smoothIndex;if(smoothIndex==2)D_800888C0=511.5f;}
}
void func_1509BFB0(s32 count,s32 selector,s32 key,...){
 __builtin_va_list va;u32 i,args[4];const Row*r=&rows[rowIndex];
 __builtin_va_start(va,key);args[0]=(u32)count;args[1]=(u32)selector;args[2]=(u32)key;args[3]=__builtin_va_arg(va,u32);__builtin_va_end(va);
 call(0x1509BFB0,args,4);++submitIndex;
 if(r->mode&4)for(i=0;i<3;i++)*pointer(i)=17.25f+31.f*(f32)submitIndex+(f32)i;
}
static int run(void){
 u32 i;
 for(rowIndex=0;rowIndex<sizeof(rows)/sizeof(rows[0]);rowIndex++){
  const Row*r=&rows[rowIndex];stepIndex=queryIndex=smoothIndex=submitIndex=bad=0;
  for(i=0;i<sizeof(view);i++)((u8*)&view)[i]=(u8)(i*19+0xA5);
  view.unk84=(s32)r->flags;view.unk7B4=number(r->dt);
  for(i=0;i<3;i++){*pointer(i)=number(r->current[i]);*pointer(i+3)=number((u32[]){0x41400000u,0x42080000u,0x42600000u}[i]);*pointer(i+6)=number(r->velocity[i]);}
  func_150D08C0(&view);compare(r->final);check(stepIndex==r->stepCount&&smoothIndex==3&&submitIndex==6);
  for(i=0;i<sizeof(view);i++)if(!(i>=0x84&&i<0x88)&&!(i>=0x7B4&&i<0x7B8))check(((u8*)&view)[i]==(u8)(i*19+0xA5));
  if(bad)return 1;
 }
 return 0;
}
'''
def vectors():
 cases=[g.Case(replies=q,flags=f,mode=mode)for q,f,mode in itertools.product(((0,1,1,1),(1,1,1,1),(1,0,1,1),(1,0,0,1),(1,0,0,0),(0xFFFFFFFF,0,0x80000000,0)),(0,0xFFFFFFFF,0x13579BDF),(0,1,2,4,7))]
 cases += [g.Case(colors=(v,)*3,mode=mode)for v,mode in itertools.product((0,0x80000000,g.bits(-.5),g.bits(63.75),g.bits(255.),g.bits(256.),g.bits(511.5),g.bits(2147483648.),g.bits(4294967040.)),(0,7))]
 rows=[];steps=[]
 for c in cases:
  m=g.check(g.streams()[0],c);final,calls,observations=g.reference(m.initial,c);start=len(steps)
  for(t,args),observation in zip(calls,observations):steps.append((t,list(args)+[0]*(6-len(args)),observation))
  rows.append((c,start,len(calls),g.snapshot(final)))
 def arr(values):return'{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}'
 text='typedef struct{u32 target,args[6],before[11];}Step;\ntypedef struct{u32 replies[4],flags,dt,current[3],velocity[3],colors[3],mode,stepStart,stepCount,final[11];}Row;\n'
 text+='static const Step steps[]={'+','.join('{0x%Xu,%s,%s}'%(t,arr(a),arr(s))for t,a,s in steps)+'};\n'
 text+='static const Row rows[]={'+','.join('{%s,0x%Xu,0x%Xu,%s,%s,%s,%du,%du,%du,%s}'%(arr(c.replies),c.flags,c.dt,arr(c.current),arr(c.velocity),arr(c.colors),c.mode,start,n,arr(final))for c,start,n,final in rows)+'};\n'
 (out/'native-vectors.h').write_text(text);return len(cases)
def main():
 count=vectors();controls={
 'wrong-query-count':BODY.replace('func_1509BE40(1,0x403D','func_1509BE40(2,0x403D'),
 'wrong-query-selector':BODY.replace('0x4043','0x4044'),
 'positive-one-only-query':BODY.replace('func_1509BE40(1,0x403D,6,0x9000))','func_1509BE40(1,0x403D,6,0x9000)==1)'),
 'wrong-disabled-flags':BODY.replace('0x7FFDEFFF','0x7FFFFFFF'),
 'wrong-palette-component':BODY.replace('64.0f','63.0f'),
 'wrong-delta-field':BODY.replace('view->unk7B4','view->unk7B8'),
 'wrong-smoothing-strength':BODY.replace('4.0f,6.0f','5.0f,6.0f'),
 'wrong-velocity-output':BODY.replace('&D_800888D8','&D_800888DC'),
 'wrong-published-width':BODY.replace('(u8)(u32)','(u16)(u32)'),
 'cached-repeated-red':BODY.replace('    func_1509BFB0(1,0x30F5','    u8 cachedRed=(u8)(u32)D_800888C0;\n    func_1509BFB0(1,0x30F5').replace('0x30FA,0x12,(u8)(u32)D_800888C0','0x30FA,0x12,cachedRed')}
 profiles={};effective=[]
 for name,body,opt in [('O0',BODY,'-O0'),('O2',BODY,'-O2'),('O3',BODY,'-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
  if name in controls:assert body!=BODY,name
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe')
  path.write_text(PRE+'\n'+body+'\n#include "native-vectors.h"\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fsanitize=float-cast-overflow',str(path),'-o',str(exe)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name in controls:assert q.returncode!=0,name;effective.append(name)
  else:assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);profiles[name]=dict(cases=count,SDK_struct_layout=True,strict_aliasing=True,UBSan=True,float_cast_sanitizer=True)
 r=dict(profiles=profiles,effective_source_controls=effective,independent_guest_checked_vectors=True,
  complete_view_canaries=True,all_call_boundary_states=True,invalid_float_conversions_excluded=True,
  defined_native_domain='finite -1 < colors < 2^32',source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
