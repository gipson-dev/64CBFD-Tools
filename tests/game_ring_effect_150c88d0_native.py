"""SDK32 legal-object cases, opaque trig effects and canonical memory digests."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_ring_effect_150c88d0_match as p
from tools.tests import game_ring_effect_150c88d0_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def digest(data):
 a,b=0x811c9dc5,0x9e3779b9
 for v in data:a=((a^v)*16777619)&0xffffffff;b=((b+v+0x7f4a7c15)*0x85ebca6b)&0xffffffff
 return a,b
def selected():
 s=p.MANIFEST['selected_source'];return s[s.index('typedef struct {\n    u8 reserved0[0x14]; s32 count;'):s.index('\ns32 func_150C8A68(')]
def generate():
 cases=[]
 for rm in range(4):
  for n in(0,1,3,8):
   for mode in(0,1,2,4,8,15):cases.append(g.Case(count=n,mode=mode,fcsr=rm,seed=(n+mode)%16,lifetime=(-32768,-1,0,32767)[mode%4],priority=255,extra=24,group=-1))
 cases += [g.Case(count=3,priority=v,mode=v%16,fcsr=v%4,seed=v%16,lifetime=(v*257)^0x8000,extra=v%3*24,group=(0,-1,0x7fffffff)[v%3])for v in range(256)]
 cases += [g.Case(count=n,outcome=0,fcsr=rm,priority=0x123400fe,mode=mode)for n in(0,1,8)for rm in range(4)for mode in(0,1)]
 rows=[]
 for c in cases:
  initial=g.fixture(c);wanted,calls,obs,fcsr,answer=g.reference(initial,c);events=[]
  for (t,args),observation in zip(calls,obs):
   code={g.ALLOC:1,g.COPY:2,g.SIN:3,g.COS:4}[t];arguments=list(args)+[0]*(6-len(args));h=digest(observation[1])if code>=3 else(0,0);events.append('{'+str(code)+',{'+','.join(str(v)+'U'for v in arguments)+'},{'+','.join(str(v)+'U'for v in h)+'}}')
  final=digest(g.data(wanted,g.DESC,48)+g.data(wanted,g.OUT,g.SIZE)+g.data(wanted,g.ALT,240)+g.read(wanted,g.PERIOD).to_bytes(4,'big'))
  values=(c.count,g.half(c.lifetime),c.extra,c.priority,c.group,c.outcome,c.period,c.mode,c.seed,len(events));rows.append('{'+','.join(str(g.u32(v))+'U'for v in values)+',{'+','.join(str(v)+'U'for v in final)+'},{'+','.join(events)+'}}')
 text='''#include <ultra64.h>\n'''+selected()+'''
typedef char check_descriptor[sizeof(RingDescriptor150C88D0)==48?1:-1];
typedef char check_count[__builtin_offsetof(RingDescriptor150C88D0,count)==20?1:-1];
typedef char check_lookup[__builtin_offsetof(RingEffect150C88D0,lookup)==0x360?1:-1];
typedef char check_step[__builtin_offsetof(RingEffect150C88D0,angleStep)==0x48?1:-1];
typedef struct {u32 a,b;} Hash;
typedef struct {u32 code,args[6];Hash header;} Event;
typedef struct {u32 count,life,extra,priority,group,outcome,period,mode,seed,events;Hash final;Event event[18];} Row;
static const Row rows[]={\n'''+',\n'.join(rows)+'''};
typedef union {u64 align;RingEffect150C88D0 header;u8 bytes[0x1200];} Arena;
static Arena arena;static union{u64 align;u8 bytes[256];} alternate;
static RingDescriptor150C88D0 descriptor;static const Row *c;static u32 bad,event_index,sines,cosines,mark_out[0x1200/4],mark_alt[64];
f32 D_800A0528;
static u32 integer(const u8 *p,int n){u32 v=0;for(int i=n-1;i>=0;i--)v=(v<<8)|p[i];return v;}
static u32 bits(f32 f){union{f32 f;u32 i;}v;v.f=f;return v.i;}
static f32 floating(u32 b){union{f32 f;u32 i;}v;v.i=b;return v.f;}
static u32 virtual_address(u32 v){if(v>=(u32)arena.bytes&&v<(u32)arena.bytes+sizeof(arena))return v-(u32)arena.bytes+0x50000;if(v>=(u32)alternate.bytes&&v<(u32)alternate.bytes+256)return v-(u32)alternate.bytes+0x60000;if(v>=(u32)&descriptor&&v<(u32)&descriptor+48)return v-(u32)&descriptor+0x30000;return v;}
static void feed(Hash *h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static u8 canonical(const u8 *p,int at,int record,int initialized){
 static const u16 offsets[]={0x24,0x28,0x40,0x44,0x48,0x4c,0x50,0x54,0x58,0x360,0x364};static const u8 widths[]={4,2,4,4,4,2,4,4,4,4,4};
 if(!record){int start=at>=20&&at<24?20:at>=24&&at<26?24:-1;if(start>=0){int n=start==20?4:2;return integer(p+start,n)>>(8*(n-1-at+start));}return p[at];}
 if(initialized){for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++){int start=offsets[i],n=widths[i];if(at>=start&&at<start+n){u32 v=integer(p+start,n);if(start==0x54||start==0x58||start==0x360||start==0x364)v=virtual_address(v);return v>>(8*(n-1-at+start));}}}
 return p[at];
}
static Hash header_hash(void){Hash h={0x811c9dc5U,0x9e3779b9U};for(int i=0;i<0x368;i++)feed(&h,canonical(arena.bytes,i,1,1));return h;}
static void check_event(u32 code,u32 a0,u32 a1,u32 a2,u32 a3,u32 a4,u32 a5){
 if(event_index>=c->events){bad=1;return;}const Event *e=&c->event[event_index++];u32 args[]={a0,a1,a2,a3,a4,a5};if(code!=e->code)bad=1;for(int i=0;i<6;i++)if(args[i]!=e->args[i])bad=1;if(code>=3){Hash h=header_hash();if(h.a!=e->header.a||h.b!=e->header.b)bad=1;}
}
static void mark(u8 *p){u32 v=(u32)p;if(v>=(u32)arena.bytes&&v+4<=(u32)arena.bytes+sizeof(arena))mark_out[(v-(u32)arena.bytes)/4]=1;else if(v>=(u32)alternate.bytes&&v+4<=(u32)alternate.bytes+256)mark_alt[(v-(u32)alternate.bytes)/4]=1;else bad=1;}
void *func_15167A68(s32 type,s32 group,s32 bytes,s32 active,u8 priority,u8 flag){check_event(1,type,group,bytes,active,priority,flag);if(c->mode&1){descriptor.count=3;descriptor.lifetime=(s16)0x8123;}return c->outcome?arena.bytes:0;}
void *memcpy(void *dest,const void *src,unsigned int n){check_event(2,virtual_address((u32)dest),virtual_address((u32)src),n,0,0,0);u8 *d=dest;const u8 *s=src;for(unsigned i=0;i<n;i++)d[i]=s[i];if(c->mode&2){descriptor.count=5;arena.header.descriptor.count=2;arena.header.descriptor.lifetime=0x7ffe;D_800A0528=3.0f;}return dest;}
f32 sinf(f32 angle){check_event(3,bits(angle),0,0,0,0,0);++sines;if(c->mode&4)arena.header.lookup=(f32 (*)[2])(sines&1?alternate.bytes:arena.bytes+0x368);mark((u8*)arena.header.lookup+(sines-1)*8);return (f32)((s32)(sines%9)-4)*0.125f;}
f32 cosf(f32 angle){check_event(4,bits(angle),0,0,0,0,0);++cosines;if(c->mode&8){arena.header.lookup=(f32 (*)[2])(cosines&1?arena.bytes+0x368:alternate.bytes);arena.header.angleStep=0.5f;arena.header.descriptor.count=2;}mark((u8*)arena.header.lookup+(cosines-1)*8+4);return (f32)(5-(s32)(cosines%11))*0.125f;}
static int run(void){
 static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
  c=&rows[row];bad=event_index=sines=cosines=0;for(int i=0;i<0x1200;i++)arena.bytes[i]=((i+16)*29+c->seed*11+0x5a)&255;for(int i=0;i<256;i++)alternate.bytes[i]=((i+16)*29+c->seed*11+0x5a)&255;for(int i=0;i<48;i++)((u8*)&descriptor)[i]=((i+16)*29+c->seed*11+0x5a)&255;for(unsigned i=0;i<sizeof(mark_out)/sizeof(mark_out[0]);i++)mark_out[i]=0;for(int i=0;i<64;i++)mark_alt[i]=0;
  descriptor.count=(s32)c->count;descriptor.lifetime=(s16)c->life;D_800A0528=floating(c->period);u32 mxcsr=0x1f80U|(rounding[row<96?row/24:row<352?(row-96)%4:((row-352)/2)%4]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");
  void *answer=func_150C88D0(&descriptor,(s32)c->extra,(u8)c->priority,(s32)c->group);if(answer!=(c->outcome?(void*)arena.bytes:0)||event_index!=c->events)bad=1;
  Hash h={0x811c9dc5U,0x9e3779b9U};for(int i=0;i<48;i++)feed(&h,canonical((u8*)&descriptor,i,0,1));for(int i=0;i<0x1200;i++)feed(&h,mark_out[i/4]?integer(arena.bytes+(i/4)*4,4)>>(8*(3-i%4)):canonical(arena.bytes,i,1,c->outcome));for(int i=0;i<240;i++)feed(&h,mark_alt[i/4]?integer(alternate.bytes+(i/4)*4,4)>>(8*(3-i%4)):alternate.bytes[i]);u32 period=bits(D_800A0528);for(int i=3;i>=0;i--)feed(&h,period>>(8*i));if(h.a!=c->final.a||h.b!=c->final.b)bad=1;if(bad)return 42;
 }return 0;
}
__attribute__((force_align_arg_pointer))void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 return text,len(cases)
def main():
 text,count=generate();profiles={};controls=[]
 def run(name,body,opt):
  f=p.OUT/(name+'.c');exe=p.OUT/(name+'.exe');f.write_text(body);command=native_command(opt)+['-frounding-math','-fno-builtin',str(f),'-o',str(exe)];q=subprocess.run(command,cwd=p.ROOT,capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True,text=True);return dict(exit=q.returncode,source_sha256=sha(f),binary_sha256=sha(exe),command=command)
 for opt in('-O0','-O2','-O3'):
  q=run('native-'+opt[1:],text,opt);assert q['exit']==0,q;profiles[opt[1:]]=q
 original=selected();mutations=[('class','func_15167A68(0x31','func_15167A68(0x30'),('copy-size','descriptor,0x30);','descriptor,0x2C);'),('lookup-base','+ 0x368','+ 0x370'),('bands','bands = 5;','bands = 4;'),('band-base','+ 0x3B8','+ 0x3B4'),('lifetime','effect->lifetime = effect->descriptor.lifetime;','effect->lifetime = effect->descriptor.lifetime + 1;'),('division','D_800A0528 / effect->descriptor.count','D_800A0528 / (effect->descriptor.count + 1)'),('cosine-call','= cosf(angle);','= sinf(angle);'),('stride','offset += 8;','offset += 4;'),('angle-step','angle += effect->angleStep;','angle += effect->angleStep * 2.0f;')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,canonical_dual32_memory_digests=True,legal_nonoverlapping_bounded_objects=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
