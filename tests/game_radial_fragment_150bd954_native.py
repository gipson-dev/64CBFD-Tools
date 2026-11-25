"""SDK32 direction input and initialized request/payload/render factory records."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_radial_fragment_150bd954_match as p
from tools.tests import game_radial_fragment_150bd954_guest as g
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
 s=p.MANIFEST['selected_source'];a=s.index('typedef struct {\n    vertex position;\n    s16 lifetime,field0E;');z=s.index('/* Emit a randomized effect along',a);return s[a:z]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.home_mutations and not c.alias));rows=[];vector=lambda a:'{'+','.join(str(g.u32(v))+'U'for v in a)+'}'
 assert len(g.KNOWN)==79
 for c in cases:
  wanted,calls,obs,_=g.reference(g.fixture(c),c);events=[]
  for(t,args),ob in zip(calls,obs):
   code={g.RNG:1,g.FRNG:2,g.SUBMIT:3}[t];arguments=list(args)+[0]*(15-len(args));mask=g.KNOWN if t==g.SUBMIT else()
   events.append('{'+str(code)+','+vector(arguments)+','+vector(digest(snapshot_bytes(ob[0])))+','+vector(digest(bytes(ob[1][i]for i in mask)))+'}')
  assert len(events)==7;values=(c.slot,c.outcome,c.mode,c.fcsr,c.seed);rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+','+vector(c.coords)+','+vector(c.normals)+','+vector(c.rng)+','+vector(c.samples)+','+vector(c.constants)+','+vector(c.unused)+','+vector(digest(snapshot_bytes(g.snapshot(wanted,c))))+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n#include "structs.h"\ns32 func_150ADA20(void);\n'+support()+'\n'+selected()+r'''
typedef char request_size[sizeof(RadialRequest150BD954)==28?1:-1];
typedef char payload_size[sizeof(RadialPayload150BD954)==32?1:-1];
typedef char render_size[sizeof(RadialRender150BD954)==32?1:-1];
typedef char request_count[__builtin_offsetof(RadialRequest150BD954,count)==21?1:-1];
typedef char payload_flags[__builtin_offsetof(RadialPayload150BD954,field18)==24?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[15];Hash state,packet;}Event;
typedef struct{u32 slot,outcome,mode,fcsr,seed,coords[3],normals[6],rng[3],samples[3],constants[6],unused[10];Hash final;Event event[7];}Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''};
typedef struct{vertex first;u8 gap0[20];vertex second;u8 gap1[20];}DirectionArena;
typedef char direction_size[sizeof(DirectionArena)==64?1:-1];
static DirectionArena directions;
static const Row*c;static u32 bad,event_index,rng_count,float_count,factory_count;
static union{u64 align;u8 bytes[0xcc];}arena;static u8 marks[32];
f32 D_8009FFD0,D_8009FFD4,D_8009FFD8,D_8009FFDC,D_8009FFE0,D_8009FFE4;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static u8 canonical(const void*object,int at,int width,int start){const u8*p=object;u32 v=0;for(int j=width-1;j>=0;j--)v=(v<<8)|p[start+j];return v>>(8*(width-1-at+start));}
static u8 direction_byte(int at){if(at<12||(at>=32&&at<44))return canonical(&directions,at,4,at&~3);return((const u8*)&directions)[at];}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};word(&h,bits(D_8009FFD0));word(&h,bits(D_8009FFD4));word(&h,bits(D_8009FFD8));word(&h,bits(D_8009FFDC));word(&h,bits(D_8009FFE0));word(&h,bits(D_8009FFE4));for(int i=0;i<0xac;i++)feed(&h,arena.bytes[16+i]);for(int i=0;i<32;i++)feed(&h,marks[i]);for(int i=0;i<64;i++)feed(&h,direction_byte(i));return h;}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static void check(u32 code,const u32*args,const RadialRequest150BD954*q,const RadialPayload150BD954*p,const RadialRender150BD954*r){
 if(event_index>=7){bad=1;return;}const Event*e=&c->event[event_index++];if(code!=e->code)bad=1;for(int i=0;i<15;i++)if((args?args[i]:0)!=e->args[i])bad=1;Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;
 h=(Hash){0x811c9dc5U,0x9e3779b9U};if(q){for(int i=0;i<20;i++)feed(&h,canonical(q,i,i<12?4:i<16?2:4,i<12?i&~3:i<16?i&~1:16));feed(&h,q->count);for(int i=0;i<28;i++)feed(&h,i<24?canonical(p,i,4,i&~3):((const u8*)p)[i]);for(int i=0;i<30;i++)feed(&h,i<28?canonical(r,i,4,i&~3):((const u8*)r)[i]);}if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;
}
s32 func_150ADA20(void){check(1,0,0,0,0);mark_call();++rng_count;return(s32)c->rng[rng_count-1];}
f32 func_150ADA68(void){check(2,0,0,0,0);mark_call();++float_count;if(c->mode&1){if(float_count==1)D_8009FFD0=.25f;if(float_count==2){D_8009FFD4=.5f;D_8009FFD8=-.25f;D_8009FFDC=.125f;}if(float_count==3){D_8009FFE0=.75f;D_8009FFE4=-.375f;}}if(float_count==1&&(c->mode&2)){directions.first.x=2.0f;directions.first.y=-3.0f;directions.first.z=4.0f;}return floating(c->samples[float_count-1]);}
void*func_15147DA0(void*request,void*descriptor,s32 bytes,s32 active,s32 first,s32 second,s32 third,s32 fourth,s32 fifth,s32 fade,s32 alpha,void*render,s32 extra,u8 slot,s32 context){
 u32 args[]={0x40000-32,0x40000-64,(u32)bytes,(u32)active,(u32)first,(u32)second,(u32)third,(u32)fourth,(u32)fifth,(u32)fade,(u32)alpha,0x40000-100,(u32)extra,slot,(u32)context};RadialRequest150BD954*q=request;RadialPayload150BD954*p=descriptor;RadialRender150BD954*r=render;check(3,args,q,p,r);mark_call();++factory_count;q->active=1;if(c->mode&2){q->position.x=7.0f;p->field10=1.5f;r->field00=0x73;}if(c->mode&4){u32 n=0x12345678;for(int i=0;i<4;i++)arena.bytes[16+i]=n>>(8*(3-i));}return c->outcome?arena.bytes+16:0;
}
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=rng_count=float_count=factory_count=0;for(int i=0;i<0xcc;i++)arena.bytes[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<64;i++)((u8*)&directions)[i]=(i*29+c->seed*11+0x5a)&255;directions.first=(vertex){floating(c->normals[0]),floating(c->normals[1]),floating(c->normals[2])};directions.second=(vertex){floating(c->normals[3]),floating(c->normals[4]),floating(c->normals[5])};D_8009FFD0=floating(c->constants[0]);D_8009FFD4=floating(c->constants[1]);D_8009FFD8=floating(c->constants[2]);D_8009FFDC=floating(c->constants[3]);D_8009FFE0=floating(c->constants[4]);D_8009FFE4=floating(c->constants[5]);u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");s32 answer=func_150BD954((s32)c->unused[0],(s16)c->unused[1],floating(c->coords[0]),floating(c->coords[1]),floating(c->coords[2]),floating(c->unused[2]),floating(c->unused[3]),floating(c->unused[4]),(s16)c->unused[5],(u8)c->unused[6],floating(c->unused[7]),(s32)c->unused[8],floating(c->unused[9]),&directions.first,(u8)c->slot);Hash h=snapshot();if(answer!=1||event_index!=7||rng_count!=3||float_count!=3||factory_count!=1||h.a!=c->final.a||h.b!=c->final.b)bad=1;for(int i=0;i<16;i++)if(arena.bytes[i]!=((i*29+c->seed*11+0x5a)&255)||arena.bytes[0xbc+i]!=(((0xbc+i)*29+c->seed*11+0x5a)&255))bad=1;if(bad)return 42;
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
 original=selected();mutations=[('speed-factor','sample * 127.0f','sample * 126.0f'),('speed-base','+ 85.0f','+ 84.0f'),('direction-x','direction->x * speed','direction->z * speed'),('saved-y','payload.field14 = y','payload.field14 = x'),('first-modulo','% 86U','% 85U'),('byte-base','% 86U + 180','% 86U + 179'),('count-mask','& 3U','& 1U'),('life-modulo','% 31U','% 30U'),('life-base','% 31U + 39','% 31U + 38'),('second-scale','+ D_8009FFD8','+ D_8009FFD4'),('third-scale','* 356.0f','* 355.0f'),('flags','payload.field18 = 8','payload.field18 = 0'),('kind','payload.kind = 9','payload.kind = 8'),('alpha','payload.alpha = 255','payload.alpha = 254'),('request-mode','request.field0E = 1','request.field0E = 0'),('factory-first','&payload,0,1,11,','&payload,0,1,10,'),('slot','&render,0,slot,1','&render,0,slot ^ 1,1'),('context','&render,0,slot,1','&render,0,slot,0'),('return','return 1;','return 0;')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b,1);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_slot_bytes=True,canonical_dual32_memory_digests=True,initialized_factory_bytes_observed=79,unspecified_factory_bytes_excluded=13,no_native_private_record_observation_before_factory=True,legal_nonoverlapping_bounded_objects=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
