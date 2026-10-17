"""Native32 typed bank and independent scripted provider ABI for the full scan."""
import itertools

from tools.experiments import game_sequence_event_scan as source
from tools.tests import game_sequence_event_scan_oracle as model

TYPES = '''#include <ultra64.h>
#include "structs.h"
typedef struct {u8 pad00[10];s16 maximum;u8 pad0C[6];s16 overrideValue;} RecordMaximum49D30;
'''+source.DECLARATIONS+'''
struct EventSlot {SequenceEvent49D30 event;u8 padding[8];};
typedef char EventSizeCheck[sizeof(SequenceEvent49D30)==8?1:-1];
typedef char EventIndexCheck[__builtin_offsetof(SequenceEvent49D30,colorIndex)==5?1:-1];
typedef char EventModeCheck[__builtin_offsetof(SequenceEvent49D30,mode)==6?1:-1];
typedef char EventSlotCheck[sizeof(struct EventSlot)==16?1:-1];
typedef char PointerWidthCheck[sizeof(void*)==4?1:-1];
struct Bank {u32 pre;u8 flag99,flag9C,flagA9,flagAA;s16 result;u8 counts[2];s32 outputs[2];
RecordMaximum49D30 *records[2][30];u8 colors[256][3],data[8][64];struct EventSlot events[8][6];u32 post;};
extern struct Bank bank;
void func_1501DAAC(s32);
'''
MACROS = '''#define D_800C3C99 bank.flag99
#define D_800C3C9C bank.flag9C
#define D_800C35A9 bank.flagA9
#define D_800C35AA bank.flagAA
#define D_800C3C8E bank.result
#define D_800C363A bank.counts
#define D_800C35B0 bank.outputs
#define D_800C3688 bank.records
#define D_80084110 (bank.colors+128)
'''
BODY_HEADER = TYPES+MACROS
FIELDS = [(at,field,1,False) for at,field in zip(model.FLAGS,('flag99','flag9C','flagAA','flagA9'))]
FIELDS += [(model.RESULT,'result',2,False)]
FIELDS += [(model.COUNTS+i,'counts[%d]'%i,1,False) for i in range(2)]
FIELDS += [(model.OUTPUT+i*4,'outputs[%d]'%i,4,False) for i in range(2)]
FIELDS += [(model.RECORDS+s*120+i*4,'records[%d][%d]'%(s,i),4,True) for s in range(2) for i in range(30)]
FIELDS += [(model.EVENTS+(i*6+j)*16+5,'events[%d][%d].event.colorIndex'%(i,j),1,False) for i in range(8) for j in range(6)]
FIELDS += [(model.EVENTS+(i*6+j)*16+6,'events[%d][%d].event.mode'%(i,j),2,False) for i in range(8) for j in range(6)]


def cases():
    for slot,count,present,pattern,mode in itertools.product((0,1),(0,1,3),(0,63),(0,3,8),(0,31)):
        yield model.fixture(slot,count,present,0,pattern,mode)
    for slot,pattern in itertools.product((0,1),range(len(model.VALUES))): yield model.fixture(slot,4,63,0,pattern)
    for index in (-128,-1,127): yield model.fixture(color_index=index)
    yield model.fixture(count=3,nulls=2)


