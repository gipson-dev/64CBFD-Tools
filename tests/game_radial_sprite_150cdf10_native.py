"""SDK32 radial C with immutable value parameters and observed payload bytes."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_radial_sprite_150cdf10_match as p
from tools.tests import game_radial_sprite_150cdf10_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def digest(data):
 a,b=0x811c9dc5,0x9e3779b9
 for v in data:a=((a^v)*16777619)&0xffffffff;b=((b+v+0x7f4a7c15)*0x85ebca6b)&0xffffffff
 return a,b
def snapshot_bytes(s):return b''.join(v.to_bytes(4,'big')for v in s[0])+s[1]+s[2]
def selected():
 s=p.MANIFEST['selected_source'];a=s.index('extern f32 D_800A07C4');return s[a:]
def packet_type():
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    f32 field00,field04,');b=s.index('} RadialSprite150CDF10;',a)+len('} RadialSprite150CDF10;');return s[a:b]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.home_mutations));rows=[];vector=lambda a:'{'+','.join(str(g.u32(v))+'U'for v in a)+'}'
 for c in cases:
  wanted,calls,obs,_=g.reference(g.fixture(c),c);events=[]
  for(t,args),ob in zip(calls,obs):
   code={g.RNG:1,g.FRNG:2,g.DIRECTION:3,g.SUBMIT:4}[t];arguments=list(args)+[0]*(6-len(args));mask=g.BEFORE_DIRECTION if t==g.DIRECTION else g.KNOWN if t==g.SUBMIT else();ph=digest(bytes(ob[1][i]for i in mask));events.append('{'+str(code)+','+vector(arguments)+','+vector(digest(snapshot_bytes(ob[0])))+','+vector(ph)+'}')
  assert len(events)==10;values=(c.angle,c.slot,c.outcome,c.mode,c.fcsr,c.seed,len(events));rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+','+vector(c.coords)+','+vector(c.rng)+','+vector(c.samples)+','+vector(c.constants)+','+vector(c.unused)+','+vector(digest(snapshot_bytes(g.snapshot(wanted,c))))+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n#include "structs.h"\nu32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_15143794(s16,s16,f32,vertex*);\nvoid*func_15132A4C(void*,s32,s32,s32,u8,s32);\n'+packet_type()+'\n'+selected()+'''
typedef char packet_size[sizeof(RadialSprite150CDF10)==124?1:-1];
typedef char packet_direction[__builtin_offsetof(RadialSprite150CDF10,direction)==0x34?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[6];Hash state,packet;}Event;
typedef struct{u32 angle,slot,outcome,mode,fcsr,seed,count,coords[3],rng[3],samples[5],constants[8],unused[10];Hash final;Event event[10];}Row;
static const Row rows[]={\n'''+',\n'.join(rows)+'''};
static const Row*c;static u32 bad,event_index,rng_count,float_count;
static union{u64 align;u8 bytes[0xcc];}arena;static u8 marks[32];
f32 D_800A07C4,D_800A07C8,D_800A07CC,D_800A07D0,D_800A07D4,D_800A07D8,D_800A07DC,D_800A07E0;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};word(&h,bits(D_800A07C4));word(&h,bits(D_800A07C8));word(&h,bits(D_800A07CC));word(&h,bits(D_800A07D0));word(&h,bits(D_800A07D4));word(&h,bits(D_800A07D8));word(&h,bits(D_800A07DC));word(&h,bits(D_800A07E0));for(int i=0;i<0xac;i++)feed(&h,arena.bytes[16+i]);for(int i=0;i<32;i++)feed(&h,marks[i]);return h;}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static u8 packet_byte(const RadialSprite150CDF10*packet,int at){const u8*p=(const u8*)packet;static const u8 offsets[]={0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64,68,72,76,80,84,86,92,108,114,116};static const u8 widths[]={4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,2,2,4,4,2,2};for(unsigned i=0;i<sizeof(offsets);i++){int start=offsets[i],n=widths[i];if(at>=start&&at<start+n){u32 v=0;for(int j=n-1;j>=0;j--)v=(v<<8)|p[start+j];return v>>(8*(n-1-at+start));}}return p[at];}
static void check(u32 code,u32 a0,u32 a1,u32 a2,u32 a3,u32 a4,u32 a5,const RadialSprite150CDF10*packet){if(event_index>=10){bad=1;return;}const Event*e=&c->event[event_index++];u32 a[]={a0,a1,a2,a3,a4,a5};if(code!=e->code)bad=1;for(int i=0;i<6;i++)if(a[i]!=e->args[i])bad=1;Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;h=(Hash){0x811c9dc5U,0x9e3779b9U};if(packet)for(int i=0;i<124;i++){int known=code==3?(i<8||(i>=0x10&&i<0x34)||(i>=0x44&&i<0x48)||(i>=0x50&&i<0x54)||(i>=0x56&&i<0x58)):(i<0x59||(i>=0x5c&&i<0x69)||i==0x6a||(i>=0x6c&&i<0x71)||(i>=0x72&&i<0x76));if(known)feed(&h,packet_byte(packet,i));}if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;}
u32 func_150ADA20(void){check(1,0,0,0,0,0,0,0);mark_call();++rng_count;if(c->mode&1){if(rng_count==1)D_800A07C4=.375f;if(rng_count==2){D_800A07D4=-1500.;D_800A07D8=.00125f;}}return c->rng[rng_count-1];}
f32 func_150ADA68(void){check(2,0,0,0,0,0,0,0);mark_call();++float_count;if(c->mode&2){if(float_count==1)D_800A07C8=.015625f;if(float_count==2)D_800A07CC=.125f;if(float_count==3)D_800A07D0=.25f;if(float_count==4){D_800A07D4=-1750.;D_800A07D8=.0015f;}if(float_count==5){D_800A07DC=300.;D_800A07E0=.00125f;}}return floating(c->samples[float_count-1]);}
void func_15143794(s16 angle,s16 pitch,f32 speed,vertex*out){const RadialSprite150CDF10*packet=(const RadialSprite150CDF10*)((const u8*)out-__builtin_offsetof(RadialSprite150CDF10,direction));check(3,(u32)(s32)angle,(u32)(s32)pitch,bits(speed),0x40000-128+0x34,0,0,packet);mark_call();out->x=(f32)pitch*.125f;out->y=-speed;out->z=(f32)angle*.125f;}
void*func_15132A4C(void*packet,s32 resource,s32 value,s32 bytes,u8 slot,s32 context){check(4,0x40000-128,(u32)resource,(u32)value,(u32)bytes,slot,(u32)context,packet);mark_call();if(c->mode&4){D_800A07E0=.5f;for(int i=0;i<4;i++)arena.bytes[16+0xa8+i]=0x87654321U>>(8*(3-i));}return c->outcome?arena.bytes+16:0;}
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=rng_count=float_count=0;for(int i=0;i<0xcc;i++)arena.bytes[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;D_800A07C4=floating(c->constants[0]);D_800A07C8=floating(c->constants[1]);D_800A07CC=floating(c->constants[2]);D_800A07D0=floating(c->constants[3]);D_800A07D4=floating(c->constants[4]);D_800A07D8=floating(c->constants[5]);D_800A07DC=floating(c->constants[6]);D_800A07E0=floating(c->constants[7]);u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");s32 answer=func_150CDF10((s32)c->unused[0],(s16)c->unused[1],floating(c->coords[0]),floating(c->coords[1]),floating(c->coords[2]),floating(c->unused[2]),floating(c->unused[3]),floating(c->unused[4]),(s16)c->angle,(u8)c->unused[5],floating(c->unused[6]),(s32)c->unused[7],floating(c->unused[8]),(s32)c->unused[9],(u8)c->slot);Hash h=snapshot();if(answer!=1||event_index!=c->count||rng_count!=3||float_count!=5||h.a!=c->final.a||h.b!=c->final.b)bad=1;for(int i=0;i<16;i++)if(arena.bytes[i]!=((i*29+c->seed*11+0x5a)&255)||arena.bytes[0xbc+i]!=(((0xbc+i)*29+c->seed*11+0x5a)&255))bad=1;if(bad)return 42;
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
 original=selected();mutations=[('flags', 'packet.field50 = 0x29E8', 'packet.field50 = 0x29E9'), ('lifetime', '% 21U', '% 20U'), ('alpha', '% 76U', '% 75U'), ('pitch', '% 41U - 61', '% 41U - 60'), ('speed', '+ 150.0f', '+ 151.0f'), ('lateral', 'func_150ADA68() * 260.0f + -130.0f', 'func_150ADA68() * 261.0f + -130.0f'), ('acceleration', '+ D_800A07D8', '+ D_800A07D4'), ('size', '+ 52.0f', '+ 53.0f'), ('slot', '(&packet,3,255,0,slot,0)', '(&packet,3,255,0,slot ^ 1,0)'), ('context', '(&packet,3,255,0,slot,0)', '(&packet,3,255,0,slot,1)'), ('payload', '(&packet,3,255,0,slot,0)', '(&packet,3,255,4,slot,0)'), ('resource', '(&packet,3,255,0,slot,0)', '(&packet,4,255,0,slot,0)'), ('tail', 'packet.field74 = 7', 'packet.field74 = 8'), ('return', 'return 1;', 'return 0;')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_byte_angles=True,signed_halfword_boundaries=True,canonical_dual32_memory_digests=True,only_initialized_packet_bytes_observed=True,legal_nonoverlapping_bounded_objects=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
