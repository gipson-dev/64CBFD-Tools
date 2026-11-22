"""Real 32-bit SDK layout and semantic C under O0/O2/O3 and UBSan."""
from pathlib import Path
import itertools,json,subprocess,sys
from tools.experiments import game_view_light_script_150ecc70_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_view_light_script_150ecc70_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
BODY=packet.MANIFEST['body']
PRE=r'''#include <ultra64.h>
#include "structs.h"
#define OFF __builtin_offsetof
typedef char layout[sizeof(void*)==4&&sizeof(struct108)==0x9A0&&OFF(struct108,unk84)==0x84&&OFF(struct108,unk134)==0x134&&OFF(struct108,unk190)==0x190&&OFF(struct108,unk7B4)==0x7B4?1:-1];
f32 D_80088AD0,D_80088AD4,D_80088AD8,D_80088ADC,D_80088AE0,D_80088AE4,D_80088AE8,D_80088AEC,D_80088AF0;
'''
HARNESS=r'''
typedef union{u32 w;f32 f;}Float;
static struct108 view;
static u32 rowIndex,stepIndex,queryIndex,smoothIndex,submitIndex,bad;
static void check(int yes){if(!yes)bad=1;}
static u32 raw(f32 f){Float x;x.f=f;return x.w;}
static f32 number(u32 w){Float x;x.w=w;return x.f;}
static f32*pointer(u32 i){switch(i){case 0:return &D_80088AD0;case 1:return &D_80088AD4;case 2:return &D_80088AD8;case 3:return &D_80088ADC;case 4:return &D_80088AE0;case 5:return &D_80088AE4;case 6:return &D_80088AE8;case 7:return &D_80088AEC;default:return &D_80088AF0;}}
static u32 address(f32*p){u32 i;for(i=0;i<9;i++)if(p==pointer(i))return 0x80088AD0u+4*i;bad=1;return 0;}
static void compare(const u32 wanted[13]){u32 i;check((u32)view.unk84==wanted[0]&&(u32)view.unk134==wanted[1]&&raw(view.unk190)==wanted[2]&&raw(view.unk7B4)==wanted[3]);for(i=0;i<9;i++)check(raw(*pointer(i))==wanted[4+i]);}
static void call(u32 t,const u32*args,u32 n){const Row*r=&rows[rowIndex];u32 i;check(stepIndex<r->n);if(bad)return;const Step*s=&steps[r->start+stepIndex++];check(s->t==t&&s->n==n);compare(s->before);for(i=0;i<n;i++)check(args[i]==s->a[i]);}
s32 func_1509BE40(s32 count,...){
 __builtin_va_list va;u32 a[5],i,index;const Row*r=&rows[rowIndex];check(count>=0&&count<=2);if(bad)return 0;
 __builtin_va_start(va,count);a[0]=(u32)count;for(i=1;i<3+(u32)count;i++)a[i]=(u32)__builtin_va_arg(va,s32);__builtin_va_end(va);
 call(0x1509BE40,a,3+(u32)count);++queryIndex;if((r->mode&1)&&queryIndex==1)view.unk84^=(s32)0xF0F0FFFFu;
 if(a[1]==0x2007&&a[2]==0xB7)return (s32)r->selector;
 if(a[1]==0x4010)return (s32)r->enabled;
 if(a[2]==0x9C)return (s32)r->parameter;
 if(a[2]==0x9A)return (s32)r->value;
 index=a[1]==0x403B?0:a[1]==0x4038?1:a[1]==0x4039?2:3;return (s32)r->replies[index];
}
void func_1509BFB0(s32 count,s32 selector,s32 key,...){
 __builtin_va_list va;u32 a[5],i;const Row*r=&rows[rowIndex];check(count>=0&&count<=2);if(bad)return;
 a[0]=(u32)count;a[1]=(u32)selector;a[2]=(u32)key;__builtin_va_start(va,key);for(i=0;i<(u32)count;i++)a[3+i]=(u32)__builtin_va_arg(va,s32);__builtin_va_end(va);
 call(0x1509BFB0,a,3+(u32)count);++submitIndex;
 if(r->mode&4){view.unk84^=(s32)0x55AA00FFu;for(i=0;i<3;i++)*pointer(i)=17.25f+31.f*(f32)submitIndex+(f32)i;}
}
void func_150495B0(f32*p,f32 target,f32*v,f32 strength,f32 damping,f32 dt){
 const Row*r=&rows[rowIndex];u32 a[6]={address(p),raw(target),address(v),raw(strength),raw(damping),raw(dt)};
 call(0x150495B0,a,6);++smoothIndex;check(smoothIndex<=3);if(bad)return;
 *p=number(r->colors[smoothIndex-1]);*v=(f32)smoothIndex;
 if(r->mode&2){view.unk7B4=.25f*(f32)smoothIndex;if(smoothIndex==2)D_80088AD0=511.5f;}
}
static int run(void){u32 i;for(rowIndex=0;rowIndex<sizeof(rows)/sizeof(rows[0]);rowIndex++){
 const Row*r=&rows[rowIndex];stepIndex=queryIndex=smoothIndex=submitIndex=bad=0;
 for(i=0;i<sizeof(view);i++)((u8*)&view)[i]=(u8)(i*19+0xA5);
 view.unk84=(s32)r->flags;view.unk7B4=number(r->dt);/*INITIAL_FIELDS*/
 for(i=0;i<3;i++){*pointer(i)=number(r->current[i]);*pointer(i+3)=number((u32[]){0x41400000u,0x42080000u,0x42600000u}[i]);*pointer(i+6)=number(r->velocity[i]);}
 func_150ECC70(&view);compare(r->final);check(stepIndex==r->n);
 for(i=0;i<sizeof(view);i++)if(!(i>=0x84&&i<0x88)&&!(i>=0x134&&i<0x138)&&!(i>=0x190&&i<0x194)&&!(i>=0x7B4&&i<0x7B8))check(((u8*)&view)[i]==(u8)(i*19+0xA5));
 if(bad)return 1;
 }return 0;}
'''
def vectors():
 cases=[g.Case(replies=q,enabled=e,flags=f,mode=m,value=v)for q,e,f,m,v in itertools.product(((0,1,1,1),(1,1,1,1),(1,0,1,1),(1,0,0,1),(1,0,0,0)),(0,1),(0,0xFFFFFFFF),(0,7),(-2147483648,359,360,463,464,900,1190,1191,2147483647))]
 cases +=[g.Case(colors=(v,)*3,mode=m)for v,m in itertools.product((0,0x80000000,g.bits(63.75),g.bits(255.),g.bits(256.),g.bits(511.5),g.bits(2147483648.),g.bits(4294967040.)),(0,7))]
 steps=[];rows=[]
 for c in cases:
  initial=g.fixture(c);final,calls,obs=g.reference(initial,c);start=len(steps)
  machine=g.check(g.streams()[1],c);assert g.public(machine.memory)==g.public(final)
  for(t,args),snap in zip(calls,obs):steps.append((t,len(args),list(args)+[0]*(6-len(args)),snap))
  rows.append((c,start,len(calls),g.snapshot(final)))
 def arr(v):return'{'+','.join('0x%Xu'%g.u32(x)for x in v)+'}'
 text='typedef struct{u32 t,n,a[6],before[13];}Step;\ntypedef struct{u32 replies[4],selector,enabled,parameter,value,flags,dt,current[3],velocity[3],colors[3],mode,start,n,final[13];}Row;\n'
 text+='static const Step steps[]={'+','.join('{0x%Xu,%du,%s,%s}'%(t,n,arr(a),arr(s))for t,n,a,s in steps)+'};\n'
 text+='static const Row rows[]={'+','.join('{%s,%s,%s,%s,%s,%du,%du,%du,%s}'%(arr(c.replies),','.join('0x%Xu'%g.u32(x)for x in(c.selector,c.enabled,c.parameter,c.value,c.flags,c.dt)),arr(c.current),arr(c.velocity),arr(c.colors),c.mode,start,n,arr(final))for c,start,n,final in rows)+'};\n'
 (out/'native-vectors.h').write_text(text);return len(cases)
