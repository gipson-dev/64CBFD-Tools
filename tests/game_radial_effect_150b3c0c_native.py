"""SDK32 tests of legal native C values, initialized bytes and provider order."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_radial_effect_150b3c0c_match as p
from tools.tests import game_radial_effect_150b3c0c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def digest(data):
 a,b=0x811c9dc5,0x9e3779b9
 for v in data:a=((a^v)*16777619)&0xffffffff;b=((b+v+0x7f4a7c15)*0x85ebca6b)&0xffffffff
 return a,b
def snapshot_bytes(s):return b''.join(v.to_bytes(4,'big')for v in s[0])+s[1]+s[2]
def selected():
 s=p.MANIFEST['selected_source'];a=s.index('extern f32 D_8009FBCC');return s[a:]
def packet_type():
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    vertex position,velocity;');b=s.index('} RadialEffect150B3C0C;',a)+len('} RadialEffect150B3C0C;');return s[a:b]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.home_mutations));rows=[];vector=lambda a:'{'+','.join(str(g.u32(v))+'U'for v in a)+'}'
 for c in cases:
  wanted,calls,obs,_=g.reference(g.fixture(c),c);events=[];colors=0
  for(t,args),ob in zip(calls,obs):
   code={g.RNG:1,g.FRNG:2,g.ANGLE:3,g.COLOR:4,g.SUBMIT:5,g.SECOND:6}[t];arguments=list(args)+[0]*(6-len(args));mask=()
   if t==g.COLOR:mask=range(32 if colors==0 else 35);colors+=1
   if t in(g.SUBMIT,g.SECOND):mask=g.KNOWN
   events.append('{'+str(code)+','+vector(arguments)+','+vector(digest(snapshot_bytes(ob[0])))+','+vector(digest(bytes(ob[1][i]for i in mask)))+'}')
  assert len(events)==12;values=(c.angle,c.slot,c.outcome,c.mode,c.fcsr,c.seed,len(events));rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+','+vector(c.coords)+','+vector(c.rng)+','+vector(c.samples)+','+vector(c.colors)+','+vector(c.constants)+','+vector(c.unused)+','+vector(digest(snapshot_bytes(g.snapshot(wanted,c))))+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n#include "structs.h"\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nf32 func_151423D8(u8);\nvoid func_151429E0(u8,u8*,u8*,u8*);\nvoid*func_15156190(void*,u8,s32,u8,s32);\nvoid func_15156388(void*,u8,s32);\n'+packet_type()+'\n'+selected()+'''
typedef char packet_size[sizeof(RadialEffect150B3C0C)==60?1:-1];
typedef char packet_velocity[__builtin_offsetof(RadialEffect150B3C0C,velocity)==12?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[6];Hash state,packet;}Event;
typedef struct{u32 angle,slot,outcome,mode,fcsr,seed,count,coords[3],rng[1],samples[3],colors[2],constants[6],unused[10];Hash final;Event event[12];}Row;
static const u32 trig[]={'''+','.join(str(v)+'U'for v in g.TRIG)+'''};
static const u8 palette[]={'''+','.join(str(v)for v in g.PALETTE)+'''};
static const Row rows[]={\n'''+',\n'.join(rows)+'''};
static const Row*c;static u32 bad,event_index,rng_count,float_count,angle_count,color_count,factory_count;
static union{u64 align;u8 bytes[0xcc];}arena;static u8 marks[32];
f32 D_8009FBCC,D_8009FBD0,D_8009FBD4,D_8009FBD8,D_8009FBDC,D_8009FBE0;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};word(&h,bits(D_8009FBCC));word(&h,bits(D_8009FBD0));word(&h,bits(D_8009FBD4));word(&h,bits(D_8009FBD8));word(&h,bits(D_8009FBDC));word(&h,bits(D_8009FBE0));for(int i=0;i<0xac;i++)feed(&h,arena.bytes[16+i]);for(int i=0;i<32;i++)feed(&h,marks[i]);return h;}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static u8 packet_byte(const RadialEffect150B3C0C*packet,int at){const u8*p=(const u8*)packet;static const u8 offsets[]={0,4,8,12,16,20,24,28,42,44,48,54,56};static const u8 widths[]={4,4,4,4,4,4,4,4,2,2,4,2,2};for(unsigned i=0;i<sizeof(offsets);i++){int start=offsets[i],n=widths[i];if(at>=start&&at<start+n){u32 v=0;for(int j=n-1;j>=0;j--)v=(v<<8)|p[start+j];return v>>(8*(n-1-at+start));}}return p[at];}
static void check(u32 code,u32 a0,u32 a1,u32 a2,u32 a3,u32 a4,u32 a5,const RadialEffect150B3C0C*packet){if(event_index>=12){bad=1;return;}const Event*e=&c->event[event_index++];u32 a[]={a0,a1,a2,a3,a4,a5};if(code!=e->code)bad=1;for(int i=0;i<6;i++)if(a[i]!=e->args[i])bad=1;Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;h=(Hash){0x811c9dc5U,0x9e3779b9U};if(packet)for(int i=0;i<60;i++){int known=code==4?(i<(color_count?35:32)):(i<0x29||(i>=0x2a&&i<0x2e)||(i>=0x30&&i<0x35)||(i>=0x36&&i<0x3a));if(known)feed(&h,packet_byte(packet,i));}if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;}
s32 func_150ADA20(void){check(1,0,0,0,0,0,0,0);mark_call();++rng_count;return(s32)c->rng[0];}
f32 func_150ADA68(void){check(2,0,0,0,0,0,0,0);mark_call();++float_count;if(c->mode&1){if(float_count==1){D_8009FBCC=.25f;D_8009FBD0=-.125f;}if(float_count==2){D_8009FBD4=.5f;D_8009FBD8=-.25f;}if(float_count==3){D_8009FBDC=.75f;D_8009FBE0=-.375f;}}return floating(c->samples[float_count-1]);}
f32 func_151423D8(u8 angle){check(3,angle,0,0,0,0,0,0);mark_call();++angle_count;u32 i=angle&64?64-(angle&63):angle&63;return floating(trig[i]^((angle&192)!=0&&(angle&192)!=192?0x80000000U:0));}
void func_151429E0(u8 command,u8*r,u8*g,u8*b){u32 off=color_count?36:32;const RadialEffect150B3C0C*packet=(const RadialEffect150B3C0C*)((const u8*)r-off);const u8*base=(const u8*)packet;check(4,command,0x40000-76+(u32)((const u8*)r-base),0x40000-76+(u32)((const u8*)g-base),0x40000-76+(u32)((const u8*)b-base),0,0,packet);mark_call();u32 draw=c->colors[color_count++]&3;*r=palette[3*draw];*g=palette[3*draw+1];*b=palette[3*draw+2];}
static void factory_effect(RadialEffect150B3C0C*packet,u32 second){if(!second&&(c->mode&2)){packet->field30=1.5f;packet->kind=0x73;}if(c->mode&4){u32 n=second?0x87654321U:0x12345678U;for(int i=0;i<4;i++)arena.bytes[16+4*second+i]=n>>(8*(3-i));}++factory_count;}
void*func_15156190(void*packet,u8 kind,s32 extra,u8 slot,s32 owner){check(5,0x40000-76,kind,(u32)extra,slot,(u32)owner,0,packet);mark_call();factory_effect(packet,0);return c->outcome&1?arena.bytes+16:0;}
void func_15156388(void*packet,u8 kind,s32 extra){check(6,0x40000-76,kind,(u32)extra,0,0,0,packet);mark_call();factory_effect(packet,1);}
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=rng_count=float_count=angle_count=color_count=factory_count=0;for(int i=0;i<0xcc;i++)arena.bytes[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;D_8009FBCC=floating(c->constants[0]);D_8009FBD0=floating(c->constants[1]);D_8009FBD4=floating(c->constants[2]);D_8009FBD8=floating(c->constants[3]);D_8009FBDC=floating(c->constants[4]);D_8009FBE0=floating(c->constants[5]);u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");s32 answer=func_150B3C0C((s32)c->unused[0],(s16)c->unused[1],floating(c->coords[0]),floating(c->coords[1]),floating(c->coords[2]),floating(c->unused[2]),floating(c->unused[3]),floating(c->unused[4]),(s32)c->angle,(s32)c->unused[5],floating(c->unused[6]),(s32)c->unused[7],floating(c->unused[8]),(s32)c->unused[9],(u8)c->slot);Hash h=snapshot();if(answer!=1||event_index!=c->count||rng_count!=1||float_count!=3||angle_count!=4||color_count!=2||factory_count!=2||h.a!=c->final.a||h.b!=c->final.b)bad=1;for(int i=0;i<16;i++)if(arena.bytes[i]!=((i*29+c->seed*11+0x5a)&255)||arena.bytes[0xbc+i]!=(((0xbc+i)*29+c->seed*11+0x5a)&255))bad=1;if(bad)return 42;
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
 original=selected();mutations=[('start-quarter','(u32)start - 64U','(u32)start - 63U'),('angle-quarter','(u32)angle - 64U','(u32)angle - 63U'),('speed','10.0f * speed','11.0f * speed'),('vertical','-10.0f * angleQuarter','10.0f * angleQuarter'),('first-scale','+ D_8009FBD0','+ D_8009FBCC'),('second-scale','+ D_8009FBD8','+ D_8009FBD4'),('color-command','func_151429E0(8,','func_151429E0(9,'),('color-output','&packet.color0[1]','&packet.color0[0]'),('kind','packet.kind = 9','packet.kind = 8'),('lifetime','& 15) + 15','& 7) + 15'),('third-scale','+ D_8009FBE0','+ D_8009FBDC'),('slot','(&packet,1,0,slot,1)','(&packet,1,0,slot ^ 1,1)'),('owner','(&packet,1,0,slot,1)','(&packet,1,0,slot,0)'),('second-extra','func_15156388(&packet,1,0)','func_15156388(&packet,1,1)'),('fade-start','packet.field36 = 10','packet.field36 = 11'),('fade-rate','packet.field38 = 25','packet.field38 = 26'),('return','return 1;','return 0;')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b,1);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_angle_and_start_bytes=True,signed_word_boundaries=True,canonical_dual32_memory_digests=True,only_initialized_packet_bytes_observed=True,legal_nonoverlapping_bounded_objects=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
