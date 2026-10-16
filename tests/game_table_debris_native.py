"""Separate-TU native32 tapes; initial indeterminate packet bytes are not observed."""
import struct

from tools.experiments import game_table_debris as source
from tools.tests import game_table_debris_oracle as guest

TYPES = 'typedef unsigned char u8;typedef unsigned short u16;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'


def declarations():
    packet = source.previous.previous.DECLARATIONS.replace('zero5C', 'control5C').replace('zero5D', 'control5D')
    return packet.replace('#pragma intrinsic (fabsf)\n', '') + source.DECLARATIONS


def fixtures(rom, count=1024):
    rows = []
    for value in range(count):
        pattern, mode, rotation = value % 3, value // 3 % 6, value // 18 % 6
        flags = 0xABCD0000 | (value * 1097 & 65535)
        context = (value * 0x1234567 + 0x80000000) & 0xFFFFFFFF
        memory, args = guest.fixture(rom, pattern, flags, context)
        calls, packets, _ = guest.reference(memory, args, mode, rotation)
        coords = [guest.short(guest.read(memory, guest.ACTOR + 16 + 2 * i, 2)) for i in range(3)]
        words = (pattern, mode, rotation, flags, context)
        rows.append('{' + ','.join('0x%Xu' % w for w in words) + ',{' + ','.join(map(str, coords)) + '},{' +
            ','.join('{' + ','.join(map(str, guest.initialized(p))) + '}' for p in packets) + '},{' +
            ','.join('0x%Xu' % c[1] for c in calls if c[0] == 'lookup') + '}}')
    table = struct.unpack_from('>42I', rom, 0x24B998)
    return TYPES + declarations() + r'''
_Static_assert(sizeof(DebrisPacket19E040)==96,"packet size");
_Static_assert(sizeof(TableDebris19E040)==28,"table stride");
_Static_assert(__builtin_offsetof(TableDebris19E040,offset)==4,"table offset");
_Static_assert(__builtin_offsetof(TableDebris19E040,rotation)==16,"table rotation");
_Static_assert(__builtin_offsetof(DebrisPacket19E040,kind)==0x5A,"kind byte");
_Static_assert(__builtin_offsetof(DebrisPacket19E040,control5C)==0x5C,"control byte");
TableDebris19E040 D_800A6ED8[6];
f32 D_800A6F98,D_800A6F9C,D_800A6FA0,D_800A6FA4,D_800A6FA8,D_800A6FAC;
struct Case {u32 pattern,mode,rotation,flags,context;s16 coords[3];u8 packets[6][90];u32 kinds[6];};
static const struct Case cases[]={ROWS};
static const u32 table[42]={TABLE};
static const u32 randoms[6]={0,0x37800000,0x3E800000,0x3F000000,0x3F400000,0x3F7FFF00};
static const struct Case *c;static u32 lookupCount,draws,submits,stage,error;
static union{u32 alignment;u8 bytes[128];}actor;
static f32 number(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
f32 fabsf(f32 f){return number(word(f)&0x7FFFFFFFu);}
s32 func_1518C900(s32 kind){u32 n=++lookupCount;
 if(stage||n>6||(u32)kind!=c->kinds[n-1]){error=20;return 0;}stage=1;
 if(c->mode==1||c->mode==3){D_800A6ED8[n-1].kind=(u16)(0xDC80+n);
 D_800A6ED8[n-1].offset[0]=(f32)n*-31.25f;D_800A6ED8[n-1].offset[1]=(f32)n*-7.5f;
 D_800A6ED8[n-1].rotation[0]=(f32)n*19.25f;*(s16 *)(actor.bytes+16)=12345;
 D_800A6F98=D_800A6F9C=D_800A6FA0=D_800A6FA4=D_800A6FA8=D_800A6FAC=99.0f;}
 return c->mode==4&&(n&1)?0:(s32)(0xABCD0000u+n);}
f32 func_150ADA68(void){f32 value=number(randoms[(draws+c->rotation)%6]);
 if(stage!=1&&stage!=2)error=21;stage++;draws++;
 if(c->mode==5)D_800A6ED8[(draws-1)/2].offset[0]=(f32)draws*17.25f;
 return value;}
static void append(u8*out,u32*n,u32 value){u32 j;for(j=0;j<4;j++)out[(*n)++]=(u8)(value>>(24-j*8));}
void func_15168BE4(void *p,u8 flags,s32 context){DebrisPacket19E040*q=p;u8 out[90];u32 i,n=0,value;
 if(stage!=3||submits>=6||flags!=(u8)c->flags||(u32)context!=c->context){error=22;return;}stage=0;
 for(i=0;i<0x44;i+=4){__builtin_memcpy(&value,(u8*)p+i,4);append(out,&n,value);}
 for(i=0x48;i<0x54;i+=4){__builtin_memcpy(&value,(u8*)p+i,4);append(out,&n,value);}
 for(i=0x54;i<0x5E;i++)out[n++]=((u8*)p)[i];
 if(n!=90)error=23;for(i=0;i<90;i++)if(out[i]!=c->packets[submits][i])error=24;
 if(c->mode==2||c->mode==3){
 if(submits){for(i=0;i<4;i++)if(q->reserved44[i]!=(u8)(submits*19+0x44+i))error=25;
 for(i=0;i<2;i++)if(q->reserved5E[i]!=(u8)(submits*19+0x5E + i))error=25;}
 for(i=0;i<4;i++)q->reserved44[i]=(u8)((submits+1)*19+0x44+i);
 for(i=0;i<2;i++)q->reserved5E[i]=(u8)((submits+1)*19+0x5E + i);
 q->rotation[0]=q->scale[0]=q->coefficient[0]=(f32)(submits+1)*1.25f;
 q->lifetime=(s32)(submits+1)*101;q->alpha=(u8)(submits+1);}
 submits++;}
void func_15170F4C(u8*,u8,s32);
static void(*volatile invoke)(u8*,u8,s32)=func_15170F4C;
static int run(void){u32 v,i,j;f32 values[6];
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(s16)!=2)return 26;
 for(v=0;v<sizeof(cases)/sizeof(cases[0]);v++){c=&cases[v];
 for(i=0;i<128;i++)actor.bytes[i]=0xA5;for(i=0;i<3;i++)*(s16*)(actor.bytes+16+i*2)=c->coords[i];
 for(i=0;i<6;i++){D_800A6ED8[i].kind=(u16)(table[i*7]>>16);D_800A6ED8[i].reserved02=(u16)table[i*7];
 for(j=0;j<6;j++)values[j]=number(table[i*7+j+1]);
 if(c->pattern){D_800A6ED8[i].kind=(u16)(c->pattern==1?0x8000+i*257:65535-i);D_800A6ED8[i].reserved02=0xABCD;
 for(j=0;j<6;j++)values[j]=(f32)((i+1)*(j+1))*3.25f*(j&1?-1.0f:1.0f);}
 for(j=0;j<3;j++){D_800A6ED8[i].offset[j]=values[j];D_800A6ED8[i].rotation[j]=values[j+3];}}
 D_800A6F98=number(0x3E99999A);D_800A6F9C=number(0xBF333333);D_800A6FA0=number(0xBE4CCCCD);
 D_800A6FA4=number(0x3DCCCCCD);D_800A6FA8=number(0x3E6B851F);D_800A6FAC=number(0x3DB851EC);
 lookupCount=draws=submits=stage=error=0;invoke(actor.bytes,(u8)c->flags,(s32)c->context);
 if(error)return error;if(lookupCount!=6||draws!=12||submits!=6||stage)return 27;
 if(actor.bytes[0x6E]!=1||actor.bytes[0x6C]!=0xA5||actor.bytes[0x6D]!=0xA5||actor.bytes[0x6F]!=0xA5)return 28;}
 return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('ROWS', ',\n'.join(rows)).replace('TABLE', ','.join('0x%Xu' % w for w in table))
