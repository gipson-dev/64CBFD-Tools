"""SDK32 descriptor execution with independent guest-checked call transcripts."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_angular_extended_150b2eb4_match as p
from tools.tests import game_angular_extended_150b2eb4_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.game_radial_angle_150c16c0_native import digest
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def snapshot_bytes(s):return b''.join(v.to_bytes(4,'big')for v in s[0])+s[1]+s[2]
def selected():
 s=p.MANIFEST['selected_source'];a,z=function_span(s,p.FUNCTION);return s[a:z]
def support():
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    f32 field00, field04, field08, field0C;');z=s.index('/* Build one extended emitter',a);return s[a:z]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.home_mutations and not c.invalid_trunc));rows=[]
 vec=lambda v:'{'+','.join(str(g.u32(x))+'U'for x in v)+'}'
 assert len(g.KNOWN)==112
 for c in cases:
  wanted,calls,obs,_=g.reference(g.fixture(c),c);events=[]
  for(t,args),ob in zip(calls,obs):
   code={g.FRNG:1,g.ANGLE:2,g.SUBMIT:3}[t];a=list(args)+[0]*(15-len(args))
   events.append('{'+str(code)+','+vec(a)+','+vec(digest(snapshot_bytes(ob[0])))+','+vec(digest(bytes(ob[1][i]for i in g.KNOWN)if t==g.SUBMIT else b''))+'}')
  assert len(events)==12;values=(c.angle,c.start,c.radius,c.extra,c.slot,c.outcome,c.mode,c.fcsr,c.seed)
  rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+','+vec(c.coords)+','+vec(c.samples)+','+vec(c.constants)+','+vec(c.unused)+','+vec(digest(snapshot_bytes(g.snapshot(wanted,c))))+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n'+support()+'\n'+selected()+r'''
typedef char descriptor_size[sizeof(AngularExtended150B2EB4)==124?1:-1];
typedef char descriptor_flags[__builtin_offsetof(AngularExtended150B2EB4,flags)==0x50?1:-1];
typedef char descriptor_control[__builtin_offsetof(AngularExtended150B2EB4,field6A)==0x6a?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[15];Hash state,packet;}Event;
typedef struct{u32 angle,start,radius,extra,slot,outcome,mode,fcsr,seed,coords[3],samples[5],constants[4],unused[7];Hash final;Event event[12];}Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''};
static const Row*c;static u32 bad,event_index,float_count,angle_count,factory_count;
static union{u64 align;u8 bytes[0xcc];}arena;static u8 marks[32];
f32 D_8009FB8C,D_8009FB90,D_8009FB94,D_8009FB98;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};word(&h,bits(D_8009FB8C));word(&h,bits(D_8009FB90));word(&h,bits(D_8009FB94));word(&h,bits(D_8009FB98));for(int i=0;i<0xac;i++)feed(&h,arena.bytes[16+i]);for(int i=0;i<32;i++)feed(&h,marks[i]);return h;}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static int unspecified(int i){return(i>=0x59&&i<0x5c)||i==0x69||i==0x6b||i==0x71||(i>=0x76&&i<0x7c);}
static u8 descriptor_byte(const u8*p,int i){int at=i;if(i<0x54||(i>=0x5c&&i<0x60)||(i>=0x6c&&i<0x70))at=(i&~3)+(3-(i&3));else if((i>=0x54&&i<0x58)||(i>=0x72&&i<0x76))at=(i&~1)+(1-(i&1));return p[at];}
static void check(u32 code,const u32*args,const u8*descriptor){
 if(event_index>=12){bad=1;return;}const Event*e=&c->event[event_index++];if(e->code!=code)bad=1;for(int i=0;i<15;i++)if(e->args[i]!=(args?args[i]:0))bad=1;Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;
 h=(Hash){0x811c9dc5U,0x9e3779b9U};if(descriptor)for(int i=0;i<124;i++)if(!unspecified(i))feed(&h,descriptor_byte(descriptor,i));if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;
}
f32 func_150ADA68(void){check(1,0,0);mark_call();u32 n=++float_count;if(n>5)bad=1;if(c->mode&1){if(n==2){D_8009FB90=.75f;D_8009FB94=-.25f;}if(n==4){D_8009FB90=.5f;D_8009FB94=-.375f;}if(n==5)D_8009FB98=-.625f;}return floating(c->samples[(n-1)%5]);}
f32 func_151423D8(u8 angle){u32 a[15]={angle};check(2,a,0);mark_call();++angle_count;if(angle_count==1&&(c->mode&1))D_8009FB8C=3.5f;u32 i=angle&64?64-(angle&63):angle&63;static const u32 trig[]={'''+','.join(str(v)+'U'for v in g.TRIG)+r'''};return floating(trig[i]^((angle&192)!=0&&(angle&192)!=192?0x80000000U:0));}
void*func_15132A4C(void*descriptor,s32 resource,s32 value,s32 bytes,u8 slot,s32 context){
 u32 a[15]={0x40000-156,(u32)resource,(u32)value,(u32)bytes,slot,(u32)context};check(3,a,descriptor);mark_call();++factory_count;if(c->mode&2)((AngularExtended150B2EB4*)descriptor)->field4C=7.f;if(c->mode&4){u32 n=0x12345678U;for(int i=0;i<4;i++)arena.bytes[16+i]=n>>(8*(3-i));}return c->outcome?arena.bytes+16:0;
}
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=float_count=angle_count=factory_count=0;for(int i=0;i<0xcc;i++)arena.bytes[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;D_8009FB8C=floating(c->constants[0]);D_8009FB90=floating(c->constants[1]);D_8009FB94=floating(c->constants[2]);D_8009FB98=floating(c->constants[3]);u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");
 s32 answer=func_150B2EB4((s32)c->unused[0],(s16)c->unused[1],floating(c->coords[0]),floating(c->coords[1]),floating(c->coords[2]),floating(c->unused[2]),floating(c->unused[3]),floating(c->unused[4]),c->angle,(s32)c->start,floating(c->radius),(s32)c->unused[5],floating(c->extra),(s32)c->unused[6],(u8)c->slot);
 Hash h=snapshot();if(answer!=1||event_index!=12||float_count!=5||angle_count!=6||factory_count!=1||h.a!=c->final.a||h.b!=c->final.b)bad=1;for(int i=0;i<16;i++)if(arena.bytes[i]!=((i*29+c->seed*11+0x5a)&255)||arena.bytes[0xbc+i]!=(((0xbc+i)*29+c->seed*11+0x5a)&255))bad=1;if(bad)return 42;
 }return 0;}
__attribute__((force_align_arg_pointer))void _start(void){int n=run();__asm__ volatile("int $0x80"::"a"(1),"b"(n):"memory");__builtin_unreachable();}
'''
 return text,len(cases)
def main():
 text,count=generate();profiles={};controls=[]
 def run(name,body,opt):
  f=p.OUT/(name+'.c');exe=p.OUT/(name+'.exe');f.write_text(body);command=native_command(opt)+['-frounding-math','-fno-builtin',str(f),'-o',str(exe)];q=subprocess.run(command,cwd=p.ROOT,capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True,text=True);return dict(exit=q.returncode,source_sha256=sha(f),binary_sha256=sha(exe),command=command)
 for opt in('-O0','-O2','-O3'):
  q=run('native-'+opt[1:],text,opt);assert q['exit']==0,q;profiles[opt[1:]]=q
 original=selected();mutations=[('heading-quarter','heading - 64U','heading - 63U'),('yaw-quarter','index - 64','index - 63'),('yaw-scale','60.0f * headingSine','61.0f * headingSine'),('pitch-scale','48.0f * headingCosine','47.0f * headingCosine'),('pitch-base','- 20;','- 19;'),('speed-factor','* 31.0f','* 32.0f'),('speed-base','+ 18.0f','+ 17.0f'),('horizontal','speed * pitchSine','speed * (pitchSine + 1.0f)'),('vertical','-speed * pitchCosine','speed * pitchCosine'),('first-drift','field40 = func_150ADA68() * 80.0f','field40 = func_150ADA68() * 81.0f'),('second-drift','field48 = func_150ADA68() * 80.0f','field48 = func_150ADA68() * 79.0f'),('duration','duration = 100','duration = 99'),('late-field','* D_8009FB90','* D_8009FB94'),('scale-factor','* 72.5f','* 73.5f'),('resource','resource = 28','resource = 27'),('flags','flags = 0x9E8','flags = 0x9E9'),('control','field6A = 2','field6A = 1'),('unit-field','field00 = 1.0f','field00 = 0.0f'),('slot','&descriptor,3,255,0,slot,0','&descriptor,3,255,0,slot ^ 1,0'),('factory-resource','&descriptor,3,255,0,slot,0','&descriptor,2,255,0,slot,0'),('return','return 1;','return 0;')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b,1);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_heading_and_slot_bytes=True,canonical_dual32_memory_digests=True,initialized_factory_bytes_observed=112,unspecified_factory_bytes_excluded=12,no_native_private_record_observation_before_factory=True,legal_nonoverlapping_bounded_objects=True,only_defined_float_to_signed32_conversions=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0)
 (p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
