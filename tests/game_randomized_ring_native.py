"""Separate-unit native32 ring fixture with independent reference packet tapes."""
import struct

from tools.experiments import game_randomized_ring_emitter as source
from tools.tests import game_randomized_ring_oracle as guest

TYPES = 'typedef unsigned char u8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'


def fixture(rom, colors, count=1024):
    table = struct.unpack_from('>65I', rom, 0x23ECE0)
    rows = []
    for v in range(count):
        mode, pattern = (2 if v & 4 else 0), v // 54 % 3
        rgba = (colors, bytes.fromhex('80ff0000'), bytes.fromhex('ff008000'))[v // 18 % 3]
        randoms = guest.RANDOMS[v // 6 % 3]
        memory, args = guest.fixture(rgba, (-1, 0, 1, 2, 5, 10)[v % 6], pattern,
            0xABCD0000 | (v * 1097 & 65535))
        args = (*args[:9], (v * 1103515245 + 12345) & 0xFFFFFFFF)
        calls, packets, _ = guest.reference(memory, args, table, randoms, mode=mode)
        row = '{{' + ','.join('0x%Xu' % (x & 0xFFFFFFFF) for x in args) + '},' + str(mode) + ',{' + ','.join(map(str, rgba[:3])) + '},{'
        row += ','.join('0x%Xu' % x for x in randoms) + '},' + str(len(packets)) + ',{'
        row += ','.join(str(c[1]) for c in calls if c[0] == source.SINE) or '0'
        row += '},{' + (','.join('{' + ','.join('0x%Xu' % x for x in p) + '}' for p in packets) or '{0}') + '}}'
        rows.append(row)
    prototype = 'void func_1516D4E8' + source.DECLARATIONS.split('void func_1516D4E8', 1)[1].split(';', 1)[0]
    factory = prototype + '{u32 got[31]={' + ','.join('(u32)arg%d' % i for i in range(31)) + r'''};u32 i;
 if(stage!=5||submits>=c->count){error=23;return;}for(i=0;i<31;i++)if(got[i]!=c->packet[submits][i])error=24;
 submits++;stage=0;mutate(submits);}
'''
    return TYPES + source.DECLARATIONS + r'''
_Static_assert(sizeof(RingColors19E040)==3,"three-byte staged palette");
RingColors19E040 D_8008CC20;
struct Case{u32 args[10],mode;u8 colors[3];u32 randoms[3],count,angles[10],packet[10][31];};
static const struct Case cases[]={ROWS};
static const u32 table[65]={TABLE};
static const struct Case *c;static u32 stage,sines,cosines,randomCount,submits,error;
static f32 number(u32 u){union{f32 f;u32 u;}x;x.u=u;return x.f;}
static void mutate(u32 n){if(c->mode==2){D_8008CC20.values[0]=(u8)(0xF0-(n&15));
 D_8008CC20.values[1]=(u8)n;D_8008CC20.values[2]=(u8)(n^0xA5);}}
static f32 trig(u8 a){u32 i=a<=64?a:a<=128?128-a:a<=192?a-128:256-a;
 return number(table[i]^((a>64&&a<=192)?0x80000000u:0));}
f32 func_15048A40(u8 a){if(stage||sines>=c->count||a!=c->angles[sines])error=20;
 stage=1;sines++;mutate(sines);return trig((u8)(a-64));}
f32 func_150489B0(u8 a){if(stage!=1||cosines>=c->count||a!=c->angles[cosines])error=21;
 stage=2;cosines++;return trig(a);}
s32 func_150ADA20(void){u32 value=c->randoms[randomCount%3];if(stage<2||stage>4)error=22;
 stage++;randomCount++;mutate(randomCount);return (s32)value;}
FACTORY
void func_151718F0(f32,f32,f32,f32,s32,f32,s32,s32,u8,s32);
static void(*volatile invoke)(f32,f32,f32,f32,s32,f32,s32,s32,u8,s32)=func_151718F0;
static int run(void){u32 v,i;if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(s16)!=2)return 25;
 for(v=0;v<sizeof(cases)/sizeof(cases[0]);v++){c=&cases[v];stage=sines=cosines=randomCount=submits=error=0;
 for(i=0;i<3;i++)D_8008CC20.values[i]=c->colors[i];
 invoke(number(c->args[0]),number(c->args[1]),number(c->args[2]),number(c->args[3]),
 (s32)c->args[4],number(c->args[5]),(s32)c->args[6],(s32)c->args[7],(u8)c->args[8],(s32)c->args[9]);
 if(error)return (int)error;if(stage||sines!=c->count||cosines!=c->count||randomCount!=c->count*3||submits!=c->count)return 26;}
 return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('ROWS', ',\n'.join(rows)).replace('TABLE', ','.join('0x%Xu' % x for x in table)).replace('FACTORY', factory)
