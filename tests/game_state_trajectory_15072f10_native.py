from pathlib import Path
from importlib.machinery import SourceFileLoader
import itertools,subprocess
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_state_trajectory_15072f10_match as packet
from tools.tests import game_state_trajectory_15072f10_reference as R
O=packet.OUT;G=R.G;source=packet.MANIFEST['selected_source'];f=body(source,'func_15072F10')
def run():
 controls={'timer':(' - 1;',' - 2;'),'pitch':('0.0054931640625f','0.004f'),'yaw':('actor->unk7A - *(s16 *)(state + 0x12)','actor->unk7A + *(s16 *)(state + 0x12)'),'distance':('2000.0f','1000.0f'),'reload':('actor = D_800D154C;\n    x =','x ='),'scale':('x * D_8009A094','x * 1.0f'),'height':('actor->y_position + (f32)actor->unkD6','actor->y_position - (f32)actor->unkD6'),'player':('D_800C3E78, 18','0, 18'),'mode':('D_800C3E78, 18','D_800C3E78, 17'),'return':('return func_150E1570','func_150E1570')}
 # A return control preserves a defined return value after the call.
 controls['return']=('return func_150E1570(actor, actor->x_position, actor->y_position + (f32)actor->unkD6,\n                         actor->z_position, x, y, z, D_800C3E78, 18);','func_150E1570(actor, actor->x_position, actor->y_position + (f32)actor->unkD6,\n                         actor->z_position, x, y, z, D_800C3E78, 18); return 0;')
 code=r"""
 #include <ultra64.h>
 typedef struct {u8 pad0[0x12];s16 unk12;u8 pad14[0x10];s16 timer;} struct126;
 typedef struct {u8 p0[0x14];f32 x_position,y_position,z_position;u8 p20[0x7a-0x20];u16 unk7A;u8 p7c[0xd6-0x7c];s16 unkD6;u8 pd8[0x1d1-0xd8];s8 unk1D1;u8 p1d2[0x31c-0x1d2];struct126 *unk31C;} struct127;
 extern struct127 *D_800D154C;extern f32 D_8009A094;extern u8 D_800C3E78;
 void func_1505A184(u16,f32,f32,f32*,f32*,f32*);
 s32 func_150E1570(struct127*,f32,f32,f32,f32,f32,f32,s32,s32);
 """+f.replace('func_15072F10(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert f.count(old)==1,(name,old);code+=f.replace('func_15072F10(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 rows=[]
 for pitch,timer,angle,offset,mutation,output in itertools.product((-128,-1,0,1,127),(-32768,-1,0,1,32767),(0,0xffff),(-32768,0,32767),range(8),(0,1)):
  c=G.Case(pitch=pitch,timer=timer,angle=angle,offset=offset,mutation=mutation,output=output);mem,calls,answer=R.reference(c);first=calls[0][1];second=calls[1][1];rows.append('{%d,%d,%d,%d,%d,%d,{%s},{%s},%d,%d}'%(pitch,timer,angle,offset,mutation,output,','.join('0x%Xu'%x for x in first[:3]),','.join('0x%Xu'%x for x in second[1:7]),second[7],G.read(mem,G.STATE+0x24,2)))
 code+='\ntypedef struct {s32 pitch,timer,angle,offset,mutation,output;u32 first[3],second[6],player,expected_timer;} Test;\nstatic const Test tests[]={\n'+',\n'.join(rows)+'\n};\n'
 code+=r"""
 static struct127 actors[2];static struct126 states[2];struct127 *D_800D154C;f32 D_8009A094;u8 D_800C3E78;static u32 trial,first_calls,second_calls,broken;
 typedef union {u32 u;f32 f;} Word;
 static u32 bits32(f32 f){Word v;v.f=f;return v.u;}
 void func_1505A184(u16 yaw,f32 distance,f32 pitch,f32 *x,f32 *z,f32 *y){const Test *t=tests+trial;first_calls++;
  if(yaw!=t->first[0]||bits32(distance)!=t->first[1]||bits32(pitch)!=t->first[2]||x==z||x==y||z==y)broken=1;
  *x=t->output?-1.25f:11.25f;*z=t->output?2.5f:-22.5f;*y=t->output?-3.75f:33.75f;
  if(t->mutation&1)D_800D154C=&actors[1];if(t->mutation&2)D_8009A094=-0.5f;if(t->mutation&4)D_800C3E78=0x6c;
 }
 s32 func_150E1570(struct127 *a,f32 x,f32 y,f32 z,f32 ex,f32 ey,f32 ez,s32 player,s32 mode){const Test *t=tests+trial;second_calls++;
  if(a!=&actors[(t->mutation&1)?1:0]||bits32(x)!=t->second[0]||bits32(y)!=t->second[1]||bits32(z)!=t->second[2]||bits32(ex)!=t->second[3]||bits32(ey)!=t->second[4]||bits32(ez)!=t->second[5]||player!=(s32)t->player||mode!=18)broken=2;
  return (s32)0xdeadbeef;
 }
 typedef s32 (*Routine)(void);
 static int check(Routine f){u32 i;for(trial=0;trial<sizeof(tests)/sizeof(tests[0]);trial++){const Test*t=tests+trial;
  for(i=0;i<2;i++){actors[i].unk31C=&states[i];actors[i].unk1D1=(s8)(t->pitch+i);actors[i].unk7A=t->angle+i*13;actors[i].unkD6=-30+i*50;states[i].unk12=t->offset-i*9;states[i].timer=t->timer+i;}
  actors[0].x_position=100.5f;actors[0].y_position=-25.25f;actors[0].z_position=300.75f;actors[1].x_position=-200.5f;actors[1].y_position=75.25f;actors[1].z_position=-400.75f;
  D_800D154C=&actors[0];D_8009A094=.25f;D_800C3E78=0xd2;first_calls=second_calls=broken=0;
  if((u32)f()!=0xdeadbeefu||broken||first_calls!=1||second_calls!=1||(u16)states[0].timer!=t->expected_timer)return 1;
  }return 0;}
 static int run(void){if(check(selected))return 10;
 """
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');(O/'native.c').write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=O/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(O/'native.c'),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'native cases',len(rows),'negative controls',len(controls),'UBSan')
