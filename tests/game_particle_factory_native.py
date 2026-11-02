"""Native32 factory protocol: defined fields, live input, aliasing copy tail and fences."""
import itertools,json,struct,subprocess

def qualify(root,output,source,headers,g):
 g.configure(root,output)
 old=g.old
 def get(data,at,n=4):return int.from_bytes(data[at:at+n],'big')
 def si(v,n=4):return v-(1<<(8*n))if v>>(8*n-1)else v
 def fl(v):
  value=old.floating(v);assert __import__('math').isfinite(value)
  return value.hex()+'f'
 def input_literal(p):
  fields=['.baseCount=(s32)0x%Xu'%get(p,0),'.countRange=(s32)0x%Xu'%get(p,4),'.position={'+','.join(fl(get(p,8+4*i))for i in range(3))+'}']
  for name,at in(('field14',0x14),('field16',0x16),('field18',0x18),('field1A',0x1A),('lifetimeBase',0x30),('lifetimeRange',0x32),('field72',0x72),('field74',0x74)):fields.append('.%s=%d'%(name,si(get(p,at,2),2)))
  fields+=['.parameters={'+','.join(fl(get(p,0x1C+4*i))for i in range(5))+'}', '.values={'+','.join(fl(get(p,0x40+4*i))for i in range(10))+'}', '.colors={'+','.join(str(x)for x in p[0x68:0x70])+'}', '.field70=%d'%p[0x70],'.field71=%d'%p[0x71],'.padding76={%d,%d}'%(p[118],p[119])]
  for name,at in(('field34',0x34),('field38',0x38),('field3C',0x3C)):fields.append('.%s=(s32)0x%Xu'%(name,get(p,at)))
  return'{'+','.join(fields)+'}'
 def descriptor_literal(p):
  fields=[]
  for name,at in(('flags',0),('field1',1),('field2',2),('field2C',44),('field2D',45),('field38',56),('field40',64),('field41',65)):fields.append('.%s=%d'%(name,p[at]))
  for name,at in(('field3',3),('field4',4)):fields.append('.%s=%d'%(name,si(p[at],1)))
  for name,at in(('lifetime',6),('field54',84),('field56',86)):fields.append('.%s=%d'%(name,si(get(p,at,2),2)))
  for name,at in(('field8',8),('fieldC',12),('field10',16),('field14',20),('field18',24),('field1C',28),('field20',32),('field24',36),('field28',40),('field3C',60)):fields.append('.%s=0x%Xu'%(name,get(p,at)))
  fields+=['.colors={{'+','.join(str(x)for x in p[48:52])+'},{'+','.join(str(x)for x in p[52:56])+'}}','.position={'+','.join(fl(get(p,68+4*i))for i in range(3))+'}']
  return'{'+','.join(fields)+'}'
 rows=[]
 corpus=[(old.Case(seed=seed,mutation=m,mode=(0,255,0x80000000,0xFFFFFFFF)[seed],extra=(0,1,0x80000000,0xFFFFFFFF)[seed]),empty)for seed,m,empty in itertools.product(range(4),(0,1,2,3,8,11,16,17,18,19,24,27),(False,True))]
 corpus.extend((old.Case(seed=mode%4,mode=0x87650000|mode,extra=old.U32(mode*0x87654321),mutation=(0,1,2,3,8,11,16,17,18,19,24,27)[mode%12]),False)for mode in range(256))
 for c,empty in corpus:
  memory,packet=g.fixture(c,empty);after=g.live_packet(packet,c);_,calls,spawns,_=g.expected(memory,packet,c)
  vectors=[args for t,args in calls if t==old.VECTOR];allocs=[args for t,args in calls if t==g.ALLOC];wanted=[]
  for index,(args,desc,state)in enumerate(spawns):
   post_property=state[48]^(0x55 if c.mutation&2 else 0);post_flags=desc[0]^(0x20 if c.mutation&1 else 0)
   vector=vectors[index];wanted.append('{'+descriptor_literal(desc)+',{'+','.join('0x%Xu'%get(state,4*i)for i in range(12))+'},%d,%d,%d,{%s},0x%Xu,0x%Xu}'%(state[48],post_property,post_flags,','.join('0x%Xu'%v for v in vector[:3]),args[2],args[3]))
  wanted_literal='{'+','.join(wanted)+'}'if wanted else'{{.descriptor={0}}}'
  rows.append('{%du,%du,0x%Xu,0x%Xu,%du,%du,%du,%du,%s,%s,%s}'%(c.seed,c.mutation,c.mode,c.extra,len(spawns),sum(t==old.INTEGER for t,_ in calls),sum(t==old.FLOAT for t,_ in calls),len(vectors),input_literal(packet),input_literal(after),wanted_literal))
 prefix='typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n'+'\n'.join(headers.splitlines()[1:])+r'''
struct Wanted{ParticleSpawnDescriptor descriptor;u32 words[12],property,post_property,post_flags,vector[3],extra2,scale;};
struct Case{u32 seed,mutation,mode,extra,count,integers,reals,vectors;ParticleFactoryInput before,after;struct Wanted wanted[15];};
static const struct Case cases[]={ROWS};
struct Fence{u32 pre[4];ParticleFactoryInput input;u32 post[4];};
static struct Fence packet,expected;
static const struct Case *current;
static u32 ints,reals,vectors,spawns,bad;
static u8 child[512];
static u32 ub(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
static u32 word(const u8 *p){u32 x;u8 *d=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=p[i];return x;}
__attribute__((noipa)) s32 func_150ADA20(void){static const u32 values[4]={0,1,255,0xFFFFFFFFu};u32 n=ints++;
 if(n==0&&(current->mutation&16))packet.input=current->after;
 return (s32)values[(n+current->seed)%4];
}
__attribute__((noipa)) f32 func_150ADA68(void){static const f32 values[4]={0.,.25,.5,.75};return values[(reals+++current->seed)%4];}
__attribute__((noipa)) void func_15143794(s16 first,s16 second,f32 radius,f32 *out){u32 n=vectors++;
 if(n>=current->count){bad=1;out[0]=out[1]=out[2]=0.;return;}
 if((u32)(s32)first!=current->wanted[n].vector[0]||(u32)(s32)second!=current->wanted[n].vector[1]||ub(radius)!=current->wanted[n].vector[2])bad=1;
 out[0]=(f32)first*.125f;out[1]=(f32)second*.25f;out[2]=radius*.5f;
}
__attribute__((noipa)) s32 func_15157898(s32 raw,void *whole,s32 extra2,f32 scale,s32 a4,s32 a5,u8 *a6,u8 mode,s32 extra){
 u32 i,n=spawns++;ParticleSpawnDescriptor *d=(ParticleSpawnDescriptor*)(u32)raw;ParticleSpawnState *state=(ParticleSpawnState*)whole;const struct Wanted *w;u8 *bytes=(u8*)whole,*actual=(u8*)d,*wanted;
 if(n>=current->count){bad=1;return 0;}w=&current->wanted[n];wanted=(u8*)&w->descriptor;
 if((u8*)d-bytes!=52||a4||a5||a6||mode!=(current->mode&255)||(u32)extra!=current->extra||(u32)extra2!=w->extra2||ub(scale)!=w->scale)bad=1;
 for(i=0;i<88;i++){
  if(i==5||i==46||i==47||i==57||i==58||i==59||i==66||i==67||(i>=80&&i<84))continue;
  if(actual[i]!=wanted[i])bad=1;
 }
 for(i=0;i<12;i++)if(word(bytes+4*i)!=w->words[i])bad=1;
 if(state->property!=w->property)bad=1;
 for(i=0;i<4;i++)if(bytes[52+i]!=actual[i])bad=1;
 if(current->mutation&1)d->flags^=0x20;
 if(current->mutation&2)state->property^=0x55;
 if(current->mutation&8){state->padding31[0]=0xD1;state->padding31[1]=0xD2;state->padding31[2]=0xD3;d->padding5=0xEF;}
 if(state->property!=w->post_property||d->flags!=w->post_flags)bad=1;
 if((n+1)%3==current->seed%3)return 0;
 for(i=0;i<512;i++)child[i]=(u8)(i*37+current->seed*7+91);
 /* Guest execution checks all 56 bytes; native checks defined fields only. */
 for(i=0;i<56;i++){if(i>=49&&i<52&&!(current->mutation&8))continue;child[0x120+i]=bytes[i];}
 for(i=0;i<12;i++)if(word(child+0x120+4*i)!=w->words[i])bad=1;
 if(child[0x150]!=w->post_property||child[0x154]!=w->post_flags||child[0x155]!=d->field1||child[0x156]!=d->field2||child[0x157]!=(u8)d->field3)bad=1;
 if((current->mutation&8)&&(child[0x151]!=0xD1||child[0x152]!=0xD2||child[0x153]!=0xD3))bad=1;
 for(i=0;i<512;i++)if((i<0x120||i>=0x158)&&child[i]!=(u8)(i*37+current->seed*7+91))bad=1;
 return (s32)child;
}
'''.replace('ROWS',','.join(rows))
 suffix=r'''
static void(*volatile invoke)(ParticleFactoryInput*,u8,s32)=func_15152520;
int run(void){u32 i,j;u8 *a=(u8*)&packet,*b=(u8*)&expected;
 if(sizeof(void*)!=4||sizeof(ParticleFactoryInput)!=120||sizeof(ParticleSpawnDescriptor)!=88||sizeof(ParticleSpawnState)!=52||sizeof(ParticleSpawnScratch)!=140||__builtin_offsetof(ParticleSpawnScratch,descriptor)!=52)return 9;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];for(j=0;j<sizeof(packet);j++)a[j]=(u8)(j*29+i*13+90);
  packet.input=current->before;for(j=0;j<sizeof(packet);j++)b[j]=a[j];expected.input=current->after;
  ints=reals=vectors=spawns=bad=0;invoke(&packet.input,(u8)current->mode,(s32)current->extra);
  if(bad||spawns!=current->count||ints!=current->integers||reals!=current->reals||vectors!=current->vectors)return 1;
  for(j=0;j<sizeof(packet);j++)if(a[j]!=b[j])return 1;
 }
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
 early=source.replace('    u32 remaining;','    u32 remaining;\n    u32 earlyBase, earlyRange;').replace('    remaining = (u32)func_150ADA20();','    earlyBase = input->baseCount; earlyRange = input->countRange;\n    remaining = (u32)func_150ADA20();').replace('(u32)input->countRange','earlyRange').replace('(u32)input->baseCount','earlyBase')
 controls={'selected':source,'unsigned-RNG':source.replace('(u32)func_150ADA20()','((u32)func_150ADA20() & 0x7FFFFFFFU)'),'count':source.replace('(u32)input->baseCount','((u32)input->baseCount + 1U)'),'lifetime':source.replace('input->lifetimeBase','(input->lifetimeBase + 1)'),'angle':source.replace('360.0f','180.0f'),'property':source.replace('input->field71','input->field70'),'second-color':source.replace('&input->colors[4]','&input->colors[0]'),'radius':source.replace('input->values[3]','input->values[1]'),'extra':source.replace('(u8)mode, extra','(u8)mode, 0'),'early-count':early,'allocation-failure':source.replace('        func_15157898(','        if (func_15157898(').replace('(u8)mode, extra);','(u8)mode, extra) == 0) return;')}
 controls['extra']=controls['extra'].replace('    u32 remaining;','    u32 remaining;\n    (void)extra;')
 assert all(v!=source for n,v in controls.items()if n!='selected');results=[]
 for opt in('-O0','-O2','-O3'):
  for label,body in controls.items():
   path=output/('native-%s-%s.c'%(label,opt[1:]));path.write_text(prefix+body+suffix);binary=path.with_suffix('.bin')
   command=['cc','-m32',opt,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign','-fexcess-precision=standard','-fno-builtin','-fno-strict-aliasing','-ffp-contract=off','-ffreestanding','-static','-fno-stack-protector','-fno-pie','-no-pie','-nostdlib','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(path)]
   q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0,(label,q.stderr[-8000:])
   q=subprocess.run([str(binary)],capture_output=True,timeout=20);assert q.returncode==(0 if label=='selected'else 1),(opt,label,q.returncode,q.stdout,q.stderr)
   results.append(dict(profile=opt,label=label,status=q.returncode))
 report=dict(success=True,cases_per_profile=len(rows),profiles=['O0','O2','O3'],effective_controls_each=10,typed_complete_scratch_140_bytes=True,defined_descriptor_76_state_49_bytes_checked=True,copy_tail_alias_first_descriptor_word=True,uninitialized_padding_not_read=True,live_input_mutation_after_first_RNG=True,pre_RNG_cached_fields_remain_old=True,allocation_success_failure_and_descriptor_state_mutations=True,all256_mode_bytes=True,finite_intermediate_domain=True,UBSan=True,results=results)
 (output/'private-native-v12.json').write_text(json.dumps(report,indent=2)+'\n');return report
