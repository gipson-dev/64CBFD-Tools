"""SDK32 particle C: observable calls and initialized packet bytes only."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_ring_emitter_150c99b4_match as p
from tools.tests import game_ring_emitter_150c99b4_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def digest(data):
 a,b=0x811c9dc5,0x9e3779b9
 for v in data:a=((a^v)*16777619)&0xffffffff;b=((b+v+0x7f4a7c15)*0x85ebca6b)&0xffffffff
 return a,b
def snapshot_bytes(s):return s[0]+s[1]+b''.join(v.to_bytes(4,'big')for v in s[2])+s[3]
def selected():
 s=p.MANIFEST['selected_source'];return s[s.index('typedef struct {\n    u32 field00,field04;'):s.index('\ns32 func_150C9BDC(')]
def owner_type():
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    u8 reserved00[0x10];');b=s.index('} RingUpdate150C8A68;',a)+len('} RingUpdate150C8A68;');return s[a:b]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.alias and not c.point_override));rows=[]
 for c in cases:
  initial=g.fixture(c);wanted,calls,obs,fcsr=g.reference(initial,c);events=[]
  for(t,args),ob in zip(calls,obs):
   code={g.RNG:1,g.FRNG:2,g.DIRECTION:3,g.SUBMIT:4}[t];arguments=list(args)+[0]*(5-len(args));h=digest(snapshot_bytes(ob[0]));mask=g.BEFORE_DIRECTION if t==g.DIRECTION else g.KNOWN if t==g.SUBMIT else();ph=digest(bytes(ob[1][i]for i in mask))
   events.append('{'+str(code)+',{'+','.join(str(v)+'U'for v in arguments)+'},{'+','.join(str(v)+'U'for v in h)+'},{'+','.join(str(v)+'U'for v in ph)+'}}')
  assert len(events)==10;values=(c.angle,c.slot,c.context,c.base,c.outcome,c.mode,c.fcsr,c.seed,c.unused_sine,c.unused_cosine);final=digest(snapshot_bytes(g.snapshot(wanted,c)))
  vector=lambda a:'{'+','.join(str(v)+'U'for v in a)+'}'
  rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+','+vector(c.point)+','+vector(c.rng)+','+vector(c.samples)+','+vector(c.constants)+','+vector(final)+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n#include "structs.h"\ns32 func_150ADA20(void);\n'+owner_type()+'\n'+selected()+'''
typedef char packet_size[sizeof(RingParticle150C99B4)==0x70?1:-1];
typedef char packet_direction[__builtin_offsetof(RingParticle150C99B4,direction)==0x48?1:-1];
typedef char packet_flags[__builtin_offsetof(RingParticle150C99B4,flags)==0x58?1:-1];
typedef char owner_size[sizeof(RingUpdate150C8A68)==84?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[5];Hash state,packet;}Event;
typedef struct{u32 angle,slot,context,base,outcome,mode,fcsr,seed,unused_sine,unused_cosine,point[3],rng[5],samples[3],constants[4];Hash final;Event event[10];}Row;
static const Row rows[]={\n'''+',\n'.join(rows)+'''};
typedef union{u64 align;RingUpdate150C8A68 effect;u8 bytes[84];}Arena;
static Arena arena;static vertex input;static u8 marks[32];static const Row*c;static u32 bad,event_index,rng_count,float_count;
f32 D_800A0570,D_800A0574,D_800A0578,D_800A057C;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};for(int i=0;i<84;i++){if(i>=0x20&&i<0x24)feed(&h,bits(arena.effect.growthRate)>>(8*(0x23-i)));else feed(&h,arena.bytes[i]);}word(&h,bits(input.x));word(&h,bits(input.y));word(&h,bits(input.z));word(&h,bits(D_800A0570));word(&h,bits(D_800A0574));word(&h,bits(D_800A0578));word(&h,bits(D_800A057C));for(int i=0;i<32;i++)feed(&h,marks[i]);return h;}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static u8 packet_byte(const RingParticle150C99B4*packet,int at){const u8*p=(const u8*)packet;static const u8 offsets[]={0,4,8,10,12,16,30,32,34,36,40,44,48,52,56,60,64,68,72,76,80,84,88};static const u8 widths[]={4,4,2,2,4,4,2,2,2,4,4,4,4,4,4,4,4,4,4,4,4,4,4};for(unsigned i=0;i<sizeof(offsets);i++){int start=offsets[i],n=widths[i];if(at>=start&&at<start+n){u32 v=0;for(int j=n-1;j>=0;j--)v=(v<<8)|p[start+j];return v>>(8*(n-1-at+start));}}return p[at];}
static void check(u32 code,u32 a0,u32 a1,u32 a2,u32 a3,u32 a4,const RingParticle150C99B4*packet){if(event_index>=10){bad=1;return;}const Event*e=&c->event[event_index++];u32 a[]={a0,a1,a2,a3,a4};if(code!=e->code)bad=1;for(int i=0;i<5;i++)if(a[i]!=e->args[i])bad=1;Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;h=(Hash){0x811c9dc5U,0x9e3779b9U};if(packet)for(int i=0;i<112;i++){int known=i<0x5c||(i>=0x60&&i<0x64);if(code==3&&i>=0x48&&i<0x54)known=0;if(known)feed(&h,packet_byte(packet,i));}if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;}
s32 func_150ADA20(void){check(1,0,0,0,0,0,0);mark_call();++rng_count;if(c->mode&1){if(rng_count==1){input.x=-1.;input.y=4.;input.z=8.;}if(rng_count==4){arena.effect.growthRate=-3.;arena.bytes[1]=0x91;}}return(s32)c->rng[rng_count-1];}
f32 func_150ADA68(void){check(2,0,0,0,0,0,0);mark_call();++float_count;if(c->mode&2){if(float_count==1){input.x=5.;input.y=-7.;input.z=9.;}if(float_count==2){D_800A0570=400.;D_800A0574=.00125f;}if(float_count==3){arena.effect.growthRate=4.;D_800A0578=.5f;D_800A057C=.75f;}}return floating(c->samples[float_count-1]);}
void func_15143794(s16 angle,s16 pitch,f32 speed,vertex*out){const RingParticle150C99B4*packet=(const RingParticle150C99B4*)((const u8*)out-__builtin_offsetof(RingParticle150C99B4,direction));check(3,(u32)(s32)angle,(u32)(s32)pitch,bits(speed),0x40000-112+0x48,0,packet);mark_call();out->x=(f32)pitch*.125f;out->y=-speed;out->z=(f32)(angle&255)*.125f;if(c->mode&4){arena.bytes[12]=0xa7;arena.bytes[1]=0xfe;}}
void*func_15130374(void*packet,u8 mode,s32 bytes,u8 slot,s32 context){check(4,0x40000-112,mode,(u32)bytes,slot,(u32)context,packet);mark_call();if(c->mode&8){arena.effect.growthRate=17.;input.x=-11.;}return c->outcome?(void*)0x90000:0;}
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=rng_count=float_count=0;for(int i=0;i<84;i++)arena.bytes[i]=((i+16)*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;arena.bytes[1]=(u8)c->context;arena.bytes[12]=(u8)c->slot;arena.effect.growthRate=floating(c->base);input.x=floating(c->point[0]);input.y=floating(c->point[1]);input.z=floating(c->point[2]);D_800A0570=floating(c->constants[0]);D_800A0574=floating(c->constants[1]);D_800A0578=floating(c->constants[2]);D_800A057C=floating(c->constants[3]);u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");func_150C99B4(&arena.effect,&input,(u8)c->angle,floating(c->unused_sine),floating(c->unused_cosine));Hash h=snapshot();if(event_index!=10||rng_count!=5||float_count!=3||h.a!=c->final.a||h.b!=c->final.b)bad=1;if(bad)return42;
 }return 0;}
__attribute__((force_align_arg_pointer))void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''.replace('return42','return 42')
 return text,len(cases)
def main():
 text,count=generate();profiles={};controls=[]
 def run(name,body,opt):
  f=p.OUT/(name+'.c');exe=p.OUT/(name+'.exe');f.write_text(body);command=native_command(opt)+['-frounding-math','-fno-builtin',str(f),'-o',str(exe)];q=subprocess.run(command,cwd=p.ROOT,capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True,text=True);return dict(exit=q.returncode,source_sha256=sha(f),binary_sha256=sha(exe),command=command)
 for opt in('-O0','-O2','-O3'):
  q=run('native-'+opt[1:],text,opt);assert q['exit']==0,q;profiles[opt[1:]]=q
 original=selected();mutations=[('kind','packet.kind = 0x26','packet.kind = 0x27'),('lifetime','% 81U','% 80U'),('alpha','% 156U','% 155U'),('size','sample * 500.0f + 500.0f','sample * 501.0f + 500.0f'),('acceleration','+ -1416.0f','+ -1415.0f'),('flag','? 0x40 : 0','? 0x20 : 0'),('pitch','% 11U - 18','% 11U - 17'),('speed','base * D_800A0578','base * D_800A057C'),('slot-context','((u8 *)owner)[0xC],((u8 *)owner)[1]','((u8 *)owner)[1],((u8 *)owner)[0xC]'),('payload','func_15130374(&packet,1,0,','func_15130374(&packet,1,4,'),('sentinel','packet.field62 = -1','packet.field62 = 0')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_angles=True,canonical_dual32_memory_digests=True,only_initialized_packet_bytes_observed=True,legal_nonoverlapping_bounded_objects=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
