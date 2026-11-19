"""Actual SDK32 C checked against independent serialized provider snapshots."""
from dataclasses import replace
import subprocess
from tools.experiments import game_ground_explosion_15103e40_match as match
from tools.tests import game_ground_explosion_15103e40_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native_checks(out):
    rows=[];values=lambda a:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in a)+'}'
    for c in g.cases():
        if c.phase or c.mutation&16:continue
        initial=g.fixture(c);memory,calls,snaps,returns=g.reference(initial,c)
        alternate=[0]*12
        if any(t==g.GROUND for t,_ in calls):
            reverse=replace(c,integers=(c.integers[1],c.integers[0],*c.integers[2:]))
            other,other_calls,other_snaps,_=g.reference(initial,reverse)
            assert other==memory and other_snaps==snaps
            assert [(t,a)for t,a in other_calls if t!=g.GROUND]==[(t,a)for t,a in calls if t!=g.GROUND]
            alternate=list(next(a for t,a in other_calls if t==g.GROUND))
        pads=17-len(calls);targets=[t for t,_ in calls]+[0]*pads;counts=[len(a)for _,a in calls]+[0]*pads
        arguments=[[*a,*([0]*(12-len(a)))]for _,a in calls]+[[0]*12]*pads
        snapshots=[v for _,v in snaps]+[(0,)*20]*pads;seen=[s for s,_ in snaps]+[0]*pads
        row=[values(c.position),values(g.vector(memory,g.POSITION)),values(targets),values(counts),
             '{'+','.join(values(a)for a in arguments)+'}',values(alternate),values(seen),'{'+','.join(values(a)for a in snapshots)+'}',values(returns+[0]*pads),
             *('0x%Xu'%(v&0xFFFFFFFF)for v in(c.source,c.ground_context,c.mode,c.detail,c.slot,c.context,c.hit,c.flags,c.height,c.move_probe,c.mutation,c.stages,len(calls)))]
        rows.append('{'+','.join(row)+'},')
    harness=r'''
typedef char Layout[(sizeof(void*)==4&&sizeof(struct17)==12&&sizeof(ExplosionGround1312F0)==36&&
 __builtin_offsetof(ExplosionGround1312F0,flags)==28&&__builtin_offsetof(ExplosionGround1312F0,vertices)==4)?1:-1];
typedef struct {u32 initial[3],expected[3],targets[17],counts[17],args[17][12],groundAlternative[12],seen[17],snapshots[17][20],returns[17],
 source,groundContext,mode,detail,slot,context,hit,flags,height,moveProbe,mutation,stages,calls;} Row;
static const Row rows[]={ROWS};
static const Row *row;
static struct17 position;
static u32 sourceObject[4],contextObject[4],otherSource[4],otherContext[4];
static ExplosionGround1312F0 *ground;
static struct17 *probe,*contact;
static u32 called,error,exposed;
static void store(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8));}
static u32 load(const u8*p){u32 i,v=0;for(i=0;i<4;i++)v|=(u32)p[i]<<(i*8);return v;}
static void store16(u8*p,u32 v){p[0]=(u8)v;p[1]=(u8)(v>>8);}
static u32 word(f32 f){return load((const u8*)&f);}
static f32 real(u32 v){f32 f;store((u8*)&f,v);return f;}
static void vector(struct17*p,u32 a,u32 b,u32 c){store((u8*)p,a);store((u8*)p+4,b);store((u8*)p+8,c);}
static u32 pointer(u32 v){
 if(!v)return 0;if(v==0x30000)return(u32)&position;
 if(v==0x70000)return(u32)sourceObject;if(v==0x60000)return(u32)contextObject;
 if(v==0x71000)return(u32)otherSource;if(v==0x61000)return(u32)otherContext;
 if(v==FRAME+0x58)return(u32)ground;if(v==FRAME+0x5C)return(u32)ground+4;
 if(v==FRAME+0x7C)return(u32)probe;if(v==FRAME+0x8C)return(u32)contact;
 error=2;return 0;
}
static int pointerArgument(u32 t,u32 i){
 if(t==0x1504715C)return i<2;
 if(t==0x15046C80)return i==0||i==3;
 if(t==0x150E7FEC)return i==2||i==3;
 if(t==0x151D40D4)return i<4;
 return i==0&&(t==0x151D3FF4||t==0x150E83AC||t==0x151D5404||t==0x151D5334||t==0x151D5514||t==0x151541B8);
}
static int snapshotEqual(const u32*v,u32 mask){
 u32 i,n=0,a[20];for(i=0;i<20;i++)a[i]=0;
 for(i=0;i<3;i++)a[n++]=load((u8*)&position+i*4);
 if(exposed&1){a[n]=load((u8*)ground);a[n+1]=ground->flags;
  for(i=0;i<9;i++)a[n+2+i]=(u32)((u8*)ground->vertices)[i*2]|(u32)((u8*)ground->vertices)[i*2+1]<<8;}
 n+=11;
 if(exposed&2)for(i=0;i<3;i++)a[n+i]=load((u8*)probe+i*4);n+=3;
 if(exposed&4)for(i=0;i<3;i++)a[n+i]=load((u8*)contact+i*4);
 if(mask!=exposed)return 0;for(i=0;i<20;i++)if(a[i]!=v[i])return 0;return 1;
}
static __attribute__((noinline,noclone)) u32 observe(u32 target,const u32*args,u32 count){
 u32 i,n=called++,mutation=(row->stages>>n&1)?row->mutation:0,result,ordinary=1,alternative=1;
 if(n>=row->calls||n>=17){error=3;return 0;}
 if(target!=row->targets[n]||count!=row->counts[n]||!snapshotEqual(row->snapshots[n],row->seen[n]))error=4;
 for(i=0;i<count;i++){
  if(args[i]!=(pointerArgument(target,i)?pointer(row->args[n][i]):row->args[n][i]))ordinary=0;
  if(target==0x150E7FEC&&args[i]!=(pointerArgument(target,i)?pointer(row->groundAlternative[i]):row->groundAlternative[i]))alternative=0;
 }
 if(!ordinary&&(target!=0x150E7FEC||!alternative))error=5;
 result=row->returns[n];
 if(target==0x1504715C){for(i=0;i<36;i++)((u8*)ground)[i]=(u8)(i*13+0xA7);
  store((u8*)ground,row->height);ground->flags=(u8)row->flags;
  for(i=0;i<9;i++)store16((u8*)ground->vertices+i*2,0x8000+i*0x1234);exposed|=1;}
 if(target==0x15046C80){store((u8*)ground,row->height);ground->flags=(u8)row->flags;
  if(row->moveProbe)vector(probe,word(17.25f),word(25.5f),word(-31.75f));}
 if(mutation&1)vector(&position,word(-17.5f+n),word(80.25f-n),word(0.75f+n));
 if((mutation&2)&&(exposed&1)){store((u8*)ground,word(-3.25f+n));ground->flags^=1;
  for(i=0;i<9;i++){u8*p=(u8*)ground->vertices+i*2;u32 v=(u32)p[0]|(u32)p[1]<<8;store16(p,v^(n+i+1));}}
 if((mutation&4)&&(exposed&2))vector(probe,word(30.5f+n),word(-1.25f-n),word(60.75f+n));
 if((mutation&8)&&(exposed&4))vector(contact,word(-60.5f-n),word(4.25f+n),word(2.75f-n));
 return result;
}
void func_151D3FF4(struct17*p,u8 s,s32 c){u32 a[]={(u32)p,s,(u32)c};observe(0x151D3FF4,a,3);}
void func_1504715C(ExplosionGround1312F0*p,void*c){u32 a[]={(u32)p,(u32)c};ground=p;observe(0x1504715C,a,2);}
s32 func_15046C80(struct17*p,u16 zero,f32 bottom,ExplosionGround1312F0*r){u32 a[]={(u32)p,zero,word(bottom),(u32)r};probe=p;exposed|=2;return(s32)observe(0x15046C80,a,4);}
f32 func_150ADA68(void){return real(observe(0x150ADA68,0,0));}
s32 func_150ADA20(void){return(s32)observe(0x150ADA20,0,0);}
void func_150E7FEC(f32 f,u8 b,s16*v,struct17*p,u32 life,s32 a,s32 c,s32 d,s32 e,s32 h,u8 slot,s32 context){
 u32 args[]={word(f),b,(u32)v,(u32)p,life,(u32)a,(u32)c,(u32)d,(u32)e,(u32)h,slot,(u32)context};
 contact=p;exposed|=4;observe(0x150E7FEC,args,12);}
void func_150E83AC(struct17*p,s16 n,u8 s,s32 c){u32 a[]={(u32)p,(u32)(s32)n,s,(u32)c};observe(0x150E83AC,a,4);}
void func_151D5404(struct17*p,f32 a,f32 b,f32 c,s16 d,s16 e,u8 s,s32 context){
 u32 args[]={(u32)p,word(a),word(b),word(c),(u32)(s32)d,(u32)(s32)e,s,(u32)context};observe(0x151D5404,args,8);}
void func_151D5334(struct17*p,f32 a,f32 b,f32 c,u8 d,u8 s,s32 context){
 u32 args[]={(u32)p,word(a),word(b),word(c),d,s,(u32)context};observe(0x151D5334,args,7);}
void func_151D5514(struct17*p,u8 s,s32 c){u32 a[]={(u32)p,s,(u32)c};observe(0x151D5514,a,3);}
void func_151D40D4(struct17*p,struct17*q,void*s,void*g,s32 a,s32 b,s32 c,s32 d){
 u32 args[]={(u32)p,(u32)q,(u32)s,(u32)g,(u32)a,(u32)b,(u32)c,(u32)d};observe(0x151D40D4,args,8);}
void func_15055A2C(s32 a,f32 x,f32 y,f32 z,s32 b){u32 args[]={(u32)a,word(x),word(y),word(z),(u32)b};observe(0x15055A2C,args,5);}
u8*func_151541B8(struct17*p,f32 a,f32 b,f32 c,f32 d,u8 s,s32 context){
 u32 args[]={(u32)p,word(a),word(b),word(c),word(d),s,(u32)context};observe(0x151541B8,args,7);return 0;}
static int run(void){u32 i,j;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){row=&rows[i];vector(&position,row->initial[0],row->initial[1],row->initial[2]);
  ground=0;probe=contact=0;called=error=exposed=0;
  func_15103E40((void*)pointer(row->source),(void*)pointer(row->groundContext),&position,(u8)row->mode,(s32)row->detail,(u8)row->slot,(s32)row->context);
  if(error||called!=row->calls)return 1;
  for(j=0;j<3;j++)if(load((u8*)&position+j*4)!=row->expected[j])return 1;
 }return 0;
}
'''.replace('ROWS','\n'.join(rows)).replace('FRAME','0x%Xu'%g.frame(g.STACK))
    changes={
        'source_gate':('source != NULL','source == NULL'),
        'bottom_reload':('position->unk4 - 100.0f','position->unk4 - 99.0f'),
        'contact_mask':('ground.flags & 1','ground.flags & 2'),
        'sample_scale':('sample * 125.0f','sample * 124.0f'),
        'random_modulus':('% 101U','% 100U'),
        'ground_context_zero':('0, 1, 0, 0, 0, slot, 0)','0, 1, 0, 0, 0, slot, context)'),
        'mode_effect':('firstEffect = 0x42','firstEffect = 0x43'),
        'particle_count':('15, 20, slot','14, 20, slot'),
        'final_size':('sample * 4.0f + 12.0f','sample * 4.0f + 13.0f'),
    }
    controls={n:match.SELECTED.replace(a,b)for n,(a,b)in changes.items()};assert all(body!=match.SELECTED for body in controls.values())
    profiles=[]
    for opt in('-O0','-O2','-O3'):
        for name,body in[('selected',match.SELECTED),*controls.items()]:
            source=out/('native'+opt+'-'+name+'.c');exe=source.with_suffix('')
            source.write_text(body+harness+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
            result=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fsanitize=float-cast-overflow',str(source),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True)
            if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30)
            assert result.returncode==(0 if name=='selected'else 1),(opt,name,result.returncode,result.stderr[:200])
        profiles.append(dict(profile=opt,cases=len(rows),effective_source_controls=len(controls),UBSan=True,float_cast_overflow=True,strict_aliasing=True))
    return dict(profiles=profiles,actual_selected_source=True,independent_serialized_reference=True,
                helper_retained_addresses_used_only_during_root_lifetime=True,guest_only_home_mutations_excluded=True,
                C_argument_order='two complete ground payload alternatives for the two integer RNG arguments',
                exact_IDO_random_order_qualified_separately_by_guest=True)
