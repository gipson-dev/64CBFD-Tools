def run():
 from pathlib import Path
 import sys,subprocess
 from tools.experiments import game_trajectory_actor_150e1570_match as packet
 root=packet.ROOT;out=packet.OUT
 from tools.experiments.game_remaining_donor_candidates import function_span
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 s=packet.MANIFEST['selected_source'];lo,hi=function_span(s,'func_150E1570');pre=s[:lo];fn=s[lo:hi]
 controls={
 'count':('index < 25','index < 24'),
 'immune':('actor->immune == 0','actor->immune != 0'),
 'health':('actor->health != 0','actor->health == 0'),
 'source':('source->indexPlusOne - 1','source->indexPlusOne'),
 'excluded':('index != excluded','index == excluded'),
 'best':('value < score','value <= score'),
 'negative':('value != 0','value > 0'),
 'height':('actor->y + (f32)actor->y_offset','actor->y - (f32)actor->y_offset'),
 'owner':('actor->unk76 = source->unk76','actor->unk76 = 0'),
 'return':('return result;','return 0;'),
 }
 code=pre+'\n'+fn.replace('func_150E1570(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert fn.count(old)>=1,(name,old)
  code+=fn.replace('func_150E1570(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+=r'''
 TrajectoryActor1570 D_800CC2D0[26];u8 D_800C3E78;static TrajectoryActor1570 source;
 static int failed,expected_count,seen,expected_slots[25],expected_best,emits,pattern;
 f32 sqrtf(f32 v) { return __builtin_sqrtf(v); }
 void func_15047390(f32 m[4][4],f32 x,f32 y,f32 z,f32 a,f32 b,f32 c,f32 d,f32 e,f32 f) {
  if(x!=1||y!=2||z!=3||a!=4||b!=6||c!=3||d!=0||e!=1||f!=0)failed=1;
  for(int i=0;i<4;i++)for(int j=0;j<4;j++)m[i][j]=(i==j)?1.0f:0.0f;
 }
 static s32 score(int n) {static const s32 x[5]={0,3,-2,7,-2};return x[(n+pattern)%5];}
 s32 func_15049440(f32 m[4][4],f32 x,f32 y,f32 z,f32 a,f32 b,f32 c,f32 length,f32 h,f32 i) {
  int n=(int)x;
  if(seen>=expected_count || n!=expected_slots[seen] || m[0][0]!=1 || m[0][1]!=0 ||
  x!=(f32)n+0.5f || y!=(f32)(100+n+n-10) || z!=(f32)(-200-n) ||
  a!=(f32)(-n-1) || b!=(f32)(n+2) || c!=0 || length!=5 || h!=10 || i!=10) failed=2;
  seen++;return score(n);
 }
 s32 func_1505D1C4(f32 x,f32 y,f32 z,s32 type,s32 player,u16 zero,s32 z2,s32 z3) {
  int n=expected_best;emits++;
  if(n<0 || x!=(f32)n+0.5f || y!=(f32)(100+n+n-10) || z!=(f32)(-200-n) ||
  type!=18 || player!=0xcd || zero || z2 || z3)failed=3;
  source.unk76=0x6789;return (s32)0xdeadbeef;
 }
 typedef s32 (*Fn)(TrajectoryActor1570*,f32,f32,f32,f32,f32,f32,s32,s32);
 static int check(Fn fn) {
  static const int excluded[]={-1,0,9,24,30}; static const int slot[]={0,1,4,25,255};
  for(int a=0;a<5;a++)for(int b=0;b<5;b++)for(int flags=0;flags<8;flags++)for(pattern=0;pattern<5;pattern++) {
   source.indexPlusOne=slot[b];source.unk76=0xb135;D_800C3E78=0xcd;expected_count=seen=emits=failed=0;expected_best=-1;s32 bestscore=0;
   for(int j=0;j<25;j++) {
    TrajectoryActor1570 *p=&D_800CC2D0[j];p->active=!(flags&1 && j%4==0);p->health=!(flags&2 && j%3==0);p->immune=!!(flags&4 && j%7==0);
    p->x=(f32)j+0.5f;p->y=(f32)(100+j);p->z=(f32)(-200-j);p->radius=-j-1;p->height=j+2;p->y_offset=j-10;p->unk76=0;
    if(p->active && p->health && !p->immune && j!=excluded[a] && j!=slot[b]-1) {
      expected_slots[expected_count++]=j;s32 value=score(j);
      if(value && (expected_best<0 || value<bestscore)){expected_best=j;bestscore=value;}
    }
   }
   s32 result=fn(&source,1,2,3,4,6,3,excluded[a],18);
   if(failed || seen!=expected_count || result!=(expected_best<0?0:(s32)0xdeadbeef) || emits!=(expected_best>=0))return 1;
   if(expected_best>=0 && D_800CC2D0[expected_best].unk76!=0x6789)return 2;
  }
  return 0;
 }
 static int run(void){if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=out/'screen-native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('screen-native'+opt);r=subprocess.run(native_command(opt)+['-fno-math-errno','-Wno-unused-but-set-variable',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'1000 finite independent cases,',len(controls),'negative controls, UBSan',flush=True)
