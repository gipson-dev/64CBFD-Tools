"""SDK32 descriptor execution with independent guest-checked call transcripts."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_tuned_extended_150b3188_match as p
from tools.tests import game_tuned_extended_150b3188_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.game_radial_angle_150c16c0_native import digest
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def snapshot_bytes(s):return b''.join(v.to_bytes(4,'big')for v in s[0])+s[1]+s[2]
def selected():
 s=p.MANIFEST['selected_source'];a,z=function_span(s,p.FUNCTION);return s[a:z]
def support():
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    f32 field00, field04, field08, field0C;');z=s.index('/* Build one extended emitter',a);support=s[a:z];body=(p.OUT/'payload-after-byte-created-body.c').read_text();return support+'\n'+body[:body.index('/* Capture retail')]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.home_mutations and not c.invalid_trunc));rows=[]
 vec=lambda v:'{'+','.join(str(g.u32(x))+'U'for x in v)+'}'
 assert len(g.KNOWN)==112
 for c in cases:
  wanted,calls,obs,_=g.reference(g.fixture(c),c);events=[]
  for(t,args),ob in zip(calls,obs):
   code={g.FRNG:1,g.ANGLE:2,g.SUBMIT:3,g.TWEAK:4,g.COPY:5}[t];a=list(args)+[0]*(15-len(args))
   events.append('{'+str(code)+','+vec(a)+','+vec(digest(snapshot_bytes(ob[0])))+','+vec(digest(bytes(ob[1][i]for i in g.KNOWN)if t==g.SUBMIT else b''))+'}')
  assert len(events)==21+c.outcome;values=(c.angle,c.start,c.radius,c.extra,c.slot,c.outcome,c.mode,c.fcsr,c.seed)
  rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+','+vec(c.coords)+','+vec(c.samples)+','+vec(c.constants)+','+vec(c.tweaks)+','+vec(c.unused)+','+vec(digest(snapshot_bytes(g.snapshot(wanted,c))))+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n#include <string.h>\n'+support()+'\n'+selected()+r'''
typedef char descriptor_size[sizeof(AngularExtended150B2EB4)==124?1:-1];
typedef char descriptor_flags[__builtin_offsetof(AngularExtended150B2EB4,flags)==0x50?1:-1];
typedef char descriptor_control[__builtin_offsetof(AngularExtended150B2EB4,field6A)==0x6a?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[15];Hash state,packet;}Event;
typedef struct{u32 angle,start,radius,extra,slot,outcome,mode,fcsr,seed,coords[3],samples[5],constants[6],tweaks[9],unused[7];Hash final;Event event[22];}Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''};
static const Row*c;static u32 bad,event_index,float_count,angle_count,factory_count,tweak_count,copy_count,copied;
static union{u64 align;u8 bytes[0x194];}arena;static u8 marks[32];
f32 D_8009FB9C,D_8009FBA0,D_8009FBA4,D_8009FBA8,D_8009FBAC,D_8009FBB0;
u8 D_8009F968[1],D_8009F970[1],D_8009F998[1],D_8009F9A4[1],D_8009F9CC[1],D_8009F9D8[1],D_8009FA00[1],D_8009FA0C[1],D_8009FA34[1],D_8009FA44[1],D_8009FA6C[1],D_8009FA78[1],D_8009FAA0[1],D_8009FAB0[1],D_8009FAD8[1],D_8009FAE4[1],D_8009FB0C[1],D_8009FB18[1];
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};word(&h,bits(D_8009FB9C));word(&h,bits(D_8009FBA0));word(&h,bits(D_8009FBA4));word(&h,bits(D_8009FBA8));word(&h,bits(D_8009FBAC));word(&h,bits(D_8009FBB0));for(int i=0;i<0x174;i++){int at=copied&&i>=0x170?(i&~3)+(3-(i&3)):i;feed(&h,arena.bytes[16+at]);}for(int i=0;i<32;i++)feed(&h,marks[i]);return h;}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static int unspecified(int i){return(i>=0x59&&i<0x5c)||i==0x69||i==0x6b||i==0x71||(i>=0x76&&i<0x7c);}
static u8 descriptor_byte(const u8*p,int i){int at=i;if(i<0x54||(i>=0x5c&&i<0x60)||(i>=0x6c&&i<0x70))at=(i&~3)+(3-(i&3));else if((i>=0x54&&i<0x58)||(i>=0x72&&i<0x76))at=(i&~1)+(1-(i&1));return p[at];}
static void check(u32 code,const u32*args,const u8*descriptor){
 if(event_index>=21+c->outcome){bad=1;return;}const Event*e=&c->event[event_index++];if(e->code!=code)bad=1;for(int i=0;i<15;i++)if(e->args[i]!=(args?args[i]:0))bad=1;Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;
 h=(Hash){0x811c9dc5U,0x9e3779b9U};if(descriptor)for(int i=0;i<124;i++)if(!unspecified(i))feed(&h,descriptor_byte(descriptor,i));if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;
}
f32 func_150ADA68(void){check(1,0,0);mark_call();u32 n=++float_count;if(n>5)bad=1;if((c->mode&1)&&n==5)D_8009FBB0=-.625f;return floating(c->samples[(n-1)%5]);}
f32 func_151423D8(u8 angle){u32 a[15]={angle};check(2,a,0);mark_call();++angle_count;if(angle_count==1&&(c->mode&1))D_8009FB9C=.002f;u32 i=angle&64?64-(angle&63):angle&63;static const u32 trig[]={'''+','.join(str(v)+'U'for v in g.TRIG)+r'''};return floating(trig[i]^((angle&192)!=0&&(angle&192)!=192?0x80000000U:0));}
void*func_15132A4C(void*descriptor,s32 resource,s32 value,s32 bytes,u8 slot,s32 context){
 u32 a[15]={0x40000-192,(u32)resource,(u32)value,(u32)bytes,slot,(u32)context};check(3,a,descriptor);mark_call();++factory_count;if(c->mode&2)((AngularExtended150B2EB4*)descriptor)->field4C=7.f;if(c->mode&4){u32 n=0x12345678U;for(int i=0;i<4;i++)arena.bytes[16+i]=n>>(8*(3-i));}return c->outcome?arena.bytes+16:0;
}

static u32 label(s32 p){static u8*const labels[]={D_8009F968,D_8009F970,D_8009F998,D_8009F9A4,D_8009F9CC,D_8009F9D8,D_8009FA00,D_8009FA0C,D_8009FA34,D_8009FA44,D_8009FA6C,D_8009FA78,D_8009FAA0,D_8009FAB0,D_8009FAD8,D_8009FAE4,D_8009FB0C,D_8009FB18};static const u32 addresses[]={0x8009f968U,0x8009f970U,0x8009f998U,0x8009f9a4U,0x8009f9ccU,0x8009f9d8U,0x8009fa00U,0x8009fa0cU,0x8009fa34U,0x8009fa44U,0x8009fa6cU,0x8009fa78U,0x8009faa0U,0x8009fab0U,0x8009fad8U,0x8009fae4U,0x8009fb0cU,0x8009fb18U};for(int i=0;i<18;i++)if((u32)p==(u32)labels[i])return addresses[i];bad=1;return 0;}
s32 func_151422DC(s32 id,s32 name,s32 minimum,s32 maximum,s32 value,s32 file,s32 line){
 u32 a[15]={(u32)id,label(name),(u32)minimum,(u32)maximum,(u32)value,label(file),(u32)line};check(4,a,0);mark_call();u32 n=++tweak_count;if(n>9){bad=1;return 0;}
 if(c->mode&1){if(n==2)D_8009FB9C=.0375f;if(n==3)D_8009FBA0=.05f;if(n==6)D_8009FBA4=.0875f;if(n==7)D_8009FBA8=.1f;if(n==9)D_8009FBAC=3.5f;}
 return (s32)c->tweaks[n-1];
}
void*memcpy(void*destination,const void*source,size_t count){
 u32 a[15]={0x90000+0x170,0x40000-200,(u32)count};check(5,a,0);++copy_count;if(destination!=arena.bytes+16+0x170||count!=4){bad=1;return destination;}
 const u8*src=source;u8*dst=destination;u32 v=0;for(int i=3;i>=0;i--)v=(v<<8)|src[i];if(v!=0xc1900000U)bad=1;for(unsigned i=0;i<count;i++)dst[i]=src[i];copied=1;return destination;
}
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=float_count=angle_count=factory_count=tweak_count=copy_count=copied=0;for(int i=0;i<0x194;i++)arena.bytes[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;D_8009FB9C=floating(c->constants[0]);D_8009FBA0=floating(c->constants[1]);D_8009FBA4=floating(c->constants[2]);D_8009FBA8=floating(c->constants[3]);D_8009FBAC=floating(c->constants[4]);D_8009FBB0=floating(c->constants[5]);u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");
 s32 answer=func_150B3188((s32)c->unused[0],(s16)c->unused[1],floating(c->coords[0]),floating(c->coords[1]),floating(c->coords[2]),floating(c->unused[2]),floating(c->unused[3]),floating(c->unused[4]),c->angle,(s32)c->start,floating(c->radius),(s32)c->unused[5],floating(c->extra),(s32)c->unused[6],(u8)c->slot);
 Hash h=snapshot();if(answer!=1||event_index!=21+c->outcome||float_count!=5||angle_count!=6||factory_count!=1||tweak_count!=9||copy_count!=c->outcome||h.a!=c->final.a||h.b!=c->final.b)bad=1;for(int i=0;i<16;i++)if(arena.bytes[i]!=((i*29+c->seed*11+0x5a)&255)||arena.bytes[0x184+i]!=(((0x184+i)*29+c->seed*11+0x5a)&255))bad=1;if(bad)return 42;
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
 original=selected();mutations=[('heading-quarter','heading - 64U','heading - 63U'),('yaw-quarter','index - 64','index - 63'),('yaw-scale','yawScale * headingSine','(yawScale + 1.0f) * headingSine'),('pitch-scale','pitchScale * headingCosine','(pitchScale + 1.0f) * headingCosine'),('pitch-base','- 20;','- 19;'),('speed-factor','* speedRange','* (speedRange + 1.0f)'),('speed-base','+ speedBase','+ (speedBase + 1.0f)'),('horizontal','speed * pitchSine','speed * (pitchSine + 1.0f)'),('vertical','-speed * pitchCosine','speed * pitchCosine'),('first-drift','field40 = func_150ADA68() * 4.0f','field40 = func_150ADA68() * 5.0f'),('second-drift','field48 = func_150ADA68() * 4.0f','field48 = func_150ADA68() * 3.0f'),('duration','duration + 32','duration + 31'),('late-field','* fieldRange','* (fieldRange + 1.0f)'),('scale-factor','* D_8009FBB0','* D_8009FBAC'),('resource','resource = 28','resource = 27'),('flags','flags = 0x29E9','flags = 0x29E8'),('control','field6A = 2','field6A = 1'),('size-field','func_150ADA68() * sizeRange + sizeBase','func_150ADA68() * sizeRange + (sizeBase + 1.0f)'),('slot','&descriptor,3,255,4,slot,0','&descriptor,3,255,4,slot ^ 1,0'),('factory-resource','&descriptor,3,255,4,slot,0','&descriptor,2,255,4,slot,0'),('return','return 1;','return 0;'),('tweak-minimum',',-5000,0,0,',',-4999,0,0,'),('tweak-id','func_151422DC(6,','func_151422DC(5,'),('tweak-default',',1,500,300,',',1,500,301,'),('payload','payload = -18.0f','payload = -19.0f'),('copy-count','&payload,4','&payload,3'),('copy-skip','memcpy((u8 *)created + 0x170,&payload,4);','(void)payload;')]

 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b,1);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_heading_and_slot_bytes=True,canonical_dual32_memory_digests=True,initialized_factory_bytes_observed=112,unspecified_factory_bytes_excluded=12,no_native_private_record_observation_before_factory=True,legal_nonoverlapping_bounded_objects=True,only_defined_float_to_signed32_conversions=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0)
 (p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
