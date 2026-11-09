"""SDK32 layout, bounded callback mutation/recursion and independent state digests."""
import json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_node_range_walker_15169070_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_node_range_walker_15169070_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_range_clamp_candidates import SELECTED as CLAMP_BODY
from tools.tests.test_game_projected_packet_draw import native_command
def mutations(selected):
 p='node = D_800DD198[D_800DD190];'
 result={'wrong-lower-bound':selected.replace('2, 0x68','3, 0x68'),'wrong-upper-bound':selected.replace('2, 0x68','2, 0x67'),'wrong-row-stride':selected.replace('0x1A0','0x19C'),'missing-next-snapshot':selected.replace('D_800DD198[D_800DD190] = *(void **) ((u8 *) node + 8);','D_800DD198[D_800DD190] = 0;'),'late-next-reload':selected.replace(p,'node = *(void **)((u8 *)node + 8);'),'cached-callback':selected.replace('    void *node;','    void *node;\n    void (*callback)(void *,s32,u8);').replace('                if (descriptor->unk1C != NULL) {','                callback = descriptor->unk1C;\n                if (callback != NULL) {').replace('descriptor->unk1C(node, payload, opcode);','callback(node, payload, opcode);'),'missing-callback':selected.replace('descriptor->unk1C(node, payload, opcode);',';'),'missing-depth-unwind':selected.replace('D_800DD190--;',';'),'wrong-opcode-byte':selected.replace('(u8 *)payload, opcode','(u8 *)payload, opcode ^ 0x80'),'wrong-payload':selected.replace('(u8 *)payload, opcode','(u8 *)payload + 1, opcode'),'row-zero-only':selected.replace('D_800DCE50 + sizeof(D_800DCE50)','D_800DCE50 + 0x1A0'),'cached-last-bound':selected.replace('    void *node;','    void *node;\n    s32 savedLast;').replace('    if (first < last) {','    savedLast = last;\n    if (first < last) {').replace('column < last * 4','column < savedLast * 4')}
 result['wrong-row-stride']=selected.replace('head += 0x1A0;','head += 0x19C;')
 assert len(result)==12 and all(v!=selected for v in result.values());return result
def cases():
 return[c for c in guest.cases()if c.payload_kind in(0,1)and not c.mode&32 and(c.empty or c.depth in(-1,0,2))]+[guest.replace(guest.Case(),first=0,last=104,opcode=15,pattern=p,mode=m,real_helpers=r,caller=True)for p in range(3)for m in(0,15,16,64)for r in(False,True)]
def nid(p):return 0 if not p else guest.NODES.index(p)+1
def digest(values):
 h=2166136261
 for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def expected(c):
 m,calls,obs=guest.reference(guest.fixture(c),c);s=guest.SYMS;values=[m[s['D_800DD190']]]
 values +=[nid(guest.read(m,s['D_800DCE50']+4*i))for i in range(208)]
 for i in range(104):
  at=s['D_8008B4A8']+52*i;cb=guest.read(m,at+28);values.append({0:0,guest.CB0:1,guest.CB1:2}[cb]);values +=[m[at+j]for j in range(52)if not 28<=j<32]
 values +=[nid(guest.read(m,s['D_800DD198']+4*i))for i in range(6)]
 for node in guest.NODES:values +=[nid(guest.read(m,node+8)),*[m[node+j]for j in range(128)if not 8<=j<12]]
 trace=[]
 for(t,a),o in zip(calls,obs):
  if t==guest.CLAMP:code,x,y,z=0,a[2],a[3],0
  elif t==guest.ENTRY:code,x,y,z=5,a[0],a[1],a[3]&255
  else:code={guest.HELPER:1,guest.CLEAN:2,guest.CB0:3,guest.CB1:4}[t];x=nid(a[0]);y=0 if code==2 else{guest.PAYLOAD:0,s['D_800DD190']:1}[a[1]];z=0 if code==2 else a[2]
  trace +=[code,x,y,z,o[0],0 if code==0 else nid(o[1]),o[2]]
 return digest(values),digest(trace),len(calls)
