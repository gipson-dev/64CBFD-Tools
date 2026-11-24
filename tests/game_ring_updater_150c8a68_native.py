"""SDK32 legal ring objects, ordered callback boundaries and dual memory digests."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_ring_updater_150c8a68_match as p
from tools.tests import game_ring_updater_150c8a68_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
FIELDS='flags life ticks fade_start fade_end initial emission update finish finish_result remainder radius growth rate step heading x z mode fcsr seed'.split()
def digest(data):
 a,b=0x811c9dc5,0x9e3779b9
 for v in data:a=((a^v)*16777619)&0xffffffff;b=((b+v+0x7f4a7c15)*0x85ebca6b)&0xffffffff
 return a,b
def snapshot_bytes(s):return s[0]+s[1]+s[2].to_bytes(4,'big')+s[3].to_bytes(4,'big')
def selected():
 s=p.MANIFEST['selected_source'];return s[s.index('typedef struct {\n    u8 reserved00[0x10];'):s.index('\ns32 func_150C8DB8(')]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not(c.flags&1)or -2147483648<=g.half(c.life)-c.ticks<=2147483647))
 cases += [g.Case(heading=g.bits(i*1.40625),rng=(0,),mode=0,fcsr=i%4)for i in range(256)]
 cases += [g.Case(flags=0,life=32767,initial=-32768,fade_start=0,emission=-1),g.Case(rate=g.bits(.125),remainder=g.bits(0.),step=g.bits(1.))]
 rows=[];angles=set()
 for c in cases:
  initial=g.fixture(c);wanted,calls,obs,fcsr=g.reference(initial,c);events=[]
  for(t,args),ob in zip(calls,obs):
   code={g.RNG:1,g.TRIG:2,g.EMIT:3,g.UPDATE:4,g.FINISH:5,g.RELEASE:6}[t];a=list(args)+[0]*(5-len(args));h=digest(snapshot_bytes(ob[0]));point=[int.from_bytes(ob[1][i:i+4],'big')for i in range(0,12,4)]if t==g.EMIT else[0,0,0]
   if t==g.EMIT:angles.add(args[2])
   events.append('{'+str(code)+',{'+','.join(str(g.u32(v))+'U'for v in a)+'},{'+','.join(str(v)+'U'for v in h)+'},{'+','.join(str(v)+'U'for v in point)+'}}')
  assert len(events)<=32;final=digest(snapshot_bytes(g.snapshot(wanted)));values=[g.u32(getattr(c,n))for n in FIELDS];randoms=list(c.rng)+[0]*(6-len(c.rng));assert len(randoms)==6
  rows.append('{'+','.join(str(v)+'U'for v in values)+','+str(len(c.rng))+',{'+','.join(str(g.u32(v))+'U'for v in randoms)+'},'+str(len(events))+',{'+','.join(str(v)+'U'for v in final)+'},{'+','.join(events)+'}}')
 assert angles==set(range(256)),set(range(256))-angles
 text='#include <ultra64.h>\n#include "structs.h"\nextern f32 D_800BE9A4;\nextern s32 D_800BE9E4;\ns32 func_150ADA20(void);\n'+selected()+'''
typedef char layout_record[sizeof(RingUpdate150C8A68)==0x54?1:-1];
typedef char layout_player[sizeof(RingPlayer150C8A68)==0x9a0?1:-1];
typedef char layout_life[__builtin_offsetof(RingUpdate150C8A68,lifetime)==0x28?1:-1];
typedef char layout_radius[__builtin_offsetof(RingUpdate150C8A68,radius)==0x44?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[5];Hash header;u32 point[3];}Event;
typedef struct{u32 '''+','.join(FIELDS)+''',rng_count,rng[6],events;Hash final;Event event[32];}Row;
static const Row rows[]={\n'''+',\n'.join(rows)+'''};
typedef union{u64 align;RingUpdate150C8A68 effect;u8 bytes[256];}Arena;
static Arena arena;static RingPlayer150C8A68 players[2];static u8 marks[32];static const Row *c;static u32 bad,event_index,rng_count,trig_count;
f32 D_800BE9A4;s32 D_800BE9E4,D_80082FA4;RingPlayer150C8A68 *D_800DBFF0=players;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n){for(int i=3;i>=0;i--)feed(h,n>>(i*8));}
static u8 canonical(int at){static const u8 offsets[]={0x10,0x14,0x18,0x20,0x24,0x28,0x2a,0x2c,0x30,0x34,0x38,0x40,0x44,0x48,0x4c,0x50};static const u8 widths[]={4,4,4,4,4,2,2,4,2,4,4,4,4,4,2,4};for(unsigned i=0;i<sizeof(offsets);i++){int start=offsets[i],n=widths[i];if(at>=start&&at<start+n){u32 v=0;for(int j=n-1;j>=0;j--)v=(v<<8)|arena.bytes[start+j];return v>>(8*(n-1-at+start));}}return arena.bytes[at];}
static Hash snapshot(void){Hash h={0x811c9dc5U,0x9e3779b9U};for(int i=0;i<256;i++)feed(&h,canonical(i));for(int i=0;i<32;i++)feed(&h,marks[i]);word(&h,bits(D_800BE9A4));word(&h,(u32)D_80082FA4);return h;}
static void mark(int at,u32 value){for(int i=3;i>=0;i--){marks[at+i]=value;value>>=8;}}
static u32 read_mark(int at){u32 value=0;for(int i=0;i<4;i++)value=(value<<8)|marks[at+i];return value;}
static void check(u32 code,u32 a0,u32 a1,u32 a2,u32 a3,u32 a4,const f32 *point){if(event_index>=c->events){bad=1;return;}const Event *e=&c->event[event_index++];u32 a[]={a0,a1,a2,a3,a4};if(code!=e->code)bad=1;for(int i=0;i<5;i++)if(a[i]!=e->args[i])bad=1;Hash h=snapshot();if(h.a!=e->header.a||h.b!=e->header.b)bad=1;if(point)for(int i=0;i<3;i++)if(bits(point[i])!=e->point[i])bad=1;}
s32 func_150ADA20(void){check(1,0,0,0,0,0,0);if(c->mode&1){D_80082FA4=1;arena.effect.radius=.25f;arena.effect.x=5.0f;D_800BE9A4=-.25f;}return(s32)c->rng[rng_count++%c->rng_count];}
f32 func_151423D8(u8 angle){check(2,angle,0,0,0,0,0);++trig_count;if(c->mode&2){arena.effect.radius=2.5f;if(trig_count&1)arena.effect.x=.5f;else arena.effect.z=-.25f;}return(f32)((s32)(trig_count%7)-3)*.125f;}
static void emit(RingUpdate150C8A68 *e,f32 *point,u8 angle,f32 sine,f32 cosine){if(e!=&arena.effect)bad=1;check(3,0x30000,0x40000-36,angle,bits(sine),bits(cosine),point);if(c->mode&4){e->remainder=1.5f;e->update=-1;e->finish=0;}mark(4,read_mark(4)+1U);}
static void update(RingUpdate150C8A68 *e,f32 previous){if(e!=&arena.effect)bad=1;check(4,0x30000,bits(previous),0,0,0,0);if(c->mode&8){e->finish=-1;e->radius=9.0f;}mark(8,0x13572468);}
static s32 finish(RingUpdate150C8A68 *e){if(e!=&arena.effect)bad=1;check(5,0x30000,0,0,0,0,0);mark(12,0x24681357);return c->mode&16?0:(s32)c->finish_result;}
void func_1516972C(struct102 *e){if((void*)e!=(void*)&arena.effect)bad=1;check(6,0x30000,0,0,0,0,0);mark(16,0x30000);}
void(*D_80088858[])(RingUpdate150C8A68*,f32*,u8,f32,f32)={emit};void(*D_80088864[])(RingUpdate150C8A68*,f32)={update};s32(*D_80088860[])(RingUpdate150C8A68*)={finish};
static int run(void){static const u32 rounding[]={0,3,2,1};for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 c=&rows[row];bad=event_index=rng_count=trig_count=0;for(int i=0;i<256;i++)arena.bytes[i]=((i+16)*29+c->seed*11+0x5a)&255;for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;
 RingUpdate150C8A68 *e=&arena.effect;e->x=floating(c->x);e->y=3.;e->z=floating(c->z);e->flags=(u8)c->flags;e->finish=(s8)c->finish;e->growthRate=floating(c->growth);e->count=3;e->lifetime=(s16)c->life;e->fadeStart=(s16)c->fade_start;e->fadeInScale=.125f;e->fadeEnd=(s16)c->fade_end;e->fadeOutScale=.25f;e->emissionRate=floating(c->rate);e->emission=(s8)c->emission;e->update=(s8)c->update;e->amplitude=7.;e->radius=floating(c->radius);e->angleStep=floating(0x3dcccccd);e->initialLifetime=(s16)c->initial;e->remainder=floating(c->remainder);
 D_800BE9A4=floating(c->step);D_800BE9E4=(s32)c->ticks;D_80082FA4=0;players[0].heading=floating(c->heading);players[1].heading=-45.;u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");func_150C8A68(e);Hash h=snapshot();if(event_index!=c->events||h.a!=c->final.a||h.b!=c->final.b)bad=1;if(bad)return 42;
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
 original=selected();mutations=[('timer','lifetime -= D_800BE9E4','lifetime += D_800BE9E4'),('growth','radius += effect->growthRate','radius -= effect->growthRate'),('elapsed-width','s16 elapsed;','s32 elapsed;'),('circumference','6.2831854820251465f','6.0f'),('rng-modulus','% 81U','% 80U'),('trig-angle','angle - 64','angle - 63'),('point-height','point[1] = effect->y','point[1] = effect->x'),('cull-limit','10894295.0f','0.0f'),('previous-radius','(effect,previousRadius)','(effect,previousRadius + 1.0f)'),('finish','(effect) == 0','(effect) != 0'),('remainder','remainder -= 1.0f','remainder -= 2.0f')]
 for name,a,b in mutations:
  assert a in original,name;changed=original.replace(a,b);q=run('native-'+name,text.replace(original,changed,1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,all_rounding_modes=True,all_256_emission_angles=True,canonical_dual32_memory_digests=True,legal_nonoverlapping_bounded_objects=True,strict_aliasing_and_UBSan=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
