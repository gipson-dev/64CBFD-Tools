"""SDK32 alternate point effect checks with sequenced provider effects."""
import itertools,subprocess,types
from tools.experiments import game_alternate_point_effect_triple_match as match
from tools.tests import game_alternate_point_effect_triple_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run(state):
 root,p=match.ROOT,match.OUT
 env=dict(vars(oracle))
 env['reference']=types.FunctionType(oracle.reference.__code__,env)
 g=env['g'];put=env['put'];read=env['read'];bits=g.bits
 # Native helpers do not modify the caller's argument-home words.
 def native_provider(m,c,h,p,r):
  if c.mutation&4:put(m,c.actor+0x40,bits(19.5));put(m,env['SCALE'][c.kind],bits(.25));put(m,r+0x18,0x13579bdf);put(m,p,bits(4.25))
 def native_emit(m,c,h,p,r):
  if c.mutation&8:put(m,r+0x18,0x76543210);put(m,p,bits(-17.5))
 env['provider_effect']=native_provider;env['emit_effect']=native_emit
 functions=[match.MANIFEST['bodies'][n] for n in env['NAMES']]
 controls=[]
 for kind,f in enumerate(functions):
  options={'gate':('== 0) return','!= 0) return'),'selector':('&result, selected) != 0','&result, selected) == 0'),'scale':('(f32)amount * D_800A57','(f32)(amount + 1) * D_800A57'),'threshold':('amount >= 115','amount > 115'),'mode':('position, selected);','position, selected + 1);')}
  for label,(a,b) in options.items():assert f.count(a)==1,(kind,label);controls.append((kind,label,f.replace(a,b,1)))
 rows=[]
 for kind,mode,active,answer,amount,mut,ret in itertools.product(range(3),(0,1,2,3,7,255,0xabcd0001,0xabcd00ff),(0,1),(0,1),(114,115,130),(0,1,4,8,16),(0,255,0x12345678)):
  c=env['Case'](kind=kind,mode=mode,active=0x50000 if active else 0,answer=answer,amount=amount,mutation=mut,provider_return=ret,value=bits(12.5));_,calls,obs=env['reference'](env['fixture'](c),c);events=[];extra=(0,0,0,0);emit=(0,0,0,0,0)
  for target,args in calls:
   events.append(1 if target==env['SELECT'] else 2 if target==env['EXTRA'] else 5 if target==env['EMIT'] else 4 if target==env['ALT'] else 3)
   if target==env['EXTRA']:
    ob=next(o for o in obs if o[0]==target);extra=(args[0],args[2],int.from_bytes(ob[1][0:4],'big'),int.from_bytes(ob[1][4:8],'big'))
   if target==env['EMIT']:
    ob=next(o for o in obs if o[0]==target);emit=(args[0],args[2],args[3],int.from_bytes(ob[2][0:4],'big'),int.from_bytes(ob[2][4:8],'big'))
  rows.append((kind,mode,active,answer,amount,mut,ret,events,extra,emit))
 code="#include <ultra64.h>\ntypedef struct HeightResult71820 { f32 height; s16 vertices[9]; s16 pad16; u32 metadata; u8 flags; u8 state; u16 pad1e; s32 value; } HeightResult71820;\nextern f32 D_800A573C,D_800A5740,D_800A5744,D_800A5748,D_800A574C,D_800A5750;\nextern s32 (*D_8008FD04)(void),(*D_8008FD1C)(void),(*D_8008FD30)(void);\ns32 func_15146890(f32 *,u8 *,HeightResult71820 *,u8);\nvoid func_15141F78(u8,u8 *,f32,u8,f32 *,u8);\nvoid func_15142180(u8,f32 *,s32,f32,f32);\n"
 code+=r'''
 _Static_assert(sizeof(void*)==4 && sizeof(HeightResult71820)==36 && __builtin_offsetof(HeightResult71820,metadata)==24,"SDK32 layout");
 typedef struct {u32 kind,mode,active,answer,amount,mut,ret,n,events[4],extra[4],emit[5];} Row;
 static const Row rows[]={
 '''
 arr=lambda seq:','.join('0x%08Xu'%v for v in seq)
 for kind,mode,active,answer,amount,mut,ret,events,extra,emit in rows:code+='{'+arr((kind,mode,active,answer,amount,mut,ret,len(events)))+', {'+arr(events+[0]*(4-len(events)))+'}, {'+arr(extra)+'}, {'+arr(emit)+'}},\n'
 code+=r'''};
 f32 D_800A573C,D_800A5740,D_800A5744,D_800A5748,D_800A574C,D_800A5750;
 s32 (*D_8008FD04)(void),(*D_8008FD1C)(void),(*D_8008FD30)(void);
 static union {u32 align;u8 bytes[0x340];} actor;static const Row *row;static u32 calls,errors;static f32 *lastPosition;static HeightResult71820 *lastResult;
 static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}static f32 val(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
 static void event(u32 code){if(calls>=row->n||row->events[calls]!=code)errors++;calls++;}
 static f32 *scale(void){return row->kind==0?&D_800A573C:row->kind==1?&D_800A5744:&D_800A574C;}
 static f32 *tag(void){return row->kind==0?&D_800A5740:row->kind==1?&D_800A5748:&D_800A5750;}
 static s32 provider_alt(void);static void set_alt(void){if(row->kind==0)D_8008FD04=provider_alt;else if(row->kind==1)D_8008FD1C=provider_alt;else D_8008FD30=provider_alt;}
 static s32 provide(u32 id){event(id);if(row->mut&4){*(f32*)(actor.bytes+0x40)=19.5f;*scale()=.25f;lastResult->metadata=0x13579bdf;lastPosition[0]=4.25f;}return (s32)row->ret;}
 static s32 provider_orig(void){return provide(3);}static s32 provider_alt(void){return provide(4);}
 s32 func_15146890(f32 *p,u8*a,HeightResult71820*r,u8 mode){event(1);if(a!=actor.bytes||mode!=(u8)row->mode)errors++;lastPosition=p;lastResult=r;p[0]=1.25f;p[1]=-2.5f;p[2]=3.75f;r->metadata=0xe9062340;
  if(row->mut&1){*(f32*)(actor.bytes+0x40)=27.5f;*scale()=.5f;*tag()=2.f;set_alt();}return row->answer;}
 void func_15141F78(u8 slot,u8*src,f32 x,u8 value,f32*p,u8 mode){event(5);if(src!=(u8*)lastResult||p!=lastPosition||mode!=(u8)row->mode||slot!=row->emit[0]||word(x)!=row->emit[1]||value!=row->emit[2]||word(p[0])!=row->emit[3]||word(p[1])!=row->emit[4])errors++;
  if(row->mut&8){lastResult->metadata=0x76543210;p[0]=-17.5f;}}
 void func_15142180(u8 slot,f32*p,s32 metadata,f32 width,f32 height){event(2);if(p!=lastPosition||slot!=row->extra[0]||(u32)metadata!=row->extra[1]||word(p[0])!=row->extra[2]||word(p[1])!=row->extra[3]||word(width)!=0x3f800000||word(height)!=0x3f800000)errors++;
  if(row->mut&16){set_alt();lastResult->metadata=0x2468ace0;p[1]=12.5f;}}
 '''
 for i,fn in enumerate(functions):code+='\n'+fn.replace(env['NAMES'][i],'test_selected_%d'%i,1)+'\n'
 for kind,label,fn in controls:code+='\n'+fn.replace(env['NAMES'][kind],'test_%s_%d'%(label,kind),1)+'\n'
 code+=r'''
 typedef void(*Fn)(u8*,s32,s32);static int check(Fn fn,u32 kind){u32 i,j;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){row=&rows[i];if(row->kind!=kind)continue;for(j=0;j<sizeof(actor.bytes);j++)actor.bytes[j]=0;*(u32*)(actor.bytes+0x1d4)=row->active;*(f32*)(actor.bytes+0x40)=12.5f;
  D_800A573C=D_800A5744=D_800A574C=val(0x3bfc0fc1);D_800A5740=D_800A5748=D_800A5750=val(0x3f360b61);D_8008FD04=D_8008FD1C=D_8008FD30=provider_orig;calls=errors=0;
  fn(actor.bytes,(s32)row->mode,(s32)row->amount);if(errors||calls!=row->n)return 1;}return 0;}
 static int run(void){
 '''
 for i in range(3):code+='if(check(test_selected_%d,%d))return %d;\n'%(i,i,i+1)
 for j,(kind,label,_) in enumerate(controls):code+='if(!check(test_%s_%d,%d))return %d;\n'%(label,kind,kind,20+j)
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=p/'native.c';path.write_text(code);results={}
 for opt in ('-O0','-O2','-O3'):
  out=p/('native'+opt);z=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(out)],cwd=root,capture_output=True,text=True);assert z.returncode==0,(opt,z.stdout,z.stderr)
  z=subprocess.run([str(out)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr);results[opt]=dict(cases=len(rows),per_target=len(rows)//3,negative_controls=len(controls),UBSan=True)
 return results