def main():
 count=vectors();controls={
  'wrong-clamp-low':BODY.replace('value < 900 ? 900','value < 900 ? 901'),
  'wrong-radius-low':BODY.replace('halfValue < 180 ? 180','halfValue < 180 ? 181'),
  'half-of-clamped-value':BODY.replace('halfValue = value >> 1;','halfValue = (value < 900 ? 900 : value >= 1191 ? 1190 : value) >> 1;'),
  'wrong-early-reset-field':BODY.replace('view->unk134 = 0;','view->unk134 = 1;'),
  'wrong-range-payload-count':BODY.replace('func_1509BFB0(2, 0x9000','func_1509BFB0(1, 0x9000'),
  'wrong-palette':BODY.replace('128.0f','127.0f'),
  'wrong-disabled-flags':BODY.replace('0x7FFDEDFF','0x7FFFFFFF'),
  'wrong-delta-field':BODY.replace('view->unk7B4','view->unk7B8'),
  'wrong-published-width':BODY.replace('(u8)(u32)','(u16)(u32)')}
 profiles={};effective=[]
 for name,body,opt in [('O0',BODY,'-O0'),('O2',BODY,'-O2'),('O3',BODY,'-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
  if name in controls:assert body!=BODY,name
  initial=g.fixture(g.Case());init='view.unk134=(s32)0x%Xu;view.unk190=number(0x%Xu);'%(g.read(initial,g.VIEW+0x134),g.read(initial,g.VIEW+0x190))
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe');path.write_text(PRE+'\n'+body+'\n#include "native-vectors.h"\n'+HARNESS.replace('/*INITIAL_FIELDS*/',init)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fsanitize=float-cast-overflow',str(path),'-o',str(exe)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name in controls:assert q.returncode!=0,name;effective.append(name)
  else:assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);profiles[name]=dict(cases=count,SDK_layout=True,strict_aliasing=True,UBSan=True,float_cast_sanitizer=True)
 r=dict(profiles=profiles,effective_source_controls=effective,complete_view_canaries=True,all_call_boundary_states=True,
  invalid_float_conversions_excluded=True,defined_native_domain='finite 0 <= colors < 2^32; signed shifts use the target arithmetic-right-shift convention',source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