def program(selected):
 rows=[]
 for c in cases():
  fields=[c.first,c.last,c.opcode,c.depth,c.pattern,c.mode,int(c.empty),c.payload_kind,c.tag,int(c.real_helpers),int(c.caller),*expected(c)];rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in fields)+'}')
 functions='\n'.join(p.replace('func_15169070(',name.replace('-','_')+'(')for name,p in{'candidate':selected,**mutations(selected)}.items())
 functions+='\n'+body((root/'conker/src/game_1944C0.c').read_text(),'func_15169040').replace('func_15169040','native_original_wrapper').replace('func_15169070','subject')
 clamp=CLAMP_BODY.replace('    s32 value1;','    s32 value1;\n    ctx.first = arg0; ctx.last = arg1; record(0, (u32)arg2, (u32)arg3, 0);')
 text=r'''#include <ultra64.h>
#include "functions.h"
#include "variables.h"
_Static_assert(sizeof(void*)==4,"SDK pointers");
_Static_assert(sizeof(struct115)==52,"descriptor stride");
_Static_assert(__builtin_offsetof(struct115,unk1C)==28,"callback offset");
struct Case{u32 first,last,opcode,depth,pattern,mode,empty,payloadKind,tag,real,caller,stateHash,traceHash,calls;};
static const struct Case rows[]={ROWS};static const struct Case*c;
struct Matrix{u8 before[16],bytes[832],after[16];};struct Matrix matrix;
struct Descriptors{u8 before[16];struct115 objects[104];u8 after[16];};struct Descriptors descriptors;
struct Slots{u8 before[16];void*values[6];u8 after[16];};struct Slots slots;
__asm__(".globl D_800DCE50\n.set D_800DCE50,matrix+16\n.globl D_8008B4A8\n.set D_8008B4A8,descriptors+16\n.globl D_800DD198\n.set D_800DD198,slots+16");
s8 D_800DD190;
struct Node{u8 before[8],bytes[128],after[8];};static struct Node nodes[10];static u8 eventBytes[32];
struct Context{s32*first,*last;};static struct Context ctx;
static u32 fired,trace,calls,failure[2];
typedef void(*Subject)(s32,s32,s32,u8);static Subject subject;
static void cb0(void*,s32,u8);static void cb1(void*,s32,u8);
static void*node(u32 i){return nodes[i].bytes;}
static u32 nodeId(void*p){u32 i;if(!p)return 0;for(i=0;i<10;i++)if(p==node(i))return i+1;return 0xFFFFFFFEu;}
static u32 payloadId(void*p){return p==eventBytes?0:p==(void*)&D_800DD190?1:99;}
static void*data(void){return c->payloadKind?(void*)&D_800DD190:eventBytes;}
static void**cursor(void){return &D_800DD198[(s32)D_800DD190];}
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static void record(u32 code,u32 a,u32 b,u32 op){u32 n=code?nodeId(*cursor()):0;hash(&trace,code);hash(&trace,a);hash(&trace,b);hash(&trace,op);hash(&trace,(u8)D_800DD190);hash(&trace,n);hash(&trace,(u32)*ctx.last);calls++;}
static void effect(void*p){void**saved;void*next;struct Context parent;if(fired)return;fired=1;saved=cursor();next=*saved;parent=ctx;
 if(c->mode&1)*(void**)((u8*)p+8)=node(8);
 if(c->mode&2)*saved=next?*(void**)((u8*)next+8):0;
 if(c->mode&4){next=*saved;D_800DD190++;*cursor()=next;}
 if(c->mode&8)D_8008B4A8[*(u8*)p].unk1C=cb1;
 if(c->mode&16)*ctx.last=3;
 if(c->mode&64){record(5,3,4,c->opcode&255);subject(3,4,(s32)data(),(u8)c->opcode);ctx=parent;}
 if(c->mode&128)*parent.first=99;
}
CLAMP
void func_1516972C(struct102*p){record(2,nodeId(p),0,0);effect(p);}
void func_1516968C(struct102*p,u8*payload,u8 opcode){record(1,nodeId(p),payloadId(payload),opcode);
 if(!c->real)effect(p);else if((opcode==15||opcode==16)&&*payload==*((u8*)p+12))func_1516972C(p);}
static void cb0(void*p,s32 payload,u8 opcode){record(3,nodeId(p),payloadId((void*)payload),opcode);effect(p);}
static void cb1(void*p,s32 payload,u8 opcode){record(4,nodeId(p),payloadId((void*)payload),opcode);effect(p);}
FUNCTIONS
static void initialize(void){u32 i,j;u8*b;static const s32 following[10]={1,2,-1,4,-1,6,-1,-1,9,-1};
 b=(u8*)&matrix;for(i=0;i<sizeof(matrix);i++)b[i]=0xA5;for(i=0;i<208;i++)*(void**)(D_800DCE50+4*i)=0;
 for(i=0;i<16;i++){descriptors.before[i]=descriptors.after[i]=slots.before[i]=slots.after[i]=0xA5;}
 for(i=0;i<104;i++){b=(u8*)&D_8008B4A8[i];for(j=0;j<52;j++)b[j]=(u8)(i*31+j*13+7);D_8008B4A8[i].unk1C=c->pattern==1||(c->pattern==2&&!(i&1))?cb0:0;}
 for(i=0;i<6;i++)D_800DD198[i]=0;
 for(i=0;i<10;i++){for(j=0;j<8;j++){nodes[i].before[j]=(u8)(i*19+((s32)j-8)*13+5);nodes[i].after[j]=(u8)(i*19+(j+128)*13+5);}for(j=0;j<128;j++)nodes[i].bytes[j]=(u8)(i*19+j*13+5);nodes[i].bytes[0]=(i<3||i==5||i==6||i>=8)?2:3;nodes[i].bytes[12]=(u8)c->tag;*(void**)(nodes[i].bytes+8)=following[i]<0?0:node((u32)following[i]);}
 if(!c->empty){*(void**)(D_800DCE50+8)=node(0);*(void**)(D_800DCE50+12)=node(3);*(void**)(D_800DCE50+416+8)=node(5);*(void**)(D_800DCE50+416+12)=node(7);}
 for(i=0;i<32;i++)eventBytes[i]=(u8)(i*17+3);eventBytes[0]=0x39;D_800DD190=(s8)c->depth;fired=calls=0;trace=2166136261u;
}
static u32 state(void){u32 h=2166136261u,i,j;u8*b;hash(&h,(u8)D_800DD190);
 for(i=0;i<208;i++)hash(&h,nodeId(*(void**)(D_800DCE50+4*i)));
 for(i=0;i<104;i++){void(*f)(void*,s32,u8)=D_8008B4A8[i].unk1C;hash(&h,f==0?0:f==cb0?1:f==cb1?2:99);b=(u8*)&D_8008B4A8[i];for(j=0;j<52;j++)if(j<28||j>=32)hash(&h,b[j]);}
 for(i=0;i<6;i++)hash(&h,nodeId(D_800DD198[i]));
 for(i=0;i<10;i++){hash(&h,nodeId(*(void**)(nodes[i].bytes+8)));for(j=0;j<128;j++)if(j<8||j>=12)hash(&h,nodes[i].bytes[j]);}
 return h;
}
static int canaries(void){u32 i,j;for(i=0;i<16;i++)if(matrix.before[i]!=0xA5||matrix.after[i]!=0xA5||descriptors.before[i]!=0xA5||descriptors.after[i]!=0xA5||slots.before[i]!=0xA5||slots.after[i]!=0xA5)return 0;
 for(i=0;i<10;i++)for(j=0;j<8;j++)if(nodes[i].before[j]!=(u8)(i*19+((s32)j-8)*13+5)||nodes[i].after[j]!=(u8)(i*19+(j+128)*13+5))return 0;return 1;}
static int check(Subject fn){u32 i;subject=fn;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){c=&rows[i];initialize();if(c->caller)native_original_wrapper((s32)data(),(u8)c->opcode);else subject((s32)c->first,(s32)c->last,(s32)data(),(u8)c->opcode);failure[0]=i;
 if(state()!=c->stateHash){failure[1]=1;return 1;}if(trace!=c->traceHash||calls!=c->calls){failure[1]=2;return 1;}if(!canaries()){failure[1]=3;return 1;}}
 return 0;}
static int run(void){if(check(candidate))return 1;
CONTROLS
return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int r=run();if(r)__asm__ volatile(".byte 0xcd,0x80"::"a"(4),"b"(2),"c"(failure),"d"(8):"memory");__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
 controls='\n'.join('if(!check('+name.replace('-','_')+')){failure[0]='+str(i)+';failure[1]=99;return 2;}'for i,name in enumerate(mutations(selected)))
 return text.replace('ROWS',',\n'.join(rows)).replace('CLAMP',clamp).replace('FUNCTIONS',functions).replace('CONTROLS',controls)
def main():
 selected=body((out/'final-owner.c').read_text(),'func_15169070');p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wno-unused-variable',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,struct.unpack('<II',r.stderr)if len(r.stderr)==8 else r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=12)
 report=dict(profiles=profiles,SDK32_layout=True,full_table_node_and_slot_canaries=True,recursive_callback_extension=True,portable_payload_aliases=True,guest_frame_and_pointer_byte_aliases_claimed=False,independent_model_expected_state=True,original_C_wrapper_cases=24)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
