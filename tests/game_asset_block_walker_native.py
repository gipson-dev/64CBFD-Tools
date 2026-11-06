"""Native32 asset walker checks with exact buffer deltas and provider call traces."""
from dataclasses import replace
from tools.experiments import game_asset_block_walker_candidates as c
from tools.tests import game_asset_block_walker_oracle as g
from tools.tests.test_game_row_destination_fill import START

def cases():
    rows=[]
    for x in g.cases():
        if g.narrow(x.selector) not in (-1,0,1):continue
        if x.base!=g.BUFFER and not(x.base==0 and g.size(x)==0):continue
        rows.append(replace(x,selector=g.narrow(x.selector),phase=0,mutation=x.mutation&15))
    return list(dict.fromkeys(rows))

def program():
    rows=[];records=[];calls=[];deltas=[]
    for case in cases():
        initial=g.fixture(case);want,trace,_,_=g.reference(initial,case);record_first=len(records);at=0
        for step in case.steps:
            if at+16>0x2800:break
            records.append((at,8 if case.mutation&4 else step,step));at+=step
        call_first=len(calls)
        for target,args in trace:
            if target==g.CONSUME:
                off=args[0]-case.base;assert 0<=off<0x2800-7
                calls.append((off,args[1],args[2]))
        delta_first=len(deltas)
        for off in range(-16,0x2810):
            if want[case.base+off]!=initial[case.base+off]:deltas.append((off+16,want[case.base+off]))
        p=g.entry(case);start,end=g.read(want,p),g.read(want,p+4)
        n=len(calls)-call_first;zero=int(bool(case.stop_after and n>=case.stop_after))
        rows.append((case.selector,g.size(case),int(case.copy_limit is not None),case.copy_limit or 0,case.stop_after,
                     case.mutation,case.copy_error,int(case.base==0),record_first,len(records)-record_first,call_first,n,
                     delta_first,len(deltas)-delta_first,start,end,zero))
    headers=c.HEADERS.replace('extern AssetRange15015920 D_80082F80[];',
        'static AssetRange15015920 allRanges[131073];\n#define D_80082F80 (allRanges + 65536)')
    text='#include <ultra64.h>\n'+headers+'''
typedef char pointer_width[sizeof(void*)==4?1:-1];
typedef char range_size[sizeof(AssetRange15015920)==8?1:-1];
typedef struct {u32 off,original,step;} Record;
typedef struct {u32 off,index,selector;} Call;
typedef struct {u16 off;u8 value;} Delta;
typedef struct {s32 selector;u32 size,hasLimit,limit,stop,mutation,copyError,nullBase,recordFirst,recordCount,callFirst,callCount,deltaFirst,deltaCount,finalStart,finalEnd,zeroLimit;} Row;
static const Record records[]={
'''+',\n'.join('{%du,0x%08Xu,0x%08Xu}'%r for r in records)+'''};
static const Call expectedCalls[]={
'''+',\n'.join('{%du,%du,0x%08Xu}'%r for r in calls)+'''};
static const Delta deltas[]={
'''+',\n'.join('{%du,%du}'%r for r in deltas)+'''};
static const Row rows[]={
'''+',\n'.join('{%d,%s}'%(r[0],','.join('0x%08Xu'%int(v) for v in r[1:])) for r in rows)+'''};
static u8 storage[0x2820] __attribute__((aligned(16))),image[0x2800],expected[0x2820];
static u8 *base;
static const Row *active;
static u32 stage,ordinal;
__attribute__((noreturn))static void reject(void){__asm__ volatile("int $0x80"::"a"(1),"b"(1):"memory");__builtin_unreachable();}
static void putBE(u8*p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
s32 func_10003C6C(s32 bytes,s32 tag,s32 pool,s32 direction,s32 mode){
 AssetRange15015920 *p=D_80082F80+active->selector;
 if(stage++!=0||bytes!=0x2800||tag!=1||pool!=2||direction!=1||mode!=0)reject();
 if(active->mutation&1){p->start=(s32)((u32)p->start+0x4000u);p->end=(s32)((u32)p->start+active->size);}
 return (s32)(u32)base;
}
s32 func_10004514(s32 source,void*destination,u32 amount,s32 block){
 u32 i;AssetRange15015920*p=D_80082F80+active->selector;
 if(stage++!=1||source!=p->start||destination!=base||amount!=active->size||block!=1)reject();
 if(!active->copyError){if(amount>0x2800)reject();for(i=0;i<amount;i++)base[i]=image[i];}
 if(active->hasLimit){p->start=(s32)((u32)p->start+0x100u);p->end=(s32)((u32)p->start+active->limit);}
 return (s32)0xACE01234u;
}
s32 func_15015A38(u8*block,s32 index,s32 selector){
 const Call*call;AssetRange15015920*p=D_80082F80+active->selector;
 if(stage!=2||ordinal>=active->callCount)reject();call=expectedCalls+active->callFirst+ordinal;
 if(block!=base+call->off||(u32)index!=call->index||(u32)selector!=call->selector)reject();
 if(active->mutation&4){if((u32)index>=active->recordCount)reject();putBE(block+4,records[active->recordFirst+(u32)index].step);}
 ordinal++;if(active->stop&&ordinal>=active->stop)p->end=(s32)((u32)p->start-(u32)base);
 return (s32)0xFEDCBA98u;
}
void func_10004074(void*p){if(stage++!=2||p!=base||ordinal!=active->callCount)reject();}
'''
    names=['selected',*g.controls()]
    for name,value in dict(selected=c.SELECTED,**g.controls()).items():text+=value.replace(c.FUNCTION,name)+'\n'
    text+='''
typedef void(*Walker)(s16);
static Walker variants[]={'''+','.join(names)+'''};
__attribute__((noinline,noclone))static void invoke(Walker fn,s16 selector){fn(selector);}
static int check(Walker fn,u32 wrapped){
 u32 r,i,j;const Record*record;const Delta*delta;AssetRange15015920*p;
 for(r=0;r<sizeof(rows)/sizeof(rows[0]);r++){
  active=rows+r;base=active->nullBase?(u8*)0:storage+16;p=D_80082F80+active->selector;
  for(i=0;i<0x2820;i++){storage[i]=(u8)(((s32)i-16)*13+89);expected[i]=storage[i];}
  for(i=0;i<0x2800;i++)image[i]=(u8)(i*13+89);
  for(i=0;i<active->recordCount;i++){
   record=records+active->recordFirst+i;j=record->off;
   image[j]=8;image[j+1]=1;image[j+2]=(u8)(0xA0+i);image[j+3]=(u8)(0x70+i);putBE(image+j+4,record->original);
  }
  if(active->copyError)for(i=0;i<0x2800;i++)storage[16+i]=expected[16+i]=image[i];
  for(i=0;i<active->deltaCount;i++){delta=deltas+active->deltaFirst+i;expected[delta->off]=delta->value;}
  p->start=0x100000;p->end=(s32)(0x100000u+active->size);stage=ordinal=0;
  if(wrapped)invoke(fn,(s16)active->selector);else fn((s16)active->selector);
  if(stage!=3||ordinal!=active->callCount||(u32)p->start!=active->finalStart||(u32)p->end!=(active->zeroLimit?active->finalStart-(u32)base:active->finalEnd))return 1;
  for(i=0;i<0x2820;i++)if(storage[i]!=expected[i])return 1;
  p->start=p->end=0;
 }return 0;
}
#ifndef VARIANT_INDEX
#define VARIANT_INDEX 0
#endif
static int run(void){Walker f=variants[VARIANT_INDEX];if(check(f,0)||check(f,1))return 1;return 0;}
'''+START
    return text,len(rows),names
