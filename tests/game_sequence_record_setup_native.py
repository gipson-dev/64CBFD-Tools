"""SDK native32 setup body with canonical pointer/halfword lanes and arena canaries."""
import itertools
from tools.experiments import game_sequence_record_setup as source
from tools.experiments import game_record_maximum_scan as maximum
from tools.tests import game_sequence_record_setup_oracle as model
from tools.tests import game_sequence_state_reset_native as reset_native

# Guest address, C type, native dimensions, visible guest dimensions, width, pointer lane.
SPECS = {base:(reset_native.ctype(base,width),(8,) if indexed else (), (2,) if indexed else (),width,
    base==0x800C3D50) for base,width,indexed in reset_native.SPECS}
SPECS.update({
    0x800C35C4:('u8',(),(),1,False),0x800C35C5:('u8',(),(),1,False),0x800BE9F0:('s32',(),(),4,False),
    0x800C35A8:('s8',(),(),1,False),0x800C35E8:('u8',(8,),(2,),1,False),
    0x800C3C90:('u8',(),(),1,False),0x800C3C94:('s32',(),(),4,False),0x800C3C98:('u8',(),(),1,False),
    0x800C3C9A:('s16',(),(),2,False),0x800DBFF4:('u8',(),(),1,False),
    model.RESOURCE:('s32',(8,),(2,),4,True),model.ENABLED:('u16 *',(8,),(2,),4,True),
    model.FALLBACK:('u16 *',(8,),(2,),4,True),model.PREFERRED:('u16 *',(8,),(2,),4,True),
    model.AUXILIARY:('u8 **',(8,),(2,),4,True),model.RUNTIME:('SequenceRuntime49D30 *',(8,),(2,),4,True),
    0x800C35F0:('u8 *',(8,),(2,),4,True),0x800C3958:('u8 *',(8,),(2,),4,True),
    0x800C3960:('u8 *',(2,30),(2,30),4,True),0x800C3868:('u8 *',(2,30),(2,30),4,True),
    0x800C3778:('u8 *',(2,30),(2,30),4,True),0x800C3688:('RecordMaximum49D30 *',(2,30),(2,30),4,True),
})
KINDS=('enabled','fallback','preferred','auxiliary','runtime','items','scratch','records68','record16','output12')
FIRED=('live-request-status','cached-bundle-header','runtime-reload','wide-capacity','hook-count','late-count','live-loop-count','empty-after-helper')
FIELDS=[]
for base,(_,_,shape,width,pointer) in SPECS.items():
    for ordinal,indexes in enumerate(itertools.product(*(range(n) for n in shape)) if shape else [()]):
        FIELDS.append((base+ordinal*width,'f_%08X'%base+''.join('[%d]'%i for i in indexes),width,pointer))
for base,name in ((model.HEADER,'header'),(model.ALT_HEADER,'otherHeader')):
    for i,field in enumerate(('activeCount','fallbackCount','preferredCount','auxiliaryCount')):FIELDS.append((base+i*2,name+'.'+field,2,False))
for base,name in ((model.BUNDLE,'bundle'),(model.ALT_BUNDLE,'otherBundle')):
    for i in range(64):FIELDS.extend(((base+i*8,name+'[%d].data'%i,4,True),(base+i*8+4,name+'[%d].bytes'%i,4,False)))
for i in range(4):
    for offset,field in ((4,'items'),(56,'scratch')):FIELDS.append((model.ALT_RUNTIME+i*64+offset,'otherRuntime[%d].'%i+field,4,True))
