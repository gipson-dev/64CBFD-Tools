"""Native32 fixture with guest-reference tapes; never observe first-packet holes."""
import struct

from tools.experiments import game_six_piece_debris as source
from tools.tests import game_six_piece_debris_oracle as guest

TYPES = 'typedef unsigned char u8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'


def fixtures(rom, count=1024):
    rows = []
    for v in range(count):
        mode, rotation, pattern = v // 6 % 5, v % 6, v // 30 % 3
        options = (0, 1, 2, 3, -1, 0x80000000)[v % 6]
        kind = (1, 169, 256, 0x7FFFFFFF)[v // 90 % 4]
        memory, args = guest.fixture(rom, options, kind, (v * 0x1234567) & 0xFFFFFFFF,
            0xABCD0000 | (v * 1097 & 65535), pattern)
        calls, packets, _, _ = guest.reference(memory, args, mode, rotation)
        coords = [guest.short(guest.read(memory, guest.ACTOR + 16 + i * 2, 2)) for i in range(3)]
        words = [*args[1:], mode, rotation]
        rows.append('{' + ','.join('0x%Xu' % value for value in words) + ',{' + ','.join(map(str, coords)) + '},{'
            + ','.join('{' + ','.join(map(str, p)) + '}' for p in packets) + '},{'
            + ','.join('0x%Xu' % c[1] for c in calls if c[0] == 'lookup') + '},{'
            + ','.join('0x%Xu' % x for x in calls[-1][1:]) + '}}')
    vector_bits = struct.unpack_from('>18I', rom, 0x24B950)
    prefix = TYPES + source.DECLARATIONS.replace('#pragma intrinsic (fabsf)\n', '')
    return prefix + r'''
_Static_assert(sizeof(DebrisPacket19E040)==96,"packet size");
_Static_assert(__builtin_offsetof(DebrisPacket19E040,asset)==0x40,"asset offset");
_Static_assert(__builtin_offsetof(DebrisPacket19E040,coefficient)==0x48,"coefficient offset");
_Static_assert(__builtin_offsetof(DebrisPacket19E040,kind)==0x5A,"kind offset");
DebrisKinds19E040 D_800A6F80;f32 D_800A6E90[18];
f32 D_800A6F88,D_800A6F8C,D_800A6F90,D_800A6F94;
struct Case {u32 kind,variant,options,flags,context,mode,rotation;s16 coords[3];
 u8 packet[6][90];u32 lookup[6],ring[10];};
static const struct Case cases[]={ROWS};
static const u32 vectors[18]={VECTORS};
static const u32 randoms[6]={0,0x7FFFFFFF,0x80000000,0xFFFF0000,0x12345678,0xFEDCBA98};
static union {u32 align;u8 bytes[128];} actor;
static const struct Case *c;static u32 lookups,randomCount,submits,ringCount,stage,error;
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static f32 number(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
f32 fabsf(f32 f){return number(word(f)&0x7FFFFFFFu);}
s32 func_1518C900(s32 kind){u32 n=++lookups;
 if(stage!=0||n>6||(u32)kind!=c->lookup[n-1]){error=20;return 0;}stage=1;
 if(c->mode==1||c->mode==3){D_800A6E90[(n-1)*3]=(f32)n*-31.25f;
 D_800A6F80.values[n%6]=(u8)(0x70+n);*(s16 *)(actor.bytes+16)=12345;
 D_800A6F94=99.0f;D_800A6F88=11.0f;}
 return c->mode==4&&(n&1)?0:(s32)(0xABCD0000u+n);}
s32 func_150ADA20(void){u32 value=randoms[(randomCount+c->rotation)%6];
 if(stage<1||stage>6)error=21;stage++;randomCount++;
 if(c->mode==3)D_800A6E90[(randomCount/6%6)*3+1]=(f32)randomCount*-2.5f;
 return (s32)value;}
static void append(u8*out,u32 *n,u32 value){u32 j;for(j=0;j<4;j++)out[(*n)++]=(u8)(value>>(24-j*8));}
void func_15168BE4(void *p,u8 flags,s32 context){DebrisPacket19E040 *q=p;u8 out[90];u32 i,n=0,value;
 if(stage!=7||submits>=6||flags!=(u8)c->flags||(u32)context!=c->context){error=22;return;}stage=0;
 for(i=0;i<0x44;i+=4){__builtin_memcpy(&value,(u8 *)p+i,4);append(out,&n,value);}
 for(i=0x48;i<0x54;i+=4){__builtin_memcpy(&value,(u8 *)p+i,4);append(out,&n,value);}
 for(i=0x54;i<0x5E;i++)out[n++]=((u8 *)p)[i];
 if(n!=90)error=23;for(i=0;i<90;i++)if(out[i]!=c->packet[submits][i])error=24;
 if(c->mode==2||c->mode==3){
 if(submits){for(i=0;i<4;i++)if(q->reserved44[i]!=(u8)(submits*19+0x44+i))error=25;
 for(i=0;i<2;i++)if(q->reserved5E[i]!=(u8)(submits*19+0x5E + i))error=25;}
 for(i=0;i<4;i++)q->reserved44[i]=(u8)((submits+1)*19+0x44+i);
 for(i=0;i<2;i++)q->reserved5E[i]=(u8)((submits+1)*19+0x5E + i);
 q->rotation[0]=q->scale[0]=q->coefficient[0]=(f32)(submits+1)*1.25f;
 q->lifetime=(s32)(submits+1)*101;q->alpha=(u8)(submits+1);}
 submits++;}
s32 func_151718F0(f32 x,f32 y,f32 z,f32 radius,s32 lifetime,f32 speed,s32 kind,s32 count,u8 flags,s32 context){
 u32 i,got[10]={word(x),word(y),word(z),word(radius),(u32)lifetime,word(speed),(u32)kind,(u32)count,flags,(u32)context};
 if(stage||lookups!=6||randomCount!=36||submits!=6)error=26;
 for(i=0;i<10;i++)if(got[i]!=c->ring[i])error=27;ringCount++;return 0;}
void func_15170B90(u8 *,s32,s32,s32,u8,s32);
static void(*volatile invoke)(u8 *,s32,s32,s32,u8,s32)=func_15170B90;
static int run(void){u32 v,i;static const u8 kinds[6]={7,2,3,8,9,10};
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(s16)!=2)return 28;
 for(v=0;v<sizeof(cases)/sizeof(cases[0]);v++){c=&cases[v];
 for(i=0;i<128;i++)actor.bytes[i]=0xA5;for(i=0;i<3;i++)*(s16 *)(actor.bytes+16+i*2)=c->coords[i];
 for(i=0;i<18;i++)D_800A6E90[i]=number(vectors[i]);for(i=0;i<6;i++)D_800A6F80.values[i]=kinds[i];
 D_800A6F88=number(0x3E99999A);D_800A6F8C=number(0xBF333333);D_800A6F90=number(0xBE4CCCCD);D_800A6F94=number(0x3DA3D70A);
 lookups=randomCount=submits=ringCount=stage=error=0;
 invoke(actor.bytes,(s32)c->kind,(s32)c->variant,(s32)c->options,(u8)c->flags,(s32)c->context);
 if(error)return error;if(lookups!=6||randomCount!=36||submits!=6||ringCount!=1)return 29;
 if(actor.bytes[0x6E]!=1||actor.bytes[0x6C]!=0xA5||actor.bytes[0x6D]!=0xA5||actor.bytes[0x6F]!=0xA5)return 30;}
 return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('ROWS', ',\n'.join(rows)).replace('VECTORS', ','.join('0x%Xu' % x for x in vector_bits))
