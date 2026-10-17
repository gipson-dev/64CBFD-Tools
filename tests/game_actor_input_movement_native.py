"""Native32 defined-field and complete-call backing for the movement recovery."""
import json
import subprocess

from tools.experiments import game_actor_input_movement_recovery as source
from tools.tests import game_actor_input_movement_oracle as model
from tools.tests.test_game_projected_packet_draw import native_command

GLOBALS=tuple(sorted(model.SIZES))
POINTERS={0x800BE728,0x800CC284,0x800D154C}
ACTOR_FIELDS=tuple(sorted(set((*model.FIELDS,(0,4),(4,1),(0x1CA,1)))))


def values(memory):
    result={}
    for region,base,count in ((0,model.ACTOR,1),(1,model.TABLE,25)):
        for index in range(count):
            for offset,size in ACTOR_FIELDS:
                off=index*0x32C+offset
                result[(region,off,size)]=model.read(memory,base+off,size)
    for region,base in ((2,model.INPUT),(3,model.OTHER_INPUT)):
        for off,size in ((0,2),(2,1),(3,1)):result[(region,off,size)]=model.read(memory,base+off,size)
    return result


DRIVER=r'''
#include <ultra64.h>
TYPE
u8 D_800CC2D0[25*0x32C] __attribute__((aligned(16)));
__asm__(".globl D_800CC5FC\n.set D_800CC5FC,D_800CC2D0+812\n.globl D_800D121C\n.set D_800D121C,D_800CC2D0+20300");
u16 D_800BE710;
MovementInput34F4 **D_800BE728,*D_800CC284;
s32 D_800CC288,D_80082FA0,D_800CC280,D_800BE9F0;
u8 D_800C3E78,D_800DDE3C[256],D_800E0B94,D_800CC26D,D_800CBDD3;
f32 D_800DDDC8[256],D_800D1550,D_800A1980,D_800A1984;
u32 D_800D1580;
MovementActor34F4 *D_800D154C;
CONSTANT_DEFINITIONS
static MovementActor34F4 actor;
static MovementInput34F4 inputA,inputB,*inputSlot;
static u8 expectedActor[0x32C],expectedTable[25*0x32C],expectedA[4],expectedB[4];
static u8 *regions[]={ (u8*)&actor,D_800CC2D0,(u8*)&inputA,(u8*)&inputB };
static u8 *expected[]={expectedActor,expectedTable,expectedA,expectedB};
static u32 lengths[]={0x32C,25*0x32C,4,4};
static void *globals[]={GLOBAL_POINTERS};
static u32 globalSizes[]={GLOBAL_SIZES};
static u32 globalIsPointer[]={GLOBAL_POINTER_FLAGS};
static void *constantPointers[]={CONSTANT_POINTERS};
static u32 constantBits[]={CONSTANT_BITS};
typedef struct {u32 region,offset,size,value;} Patch;
typedef struct {u32 target,n,args[7],command,gate;} Call;
typedef struct {
 u32 initStart,initCount,endStart,endCount,callStart,callCount,mutation,angle,magnitude,gate,gateFloat;
 u32 initialGlobals[GLOBAL_COUNT],finalGlobals[GLOBAL_COUNT],distances[25];
} Case;
static Patch patches[]={PATCHES};
static Call calls[]={CALLS};
static Case cases[]={CASES};
static Case *c;static u32 nextCall,error;
static u32 word(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static f32 real(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static void write(void *p,u32 value,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=((u8*)&value)[i];}
static u32 read(const void *p,u32 n){u32 i,v=0;for(i=0;i<n;i++)((u8*)&v)[i]=((const u8*)p)[i];return v;}
static u32 canonical(const void *p){
 u32 v=(u32)p;
 if(p==&actor)return 0x20000;
 if(p==&inputA)return 0x60000;if(p==&inputB)return 0x60010;if(p==&inputSlot)return 0x62000;
 if(v>=(u32)D_800CC2D0&&v<=(u32)D_800CC2D0+25*0x32C)return 0x800CC2D0+v-(u32)D_800CC2D0;
 return v;
}
static void *decoded(u32 v){
 if(v==0x20000)return &actor;if(v==0x60000)return &inputA;if(v==0x60010)return &inputB;
 if(v==0x62000)return &inputSlot;
 if(v>=0x800CC2D0&&v<=0x800CC2D0+25*0x32C)return D_800CC2D0+v-0x800CC2D0;
 return (void*)v;
}
static void apply(u32 begin,u32 n,u8 **base){u32 i;for(i=begin;i<begin+n;i++){
 Patch *p=patches+i;write(base[p->region]+p->offset,p->value,p->size);}}
static void effect(u32 t){
 switch(c->mutation){
 case 1:if(t==0x1505A630)D_800CC284=&inputB;break;
 case 2:if(t==0x15059140){actor.held=101;actor.depth=25.f;actor.speed=-2.f;}break;
 case 3:if(t==0x1505A6F8){D_800D154C=(MovementActor34F4*)(D_800CC2D0+2*0x32C);D_800CC26D=101;}break;
 case 4:if(t==0x1505A3A8){actor.verticalVelocity=-100.f;actor.speed=205.f;actor.yaw=32767;actor.flag86=1;}break;
 case 5:if(t==0x150599C8)D_800CC284=&inputB;break;
 case 6:if(t==0x1506E8D8){D_800CC26D=102;D_800C3E78=2;}break;
 case 7:if(t==0x1505959C)D_800CC26D=102;break;
 case 8:if(t==0x15059140){actor.controlFlags=2;actor.held=101;inputA.buttons=0;}break;
 case 9:if(t==0x15052590)D_800CC26D=101;break;
 }
}
static u32 callback(u32 t,u32 n,u32 *a){
 u32 i,value=0xA5000002;
 if(nextCall>=c->callCount){error=40;return value;}
 {Call *call=calls+c->callStart+nextCall++;
 if(call->target!=t||call->n!=n||call->command!=D_800D1580||call->gate!=D_800CBDD3)error=41;
 for(i=0;i<n;i++)if(a[i]!=call->args[i])error=42;}
 if(t==0x1505A630)value=c->angle;
 if(t==0x1505A5CC)value=c->magnitude;
 if(t==0x1505A6F8)value=c->distances[(a[1]-0x800CC2D0)/0x32C];
 effect(t);return value;
}
static u32 call0(u32 t){u32 a[1]={0};return callback(t,0,a);}
void func_150585F0(MovementActor34F4*p,f32 v){u32 a[]={canonical(p),word(v)};callback(0x150585F0,2,a);}
void func_15059140(MovementActor34F4*p){u32 a[]={canonical(p)};callback(0x15059140,1,a);}
u16 func_1505A630(f32 x,f32 y,s32 z){u32 a[]={word(x),word(y),(u32)z};return callback(0x1505A630,3,a);}
f32 func_1505A5CC(MovementInput34F4*p){u32 a[]={canonical(p)};return real(callback(0x1505A5CC,1,a));}
void func_15052590(MovementActor34F4*p){u32 a[]={canonical(p)};callback(0x15052590,1,a);}
void func_1506E8D8(void){call0(0x1506E8D8);}
void func_1506E5FC(void){call0(0x1506E5FC);}
void func_1505959C(MovementActor34F4*p,s32 v){u32 a[]={canonical(p),(u32)v};callback(0x1505959C,2,a);}
f32 func_1505A6F8(MovementActor34F4*p,MovementActor34F4*q){u32 a[]={canonical(p),canonical(q)};return real(callback(0x1505A6F8,2,a));}
u8 func_150599C8(MovementActor34F4*p,u8 v,u16 w){u32 a[]={canonical(p),v,w};return callback(0x150599C8,3,a);}
f32 func_1505A3A8(f32 f,MovementActor34F4*p,f32 g,f32 h,u8 v){
 u32 a[]={word(f),canonical(p),word(g),word(h),v};return real(callback(0x1505A3A8,5,a));}
s32 func_15073FA0(void){return call0(0x15073FA0);}
void func_1505E650(MovementActor34F4*p,u16 v,f32 f,f32 g,f32 h,f32 j,s32 w){
 u32 a[]={canonical(p),v,word(f),word(g),word(h),word(j),(u32)w};callback(0x1505E650,7,a);}
f32 func_150F34A0(u8*p,f32 f){u32 a[]={canonical(p),word(f)};callback(0x150F34A0,2,a);return f < -5.f ? f*D_800A1980+D_800A1984 : .75f;}
f32 fabsf(f32 f){return real(word(f)&0x7FFFFFFF);}
void func_150F34F4(MovementActor34F4*);
static int run(void){
 u32 n,i,j;
 if(sizeof(void*)!=4||sizeof(MovementActor34F4)!=0x32C||sizeof(MovementInput34F4)!=4)return 30;
 LAYOUT_CHECKS
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;nextCall=error=0;inputSlot=&inputA;
 for(j=0;j<4;j++)for(i=0;i<lengths[j];i++)regions[j][i]=expected[j][i]=0xA5;
 apply(0,BASE_COUNT,regions);apply(0,BASE_COUNT,expected);
 apply(c->initStart,c->initCount,regions);apply(c->endStart,c->endCount,expected);
 for(i=0;i<GLOBAL_COUNT;i++)write(globals[i],globalIsPointer[i]?(u32)decoded(c->initialGlobals[i]):c->initialGlobals[i],globalSizes[i]);
 for(i=0;i<sizeof(constantBits)/sizeof(constantBits[0]);i++)write(constantPointers[i],constantBits[i],4);
 D_800DDE3C[0]=c->gate;D_800DDDC8[0]=real(c->gateFloat);
 func_150F34F4(&actor);
 if(error||nextCall!=c->callCount)return error?error:43;
 for(j=0;j<4;j++)for(i=0;i<lengths[j];i++)if(regions[j][i]!=expected[j][i])return 44;
 for(i=0;i<GLOBAL_COUNT;i++){u32 value=read(globals[i],globalSizes[i]);
 if(globalIsPointer[i])value=canonical((void*)value);if(value!=c->finalGlobals[i])return 45;}
 if(inputSlot!=&inputA||D_800DDE3C[0]!=c->gate||word(D_800DDDC8[0])!=c->gateFloat)return 46;
 }
 return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''


def driver(rom,specs):
    base,_=model.fixture(rom);baseline=values(base)
    patches=[(*key,v) for key,v in baseline.items() if v!=int.from_bytes(b'\xA5'*key[2],'big')]
    base_count=len(patches);calls=[];cases=[]
    for spec in specs:
        memory,case=model.fixture(rom,**spec)
        if case['actor']!=model.ACTOR:raise ValueError('Native actor/table aliases are guest-only')
        end,packets,observations,_=model.reference(memory,case)
        starts=[]
        for image in (memory,end):
            delta=[(*key,v) for key,v in values(image).items() if v!=baseline[key]]
            starts.extend((len(patches),len(delta)));patches.extend(delta)
        call_start=len(calls)
        for (target,args),observation in zip(packets,observations):
            calls.append('{0x%X,%d,{%s},0x%X,%d}'%(target,len(args),
                ','.join('0x%X'%v for v in (*args,*([0]*(7-len(args))))),observation[-1],observation[-2]))
        scalar=[*starts,call_start,len(packets),case['mutation'],case['angle'],model.bits(case['magnitude']),
            model.read(memory,0x800DDE3C,1),model.read(memory,0x800DDDC8)]
        array=lambda data:','.join('0x%X'%v for v in data)
        distances=dict(case['distances'])
        cases.append('{%s,{%s},{%s},{%s}}'%(array(scalar),
            array(model.read(memory,a,model.SIZES[a]) for a in GLOBALS),
            array(model.read(end,a,model.SIZES[a]) for a in GLOBALS),
            array(model.bits(distances.get(i,1000.-i*11.)) for i in range(25))))
    constants=range(0x800A1980,0x800A19D8,4)
    fields={'active':0,'kind':4,'positionY':0x18,'verticalVelocity':0x20,'acceleration':0x24,'depth':0x28,
        'speed':0x3C,'facingAngle':0x40,'targetSpeed':0x44,'heading':0x76,
        'desiredHeading':0x78,'yaw':0x7A,'turnStep':0x7E,'flag80':0x80,'flag83':0x83,
        'flag86':0x86,'flagAB':0xAB,'flagAD':0xAD,'valueB8':0xB8,'valueC0':0xC0,
        'valueC4':0xC4,'flags':0xF8,'mode':0x102,'cooldown':0x103,'disabled':0x104,
        'thresholdY':0x118,'held':0x13C,'heldBy':0x13D,'eligible':0x1CA,
        'previousY':0x1CC,'state':0x218,'nearest':0x222,'animation':0x232,'controlFlags':0x25C}
    replacements=dict(TYPE=source.TYPE,
        CONSTANT_DEFINITIONS='f32 '+','.join('D_%08X'%a for a in constants if a>=0x800A1988)+';',
        GLOBAL_POINTERS=','.join('&D_%08X'%a for a in GLOBALS),
        GLOBAL_SIZES=','.join(str(model.SIZES[a]) for a in GLOBALS),
        GLOBAL_POINTER_FLAGS=','.join('1' if a in POINTERS else '0' for a in GLOBALS),
        GLOBAL_COUNT=str(len(GLOBALS)),CONSTANT_POINTERS=','.join('&D_%08X'%a for a in constants),
        CONSTANT_BITS=','.join('0x%X'%struct_word(rom,a) for a in constants),
        PATCHES=',\n'.join('{%d,%d,%d,0x%X}'%p for p in patches),
        CALLS=',\n'.join(calls),CASES=',\n'.join(cases),BASE_COUNT=str(base_count),
        LAYOUT_CHECKS='\n'.join('if(__builtin_offsetof(MovementActor34F4,%s)!=0x%X)return 31;'%(n,v) for n,v in fields.items()))
    text=DRIVER
    for key in sorted(replacements,key=len,reverse=True):text=text.replace(key,replacements[key])
    return text


def struct_word(rom,address):
    import struct
    return struct.unpack_from('>I',rom,0x246440+address-0x800A1980)[0]


def qualify(root,out,rom,specs):
    specs=list(specs);native=out/'native-driver.c';native.write_text(driver(rom,specs))
    controls={
        'signed-stick':source.SELECTED.replace('(f32)D_800CC284->y','(f32)(u8)D_800CC284->y'),
        'signed-yaw':source.SELECTED.replace('actor->yaw + 0x4000','(u16)actor->yaw + 0x4000'),
        'angle-ABI':source.SELECTED.replace('(f32)D_800CC284->y, 0)','(f32)D_800CC284->y, 1)'),
        'floor':source.SELECTED.replace('actor->depth <= contactHeight','actor->depth < contactHeight')}
    exits=[]
    for opt in ('-O2','-O0'):
        for label,body in (('selected',source.SELECTED),*controls.items()):
            path=out/('native-'+label+'.c');path.write_text('#include <ultra64.h>\n'+source.TYPE+body+'\n')
            exe=out/('native-'+label+opt)
            result=subprocess.run(native_command(opt)+['-mstackrealign','-fno-strict-aliasing','-fno-builtin',str(path.relative_to(root)),
                str(native.relative_to(root)),'-o',str(exe)],cwd=root,capture_output=True,text=True)
            if result.returncode:raise ValueError('Movement native compiler: '+result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True)
            if label=='selected' and result.returncode:raise ValueError('Movement native mismatch '+str((opt,result.returncode)))
            if label!='selected':
                if result.returncode not in (40,41,42,43,44,45,46):
                    raise ValueError('Native control must fail a semantic gate, not crash: '+str((label,result.returncode)))
                exits.append(dict(profile=opt,control=label,exit_code=result.returncode))
    row=dict(cases_per_profile=len(specs),profiles=['O2','O0'],UBSan=True,effective_controls=8,
        control_exit_codes=exits,
        complete_actor_table_and_controller_bytes=True,complete_semantic_call_packets=True,
        packet_command_and_gate_snapshots=True,native32_layout_offsets=len(ACTOR_FIELDS),
        no_native_private_stack_fault_or_general_FCSR_claim=True)
    (out/'native.json').write_text(json.dumps(row,indent=2)+'\n')
    return row
