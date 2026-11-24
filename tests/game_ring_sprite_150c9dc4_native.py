"""SDK32 sprite C: legal objects, ordered calls and initialized bytes only."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_ring_sprite_150c9dc4_match as p
from tools.tests import game_ring_sprite_150c9dc4_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()

def digest(data):
 a,b=0x811c9dc5,0x9e3779b9
 for v in data:a=((a^v)*16777619)&0xffffffff;b=((b+v+0x7f4a7c15)*0x85ebca6b)&0xffffffff
 return a,b

def snapshot_bytes(s):return s[0]+s[1]+b''.join(v.to_bytes(4,'big')for v in s[2])+s[3]
def selected():
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    f32 field00,field04,');return s[a:s.index('\n/* Integrate position and angles',a)]
def owner_type():
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    u8 reserved00[0x10];');b=s.index('} RingUpdate150C8A68;',a)+len('} RingUpdate150C8A68;');return s[a:b]

def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.alias and not c.point_override));rows=[]
 vector=lambda a:'{'+','.join(str(v)+'U'for v in a)+'}'
 for c in cases:
  wanted,calls,obs,_=g.reference(g.fixture(c),c);events=[]
  for(t,args),ob in zip(calls,obs):
   code={g.RNG:1,g.FRNG:2,g.DIRECTION:3,g.SUBMIT:4,g.RGB:5}[t];arguments=list(args)+[0]*(6-len(args));h=digest(snapshot_bytes(ob[0]));mask=g.BEFORE_DIRECTION if t==g.DIRECTION else g.KNOWN if t==g.SUBMIT else();ph=digest(bytes(ob[1][i]for i in mask));events.append('{'+str(code)+','+vector(arguments)+','+vector(h)+','+vector(ph)+'}')
  assert len(events)==14;values=(c.angle,c.slot,c.context,c.base,c.outcome,c.mode,c.fcsr,c.seed,c.unused_sine,c.unused_cosine);final=digest(snapshot_bytes(g.snapshot(wanted,c)));rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+','+vector(c.point)+','+vector(c.rng)+','+vector(c.samples)+','+vector(c.constants)+','+vector(final)+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n#include "structs.h"\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_15143794(s16,s16,f32,vertex*);\n'+owner_type()+'\n'+selected()+'''
typedef char packet_size[sizeof(RingSprite150C9DC4)==0x7c?1:-1];
typedef char packet_direction[__builtin_offsetof(RingSprite150C9DC4,direction)==0x34?1:-1];
typedef char packet_flags[__builtin_offsetof(RingSprite150C9DC4,field50)==0x50?1:-1];
typedef char owner_size[sizeof(RingUpdate150C8A68)==84?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[6];Hash state,packet;}Event;
typedef struct{u32 angle,slot,context,base,outcome,mode,fcsr,seed,unused_sine,unused_cosine,point[3],rng[3],samples[8],constants[8];Hash final;Event event[14];}Row;
static const Row rows[]={\n'''+',\n'.join(rows)+'''};
typedef union{u64 align;RingUpdate150C8A68 effect;u8 bytes[84];}Arena;
static Arena arena;static vertex input;static u8 marks[32];static const Row*c;static u32 bad,event_index,rng_count,float_count;
f32 D_800A0580,D_800A0584,D_800A0588,D_800A058C,D_800A0590,D_800A0594,D_800A0598,D_800A059C;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};for(int i=0;i<84;i++){if(i>=0x20&&i<0x24)feed(&h,bits(arena.effect.growthRate)>>(8*(0x23-i)));else feed(&h,arena.bytes[i]);}word(&h,bits(input.x));word(&h,bits(input.y));word(&h,bits(input.z));word(&h,bits(D_800A0580));word(&h,bits(D_800A0584));word(&h,bits(D_800A0588));word(&h,bits(D_800A058C));word(&h,bits(D_800A0590));word(&h,bits(D_800A0594));word(&h,bits(D_800A0598));word(&h,bits(D_800A059C));for(int i=0;i<32;i++)feed(&h,marks[i]);return h;}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static u8 packet_byte(const RingSprite150C9DC4*packet,int at){const u8*p=(const u8*)packet;static const u8 offsets[]={0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64,68,72,76,80,84,86,92,108,114,116};static const u8 widths[]={4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,2,2,4,4,2,2};for(unsigned i=0;i<sizeof(offsets);i++){int start=offsets[i],n=widths[i];if(at>=start&&at<start+n){u32 v=0;for(int j=n-1;j>=0;j--)v=(v<<8)|p[start+j];return v>>(8*(n-1-at+start));}}return p[at];}
static void check(u32 code,u32 a0,u32 a1,u32 a2,u32 a3,u32 a4,u32 a5,const RingSprite150C9DC4*packet){if(event_index>=14){bad=1;return;}const Event*e=&c->event[event_index++];u32 a[]={a0,a1,a2,a3,a4,a5};if(code!=e->code)bad=1;for(int i=0;i<6;i++)if(a[i]!=e->args[i])bad=1;Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;h=(Hash){0x811c9dc5U,0x9e3779b9U};if(packet)for(int i=0;i<124;i++){int known=code==3?(i<8||(i>=0x10&&i<0x34)||(i>=0x44&&i<0x48)||(i>=0x50&&i<0x54)||(i>=0x56&&i<0x58)):(i<0x59||(i>=0x5c&&i<0x69)||i==0x6a||(i>=0x6c&&i<0x71)||(i>=0x72&&i<0x76));if(known)feed(&h,packet_byte(packet,i));}if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;}
void func_150CCD90(f32 level,f32*red,f32*green,f32*blue){check(5,bits(level),0x40000-128,0x40000-132,0x40000-136,0,0,0);mark_call();*red=88.;*green=77.;*blue=66.;if(c->mode&1){input.x=-1.;input.y=4.;input.z=8.;}}
s32 func_150ADA20(void){check(1,0,0,0,0,0,0,0);mark_call();++rng_count;if(c->mode&1){if(rng_count==1)arena.effect.growthRate=-3.;if(rng_count==2)arena.bytes[1]=0x91;if(rng_count==3)input.x=-11.;}return(s32)c->rng[rng_count-1];}
f32 func_150ADA68(void){check(2,0,0,0,0,0,0,0);mark_call();++float_count;if(c->mode&2){if(float_count==1){input.x=5.;input.y=-7.;input.z=9.;}if(float_count==4){arena.effect.growthRate=4.;D_800A0584=.015625f;}if(float_count==5)D_800A0588=.125f;if(float_count==6)D_800A058C=.25f;if(float_count==7){D_800A0590=1000.;D_800A0594=-1500.;D_800A0598=.00125f;}if(float_count==8)D_800A059C=.00125f;}return floating(c->samples[float_count-1]);}
void func_15143794(s16 angle,s16 pitch,f32 speed,vertex*out){const RingSprite150C9DC4*packet=(const RingSprite150C9DC4*)((const u8*)out-__builtin_offsetof(RingSprite150C9DC4,direction));check(3,(u32)(s32)angle,(u32)(s32)pitch,bits(speed),0x40000-124+0x34,0,0,packet);mark_call();out->x=(f32)pitch*.125f;out->y=-speed;out->z=(f32)(angle&255)*.125f;if(c->mode&4){arena.bytes[12]=0xa7;arena.bytes[1]=0xfe;}}
void*func_15132A4C(void*packet,s32 resource,s32 value,s32 bytes,u8 slot,s32 context){check(4,0x40000-124,(u32)resource,(u32)value,(u32)bytes,slot,(u32)context,packet);mark_call();if(c->mode&8){arena.effect.growthRate=17.;input.x=-11.;}return c->outcome?(void*)0x90000:0;}
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=rng_count=float_count=0;for(int i=0;i<84;i++)arena.bytes[i]=((i+16)*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;arena.bytes[1]=(u8)c->context;arena.bytes[12]=(u8)c->slot;arena.effect.growthRate=floating(c->base);input.x=floating(c->point[0]);input.y=floating(c->point[1]);input.z=floating(c->point[2]);D_800A0580=floating(c->constants[0]);D_800A0584=floating(c->constants[1]);D_800A0588=floating(c->constants[2]);D_800A058C=floating(c->constants[3]);D_800A0590=floating(c->constants[4]);D_800A0594=floating(c->constants[5]);D_800A0598=floating(c->constants[6]);D_800A059C=floating(c->constants[7]);u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");func_150C9DC4(&arena.effect,&input,(u8)c->angle,floating(c->unused_sine),floating(c->unused_cosine));Hash h=snapshot();if(event_index!=14||rng_count!=3||float_count!=8||h.a!=c->final.a||h.b!=c->final.b)bad=1;if(bad)return 42;
 }return 0;}
__attribute__((force_align_arg_pointer))void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 return text,len(cases)

def main():
 text,count=generate();profiles={};controls=[]
 def run(name,body,opt):
  f=p.OUT/(name+'.c');exe=p.OUT/(name+'.exe');f.write_text(body);command=native_command(opt)+['-frounding-math','-fno-builtin',str(f),'-o',str(exe)];q=subprocess.run(command,cwd=p.ROOT,capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True,text=True);return dict(exit=q.returncode,source_sha256=sha(f),binary_sha256=sha(exe),command=command)
 for opt in('-O0','-O2','-O3'):
  q=run('native-'+opt[1:],text,opt);assert q['exit']==0,q;profiles[opt[1:]]=q
 original=selected();mutations=[('flags','packet.field50 = 0x29E8','packet.field50 = 0x29E9'),('lifetime','% 41U','% 40U'),('alpha','% 101U','% 100U'),('rotation','func_150ADA68() * 360.0f','func_150ADA68() * 361.0f'),('size','* 400.0f','* 401.0f'),('acceleration','+ D_800A0594','+ D_800A0590'),('pitch','% 26U - 45','% 26U - 44'),('speed','* D_800A0584','* D_800A0588'),('slot-context','((u8 *)owner)[0xC],((u8 *)owner)[1]','((u8 *)owner)[1],((u8 *)owner)[0xC]'),('payload','func_15132A4C(&packet,3,255,0,','func_15132A4C(&packet,3,255,4,'),('resource','func_15132A4C(&packet,3,','func_15132A4C(&packet,4,'),('last-field','packet.field74 = 7','packet.field74 = 8')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_angles=True,canonical_dual32_memory_digests=True,only_initialized_packet_bytes_observed=True,legal_nonoverlapping_bounded_objects=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
