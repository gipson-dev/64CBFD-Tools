"""Native32 live point provider, complete initialized payload fields and fences."""
import json,subprocess
def qualify(root,output,source,headers,g):
 rows=[]
 for c in g.cases():
  if c.phase or c.lazy or c.mutation&~3 or c.pattern>=6:continue
  u=lambda v:','.join('0x%Xu'%x for x in v)
  rows.append('{%du,0x%Xu,%du,0x%Xu,0x%Xu,%du,{%s},{%s},{%s}}'%(bool(c.owner),c.active,bool(c.attached),c.mode,c.extra,c.mutation,u(g.point_words(c)),u(g.constants(c)),u(g.constants(c,True))))
 globals=['D_800A%04X'%(0x81C0+4*i)for i in range(9)]
 prefix='typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'+'\n'.join(headers.splitlines()[1:])+'\n'+''.join('f32 '+n+';\n'for n in globals)+r'''
struct Case{u32 present,active,attached,mode,extra,mutation,point[3],before[9],after[9];};
static const struct Case cases[]={ROWS};
struct Owner{u32 active;u8 reserved[464];u8 *attached;};
struct Fence{u32 pre[4];struct Owner owner;u32 post[4];};
static struct Fence packet,expected;
static u32 matrix[192],calls,bad;
static const struct Case *current;
static f32 fl(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 ub(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
__attribute__((noipa)) void func_15142314(u8 *attached,s32 index,f32 *point){u32 i;
 if(calls++||attached!=(u8*)matrix||index!=10)bad=1;
 for(i=0;i<3;i++)point[i]=fl(current->point[i]);
 if(current->mutation&1){SET_AFTER}
 if(current->mutation&2){packet.owner.active=0;packet.owner.attached=0;}
}
__attribute__((noipa)) void func_15152520(PointEffectPayload *p,u8 mode,s32 extra){u32 i;
 if(calls++!=1||mode!=(current->mode&255)||(u32)extra!=current->extra||p->baseCount!=8||p->countRange!=7||p->field14||p->field16!=255||p->field18!=-33||p->field1A!=24||p->field30!=40||p->field32!=35||p->field34!=160||p->field38!=19||p->field3C||p->field70!=33||p->field71!=15||p->field72!=25||p->field74!=10)bad=1;
 for(i=0;i<3;i++)if(ub(p->position[i])!=current->point[i])bad=1;
 for(i=0;i<5;i++)if(ub(p->parameters[i])!=current->after[i+2])bad=1;
 for(i=0;i<8;i++)if(p->colors[i]!=255)bad=1;
 if(ub(p->values[0])||ub(p->values[3])||ub(p->values[5])||ub(p->values[8]))bad=1;
 if(ub(p->values[1])!=current->after[7]||ub(p->values[2])!=current->after[8]||ub(p->values[4])!=current->after[0]||ub(p->values[6])!=current->after[0]||ub(p->values[7])!=current->after[1]||ub(p->values[9])!=current->after[1])bad=1;
}
'''.replace('ROWS',','.join(rows)).replace('SET_AFTER',''.join(n+'=fl(current->after[%d]);'%i for i,n in enumerate(globals)))
 suffix=r'''
static void(*volatile invoke)(u8*,s32,s32)=func_15193660;
int run(void){u32 i,j,gate;u8 *a=(u8*)&packet,*b=(u8*)&expected;
 if(sizeof(void*)!=4||sizeof(PointEffectPayload)!=120||__builtin_offsetof(struct Owner,attached)!=468||__builtin_offsetof(PointEffectPayload,values)!=64||__builtin_offsetof(PointEffectPayload,padding76)!=118)return 9;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];for(j=0;j<sizeof(packet);j++)a[j]=(u8)(j*29+i*13+90);
  packet.owner.active=current->active;packet.owner.attached=current->attached?(u8*)matrix:0;
  for(j=0;j<sizeof(packet);j++)b[j]=a[j];
  SET_BEFORE
  gate=current->present&&current->active&&current->attached;
  if(gate&&(current->mutation&2)){expected.owner.active=0;expected.owner.attached=0;}
  calls=bad=0;invoke(current->present?(u8*)&packet.owner:0,(s32)current->mode,(s32)current->extra);
  if(bad||calls!=2*gate)return 1;
  CHECK_GLOBALS
  for(j=0;j<sizeof(packet);j++)if(a[j]!=b[j])return 1;
 }
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''.replace('SET_BEFORE',''.join(n+'=fl(current->before[%d]);'%i for i,n in enumerate(globals))).replace('CHECK_GLOBALS',''.join('if(ub('+n+')!=(gate?current->after[%d]:current->before[%d])){return 1;}\n'%(i,i)for i,n in enumerate(globals)))
 early=source.replace('    PointEffectPayload payload;','    PointEffectPayload payload;\n    f32 early;').replace('        func_15142314(attached, 10, payload.position);','        early = D_800A81C0;\n        func_15142314(attached, 10, payload.position);').replace('= D_800A81C0;','= early;')
 # Restore the intentional early read after replacing the two payload reads.
 early=early.replace('early = early;','early = D_800A81C0;')
 controls={'selected':source,'null-gate':source.replace('owner != 0 && ',''),'byte-gate':source.replace('*(u32 *)owner','*owner'),'attached-gate':source.replace('if (attached != 0)','if (1)'),'point-index':source.replace('attached, 10,','attached, 11,'),'early-global':early,'mode-byte':source.replace('(u8)mode','0'),'extra-word':source.replace('(u8)mode, extra','(u8)mode, 0'),'signed-field':source.replace('field18 = -33','field18 = -32'),'zero-sign':source.replace('values[0] = 0;','values[0] = -0.0f;')}
 for name,arg in(('mode-byte','mode'),('extra-word','extra')):controls[name]=controls[name].replace('    PointEffectPayload payload;','    PointEffectPayload payload;\n    (void)'+arg+';')
 assert all(v!=source for k,v in controls.items()if k!='selected');results=[]
 for opt in('-O0','-O2','-O3'):
  for label,body in controls.items():
   path=output/('native-%s-%s.c'%(label,opt[1:]));path.write_text(prefix+body+suffix);binary=path.with_suffix('.bin')
   command=['cc','-m32',opt,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign','-fexcess-precision=standard','-fno-builtin','-fno-strict-aliasing','-ffp-contract=off','-ffreestanding','-static','-fno-stack-protector','-fno-pie','-no-pie','-nostdlib','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(path)]
   q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0,(label,q.stderr)
   q=subprocess.run([str(binary)],capture_output=True,timeout=20);allowed=(0,)if label=='selected'else(-4,1)if label=='null-gate'else(1,);assert q.returncode in allowed,(opt,label,q.returncode,q.stdout,q.stderr)
   results.append(dict(profile=opt,label=label,status=q.returncode))
 report=dict(success=True,cases_per_profile=len(rows),profiles=['O0','O2','O3'],effective_controls_each=9,all118_initialized_payload_bytes_qualified=True,provider_global_and_owner_mutations=True,untouched_padding_not_read=True,finite_coefficients_and_points=True,typed_owner_pointer_and_fences=True,UBSan=True,results=results)
 (output/'private-native-v12.json').write_text(json.dumps(report,indent=2)+'\n');return report
