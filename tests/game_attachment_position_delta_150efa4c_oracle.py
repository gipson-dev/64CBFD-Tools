"""Attachment snapshots, live matrix/coordinate rereads and registered callback."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read,PointOracle,CONVERT,TRANSFORM,TRANSLATE
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,POINT=0x150EFA4C,0x15143134
EFFECT,LINK,SOURCE,OWNER,ALT,MATRIX=0x30000,0x40000,0x50000,0x60000,0x70000,0x90000
STATUS,DIAGNOSTIC,FLAG=0x800DCA00,0x800DCA04,0x800C3E90
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    gate:int=1
    matrix:int=MATRIX
    index:int=0
    selector:int=3
    status:int=0xA5
    mutation:int=0
    phase:int=0
    seed:int=0
    alias:int=0
    point_zero:bool=False
def symbols(index=0):
    bases=(0x800A1620,0x02337FF8,0x0343FFF8)
    return dict(D_800A1620=bases[index],D_800A1638=bases[index]+24,
                func_15143134=(POINT,0x17F08000,0x1EF0FFFC)[index])
def locations(c,s):
    s=dict(s);source=SOURCE;owner=OWNER
    if c.alias in(1,2,3):source=EFFECT+{1:-4,2:0,3:-8}[c.alias]
    if c.alias==4:owner=EFFECT+0x30-0x1D4
    if c.alias==5:s['D_800A1638']=EFFECT+0x30-c.index
    if c.alias==7:owner=EFFECT+0x54-0x1D4
    if c.alias==8:source=EFFECT+0x1C-0x128
    return source,owner,s
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def fixture(c=Case(),s=None):
    base=symbols()if s is None else s;source,owner,s=locations(c,base)
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
    for p,n in((EFFECT,768),(ALT,768),(LINK,64),(source,512),(owner,512),
                (s['D_800A1620']-16,3104),(s['D_800A1638']-16,288),(STATUS-16,64),(FLAG,1)):
        for i in range(n):m.setdefault(u32(p+i),(i*29+c.seed*11+0x5A)&255)
    for effect in(EFFECT,ALT):
        for i,value in enumerate((1.25,-2.5,0.125,7.5,-9.25,3.75,13.25,-19.5,0.25)):
            put(m,effect+0x30+4*i,bits(value))
        m[effect+0x1C]=c.status&255
    for i,v in enumerate((2.5,-4.25,1.125,0.0,-0.0,0.25)):
        put(m,source+0x34+4*i,bits(v))
    # Preserve non-arithmetic payloads, including NaNs, in the copied rotation
    # and auxiliary fields. Only position components undergo subtraction.
    put(m,source+0x40,0x7FC12345);put(m,source+0x44,0x80000000);put(m,source+0x48,0xFFC54321)
    put(m,source+0x14C,0x7FA12345);put(m,source+0x150,0xFF800000)
    point=s['D_800A1620']+12*c.index
    for i,v in enumerate((0.,0.,0.)if c.point_zero else(2.25,-3.5,1.125)):put(m,point+4*i,bits(v))
    m[s['D_800A1638']+c.index]=c.selector&255
    put(m,EFFECT+0x60,LINK);put(m,LINK+8,source);put(m,source+0x110,owner)
    m[source+0x11D]=c.index&255;m[source+0x128]=c.gate&255;put(m,owner+0x1D4,c.matrix)
    put(m,STATUS,0x11223344);put(m,DIAGNOSTIC,0x55667788);m[FLAG]=0
    for i in range(3):put(m,STATUS+8+4*i,0x87654321+i)
    if c.matrix:
        p=u32(c.matrix+((c.selector&255)<<6))
        values=[0.0]*16
        for i in(0,5,10,15):values[i]=0.5
        values[12:15]=[3.25,-4.5,5.75]
        for i,v in enumerate(values):put(m,p+4*i,bits(v))
    return m,s
def point_observation(m,args):
    p,out,matrix=args;effect=u32(out-0x48)
    return tuple(args),data(m,p,12),data(m,effect+0x30,0x30),m[effect+0x1C]
def mutations(m,c,s,home,effect=EFFECT):
    source=read(m,read(m,effect+0x60)+8)
    if c.mutation&1:
        for i,v in enumerate((5.5,-7.25,0.5)):put(m,effect+0x30+4*i,bits(v))
    if c.mutation&2:m[effect+0x1C]^=0x5A
    if c.mutation&4:
        for i in range(6):put(m,source+0x34+4*i,0x41200000+i)
        m[source+0x11D]^=0xFF;put(m,effect+0x60,0xDEADBEEF)
    if c.mutation&8:put(m,home,ALT)
def homes(m,sp):
    for i in range(4):put(m,sp+4*i,0xB5000000+i)
def point_reference(m,args):
    point,out,matrix=args;values=[floating(read(m,point+4*i))for i in range(3)]
    put(m,STATUS,0)
    if any(v!=0. for v in values):
        for i in range(3):put(m,STATUS+8+4*i,read(m,point+4*i))
        put(m,DIAGNOSTIC,matrix);mat=[floating(read(m,matrix+4*i))for i in range(16)]
        x,y,z=values
        result=[bits(floating(bits(floating(bits(mat[i]*x))+floating(bits(mat[i+4]*y))))+
                     floating(bits(floating(bits(mat[i+8]*z))+mat[i+12])))for i in range(3)]
    else:result=[read(m,matrix+0x30+4*i)for i in range(3)]
    for i,v in enumerate(result):put(m,out+4*i,v)
def reference(initial,c=Case(),s=None,home=None,actual_point=False,ra=0xDEAD0000):
    s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home
    put(m,home-0x18+0x14,ra);calls=[];obs=[]
    source=read(m,read(m,EFFECT+0x60)+8);attachment=source+0x110
    if m[source+0x128]&1:
        owner=read(m,attachment)
        if read(m,owner+0x1D4):
            first=read(m,source+0x34);index=m[attachment+0xD];put(m,EFFECT+0x30,first)
            for i in range(1,6):put(m,EFFECT+0x30+4*i,read(m,source+0x34+4*i))
            put(m,EFFECT+0x54,read(m,attachment+0x3C));put(m,EFFECT+0x58,read(m,attachment+0x40))
            selector=m[s['D_800A1638']+index];matrix=read(m,owner+0x1D4)
            args=(s['D_800A1620']+12*index,EFFECT+0x48,u32(matrix+(selector<<6)))
            put(m,home,EFFECT);calls.append((s['func_15143134'],args));obs.append(point_observation(m,args))
            if actual_point:point_reference(m,args)
            else:
                for i,v in enumerate((13.25,-19.5,0.25)):put(m,args[1]+4*i,bits(v))
                mutations(m,c,s,home);homes(m,home-0x18)
            effect=read(m,home)
            # Independent scalar model: read each component after the provider.
            for i in range(3):
                value=bits(floating(read(m,effect+0x48+4*i))-floating(read(m,effect+0x30+4*i)))
                put(m,effect+0x48+4*i,value)
            m[effect+0x1C]|=2
            return m,calls,obs
    m[EFFECT+0x1C]&=0xFD
    return m,calls,obs

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=(EFFECT,))
        self.f=[u32(c.seed*0x9E3779B9+i*0x1020304)for i in range(32)];self.saved_f=self.f[20:]
        self.before=self.r[:];self.before_f=self.f[:];self.point_observations=[];self.mutate=False
    def record_call(self,t):
        if t==ENTRY:self.target_home=self.r[29];args=self.arguments(1)
        elif t==self.syms['func_15143134']:
            args=self.arguments(3);self.point_observations.append(point_observation(self.memory,args))
        else:
            assert t in(CONVERT,TRANSFORM,TRANSLATE),hex(t);args=self.arguments({CONVERT:2,TRANSFORM:7,TRANSLATE:3}[t])
        args=tuple(map(u32,args));self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        if t!=self.syms['func_15143134']:return PointOracle.hook(self,t)
        args=self.calls[-1][1]
        for i,v in enumerate((13.25,-19.5,0.25)):put(self.memory,args[1]+4*i,bits(v))
        mutations(self.memory,self.case,self.syms,self.target_home);homes(self.memory,self.r[29])
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xDEAD0000
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True
def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.point_observations)
def original_object(core,q,out):
    text=(out/'frozen/conker/asm/11C2B0.s').read_text();a=text.index('glabel '+core.FUNCTION);b=text.index('endlabel '+core.FUNCTION,a)+len('endlabel '+core.FUNCTION)
    p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+text[a:b]+'\n.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
    q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s=None):
    s=symbols()if s is None else s
    programs=[list(core.bound_blob(q[key],q[refs],s))for key,refs in(('original','original_refs'),('raw','refs'),('normal','normal_refs'))]
    assert programs[0]==programs[2]
    return programs
def cases():
    rows=[Case(gate=g,matrix=m,index=i,selector=b,mutation=mode,phase=p,seed=(i+mode)%8)
          for g,m,i,b,mode,p in itertools.product((0,1,2,0x81,255),(0,MATRIX,0x8000FFF0),(0,1,2,127,255),(0,255),(0,1,2,4,8,15),(0,8))]
    rows +=[Case(index=i,selector=255-i,mutation=i%16)for i in range(256)]
    rows +=[Case(gate=i,status=i,mutation=15)for i in range(256)]
    return rows
def guest(core,q):
    original_object(core,q,core.ROOT/core.BUILD);count=0;seen=set();rows=[(c,symbols(),ENTRY)for c in cases()]
    for i in(1,2):rows.extend((Case(gate=g,matrix=m,mutation=15,index=255),symbols(i),0x17007FFC if i==1 else 0x1F00FFFC)for g,m in itertools.product((0,1,255),(0,MATRIX)))
    for c,base,entry in rows:
        initial,s=fixture(c,base);wanted,calls,obs=reference(initial,c,s);models=[]
        for body in programs(core,q,s):
            m=Oracle(body,initial,c,entry=entry,s=s).run()
            assert(m.memory,m.calls,m.point_observations)==(wanted,calls,obs),(c,s)
            assert m.r[2]==1 and m.f[20:]==m.before_f[20:]
            models.append(m)
        assert literal(models[0])==literal(models[2]);seen.update(pc-entry for pc in models[0].visits);count+=1
    assert seen==set(range(0,308,4))-{0x100,0x114},sorted(set(range(0,308,4))-seen)
    aliases=0
    for alias,gate,matrix,mode in itertools.product((1,2,3,4,5,7,8),(0,1,255),(0,MATRIX),(0,1,2,4,8,15)):
        c=Case(alias=alias,gate=gate,matrix=matrix,mutation=mode,index=1)
        initial,s=fixture(c);wanted,calls,obs=reference(initial,c,s)
        models=[Oracle(body,initial,c,s=s).run()for body in programs(core,q,s)]
        assert all((m.memory,m.calls,m.point_observations)==(wanted,calls,obs)for m in models),(c,'alias')
        assert literal(models[0])==literal(models[2]);aliases+=1
    cuts=0
    for c in(Case(gate=0),Case(matrix=0),Case(mutation=15),Case(alias=3,mutation=1),Case(alias=5,index=1)):
        initial,s=fixture(c);ps=programs(core,q,s);full=Oracle(ps[0],initial,c,s=s).run()
        for cut in range(full.all_accesses):
            models=[]
            for body in(ps[0],ps[2]):
                m=Oracle(body,initial,c,s=s);m.cut=cut
                try:m.run();raise AssertionError(('Unfired attachment access cut',cut))
                except AccessBoundary:pass
                models.append(m)
            assert literal(models[0])==literal(models[1]);cuts+=1
    return dict(cases=count,all256_index_and_flag_bytes=True,code_global_helper_layouts=3,
                reached_words=75,preserved_unreachable_offsets=['0x100','0x114'],alias_cases=aliases,
                normalized_fault_prefix_cuts=cuts,independent_complete_memory=True,
                raw_public_semantics=True,normalized_literal_state=True,synthetic_aliases_guest_only=True,
                finite_arithmetic_and_exact_nonarithmetic_FP_payloads=True,FCSR_exception_equivalence_not_claimed_for_raw=True)

def connections(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();helper=struct.unpack_from('>98I',rom,0x1705E4)
    connected=dict(zip(range(POINT,POINT+392,4),helper));count=0
    public=lambda mem:{a:v for a,v in mem.items()if not STACK-2048<=a<STACK+1024}
    for c in(Case(gate=g,matrix=m,index=i,selector=b,point_zero=z,phase=p)
             for g,m,i,b,z,p in itertools.product((0,1,255),(0,MATRIX),(0,1),(0,255),(False,True),(0,8))):
        initial,s=fixture(c);wanted,calls,obs=reference(initial,c,s,actual_point=True);models=[]
        for body in programs(core,q,s):
            m=Oracle(body,initial,c,s=s,connected=connected).run()
            assert(public(m.memory),[call for call in m.calls if call[0]==POINT],m.point_observations)==(public(wanted),calls,obs),(c,'original point helper')
            models.append(m)
        assert literal(models[0])==literal(models[2]);count+=1
    table=0x8008F940;start,end=0x151A7AF0,0x151A7B1C;caller_words=struct.unpack_from('>11I',rom,0x1D4FA0)
    assert struct.unpack_from('>I',rom,0x234400)[0]==ENTRY
    caller=0
    for c in(Case(gate=g,matrix=m,mutation=mode,phase=p)for g,m,mode,p in itertools.product((0,1,255),(0,MATRIX),(0,1,2,4,8,15),(0,8))):
        initial,s=fixture(c);put(initial,table,ENTRY)
        wanted,calls,obs=reference(initial,c,s,ra=0x151A7B0C)
        put(wanted,STACK+c.phase+0x64,EFFECT);models=[]
        for body in programs(core,q,s):
            code=dict(zip(range(ENTRY,ENTRY+308,4),body));code[end]=0
            m=Oracle(caller_words,initial,c,entry=start,s=s,connected=code)
            m.r[16]=m.r[8]=EFFECT;m.r[12]=0;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run();raise AssertionError('Missing registered callback boundary')
            except WindowBoundary:pass
            assert(m.memory,m.calls,m.point_observations)==(wanted,[(ENTRY,(EFFECT,)),*calls],obs),(c,'registered callback')
            assert m.r[9]==0 and m.r[8]==EFFECT and m.r[2]==1
            models.append(m)
        assert literal(models[0])==literal(models[2]);caller+=1
    return dict(actual_point_helper_cases=count,actual_point_helper_words=98,bounded_existing_leaf_providers=True,
                registered_callback_cases=caller,registered_table=hex(table),caller_words=11,
                caller_start=hex(start),caller_end=hex(end),return1_consumed_as_continue=True,
                whole_dispatcher_not_qualified=True)

def native_text(core,selected=None):
    selected=core.SELECTED if selected is None else selected
    return '#include <ultra64.h>\n'+selected+r'''
typedef struct {u8 pad[8];u8 *source;} NativeLink;
typedef struct {u8 pad[0x1D4];u8 *matrix;} NativeOwner;
typedef struct {u8 *owner;u8 pad4[9];u8 index;u8 padE[10];u8 active;u8 pad19[35];f32 aux0,aux1;} NativeAttachment;
typedef struct {u8 pad0[0x34];AttachmentVector11C2B0 position,rotation;u8 pad4C[0xC4];NativeAttachment attachment;} NativeSource;
typedef struct {u8 pad0[0x1C];u8 flags;u8 pad1D[0x13];AttachmentVector11C2B0 position,rotation,output;f32 aux0,aux1;u8 pad5C[4];u8 *link;u8 tail[32];} NativeEffect;
typedef char Layout[(sizeof(void*)==4&&sizeof(AttachmentVector11C2B0)==12&&
 __builtin_offsetof(NativeEffect,position)==0x30&&__builtin_offsetof(NativeEffect,output)==0x48&&
 __builtin_offsetof(NativeEffect,link)==0x60&&__builtin_offsetof(NativeSource,position)==0x34&&
 __builtin_offsetof(NativeSource,rotation)==0x40&&__builtin_offsetof(NativeSource,attachment)==0x110&&
 __builtin_offsetof(NativeAttachment,index)==0xD&&__builtin_offsetof(NativeAttachment,active)==0x18&&
 __builtin_offsetof(NativeAttachment,aux0)==0x3C&&__builtin_offsetof(NativeOwner,matrix)==0x1D4)?1:-1];
AttachmentVector11C2B0 D_800A1620[2];u8 D_800A1638[2];
static NativeEffect effect,expected,atCall;static NativeSource source,expectedSource;
static NativeLink link,expectedLink;static NativeOwner owner,expectedOwner;
static u8 matrixData[16384];static int mode,index,calls,error;static u8 *wantedMatrix;
static void bytes(void*d,const void*s,unsigned n){u8*a=d;const u8*b=s;unsigned i;for(i=0;i<n;i++)a[i]=b[i];}
static void fill(void*d,unsigned n,u8 value){u8*a=d;unsigned i;for(i=0;i<n;i++)a[i]=(u8)(value+i*17);}
static int equal(const void*a,const void*b,unsigned n){const u8*x=a,*y=b;unsigned i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static void setbits(f32*p,u32 n){bytes(p,&n,4);}
static void changeSource(NativeSource*p){u32 words[6];unsigned i;for(i=0;i<6;i++)words[i]=0x41200000u+i;bytes(&p->position,words,24);p->attachment.index^=255;}
void func_15143134(f32 *point,f32 *output,u8 *matrix){
 calls++;
 if(calls!=1||point!=(f32 *)&D_800A1620[index]||output!=(f32 *)&effect.output||matrix!=wantedMatrix||
  !equal(&effect.position,&atCall.position,24)||!equal(&effect.aux0,&atCall.aux0,8)||effect.flags!=atCall.flags)error=1;
 effect.output.x=13.25f;effect.output.y=-19.5f;effect.output.z=0.25f;
 if(mode&1){effect.position.x=5.5f;effect.position.y=-7.25f;effect.position.z=0.5f;}
 if(mode&2)effect.flags^=0x5A;
 if(mode&4){changeSource(&source);effect.link=0;}
}
static int run(void){
 unsigned gate,mat,idx,selector,md,i;unsigned choices[4]={0,1,127,255};int count=0;
 for(gate=0;gate<256;gate++)for(mat=0;mat<2;mat++)for(idx=0;idx<2;idx++)for(selector=0;selector<4;selector++)for(md=0;md<8;md++){
  fill(&effect,sizeof(effect),0xA5);fill(&source,sizeof(source),0x5A);fill(&owner,sizeof(owner),0x87);fill(&link,sizeof(link),0x19);
  effect.flags=(u8)(gate^0x55);effect.position.x=1.25f;effect.position.y=-2.5f;effect.position.z=0.125f;
  effect.output.x=7.25f;effect.output.y=-1.75f;effect.output.z=9.5f;
  source.position.x=2.5f;source.position.y=-4.25f;source.position.z=1.125f;
  setbits(&source.rotation.x,0x7FC12345);setbits(&source.rotation.y,0x80000000);setbits(&source.rotation.z,0xFFC54321);
  setbits(&source.attachment.aux0,0x7FA12345);setbits(&source.attachment.aux1,0xFF800000);
  effect.link=(u8 *)&link;link.source=(u8 *)&source;source.attachment.owner=(u8 *)&owner;
  source.attachment.active=(u8)gate;source.attachment.index=(u8)idx;owner.matrix=mat?matrixData:0;
  for(i=0;i<2;i++){D_800A1620[i].x=2.25f;D_800A1620[i].y=-3.5f;D_800A1620[i].z=1.125f;D_800A1638[i]=(u8)choices[selector];}
  bytes(&expected,&effect,sizeof(effect));bytes(&expectedSource,&source,sizeof(source));bytes(&expectedOwner,&owner,sizeof(owner));bytes(&expectedLink,&link,sizeof(link));
  mode=(int)md;index=(int)idx;calls=error=0;wantedMatrix=matrixData+(choices[selector]<<6);
  if((gate&1)&&mat){
   expected.position=source.position;expected.rotation=source.rotation;bytes(&expected.aux0,&source.attachment.aux0,8);
   bytes(&atCall,&expected,sizeof(expected));
   if(md&1){expected.position.x=5.5f;expected.position.y=-7.25f;expected.position.z=0.5f;}
   if(md&2)expected.flags^=0x5A;
   if(md&4){changeSource(&expectedSource);expected.link=0;}
   expected.output.x=13.25f-expected.position.x;expected.output.y=-19.5f-expected.position.y;expected.output.z=0.25f-expected.position.z;expected.flags|=2;
  }else expected.flags&=0xFD;
  if(func_150EFA4C((u8 *)&effect)!=1||error||calls!=((gate&1)&&mat?1:0))return 1;
  if(!equal(&effect,&expected,sizeof(effect))||!equal(&source,&expectedSource,sizeof(source))||!equal(&owner,&expectedOwner,sizeof(owner))||!equal(&link,&expectedLink,sizeof(link)))return 2;
  count++;
 }
 return count==32768?0:3;
}
'''+START
def controls(core):
    s=core.SELECTED;pos='''            *(AttachmentVector11C2B0 *)(effect + 0x30) =
                *(AttachmentVector11C2B0 *)(source + 0x34);'''
    rot='''            *(AttachmentVector11C2B0 *)(effect + 0x3C) =
                *(AttachmentVector11C2B0 *)(source + 0x40);'''
    rows={
        'stub':s[:s.index('/* Refresh')]+'s32 func_150EFA4C(u8 *effect){return 0;}',
        'wrong_gate_bit':s.replace('source[0x128] & 1','source[0x128] & 2'),
        'wrong_position':s.replace(pos,pos.replace('source + 0x34','source + 0x40')),
        'missing_rotation':s.replace(rot,''),
        'wrong_auxiliary':s.replace('*(f32 *)(attachment + 0x3C)','*(f32 *)(attachment + 0x40)'),
        'wrong_vector':s.replace('&D_800A1620[index]','&D_800A1620[1 - index]'),
        'wrong_matrix_stride':s.replace('D_800A1638[index] << 6','D_800A1638[index] << 5'),
        'wrong_set_bit':s.replace('effect[0x1C] |= 2','effect[0x1C] |= 1'),
        'wrong_clear_bit':s.replace('effect[0x1C] &= ~2','effect[0x1C] &= ~1'),
        'wrong_return':s.replace('return 1;','return 0;'),
        'stale_first_position':s.replace('*(f32 *)(effect + 0x30);','*(f32 *)(source + 0x34);'),
        'stale_second_position':s.replace('*(f32 *)(effect + 0x34);','*(f32 *)(source + 0x38);'),
        'stale_third_position':s.replace('*(f32 *)(effect + 0x38);','*(f32 *)(source + 0x3C);'),
        'missing_subtraction':s.replace('            *(f32 *)(effect + 0x48) -= *(f32 *)(effect + 0x30);',''),
    }
    assert all(body!=s for body in rows.values())
    return rows
def native(core,out):
    rows=[('valid-'+opt[1:],None,opt,True)for opt in('-O0','-O2','-O3')]
    rows +=[(name,body,'-O2',False)for name,body in controls(core).items()];records=[]
    for name,body,opt,valid in rows:
        p=out/('native-'+name);p.with_suffix('.c').write_text(native_text(core,body))
        compile=subprocess.run([*native_command(opt),'-mstackrealign',str(p.with_suffix('.c')),'-o',str(p)],cwd=core.ROOT,capture_output=True,text=True)
        assert compile.returncode==0 and not compile.stdout and not compile.stderr,(name,compile.stdout,compile.stderr)
        run=subprocess.run([str(p)],capture_output=True,text=True,timeout=30)
        assert not run.stdout and not run.stderr and((run.returncode==0)==valid),(name,run.returncode,run.stdout,run.stderr)
        records.append(dict(name=name,opt=opt,exit=run.returncode,valid=valid))
    return dict(cases_per_profile=32768,profiles=['O0','O2','O3'],trapping_UBSan=True,effective_controls=len(controls(core)),
                records=records,typed_backing_objects_and_all_field_offsets=True,whole_object_canaries=True,
                native_table_indices=[0,1],synthetic_aliases_guest_only=True)
