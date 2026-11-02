"""Native32 affine-position ABI, live provider reads and sequential aliases."""
import json,subprocess

def qualify(root,output,source,headers,oracle):
    _,symbols,_=oracle.programs(output,0);rows=[]
    for c in oracle.cases():
        if c.phase or c.out_index<-1 or c.mutation&~7:continue
        initial=oracle.fixture(c);expected,calls,dest=oracle.reference(initial,c,symbols)
        before=[oracle.read(initial,oracle.OWNER+i*4)for i in range(16)]
        after=[oracle.read(expected,oracle.OWNER+i*4)for i in range(16)]
        vector=[oracle.read(expected,dest+i*4)for i in range(3)]
        angle,radius,*_=calls[2][1]
        u=lambda values:','.join('0x%Xu'%v for v in values)
        rows.append('{{%s},{%s},{%s},0x%Xu,0x%Xu,0x%Xu,%d,%du,%du,0x%Xu}'%(u(before),u(after),u(vector),c.scale,c.rng,c.unit,c.out_index,c.mutation,angle,radius))
    prefix='typedef unsigned char u8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'
    prefix+='\n'.join(headers.splitlines()[1:])+r'''
struct Case{u32 before[16],after[16],vector[3],scale,rng,unit;s32 out_index;u32 mutation,angle,radius;};
static const struct Case cases[]={ROWS};
struct Packet{u32 pre[4];f32 basis[16],vector[3],other[3];u32 post[4];};
static struct Packet packet,expected;
static const struct Case *current;
static u32 calls,bad;
static f32 fl(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 ub(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
__attribute__((noipa)) s32 func_150ADA20(void){
 if(calls++!=0)bad=1;
 if(current->mutation&1){packet.basis[10]=3.25;packet.basis[1]=-7.;packet.basis[4]=2.;}
 return (s32)current->rng;
}
__attribute__((noipa)) f32 func_150ADA68(void){
 if(calls++!=1)bad=1;
 if(current->mutation&2){packet.basis[10]=-2.5;packet.basis[7]=11.;packet.basis[2]=13.;}
 return fl(current->unit);
}
__attribute__((noipa)) void func_15143874(s16 angle,f32 radius,f32 *first,f32 *second){
 if(calls++!=2||(u32)(s32)angle!=current->angle||ub(radius)!=current->radius||first==second)bad=1;
 if(current->mutation&4){packet.basis[1]=17.;packet.basis[5]=-5.;packet.basis[9]=.75;}
 *first=(angle-128)*.125f;*second=(64-angle)*.25f;
}
'''.replace('ROWS',','.join(rows))
    suffix=r'''
static void(*volatile invoke)(f32*,f32,f32*)=func_1514F808;
int run(void){u32 i,j;u8 *a=(u8*)&packet,*b=(u8*)&expected;
 if(sizeof(void*)!=4||sizeof(f32)!=4||__builtin_offsetof(struct Packet,basis)!=16)return 9;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];for(j=0;j<sizeof(packet);j++)a[j]=(u8)(j*29+i*13+90);
  for(j=0;j<16;j++)packet.basis[j]=fl(current->before[j]);
  for(j=0;j<sizeof(packet);j++)b[j]=a[j];
  for(j=0;j<16;j++)expected.basis[j]=fl(current->after[j]);
  if(current->out_index==-1)for(j=0;j<3;j++)expected.vector[j]=fl(current->vector[j]);
  f32 *out=current->out_index==-1?packet.vector:packet.basis+current->out_index;
  calls=bad=0;invoke(packet.basis,fl(current->scale),out);
  if(bad||calls!=3)return 1;
  for(j=0;j<sizeof(packet);j++)if(a[j]!=b[j])return 1;
 }
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    old=''.join('    output[%d] = ((basis[%d] * first + basis[%d] * second) + basis[%d]) * scale;\n'%(i,i+4,i+7,i+1)for i in range(3))
    cached='    { f32 cached[3];\n'+old.replace('output[','cached[')+''.join('    output[%d] = cached[%d];\n'%(i,i)for i in range(3))+'    }\n'
    assert old in source
    controls={
        'selected':source,
        'angle-mask':source.replace('random & 255','random & 127'),
        'unmasked-angle':source.replace('(random & 255)','random'),
        'wrong-radius':source.replace('basis[10]','basis[9]'),
        'early-radius':source.replace('    s32 random;','    s32 random;\n    f32 radius;').replace('    sample = func_150ADA68();','    radius = basis[10];\n    sample = func_150ADA68();').replace('sample * basis[10]','sample * radius'),
        'wrong-origin':source.replace('+ basis[1])','+ basis[2])'),
        'wrong-axis':source.replace('basis[8] * second','basis[7] * second'),
        'swapped-points':source.replace('&first, &second','&second, &first'),
        'cached-all-axes':source.replace(old,cached),
        'lost-scale':source.replace('    random = func_150ADA20();','    scale = 1.0f;\n    random = func_150ADA20();'),
    }
    assert all(body!=source for name,body in controls.items()if name!='selected');results=[]
    for opt in('-O0','-O2','-O3'):
        for label,body in controls.items():
            path=output/('native-%s-%s.c'%(label,opt[1:]));path.write_text(prefix+body+suffix);binary=path.with_suffix('.bin')
            command=['cc','-m32',opt,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign','-fexcess-precision=standard','-fno-builtin','-fno-strict-aliasing','-ffp-contract=off','-ffreestanding','-static','-fno-stack-protector','-fno-pie','-no-pie','-nostdlib','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(path)]
            q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0,(label,q.stderr)
            q=subprocess.run([str(binary)],capture_output=True,timeout=20);assert q.returncode==(0 if label=='selected'else 1),(opt,label,q.returncode,q.stdout,q.stderr)
            results.append(dict(profile=opt,label=label,status=q.returncode))
    report=dict(success=True,cases_per_profile=len(rows),profiles=['O0','O2','O3'],effective_controls_each=9,typed_float_arrays_and_fences=True,live_provider_mutations=True,sequential_output_basis_aliases=True,finite_inputs=True,UBSan=True,guest_incoming_homes_not_native_claim=True,results=results)
    (output/'private-native-v8.json').write_text(json.dumps(report,indent=2)+'\n');return report
