"""Native32 semantic, layout and effective-control qualification for func_15152874."""
import json,subprocess

def qualify(root,output,source,headers):
 prefix='typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'+'\n'.join(headers.splitlines()[1:])+'\n'
 suffix=r'''
typedef struct {u32 mode,extra,seed,mutation;ColorEffectInput before;} TestCase;
static TestCase current;
static ColorEffectInput live,expectedLive;
static ColorEffectPacket expectedPackets[8];
static u32 expectedCount,expectedIntegers,expectedReals,integerIndex,realIndex,submitIndex,bad;
static u32 ub(f32 value){union{f32 f;u32 u;}x;x.f=value;return x.u;}
static u32 rngInteger(u32 index,u32 seed){static const u32 values[4]={0,1,255,0xFFFFFFFFu};return values[(index+seed)&3];}
static f32 rngReal(u32 index,u32 seed){static const f32 values[4]={0.0f,0.25f,0.5f,0.75f};return values[(index+seed)&3];}
static void mutate(ColorEffectInput *p,u32 late){
 if(!(current.mutation&(late?2u:1u)))return;
 p->position.x=-8.0f;p->position.y=9.0f;p->position.z=-10.0f;
 p->firstBase=-12;p->firstRange=20;p->secondBase=6;p->secondRange=18;
 p->radiusBase=1.0f;p->radiusRange=2.0f;p->field24=9.0f;
 p->scaleBase=3.0f;p->scaleRange=5.0f;p->lifetimeBase=7;p->lifetimeRange=3;
 p->field38=6.0f;p->field3C=7.0f;p->field40=8.0f;p->field44=9.0f;p->field48=10.0f;
}
static void writeVector(s16 first,s16 second,f32 radius,f32 *out){out[0]=(f32)first*.125f;out[1]=(f32)second*.25f;out[2]=radius*.5f;}
static void writeColors(u8 *out,u32 seed,u32 index){u32 i;for(i=0;i<4;i++)out[i]=(u8)(seed*31+index*47+i*53+17);}
static void reference(void){
 ColorEffectInput input=current.before;ColorEffectPacket packet;u32 remaining,first,second,ni=0,nf=0,n=0;
 first=rngInteger(ni++,current.seed);mutate(&input,0);
 remaining=first/((u32)input.countRange+1u);remaining=first-remaining*((u32)input.countRange+1u)+(u32)input.baseCount;
 packet.position=input.position;packet.field18=input.field24;packet.field30=input.field48;
 while(remaining){
  first=rngInteger(ni++,current.seed);second=rngInteger(ni++,current.seed);
  writeVector((s16)(first%(u32)(input.firstRange+1)+input.firstBase),(s16)(second%(u32)(input.secondRange+1)+input.secondBase),rngReal(nf++,current.seed)*input.radiusRange+input.radiusBase,packet.direction);
  packet.scale=rngReal(nf++,current.seed)*input.scaleRange+input.scaleBase;
  first=rngInteger(ni++,current.seed);packet.lifetime=first%(u32)(input.lifetimeRange+1)+input.lifetimeBase;
  packet.field28=rngReal(nf++,current.seed)*input.field40+input.field38;
  packet.field2C=rngReal(nf++,current.seed)*input.field44+input.field3C;
  if(input.colorSelector!=-1)writeColors(packet.colors,current.seed,n);else{packet.colors[0]=255;packet.colors[1]=255;packet.colors[2]=255;packet.colors[3]=255;}
  expectedPackets[n++]=packet;mutate(&input,1);remaining--;
 }
 expectedCount=n;expectedIntegers=ni;expectedReals=nf;expectedLive=input;
}
static int samePacket(const ColorEffectPacket *a,const ColorEffectPacket *b){u32 i;
 if(ub(a->position.x)!=ub(b->position.x)||ub(a->position.y)!=ub(b->position.y)||ub(a->position.z)!=ub(b->position.z))return 0;
 for(i=0;i<3;i++)if(ub(a->direction[i])!=ub(b->direction[i]))return 0;
 if(ub(a->field18)!=ub(b->field18)||ub(a->scale)!=ub(b->scale)||a->lifetime!=b->lifetime||ub(a->field28)!=ub(b->field28)||ub(a->field2C)!=ub(b->field2C)||ub(a->field30)!=ub(b->field30))return 0;
 for(i=0;i<4;i++){if(a->colors[i]!=b->colors[i])return 0;}return 1;
}
s32 func_150ADA20(void){u32 value=rngInteger(integerIndex++,current.seed);if(integerIndex==1)mutate(&live,0);return(s32)value;}
f32 func_150ADA68(void){return rngReal(realIndex++,current.seed);}
void func_15143794(s16 first,s16 second,f32 radius,f32 *out){writeVector(first,second,radius,out);}
static void callback0(u8 *out){writeColors(out,current.seed,submitIndex);}
void (*D_8008AC60[])(u8 *)={callback0};
s32 func_150CCEB0(ColorEffectPacket *packet,u8 mode,u8 extra){
 if(submitIndex>=expectedCount||mode!=(u8)current.mode||extra!=(u8)current.extra||!samePacket(packet,&expectedPackets[submitIndex]))bad=1;
 submitIndex++;mutate(&live,1);return 0x76543210;
}
static void initialize(u32 mode){u32 i;u8 *p=(u8*)&current.before;for(i=0;i<sizeof(current.before);i++)p[i]=(u8)(i*29+mode*13+91);
 current.before.baseCount=(s32)(mode%3);current.before.countRange=(s32)(mode%3);
 current.before.position.x=1.25f;current.before.position.y=-2.5f;current.before.position.z=3.75f;
 current.before.firstBase=-30;current.before.firstRange=60;current.before.secondBase=15;current.before.secondRange=45;
 current.before.radiusBase=2.0f;current.before.radiusRange=4.0f;current.before.field24=.75f;
 current.before.scaleBase=1.0f;current.before.scaleRange=3.0f;current.before.colorSelector=(mode&1)?0:-1;
 current.before.lifetimeBase=20;current.before.lifetimeRange=8;
 current.before.field38=.5f;current.before.field3C=1.5f;current.before.field40=2.5f;current.before.field44=3.5f;current.before.field48=4.5f;
 current.mode=mode;current.extra=mode*0x87654321u;current.seed=mode&3;current.mutation=mode&3;
}
static void(*volatile invoke)(ColorEffectInput*,u8,s32)=func_15152874;
int run(void){u32 mode,i;u8 *a,*b;
 if(sizeof(void*)!=4||sizeof(ColorEffectInput)!=76||sizeof(ColorEffectPacket)!=56||__builtin_offsetof(ColorEffectPacket,privateTail34)!=52)return 9;
 for(mode=0;mode<256;mode++){
  initialize(mode);reference();live=current.before;integerIndex=realIndex=submitIndex=bad=0;invoke(&live,(u8)current.mode,(s32)current.extra);
  if(bad||submitIndex!=expectedCount||integerIndex!=expectedIntegers||realIndex!=expectedReals)return 1;
  a=(u8*)&live;b=(u8*)&expectedLive;for(i=0;i<sizeof(live);i++){if(a[i]!=b[i])return 1;}
 }
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
 early=source.replace('void func_15152874(ColorEffectInput *input, u8 mode, s32 extra) {','void func_15152874(ColorEffectInput *input, u8 mode, s32 extra) {\n    ColorEffectInput cached = *input;').replace('input->','cached.')
 controls={
  'selected':(source,headers),
  'unsigned-RNG':(source.replace('(u32)func_150ADA20()','((u32)func_150ADA20() & 0x7FFFFFFFU)'),headers),
  'count':(source.replace('(u32)input->baseCount','((u32)input->baseCount + 1U)'),headers),
  'first-angle':(source.replace('input->firstBase','(input->firstBase + 1)'),headers),
  'lifetime':(source.replace('input->lifetimeBase','(input->lifetimeBase + 1)'),headers),
  'scale':(source.replace('input->scaleRange','input->field40'),headers),
  'color':(source.replace('if (input->colorSelector != -1)','if (0)'),headers),
  'mode':(source.replace('    ColorEffectPacket packet;','    ColorEffectPacket packet;\n    (void)mode;').replace('(u8)mode, (u8)extra','(u8)0, (u8)extra'),headers),
  'extra':(source.replace('    ColorEffectPacket packet;','    ColorEffectPacket packet;\n    (void)extra;').replace('(u8)mode, (u8)extra','(u8)mode, (u8)0'),headers),
  'radius':(source.replace('input->radiusBase','input->scaleBase'),headers),
  'cached-input':(early,headers),
  'packet-extent':(source,headers.replace('    u8 privateTail34[4];\n','    u8 privateTail34[8];\n')),
 }
 assert all(body!=source or name in('selected','packet-extent') for name,(body,_) in controls.items())
 results=[]
 for opt in('-O0','-O2','-O3'):
  for label,(body,head) in controls.items():
   path=output/('native-%s-%s.c'%(label,opt[1:]));path.write_text('typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'+'\n'.join(head.splitlines()[1:])+'\n'+body+'\n'+suffix);binary=path.with_suffix('.bin')
   command=['cc','-m32',opt,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign','-fexcess-precision=standard','-fno-builtin','-fno-strict-aliasing','-ffp-contract=off','-ffreestanding','-static','-fno-stack-protector','-fno-pie','-no-pie','-nostdlib','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(path)]
   q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0,(opt,label,q.stderr[-8000:])
   q=subprocess.run([str(binary)],capture_output=True,timeout=20)
   assert (q.returncode==0)==(label=='selected'),(opt,label,q.returncode,q.stdout,q.stderr);results.append(dict(profile=opt,label=label,status=q.returncode))
 report=dict(success=True,cases_per_profile=256,profiles=['O0','O2','O3'],effective_controls_each=len(controls)-1,input_size=76,packet_visible_bytes=52,packet_private_extent=56,private_tail_not_read_by_submit=True,all256_mode_bytes=True,extra_low_byte=True,unsigned_count_and_RNG=True,signed_angle_and_lifetime_fields=True,default_and_callback_color_paths=True,live_input_after_first_RNG_and_submit=True,finite_float_domain=True,UBSan=True,results=results)
 (output/'private-native-v1.json').write_text(json.dumps(report,indent=2)+'\n');return report