def program():
    initial=[]; final=[]; scripts=[]; mutations=[]; rows=[]
    for memory,args,config in cases():
        reference=model.Reference(memory,args,config).run(); init=len(initial); start=len(scripts)
        initial.extend(model.read(memory,at,width) for at,_,width,_ in FIELDS)
        final.extend(model.read(reference.memory,at,width) for at,_,width,_ in FIELDS)
        for target,packet,event,value,writes in reference.script:
            at=len(mutations); mutations.extend('{0x%Xu,0x%Xu,%d}'%row for row in writes)
            scripts.append('{0x%Xu,{%s},0x%Xu,0x%Xu,%d,%d}'%(target,
                ','.join('0x%Xu'%v for v in (*packet,*([0]*(11-len(packet))))),event,value,at,len(writes)))
        rows.append('{%d,%d,%d,%d,%d}'%(args[0],config['pattern'],init,start,len(reference.script)))
    return TYPES+'''
struct Bank bank;static struct Bank wanted;
struct Field {u32 guest,offset,width,pointer;};
struct Write {u32 address,value,width;};
struct Script {u32 target,args[11],event,value,start,count;};
struct Case {u32 slot,pattern,init,start,count;};
'''+ 'static const struct Field fields[]={'+','.join('{0x%Xu,__builtin_offsetof(struct Bank,%s),%d,%d}'%(a,f,w,p) for a,f,w,p in FIELDS)+'};\n'+ \
        'static const u32 initial[]={'+','.join('0x%Xu'%v for v in initial)+'};\n'+ \
        'static const u32 final[]={'+','.join('0x%Xu'%v for v in final)+'};\n'+ \
        'static const struct Script scripts[]={'+','.join(scripts)+'};\n'+ \
        'static const struct Write mutations[]={'+','.join(mutations)+'};\n'+ \
        'static const struct Case cases[]={'+','.join(rows)+'};\n'+HARNESS


HARNESS = r'''
static const struct Case *current;static u32 next;
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 host(u32 p){
 if(p>=0x60000u&&p<0x60200u)return (u32)bank.data+p-0x60000u;
 if(p>=0x70000u&&p<0x70300u)return (u32)bank.events+p-0x70000u;
 return p;
}
static u32 guest(u32 p){
 if(p>=(u32)bank.data&&p<(u32)bank.data+sizeof(bank.data))return 0x60000u+p-(u32)bank.data;
 if(p>=(u32)bank.events&&p<(u32)bank.events+sizeof(bank.events))return 0x70000u+p-(u32)bank.events;
 return p;
}
static void field_store(struct Bank*b,u32 index,u32 value){
 const struct Field*f=&fields[index];u8*p=(u8*)b+f->offset;
 if(f->pointer)value=host(value);
 if(f->width==1)*p=(u8)value;else if(f->width==2)*(u16*)p=(u16)value;else *(u32*)p=value;
}
static void mutation(const struct Write*w){u32 i;
 for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++)if(fields[i].guest==w->address&&fields[i].width==w->width){field_store(&bank,i,w->value);return;}
 die(23);
}
static const struct Script*expect(u32 target,const u32*args,u32 count){
 const struct Script*s;u32 i;
 if(next>=current->start+current->count)die(21);s=&scripts[next++];if(s->target!=target)die(21);
 for(i=0;i<count;i++)if(args[i]!=s->args[i])die(21);
 for(i=0;i<s->count;i++)mutation(&mutations[s->start+i]);return s;
}
s32 func_15023BB0(u8*a,s32 b,s32 c,SequenceEvent49D30**d,s32 e,s32 f,s32 g,s32 h,s32 i,s32 j,s32 k){
 u32 args[11]={guest((u32)a),(u32)b,(u32)c,0,(u32)e,(u32)f,(u32)g,(u32)h,(u32)i,(u32)j,(u32)k};
 const struct Script*s;if(*d!=0)die(21);s=expect(0x15023BB0u,args,11);*d=(SequenceEvent49D30*)host(s->event);return (s32)s->value;
}
void func_1517EE40(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f){
 u32 args[6]={(u32)a,(u32)b,(u32)c,(u32)d,(u32)e,(u32)f};(void)expect(0x1517EE40u,args,6);
}
void _start(void){u32 n,i,j,width;const u8*a,*b;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];next=current->start;fill(&bank,sizeof(bank));
  for(i=0;i<256;i++)for(j=0;j<3;j++)bank.colors[i][j]=(u8)(((s32)i-128)*17+(s32)j*31+9);
  for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++)field_store(&bank,i,initial[current->init+i]);
  copy(&wanted,&bank,sizeof(bank));for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++)field_store(&wanted,i,final[current->init+i]);
  func_1501DAAC((s32)current->slot);if(next!=current->start+current->count)die(21);
  a=(const u8*)&bank;b=(const u8*)&wanted;width=sizeof(bank);for(i=0;i<width;i++)if(a[i]!=b[i])die(22);
 }
 die(0);
}
'''
