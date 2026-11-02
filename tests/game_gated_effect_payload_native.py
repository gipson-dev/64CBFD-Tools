"""Native32 sparse payload ABI; no uninitialized padding claim."""
import json,subprocess

def qualify(root,output,source,headers,g):
    rows=[]
    for c in g.cases():
        if c.phase or c.lazy or c.mutation&~3 or (c.constant&0x7F800000)==0x7F800000:continue
        rows.append('{%du,0x%Xu,%du,0x%Xu,0x%Xu,0x%Xu,%du,%du}'%(c.owner!=0,c.active,c.tag,c.ignored1,c.ignored2,c.constant,c.mutation,c.outcome))
    prefix='typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'+'\n'.join(headers.splitlines()[1:])+r'''
struct Case{u32 present,active,tag,ignored1,ignored2,constant,mutation,outcome;};
static const struct Case cases[]={ROWS};
struct Owner{u32 active;u8 rest[56];};
struct Fence{u32 pre[4];struct Owner owner;u32 post[4];};
static struct Fence packet,expected;
static const struct Case *current;
static u32 calls,bad;
f32 D_800A81E4;
static f32 fl(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 ub(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
__attribute__((noipa)) void *func_15134DAC(GatedEffectPayload *p,s32 extra){
 static const f32 values[6]={-28.,6.,1.,-58.,-3.,-31.};u32 j;
 if(calls++||extra||p->owner!=(u8*)&packet.owner||p->ownerTag!=current->tag||p->field8||p->kind!=2||p->field26!=30||p->field28!=25||p->field2A!=750||p->field2E!=3||p->field2F!=3||p->field30!=-1||p->field38!=4||p->field39!=-1||ub(p->coefficient)!=current->constant)bad=1;
 for(j=0;j<6;j++)if(ub(p->parameters[j])!=ub(values[j]))bad=1;
 if(current->mutation&1){p->ownerTag^=85;p->field28=-123;for(j=0;j<3;j++)p->padding1[j]=(u8)j;}
 if(current->mutation&2){packet.owner.active=0;packet.owner.rest[55]^=255;D_800A81E4=fl(0x87654321);}
 return current->outcome?&packet:0;
}
'''.replace('ROWS',','.join(rows))
    suffix=r'''
static void(*volatile invoke)(u8*,s32,s32)=func_151937F4;
int run(void){u32 i,j,gate;u8 *a=(u8*)&packet,*b=(u8*)&expected;
 if(sizeof(void*)!=4||sizeof(GatedEffectPayload)!=60||__builtin_offsetof(GatedEffectPayload,parameters)!=12||__builtin_offsetof(GatedEffectPayload,coefficient)!=52||__builtin_offsetof(GatedEffectPayload,field39)!=57||sizeof(struct Owner)!=60)return 9;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];for(j=0;j<sizeof(packet);j++)a[j]=(u8)(j*29+i*13+90);
  packet.owner.active=current->active;packet.owner.rest[55]=(u8)current->tag;
  for(j=0;j<sizeof(packet);j++)b[j]=a[j];
  gate=current->present&&current->active;D_800A81E4=fl(current->constant);
  if(gate&&(current->mutation&2)){expected.owner.active=0;expected.owner.rest[55]^=255;}
  calls=bad=0;invoke(current->present?(u8*)&packet.owner:0,(s32)current->ignored1,(s32)current->ignored2);
  if(bad||calls!=gate||ub(D_800A81E4)!=(gate&&(current->mutation&2)?0x87654321u:current->constant))return 1;
  for(j=0;j<sizeof(packet);j++)if(a[j]!=b[j])return 1;
 }
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    controls={'selected':source,'null-gate':source.replace('owner != 0 && ',''),'byte-gate':source.replace('*(u32 *)owner','*owner'),'tag-offset':source.replace('owner[0x3B]','owner[0x3A]'),'lost-owner':source.replace('payload.owner = owner','payload.owner = 0'),'wrong-parameter':source.replace('-58.0f','-57.0f'),'wrong-duration':source.replace('field2A = 750','field2A = 751'),'lost-sentinel':source.replace('field30 = -1','field30 = 0'),'lost-coefficient':source.replace('payload.coefficient = D_800A81E4','payload.coefficient = 0.0f'),'wrong-extra':source.replace('(&payload, 0)','(&payload, 1)')}
    assert all(v!=source for k,v in controls.items()if k!='selected');results=[]
    for opt in('-O0','-O2','-O3'):
        for label,body in controls.items():
            path=output/('native-%s-%s.c'%(label,opt[1:]));path.write_text(prefix+body+suffix);binary=path.with_suffix('.bin')
            command=['cc','-m32',opt,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign','-fexcess-precision=standard','-fno-builtin','-fno-strict-aliasing','-ffp-contract=off','-ffreestanding','-static','-fno-stack-protector','-fno-pie','-no-pie','-nostdlib','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(path)]
            q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0,(label,q.stderr)
            q=subprocess.run([str(binary)],capture_output=True,timeout=20);allowed=(0,)if label=='selected'else(-4,1)if label=='null-gate'else(1,);assert q.returncode in allowed,(opt,label,q.returncode,q.stdout,q.stderr)
            results.append(dict(profile=opt,label=label,status=q.returncode))
    report=dict(success=True,cases_per_profile=len(rows),profiles=['O0','O2','O3'],effective_controls_each=9,typed_owner_payload_and_fences=True,all46_initialized_bytes_qualified=True,uninitialized_padding_not_read_by_native_harness=True,finite_constant_patterns=True,UBSan=True,unused_full32_arguments=True,results=results)
    (output/'private-native-v5.json').write_text(json.dumps(report,indent=2)+'\n');return report
