"""Native32 defined-packet regression and effective source controls."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_randomized_short_packet_151a0c0c_match as m
from tools.tests import game_randomized_short_packet_151a0c0c_oracle as g
r,o=m.ROOT,m.OUT
def main():
 record=json.loads((m.FROZEN/'fingerprints.json').read_text())
 def immutable():
  m.check_inputs()
 immutable()
 cases=[g.Case(seed=i%8,mode=i,style=style,heading=(0,63,64,255,0x12340080)[i%5],x=(-0.0,0.125,7.75,-19.375,127.5)[i%5],y=-2.25-i,z=0.75+i)for i in range(256)for style in(0,1)]
 retail=g.programs if hasattr(g,'programs')else None
 import struct
 words=list(struct.unpack_from('>141I',(r/'conker/conker.us.bin').read_bytes(),0x1CE0BC));rows=[]
 for c in cases:
  packet,calls=g.reference(c);q=g.Machine(words,c).run();assert q.payloads[0][0]==packet and q.calls==calls
  sine=[args[0]for target,args in calls if target==g.S['func_151423D8']]
  rows.append('{%d,%d,%du,%du,{%s},{%s},{%s}}'%(c.seed,c.style,g.u32(c.heading),c.mode,','.join('%du'%g.bits(v)for v in(c.x,c.y,c.z)),','.join(map(str,sine)),','.join(map(str,packet))))
 vectors='static const struct Vector vectors[] = {\n'+',\n'.join(rows)+'\n};\n'
 fields=[(12,2),(14,2),(16,2),(18,2),(20,2),(22,2),(24,2),(28,1),(29,1),(30,1),(31,1),(32,2),(34,2),(36,2),(38,2),(40,2),(42,1),(44,1),(45,1),(46,1),(47,1),(48,1),(49,1),(50,1),(52,2)]
 prefix='''typedef signed int s32; typedef unsigned int u32; typedef signed short s16; typedef unsigned short u16; typedef signed char s8; typedef unsigned char u8; typedef float f32;
 #define offsetof(type,field) __builtin_offsetof(type,field)
 void *memcpy(void *destination,const void *source,unsigned n){u8 *d=destination;const u8 *s=source;for(unsigned i=0;i<n;i++)d[i]=s[i];return destination;}
 __attribute__((noreturn)) static void quit(int code){__asm__ volatile(".byte 0xcd,0x80" : : "a"(1), "b"(code) : "memory");__builtin_unreachable();}
 s32 func_150ADA20(void); f32 func_150ADA68(void); f32 func_151423D8(u8);
 '''
 declarations=m.PIN['declarations'];body=m.PIN['source']
 harness='''
 _Static_assert(sizeof(void *)==4,"native32 required");
 _Static_assert(sizeof(RandomShortPacket151A0C0C)==56,"packet extent");
 _Static_assert(offsetof(RandomShortPacket151A0C0C,positionX)==16,"position");
 _Static_assert(offsetof(RandomShortPacket151A0C0C,directionY)==32,"Y direction");
 _Static_assert(offsetof(RandomShortPacket151A0C0C,fixed34)==52,"tail field");
 u8 D_800918A0[1], D_8009187C[1], D_8008F8D0[16]={128,128};
 const f32 D_800A8D14=503.0f,D_800A8D18=801.0f;
 struct Vector {u32 seed,style,heading,mode,xyz[3],sine[4]; u8 packet[56];};
 VECTORS
 static const unsigned fields[][2]={FIELDS};
 static const struct Vector *v; static unsigned event_index,ri,si,submits;
 static void check(int good) {if(!good)quit(3);}
 static void event(unsigned kind){static const unsigned order[]={1,2,2,2,2,3,1,1,1,4};check(event_index<10);check(order[event_index++]==kind);}
 static float fp(u32 value){float f;memcpy(&f,&value,4);return f;}
 s32 func_150ADA20(void){static const u32 values[]={0,1,2,5,17,255,0xffffffffu,3};u32 a;event(1);a=values[(ri+++v->seed)%8];return (s32)a;}
 f32 func_150ADA68(void){static const float values[]={0.0f,0.25f,0.5f,0.75f,-0.5f,1.25f,-1.5f,2.0f};event(3);return values[v->seed%8];}
 f32 func_151423D8(u8 angle){static const float values[]={0.0f,0.25f,-0.5f,0.75f,-1.0f,1.5f};unsigned ordinal=si++;event(2);check(ordinal<4&&angle==v->sine[ordinal]);return values[(ordinal+angle+v->seed)%6];}
 void func_15167D84(void *input,s32 kind,s32 offset,s8 marker,u8 mode,s32 owner){
  RandomShortPacket151A0C0C *packet=input;unsigned i,j;event(4);submits++;
  check(kind==0&&offset==0&&marker==-1&&mode==v->mode&&owner==1);
  check(packet->template==(v->style==0?D_800918A0:D_8009187C));
  for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){
   unsigned at=fields[i][0],width=fields[i][1];u32 expected=0,actual=0;
   for(j=0;j<width;j++)expected=(expected<<8)|v->packet[at+j];
   if(width==1)actual=((const u8*)packet)[at];else{u16 half;memcpy(&half,(const u8*)packet+at,2);actual=half;}
   check(actual==expected);
  }
 }
 static int run(void){unsigned i;for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){
  s32 result;v=&vectors[i];event_index=ri=si=submits=0;
  result=func_151A0C0C(1,(s32)0x87654321u,fp(v->xyz[0]),fp(v->xyz[1]),fp(v->xyz[2]),0,0,0,(s32)v->heading,255,0.5f,(s32)v->style,1.0f,0,(u8)v->mode);
  check(result==1&&event_index==10&&ri==4&&si==4&&submits==1);
  }return 0;}
 '''.replace('VECTORS',vectors).replace('FIELDS',','.join('{%d,%d}'%pair for pair in fields))+START
 profiles=[];environment=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 flags=native_command('-O0')+['-std=gnu11','-mstackrealign','-fsanitize=float-cast-overflow','-fno-sanitize-recover=all']
 def run(label,source,options):
  path=o/(label+'.c');path.write_text(source);exe=o/label
  p=subprocess.run([*flags,*options,'-o',str(exe),str(path)],capture_output=True,text=True);assert p.returncode==0 and not p.stderr,(label,p.stderr)
  return subprocess.run([str(exe)],capture_output=True,text=True,env=environment)
 for opt in ('-O0','-O2','-O3'):
  for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
   label='native'+opt+alias;p=run(label,prefix+declarations+'\n'+body+harness,[opt,alias]);assert p.returncode==0,(label,p.stdout,p.stderr)
   assert not p.stdout and not p.stderr;profiles.append(dict(options=[opt,alias],cases=512,UBSan_clean=True,float_cast_overflow_clean=True))
 controls={
  'fractional-y':body.replace('(s8)(s32)(x * 256.0f)','(s8)(s32)(y * 256.0f)'),
  'signed-remainder':body.replace('(u32)func_150ADA20() % 15U','func_150ADA20() % 15'),
  'direct-float-byte-cast':body.replace('(s8)(s32)(x * 256.0f)','(s8)(x * 256.0f)'),
  'wrong-template':body.replace('packet.template = D_800918A0','packet.template = D_8009187C'),
 }
 neg=[]
 for label,changed in controls.items():
  assert changed!=body;p=run('negative-'+label,prefix+declarations+'\n'+changed+harness,['-O2','-fstrict-aliasing']);assert p.returncode!=0,('ineffective source control',label);(o/('negative-'+label+'.txt')).write_text(p.stdout+p.stderr);neg.append(label)
 immutable();report=dict(private_only=True,c_match_credit=0,cases_per_profile=512,profiles=profiles,total_native_executions=3072,retail_guest_vectors=512,defined_packet_bytes_compared=42,private_representation_bytes_not_fixed=14,valid_template_styles=[0,1],all256_mode_bytes=True,controls=neg,source_sha256=hashlib.sha256(body.encode()).hexdigest(),native32=True,portable_FP_domain='finite inputs and intermediates within s32 truncation range')
 (o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=="__main__":main()
