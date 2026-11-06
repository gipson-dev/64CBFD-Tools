"""Exhaustive 12-bit native32 grid against an independent widened formula."""
def source(body):
    return '#include <ultra64.h>\n'+r'''
static s32 gates[3];
#define D_800D19A0 (gates[0])
static s32 words[3][2][16][2];static s32*banks[3][2];s32**D_800C4488[3];
'''+body.replace('void func_15062D10(', '__attribute__((noinline)) void func_15062D10(',1)+r'''
static void(*volatile probe)(s32,s32,s32,s32,s32,s32)=func_15062D10;
static u32 axis(u32 initial,s32 delta,u32 extent,s32 absolute){
 u32 low=(u32)((s64)initial+(s64)delta);s64 value=low<0x80000000u?(s64)low:(s64)low-0x100000000ll;
 s64 adjusted=value+(value<0?(s64)extent:0)-(value>(s64)extent?(s64)extent:0);
 return(absolute?(u32)delta:(u32)adjusted)&4095u;
}
static int run(void){
 static const s32 steps[]={(-2147483647-1),-8195,-4097,-4096,-1,0,1,4096,4097,2147483647};
 static const s32 modes[]={0,1,-1,(-2147483647-1)};static const u32 extents[]={2,3,4096,4097};
 for(u32 s=0;s<3;s++){D_800C4488[s]=banks[s];for(u32 b=0;b<2;b++){banks[s][b]=&words[s][b][0][0];for(u32 n=0;n<16;n++){words[s][b][n][0]=(s32)(0xA5000000u|(s*64+b*32+n));words[s][b][n][1]=(s32)0x5AA55AA5u;}}}
 for(u32 s=0;s<3;s++){gates[s]=0;s32**saved=D_800C4488[s];D_800C4488[s]=0;for(u32 m=0;m<4;m++)probe(s,0,steps[0],steps[9],0,modes[m]);D_800C4488[s]=saved;}
 for(u32 d=0;d<4;d++)for(u32 j=0;j<10;j++)for(u32 n=0;n<4096;n++)for(u32 m=0;m<4;m++){
  u32 slot=(n+d)%3,bank=(j+d)&1,entry=(n+j+d)&15,oldY=(n*37+13)&4095u;u32 opcode=((n+j+d)&255u)<<24;
  s32*p=words[slot][bank][entry];u32 before=opcode|(n<<12)|oldY,size=((extents[d]-2)<<12)|(extents[(d+1)&3]-2)|0xD3000000u;
  p[0]=(s32)before;p[1]=(s32)size;u32 adjacent=entry^1;u32 a=(u32)words[slot][bank][adjacent][0],b=(u32)words[slot][bank][adjacent][1];
  gates[slot]=(n&1)?1:(s32)0x80000000u;probe(slot,entry,steps[j],steps[(j+3)%10],bank,modes[m]);
  u32 expected=opcode|(axis(n,steps[j],extents[d],modes[m])<<12)|axis(oldY,steps[(j+3)%10],extents[(d+1)&3],modes[m]);
  if((u32)p[0]!=expected||(u32)p[1]!=size||(u32)words[slot][bank][adjacent][0]!=a||(u32)words[slot][bank][adjacent][1]!=b||D_800C4488[slot]!=banks[slot]||banks[slot][bank]!=&words[slot][bank][0][0])return 1;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
