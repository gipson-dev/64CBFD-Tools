"""Native SDK32 public bytes, passed records, rounding and effective source controls."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_dual_actor_emitter_150b37c8_match as p
from tools.tests import game_dual_actor_emitter_150b37c8_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.game_radial_angle_150c16c0_native import digest
from tools.experiments.game_remaining_donor_candidates import function_span
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
BLOCKS=((g.ACTOR,0xa0),(g.RECORD,64),(g.ALT,64),(g.PARAM,32),(g.ALTPARAM,32),(g.POSITIONS-128*20,256*20),(g.ALTPOS-128*20,256*20),(g.MARK,32),(g.TEMPLATE,6))
D=tuple(i for i in range(40)if i<7 or 8<=i<22 or 24<=i<28)
Q=tuple(i for i in range(28)if i<20 or i==21);P=tuple(i for i in range(32)if i<20 or 24<=i<28);V=tuple(range(30))
def public_bytes(m,c):
 assert set(g.public(m,c))=={a+i for a,n in BLOCKS for i in range(n)}
 return b''.join(g.data(m,a,n)for a,n in BLOCKS)
def known(private):
 if len(private)==1:return bytes(private[0][i]for i in D)
 if len(private)==3:return b''.join(bytes(b[i]for i in mask)for b,mask in zip(private,(Q,P,V)))
 assert not private;return b''
def selected():
 s=p.MANIFEST['selected_source'];a,z=function_span(s,p.FUNCTION);return s[a:z]
def support():
 s=(p.OUT/'selected-body.c').read_text();return s[:s.index('/* Submit the actor')]
def generate():
 cases=list(dict.fromkeys(replace(c,phase=0)for c in g.cases()if not c.home_mutations));rows=[];vec=lambda x:'{'+','.join(str(g.u32(v))+'U'for v in x)+'}'
 assert(len(D),len(Q)+len(P)+len(V))==(25,75)
 for c in cases:
  wanted,calls,obs,_=g.reference(g.fixture(c),c);events=[]
  for(t,args),(snapshot,fcsr)in zip(calls,obs):
   pub,private,homes=snapshot;code={g.FRNG:1,g.RNG:2,g.SUBMIT:3,g.FACTORY:4}[t];public_m=pub
   events.append('{'+str(code)+','+vec(list(args)+[0]*(15-len(args)))+','+vec(digest(public_bytes(public_m,c)))+','+vec(digest(known(private)))+'}')
  assert len(events)==8
  rows.append('{'+','.join(str(g.u32(v))+'U'for v in(c.index,c.height,c.mode,c.seed,c.fcsr,c.outcome))+','+vec(c.rng)+','+vec(c.samples)+','+vec(digest(public_bytes(wanted,c)))+',{'+','.join(events)+'}}')
 text='#include <ultra64.h>\n#include "structs.h"\n'+support()+'\nf32 func_150ADA68(void);\n'+selected()+r"""
