"""Finite native32 recovery checks; code writes use a mutable modeled slot."""
import hashlib,json,re,subprocess
from tools.experiments import game_actor_exit_150c3d5c_recovery as s
from tools.experiments import game_type07_parameter_record_match as factory
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_actor_exit_150c3d5c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

CONTROLS={
    'cartridge-branch':('cartridgeWord != 0x0330C820','cartridgeWord == 0x0330C820'),
    'return-word':('= 0x03E00008','= 0x03E00009'),
    'debris-kind':('func_15171200(3, 203','func_15171200(3, 204'),
    'spray-scale':('2000.0f','1999.0f'),
    'config-kind':('13, 0, 0, 0','12, 0, 0, 0'),
    'descriptor-count':('% 11U','% 10U'),
    'lifetime':('% 52U','% 51U'),
    'position-width':('position.unk0 = (s32)','position.unk0 = (s16)(s32)'),
}
def arr(v):return '{'+','.join(str(x&0xFFFFFFFF)+'U' for x in v)+'}'

def main():
    selected=body((s.OUT/'recovered.c').read_text(),s.NAME)
    constructor=body((s.OUT/'production-baseline'/factory.SOURCE).read_text(),factory.FUNCTION)
    assert constructor==body(factory.SELECTED,factory.FUNCTION)
    decoder=body((s.OUT/'production-baseline'/s.SOURCE).read_text(),'func_150C3D48')
    values=list(g.cases())
    code='''#include <ultra64.h>
typedef struct {s8 unk0,unk1;s16 unk2;s8 unk4;u8 pad5;} Header;
typedef struct {s32 unk0,unk4,unk8;} Header2;
typedef struct struct225 struct225;
static u8 storage[128] __attribute__((aligned(16)));
static u8 output[128] __attribute__((aligned(16)));
static u8 *actor=storage+32;
static u32 patch_words[2],mark;
#define func_10004074 patch_words
_Static_assert(sizeof(Header)==6 && sizeof(Header2)==12,"packet layout");
'''+s.PREAMBLE.replace('extern f32','f32')+'''
void func_151B9BF0(s32,s32,s16,s16,s16,s16,s16,s16,s16,s16,s16,s16,s16,u32,u8,s32);
s32 func_150C3D48(s32);
s32 func_150ADA20(void);
struct Event {u32 target,count,args[49];};
struct Case {u32 seed,mutation,outcome,readmode,mark,count,before[2],after[2],descriptor[4],position[3];u8 initial[128],final[128],outputInitial[128],outputFinal[128];struct Event calls[12];};
static const struct Case cases[]={
'''
    for c in values:
        initial=g.fixture(c);final,calls,observed=g.reference(initial,c);assert len(calls)<=12 and len(observed)==1
        events='{'+','.join('{'+str(t)+'U,'+str(len(a))+'U,'+arr(a)+'}' for t,a in calls)+'}'
        row=(str(c.seed),str(c.mutation),str(c.outcome),str(c.read_mode),str(g.read(final,g.MARK))+'U',str(len(calls)),arr(g.read(initial,g.PATCH+4*i) for i in range(2)),arr(g.read(final,g.PATCH+4*i) for i in range(2)),arr(observed[0][0]),arr(observed[0][1]),arr(initial[g.OWNER-32+i] for i in range(128)),arr(final[g.OWNER-32+i] for i in range(128)),arr(initial[g.OUTPUT-32+i] for i in range(128)),arr(final[g.OUTPUT-32+i] for i in range(128)),events)
        code+='{'+','.join(row)+'},\n'
    code+='''};
static const struct Case *current;static u32 index,bad,counts[9];
static f32 value(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static u32 be(const u8*p,u32 n){u32 v=0,i;for(i=0;i<n;i++)v=v*256+p[i];return v;}
static void storebe(u8*p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(8*(n-1-i)));}
static u32 raw(const u8*p,u32 n){u32 v=0,i;u8*q=(u8*)&v;for(i=0;i<n;i++)q[i]=p[i];return v;}
static void store(u8*p,u32 v,u32 n){u32 i;u8*q=(u8*)&v;for(i=0;i<n;i++)p[i]=q[i];}
static void event(u32 t,u32 n,const u32*a){const struct Event*v;u32 i;
 if(index>=current->count){bad=1;return;}v=&current->calls[index++];if(t!=v->target||n!=v->count)bad=2;
 for(i=0;i<n;i++)if(a[i]!=v->args[i])bad=3;
}
static u32 effect(u32 t,u32 slot){u32 n=counts[slot]++;f32 x=0.f,y=0.f,z=0.f;
 mark=0x13579bdfU+t+n*0x10203U;
 if(!current->mutation)return n;
 if(t==0x15167a68){x=1.25f;y=2.5f;z=3.75f;}
 else if(t==0x151ef040){x=4.5f;y=-6.75f;z=8.25f;}
 else if(t==0x15171200){x=17.25f;y=-31.5f;z=103.75f;}
 else if(t==0x151709b4){x=65537.75f;y=-32769.5f;z=32768.25f;}
 else if(t==0x1516d99c){x=75.5f;y=-95.75f;z=144.125f;}
 else if(t==0x150ada20){if(n==0){x=9.5f;y=-20.25f;z=25.75f;}else{x=-999.25f;y=444.25f;z=777.5f;}}
 else return n;
 *(f32*)(actor+0x14)=x;*(f32*)(actor+0x18)=y;*(f32*)(actor+0x1c)=z;return n;
}
void *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){u32 i;
 event(0x15167a68,6,(u32[]){(u32)a,(u32)b,(u32)c,(u32)d,e,f});effect(0x15167a68,1);
 if(!current->outcome)return 0;for(i=0;i<44;i++)output[32+i]=(u8)(i*19+current->seed*7+0x31);return output+32;
}
'''
    code+=factory.DECLARATIONS+constructor.replace('func_151B9BF0','constructor_impl',1)+'\n'
    code+=decoder.replace('func_150C3D48','decoder_impl',1)+'\n'
    code+='''
void func_151B9BF0(s32 a,s32 b,s16 c,s16 d,s16 e,s16 f,s16 h,s16 i,s16 j,s16 k,s16 l,s16 m,s16 n,u32 v,u8 view,s32 context){
 event(0x151b9bf0,16,(u32[]){(u32)a,(u32)b,(u32)c,(u32)d,(u32)e,(u32)f,(u32)h,(u32)i,(u32)j,(u32)k,(u32)l,(u32)m,(u32)n,v,view,(u32)context});
 constructor_impl(a,b,c,d,e,f,h,i,j,k,l,m,n,v,view,context);
}
s32 func_150C3D48(s32 a){event(0x150c3d48,1,(u32[]){(u32)a});return decoder_impl(a);}
s32 func_151EF040(s32 a,s32 b){u32*p=(u32*)b;
 event(0x151ef040,2,(u32[]){(u32)a,0});if(*p!=0xc23459b8U)bad=4;effect(0x151ef040,3);
 if(current->readmode!=2)*p=current->readmode==0?0x0330c820U:0x0330c821U;
 return current->readmode==2?-1:0;
}
s32 func_150ADA20(void){u32 n;static const u32 draws[7]={0,0xffffffffU,0x80000000U,10,11,51,52};
 event(0x150ada20,0,(u32[]){0});n=effect(0x150ada20,7);return(s32)draws[(current->seed/12+n)%7];
}
struct225 *func_151602C0(Header*h,Header2*p,s32 a2,s32 a3,s32 a4,s32 a5,u8 a6,u8 a7,s32 a8,u8 a9,s32 a10){
 u32 desc[4]={(u8)h->unk0,(u8)h->unk1,(u16)h->unk2,(u8)h->unk4},pos[3]={(u32)p->unk0,(u32)p->unk4,(u32)p->unk8},i;
 event(0x151602c0,11,(u32[]){0,0,(u32)a2,(u32)a3,(u32)a4,(u32)a5,a6,a7,(u32)a8,a9,(u32)a10});
 for(i=0;i<4;i++)if(desc[i]!=current->descriptor[i])bad=5;
 for(i=0;i<3;i++)if(pos[i]!=current->position[i])bad=6;
 effect(0x151602c0,8);return 0;
}
'''
    for name,slot,target in (('func_15171200',4,g.DEBRIS),('func_151709B4',5,g.SPRAY),('func_1516D99C',6,g.CONFIG)):
        m=re.search(r'void '+name+r'\((.*?)\);',s.PREAMBLE,re.S);assert m,name
        types=[v.strip() for v in m[1].split(',')];names=['a'+str(i) for i in range(len(types))]
        args=['word('+n+')' if t=='f32' else '(u32)'+n for t,n in zip(types,names)]
        code+='void '+name+'('+','.join(t+' '+n for t,n in zip(types,names))+'){event(0x%X,%d,(u32[]){%s});effect(0x%X,%d);}\n'%(target,len(types),','.join(args),target,slot)
    for name,text in [('selected',selected)]+[(n,selected.replace(a,b,1)) for n,(a,b) in CONTROLS.items()]:
        if name!='selected':assert text!=selected,name
        code+='\n'+text.replace(s.NAME,'test_'+name.replace('-','_'),1)+'\n'
    code+='''
typedef void (*Test)(u8*);
static int check(Test test){u32 n,i,p;u8 bytes[128];
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];current=c;index=bad=mark=0;for(i=0;i<9;i++)counts[i]=0;
  for(i=0;i<128;i++){storage[i]=c->initial[i];output[i]=c->outputInitial[i];}
  for(i=0;i<3;i++){p=32+0x14+4*i;store(storage+p,be(c->initial+p,4),4);}
  for(i=0;i<2;i++)patch_words[i]=c->before[i];D_800A0338=value(0xbf333333);
  test(actor);
  if(bad||index!=c->count||mark!=c->mark)return 1;
  for(i=0;i<2;i++)if(patch_words[i]!=c->after[i])return 2;
  for(i=0;i<128;i++)bytes[i]=storage[i];for(i=0;i<3;i++){p=32+0x14+4*i;storebe(bytes+p,raw(storage+p,4),4);}
  for(i=0;i<128;i++)if(bytes[i]!=c->final[i])return 3;
  for(i=0;i<128;i++)bytes[i]=output[i];if(c->outcome){storebe(bytes+48,raw(output+48,4),4);for(i=0;i<11;i++)storebe(bytes+54+2*i,raw(output+54+2*i,2),2);}
  for(i=0;i<128;i++)if(bytes[i]!=c->outputFinal[i])return 4;
 }return 0;
}
static int run(void){if(check(test_selected))return 1;
'''
    for i,name in enumerate(CONTROLS):code+='if(!check(test_'+name.replace('-','_')+'))return '+str(20+i)+';\n'
    code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    src=s.OUT/'native.c';src.write_text(code);profiles={}
    for opt in ('-O0','-O2','-O3'):
        exe=s.OUT/('native'+opt);p=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True)
        assert p.returncode==0 and not p.stdout and not p.stderr,(opt,p.stdout,p.stderr)
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
        profiles[opt]=dict(cases=len(values),effective_controls=len(CONTROLS),UBSan=True,sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
    report=dict(profiles=profiles,finite_only=True,actor_bytes=128,output_bytes=128,code_slot_bytes=8,
        descriptor_defined_bytes=5,descriptor_padding_bytes_uncredited=1,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),installed=False,c_match_credit=0)
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
