"""Complete SDK32 parent checked against the complete retail MIPS parent."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess,sys
from tools.experiments import game_render_list_parent_151674f8_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests.game_render_list_parent_151674f8_guest import Parent,p,g
from tools.tests.test_game_projected_packet_draw import native_command
ALT=0x15602000;CACHE=g.SYMS['D_800DD1B0'];WORDS=128
FIELDS=[(0,4,'u32'),(4,4,'s32'),(8,4,'s32')]+[(i,2,'s16')for i in range(12,32,2)]+[(0x48,2,'s16'),(0x4C,4,'s32'),(0x50,4,'s32'),(0x54,2,'s16'),(0x56,2,'s16')]+[(i,4,'u32'if i in(0x68,0x6C)else's32')for i in range(0x58,0x7C,4)]
SIZES={i:n for i,n,t in FIELDS}
@dataclass(frozen=True)
class Case(p.Case):
 stage_mask:int=15
 before_effect:int=0
 draw_effect:int=0
 after_effect:int=0
 initial_depth:int=0
 recursive:bool=False
def cases():
 result=[Case(**{**vars(c),'phase':0,'viewport':min(c.viewport,1),'effect':0})for c in p.rows()]
 result +=[Case(row=row,shape=shape,draw_mode=mode,stages=stage,budget=budget,view=view)for row,shape,mode,stage,budget,view in itertools.product((0,1),(2,3),(0,1,2),(False,True),(0,2,3,4,5,8,1000),(-32768,-1,0,1,32767))]
 result +=[Case(row=row,shape=3,draw_mode=mode,stages=True,stage_mask=mask,budget=budget,view=-1,before_effect=be,draw_effect=de,after_effect=ae,initial_depth=depth)
  for row,mode,mask,budget,be,de,ae,depth in itertools.product((0,1),(0,1,2),(1,2,4,8,15),(3,1000),(0,),(0,),(0,),(0,))]
 for effect in(1,2,4,8,15):
  for row,mode,budget,depth in itertools.product((0,1),(0,1,2),(3,1000),(0,4)):
   result +=[Case(row=row,shape=3,draw_mode=mode,stages=True,budget=budget,before_effect=effect,initial_depth=depth),Case(row=row,shape=3,draw_mode=mode,stages=True,budget=budget,draw_effect=effect,initial_depth=depth),Case(row=row,shape=3,draw_mode=mode,stages=True,budget=budget,after_effect=effect,initial_depth=depth)]
 result +=[Case(shape=3,draw_mode=mode,stages=stage,budget=1000,clear_next=True,start=5,stop=6,view=view,initial_depth=depth,recursive=True)for mode,stage,view,depth in itertools.product((0,1,2),(False,True),(0,1),(0,2,3))]
 return list(dict.fromkeys(result))
def fixture(c):
 m,nodes=p.fixture(c);base=g.fixture(c)
 for idx in range(4):
  at=g.STATE+idx*0x100
  if at not in m:
   for j in range(76):m[at+j]=base[g.STATE+j]
 m[p.DEPTH]=c.initial_depth
 for col in(5,66):
  d=p.DESC+col*52
  for bit,off in((1,0x10),(2,0x14),(4,0x24),(8,0x20)):
   if not c.stage_mask&bit:g.put(m,d+off,0)
 if c.recursive:g.put(m,p.HEADS+0x1A0+66*4,g.STATE+0x200)
 return m,nodes
def fnv(values):
 h=2166136261
 for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def cache_values(m):
 result=[];i=0
 while i<128:
  n=SIZES.get(i,1);result.append(g.get(m,CACHE+i,n));i+=n
 return result
def boundary_values(m):
 result=[m[p.DEPTH],m[g.SYMS['D_800BE9C0']],g.get(m,g.SYMS['D_800BEBA4']),g.get(m,g.SYMS['D_8003C8E0']),m[g.SYMS['D_800D2DAB']]]
 result +=[g.get(m,p.ITER+i*4)for i in range(6)]
 result +=[g.get(m,g.SYMS['D_800BE9C8']+i*4)for i in range(2)]
 result +=[g.get(m,p.HEADS+i*4)for i in range(208)]
 result +=cache_values(m)
 for idx in range(4):
  at=g.STATE+idx*0x100;i=0
  while i<76:
   n=4 if i in(4,8)else 1;result.append(g.get(m,at+i,n));i+=n
 return result
def state_values(m):
 result=boundary_values(m)
 for col in range(101):
  at=p.DESC+col*52;i=0
  while i<52:
   n=4 if i in(8,0x10,0x14,0x20,0x24)else 1;result.append(g.get(m,at+i,n));i+=n
 result +=[g.get(m,g.OUTPUT+i*4)for i in range(WORDS)]
 return result
def trace_values(log):
 result=[]
 for event in log:result.extend(event)
 return result
class Model(Parent):
 def __init__(self,words,m,c,nodes):super().__init__(words,[],m,c,nodes);self.log=[];self.draw_id=0;self.parent_words=words;self.child_invocations=0
 def record_call(self,t):
  if t in(g.ENTRY,ALT):
   self.draw_id=int(t==ALT);super().record_call(g.ENTRY);a=self.called_targets[-1];self.log.append((2+self.draw_id,*a,fnv(boundary_values(self.memory))));return
  super().record_call(t);a=self.parent_events[-1][1]
  args=(a[0],0xF001,0xF002)if t==p.RANGE else a
  self.log.append((0 if t==p.RANGE else 1 if t==p.BEFORE else 4,*args,fnv(boundary_values(self.memory))))
 def hook(self,t):
  if t in(g.ENTRY,ALT):
   output,node,view=self.called_targets[-1];idx=(node-g.STATE)//0x100;col=66 if idx>=2 else 5;ef=self.case.draw_effect
   g.put(self.memory,output,0xAB000000|self.draw_id);g.put(self.memory,output+4,idx<<16|(view&65535))
   if self.case.clear_next or ef&1:g.put(self.memory,node+8,0)
   if ef&2:
    self.memory[g.SYMS['D_800BE9C0']]=1;g.put(self.memory,g.SYMS['D_800BE9C8']+4,g.OUTPUT+8);g.put(self.memory,g.SYMS['D_800BEBA4'],1)
   if ef&4:
    depth=g.s16(self.memory[p.DEPTH])
    assert 0<=depth<6;g.put(self.memory,p.ITER+8,g.get(self.memory,p.ITER+4*depth));self.memory[p.DEPTH]=2
   if ef&8:g.put(self.memory,p.DESC+col*52+8,ALT)
   value=output+8
   if self.case.recursive:
    child_case=replace(self.case,row=1,start=66,stop=67,recursive=False,phase=0)
    child=Model(self.parent_words,self.memory,child_case,self.nodes)
    # Bootstrap through the shared entry-phase fixture, then supply the
    # actual lower, aligned child stack below a bounded callback frame.
    child.r[29]=self.r[29]-32;child.before[29]=child.r[29];child.r[4]=value;child.run()
    self.memory=child.memory;self.log.extend(child.log);self.child_invocations+=1+child.child_invocations;value=child.r[2]
  else:
   super().hook(t)
   if t==p.RANGE:return
   a=self.parent_events[-1][1];col=a[1];ef=self.case.before_effect if t==p.BEFORE else self.case.after_effect
   if t==p.BEFORE:
    if ef&1:
     chain=self.nodes[col];g.put(self.memory,p.HEADS+self.case.row*0x1A0+col*4,chain[-1]if chain else 0)
    if ef&2:g.put(self.memory,p.DESC+col*52+8,ALT)
    if ef&8:g.put(self.memory,CACHE+4,0x11223344)
   else:
    if ef&2:self.memory[p.DEPTH]=3
    if ef&4:g.put(self.memory,CACHE+4,0x55667788)
    if ef&8:g.put(self.memory,p.DESC+66*52+8,ALT)
   if(t==p.BEFORE and ef&4)or(t==p.AFTER and ef&1):
    self.memory[g.SYMS['D_800BE9C0']]=1;g.put(self.memory,g.SYMS['D_800BE9C8']+4,g.OUTPUT+8);g.put(self.memory,g.SYMS['D_800BEBA4'],3 if t==p.BEFORE else 1)
   return
  for i in range(4):g.put(self.memory,self.r[29]+i*4,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def controls(body):
 result={
 'missing-matrix':body.replace('gSPMatrix(output++, &D_80089470, G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);',';'),
 'wrong-row-stride':body.replace('row * 0x1A0','row * 0x1A4'),
 'missing-image-invalidation':body.replace('D_800DD1B0 = 0xFFFFFFFFU;',';'),
 'wrong-material-reset':body.replace('D_800DD224 = 2;','D_800DD224 = 1;'),
 'wrong-short-sentinel':body.replace('D_800DD1C6 = -1;','D_800DD1C6 = 0;'),
 'missing-before-list':body.replace('gSPDisplayList(output++, descriptor->beforeList);',';'),
 'missing-before-hook':body.replace('output = descriptor->before(output, column, row, view);',';'),
 'wrong-clear-geometry':body.replace('gSPClearGeometryMode(output++, G_LIGHTING);','gSPClearGeometryMode(output++, G_CULL_BACK);'),
 'lost-saved-next':body.replace('D_800DD198[D_800DD190] = node->next;','D_800DD198[D_800DD190] = NULL;'),
 'wrong-depth-slot':body.replace('D_800DD198[D_800DD190]','D_800DD198[0]'),
 'premature-list-end':body.replace('node = D_800DD198[D_800DD190];','node = NULL;'),
 'wrong-budget-equality':body.replace('> D_800BEBA4','>= D_800BEBA4'),
 'missing-node-rollback':body.replace('output = beforeNode;','output = output;'),
 'lost-sticky-overflow':body.replace('overflowed = 1;','overflowed = 0;'),
 'wrong-mode-zero-return':body.replace('return modeZeroStart;','return output;'),
 'wrong-mode-one-return':body.replace('return modeOneStart;','return output;'),
 'missing-after-list':body.replace('gSPDisplayList(output++, descriptor->afterList);',';'),
 'missing-after-hook':body.replace('output = descriptor->after(output, column, view);',';'),
 'wrong-draw-view':body.replace('output = draw(output, node, view);','output = draw(output, node, 0);'),
 'missing-final-geometry':body.replace('gSPSetGeometryMode(output++, G_ZBUFFER);',';'),
 }
 assert all(v!=body for v in result.values());return result
def program():
 rows=cases();retail=list(struct.unpack('>348I',(r/'conker/conker.us.bin').read_bytes()[0x1949A8:0x194F18]));raw=g.bound_blob(*g.payload(o/'selected/candidate.o','func_151674F8'),g.SYMS);encoded=[]
 def arr(xs):return'{'+','.join('0x%Xu'%g.u32(x)for x in xs)+'}'
 for c in rows:
  memory,nodes=fixture(c);truth=Model(retail,memory,c,nodes).run();source=Model(raw,memory,c,nodes).run()
  assert g.public(truth.memory)==g.public(source.memory)and truth.log==source.log and truth.r[2]==source.r[2]and truth.child_invocations==source.child_invocations,c
  if c.recursive:assert truth.child_invocations==2
  assert g.OUTPUT<=truth.r[2]<=g.OUTPUT+WORDS*4
  encoded.append(arr((c.row,c.shape,c.draw_mode,c.stage_mask if c.stages else 0,c.budget,c.clear_next,c.start,c.stop,c.viewport,c.view,c.before_effect,c.draw_effect,c.after_effect,c.initial_depth,fnv(state_values(truth.memory)),fnv(trace_values(truth.log)),len(truth.log),(truth.r[2]-g.OUTPUT)//8,c.recursive)))
 memory,_=fixture(Case());base=g.fixture(Case());data=g.data(memory,p.DESC,101*52);cache_decl=[];at=0
 for i,n,t in FIELDS:
  if i>at:cache_decl.append('u8 pad%02X[%d];'%(at,i-at))
  cache_decl.append('%s f%02X;'%(t,i));at=i+n
 if at<128:cache_decl.append('u8 pad%02X[%d];'%(at,128-at))
 pre='#include <ultra64.h>\n#include "structs.h"\n'+'''typedef struct ListNode {u8 index,row,pad2[2];struct ListNode *prev,*next;}ListNode;\n'''+(o/'selected/declarations.c').read_text()+'''\nextern struct115 D_8008B4A8[];extern u8 D_800DCE50[0x340];extern s8 D_800DD190;extern void*D_800DD198[];extern u8 D_800BE9C0,D_800D2DAB;extern s32 D_8003C8E0;\n'''
 pre+='typedef struct {'+''.join(cache_decl)+'}Cache;\n'
 pre+=r'''
typedef struct{ListNode header;u8 opaque[64];}Node;
static struct{u8 before[16];Node value[4];u8 after[16];}records;
static struct{u8 before[16];ListRenderDescriptor value[101];u8 after[16];}descriptors;
static struct{u8 before[16];ListNode*value[208];u8 after[16];}heads;
static struct{u8 before[16];Cache value;u8 after[16];}cache;
static struct{u8 before[16];Gfx value[64];u8 after[16];}commands;
static struct{u8 before[16];s8 depth;u8 pad[3];void*iter[6];Gfx*bases[2];s32 budget;u32 tag;u8 viewport,dirty;u8 tail[14];u8 after[16];}globals;
Mtx D_80089470 __attribute__((section(".matrix"),aligned(8)));
#define D_8008B4A8 descriptors.value
#define D_800DCE50 ((u8*)heads.value)
#define D_800DD190 globals.depth
#define D_800DD198 globals.iter
#define D_800BE9C8 globals.bases
#define D_800BEBA4 globals.budget
#define D_800BE9C0 globals.viewport
#define D_800D2DAB globals.dirty
#define D_8003C8E0 globals.tag
'''
 for i,n,t in FIELDS:pre+='#define D_800DD%03X cache.value.f%02X\n'%(0x1B0+i,i)
 assertions='_Static_assert(sizeof(void*)==4&&sizeof(Gfx)==8&&sizeof(ListNode)==12&&sizeof(Node)==76&&sizeof(ListRenderDescriptor)==52&&sizeof(Cache)==128,"SDK32 measured objects");\n'
 for field,off in(('draw',8),('beforeList',16),('before',20),('after',32),('afterList',36),('mode',48)):assertions+='_Static_assert(__builtin_offsetof(ListRenderDescriptor,%s)==%d,"Descriptor %s");\n'%(field,off,field)
 assertions+='_Static_assert(__builtin_offsetof(ListNode,next)==8&&104*sizeof(ListNode*)==0x1A0,"Node/list layouts");\n'
 for i,n,t in FIELDS:assertions+='_Static_assert(__builtin_offsetof(Cache,f%02X)==%d,"Cache field");\n'%(i,i)
 support=r'''
typedef struct{u32 row,shape,mode,stages,budget,clearNext,first,last,viewport,view,beforeEffect,drawEffect,afterEffect,initialDepth,stateHash,traceHash,calls,returned,recursive;}Row;
static const Row rows[]={ROWS};static const Row*c;
static const u8 descriptorInitial[]={DESCRIPTORS};static const u8 nodeInitial[]={NODE};
static u32 trace,calls,error,inChild;
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static u32 be(const u8*p,u32 n){u32 v=0,i;for(i=0;i<n;i++)v=v*256+p[i];return v;}
static u32 le(const u8*p,u32 n){u32 v=0,i;for(i=0;i<n;i++)v|=(u32)p[i]<<(i*8);return v;}
static void putbe16(u8*p,s32 v){p[0]=(u8)((u32)v>>8);p[1]=(u8)v;}
static u32 nodeId(const void*p){u32 i;for(i=0;i<4;i++)if(p==&records.value[i].header)return 0x30000+i*0x100;return(u32)p;}
static ListNode*nodePointer(u32 v){u32 i;for(i=0;i<4;i++)if(v==0x30000+i*0x100)return&records.value[i].header;return(ListNode*)v;}
static u32 outId(const Gfx*p){u32 v=(u32)p,base=(u32)commands.value;if(v<base||v>base+sizeof(commands.value)||((v-base)&7)){error++;return v;}return 0x50000+v-base;}
static u32 numberSize(u32 i){switch(i){CACHE_SIZES default:return 1;}}
static void boundary(u32*h){u32 i,k,n;u8*b=(u8*)&cache.value;
 hash(h,(u8)globals.depth);hash(h,globals.viewport);hash(h,(u32)globals.budget);hash(h,globals.tag);hash(h,globals.dirty);
 for(i=0;i<6;i++)hash(h,nodeId(globals.iter[i]));for(i=0;i<2;i++)hash(h,outId(globals.bases[i]));for(i=0;i<208;i++)hash(h,nodeId(heads.value[i]));
 for(i=0;i<128;i+=n){n=numberSize(i);hash(h,le(b+i,n));}
 for(k=0;k<4;k++){b=(u8*)&records.value[k];for(i=0;i<76;i+=n){n=(i==4||i==8)?4:1;hash(h,i==8?nodeId(records.value[k].header.next):le(b+i,n));}}
}
static u32 boundaryHash(void){u32 h=2166136261u;boundary(&h);return h;}
static Gfx*drawA(Gfx*,void*,s16);static Gfx*drawB(Gfx*,void*,s16);static Gfx*before(Gfx*,s32,s32,s16);static Gfx*after(Gfx*,s32,s16);
static u32 functionId(u32 p){if(p==(u32)drawA)return ENTRY;if(p==(u32)drawB)return ALT;if(p==(u32)before)return BEFORE;if(p==(u32)after)return AFTER;return p;}
static u32 stateHash(void){u32 h=2166136261u,i,k,n;boundary(&h);
 for(k=0;k<101;k++){u8*b=(u8*)&descriptors.value[k];for(i=0;i<52;i+=n){n=(i==8||i==16||i==20||i==32||i==36)?4:1;hash(&h,(i==8||i==20||i==32)?functionId(le(b+i,n)):le(b+i,n));}}
 for(i=0;i<64;i++){hash(&h,commands.value[i].words.w0);hash(&h,commands.value[i].words.w1);}return h;
}
static void observe(u32 id,u32*a,u32 n){u32 i;hash(&trace,id);for(i=0;i<n;i++)hash(&trace,a[i]);hash(&trace,boundaryHash());calls++;}
void func_15168F84(s32 selector,s32*first,s32*last){u32 a[]={(u32)selector,0xF001,0xF002};if((u32)selector!=SELECTOR||first==last||((u32)first&3)||((u32)last&3))error++;observe(0,a,3);*first=inChild?66:(s32)c->first;*last=inChild?67:(s32)c->last;}
static Gfx*stage(Gfx*out,s32 col,s32 row,s16 view,u32 post){u32 a[]={outId(out),(u32)col,post?(u32)(s32)view:(u32)row,(u32)(s32)view};u32 ef=post?c->afterEffect:c->beforeEffect;u32 index=outId(out)-0x50000;
 observe(post?4:1,a,post?3:4);if(index>=sizeof(commands.value)){error++;return commands.value;}out->words.w0=0xAA000000u|post;out->words.w1=(u32)col;
 if(!post){if(ef&1){u32 k=col==66?2:0;u32 count=c->shape==0?0:c->shape==1?(col==5?1:0):c->shape==2?1:2;heads.value[c->row*104+col]=count?&records.value[k+count-1].header:0;}if(ef&2)descriptors.value[col].draw=drawB;if(ef&8)cache.value.f04=0x11223344;}
 else{if(ef&2)globals.depth=3;if(ef&4)cache.value.f04=0x55667788;if(ef&8)descriptors.value[66].draw=drawB;}
 if((!post&&(ef&4))||(post&&(ef&1))){globals.viewport=1;globals.bases[1]=commands.value+1;globals.budget=post?1:3;}return out+1;
}
static Gfx*before(Gfx*out,s32 col,s32 row,s16 view){return stage(out,col,row,view,0);}
static Gfx*after(Gfx*out,s32 col,s16 view){return stage(out,col,0,view,1);}
static Gfx*draw(Gfx*out,void*node,s16 view,u32 id){u32 guest=nodeId(node),idx=(guest-0x30000)/0x100,col=idx>=2?66:5;u32 a[]={outId(out),guest,(u32)(s32)view};u32 ef=c->drawEffect;
 if(idx>=4||outId(out)-0x50000>=sizeof(commands.value)){error++;return commands.value;}observe(2+id,a,3);out->words.w0=0xAB000000u|id;out->words.w1=idx<<16|((u32)view&65535);
 if(c->clearNext||(ef&1))((ListNode*)node)->next=0;if(ef&2){globals.viewport=1;globals.bases[1]=commands.value+1;globals.budget=1;}
 if(ef&4){if(globals.depth<0||globals.depth>=6){error++;return commands.value;}globals.iter[2]=globals.iter[(s32)globals.depth];globals.depth=2;}if(ef&8)descriptors.value[col].draw=drawB;
 if(c->recursive&&!inChild){Gfx*answer;inChild=1;answer=subject(out+1,SELECTOR,view,1);inChild=0;return answer;}return out+1;
}
static Gfx*drawA(Gfx*out,void*node,s16 view){return draw(out,node,view,0);}static Gfx*drawB(Gfx*out,void*node,s16 view){return draw(out,node,view,1);}
static void setup(void){u32 i,k,j,count,col;u8*b;
 fill(records.before,16,0xD1);fill(records.after,16,0xD2);fill(descriptors.before,16,0xD3);fill(descriptors.after,16,0xD4);fill(heads.before,16,0xD5);fill(heads.after,16,0xD6);fill(cache.before,16,0xD7);fill(cache.after,16,0xD8);fill(commands.before,16,0xD9);fill(commands.after,16,0xDA);fill((u8*)&globals,sizeof(globals),0xA6);fill(globals.before,16,0xDB);fill(globals.after,16,0xDC);
 for(k=0;k<4;k++){b=(u8*)&records.value[k];for(i=0;i<76;i++)b[i]=nodeInitial[i];records.value[k].header.prev=(ListNode*)be(nodeInitial+4,4);records.value[k].header.next=nodePointer(be(nodeInitial+8,4));}
 for(k=0;k<101;k++){b=(u8*)&descriptors.value[k];for(i=0;i<52;i++)b[i]=descriptorInitial[k*52+i];descriptors.value[k].draw=(Gfx*(*)(Gfx*,void*,s16))be(descriptorInitial+k*52+8,4);descriptors.value[k].beforeList=(Gfx*)be(descriptorInitial+k*52+16,4);descriptors.value[k].before=(Gfx*(*)(Gfx*,s32,s32,s16))be(descriptorInitial+k*52+20,4);descriptors.value[k].after=(Gfx*(*)(Gfx*,s32,s16))be(descriptorInitial+k*52+32,4);descriptors.value[k].afterList=(Gfx*)be(descriptorInitial+k*52+36,4);}
 for(i=0;i<208;i++)heads.value[i]=0;fill((u8*)&cache.value,128,0xA5);globals.depth=(s8)c->initialDepth;for(i=0;i<6;i++)globals.iter[i]=(void*)(0xCC000000u+i);globals.bases[0]=globals.bases[1]=commands.value;globals.viewport=(u8)c->viewport;globals.budget=(s32)c->budget;globals.tag=0;globals.dirty=0;
 for(i=0;i<128;i++){u32 off=i*4,v=0;for(j=0;j<4;j++)v=v*256+(u8)((off+j)*13+7);if(i&1)commands.value[i/2].words.w1=v;else commands.value[i/2].words.w0=v;}
 for(k=0;k<2;k++){col=k?66:5;descriptors.value[col].draw=drawA;descriptors.value[col].beforeList=c->stages&1?(Gfx*)(0x80123400u+col*8):0;descriptors.value[col].before=c->stages&2?before:0;descriptors.value[col].afterList=c->stages&4?(Gfx*)(0x80123500u+col*8):0;descriptors.value[col].after=c->stages&8?after:0;descriptors.value[col].mode=(s8)c->mode;
  count=c->shape==0?0:c->shape==1?(k==0?1:0):c->shape==2?1:2;for(i=0;i<count;i++){Node*n=&records.value[k*2+i];n->header.next=i+1<count?&records.value[k*2+i+1].header:0;b=(u8*)n;putbe16(b+0x20,-32768+k*17+i);putbe16(b+0x22,19+k*23+i);}heads.value[c->row*104+col]=count?&records.value[k*2].header:0;
 }
 if(c->recursive)heads.value[104+66]=&records.value[2].header;
 trace=2166136261u;calls=error=inChild=0;
}
static u32 canaries(void){u32 i;for(i=0;i<16;i++)if(records.before[i]!=0xD1||records.after[i]!=0xD2||descriptors.before[i]!=0xD3||descriptors.after[i]!=0xD4||heads.before[i]!=0xD5||heads.after[i]!=0xD6||cache.before[i]!=0xD7||cache.after[i]!=0xD8||commands.before[i]!=0xD9||commands.after[i]!=0xDA||globals.before[i]!=0xDB||globals.after[i]!=0xDC)return 1;for(i=0;i<3;i++)if(globals.pad[i]!=0xA6)return 1;for(i=0;i<14;i++)if(globals.tail[i]!=0xA6)return 1;return 0;}
void __attribute__((force_align_arg_pointer)) _start(void){u32 n,k;int result=0;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){c=rows+n;setup();k=(outId(subject(commands.value,SELECTOR,(s16)c->view,(s32)c->row))-0x50000)/8;
  if(stateHash()!=c->stateHash||trace!=c->traceHash||calls!=c->calls||k!=c->returned||error||canaries()){u32 diagnostic[]={n,stateHash(),c->stateHash,trace,c->traceHash,calls,c->calls,k,c->returned,error,canaries()};__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(diagnostic),"d"(sizeof(diagnostic)));result=1;break;}}
 __asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 values={'ROWS':',\n'.join(encoded),'DESCRIPTORS':','.join(str(b)for b in data),'NODE':','.join(str(base[g.STATE+i])for i in range(76)),'CACHE_SIZES':''.join('case %d:return %d;'%(i,n)for i,n,t in FIELDS),'SELECTOR':hex(p.SELECTOR),'ENTRY':hex(g.ENTRY),'ALT':hex(ALT),'BEFORE':hex(p.BEFORE),'AFTER':hex(p.AFTER)}
 for a,b in values.items():support=support.replace(a,b)
 body=(o/'selected/body.c').read_text().replace('func_151674F8(','subject(')
 return pre+assertions+'\n'+body+'\n'+support,body,len(rows)
def main():
 text,body,count=program();profiles={}
 def run(text,label,opt):
  # These contracts never change descriptor.mode. Each rollback home is
  # therefore initialized on every native path which reads it; opaque
  # function-pointer calls prevent GCC's local warning analysis proving that.
  src=o/(label+'.c');exe=o/(label+opt);src.write_text(text);cmd=native_command(opt)+['-fstrict-aliasing','-Wno-unused-but-set-variable','-Wno-maybe-uninitialized','-Wl,--section-start=.matrix=0x80089470',str(src),'-o',str(exe)]
  q=subprocess.run(cmd,cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(label,q.stdout+q.stderr)
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 opts=('-O0',)if '--first'in sys.argv else('-O0','-O2','-O3')
 for opt in opts:
  q=run(text,'native',opt);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,list(struct.unpack('<%dI'%(len(q.stderr)//4),q.stderr))if len(q.stderr)%4==0 else q.stderr)
  profiles[opt]=dict(cases=count,SDK32=True,strict_aliasing=True,UBSan=True)
 effective=[]
 if '--first'not in sys.argv:
  for name,changed in controls((o/'selected/body.c').read_text()).items():
   q=run(text.replace(body,changed.replace('func_151674F8(','subject(')),'native-control-'+name,'-O2');assert q.returncode==1,('Ineffective/trap-only source control',name,q.returncode,q.stderr);effective.append(name)
 report=dict(profiles=profiles,effective_source_controls=effective,recursive_parent_cases=sum(c.recursive for c in cases()),two_complete_recursive_children_per_recursive_case=True,complete_retail_and_raw_parent_used_for_expected_values=True,all_descriptor_node_cache_and_row_offsets_asserted=True,full_nodes_descriptors_heads_iterators_cache_commands_and_ordered_calls=True,canaries=True,rollback_modes_stable_in_native_callback_contract=True,source_installed=packet.installed(),matching_credit=0,limits='Actual SDK32 body with bounded range/pre/post/draw providers and complete recursive parent calls; ordinary object/array domains, stable descriptor modes across callbacks, signed16 view, six iterator slots. No private stack alias/FCSR/hardware or gameplay claim.')
 (o/('native-first.json'if '--first'in sys.argv else'native.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
