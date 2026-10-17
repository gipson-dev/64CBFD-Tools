"""Native32 typed scalar/pointer lanes and bounded byte-DMA providers."""
import itertools

from tools.tests import game_microcode_loader_oracle as model

REGIONS = ((model.STATE, 4), (model.STATE_OBJECT, 64), (model.CACHE, 8), (model.TABLE, 4160),
    (model.FLAG, 8), (model.SECONDARY_DATA, 4), (model.PRIMARY, 0x3000), (model.SECONDARY, 0x2200))
BYTES = sum(size for _, size in REGIONS)
HEADER = '''#include <ultra64.h>
#include "structs.h"
typedef struct {u32 pre[4];struct104 state;u32 post[4];} StateBank;
typedef struct {u32 pre,flag;u64 *primary,*secondary;u32 post;} Scalars;
extern StateBank stateBank;extern Scalars scalars;
extern u64 primaryArena[1540],secondaryArena[1092];
extern s32 recordWords[1048];extern u8 cacheBytes[8];
struct Event{u32 packet[4],cache0,cache1,data0,data1;};
extern struct Event events[4];extern u32 eventCount,mode,fired,error,variant,paired;
#define D_800B0DF0 (&stateBank.state)
#define D_800BEB98 (*(s32 *)&scalars.flag)
#define D_80084070 (*(s8 *)(cacheBytes+0))
#define D_80084074 (*(s8 *)(cacheBytes+4))
#define D_80084078 (recordWords+4)
#define D_800C1060 (primaryArena+2)
#define D_800BEBB0 (secondaryArena+2)
#define D_800BEB9C scalars.primary
#define D_800BEAD0 scalars.secondary
#define D_2D4B0 ((u8 *)0x2D4B0u)
u32 abstractPointer(u32);
s32 func_10004514(s32,void *,u32,s32);
'''


def cases():
    for value, flag, cache in itertools.product((0, 1, 2, 3, 4, 5, 7, 127, 128, 129, 255),
            (0, 1, 2, 0x10000, 0x10001, 0xFFFFFFFF, 0x80000001), range(5)):
        yield model.fixture(value, flag, cache), 0, False
    for value, flag, mode in itertools.product(range(4), (0, 1), (1, 2, 4, 8, 15)):
        yield model.fixture(value, flag), mode, False
    for value, flag, cache in itertools.product(range(6), (0, 1), (0, 1)):
        yield model.fixture(value, flag, cache, retail=True), 0, True


def program():
    rows, changes, events = [], [], []
    for memory, mode, retail in cases():
        expected, calls, observations, fired = model.reference(memory, mode)
        delta, offset = [], 0
        for base, size in REGIONS:
            for i in range(size):
                if memory[base + i] != expected[base + i]: delta.append((offset + i, expected[base + i]))
            offset += size
        assert offset == BYTES
        values = (memory[model.STATE_OBJECT + 43], model.read(memory, model.FLAG), memory[model.CACHE],
            memory[model.PAIR_CACHE], mode, int(retail), len(changes), len(delta), len(events), len(calls),
            sum(1 << (n - 1) for n in fired))
        rows.append('{%s}' % ','.join('0x%Xu' % n for n in values)); changes.extend(delta)
        events.extend((*packet, *snapshot) for (_, packet), snapshot in zip(calls, observations))
    text = HEADER + '''
StateBank stateBank;Scalars scalars;u64 primaryArena[1540],secondaryArena[1092];
s32 recordWords[1048];u8 cacheBytes[8];struct Event events[4];
u32 eventCount,mode,fired,error,variant,paired;
void func_1501CC3C(void);
struct Change{u32 at;u8 value;};static const struct Change changes[]={'''
    text += ','.join('{%d,%d}' % row for row in changes) + '};\n'
    text += 'static const u32 cases[][11]={' + ',\n'.join(rows) + '};\n'
    text += 'static const struct Event wantedEvents[]={' + ','.join('{{%s},%s}' % (
        ','.join('0x%Xu' % n for n in row[:4]), ','.join('0x%Xu' % n for n in row[4:])) for row in events) + '};\n'
    text += 'static const s32 retailTable[8][4]={' + ','.join('{' + ','.join(str(n) for n in row) + '}' for row in model.RETAIL_TABLE) + '};\n'
    text += '''
static u8 initial[25240];
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
u32 abstractPointer(u32 p){u32 a=(u32)D_800C1060,b=(u32)D_800BEBB0;
 if(p>=a&&p<a+0x3000u)return 0x800C1060u+p-a;
 if(p>=b&&p<b+0x2200u)return 0x800BEBB0u+p-b;return p;}
static u32 byte(u32 value,u32 at){return (value>>(24-8*(at&3u)))&255u;}
static u32 publicByte(u32 i){
 if(i<4)return byte(0x70000u,i);i-=4;
 if(i<64)return ((u8*)&stateBank.state)[i];i-=64;
 if(i<8)return cacheBytes[i];i-=8;
 if(i<4160)return byte((u32)D_80084078[i>>2],i);i-=4160;
 if(i<8)return byte(i<4?scalars.flag:abstractPointer((u32)scalars.primary),i);i-=8;
 if(i<4)return byte(abstractPointer((u32)scalars.secondary),i);i-=4;
 if(i<0x3000u)return ((u8*)D_800C1060)[i];i-=0x3000u;
 if(i<0x2200u)return ((u8*)D_800BEBB0)[i];die(29);}
static void canaries(void){u32 i;
 for(i=0;i<4;i++)if(stateBank.pre[i]!=0xA5A5A5A5u||stateBank.post[i]!=0xA5A5A5A5u||
  recordWords[i]!=(s32)0xA5A5A5A5u||recordWords[1044+i]!=(s32)0xA5A5A5A5u)die(21);
 for(i=64;i<sizeof(stateBank.state);i++)if(((u8*)&stateBank.state)[i]!=0xA5)die(21);
 for(i=0;i<16;i++)if(((u8*)primaryArena)[i]!=0xA5||((u8*)primaryArena)[16+0x3000+i]!=0xA5||
  ((u8*)secondaryArena)[i]!=0xA5||((u8*)secondaryArena)[16+0x2200+i]!=0xA5)die(21);
 if(scalars.pre!=0xA5A5A5A5u||scalars.post!=0xA5A5A5A5u)die(21);}
static void reset(const u32*c){u32 i;const s32 *row;
 fill(&stateBank,sizeof(stateBank));fill(&scalars,sizeof(scalars));fill(primaryArena,sizeof(primaryArena));
 fill(secondaryArena,sizeof(secondaryArena));fill(recordWords,sizeof(recordWords));fill(cacheBytes,sizeof(cacheBytes));
 for(i=0;i<260;i++){row=retailTable[i&7u];
  D_80084078[4*i+0]=(s32)(c[5]&&i<8?(u32)row[0]:0x2000u+i*64u);
  D_80084078[4*i+1]=(s32)(c[5]&&i<8?(u32)row[1]:0x2010u+i*64u);
  D_80084078[4*i+2]=(s32)(c[5]&&i<8?(u32)row[2]:0x10000u+i*32u);
  D_80084078[4*i+3]=(s32)(c[5]&&i<8?(u32)row[3]:0x10008u+i*32u);}
 stateBank.state.pad2B[0]=(u8)c[0];scalars.flag=c[1];cacheBytes[0]=(u8)c[2];cacheBytes[4]=(u8)c[3];
 scalars.primary=(u64*)0x80401230u;scalars.secondary=(u64*)0x80502340u;
 variant=c[0];paired=4;if(variant>=2){variant-=2;paired=0;}if(c[1]==1)variant+=2;
 mode=c[4];eventCount=fired=error=0;for(i=0;i<25240;i++)initial[i]=(u8)publicByte(i);}
static void run(void){u32 n,i,j;const u32*c;const struct Event*e;
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(u64)!=8||__builtin_offsetof(struct104,pad2B)!=43)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=cases[n];reset(c);func_1501CC3C();canaries();
  if(error||eventCount!=c[9]||fired!=c[10])die(22);
  for(i=0;i<eventCount;i++){e=&wantedEvents[c[8]+i];
   for(j=0;j<4;j++)if(events[i].packet[j]!=e->packet[j])die(22);
   if(events[i].cache0!=e->cache0||events[i].cache1!=e->cache1||events[i].data0!=e->data0||events[i].data1!=e->data1)die(22);}
  for(i=0;i<c[7];i++)initial[changes[c[6]+i].at]=changes[c[6]+i].value;
  for(i=0;i<25240;i++)if(publicByte(i)!=initial[i])die(21);}}
void _start(void){run();die(0);}
'''
    return text


