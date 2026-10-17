"""Typed native32 body/caller fixture; no mixed-endian overlapping-object claims."""
from tools.experiments import game_record_maximum_scan as source
from tools.tests import game_record_maximum_oracle as model

HEADER = '#include <ultra64.h>\n' + source.DECLARATIONS.split('extern s32')[0] + '''
struct Inputs {
 u32 pre;u8 count[3];u8 pad;
 u16 *primary[3],*enabled[3],*counts[3];
 RecordMaximum49D30 *preferred[3][30];u8 *fallback[3][30];
 u16 primaryData[3][256],enabledData[3][256],countData[3][256];
 RecordMaximum49D30 records[3][30];s16 tails[3][30][40];
 s16 big[0x40008];u32 post;
};
struct Output {u32 pre;s32 cells[3];u32 post;};
extern struct Inputs inputs;extern struct Output output;
#define D_800C363A inputs.count
#define D_800C3640 output.cells
#define D_800C35D8 inputs.primary
#define D_800C35C8 inputs.enabled
#define D_800C35D0 inputs.counts
#define D_800C3688 inputs.preferred
#define D_800C3778 inputs.fallback
void func_1501CE54(s32);
'''


def program():
    rows = []
    for case in model.cases():
        memory = model.fixture(case); expected = model.reference(memory, case[0])
        value = model.signed(model.read(expected, model.OUTPUT + case[0] * 4))
        rows.append('{%s,%d}' % (','.join(map(str, case)), value))
    text = HEADER + '\nstruct Inputs inputs;struct Output output;\n'
    text += 'static const s32 cases[][6]={' + ',\n'.join(rows) + '};\n'
    text += '''
static u8 initial[sizeof(struct Inputs)];
static const s16 values[7]={-32768,-9999,-1,0,1,37,32767};
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void reset(const s32*c){u32 i,j,slot=(u32)c[0],n=(u32)c[1],mode=(u32)c[2],seed=(u32)c[3];
 const u16 activeValues[5]={0,1,0x100,0x8000,0xFFFF},primaryValues[3]={0,1,3},counts[4]={0,1,2,8};
 u16 active,primary,entries;s16 value,tail;u32 size=sizeof(inputs);
 for(i=0;i<size;i++)((u8*)&inputs)[i]=0xA5;
 for(i=0;i<sizeof(output);i++)((u8*)&output)[i]=0xA5;
 for(i=0;i<3;i++){inputs.primary[i]=inputs.primaryData[i];inputs.enabled[i]=inputs.enabledData[i];inputs.counts[i]=inputs.countData[i];
  for(j=0;j<30;j++){inputs.preferred[i][j]=&inputs.records[i][j];inputs.fallback[i][j]=(u8*)inputs.tails[i][j];}}
 inputs.count[slot]=(u8)n;
 for(i=0;i<n;i++){
  active=activeValues[(seed+3*i)%5];primary=primaryValues[(seed+i)%3];entries=counts[(seed+i)%4];
  value=values[(seed+i*5)%7];tail=values[(seed*3+i*2+2)%7];
  if(mode==1){active=primary=entries=1;value=(s16)(7+i);tail=32767;}
  else if(mode==2){active=primary=entries=1;value=(s16)(-1-(s32)i);tail=(s16)(17+i);}
  else if(mode==5){active=(u16)(0x100u<<(i%2));primary=1;value=-1;entries=2;tail=(s16)(99+i);}
  else if(mode==6)active=0;
  else if(mode==7){active=65535;primary=0;value=-1;entries=(u16)((seed&1u)?65535:32768);tail=32767;}
  else if(mode==8){active=primary=entries=1;value=-1;tail=(s16)(i==0?17:-1);}
  if(i==0&&(mode==3||mode==4))primary=4;
  inputs.enabledData[slot][i]=active;inputs.primaryData[slot][i]=primary;inputs.countData[slot][i]=entries;
  if(i>=30)continue;
  inputs.records[slot][i].maximum=value;inputs.records[slot][i].overrideValue=(s16)c[4];
  if(mode==7)inputs.fallback[slot][i]=(u8*)inputs.big;
  if(entries){s16*p=(s16*)inputs.fallback[slot][i];p[entries*4u-1u]=tail;}
 }
 for(i=0;i<size;i++)initial[i]=((u8*)&inputs)[i];
}
void _start(void){u32 n,i,slot;const s32*c;
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(RecordMaximum49D30)!=20||
  __builtin_offsetof(RecordMaximum49D30,maximum)!=10||__builtin_offsetof(RecordMaximum49D30,overrideValue)!=18)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  c=cases[n];slot=(u32)c[0];reset(c);func_1501CE54((s32)slot);
  if(output.cells[slot]!=c[5]||output.pre!=0xA5A5A5A5u||output.post!=0xA5A5A5A5u)die(21);
  for(i=0;i<3;i++)if(i!=slot&&(u32)output.cells[i]!=0xA5A5A5A5u)die(21);
  for(i=0;i<sizeof(inputs);i++)if(((u8*)&inputs)[i]!=initial[i])die(21);
 }
 die(0);
}
'''
    return text


def controls(body):
    return dict(
        negative_override=body.replace('value != -9999', 'value >= 0'),
        unsigned_preferred=body.replace('->maximum;', '->maximum;\n                    primaryValue = (u16)primaryValue;'),
        presence_not_update=body.replace('primaryValue = D_800C3688', 'value = 1;\n                    primaryValue = D_800C3688'),
        always_fallback=body.replace('if (!value)', 'if (1)'),
        byte_enable=body.replace('active != 0', '(active & 255) != 0'),
        unsigned_tail=body.replace('*(s16 *)', '*(u16 *)'),
        byte_tail_count=body.replace('u16 entries;', 'u8 entries;'),
        wrong_tail_stride=body.replace('entries * 8 - 2', 'entries * 4 - 2'))
