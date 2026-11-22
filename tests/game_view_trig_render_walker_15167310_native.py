"""Actual SDK32 records, view fields, callback mutation and source controls."""
from pathlib import Path
import itertools,json,struct,subprocess,sys
from tools.experiments import game_view_trig_render_walker_15167310_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_view_trig_render_walker_15167310_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
def cases():
 return[g.Case(count=n,shape=shape,mode=mode,depth=(i%2)*3,angle=0x80000000 if i%3==0 else 0x3F123456)for i,(n,shape,mode)in enumerate(itertools.product((-3,-1,0,1,3,0x7FFFFFFF,0x80000000),(0,1,2,3),(0,1,2,4,16,32,64,128)))]+[g.Case(shape=4,mode=8,depth=0),g.Case(shape=1,mode=33),g.Case(shape=2,mode=129)]
def fnv(values):
 h=2166136261
 for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def ident(p):return 0 if not p else g.node_id(p)+1
def expected(c):
 m,calls,obs=g.reference(g.fixture(c),c);vals=[];trace=[]
 for o in obs:
  t,arg,a,b=o
  trace +=[1 if t==g.SYMS['sinf']else 2 if t==g.SYMS['cosf']else 3 if t==g.CB0 else 4,arg if t in(g.SYMS['sinf'],g.SYMS['cosf'])else ident(arg),a,(1 if b==g.VIEW else 2)if t in(g.SYMS['sinf'],g.SYMS['cosf'])else ident(b)]
 vals +=[g.read(m,g.SYMS[name]+4*i)for name,n in(('D_800DD1D8',4),('D_800DD1E8',4),('D_800DD1D0',2))for i in range(n)]
 vals +=[g.read(m,base+i*0x9A0+0x3A0)for base in(g.VIEW,g.ALT)for i in range(4)]
 vals +=[g.read(m,g.SYMS['D_80082FA0']),g.s8(m[g.SYMS['D_800DD190']]),1 if g.read(m,g.SYMS['D_800DBFF0'])==g.VIEW else 2]
 vals +=[0 if g.read(m,g.SYMS['D_8008B4A8']+52*i+12)==0 else 1 if g.read(m,g.SYMS['D_8008B4A8']+52*i+12)==g.CB0 else 2 for i in range(104)]
 vals +=[ident(g.read(m,g.SYMS['D_800DCE50']+4*i))for i in range(208)]
 for col in range(104):
  for row in range(2):
   active=c.shape==3 or c.shape in(1,2)and col in(0,1,51,103)or c.shape==4 and col==103 and row==1
   if active:vals +=[ident(g.read(m,g.node_at(row,col,i)+8))for i in range(3)]
 vals +=[ident(g.read(m,g.SYMS['D_800DD198']+4*i))for i in range(6)]
 return fnv(vals),fnv(trace),len(calls)
def controls(body):
 r={
 'initial-count-off-by-one':body.replace('+ 1) > 0','+ 1) > 1'),
 'wrong-angle-field':body.replace('.unk3A0','.pad3A4').replace('->unk3A0','->pad3A4'),
 'angle-reloaded-between-helpers':body.replace('cosf(angle)','cosf(D_800DBFF0->unk3A0)'),
 'missing-final-view-pair':body.replace('D_800DD1D0[1] = cosf(angle);','D_800DD1D0[1] = 0.0f;'),
 'wrong-sin-cos-output':body.replace('D_800DD1D8[i] = sinf(angle);','D_800DD1E8[i] = sinf(angle);'),
 'missing-last-column':body.replace('column != 104','column != 103'),
 'missing-second-row':body.replace('row += 0x1A0','row += 0x340'),
 'wrong-descriptor-column':body.replace('D_8008B4A8[column]','D_8008B4A8[column ^ 1]'),
 'missing-depth-increment':body.replace('D_800DD190++;',';'),
 'missing-depth-decrement':body.replace('D_800DD190--;',';'),
 'next-read-after-callback':body.replace('D_800DD198[D_800DD190] = (void *)node->unk8;\n                        descriptor->unkC(node);','descriptor->unkC(node);\n                        D_800DD198[D_800DD190] = (void *)node->unk8;'),
 'ignores-live-continuation':body.replace('node = D_800DD198[D_800DD190];','node = (struct102 *)node->unk8;'),
 'callback-captured-once':body.replace('    f32 angle;','    f32 angle;\n    void (*callback)(struct102 *);').replace('node = head;','node = head;\n                    callback = descriptor->unkC;').replace('descriptor->unkC(node);','callback(node);')}
 assert all(v!=body for v in r.values());return r