typedef char check_abi[sizeof(void*)==4?1:-1];
typedef char check_descriptor[sizeof(Descriptor150B37C8)==40?1:-1];
typedef char check_request[sizeof(Request150B37C8)==28?1:-1];
typedef char check_payload[sizeof(Payload150B37C8)==32?1:-1];
typedef char check_render[sizeof(Render150B37C8)==32?1:-1];
typedef char check_position[sizeof(Position150B37C8)==20?1:-1];
typedef char check_choices[sizeof(Choices150B37C8)==6?1:-1];
typedef struct{u32 a,b;}Hash;
typedef struct{u32 code,args[15];Hash state,packet;}Event;
typedef struct{u32 index,height,mode,seed,fcsr,outcome,rng[4],samples[2];Hash final;Event event[8];}Row;
static const Row rows[]={
"""+',\n'.join(rows)+r"""};
typedef struct{u8 prefix[0x94];Position150B37C8*positions;u8*record;u8 tail[4];}ActorABI;
typedef struct{f32 f[5];u8 tail[44];}RecordABI;
static union{u64 align;ActorABI data;}actor_store;
static RecordABI records[2];static Position150B37C8 positions[2][256];static u8 params[2][32],marks[32];
Choices150B37C8 D_80088700;
static const Row*c;static u32 bad,event_index,float_count,int_count,first_count,last_count;
static u32 bits(f32 f){union{f32 f;u32 n;}v;v.f=f;return v.n;}
static f32 floating(u32 n){union{f32 f;u32 n;}v;v.n=n;return v.f;}
static void feed(Hash*h,u8 v){h->a=(h->a^v)*16777619U;h->b=(h->b+v+0x7f4a7c15U)*0x85ebca6bU;}
static void word(Hash*h,u32 n,int count){for(int i=count-1;i>=0;i--)feed(h,n>>(i*8));}
static Hash empty_hash(void){Hash h={0x811c9dc5U,0x9e3779b9U};return h;}
static u32 canonical_pointer(const void*p){
 if(p==(void*)(positions[0]+128))return 0x51000;if(p==(void*)(positions[1]+128))return 0x61000;
 if(p==(void*)&records[0])return 0x32000;if(p==(void*)&records[1])return 0x33000;
 if(p==(void*)params[0])return 0x36000;if(p==(void*)params[1])return 0x36100;bad=1;return 0;
}
static Hash snapshot(void){
 Hash h=empty_hash();u8*a=(u8*)&actor_store.data;
 for(int i=0;i<0x94;i++)feed(&h,a[i]);
 word(&h,canonical_pointer(actor_store.data.positions),4);word(&h,canonical_pointer(actor_store.data.record),4);
 for(int i=0;i<4;i++)feed(&h,actor_store.data.tail[i]);
 for(int k=0;k<2;k++){for(int i=0;i<5;i++)word(&h,bits(records[k].f[i]),4);for(int i=0;i<44;i++)feed(&h,records[k].tail[i]);}
 for(int k=0;k<2;k++)for(int i=0;i<32;i++)feed(&h,params[k][i]);
 for(int k=0;k<2;k++)for(int i=0;i<256;i++){word(&h,bits(positions[k][i].x),4);word(&h,bits(positions[k][i].y),4);word(&h,bits(positions[k][i].z),4);for(int j=0;j<8;j++)feed(&h,positions[k][i].opaque0C[j]);}
 for(int i=0;i<32;i++)feed(&h,marks[i]);for(int i=0;i<3;i++)word(&h,(u16)D_80088700.entries[i],2);return h;
}
static void mark_call(void){u32 n=0;for(int i=0;i<4;i++)n=(n<<8)|marks[i];++n;for(int i=3;i>=0;i--){marks[i]=n;n>>=8;}}
static int known_offset(int kind,int i){
 if(kind==0)return i<7||(i>=8&&i<22)||(i>=24&&i<28);
 if(kind==1)return i<20||i==21;if(kind==2)return i<20||(i>=24&&i<28);return i<30;
}
static u8 packet_byte(const u8*p,int kind,int i){
 int at=i;
 if(kind==0){if(i<4||(i>=8&&i<16)||(i>=24&&i<28))at=(i&~3)+3-(i&3);else if(i>=4&&i<6)at=(i&~1)+1-(i&1);}
 else if(kind==1){if(i<12||(i>=16&&i<20))at=(i&~3)+3-(i&3);else if(i>=12&&i<16)at=(i&~1)+1-(i&1);}
 else if(kind==2){if(i<20)at=(i&~3)+3-(i&3);}
 else if(i<28)at=(i&~3)+3-(i&3);
 return p[at];
}
static void packet(Hash*h,const void*p,int kind,int n){if(p)for(int i=0;i<n;i++)if(known_offset(kind,i))feed(h,packet_byte(p,kind,i));}
static void check(u32 code,const u32*a,const void*d,const void*q,const void*p,const void*v){
 if(event_index>=8){bad=1;return;}const Event*e=&c->event[event_index++];if(e->code!=code)bad=1;for(int i=0;i<15;i++)if(e->args[i]!=(a?a[i]:0))bad=1;
 Hash h=snapshot();if(h.a!=e->state.a||h.b!=e->state.b)bad=1;h=empty_hash();packet(&h,d,0,40);packet(&h,q,1,28);packet(&h,p,2,32);packet(&h,v,3,32);if(h.a!=e->packet.a||h.b!=e->packet.b)bad=1;
}
f32 func_150ADA68(void){
 check(1,0,0,0,0,0);mark_call();u32 n=++float_count;if(n>2){bad=1;return 0;}
 if(n==1&&(c->mode&1)){actor_store.data.positions=positions[1]+128;actor_store.data.record=(u8*)&records[1];for(int i=0;i<3;i++)D_80088700.entries[i]=100+i;}
 if(n==2&&(c->mode&8))records[0].f[3]=-12.f;return floating(c->samples[n-1]);
}
s32 func_150ADA20(void){
 check(2,0,0,0,0,0);mark_call();u32 n=++int_count;if(n>4){bad=1;return 0;}u8*a=(u8*)&actor_store.data;u8*rec=(u8*)&records[0];
 if(c->mode&2){if(n==2){rec[0x1a]=0x72;rec[0x1b]=0x83;}if(n==4){a[0x2d]=255;positions[0][127].x=42.f;positions[0][127].z=-17.f;a[0xc]=0xc3;a[1]=0xd4;}}
 return(s32)c->rng[n-1];
}
struct210*func_1513C73C(s32 descriptor,u8 tag,u8 tag2,s32 context,f32 x,f32 y,f32 z,f32 rangeX,f32 rangeZ,u8 byte,u8 parity,s32 flags,u8 channel,s32 kind){
 void*d=(void*)(u32)descriptor;u32 a[15]={0x40000-48,tag,tag2,canonical_pointer((void*)(u32)context),bits(x),bits(y),bits(z),bits(rangeX),bits(rangeZ),byte,parity,(u32)flags,channel,(u32)kind};
 check(3,a,d,0,0,0);mark_call();++first_count;u8*actor=(u8*)&actor_store.data;u8*rec=(u8*)&records[0];
 if(c->mode&4){actor[0x2d]=1;positions[0][129].x=123.f;positions[0][129].z=-82.f;records[0].f[0]=4.f;records[0].f[1]=7.f;records[0].f[3]=-9.f;records[0].f[4]=1.25f;rec[0x19]=23;rec[0x1a]=0x56;rec[0x1b]=0x67;actor[0x25]=13;}
 if(c->mode&8)for(int i=0;i<40;i++)((u8*)d)[i]=(i*7+0x31)&255;
 return c->outcome?(struct210*)(void*)&actor_store.data:0;
}
void*func_15147DA0(void*q,void*p,s32 a2,s32 a3,s32 a4,s32 a5,s32 a6,s32 a7,s32 a8,s32 a9,s32 a10,void*v,s32 a12,u8 a13,s32 a14){
 u32 a[15]={0x40000-88,0x40000-120,(u32)a2,(u32)a3,(u32)a4,(u32)a5,(u32)a6,(u32)a7,(u32)a8,(u32)a9,(u32)a10,0x40000-152,(u32)a12,a13,(u32)a14};check(4,a,0,q,p,v);mark_call();++last_count;
 if(c->mode&8){for(int i=0;i<28;i++)((u8*)q)[i]=(i*3+0x55)&255;for(int i=0;i<32;i++){((u8*)p)[i]=(i*3+0x55)&255;((u8*)v)[i]=(i*3+0x55)&255;}}
 return c->outcome?params[0]:0;
}
static void reset(void){
 u8*a=(u8*)&actor_store.data;for(int i=0;i<0xa0;i++)a[i]=(i*29+c->seed*11+0x5a)&255;
 actor_store.data.positions=positions[0]+128;actor_store.data.record=(u8*)&records[0];a[0x2d]=c->index;a[0xc]=0xa1;a[1]=0xb2;a[0x25]=7;
 for(int k=0;k<2;k++){
  u8*rec=(u8*)&records[k];for(int i=0;i<64;i++)rec[i]=(i*29+c->seed*11+0x5a)&255;records[k].f[0]=8.f;records[k].f[1]=2.f;records[k].f[2]=-3.f;records[k].f[3]=4.f;records[k].f[4]=.5f;rec[0x19]=17;rec[0x1a]=0xc1;rec[0x1b]=0xd2;
  for(int i=0;i<32;i++)params[k][i]=(i*29+c->seed*11+0x5a)&255;
  for(int i=0;i<256;i++){int index=i-128;positions[k][i].x=10.f+index;positions[k][i].y=20.f-index;positions[k][i].z=-30.f-index;u32 values[2]={bits(-1.f),bits(2.f)};for(int j=0;j<8;j++)positions[k][i].opaque0C[j]=values[j/4]>>(8*(3-(j&3)));}
 }
 for(int i=0;i<32;i++)marks[i]=(i*29+c->seed*11+0x5a)&255;for(int i=0;i<3;i++)D_80088700.entries[i]=15+i;
}
static int run(void){
 static const u32 rounding[]={0,3,2,1};
 for(unsigned row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
  c=&rows[row];bad=event_index=float_count=int_count=first_count=last_count=0;u32 initialize_mxcsr=0x1f80U;__asm__ volatile("ldmxcsr %0"::"m"(initialize_mxcsr):"memory");reset();u32 mxcsr=0x1f80U|(rounding[c->fcsr&3]<<13);__asm__ volatile("ldmxcsr %0"::"m"(mxcsr):"memory");
  s32 answer=func_150B37C8((u8*)&actor_store.data,1.f,2.f,3.f,floating(c->height),params[0]);Hash h=snapshot();
  if(answer!=1||event_index!=8||float_count!=2||int_count!=4||first_count!=1||last_count!=1||h.a!=c->final.a||h.b!=c->final.b)bad=1;if(bad)return 42;
 }return 0;
}
__attribute__((force_align_arg_pointer))void _start(void){int n=run();__asm__ volatile("int $0x80"::"a"(1),"b"(n):"memory");__builtin_unreachable();}
"""
 return text,len(cases)

def main():
 text,count=generate();profiles={};controls=[]
 def run(name,body,opt):
  f=p.OUT/(name+'.c');exe=p.OUT/(name+'.exe');f.write_text(body);command=native_command(opt)+['-frounding-math','-fno-builtin',str(f),'-o',str(exe)];q=subprocess.run(command,cwd=p.ROOT,capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True,text=True);return dict(exit=q.returncode,source_sha256=sha(f),binary_sha256=sha(exe),command=command)
 for opt in('-O0','-O2','-O3'):
  q=run('native-'+opt[1:],text,opt);assert q['exit']==0,q;profiles[opt[1:]]=q
 original=selected();mutations=[('record-control','record[0x20]=4','record[0x20]=3'),('first-range-factor','*50.0f+50.0f','*51.0f+50.0f'),('first-range-base','*50.0f+50.0f','*50.0f+49.0f'),('choice-modulo','%3U','%2U'),('first-duration','descriptor.duration=150','descriptor.duration=151'),('flags','descriptor.flags=17','descriptor.flags=16'),('resource','descriptor.resource=0x30002','descriptor.resource=0x30003'),('first-color','descriptor.field10=record[0x1B]','descriptor.field10=record[0x1A]'),('byte-mask','byteDraw&255','byteDraw&127'),('parity-bit','(func_150ADA20()&1)','(func_150ADA20()&0)'),('secondary-duration','request.duration=60','request.duration=61'),('secondary-kind','payload.kind=record[0x19]','payload.kind=record[0x1A]'),('scale-factor','*0.75f','*0.5f'),('secondary-range','*15.0f+15.0f','*16.0f+15.0f'),('factory-control','&request,&payload,0,1,7','&request,&payload,0,1,8'),('channel-byte','actor[0x0C]','actor[0x0D]'),('return','return 1;','return 0;')]
 for name,old,new in mutations:
  assert old in original,name;q=run('native-'+name,text.replace(original,original.replace(old,new,1),1),'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,SDK32=True,strict_aliasing_and_UBSan=True,all_four_rounding_modes=True,finite_inexact_cases=True,all_signed_byte_indices=True,canonical_dual32_public_byte_digests=True,first_descriptor_initialized_bytes=25,first_descriptor_unspecified_bytes_excluded=15,secondary_initialized_bytes=75,secondary_unspecified_bytes_excluded=17,no_private_inspection_without_passed_pointer=True,only_legal_bounded_native_objects=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0)
 (p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
