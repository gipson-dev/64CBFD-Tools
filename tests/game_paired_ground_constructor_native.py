"""Native 32-bit checks for typed ground-effect constructors."""
import subprocess
from tools.experiments import game_paired_ground_constructor_match as packet
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_paired_ground_constructor_oracle as model
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
DESC=[(0,4),(4,2),(6,1),(8,4),(12,4),*[(x,1)for x in range(16,24)],(24,4)]
PAYLOAD=[(4,1),(8,4),(12,4),(16,4),(20,2),(22,2),(24,2),(28,4)]
def run():
 report={}
 for spec in packet.MANIFEST['targets']:
  name=spec['name'];first=name.endswith('6460');fn=body(spec['selected_source'],name)
  start=spec['selected_source'].index('typedef struct {\n    u8 *owner;\n    u8 enabled');end=spec['selected_source'].index('s32 '+name+'(',start);decl=spec['selected_source'][start:end]
  controls={'query_high':('local.position[1] + 200.0f','local.position[1] + 199.0f'),'query_low':('local.position[1] - 200.0f','local.position[1] - 199.0f'),'enabled':('local.payload.enabled = 1','local.payload.enabled = 0'),'duration':('local.descriptor.duration = 300','local.descriptor.duration = 301'),'channel':('context[0x0C]','context[0x0D]'),'palette':('index * 3','index * 3 + 1'),'scale':('* 50.0f + 100.0f' if first else '* 100.0f + 200.0f','* 49.0f + 100.0f' if first else '* 99.0f + 200.0f')}
  text='#include <ultra64.h>\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid *memcpy(void *,const void *,u32);\n'+decl+'\n'+fn.replace(name+'(','selected(',1)+'\n'
  for label,(old,new) in controls.items():
   assert fn.count(old)==1,(label,old);text+=fn.replace(name+'(','bad_'+label+'(',1).replace(old,new,1)+'\n'
  vector='D_800887D0' if first else 'D_800887E0';c0='D_800A043C' if first else 'D_800A047C';c1='D_800A0440' if first else 'D_800A0480'
  text+='\nGroundVectorWords '+vector+';\nf32 '+c0+','+c1+';\nu8 D_800AB414[768];\n'
  rows=[]
  for seed in range(5):
   c=model.Case(seed=seed);d,p,_,_=model.expected(c,name);values=[int.from_bytes(d[o:o+n],'big')for o,n in DESC]+[int.from_bytes(p[o:o+n],'big')for o,n in PAYLOAD];rows.append('{'+','.join(str(x)+'u'for x in values)+'}')
  text+='static const u32 expected[][{}]={{\n'.format(len(DESC)+len(PAYLOAD))+',\n'.join(rows)+'\n};\n'
  text+='''
 static u32 owner_words[256],context_words[128],out_words[128],matrix_words[32];static u8 descriptor[40];
 static u32 seed,matrix,hit,success,nquery,ntransform,ncolor,nfloat,nrng,nfactory,ncopy,broken;
 static u32 ints[3]={0xffffffffu,0,0x12345678u};
 void *memcpy(void *d,const void *s,u32 n){u32 i;u8 *dst=d;const u8 *src=s;ncopy++;if(n!=32)broken=1;for(i=0;i<n;i++)dst[i]=src[i];return d;}
 void func_15143134(f32 *p,f32 *o,u8 *m){ntransform++;if(!matrix||m!=(u8*)matrix_words||p[0]!=.5f||p[1]!=1.0f||p[2]!=-.5f)broken=2;o[0]=11.0f;o[1]=22.0f;o[2]=33.0f;}
 s32 func_15045800(f32 *p,u16 mode,f32 low,void *result){f32 x=matrix?11.0f:1.25f,y=matrix?22.0f:4.5f,z=matrix?33.0f:-3.0f;nquery++;if(mode||p[0]!=x||p[1]!=y+200.0f||p[2]!=z||low!=y-200.0f||result!=(u8*)context_words+0x34)broken=3;*(f32*)result=77.25f;return hit;}
 s32 func_151D8E20(void){ncolor++;return 3+seed;}
 f32 func_150ADA68(void){nfloat++;return (f32)seed*.25f;}
 s32 func_150ADA20(void){u32 v=ints[(nrng+seed)%3];nrng++;return (s32)v;}
 u8 *func_1513C73C(s32 d,u8 a,u8 b,s32 target,f32 x,f32 y,f32 z,f32 s0,f32 s1,u8 r,u8 v,s32 count,u8 ch,s32 sel){
  u32 i;u8 *src=(u8*)d,*ctx=(u8*)context_words;f32 scale='''+('100.0f+50.0f' if first else '200.0f+100.0f')+'''*(f32)seed*.25f;nfactory++;
  if(a!='''+('8' if first else '9')+'''||b!='''+('2' if first else '3')+'''||(u32)target!=(u32)(ctx+0x38)||x!=(matrix?11.0f:1.25f)||y!=77.25f||z!=(matrix?33.0f:-3.0f)||s0!=scale||s1!=scale||r!=(u8)ints[seed%3]||v!=(((ints[(seed+2)%3]&1)<<1)+(ints[(seed+1)%3]&1))||count!=32||ch!=ctx[0xc]||sel!=ctx[1])broken=4;
  for(i=0;i<40;i++)descriptor[i]=src[i];return success?(u8*)out_words:(u8*)0;}
 static u32 word(const u8*p){return (u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);}
 static u32 half(const u8*p){return (u32)p[0]|((u32)p[1]<<8);}
 typedef s32 (*Routine)(u8 *);
 static int check(Routine f){u32 i;u8 *a=(u8*)owner_words,*ctx=(u8*)context_words,*out=(u8*)out_words;
 for(seed=0;seed<5;seed++)for(matrix=0;matrix<2;matrix++)for(hit=0;hit<2;hit++)for(success=0;success<2;success++){
  s32 answer;for(i=0;i<sizeof(owner_words);i++)a[i]=(u8)(i*29+seed*13+0x5a);for(i=0;i<sizeof(context_words);i++)ctx[i]=(u8)(i*29+seed*13+0x5a);for(i=0;i<sizeof(out_words);i++)out[i]=0xa5;
  for(i=0;i<768;i++)D_800AB414[i]=(u8)(i*29+seed*13+0x5a);*(u8**)(ctx+0x18)=a;*(u8**)(a+0x1d4)=matrix?(u8*)matrix_words:(u8*)0;
  *(f32*)(a+0x14)=1.25f;*(f32*)(a+0x18)=4.5f;*(f32*)(a+0x1c)=-3.0f;
 '''+vector+'''.coords[0]=.5f;'''+vector+'''.coords[1]=1.0f;'''+vector+'''.coords[2]=-.5f;'''+c0+'''=.25f;'''+c1+'''=.375f;
  nquery=ntransform=ncolor=nfloat=nrng=nfactory=ncopy=broken=0;answer=f(ctx);
  if(broken||nquery!=1||ntransform!=matrix||ncolor!=hit||nfloat!=hit||nrng!=hit*3||nfactory!=hit||ncopy!=hit*success||(u32)answer!=((hit&&success)?(u32)out:0))return 1;
  if(hit){
 '''
  for i,(off,size) in enumerate(DESC):
   expr={1:f'descriptor[{off}]',2:f'half(descriptor+{off})',4:f'word(descriptor+{off})'}[size];text+='if('+expr+'!=expected[seed]['+str(i)+'])return 2;\n'
  text+='if(success){if(word(out+0xb0)!=(u32)ctx)return 3;\n'
  for i,(off,size) in enumerate(PAYLOAD):
   expr={1:f'out[0xb0+{off}]',2:f'half(out+0xb0+{off})',4:f'word(out+0xb0+{off})'}[size];text+='if('+expr+'!=expected[seed]['+str(len(DESC)+i)+'])return 4;\n'
  text+='}\n}\n}return 0;}\nstatic int run(void){if(check(selected))return 10;\n'
  for i,label in enumerate(controls):text+='if(!check(bad_'+label+'))return '+str(20+i)+';\n'
  text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
  file=packet.OUT/(name+'-native.c');file.write_text(text);profiles={}
  for opt in ('-O0','-O2','-O3'):
   exe=packet.OUT/(name+'-native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-fno-builtin-memcpy',str(file),'-o',str(exe)],cwd=packet.ROOT,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr)
   r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0,(name,opt,r.returncode,r.stderr)
   profiles[opt]={'cases':40,'effective_negative_controls':len(controls),'ubsan':True}
  report[name]=profiles
 return report