PROVIDERS = HEADER + '''
s32 func_10004514(s32 device,void*destination,u32 size,s32 block){u32 n=eventCount,i,a=(u32)destination;
 u32 p=(u32)D_800C1060,s=(u32)D_800BEBB0,src=(u32)device;struct Event*e;s32*r;
 if(n>=4||block!=1||size>0x2000u||!((a>=p&&a<=p+0x3000u&&size<=p+0x3000u-a)||
  (a>=s&&a<=s+0x2200u&&size<=s+0x2200u-a))){error=1;return 0;}
 e=&events[eventCount++];e->packet[0]=src;e->packet[1]=abstractPointer(a);e->packet[2]=size;e->packet[3]=(u32)block;
 e->cache0=cacheBytes[0];e->cache1=cacheBytes[4];e->data0=abstractPointer((u32)scalars.primary);e->data1=abstractPointer((u32)scalars.secondary);
 for(i=0;i<size;i++)((u8*)destination)[i]=(u8)((src+i)*37u+((src+i)>>8)*13u+0x59u);
 if(n==0&&(mode&1u)){r=D_80084078+variant*4;r[1]+=8;r[2]+=16;r[3]+=24;
  stateBank.state.pad2B[0]=255;scalars.flag=0x10001u;scalars.primary=(u64*)0x80405678u;fired|=1;}
 else if(n==1&&(mode&2u)){cacheBytes[0]=128;cacheBytes[4]=254;fired|=2;}
 else if(n==2&&(mode&4u)){r=D_80084078+(variant+paired)*4;r[1]+=8;r[2]+=16;r[3]+=24;
  scalars.secondary=(u64*)0x80506789u;fired|=4;}
 else if(n==3&&(mode&8u)){cacheBytes[0]=129;cacheBytes[4]=253;
  scalars.primary=(u64*)0x8060789Au;scalars.secondary=(u64*)0x807089ABu;fired|=8;}
 return 0;}
'''


def controls(body):
    early = body.replace('        D_80084070 = variant;\n', '').replace('        D_80084074 = pairedOffset;\n', '')
    early = early.replace('        func_10004514', '        D_80084070 = variant;\n        D_80084074 = pairedOffset;\n        func_10004514', 1)
    stale = body.replace('    s32 variant;', '    u32 cachedTextBytes;\n    s32 variant;').replace(
        '        func_10004514', '        cachedTextBytes = range[1] - range[0];\n        func_10004514', 1).replace(
        '(s32)(range[1] - range[0])', 'cachedTextBytes', 1)
    return dict(unsigned_cache=body.replace('variant != D_80084070', 'variant != (u8)D_80084070'),
        nonzero_flag=body.replace('D_800BEB98 == 1', 'D_800BEB98 != 0'), early_cache=early, stale_span=stale)
