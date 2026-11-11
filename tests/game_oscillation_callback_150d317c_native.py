"""Typed SDK32 cases for defined conversions, with incorrect-C controls."""
import itertools,json,math,subprocess
from tools.experiments import game_oscillation_callback_150d317c_match as p
from tools.tests import game_oscillation_callback_150d317c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=(p.out/'selected-source.c').read_text(encoding='utf-8');head=selected[:selected.index('typedef struct ReloadRecord')];body=p.body(selected,p.NAME)
 controls={'missing_x_step':('record->motion.speedX * D_800BE9A4','record->motion.speedY * D_800BE9A4'),'wrong_y_step':('record->motion.speedY * D_800BE9A4','record->motion.speedX * D_800BE9A4'),'wrong_x_base':('motion->amplitudeX + motion->baseX','motion->amplitudeX + motion->baseY'),'wrong_y_base':('motion->amplitudeY + motion->baseY','motion->amplitudeY + motion->baseX'),'wrong_timer':('motion->timer -= D_800BE9A4','motion->timer += D_800BE9A4'),'wrong_opacity':('motion->opacityRate * motion->timer','motion->opacityRate + motion->timer'),'wrong_return':('motion->timer > 0.0f','motion->timer >= 0.0f'),'wrong_x_sine':('sinf(motion->phaseX)','sinf(motion->phaseY)')}
 rows=[]
 for timer,rate,mutation in itertools.product((g.bits(-1.),0,g.bits(.5),g.bits(1.),g.bits(3.),g.bits(255.)),(0,g.bits(1.),g.bits(2.),g.bits(100.)),range(8)):
  c=g.Case(timer=timer,rate=rate,mutation=mutation);initial=g.fixture(c);want,calls,ret=g.reference(initial,c);t=g.floating(g.read(want,g.ACTOR+0x138));rate0=g.floating(g.read(want,g.ACTOR+0x13C));value=g.rounded(t*rate0)
  if not math.isfinite(value)or value<0 or value>=2**32:continue
  fields=[g.read(want,g.ACTOR+off)for off in(0x110,0x114,0x118,0x11C,0x120,0x124,0x128,0x12C,0x130,0x134,0x138,0x13C)]
  rows.append((timer,rate,mutation,ret,want[g.ACTOR+0x5C],[v for _,v in calls],fields))
 assert rows
 code=head+r'''
_Static_assert(sizeof(void*)==4,"SDK32");
_Static_assert(__builtin_offsetof(OscillatingRecordFFBA0,opacity)==0x5c && __builtin_offsetof(OscillatingRecordFFBA0,motion)==0x110 && sizeof(OscillationFFBA0)==0x30,"record layout");
typedef struct {u32 timer,rate,mutation,result,opacity,calls[4],fields[12];} Fixture;
static OscillatingRecordFFBA0 actor;static const Fixture *current;static u32 calls,bad;
f32 D_800BE9A4;
static f32 asfloat(u32 n){union{u32 u;f32 f;}v;v.u=n;return v.f;}
static u32 asbits(f32 n){union{u32 u;f32 f;}v;v.f=n;return v.u;}
static f32 effect(f32 x,u32 stage){
 static const u32 returns[]={0x3e000000u,0x3f200000u,0x3f000000u,0xbe800000u};
 if(calls!=stage || asbits(x)!=current->calls[stage])bad=1;calls++;
 if((current->mutation&1)&&stage==0){actor.motion.phaseY=1.25f;D_800BE9A4=.5f;}
 if((current->mutation&2)&&stage==2){actor.motion.amplitudeX=4.f;actor.motion.phaseY=1.5f;}
 if((current->mutation&4)&&stage==3){actor.motion.baseY=12.f;actor.motion.timer=2.f;D_800BE9A4=.25f;}
 return asfloat(returns[stage]);
}
f32 func_15144B68(f32 x){return effect(x,calls);}
f32 sinf(f32 x){return effect(x,calls);}
'''
 variants={'selected':body}
 for name,(old,new)in controls.items():assert old in body;variants[name]=body.replace(old,new,1)
 for name,text in variants.items():code+='\n'+text.replace(p.NAME,'test_'+name,1)+'\n'
 code+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{%du,%du,%du,%du,%du,{%s},{%s}}'%(t,r,m,ret,a,','.join(str(x)+'u'for x in calls0),','.join(str(x)+'u'for x in fields))for t,r,m,ret,a,calls0,fields in rows)+'\n};\n'
 code+=r'''
typedef s32(*Update)(OscillatingRecordFFBA0*);
static int check(Update fn){u32 n,i;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;calls=bad=0;for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=(u8)(i*29+90);D_800BE9A4=1.f;
 actor.motion.x=0;actor.motion.y=0;actor.motion.baseX=10.f;actor.motion.baseY=-10.f;actor.motion.amplitudeX=2.f;actor.motion.amplitudeY=3.f;actor.motion.phaseX=.25f;actor.motion.phaseY=.75f;actor.motion.speedX=.5f;actor.motion.speedY=-.25f;actor.motion.timer=asfloat(current->timer);actor.motion.opacityRate=asfloat(current->rate);
 if(fn(&actor)!=(s32)current->result||bad||calls!=4||actor.opacity!=current->opacity)return 1;
 if(CHECK_FIELDS)return 2;}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows))).replace('CHECK_FIELDS',' || '.join('asbits(actor.motion.%s)!=current->fields[%d]'%(name,i)for i,name in enumerate(('x','y','baseX','baseY','amplitudeX','amplitudeY','phaseX','phaseY','speedX','speedY','timer','opacityRate'))))
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=p.out/'native.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=p.out/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,(opt,build.stdout,build.stderr);run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(cases=len(rows),controls=len(controls),UBSan=True,typed_layout_asserted=True)
 r=dict(profiles=reports,finite_float_to_u32_in_range_only=True,nonfinite_and_out_of_range_guest_only=True,source_installed=False);(p.out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
