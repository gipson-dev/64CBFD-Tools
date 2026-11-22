"""Defined SDK32 cooldown arithmetic and the actual eleven-argument sound wrapper."""
from pathlib import Path
import itertools,json,subprocess,sys
from tools.experiments import game_record_sound_scheduler_150d0730_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_record_sound_scheduler_150d0730_guest as g
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
selected=packet.MANIFEST['selected_source'];a,b=function_span(selected,'func_150D0730');BODY=selected[a:b];PRE=selected[:a]
wrapper_source=(root/'conker/src/init_EB00.c').read_text();a,b=function_span(wrapper_source,'func_10010F88');WRAPPER=wrapper_source[a:b]
PRE+='\nu16 func_10010E78(u16,s32,u16,s16,u8,s32,s16,s16,s16,s16,s16);\n'
HARNESS=r'''
typedef char record_layout[sizeof(void*)==4&&sizeof(AmbientSoundRecord)==52&&__builtin_offsetof(AmbientSoundRecord,y)==2&&__builtin_offsetof(AmbientSoundRecord,z)==4?1:-1];
static AmbientSoundRecord records[2][73];AmbientSoundRecord *D_800D3098;
u8 D_800D98F0;s32 D_800BE9E4;
static u32 rowIndex,stepIndex,queryIndex,randomIndex,bad;
static const u32 indices[6]={0x15,0x1A,0x1B,0x1C,0x1D,0x20};
static void check(int yes){if(!yes)bad=1;}
static void compare(const u32 wanted[39]){
 u32 t,i,n=3;check(D_800D98F0==wanted[0]&&(u32)D_800BE9E4==wanted[1]);
 check((D_800D3098==records[0]?0x30000u:0x40000u)==wanted[2]);
 for(t=0;t<2;t++)for(i=0;i<6;i++){AmbientSoundRecord*p=&records[t][indices[i]];check((u16)p->x==wanted[n++]&&(u16)p->y==wanted[n++]&&(u16)p->z==wanted[n++]);}
}
static void call(u32 t,const u32*args,u32 count){
 const Row*r=&rows[rowIndex];u32 i;check(stepIndex<r->stepCount);if(bad)return;
 const Step*s=&steps[r->stepStart+stepIndex++];check(s->target==t);compare(s->before);for(i=0;i<count;i++)check(args[i]==s->args[i]);
}
void func_151827D0(void){
 const Row*r=&rows[rowIndex];call(0x151827D0,0,0);
 if(r->mode&1){D_800D98F0^=0x80;D_800BE9E4=-1;}
}
s32 func_150A29C8(u32 actor,u32 index){
 const Row*r=&rows[rowIndex];u32 i,args[2]={actor,index};call(0x150A29C8,args,2);++queryIndex;
 if(r->mode&2){D_800D3098=records[1];records[1][index].y=(s16)0x8001;}
 for(i=0;i<6;i++)if(indices[i]==index)return(s32)r->replies[i];
 bad=1;return 1;
}
u32 func_150ADA20(void){
 const Row*r=&rows[rowIndex];u32 i;call(0x150ADA20,0,0);++randomIndex;check(randomIndex<=2);if(bad)return 0;
 if(r->mode&4){D_800D3098=records[randomIndex==1?1:0];for(i=0;i<6;i++){AmbientSoundRecord*p=&records[0][indices[i]];p->x=(s16)(0x8000+0x111*randomIndex);p->y=(s16)(0x8001+0x111*randomIndex);p->z=(s16)(0x8002+0x111*randomIndex);}}
 return r->randoms[randomIndex-1];
}
u16 func_10010E78(u16 handle,s32 sound,u16 volume,s16 pitch,u8 flags,s32 channel,s16 x,s16 y,s16 z,s16 minimum,s16 maximum){
 u32 args[10]={(u32)sound,volume,(u32)(s32)pitch,flags,(u32)channel,(u32)(s32)x,(u32)(s32)y,(u32)(s32)z,(u32)(s32)minimum,(u32)(s32)maximum};
 check(handle==0);call(0x10010F88,args,10);if(rows[rowIndex].mode&8)D_800D98F0=17;return 0xBEEF;
}
static int run(void){
 u32 t,i,j;
 for(rowIndex=0;rowIndex<sizeof(rows)/sizeof(rows[0]);rowIndex++){
  const Row*r=&rows[rowIndex];stepIndex=queryIndex=randomIndex=bad=0;
  for(t=0;t<2;t++)for(i=0;i<73;i++){
   u8*p=(u8*)&records[t][i];for(j=0;j<52;j++)p[j]=(u8)((i*52+j)*19+0xA5);
   records[t][i].x=(s16)(r->coordinates[i%3]^(t?0x5555u:0));records[t][i].y=(s16)(r->coordinates[(i+1)%3]^(t?0x5555u:0));records[t][i].z=(s16)(r->coordinates[(i+2)%3]^(t?0x5555u:0));
  }
  D_800D3098=records[0];D_800D98F0=(u8)r->timer;D_800BE9E4=(s32)r->step;
  func_150D0730((s32)r->argument);compare(r->final);check(stepIndex==r->stepCount);
  for(t=0;t<2;t++)for(i=0;i<73;i++)for(j=6;j<52;j++)check(((u8*)&records[t][i])[j]==(u8)((i*52+j)*19+0xA5));
  if(bad)return 1;
 }
 return 0;
}
'''
def vectors():
 cases=[g.Case(timer=i,step=(0,1,127,255,256,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[i%8])for i in range(256)]
 cases += [g.Case(timer=t,step=s,mode=mode)for t,s,mode in itertools.product((0,1,127,128,255),(0,1,2,255,256,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1))]
 cases += [g.Case(replies=tuple(0 if i==selection else answer for i in range(6)),mode=mode)for selection,answer,mode in itertools.product(range(7),(1,0x80000000,0xFFFFFFFF),(0,2,4,8,14))]
 cases += [g.Case(randoms=(a,b),coordinates=coords)for a,b in itertools.product((0,1,127,128,255,0x7FFFFFFF,0x80000000,0xFFFFFFFF),repeat=2)for coords in((0,1,32767),(32768,65535,0))]
 rows=[];steps=[]
 for c in cases:
  m=g.check(g.streams()[0],c);final,calls,observations=g.reference(m.initial,c);start=len(steps)
  for(t,args),observation in zip(calls,observations):steps.append((t,list(args)+[0]*(10-len(args)),observation))
  rows.append((c,start,len(calls),g.snapshot(final)))
 def arr(values):return'{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}'
 text='typedef struct{u32 target,args[10],before[39];}Step;\ntypedef struct{u32 timer,step,replies[6],randoms[2],coordinates[3],mode,argument,stepStart,stepCount,final[39];}Row;\n'
 text+='static const Step steps[]={'+','.join('{0x%Xu,%s,%s}'%(t,arr(a),arr(s))for t,a,s in steps)+'};\n'
 text+='static const Row rows[]={'+','.join('{%du,0x%Xu,%s,%s,%s,%du,0x%Xu,%du,%du,%s}'%(c.timer,c.step,arr(c.replies),arr(c.randoms),arr(c.coordinates),c.mode,c.argument,start,n,arr(final))for c,start,n,final in rows)+'};\n'
 (out/'native-vectors.h').write_text(text);return len(cases)
def main():
 count=vectors();controls={
 'signed-cooldown-gate':BODY.replace('D_800D98F0 != 0','(s8)D_800D98F0 > 0'),
 'unsigned-step-compare':BODY.replace('D_800BE9E4 < D_800D98F0','(u32)D_800BE9E4 < D_800D98F0'),
 'missing-setup-helper':BODY.replace('func_151827D0();',''),
 'positive-query-only':BODY.replace('!func_150A29C8(0,0x15)','func_150A29C8(0,0x15)!=1'),
 'wrong-first-priority':BODY.replace('func_150A29C8(0,0x15)','func_150A29C8(0,0x1A)'),
 'wrong-delay-mask':BODY.replace('&127','&255'),
 'signed-sound-remainder':BODY.replace('func_150ADA20()%3','(s32)func_150ADA20()%3'),
 'wrong-coordinate':BODY.replace('D_800D3098[selected].y','D_800D3098[selected].z'),
 'wrong-attenuation':BODY.replace(',800,1500',',801,1500'),
 'cached-record-pointer':BODY.replace('D_800D98F0=(func_150ADA20()','AmbientSoundRecord *cached=D_800D3098;\n            D_800D98F0=(func_150ADA20()').replace('D_800D3098[selected]','cached[selected]')}
 profiles={};effective=[]
 for name,body,opt in [('O0',BODY,'-O0'),('O2',BODY,'-O2'),('O3',BODY,'-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
  if name in controls:assert body!=BODY,name
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe')
  path.write_text(PRE+'\n'+body+'\n'+WRAPPER+'\n#include "native-vectors.h"\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name in controls:assert q.returncode!=0,name;effective.append(name)
  else:assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);profiles[name]=dict(cases=count,SDK_struct_layout=True,strict_aliasing=True,UBSan=True)
 r=dict(profiles=profiles,effective_source_controls=effective,independent_guest_checked_vectors=True,
  actual_sound_wrapper_C_executed=True,all_eleven_forwarded_sound_words=True,all_call_boundary_states=True,
  signed_step_extremes_defined=True,source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