for i in range(168):FIELDS.append((model.reset.TABLE+i,'actors[%d]'%i,1,False))
TYPES=maximum.DECLARATIONS.split('extern s32')[0]+source.DECLARATIONS.split('extern u8')[0]
HEADER='#include <ultra64.h>\n#include "structs.h"\n'+TYPES+'\nstruct Bank{u32 pre;\n'
HEADER+='\n'.join('%s f_%08X%s;'%(ctype,base,''.join('[%d]'%n for n in shape)) for base,(ctype,shape,_,_,_) in SPECS.items())
HEADER+='''
SequenceHeader49D30 header,otherHeader;SequenceDescriptor49D30 bundle[64],otherBundle[64];
SequenceRuntime49D30 otherRuntime[4];u8 actors[168],payload[0x4000];
void(*hooks[4])(s32,s32,s32,s32);u32 post;};extern struct Bank bank;
extern u8 arena[0x400000];
void actual_reset(s32);void func_150233BC(void);void func_1501D044(s32);s32 func_1501D1D4(s32,s32,s32);
s32 func_1501CFF8(s32);void func_1501CDC0(s32);void func_1501CE54(s32);
void func_1501D348(s32,s32,s32,s32,s32);
'''+source.DECLARATIONS[source.DECLARATIONS.index('s32 allocate_memory'):]
BODY_HEADER=HEADER+'\n'.join('#define D_%08X bank.f_%08X'%(base,base) for base in SPECS)+'\n#define D_800840FC bank.hooks\n'


def cases():
    for slot,counts,mode,hook in itertools.product((0,1),((0,0,0,0),(1,0,0,0),(2,3,1,2),(3,1,3,1)),(0,63),(0,1)):
        yield model.fixture(slot,counts=counts,mode=mode,hook=hook)
    for slot,pattern in itertools.product((0,1),(1,2,3)):
        yield model.fixture(slot,counts=(1,1,1,1),pattern=pattern,total=0x1234FFFF)
    for slot,state,gate,scene in itertools.product((0,1),(1,2),(0,1),(37,99)):
        yield model.fixture(slot,state,gate,scene,mode=1)
    for slot in (0,1):
        yield model.fixture(slot,fail=1);yield model.fixture(slot,scene=99,sequence=0x7FFFFFFF,mode=1)
        yield model.fixture(slot,counts=(0,65535,65535,0),mode=64,hook=0)


def runs(values):
    for value,group in itertools.groupby(values):yield len(list(group)),value


def program():
    rows=[];events=[];plans=[];heap=[];initial=[];final=[]
    for memory,args,config in cases():
        ref=model.Reference(memory,args,config).run();start=len(events);allocation=len(plans);run_start=len(heap);init=len(initial)
        initial.extend(model.read(memory,at,width) for at,_,width,_ in FIELDS)
        final.extend(model.read(ref.memory,at,width) for at,_,width,_ in FIELDS)
        for (target,packet),result,snapshot in zip(ref.calls,ref.results,ref.snapshots):
            events.append('{0x%Xu,{%s},0x%Xu,{%s}}'%(target,','.join('0x%Xu'%n for n in (*packet,*([0]*(5-len(packet))))),result,','.join('0x%Xu'%n for n in snapshot)))
        plans.extend('{0x%Xu,%d,%d}'%(p,n,KINDS.index(kind)) for p,n,kind in ref.allocations)
        length=ref.used+16 if ref.allocations else 0
        heap.extend('{%d,%d}'%(count,value) for count,value in runs(ref.memory.get(model.HEAP+i,0xA5) for i in range(length)))
        rows.append('{ {%s},%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d }'%(','.join('0x%Xu'%n for n in args),config['mode'],config['fail'],
            start,len(ref.calls),allocation,len(ref.allocations),run_start,len(heap)-run_start,length,init,
            sum(1<<i for i,name in enumerate(FIRED) if name in ref.fired)))
    text=HEADER+'''
struct Bank bank;static struct Bank wanted;u8 arena[0x400000] __attribute__((aligned(16)));
struct Field{u32 guest,offset,width,pointer;};struct Event{u32 target,args[5],result,snapshot[31];};
struct Plan{u32 start,size,kind;};struct Run{u32 size,value;};
struct Case{u32 args[5],mode,fail,event,count,plan,allocations,run,runs,length,init,fired;};
'''
    text+='static const struct Field fields[]={'+','.join('{0x%Xu,__builtin_offsetof(struct Bank,%s),%d,%d}'%(at,field,width,pointer) for at,field,width,pointer in FIELDS)+'};\n'
    text+='static const struct Event events[]={'+','.join(events)+'};\nstatic const struct Plan plans[]={'+','.join(plans)+'};\n'
    text+='static const struct Run runs[]={'+','.join(heap)+'};\nstatic const struct Case cases[]={'+',\n'.join(rows)+'};\n'
    text+='static const u32 initial[]={'+','.join('0x%Xu'%n for n in initial)+'};\nstatic const u32 final[]={'+','.join('0x%Xu'%n for n in final)+'};\n'
    text+='static const u32 snapshotAddresses[][2]={'+','.join('{0x%Xu,%d}'%row for row in model.SNAPSHOT_LANES)+'};\n'
    return text+HARNESS


