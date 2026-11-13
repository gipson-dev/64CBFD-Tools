"""Native32 boundary, callback and object-bit-pattern checks with UBSan."""
from pathlib import Path
import importlib.util,itertools,json,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-linked-effect-151d2c40-durable'
from tools.tests import game_actor_linked_effect_151d2c40_guest as g
text=(out/'formatted.c').read_text();head=text[:text.index('/* Generated placeholder declarations. */')]
start=text.index('#ifdef __GNUC__');end=text.index('/* Update a linked actor effect',start)
header=head+text[start:end];source=body(text,'func_151D2C40')
cases=[]
for gate,flags,timer,ticks,answer,mutation,phase in itertools.product(range(6),(0,1),(-32768,-1,0,1,32767),(0,1,0x7fffffff,0x80000000),(0,1),range(3),(0,8)):
    n=len(cases);kinds=(-128,-2,-1,0,1,3,127);u=kinds[(n*5+gate)%len(kinds)];r=kinds[(n*3+flags)%len(kinds)]
    cases.append(g.Case(gate,flags,timer,ticks,u,r,answer,mutation,phase))
rows=[]
for c in cases:
    m=g.fixture(c);expected,calls=g.reference(m,c)
    after_helper=dict(m)
    if c.gate==0:g.helper_effect(after_helper,c,g.STACK+c.phase-0x10)
    timer_after=(g.signed16(g.read(after_helper,g.EFFECT+0x26,2))-g.read(after_helper,g.TICKS))&65535
    is_release=int(c.gate==0 and (after_helper[g.EFFECT+0x28]&1)!=0 and g.signed16(timer_after)<0)
    sequence=0;slot=-1
    for target,args in calls:
        code=1 if target==g.TRANSFORM else 3 if target==g.DESTROY else 2
        sequence=(sequence<<2)|code
        if code==2:slot=(target-g.CBBASE)//4
    child=g.read(expected,g.EFFECT+0x2c);outputs=[g.read(expected,g.EFFECT+0x34+4*i) for i in range(3)]
    rows.append('{%d,%d,%d,0x%08Xu,%d,%d,%d,%d,%d,%d,0x%X,%d,%d,0x%04Xu,0x%08Xu,{%s},%d,%d,%d}'%(
        c.gate,c.flags,c.timer,c.ticks&0xffffffff,c.update,c.release,c.answer,c.mutation,c.phase,len(calls),sequence,slot,is_release,
        g.read(expected,g.EFFECT+0x26,2),child,','.join('0x%08Xu'%x for x in outputs),
        expected[g.EFFECT+0x28],expected[g.EFFECT+0x29],expected[g.EFFECT+0x2a]))
