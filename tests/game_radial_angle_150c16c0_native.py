"""SDK32 direction input and initialized request/payload/render factory records."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_radial_angle_150c16c0_match as p
from tools.tests import game_radial_angle_150c16c0_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.game_remaining_donor_candidates import function_span
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def digest(data):
 a,b=0x811c9dc5,0x9e3779b9
 for v in data:a=((a^v)*16777619)&0xffffffff;b=((b+v+0x7f4a7c15)*0x85ebca6b)&0xffffffff
 return a,b
def snapshot_bytes(s):return b''.join(v.to_bytes(4,'big')for v in s[0])+s[1]+s[2]+s[3]
def selected():
 s=p.MANIFEST['selected_source'];a,z=function_span(s,p.FUNCTION);return s[a:z]
def support():
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    vertex position;\n    s16 lifetime,field0E;');z=s.index('/* Emit one randomized radial effect using',a);return s[a:z]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.home_mutations and not c.alias));rows=[];vector=lambda a:'{'+','.join(str(g.u32(v))+'U'for v in a)+'}'
 assert len(g.KNOWN)==75
 for c in cases:
  wanted,calls,obs,_=g.reference(g.fixture(c),c);events=[]
  for(t,args),ob in zip(calls,obs):
   code={g.RNG:1,g.FRNG:2,g.SUBMIT:3,g.ANGLE:4}[t];arguments=list(args)+[0]*(15-len(args));mask=g.KNOWN if t==g.SUBMIT else()
   events.append('{'+str(code)+','+vector(arguments)+','+vector(digest(snapshot_bytes(ob[0])))+','+vector(digest(bytes(ob[1][i]for i in mask)))+'}')
  assert len(events)==11;values=(c.angle,c.slot,c.outcome,c.mode,c.fcsr,c.seed);rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+','+vector(c.coords)+','+vector(c.normals)+','+vector(c.rng)+','+vector(c.samples)+','+vector(c.constants)+','+vector(c.unused)+','+vector(digest(snapshot_bytes(g.snapshot(wanted,c))))+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n#include "structs.h"\ns32 func_150ADA20(void);\n'+support()+'\n'+selected()+r'''
typedef char request_size[sizeof(RadialRequest150C16C0)==28?1:-1];
typedef char payload_size[sizeof(RadialPayload150C16C0)==32?1:-1];
typedef char render_size[sizeof(RadialRender150C16C0)==32?1:-1];
typedef char request_count[__builtin_offsetof(RadialRequest150C16C0,count)==21?1:-1];
typedef char payload_flags[__builtin_offsetof(RadialPayload150C16C0,field18)==24?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[15];Hash state,packet;}Event;
typedef struct{u32 angle,slot,outcome,mode,fcsr,seed,coords[3],normals[6],rng[3],samples[3],constants[5],unused[10];Hash final;Event event[11];}Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''};
typedef struct{vertex first;u8 gap0[20];vertex second;u8 gap1[20];}DirectionArena;
typedef char direction_size[sizeof(DirectionArena)==64?1:-1];
static DirectionArena directions;
static const Row*c;static u32 bad,event_index,rng_count,float_count,factory_count,angle_count;
static union{u64 align;u8 bytes[0xcc];}arena;static u8 marks[32];
f32 D_800A01F0,D_800A01F4,D_800A01F8,D_800A01FC,D_800A0200;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static u8 canonical(const void*object,int at,int width,int start){const u8*p=object;u32 v=0;for(int j=width-1;j>=0;j--)v=(v<<8)|p[start+j];return v>>(8*(width-1-at+start));}
static u8 direction_byte(int at){if(at<12||(at>=32&&at<44))return canonical(&directions,at,4,at&~3);return((const u8*)&directions)[at];}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};word(&h,bits(D_800A01F0));word(&h,bits(D_800A01F4));word(&h,bits(D_800A01F8));word(&h,bits(D_800A01FC));word(&h,bits(D_800A0200));for(int i=0;i<0xac;i++)feed(&h,arena.bytes[16+i]);for(int i=0;i<32;i++)feed(&h,marks[i]);for(int i=0;i<64;i++)feed(&h,direction_byte(i));return h;}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static void check(u32 code,const u32*args,const RadialRequest150C16C0*q,const RadialPayload150C16C0*p,const RadialRender150C16C0*r){
 if(event_index>=11){bad=1;return;}const Event*e=&c->event[event_index++];if(code!=e->code)bad=1;for(int i=0;i<15;i++)if((args?args[i]:0)!=e->args[i])bad=1;Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;
 h=(Hash){0x811c9dc5U,0x9e3779b9U};if(q){for(int i=0;i<20;i++)feed(&h,canonical(q,i,i<12?4:i<16?2:4,i<12?i&~3:i<16?i&~1:16));feed(&h,q->count);for(int i=0;i<28;i++)if(i<20||i>=24)feed(&h,i<20?canonical(p,i,4,i&~3):((const u8*)p)[i]);for(int i=0;i<30;i++)feed(&h,i<28?canonical(r,i,4,i&~3):((const u8*)r)[i]);}if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;
}
s32 func_150ADA20(void){check(1,0,0,0,0);mark_call();u32 i=rng_count++;if(i>=3)bad=1;return(s32)c->rng[i%3];}
f32 func_150ADA68(void){check(2,0,0,0,0);mark_call();u32 i=float_count++;if(i>=3)bad=1;if(c->mode&1){if(i==0)D_800A01F0=.25f;if(i==1){D_800A01F4=.5f;D_800A01F8=-.25f;}if(i==2){D_800A01FC=.75f;D_800A0200=-.375f;}}if(i==0&&(c->mode&2)){directions.first.x=2.0f;directions.first.y=-3.0f;directions.first.z=4.0f;}return floating(c->samples[i%3]);}
f32 func_151423D8(u8 angle){u32 args[15]={angle};check(4,args,0,0,0);mark_call();++angle_count;if(angle_count==1&&(c->mode&2))D_800A01F0=.375f;u32 i=angle&64?64-(angle&63):angle&63;static const u32 trig[]={'''+','.join(str(v)+'U'for v in g.TRIG)+r'''};return floating(trig[i]^((angle&192)!=0&&(angle&192)!=192?0x80000000U:0));}
void*func_15147DA0(void*request,void*descriptor,s32 bytes,s32 active,s32 first,s32 second,s32 third,s32 fourth,s32 fifth,s32 fade,s32 alpha,void*render,s32 extra,u8 slot,s32 context){
 u32 args[]={0x40000-32,0x40000-64,(u32)bytes,(u32)active,(u32)first,(u32)second,(u32)third,(u32)fourth,(u32)fifth,(u32)fade,(u32)alpha,0x40000-96,(u32)extra,slot,(u32)context};RadialRequest150C16C0*q=request;RadialPayload150C16C0*p=descriptor;RadialRender150C16C0*r=render;check(3,args,q,p,r);mark_call();++factory_count;q->active=1;if(c->mode&2){q->position.x=7.0f;p->field10=1.5f;r->field00=0x73;}if(c->mode&4){u32 n=0x12345678;for(int i=0;i<4;i++)arena.bytes[16+i]=n>>(8*(3-i));}return c->outcome?arena.bytes+16:0;
}
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=rng_count=float_count=factory_count=angle_count=0;for(int i=0;i<0xcc;i++)arena.bytes[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<64;i++)((u8*)&directions)[i]=(i*29+c->seed*11+0x5a)&255;directions.first=(vertex){floating(c->normals[0]),floating(c->normals[1]),floating(c->normals[2])};directions.second=(vertex){floating(c->normals[3]),floating(c->normals[4]),floating(c->normals[5])};D_800A01F0=floating(c->constants[0]);D_800A01F4=floating(c->constants[1]);D_800A01F8=floating(c->constants[2]);D_800A01FC=floating(c->constants[3]);D_800A0200=floating(c->constants[4]);u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");s32 answer=func_150C16C0((s32)c->unused[0],(s16)c->unused[1],floating(c->coords[0]),floating(c->coords[1]),floating(c->coords[2]),floating(c->unused[2]),floating(c->unused[3]),floating(c->unused[4]),(s32)c->angle,(s32)c->unused[5],floating(c->unused[6]),(s32)c->unused[7],floating(c->unused[8]),(s32)c->unused[9],(u8)c->slot);Hash h=snapshot();if(answer!=1||event_index!=11||rng_count!=3||float_count!=3||factory_count!=1||angle_count!=4||h.a!=c->final.a||h.b!=c->final.b)bad=1;for(int i=0;i<16;i++)if(arena.bytes[i]!=((i*29+c->seed*11+0x5a)&255)||arena.bytes[0xbc+i]!=(((0xbc+i)*29+c->seed*11+0x5a)&255))bad=1;if(bad)return 42;
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
 original=selected();mutations=[('heading-quarter','(u32)angle - 64U','(u32)angle - 63U'),('pitch-quarter','(u32)pitch - 64U','(u32)pitch - 63U'),('pitch-modulo','% 13U','% 12U'),('pitch-base','% 13U - 63','% 13U - 62'),('speed-base','+ 25.5f','+ 26.5f'),('captured-coefficient','scale = D_800A01F0','scale = D_800A01F4'),('count-modulo','% 9U','% 8U'),('count-base','% 9U + 5','% 9U + 4'),('lifetime-mask','& 63U','& 31U'),('lifetime-base','+ 90','+ 89'),('first-field-bias','+ D_800A01F8','+ D_800A01F4'),('second-field-bias','+ D_800A0200','+ D_800A01FC'),('horizontal','speed * pitchValue','speed * pitchQuarter'),('vertical','-speed * pitchQuarter','speed * pitchQuarter'),('flags','payload.field18 = 40','payload.field18 = 41'),('kind','payload.kind = 10','payload.kind = 9'),('alpha','payload.alpha = 255','payload.alpha = 254'),('last-byte','payload.field1B = 255','payload.field1B = 254'),('request-mode','request.field0E = 1','request.field0E = 0'),('factory-control','&payload,0,1,5,','&payload,0,1,4,'),('slot','&render,0,slot,0','&render,0,slot ^ 1,0'),('context','&render,0,slot,0','&render,0,slot,1'),('loop-count','remaining = 1','remaining = 2'),('return','return 1;','return 0;')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b,1);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 late=original.replace('    scale = D_800A01F0;\n','').replace('speed = func_150ADA68() * scale + 25.5f;','speed = func_150ADA68(); scale = D_800A01F0; speed = speed * scale + 25.5f;');assert late!=original;q=run('native-late-coefficient',text.replace(original,late,1),'-O2');assert q['exit']==42,q;controls.append(dict(name='late-coefficient',comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))

 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_heading_and_slot_bytes=True,canonical_dual32_memory_digests=True,initialized_factory_bytes_observed=75,unspecified_factory_bytes_excluded=17,no_native_private_record_observation_before_factory=True,legal_nonoverlapping_bounded_objects=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
