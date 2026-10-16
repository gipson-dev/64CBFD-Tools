"""Native32 SDK task layout and explicit pointer/endian lanes for submission."""
import itertools

from tools.experiments import game_graphics_task_submit as source
from tools.tests import game_graphics_task_submit_oracle as model

WORDS = sum(size // 4 for _, size in model.REGIONS)
HEADER = '''#include <ultra64.h>
#include <PR/sched.h>
typedef union {u64 align;u32 words[1024];u8 bytes[4096];} Globals;
typedef union {u64 align;u32 words[128];OSScTask task;} TaskBank;
extern Globals globals;extern Gfx commands[4608];extern TaskBank other,third;
extern u32 systemWords[8],framebuffers[256];extern s32 viewCount;
struct Event{u32 target,count,args[3];};extern struct Event events[4];
extern u32 eventCount,mode,fired,error;
u32 abstractPointer(u32);
#define D_800BE9C0 globals.bytes[0x3C0]
#define D_800BE617 globals.bytes[0x17]
#define D_800BEBA0 globals.bytes[0x5A0]
#define D_800BEAA8 (*(s16 *)(globals.bytes+0x4A8))
#define D_80082FA0 viewCount
#define D_800BE9C8 ((Gfx **)(globals.bytes+0x3C8))
#define D_800BE9D0 (*(Gfx **)(globals.bytes+0x3D0))
#define D_800BE9D8 ((Gfx **)(globals.bytes+0x3D8))
#define D_800BEAD4 (*(OSScTask **)(globals.bytes+0x4D4))
#define D_800BEAD8 ((OSScTask *)(globals.bytes+0x4D8))
#define D_800BEAD0 (*(u64 **)(globals.bytes+0x4D0))
#define D_800BEB9C (*(u64 **)(globals.bytes+0x59C))
#define D_80038090 (*(u64 **)(systemWords+4))
#define D_80038094 (*(u64 **)(systemWords+5))
#define D_8002AAE8 ((void **)framebuffers)
#define D_800BEA10 (*(OSMesgQueue *)(globals.bytes+0x410))
#define D_800BEA68 ((OSScMsg *)(globals.bytes+0x468))
#define D_100290D0 ((u64 *)0x100290D0u)
#define D_100291A0 ((u64 *)0x100291A0u)
#define D_800C1060 ((u64 *)0x800C1060u)
#define D_800BEBB0 ((u64 *)0x800BEBB0u)
#define D_800CBE10 ((u64 *)0x800CBE10u)
#define D_8003A5E8 ((u64 *)0x8003A5E8u)
#define D_8003B1E8 (*(OSMesgQueue *)0x8003B1E8u)
void func_1501A39C(void);s32 func_1501CC3C(void);
'''


def cases():
    for memory, args in model.corpus(): yield memory, args, 0
    for page, swap, mode in itertools.product((0, 1), (0, 1, 0x10000), range(1, 7)):
        memory, args = model.fixture(used=1001 if mode in (1, 6) else 20, page=page, swap=swap)
        yield memory, args, mode


def program():
    rows, changes, events = [], [], []
    for memory, args, mode in cases():
        expected, calls, fired = model.reference(memory, args, mode)
        delta, i = [], 0
        for base, size in model.REGIONS:
            for p in range(0, size, 4):
                a, b = model.read(memory, base + p), model.read(expected, base + p)
                if a != b: delta.append((i, b))
                i += 1
        assert i == WORDS
        capacity = model.signed((model.read(memory, model.ROWS + 4) - model.read(memory, model.ROWS)) & 0xFFFFFFFF) >> 3
        first = model.read(memory, model.ROWS + memory[model.PAGE] * 4)
        used = model.signed((model.read(memory, model.CURSOR) - first) & 0xFFFFFFFF) >> 3
        remainder = (model.read(memory, model.CURSOR) - first) & 7
        values = (capacity, used, memory[model.PAGE], memory[model.PROGRAM], args[1], memory[model.DIRTY],
            model.read(memory, model.VIEW_COUNT), model.read(memory, model.COUNTER, 2), remainder, mode, len(fired),
            len(changes), len(delta), len(events), len(calls))
        rows.append('{%s}' % ','.join('0x%Xu' % (v & 0xFFFFFFFF) for v in values)); changes.extend(delta)
        events.extend((target, len(packet), (*packet, *([0] * (3 - len(packet))))) for target, packet in calls)
    text = HEADER + '''
void func_1501C880(s32,s32);
Globals globals;Gfx commands[4608];TaskBank other,third;
u32 systemWords[8],framebuffers[256];s32 viewCount;
struct Event events[4];u32 eventCount,mode,fired,error;
struct Patch{u32 index,value;};static const struct Patch changes[]={'''
    text += ','.join('{%d,0x%Xu}' % row for row in changes) + '};\n'
    text += 'static const struct Event wantedEvents[]={' + ','.join('{0x%Xu,%d,{%s}}' %
        (target, count, ','.join('0x%Xu' % v for v in packet)) for target, count, packet in events) + '};\n'
    text += 'static const u32 cases[][15]={' + ',\n'.join(rows) + '};\n'
    text += '''
static u32 initial[10761];
static void die(u32 c){__asm__ volatile("int $0x80"::"a"(1),"b"(c):"memory");__builtin_unreachable();}
static void mismatch(u32 n,u32 i,u32 actual,u32 wanted){u32 a[4]={n,i,actual,wanted},j,k;char s[36];
 for(j=0;j<4;j++){for(k=0;k<8;k++)s[j*9+k]="0123456789ABCDEF"[(a[j]>>(28-k*4))&15];s[j*9+8]=(char)(j==3?10:32);}
 __asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(s),"d"(36):"memory");die(21);}
static u32*data[]={globals.words,(u32*)commands,other.words,third.words,systemWords,framebuffers,(u32*)&viewCount};
static const u32 bases[]={0x800BE600u,0x20000u,0x60000u,0x61000u,0x80038080u,0x8002AAE8u,0x80082FA0u};
static const u32 sizes[]={1024,9216,128,128,8,256,1};
u32 abstractPointer(u32 p){u32 i;for(i=0;i<7;i++)if(p>=(u32)data[i]&&p<(u32)data[i]+sizes[i]*4)return bases[i]+p-(u32)data[i];return p;}
static u32 pointerField(u32 a){u32 base,p;const u32 taskBases[]={0x800BEAD8u,0x800BEB38u,0x60000u,0x61000u};
 if(a==0x800BE9C8u||a==0x800BE9CCu||a==0x800BE9D0u||a==0x800BE9D8u||a==0x800BE9DCu||
    a==0x800BEAD4u||a==0x800BEAD0u||a==0x800BEB9Cu)return 1;
 for(base=0;base<4;base++){p=a-taskBases[base];if(p==0||p==16||p==32||p==40||p==48||p==56||p==64||p==68||p==72||p==80||p==88||p==92)return 1;}
 return 0;}
static u32 word(u32 i){u32 region,a,v;for(region=0;region<7;region++){if(i<sizes[region])break;i-=sizes[region];}
 if(region==7)die(29);a=bases[region]+i*4;v=data[region][i];
 if(a==0x800BE9C0u||a==0x800BE614u||a==0x800BEBA0u)return (v>>24)|((v>>8)&0xFF00u)|((v<<8)&0xFF0000u)|(v<<24);
 if(a==0x800BEAA8u)return (v>>16)|(v<<16);return pointerField(a)?abstractPointer(v):v;}
static void reset(const u32*c){u32 i,j;Gfx*first;Gfx*second;
 for(i=0;i<7;i++)for(j=0;j<sizes[i];j++)data[i][j]=0xA5A5A5A5u;
 first=(Gfx*)((u8*)commands+0x4000);second=first+(s32)c[0];
 D_800BE9C8[0]=first;D_800BE9C8[1]=second;D_800BE9D0=(Gfx*)((u8*)(c[2]?second:first)+(s32)c[1]*8+c[8]);
 D_800BE9D8[0]=first+5;D_800BE9D8[1]=second+5;D_800BEAD4=&third.task;
 viewCount=(s32)c[6];globals.words[0x3C4/4]=0x80300000u;globals.words[0x28/4]=0x80200000u;
 D_800BEAD0=(u64*)0x80340000u;D_800BEB9C=(u64*)0x80450000u;D_80038090=(u64*)0x80560000u;D_80038094=(u64*)0x80670000u;
 for(i=0;i<256;i++)framebuffers[i]=0x80700000u+i*256;
 D_800BE9C0=(u8)c[2];D_800BEBA0=(u8)c[3];D_800BE617=(u8)c[5];D_800BEAA8=(s16)c[7];
 mode=c[9];eventCount=fired=error=0;for(i=0;i<10761;i++)initial[i]=word(i);}
static void run(void){u32 n,i,j,wanted;const u32*c;const struct Event*e;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(OSScTask)!=96||sizeof(OSScMsg)!=32||
 __builtin_offsetof(OSScTask,list)!=24||__builtin_offsetof(OSScTask,flags)!=12||
 __builtin_offsetof(OSScTask,msgQ)!=88||__builtin_offsetof(OSScTask,msg)!=92)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=cases[n];reset(c);func_1501C880((s32)0xDEADBEEFu,(s32)c[4]);
  if(error||eventCount!=c[14]||fired!=c[10])die(22);
  for(i=0;i<eventCount;i++){e=&wantedEvents[c[13]+i];if(events[i].target!=e->target||events[i].count!=e->count)die(22);
   for(j=0;j<3;j++)if(events[i].args[j]!=e->args[j])die(22);}
  for(i=0;i<10761;i++){wanted=initial[i];for(j=0;j<c[12];j++)if(changes[c[11]+j].index==i)wanted=changes[c[11]+j].value;
   if(word(i)!=wanted)mismatch(n,i,word(i),wanted);}}}
void _start(void){run();die(0);}
'''
    return text


def providers(before):
    lo, hi = source.build.function_span(before, 'func_1501A39C')
    actual = before[lo:hi].replace('void func_1501A39C(', 'static void actualLists(', 1)
    return HEADER + '''
#undef D_800BE9C8
#undef D_800BE9D8
#define D_800BE9C8 ((s32 *)(globals.bytes+0x3C8))
#define D_800BE9D8 ((s32 *)(globals.bytes+0x3D8))
#define D_800BE9E0 (*(s32 *)(globals.bytes+0x3E0))
#define D_800BE9C4 (*(s32 *)(globals.bytes+0x3C4))
#define D_800BE628 (*(s32 *)(globals.bytes+0x28))
#define D_8002C930 ((Gfx*)0x8002C930u)
''' + actual + '''
static void record(u32 target,u32 count,u32 a,u32 b,u32 c){struct Event*e;if(eventCount>=4){error=1;return;}
 e=&events[eventCount++];e->target=target;e->count=count;e->args[0]=a;e->args[1]=b;e->args[2]=c;}
static void effect(u32 target){
 if(mode==1&&target==0x1501A39Cu)D_800BE9C0^=1;
 else if(mode==2&&target==0x1501CC3Cu){D_800BEAD4=&other.task;D_800BEBA0^=1;D_800BEB9C=(u64*)0x80402340u;D_800BEAD0=(u64*)0x80501230u;}
 else if(mode==3&&target==0x10024F10u){D_800BEAD4=&third.task;D_800BE9C0^=1;}
 else if(mode==4&&target==0x10023580u){D_800BE9C0=255;D_800BEAA8=-1;}
 else if(mode==5&&target==0x1501CC3Cu){D_800BE617=1;viewCount=0x7FFFFFFF;}
 else if(mode==6&&target==0x1501A39Cu)D_800BE9C8[1]+=800;
 else return;fired++;}
void func_1501A39C(void){record(0x1501A39Cu,0,0,0,0);actualLists();effect(0x1501A39Cu);}
s32 func_1501CC3C(void){record(0x1501CC3Cu,0,0,0,0);effect(0x1501CC3Cu);return 0;}
void osWritebackDCacheAll(void){record(0x10024F10u,0,0,0,0);effect(0x10024F10u);}
s32 osSendMesg(OSMesgQueue*q,OSMesg msg,s32 flag){record(0x10023580u,3,(u32)q,abstractPointer((u32)msg),(u32)flag);effect(0x10023580u);return 0;}
'''


def controls(body):
    return dict(no_flip=body.replace('D_800BE9C0 ^= 1;', 'D_800BE9C0 = D_800BE9C0;'),
        limit399=body.replace('available = capacity - 400;', 'available = capacity - 399;'),
        inclusive_reset=body.replace('capacity < used', 'capacity <= used'),
        low_half_swap=body.replace('if (swapBuffers != 0)', 'if ((s16)swapBuffers != 0)'),
        reloaded_capacity=body.replace('    available = capacity - 400;',
            '    capacity = (s32)((u32)D_800BE9C8[1] - (u32)D_800BE9C8[0]) >> 3;\n    available = capacity - 400;'),
        cached_task=body.replace('    s32 capacity;', '    OSScTask *cachedTask;\n    s32 capacity;').replace(
            '    D_800BEAD4->next = 0;', '    cachedTask = D_800BEAD4;\n    D_800BEAD4->next = 0;').replace('D_800BEAD4->', 'cachedTask->'))