fixture=r'''
static u8 effectBytes[256] __attribute__((aligned(16)));
static u8 actorBytes[0x400] __attribute__((aligned(16)));
static u8 matrixBytes[0x4000] __attribute__((aligned(16)));
void *callbackSlots[262];
__asm__(".globl D_8008FC40\n.set D_8008FC40,callbackSlots+520\n.globl D_8008FC48\n.set D_8008FC48,callbackSlots+528");
s32 D_800BE9E4;
typedef struct {s32 gate,flags,timer;u32 ticks;s32 update,release,answer,mutation,phase,ncalls,sequence,slot,isRelease;
                u32 expectedTimer,expectedChild,output[3];u8 expectedFlags,expectedUpdate,expectedRelease;} Row;
static const Row rows[]={ROWS};
static const Row *current;static int ncall,sequence,error;static f32 *savedPoint;
static void write16(u8 *p,u16 v){__builtin_memcpy(p,&v,2);}
static void write32(u8 *p,u32 v){__builtin_memcpy(p,&v,4);}
static u16 read16(const u8 *p){u16 v;__builtin_memcpy(&v,p,2);return v;}
static u32 read32(const u8 *p){u32 v;__builtin_memcpy(&v,p,4);return v;}
static void event(int k){ncall++;sequence=(sequence<<2)|k;}
void func_15143134(f32 *input,f32 *output,u8 *matrix){
 event(1);savedPoint=output;
 if(input!=(f32*)(effectBytes+0x18)||matrix!=matrixBytes+3*64)error=1;
 write32((u8*)output+0,0x3f123456u);write32((u8*)output+4,0xbf456789u);write32((u8*)output+8,0x7fc12345u);
 if(current->mutation==1){effectBytes[0x28]^=1;write16(effectBytes+0x26,0xfffd);effectBytes[0x2a]=0;effectBytes[0x29]=1;}
 else if(current->mutation==2){effectBytes[0x28]=0;effectBytes[0x29]=0xff;}
}
static void changed(void *effect,void *point){
 event(2);if(effect!=(void*)effectBytes||point!=(void*)savedPoint)error=2;
 write32((u8*)point,read32((u8*)point)^0x11223344u);write32(effectBytes+0x2c,0xcafebabeu);
}
static s32 updateGood(LinkedEffect151D2C40 *p,f32 *v){changed(p,v);return current->answer;}
static s32 updateBad(LinkedEffect151D2C40 *p,f32 *v){error=3;return updateGood(p,v);}
static void releaseGood(ReleaseChainNode *p,void *v){changed(p,v);}
static void releaseBad(ReleaseChainNode *p,void *v){error=4;releaseGood(p,v);}
void func_1516972C(struct102 *p){event(3);if((void*)p!=(void*)effectBytes)error=5;}
static int run(void){unsigned n,i;struct127 *actor=(struct127*)actorBytes;
 if(sizeof(void*)!=4||__builtin_offsetof(LinkedEffect151D2C40,timer)!=0x26||
    __builtin_offsetof(LinkedEffect151D2C40,output)!=0x34||__builtin_offsetof(struct127,unk1D4)!=0x1d4)return 10;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  current=&rows[n];for(i=0;i<256;i++)effectBytes[i]=(u8)((i+16)*29+0x35);
  for(i=0;i<0x400;i++)actorBytes[i]=(u8)((i+16)*29+0x35);
  for(i=0;i<262;i++){if(current->isRelease)callbackSlots[i]=(void*)releaseBad;else callbackSlots[i]=(void*)updateBad;}
  write32(effectBytes+0x10,(u32)actor);effectBytes[0x14]=0x43;effectBytes[0x24]=3;
  write16(effectBytes+0x26,(u16)current->timer);effectBytes[0x28]=(u8)current->flags;
  effectBytes[0x29]=(u8)current->update;effectBytes[0x2a]=(u8)current->release;
  write32(effectBytes+0x2c,0x12345678u);
  for(i=0;i<3;i++){u8 *p=effectBytes+0x34+4*i;u32 v=((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];write32(p,v);}
  actor->interaction_state=1;actor->id=2;actor->unique_id=0x43;actor->unk74=0x12;actor->unk1D4=(struct255*)matrixBytes;
  if(current->gate==1)actor->interaction_state=0;
  if(current->gate==2)actor->id=255;
  if(current->gate==3)actor->unique_id=0x44;
  if(current->gate==4)actor->unk1D4=0;
  if(current->gate==5)actor->unk74=0xff;
  write32((u8*)&D_800BE9E4,current->ticks);
  if(current->slot>=0){if(current->slot>=262)return 11;
    if(current->isRelease)callbackSlots[current->slot]=(void*)releaseGood;
    else callbackSlots[current->slot]=(void*)updateGood;}
  ncall=sequence=error=0;savedPoint=0;func_151D2C40((LinkedEffect151D2C40*)effectBytes);
  if(error||ncall!=current->ncalls||sequence!=current->sequence)return 12;
  if(read16(effectBytes+0x26)!=current->expectedTimer||read32(effectBytes+0x2c)!=current->expectedChild)return 13;
  for(i=0;i<3;i++)if(read32(effectBytes+0x34+4*i)!=current->output[i])return 14;
  if(effectBytes[0x28]!=current->expectedFlags||effectBytes[0x29]!=current->expectedUpdate||effectBytes[0x2a]!=current->expectedRelease)return 15;
 }
 return 0;
}
'''.replace('ROWS',',\n'.join(rows))
candidate=out/'native-candidate.c';candidate.write_text(header+source+'\n'+fixture+START)
def execute(src,name,opt):
    path=out/(name+'.c');path.write_text(header+src+'\n'+fixture+START);exe=out/(name+'-'+opt[1:])
    p=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=root,capture_output=True,text=True)
    assert not p.returncode,(name,opt,p.stderr);return subprocess.run([str(exe)]).returncode
for opt in ('-O0','-O2','-O3'):assert execute(source,'native-candidate',opt)==0,opt
controls=[('wrong-gate','effect->actorId != actor->unique_id','effect->actorId == actor->unique_id'),
          ('wrong-timer','(u32)(s32)effect->timer - (u32)D_800BE9E4','(u32)(s32)effect->timer + (u32)D_800BE9E4'),
          ('wrong-matrix','effect->matrixIndex << 6','effect->matrixIndex << 5'),
          ('wrong-callback-result','!D_8008FC40[kind](effect, point)','D_8008FC40[kind](effect, point)'),
          ('missing-child-clear','effect->child = 0;','(void)0;')]
rejected=[]
for name,old,new in controls:
    assert source.count(old)==1,(name,source.count(old));code=execute(source.replace(old,new),name,'-O2')
    assert code!=0,('ineffective control',name);rejected.append(name)
report={'cases_per_optimization':len(cases),'optimizations':['-O0','-O2','-O3'],
        'effective_controls':rejected,'helper_and_callbacks_modeled':True,'ubsan_trapping':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
