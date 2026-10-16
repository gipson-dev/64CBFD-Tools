"""Native32 typed backing and separate bounded providers for the complete initializer."""
from tools.experiments import game_viewport_initialize as source
from tools.tests import game_viewport_initialize_oracle as model

REGIONS = ((model.VIEWS, 0x2200), (model.OTHER, 0x2200), (model.THIRD, 0x2200),
    (0x800BE600, 0x440), (model.BUFFER, 0x200), (model.ASPECTS, 32))
WORDS = sum(size // 4 for _, size in REGIONS)


def header(before):
    owner = source.recovered_owner(before)
    end = owner.index('} ViewProjection476D0;') + len('} ViewProjection476D0;')
    start = owner.rfind('typedef struct {', 0, end)
    return '#include <ultra64.h>\n' + owner[start:end] + '''
typedef union {u32 words[2176];ViewProjection476D0 views[22];} ViewBank;
typedef union {u32 words[272];s32 signedWords[272];f32 floats[272];u8 bytes[1088];} Globals;
typedef union {u32 words[128];Vp viewports[32];} Scratch;
typedef union {u32 words[8];f32 values[8];} Aspects;
typedef union {u32 word;f32 value;} Coefficient;
struct Event {u32 target,count,args[4];};
extern ViewBank banks[3];extern Globals globals;extern Scratch scratch;extern Aspects aspects;
extern const Coefficient coefficients[4];extern struct Event events[12];
extern u32 eventCount,trigCount,seed,mode,fired,indexValue,error;
u32 pointer(u32);u32 abstractPointer(u32);
#define D_800BE620 globals.signedWords[8]
#define D_800BE624 globals.signedWords[9]
#define D_800BE628 globals.signedWords[10]
#define D_800BE62C globals.signedWords[11]
#define D_800BE630 (globals.bytes+48)
#define D_800BE638 globals.signedWords[14]
#define D_800BE650 globals.signedWords[20]
#define D_800BE668 ((s16 (*)[2])(globals.bytes+104))
#define D_800BE6B8 globals.floats[46]
#define D_800BE9C0 globals.bytes[960]
#define D_80082FA8 aspects.values
#define D_800968E4 coefficients[0].value
#define D_800968E8 coefficients[1].value
#define D_800968EC coefficients[2].value
#define D_800968F0 coefficients[3].value
#define VIEW_PROJECTIONS_476D0 ((ViewProjection476D0 *)D_800BE628)
void func_1501B0A0(s32,s32);s32 func_1501AE94(s32);void func_1501AF44(f32*,f32*,f32*,f32*);
void func_1510B32C(s32,f32,f32,f32);
'''


def cases():
    for index in (0, 1, 3):
        for layout in (0, 1, 2, 3):
            for depth in (1023, -1, 65535, 65536):
                for transfer in (0, 1, 0x10000, 0x8000):
                    for page in (0, 1):
                        yield model.fixture(index, layout, depth, transfer, page), 0, 0, False
    for index in (0, 1, 3):
        for layout in (0, 1, 3):
            for transfer in (0, 1):
                for mode in range(1, 6):
                    yield model.fixture(index, layout, transfer=transfer), 2, mode, False
    memory, args = model.fixture(1, 2)
    model.put(memory, model.ORIGINS + 44, 0x8000, 2)
    yield (memory, args), 0, 0, True


def patches(before, after):
    index = 0
    result = []
    for base, size in REGIONS:
        for p in range(0, size, 4):
            a, b = model.read(before, base + p), model.read(after, base + p)
            if a != b: result.append((index, b))
            index += 1
    assert index == WORDS
    return result


def program(before):
    rows, changes, calls = [], [], []
    for (memory, args), seed, mode, negative in cases():
        expected, packets, complete = model.reference(memory, args, seed, mode)
        assert complete
        delta = patches(memory, expected)
        values = (*args, memory[model.PAGE], seed, mode, int(negative), len(changes), len(delta), len(calls), len(packets))
        rows.append('{%s}' % ','.join('0x%Xu' % v for v in values))
        changes.extend(delta)
        calls.extend((target, len(args), (*args, *([0] * (4 - len(args))))) for target, args in packets)
    payload = header(before) + '''
void func_1501A8C0(s32,s32,s32,s16);
ViewBank banks[3];Globals globals;Scratch scratch;Aspects aspects;
const Coefficient coefficients[4]={{0x42CE0A3Du},{0x42726666u},{0x3C8EFA35u},{0x3C8EFA35u}};
struct Event events[12];u32 eventCount,trigCount,seed,mode,fired,indexValue,error;
struct Patch{u32 index,value;};static const struct Patch changes[]={'''
    payload += ','.join('{%d,0x%Xu}' % p for p in changes) + '};\n'
    payload += 'static const struct Event expectedEvents[]={'+','.join('{0x%Xu,%d,{%s}}' %
        (target, count, ','.join('0x%Xu' % v for v in args)) for target, count, args in calls) + '};\n'
    payload += 'static const u32 cases[][12]={' + ',\n'.join(rows) + '};\n'
    payload += '''
static u32 initial[6936];
static const u32 fields[3][8]={{0x438C0000u,0x43480000u,0x430C0000u,0x42C80000u,0x43120000u,0x42D80000u,0x42820000u,0x42340000u},
 {0x438C8000u,0x43490000u,0x430D0000u,0x42CA0000u,0x43130000u,0x42DA0000u,0x42840000u,0x42380000u},
 {0x438D0000u,0x434A0000u,0x430E0000u,0x42CC0000u,0x43140000u,0x42DC0000u,0x42860000u,0x423C0000u}};
static const u32 offsets[]={1,2,3,4,13,14,27,28};
static const s32 widths[]={292,292,146,146,320,320},heights[]={216,108,108,108,240,240};
static const u32 aspectValues[]={0x3FD47AE1u,0x3F547AE1u,0x3FD70A3Du,0x3FD70A3Du,0x3FD47AE1u,0};
static void die(u32 c){__asm__ volatile("int $0x80"::"a"(1),"b"(c):"memory");__builtin_unreachable();}
static void mismatch(u32 n,u32 i,u32 actual,u32 wanted){u32 a[4]={n,i,actual,wanted},j,k;char s[36];
 for(j=0;j<4;j++){for(k=0;k<8;k++)s[j*9+k]="0123456789ABCDEF"[(a[j]>>(28-k*4))&15];s[j*9+8]=(char)(j==3?10:32);}
 __asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(s),"d"(36):"memory");die(21);}
u32 pointer(u32 p){u32 i;for(i=0;i<3;i++)if(p>=0x70000u+i*0x10000u&&p<0x72200u+i*0x10000u)return (u32)&banks[i]+p-(0x70000u+i*0x10000u);
 if(p>=0x800BE600u&&p<0x800BEA40u)return (u32)&globals+p-0x800BE600u;
 if(p>=0xA0000u&&p<0xA0200u)return (u32)&scratch+p-0xA0000u;
 if(p>=0x80082FA8u&&p<0x80082FC8u)return (u32)&aspects+p-0x80082FA8u;
 die(29);return 0;}
u32 abstractPointer(u32 p){u32 i;for(i=0;i<3;i++)if(p>=(u32)&banks[i]&&p<(u32)&banks[i]+0x2200u)return 0x70000u+i*0x10000u+p-(u32)&banks[i];
 if(p>=(u32)&scratch&&p<(u32)&scratch+512u)return 0xA0000u+p-(u32)&scratch;
 if(p>=(u32)&globals&&p<(u32)&globals+1088u)return 0x800BE600u+p-(u32)&globals;
 die(29);return 0;}
static u32 byteswap(u32 w){return (w>>24)|((w>>8)&0xFF00u)|((w<<8)&0xFF0000u)|(w<<24);}
static u32 halfswap(u32 w){return (w>>16)|(w<<16);}
static u32 word(u32 i){u32 bank,at,v;if(i<6528){bank=i/2176;at=(i%2176)%96;v=banks[bank].words[i%2176];
  if(at==0)return byteswap(v);if(at>=16&&at<24)return halfswap(v);return v;}
 if(i<6800){at=i-6528;v=globals.words[at];if(at==10||at==11)return abstractPointer(v);
  if(at==12||at==240)return byteswap(v);if(at>=26&&at<56&&at!=46)return halfswap(v);return v;}
 if(i<6928)return halfswap(scratch.words[i-6800]);return aspects.words[i-6928];}
static void reset(const u32*c){u32 i,j,b;
 for(b=0;b<3;b++)for(i=0;i<2176;i++)banks[b].words[i]=0xA5A5A5A5u;
 for(i=0;i<272;i++)globals.words[i]=0xA5A5A5A5u;for(i=0;i<128;i++)scratch.words[i]=0xA5A5A5A5u;
 for(i=0;i<8;i++)aspects.words[i]=0xA5A5A5A5u;
 for(i=0;i<6;i++){globals.signedWords[14+i]=widths[i];globals.signedWords[20+i]=heights[i];aspects.words[i]=aspectValues[i];
  for(j=0;j<5;j++){D_800BE668[i*5+j][0]=(s16)(146+j*20);D_800BE668[i*5+j][1]=(s16)(108-j*10);}}
 for(b=0;b<3;b++)for(i=0;i<5;i++)for(j=0;j<8;j++)banks[b].words[i*96+offsets[j]]=fields[b][j];
 D_800BE620=292;D_800BE624=216;D_800BE628=(s32)&banks[0];D_800BE62C=(s32)&scratch;
 globals.words[46]=0x3F4CCCCDu;D_800BE9C0=(u8)c[4];
 if(c[7])D_800BE668[c[1]*5+c[0]][0]=-32768;
 seed=c[5];mode=c[6];indexValue=c[0];eventCount=trigCount=fired=error=0;
 for(i=0;i<6936;i++)initial[i]=word(i);
}
static void run(void){u32 n,i,j,wanted;const u32*c;const struct Event*e;
 if(sizeof(void*)!=4||sizeof(Vp)!=16||sizeof(ViewProjection476D0)!=384||sizeof(ViewBank)!=8704||
 __builtin_offsetof(ViewProjection476D0,insideBounds)!=1||__builtin_offsetof(ViewProjection476D0,viewport)!=64||
 __builtin_offsetof(ViewProjection476D0,projectionScale)!=132)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=cases[n];reset(c);
  func_1501A8C0((s32)c[0],(s32)c[1],(s32)c[2],(s16)c[3]);
  if(error||eventCount!=c[11]||fired!=(u32)((mode>=1&&mode<=4)||(mode==5&&(s16)c[3]!=0)))die(22);
  for(i=0;i<eventCount;i++){e=&expectedEvents[c[10]+i];if(events[i].target!=e->target||events[i].count!=e->count)die(22);
   for(j=0;j<4;j++)if(events[i].args[j]!=e->args[j])die(22);}
  for(i=0;i<6936;i++){wanted=initial[i];for(j=0;j<c[9];j++)if(changes[c[8]+j].index==i)wanted=changes[c[8]+j].value;
   if(word(i)!=wanted)mismatch(n,i,word(i),wanted);}
 }}
void _start(void){run();die(0);}
'''
    return payload


def providers(before):
    bounds = source.build.function_span(before, 'func_1501AE94')
    clamp = source.build.function_span(before, 'func_1501AF44')
    bodies = before[bounds[0]:bounds[1]].replace('s32 func_1501AE94(', 'static s32 actualBounds(', 1) + '\n'
    bodies += before[clamp[0]:clamp[1]].replace('void func_1501AF44(', 'static void actualClamp(', 1) + '\n'
    return header(before) + bodies + '''
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static f32 scalar(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static void record(u32 target,u32 count,u32 a,u32 b,u32 c,u32 d){struct Event*e;
 if(eventCount>=12){error=1;return;}e=&events[eventCount++];e->target=target;e->count=count;
 e->args[0]=a;e->args[1]=b;e->args[2]=c;e->args[3]=d;}
static void effect(u32 target){ViewProjection476D0*v;
 if(mode==1&&target==0x15047D60u&&trigCount==1)D_800BE628=(s32)&banks[1];
 else if(mode==2&&target==0x15047C00u&&trigCount==2)D_800BE628=(s32)&banks[2];
 else if(mode==3&&target==0x15047C00u&&trigCount==4)D_800BE9C0=1;
 else if(mode==4&&target==0x1510B32Cu)D_800BE628=(s32)&banks[2];
 else if(mode==5&&target==0x1501B0A0u){v=&VIEW_PROJECTIONS_476D0[indexValue];v->baseFovX=75.0f;v->baseFovY=35.0f;}
 else return;fired++;}
static f32 trig(u32 target,f32 a){static const u32 values[]={0x3E800000u,0x3F800000u,0xBF000000u,0x40000000u,0x3E000000u,0xBE800000u};
 trigCount++;record(target,1,bits(a),0,0,0);effect(target);return scalar(values[(trigCount-1+seed)%6]);}
f32 sinf(f32 a){return trig(0x15047D60u,a);}f32 cosf(f32 a){return trig(0x15047C00u,a);}
void func_1501B0A0(s32 i,s32 layout){record(0x1501B0A0u,2,(u32)i,(u32)layout,0,0);effect(0x1501B0A0u);}
s32 func_1501AE94(s32 i){record(0x1501AE94u,1,(u32)i,0,0,0);return actualBounds(i);}
void func_1501AF44(f32*a,f32*b,f32*c,f32*d){record(0x1501AF44u,4,abstractPointer((u32)a),abstractPointer((u32)b),abstractPointer((u32)c),abstractPointer((u32)d));actualClamp(a,b,c,d);}
void func_1510B32C(s32 i,f32 x,f32 y,f32 scale){record(0x1510B32Cu,4,(u32)i,bits(x),bits(y),bits(scale));effect(0x1510B32Cu);}
'''


def controls(body):
    cached = body.replace('VIEW_PROJECTIONS_476D0', 'cachedViews').replace('    s16 *origin;',
        '    ViewProjection476D0 *cachedViews = VIEW_PROJECTIONS_476D0;\n    s16 *origin;', 1)
    return dict(narrow_depth_first=body.replace(' = depth >> 1;', ' = (s16)depth >> 1;'),
        wrong_origin_stride=body.replace('layout * 20 + index * 4', 'layout * 20 + index * 8'),
        unsigned_origin=body.replace('(f32)origin[0]', '(f32)(u16)origin[0]'),
        cached_base=cached, wrong_layout=body.replace('if (layout == 1)', 'if (layout == 2)'),
        division_depth=body.replace(' = depth >> 1;', ' = depth / 2;'))