HARNESS=r'''
static const struct Case*c;static u32 eventIndex,allocationIndex,fired;
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 host(u32 p){
 if(p>=0x100000u&&p<0x500000u)return (u32)arena+p-0x100000u;
 if(p>=0x60000u&&p<0x60008u)return (u32)&bank.header+p-0x60000u;
 if(p>=0x62000u&&p<0x62008u)return (u32)&bank.otherHeader+p-0x62000u;
 if(p>=0x61000u&&p<0x61200u)return (u32)bank.bundle+p-0x61000u;
 if(p>=0x63000u&&p<0x63200u)return (u32)bank.otherBundle+p-0x63000u;
 if(p>=0x64000u&&p<0x64100u)return (u32)bank.otherRuntime+p-0x64000u;
 if(p>=0x70000u&&p<0x74000u)return (u32)bank.payload+p-0x70000u;return p;
}
static u32 guest(u32 p){
 if(p>=(u32)arena&&p<(u32)arena+sizeof(arena))return 0x100000u+p-(u32)arena;
 if(p>=(u32)&bank.header&&p<(u32)&bank.header+8)return 0x60000u+p-(u32)&bank.header;
 if(p>=(u32)&bank.otherHeader&&p<(u32)&bank.otherHeader+8)return 0x62000u+p-(u32)&bank.otherHeader;
 if(p>=(u32)bank.bundle&&p<(u32)bank.bundle+512)return 0x61000u+p-(u32)bank.bundle;
 if(p>=(u32)bank.otherBundle&&p<(u32)bank.otherBundle+512)return 0x63000u+p-(u32)bank.otherBundle;
 if(p>=(u32)bank.otherRuntime&&p<(u32)bank.otherRuntime+256)return 0x64000u+p-(u32)bank.otherRuntime;
 if(p>=(u32)bank.payload&&p<(u32)bank.payload+0x4000)return 0x70000u+p-(u32)bank.payload;return p;
}
static u32 load(const void*p,u32 n){return n==1?*(const u8*)p:n==2?*(const u16*)p:*(const u32*)p;}
static void store(void*p,u32 n,u32 v){if(n==1)*(u8*)p=(u8)v;else if(n==2)*(u16*)p=(u16)v;else *(u32*)p=v;}
static u32 visible(u32 at,u32 n){u32 i,v;for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++)if(fields[i].guest==at){
 if(fields[i].width!=n)die(29);v=load((u8*)&bank+fields[i].offset,n);return fields[i].pointer?guest(v):v;}die(29);}
static const struct Event*enter(u32 target,u32 a,u32 b,u32 d,u32 e,u32 f){const struct Event*v;
 if(eventIndex>=c->count)die(22);v=&events[c->event+eventIndex++];
 if(v->target!=target||v->args[0]!=a||v->args[1]!=b||v->args[2]!=d||v->args[3]!=e||v->args[4]!=f)die(22);return v;}
static void finish(const struct Event*v){u32 i;for(i=0;i<31;i++)if(visible(snapshotAddresses[i][0],snapshotAddresses[i][1])!=v->snapshot[i])die(22);}
s32 allocate_memory(s32 size,s32 tag,s32 pool,s32 flags){const struct Event*v=enter(0x10003C40u,(u32)size,(u32)tag,(u32)pool,(u32)flags,0);const struct Plan*p;
 if(allocationIndex>=c->allocations)die(22);p=&plans[c->plan+allocationIndex];
 if(p->size!=(u32)size||p->start!=v->result)die(22);
 if(allocationIndex==0&&(c->mode&2u)){bank.f_800C3668[c->args[2]]=(s32)bank.otherBundle;bank.bundle[0].data=(u8*)&bank.otherHeader;fired|=2;}
 if((p->kind==5||p->kind==6)&&(c->mode&4u)){bank.f_800C3A50[c->args[2]]=bank.otherRuntime;fired|=4;}
 if((c->mode&64u)&&(p->kind==1||p->kind==2)){if(p->kind==1)bank.header.fallbackCount=0;else bank.header.preferredCount=0;fired|=8;}
 allocationIndex++;finish(v);return (s32)host(v->result);}
void bzero(void*destination,int size){u32 i,a=guest((u32)destination);const struct Event*v=enter(0x100226F0u,a,(u32)size,0,0,0);
 if(a<0x100000u||size<0||(u32)size>0x20000u)die(22);for(i=0;i<(u32)size;i++)((u8*)destination)[i]=0;finish(v);}
void func_150233BC(void){u32 i;for(i=0;i<168;i++)bank.actors[i]=0;}
void func_1501D044(s32 slot){const struct Event*v=enter(0x1501D044u,(u32)slot,0,0,0,0);actual_reset(slot);finish(v);}
s32 func_1501D1D4(s32 a,s32 b,s32 slot){const struct Event*v=enter(0x1501D1D4u,(u32)a,(u32)b,(u32)slot,0,0);
 bank.f_800C3668[slot]=(s32)host(v->result);finish(v);return (s32)host(v->result);}
void func_1501C730(s32 a,s32 b,s32 d,s32 e,s32 f){const struct Event*v=enter(0x1501C730u,(u32)a,(u32)b,(u32)d,(u32)e,(u32)f);
 if(c->mode&1u){u32 slot=c->args[2];bank.f_800C35EA[slot]=bank.f_800C35EA[slot]?0:2;fired|=1;}finish(v);}
static void hook(u32 number,s32 a,s32 b,s32 d,s32 e){const struct Event*v=enter(0x151FF000u+number*4u,(u32)a,(u32)b,(u32)d,(u32)e,0);
 if(c->mode&8u){bank.f_800C363A[c->args[2]]=0;fired|=16;}finish(v);}
static void hook0(s32 a,s32 b,s32 d,s32 e){hook(0,a,b,d,e);}static void hook1(s32 a,s32 b,s32 d,s32 e){hook(1,a,b,d,e);}
static void hook2(s32 a,s32 b,s32 d,s32 e){hook(2,a,b,d,e);}static void hook3(s32 a,s32 b,s32 d,s32 e){hook(3,a,b,d,e);}
s32 func_1501CFF8(s32 slot){const struct Event*v=enter(0x1501CFF8u,(u32)slot,0,0,0,0);finish(v);return (s32)v->result;}
void func_1501CDC0(s32 slot){const struct Event*v=enter(0x1501CDC0u,(u32)slot,0,0,0,0);finish(v);}
void func_1501CE54(s32 slot){const struct Event*v=enter(0x1501CE54u,(u32)slot,0,0,0,0);finish(v);}
s32 func_15022BA4(s32 slot){const struct Event*v=enter(0x15022BA4u,(u32)slot,0,0,0,0);if(c->mode&8u){bank.f_800C363A[slot]=2;fired|=32;}finish(v);return 0;}
s32 func_15020388(s32 i,s32 slot){const struct Event*v=enter(0x15020388u,(u32)i,(u32)slot,0,0,0);if(i==0&&(c->mode&16u)){bank.f_800C363A[slot]=1;fired|=64;}finish(v);return 0;}
s32 func_150238D0(void){const struct Event*v=enter(0x150238D0u,0,0,0,0,0);finish(v);return 0;}
void func_15022234(s32 slot){const struct Event*v=enter(0x15022234u,(u32)slot,0,0,0,0);finish(v);}
void func_15022248(s32 slot){const struct Event*v=enter(0x15022248u,(u32)slot,0,0,0,0);if(c->mode&32u){bank.f_800C363A[slot]=0;fired|=128;}finish(v);}
'''+ '\n'.join('%s %s(%s){const struct Event*v=enter(0x%Xu,%s);finish(v);%s}'%('void' if name=='func_15022754' else 's32',name,
    ','.join('s32 '+chr(97+i) for i in range(arity)),target,','.join(['(u32)'+chr(97+i) for i in range(arity)]+['0']*(5-arity)),
    '' if name=='func_15022754' else 'return 0;')
    for name,target,arity in [('func_1501E81C',0x1501E81C,2),('func_150242F8',0x150242F8,2),('func_1501EC38',0x1501EC38,1),
    ('func_15022848',0x15022848,1),('func_15022754',0x15022754,1),('func_15022528',0x15022528,1),('func_15020EC4',0x15020EC4,1),('func_1501DAAC',0x1501DAAC,1)])+r'''
static u32 heapByte(u32 offset){u32 i,start,relative,width=1,pointer=0,at=offset,value;const struct Plan*p;
 for(i=0;i<c->allocations;i++){p=&plans[c->plan+i];start=p->start-0x100000u;if(offset<start||offset>=start+p->size)continue;
  relative=offset-start;if(p->kind<=2){width=2;at=start+(relative&~1u);}
  else if(p->kind==3){width=4;pointer=1;at=start+(relative&~3u);}
  else if(p->kind==4&&((relative%64u>=4&&relative%64u<8)||(relative%64u>=56&&relative%64u<60))){width=4;pointer=1;at=offset-(relative&3u);}break;}
 value=load(arena+at,width);if(pointer)value=guest(value);return (value>>(8u*(width-1u-(offset-at))))&255u;
}
void _start(void){u32 n,i,j,v,position;const struct Field*f;const struct Run*r;
 if(sizeof(void*)!=4||sizeof(SequenceHeader49D30)!=8||sizeof(SequenceDescriptor49D30)!=8||sizeof(SequenceRuntime49D30)!=64||
  __builtin_offsetof(SequenceRuntime49D30,items)!=4||__builtin_offsetof(SequenceRuntime49D30,scratch)!=56)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];fill(&bank,sizeof(bank));fill(arena,sizeof(arena));
  for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){f=&fields[i];v=initial[c->init+i];if(f->pointer)v=host(v);store((u8*)&bank+f->offset,f->width,v);}
  bank.hooks[0]=hook0;bank.hooks[1]=hook1;bank.hooks[2]=hook2;bank.hooks[3]=hook3;copy(&wanted,&bank,sizeof(bank));
  for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){f=&fields[i];v=final[c->init+i];if(f->pointer)v=host(v);store((u8*)&wanted+f->offset,f->width,v);}
  eventIndex=allocationIndex=fired=0;func_1501D348((s32)c->args[0],(s32)c->args[1],(s32)c->args[2],(s32)c->args[3],(s32)c->args[4]);
  if(eventIndex!=c->count||allocationIndex!=c->allocations||fired!=c->fired)die(22);
  for(i=0;i<sizeof(bank);i++)if(((u8*)&bank)[i]!=((u8*)&wanted)[i])die(21);
  position=0;for(i=0;i<c->runs;i++){r=&runs[c->run+i];for(j=0;j<r->size;j++)if(heapByte(position++)!=r->value)die(21);}
  if(position!=c->length)die(29);
 }
 die(0);
}
'''


def controls(body):
    stale=body.replace('    void *allocated;', '    void *allocated;\n    SequenceRuntime49D30 *cachedRuntime;').replace(
        '            if (entries != 0) {','            if (entries != 0) {\n                cachedRuntime = *runtime;').replace('(*runtime)[i].','cachedRuntime[i].')
    return dict(half_descriptor_size=body.replace('descriptor->bytes >> 3','(u16)descriptor->bytes >> 3'),
        missing_descriptor_group=body.replace('    cursor += header->activeCount;',''),
        wrong_capacity=body.replace('bytes = capacity * 2','bytes = capacity * 4'),stale_runtime=stale,
        wrong_process_index=body.replace('func_15020388(i, slot); i++;','i++; func_15020388(i, slot);'),
        signed_total=body.replace('u16 total;','s16 total;'),stale_request_status=body.replace('if (*status != 0)','if (state != 0)'),
        wrong_callback_parameter=body.replace('D_800840FC[hook](scene, sequence, slot, parameter)','D_800840FC[hook](scene, sequence, slot, 0)'))