def program(body):
 rows=[]
 for c in cases():rows.append('{'+','.join(str(v)+'u'for v in[c.count&0xFFFFFFFF,c.shape,c.mode,c.depth,c.angle,*expected(c)])+'}')
 pre='''#include <ultra64.h>
#include "structs.h"
extern s32 D_80082FA0;extern struct108 *D_800DBFF0;extern f32 D_800DD1D8[4],D_800DD1E8[4],D_800DD1D0[2];
extern struct115 D_8008B4A8[104];extern u8 D_800DCE50[0x340];extern s8 D_800DD190;extern void *D_800DD198[6];
f32 sinf(f32);f32 cosf(f32);
'''
 text=pre+body.replace('func_15167310(','subject(')+'\n'
 text+='''
_Static_assert(sizeof(struct102)==0x1D8&&sizeof(struct108)==0x9A0&&sizeof(struct115)==52,"Actual SDK32 records");
_Static_assert(__builtin_offsetof(struct102,unk8)==8&&__builtin_offsetof(struct108,unk3A0)==0x3A0&&__builtin_offsetof(struct115,unkC)==12,"Recovered fields");
typedef struct{u32 count,shape,mode,depth,angle,state,trace,calls;}Row;
static const Row rows[]={'''+',\n'.join(rows)+'''};
static const Row *c;static struct{u8 before[16];struct102 nodes[624];u8 after[16];}store;
static struct108 views[2][4];s32 D_80082FA0;struct108 *D_800DBFF0;
f32 D_800DD1D8[4],D_800DD1E8[4],D_800DD1D0[2];struct115 D_8008B4A8[104];
u8 D_800DCE50[0x340] __attribute__((aligned(4)));s8 D_800DD190;void *D_800DD198[6];
static u32 calls,trace,error;static void cb0(struct102*);static void cb1(struct102*);
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static u32 word(f32 f){union{u32 b;f32 f;}v;v.f=f;return v.b;}
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
static u32 id(struct102*p){return p?(u32)(p-store.nodes)+1:0;}
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static f32 trig(u32 target,f32 angle){u32 b=word(angle);hash(&trace,target);hash(&trace,b);hash(&trace,(u32)D_80082FA0);hash(&trace,D_800DBFF0==views[0]?1:2);
 if(!calls){if(c->mode&32){D_800DBFF0=views[1];views[0][0].unk3A0=real(0xBF654321);}if(c->mode&64)D_80082FA0=-1;if(c->mode&128)D_80082FA0=3;}calls++;
 return real((b^(target==1?0x13579BDFu:0x2468ACE0u))+0x10203u);
}
f32 sinf(f32 a){return trig(1,a);}f32 cosf(f32 a){return trig(2,a);}
static void callback(struct102*p,u32 target){u32 n=id(p)-1,col=n/6,index=n%3;
 hash(&trace,target);hash(&trace,n+1);hash(&trace,(u32)(s32)D_800DD190);hash(&trace,id(D_800DD198[(s32)D_800DD190]));calls++;
 if(c->mode&1)D_8008B4A8[col].unkC=cb1;if(c->mode&2)p->unk8=0;
 if(c->mode&4)D_800DD198[(s32)D_800DD190]=0;
 if((c->mode&8)&&index==0){D_800DD190++;D_800DD198[(s32)D_800DD190]=0;}
 if((c->mode&16)&&col==0)*(struct102**)(D_800DCE50+4*51)=0;
}
static void cb0(struct102*p){callback(p,3);}static void cb1(struct102*p){callback(p,4);}
static u32 active(u32 col,u32 row){return c->shape==3||((c->shape==1||c->shape==2)&&(col==0||col==1||col==51||col==103))||(c->shape==4&&col==103&&row==1);}
static u32 state(void){u32 h=2166136261u,i,j,row,col;u8*p;
 for(i=0;i<4;i++)hash(&h,word(D_800DD1D8[i]));for(i=0;i<4;i++)hash(&h,word(D_800DD1E8[i]));for(i=0;i<2;i++)hash(&h,word(D_800DD1D0[i]));
 for(row=0;row<2;row++)for(i=0;i<4;i++)hash(&h,word(views[row][i].unk3A0));
 hash(&h,(u32)D_80082FA0);hash(&h,(u32)(s32)D_800DD190);hash(&h,D_800DBFF0==views[0]?1:2);
 for(i=0;i<104;i++){hash(&h,D_8008B4A8[i].unkC==cb0?1:D_8008B4A8[i].unkC==cb1?2:0);p=(u8*)&D_8008B4A8[i];for(j=0;j<52;j++)if((j<12||j>=16)&&p[j])error++;}
 for(i=0;i<208;i++)hash(&h,id(*(struct102**)(D_800DCE50+4*i)));
 for(col=0;col<104;col++)for(row=0;row<2;row++)if(active(col,row))for(i=0;i<3;i++){
  struct102*n=&store.nodes[(col*2+row)*3+i];hash(&h,id((struct102*)n->unk8));p=(u8*)n;
  for(j=0;j<sizeof(*n);j++)if((j<8||j>=12)&&p[j]!=(u8)(j*13+col+row+i))error++;
 }
 for(i=0;i<6;i++)hash(&h,id(D_800DD198[i]));for(i=0;i<16;i++)if(store.before[i]!=0xD1||store.after[i]!=0xD2)error++;
 return h;
}
void _start(void){u32 n,i,j,k,col,row,h;int result=0;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  c=&rows[n];calls=0;trace=2166136261u;error=0;fill(store.before,16,0xD1);fill(store.after,16,0xD2);
  fill((u8*)D_8008B4A8,sizeof(D_8008B4A8),0);fill(D_800DCE50,sizeof(D_800DCE50),0);fill((u8*)D_800DD198,sizeof(D_800DD198),0);
  for(i=0;i<4;i++){D_800DD1D8[i]=0;D_800DD1E8[i]=0;}D_800DD1D0[0]=0;D_800DD1D0[1]=0;
  for(i=0;i<2;i++)for(j=0;j<4;j++){views[i][j].unk3A0=real(c->angle+0x12345*j+(i?0x100000:0));views[i][j].pad3A4=real(0x12345678);}
  D_800DBFF0=views[0];D_80082FA0=(s32)c->count;D_800DD190=(s8)c->depth;
  for(col=0;col<104;col++){
   D_8008B4A8[col].unkC=c->shape==0||(c->shape==2&&(col&1))?0:cb0;
   for(row=0;row<2;row++)if(active(col,row)){
    *(struct102**)(D_800DCE50+416*row+4*col)=&store.nodes[(col*2+row)*3];
    for(i=0;i<3;i++){
     struct102*p=&store.nodes[(col*2+row)*3+i];for(k=0;k<sizeof(*p);k++)((u8*)p)[k]=(u8)(k*13+col+row+i);
     p->unk8=i<2&&c->shape!=4?(s32)&store.nodes[(col*2+row)*3+i+1]:0;
    }
   }
  }
  subject();h=state();if(error||h!=c->state||trace!=c->trace||calls!=c->calls){u32 diagnostic[7]={n,h,c->state,trace,c->trace,calls,c->calls};__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(diagnostic),"d"(28));result=1;break;}
 }
 __asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return text
def main():
 body=(out/'selected-body.c').read_text();text=program(body);source=out/'native.c';source.write_text(text);profiles={}
 def run(text,label,opt):
  src=out/(label+'.c');src.write_text(text);exe=out/(label+opt);cmd=native_command(opt);cmd[1:1]=['-I',str(out/'proposal/conker/include')];cmd+=['-fno-builtin','-fstrict-aliasing',str(src),'-o',str(exe)]
  q=subprocess.run(cmd,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(text,'native',opt);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stderr.hex());profiles[opt]=dict(cases=len(cases()),SDK32=True,strict_aliasing=True,UBSan=True)
 effective=[]
 for name,changed in controls(body).items():
  q=run(program(changed),'native-control-'+name,'-O2');assert q.returncode!=0,('Ineffective native source control',name);effective.append(name)
 r=dict(profiles=profiles,effective_source_controls=effective,actual_SDK_records_and_full_unchanged_fields=True,ordered_trace_and_all_caches_heads_callbacks_continuations=True,
  limits='Native depth slots0..5 and four-view domain only; pointer heads retain the existing SDK byte-table view. Guest-only extended depth bytes are separately mapped.',source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
