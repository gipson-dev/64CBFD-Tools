"""Native32 shared node types, actual append C and guest-derived scalar rows."""
from dataclasses import replace
from tools.experiments import game_keyed_buffer_registration_candidates as c
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_keyed_buffer_registration_oracle as g
from tools.tests.test_game_row_destination_fill import START

def cases():return list(dict.fromkeys(replace(x,phase=0,mutation=x.mutation&7)for x in g.cases()))

def program(root):
    rows=[];pointers={0:0,**{g.NODES+32*i:i+1 for i in range(4)},g.OTHER:5,g.NEW:6}
    for case in cases():
        initial=g.fixture(case);want,calls=g.reference(initial,case);nodes=[]
        for i,p in enumerate((*[g.NODES+32*j for j in range(4)],g.OTHER,g.NEW)):
            next_value=g.read(want,p+12);next_id=pointers.get(next_value,-1)
            if next_id<0:assert i==5
            # Unknown next and buffer words stay byte-identical and are never
            # dereferenced by the native fixture before the helper replaces them.
            if next_id<0:assert bytes(want[p+12+j]for j in range(4))==bytes(initial[p+12+j]for j in range(4))
            has_buffer=int(g.read(want,p+8)==g.buffer(case))
            if not has_buffer:assert bytes(want[p+8+j]for j in range(4))==bytes(initial[p+8+j]for j in range(4))
            nodes.append('{{%s},%d,0x%08Xu,%d,%d}'%(','.join(str(want[p+j])for j in range(6)),g.signed16(g.read(want,p+6,2)),g.read(want,p+16),next_id,has_buffer))
        values=bytes(want[g.buffer(case)+i]for i in range(384));original=bytes(initial[g.buffer(case)+i]for i in range(384))
        buffer_kind=0 if values==bytes(384)else 1 if values==bytes([0xD3])*384 else 2
        if buffer_kind==2:assert values==original
        counts=[sum(t==g.SYMS[n]for t,a in calls)for n in('allocate_memory','func_10004074','bzero','func_15188A58')]
        rows.append('{%d,%d,%d,%d,0x%08Xu,%d,%d,%d,0x%08Xu,%d,%d,{%s},{%s}}'%(
            case.count,case.match,case.old,case.timer,case.mode,case.outcome,case.mutation,case.residue,case.key,pointers[g.read(want,g.HEAD)],buffer_kind,','.join(map(str,counts)),','.join(nodes)))
    helper=body((root/c.SOURCE).read_text(encoding='utf-8'),'func_15188A58').replace('func_15188A58','append_impl',1)
    text='#include <ultra64.h>\n'+c.HEADERS+'''
typedef char pointer_width[sizeof(void*)==4?1:-1];
typedef char node_size[sizeof(ListNode15188A58)==20?1:-1];
typedef char timer_offset[__builtin_offsetof(ListNode15188A58,timer)==6?1:-1];
typedef char buffer_offset[__builtin_offsetof(ListNode15188A58,buffer)==8?1:-1];
typedef char next_offset[__builtin_offsetof(ListNode15188A58,next)==12?1:-1];
typedef char key_offset[__builtin_offsetof(ListNode15188A58,key)==16?1:-1];
static ListNode15188A58 nodes[4],other,fresh;
ListNode15188A58 *D_800DF7CC;
static u8 storage[448],saved[6][20];
static u32 calls[4],bad,outcome,mutation,residue;
static u8 *buffer;
static void effects(u32 stage){u32 i;
 if(stage==0&&(mutation&1)){other.next=D_800DF7CC;D_800DF7CC=&other;}
 if(stage==1&&(mutation&2)){fresh.retained05=0xED;for(i=0;i<384;i++)buffer[i]=0xD3;}
 if(stage==2&&(mutation&4)){fresh.mode=0xAB;fresh.timer=(s16)0x8123;}
}
s32 allocate_memory(s32 size,s32 tag,s32 pool,s32 flags){
 u32 stage=calls[0]++;if(size!=(stage?384:20)||tag!=1||pool!=(stage?1:0)||flags!=0||stage>1)bad=1;
 effects(stage);return stage?(outcome==2?(s32)(u32)buffer:0):(outcome?(s32)(u32)&fresh:0);
}
void func_10004074(void*p){calls[1]++;if(p!=&fresh)bad=1;}
void bzero(void*p,int n){u32 i;calls[2]++;if(p!=buffer||n!=384)bad=1;for(i=0;i<(u32)n;i++)((u8*)p)[i]=0;effects(2);}
'''+helper+'''
void func_15188A58(ListNode15188A58*p,ListNode15188A58*head){
 calls[3]++;if(p!=&fresh||head!=(ListNode15188A58*)&D_800DF7CC)bad=1;append_impl(p,head);
}
'''
    for name,value in dict(selected=c.SELECTED,**g.controls()).items():text+=value.replace(c.FUNCTION,name)+'\n'
    text+='''
typedef struct {u8 bytes[6];s16 timer;u32 key;s32 next;u32 buffer;} Expected;
typedef struct {s32 count,match,old,timer;u32 mode,outcome,mutation,residue,key,head,bufferKind,calls[4];Expected nodes[6];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
static ListNode15188A58 *pointer(s32 n){return n==0?(ListNode15188A58*)0:n<=4?nodes+n-1:n==5?&other:&fresh;}
typedef void(*Update)(s32,s32,s32);
__attribute__((noinline,noclone))static void invoke(Update fn,s32 key,s32 timer,s32 mode){fn(key,timer,mode);}
static int variant(Update fn,u32 wrapped){
 u32 i,j,k,r;ListNode15188A58 *p;const Row*row;
 for(r=0;r<sizeof(rows)/sizeof(rows[0]);r++){
  row=rows+r;outcome=row->outcome;mutation=row->mutation;residue=row->residue;buffer=storage+16+residue;
  for(i=0;i<448;i++)storage[i]=(u8)(i*7+0xA7);
  for(i=0;i<432;i++)storage[residue+i]=(u8)(i*13+89);
  for(i=0;i<6;i++){
   p=i<4?nodes+i:i==4?&other:&fresh;
   for(j=0;j<20;j++)((u8*)p)[j]=(u8)(((i<4?32*i:0)+j)*13+89);
   p->timer=i<4?(s16)row->old:(s16)0xA7B4;
   p->key=i<4?(s32)((row->match==(s32)i||(row->match==4&&(i==0||i==2)))?row->key:(row->key^0x1010000u)+i):i==4?(s32)(row->key^0x55550000u):(s32)0x29364350;
   if(i<4)p->next=i+1<(u32)row->count?nodes+i+1:(ListNode15188A58*)0;
   else if(i==4)p->next=(ListNode15188A58*)0;
   for(j=0;j<20;j++)saved[i][j]=((u8*)p)[j];
  }
  D_800DF7CC=row->count?nodes:(ListNode15188A58*)0;
  bad=0;for(i=0;i<4;i++)calls[i]=0;
  if(wrapped)invoke(fn,(s32)row->key,row->timer,(s32)row->mode);else fn((s32)row->key,row->timer,(s32)row->mode);
  if(bad||D_800DF7CC!=pointer((s32)row->head))return 1;
  for(i=0;i<4;i++)if(calls[i]!=row->calls[i])return 1;
  for(i=0;i<6;i++){
   p=i<4?nodes+i:i==4?&other:&fresh;
   for(j=0;j<6;j++)if(((u8*)p)[j]!=row->nodes[i].bytes[j])return 1;
   if(p->timer!=row->nodes[i].timer||(u32)p->key!=row->nodes[i].key)return 1;
   if(row->nodes[i].buffer){if(p->buffer!=buffer)return 1;}else for(j=8;j<12;j++)if(((u8*)p)[j]!=saved[i][j])return 1;
   if(row->nodes[i].next>=0){if(p->next!=pointer(row->nodes[i].next))return 1;}else for(j=12;j<16;j++)if(((u8*)p)[j]!=saved[i][j])return 1;
  }
  for(i=0;i<448;i++){
   k=(i*7+0xA7)&255;
   if(i>=residue&&i<residue+432){j=i-residue;k=(j*13+89)&255;
    if(j>=16&&j<400&&row->bufferKind<2)k=row->bufferKind?0xD3:0;
   }
   if(storage[i]!=k)return 1;
  }
 }return 0;
}
static int run(void){if(variant(selected,0)||variant(selected,1))return 1;
'''
    for i,name in enumerate(g.controls()):text+=' if(variant(%s,0)!=1)return %d;\n'%(name,i+2)
    return text+'return 0;}\n'+START,len(rows)
