"""Record effect packet: captured bytes, expiration dispatcher, aliases, real helpers and image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_effect_packet_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];RECORD,EFFECT,UPDATE,FREE=0x20000,0x50000,0x151B8000,0x1516972C
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,1,0x80000001,0x7F7FFFFF,0x7FC12345)
VALUES=(0,1,127,128,255,256,32767,32768,65535,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
@dataclass(frozen=True)
class Case:
    pattern:int=0
    byte:int=37
    word:int=0x8000
    allocated:bool=True
    mutation:int=0
    destination:int=0
    input_layout:int=0
    phase:int=0
    flags:int=1
    age:int=-1
    update:int=-1
    death:int=3
    ticks:int=1
    update_mode:int=0

def source_pointer(c,entered=None):
    sp=STACK+c.phase if entered is None else entered
    return(RECORD,sp-76,sp-72,sp)[c.input_layout]
def pointer(c,entered=None,record=None):
    sp=STACK+c.phase if entered is None else entered;record=source_pointer(c,sp)if record is None else record
    return(EFFECT,sp-76,sp-72,record)[c.destination]if c.allocated else 0

def fixture(c):
    sp=STACK+c.phase;m={sp+i:(i*17+0xA5)&255 for i in range(-1024,512)}
    for base,length in((RECORD-16,112),(EFFECT-16,192)):m.update({base+i:(i*13+0x59)&255 for i in range(length)})
    record=source_pointer(c)
    for i in range(80):m[record+i]=(i*13+0x59)&255
    m[record+1]=255-c.byte;m[record+12]=c.byte;m[record+13]=c.flags;put(m,record+14,c.age&65535,2);m[record+16]=c.death&255;m[record+17]=c.update&255
    for i in range(3):put(m,record+40+4*i,FLOATS[(c.pattern+i)%8])
    put(m,record+52,FLOATS[(c.pattern+3)%8]);put(m,record+56,FLOATS[(c.pattern+4)%8]);put(m,record+60,c.word&65535,2)
    for i in range(4):put(m,record+62+i*2,(c.word*(2*i+1)^(i*0x5555))&65535,2)
    for i in range(10):put(m,source.TABLE+4*i,source.ENTRY if i==3 else 0)
    for i in range(10):put(m,source.UPDATE_TABLE+4*i,UPDATE if i==2 else 0)
    put(m,source.TICKS,c.ticks&0xFFFFFFFF);return m

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def half(v):return(((v&65535)^32768)-32768)&0xFFFFFFFF
def signed_half(m,address):return((read(m,address,2)^32768)-32768)
def mutate_source(m,record):
    for off,v in((40,0x42040000),(44,0xC2300000),(48,0x425C0000),(52,0x3F000000),(56,0xBF000000)):put(m,record+off,v)
    put(m,record+60,0x1234,2)
    for i,v in enumerate((9,-10,11,-12)):put(m,record+62+2*i,v&65535,2)
    m[record+1]=0x6B;m[record+12]=0xA7

def change(m,c,entered,record):
    if c.mutation&1:mutate_source(m,record)
    if c.mutation&2:
        for i in(0,7,16,31):m[entered-36+i]=(i*3+0x19)&255
    if c.mutation&4:put(m,record+14,2,2)
def clobber(m,sp):
    for i in range(4):put(m,sp+4*i,0xB5000000+i)
def update_effect(m,c,record):
    if c.update_mode:
        put(m,record+14,1 if c.update_mode==1 else 0xFFFF,2)
        if c.update_mode==2:mutate_source(m,record)

def capture_and_spawn(initial,c,entered=None,record=None):
    sp=STACK+c.phase if entered is None else entered;record=source_pointer(c,sp)if record is None else record;m=dict(initial);packet=sp-36;frame=sp-88
    for i in range(3):put(m,packet+4*i,read(m,record+40+4*i))
    first=read(m,record+52);put(m,packet+16,0);put(m,packet+12,first);put(m,packet+20,read(m,record+56))
    for i in range(4):put(m,packet+24+2*i,read(m,record+62+2*i,2),2)
    life=half(read(m,record+60,2));put(m,frame+20,32);put(m,frame+16,0);slot=m[record+12];put(m,frame+24,slot);context=m[record+1];put(m,frame+28,context)
    calls=[(source.FACTORY,(life,0xFFFFFFFF,3,1,0,32,slot,context))];snapshot=bytes(m[packet+i]for i in range(32));change(m,c,sp,record);clobber(m,frame);copied=None
    if c.allocated:
        dst=pointer(c,sp,record)+40;calls.append((source.COPY,(dst,packet,32)));copied=bytes(m[packet+i]for i in range(32))
        for i in range(32):m[dst+i]=m[packet+i]
    return m,calls,snapshot,copied

def parent_reference(initial,c):
    m=dict(initial);calls=[];record=RECORD
    if m[record+13]&1:put(m,record+14,(signed_half(m,record+14)-read(m,source.TICKS))&65535,2)
    if m[record+17]!=255:calls.append((UPDATE,(record,)));update_effect(m,c,record)
    if signed_half(m,record+14)<0 and m[record+16]!=255:
        calls.append((source.ENTRY,(record,)));m,more,_,_=capture_and_spawn(m,c,STACK+c.phase-24,record);calls+=more
    if signed_half(m,record+14)<0:calls.append((FREE,(record,)));put(m,record+4,0xDEAD0001)
    return public(m),calls

class PacketOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,factory=source.FACTORY,copy=source.COPY,connected=None):
        self.entered=STACK+c.phase;self.record=source_pointer(c,self.entered)
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(self.record,),connected=connected)
        self.case,self.factory,self.copy,self.trace=c,factory,copy,[];self.snapshot,self.copied,self.factory_packet=None,None,None
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        sizes={source.ENTRY:1,self.factory:8,self.copy:3,source.CONSTRUCTOR:9,source.ALLOC:6,source.ZERO:2,source.HEAP:5,source.REGISTER:2,UPDATE:1,FREE:1};assert target in sizes,hex(target);args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==source.ENTRY:self.entered=self.r[29];self.record=args[0]
        if target==self.factory:self.factory_packet=args;self.snapshot=bytes(self.memory[self.entered-36+i]for i in range(32))
        if target==self.copy:self.copied=bytes(self.memory[args[1]+i]for i in range(args[2]))
    def hook(self,target):
        c=self.case;a=self.calls[-1][1]
        if target in(self.factory,source.HEAP,source.ALLOC):change(self.memory,c,self.entered,self.record);result=pointer(c,self.entered,self.record)
        elif target==self.copy:
            for i in range(a[2]):self.put(a[0]+i,self.get(a[1]+i,1),1)
            result=a[0]
        elif target==source.ZERO:
            for i in range(a[1]):self.put(a[0]+i,0,1)
            result=0
        elif target==UPDATE:update_effect(self.memory,c,a[0]);result=0xDEAD0002
        elif target==FREE:put(self.memory,a[0]+4,0xDEAD0001);result=0xDEAD0001
        else:assert target==source.REGISTER;result=0xB5000001
        clobber(self.memory,self.r[29])
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result;self.hi,self.lo=0xA5000010,0xA5000011

def controls():
    b=source.SELECTED;begin=b.index('    packet.position =');end=b.index('    effect =');capture=b[begin:end];late=b[:begin]+b[end:];late=late.replace('    if (effect != NULL) {','    if (effect != NULL) {'+chr(10)+capture)
    return dict(wrong_lifetime=b.replace('*(s16 *)((u8 *)record + 0x3C)','(u8)*(s16 *)((u8 *)record + 0x3C)'),wrong_kind=b.replace(' -1, 3, 1, 0,',' -1, 2, 1, 0,'),wrong_size=b.replace('sizeof(packet)','sizeof(packet) - 1'),wrong_slot=b.replace('((u8 *)record)[0xC]','((u8 *)record)[0xC] ^ 1U'),wrong_context=b.replace('((u8 *)record)[1]','((u8 *)record)[1] ^ 1U'),nonzero_phase=b.replace('packet.phase = 0.0f','packet.phase = 1.0f'),wrong_value=b.replace('packet.sourceValueB = *(f32 *)((u8 *)record + 0x38)','packet.sourceValueB = *(f32 *)((u8 *)record + 0x34)'),wrong_parameter=b.replace('packet.parameters[3] = *(s16 *)((u8 *)record + 0x44)','packet.parameters[3] = 0'),wrong_destination=b.replace('(u8 *)effect + 0x28','(u8 *)effect + 0x24'),late_capture=late)

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
typedef struct{EffectPacketPosition1CC440 position;f32 sourceValueA,sourceValueB;s16 lifetime;s16 parameters[4];}SourceState;
typedef struct{struct260 header;u8 gap24[4];SourceState state;}SourceRecord;
typedef char ABI[(sizeof(void*)==4&&sizeof(RecordEffectPacket1CC440)==32&&__builtin_offsetof(RecordEffectPacket1CC440,parameters)==24&&sizeof(struct260)==36&&__builtin_offsetof(SourceRecord,state)==40&&__builtin_offsetof(SourceState,parameters)==22)?1:-1];
static struct{u32 pre[4];SourceRecord record;u32 post[4];}actualInput,expectedInput;
static union{u64 align;u8 data[160];}actualOutput,expectedOutput;
static RecordEffectPacket1CC440 expectedPacket,captured;static u32 allocated,mutation,layout,calls,bad,wantedSlot,wantedContext;static s16 wantedLife;
static f32 real(u32 v){union{f32 f;u32 u;}x;x.u=v;return x.f;}
static void bytes(void*d,const void*s,u32 n){volatile u8*a=d;const u8*b=s;u32 i;for(i=0;i<n;i++)a[i]=b[i];}
struct260*func_151491F4(s16 life,s8 death,s8 update,u8 flags,u8 selector,s32 size,u8 slot,s32 context){
 if(calls++||life!=wantedLife||death!=-1||update!=3||flags!=1||selector||size!=32||slot!=wantedSlot||(u32)context!=wantedContext)bad=1;
 if(mutation){actualInput.record.state.position.x=33.0f;actualInput.record.state.position.y=-44.0f;actualInput.record.state.position.z=55.0f;actualInput.record.state.sourceValueA=0.5f;actualInput.record.state.sourceValueB=-0.5f;actualInput.record.state.lifetime=0x1234;for(u32 i=0;i<4;i++)actualInput.record.state.parameters[i]=(s16)(i%2?-10-(s32)i+1:9+(s32)i);((u8*)&actualInput.record)[1]=0x6B;((u8*)&actualInput.record)[12]=0xA7;}
 return allocated?(struct260*)(actualOutput.data+layout*4):0;
}
void*memcpy(void*d,const void*s,u32 n){if(calls++!=1||!allocated||d!=actualOutput.data+layout*4+40||n!=32){bad=1;return d;}bytes(&captured,s,n);bytes(d,s,n);return d;}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+chr(10)
    t+=r'''
typedef void(*Spawn)(struct260*);
static int check(Spawn fn){const u32 fp[]={0,0x80000000,0x3F800000,0xC0200000,1,0x80000001,0x7F7FFFFF,0x7FC12345};u32 value,a,change,offset,i,p;u8 *ai=(u8*)&actualInput,*ei=(u8*)&expectedInput;
 for(value=0;value<65536;value++)for(a=0;a<2;a++)for(change=0;change<2;change++)for(offset=0;offset<2;offset++){
  for(i=0;i<sizeof(actualInput);i++)ai[i]=ei[i]=(u8)(i*13+value);for(i=0;i<160;i++)actualOutput.data[i]=expectedOutput.data[i]=(u8)(i*17+value);
  p=value&7;actualInput.record.state.position.x=real(fp[p]);actualInput.record.state.position.y=real(fp[(p+1)&7]);actualInput.record.state.position.z=real(fp[(p+2)&7]);actualInput.record.state.sourceValueA=real(fp[(p+3)&7]);actualInput.record.state.sourceValueB=real(fp[(p+4)&7]);actualInput.record.state.lifetime=(s16)value;
  for(i=0;i<4;i++)actualInput.record.state.parameters[i]=(s16)((value*(2*i+1))^(i*0x5555));wantedLife=(s16)value;wantedSlot=value&255;wantedContext=value>>8;((u8*)&actualInput.record)[12]=(u8)wantedSlot;((u8*)&actualInput.record)[1]=(u8)wantedContext;
  bytes(&expectedInput,&actualInput,sizeof(actualInput));expectedPacket.position=actualInput.record.state.position;expectedPacket.sourceValueA=actualInput.record.state.sourceValueA;expectedPacket.phase=0.0f;expectedPacket.sourceValueB=actualInput.record.state.sourceValueB;for(i=0;i<4;i++)expectedPacket.parameters[i]=actualInput.record.state.parameters[i];
  if(change){expectedInput.record.state.position.x=33.0f;expectedInput.record.state.position.y=-44.0f;expectedInput.record.state.position.z=55.0f;expectedInput.record.state.sourceValueA=0.5f;expectedInput.record.state.sourceValueB=-0.5f;expectedInput.record.state.lifetime=0x1234;expectedInput.record.state.parameters[0]=9;expectedInput.record.state.parameters[1]=-10;expectedInput.record.state.parameters[2]=11;expectedInput.record.state.parameters[3]=-12;((u8*)&expectedInput.record)[1]=0x6B;((u8*)&expectedInput.record)[12]=0xA7;}
  if(a)bytes(expectedOutput.data+offset*4+40,&expectedPacket,32);allocated=a;mutation=change;layout=offset;calls=bad=0;fn(&actualInput.record.header);
  if(bad||calls!=(a?2:1))return 1;for(i=0;i<sizeof(actualInput);i++)if(ai[i]!=ei[i])return 1;for(i=0;i<160;i++)if(actualOutput.data[i]!=expectedOutput.data[i])return 1;if(a)for(i=0;i<32;i++)if(((u8*)&captured)[i]!=((u8*)&expectedPacket)[i])return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';'+chr(10)
    return t+'return 0;}'+chr(10)+START

class RecordEffectPacketTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+chr(10))
    def linked(self,entry,factory,copy):
        key=(entry,factory,copy)
        if not hasattr(self,'links'):self.links={}
        if key in self.links:return self.links[key]
        symbols=dict(func_151491F4=factory,memcpy=copy);pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text(('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }'%entry)+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def compare(self,c=Case(),images=None,entry=source.ENTRY,factory=source.FACTORY,copy=source.COPY):
        initial=fixture(c);want,calls,snapshot,copied=capture_and_spawn(initial,c);calls=[(factory if t==source.FACTORY else copy,a)for t,a in calls];pair=[]
        for words in images or(self.truth,self.words):
            m=PacketOracle(words,initial,c,entry,factory,copy).run();self.assertEqual((public(m.memory),m.calls,m.snapshot,m.copied),(public(want),calls,snapshot,copied),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_owner_Make_callback_ABI_and_literal_registration(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFA8)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),39)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),38);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_1CC440.c.o.compact'),39);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22EF8C]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22EF80+3*4)[0],source.ENTRY)
        self.assertIn('extern void (*D_8008A4C0[])(struct260*);',(ROOT/'conker/include/variables.h').read_text());self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=88,bindings=2,guards=0,neighbors=38,compact_functions=39,GLOBAL_ASM_routines=6,Make_commands=5,typed_void_struct260_callback=True,registered_table_slot=3,no_diagnostics=True)
    def test_02_complete_packet_snapshot_aliases_and_provider_changes(self):
        count=0;visits=set()
        for byte,pattern,allocated,phase in itertools.product(range(256),range(8),(False,True),(0,8)):
            m=self.compare(Case(byte=byte,pattern=pattern,word=(byte*257)^0x8000,allocated=allocated,phase=phase));visits.update(m.visits);count+=1
        for layout,mutation,allocated,phase in itertools.product((1,2,3),range(8),(False,True),(0,8)):
            self.compare(Case(input_layout=layout,mutation=mutation,allocated=allocated,phase=phase));count+=1
        for destination,mutation,pattern,allocated,phase in itertools.product(range(4),range(8),range(4),(False,True),(0,8)):
            self.compare(Case(destination=destination,mutation=mutation,pattern=pattern,allocated=allocated,phase=phase));count+=1
        for word,allocated,phase in itertools.product(VALUES,(False,True),(0,8)):
            self.compare(Case(word=word,allocated=allocated,phase=phase));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4)));self.receipt['guest']=dict(cases=count,all47words_visited=True,all_slot_context_bytes_and_halfword_boundaries=True,complete32byte_snapshot_and_no_unwritten_packet_bytes=True,four_input_and_returned_record_layouts=True,source_snapshot_precedes_factory=True,late_packet_changes_and_forward_copy_overlap=True,full_private_state_and_access_trace=True,null_still_captures_source_packet=True)
    def test_03_full_original_dispatcher_and_retained_factory_chain(self):
        old=self.values['conker/build/conker.us.elf'];caller=list(struct.unpack_from('>45I',self.rom,0x176714));self.assertEqual(caller,list(struct.unpack_from('>45I',old,source.elf_slot_offset(old,source.CALLER,180))));count=0;visited=set()
        for flags,age,ticks,update,death,mode,allocated,mutation,phase in itertools.product((0,1),(-1,0,-32768,32767),(0,1,0xFFFFFFFF),(-1,2),(-1,3),range(3),(False,True),(0,4),(0,8)):
            c=Case(flags=flags,age=age,ticks=ticks,update=update,death=death,update_mode=mode,allocated=allocated,mutation=mutation,phase=phase);initial=fixture(c);want,calls=parent_reference(initial,c);pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=PacketOracle(caller,initial,c,entry=source.CALLER,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(want,calls),c);visited.update(p for p in m.visits if source.CALLER<=p<source.CALLER+180);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.assertEqual(visited,set(range(source.CALLER,source.CALLER+180,4)))
        descriptions=((source.FACTORY,0x1766A4,28),(source.CONSTRUCTOR,0x1765E0,49),(source.ALLOC,0x194F18,28),(source.COPY,0x22EC0,11));connected={};helper_visits={entry:set()for entry,_,_ in descriptions}
        for entry,rom,words in descriptions:
            body=list(struct.unpack_from('>%dI'%words,self.rom,rom));self.assertEqual(body,list(struct.unpack_from('>%dI'%words,old,source.elf_slot_offset(old,entry,words*4))));connected.update({entry+4*i:w for i,w in enumerate(body)})
        helpers=0
        for byte,allocated,mutation,phase in itertools.product((0,1,127,128,255),(False,True),(0,1,2,4),(0,8)):
            c=Case(byte=byte,word=0x8000|byte,allocated=allocated,mutation=mutation,phase=phase);initial=fixture(c);pair=[]
            for target in(self.truth,self.words):
                m=PacketOracle(target,initial,c,connected=connected).run();a=m.factory_packet;self.assertEqual([v for t,v in m.calls if t==source.CONSTRUCTOR],[(a[0],a[1],a[2],0xFFFFFFFF,a[3],a[4],a[5],a[6],a[7])]);self.assertEqual([v for t,v in m.calls if t==source.ALLOC],[(35,a[7],72,1,a[6],1)]);self.assertEqual([v for t,v in m.calls if t==source.HEAP],[(72,1,1,0,1)])
                if allocated:
                    self.assertEqual([v for t,v in m.calls if t==source.REGISTER],[(EFFECT,35)]);self.assertEqual(m.memory[EFFECT+1],a[7]&255);self.assertEqual(m.memory[EFFECT+12],a[6]);self.assertEqual(read(m.memory,EFFECT+14,2),a[0]&65535);self.assertEqual(bytes(m.memory[EFFECT+i]for i in(13,16,17,18,19)),bytes((1,255,3,255,0)));self.assertTrue(all(m.memory[EFFECT+20+i]==0 for i in range(16)));self.assertEqual(bytes(m.memory[EFFECT+40+i]for i in range(32)),m.copied)
                else:self.assertFalse(any(t in(source.REGISTER,source.ZERO,source.COPY)for t,a in m.calls))
                for entry,_,words in descriptions:helper_visits[entry].update(p for p in m.visits if entry<=p<entry+4*words)
                pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));helpers+=1
        self.receipt['caller']=dict(original_and_retained_dispatcher_words=45,cases=count,all45dispatcher_words_visited=True,actual_indirect_slot3_and_void_return=True,late_lifetime_reload_and_update_cleanup_gates=True,original_and_retained_helpers_words=116,helper_cases=helpers,helper_visited_words={hex(e):len(v)for e,v in helper_visits.items()},real_header_and_complete_payload_copy=True,bounded_heap_registration_bzero_updater_and_cleanup=True,no_full_heap_dispatcher_provider_or_gameplay_claim=True)
    def test_04_native32_all_halfwords_defined_packet_and_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=524288,effective_controls=len(controls()),trapping_UBSan=True,all65536_halfword_values_and_slot_context_pairs=True,all32_defined_packet_bytes_and_arena_fences=True,source_changes_after_capture=True,valid_disjoint_objects_and_two_destinations=True,no_guest_stack_overlap_or_FCSR_claim=True)
    def test_05_fired_access_prefixes_and_null_destination_suppression(self):
        cuts=0
        for c in(Case(),Case(allocated=False),Case(mutation=7),Case(input_layout=1),Case(input_layout=2,mutation=1),Case(destination=1),Case(destination=2),Case(destination=3)):
            initial=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=PacketOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        c=Case(allocated=False);initial={a:b for a,b in fixture(c).items()if not EFFECT-16<=a<EFFECT+176}
        for words in(self.truth,self.words):m=PacketOracle(words,initial,c).run();self.assertEqual(len(m.calls),1);self.assertEqual(len(m.snapshot),32)
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,null_still_reads_all_source_fields_but_needs_no_child_mapping=True)
    def test_06_actual_padder_corruptions_and_independent_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{140:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,factory,copy in((source.ENTRY,source.FACTORY,source.COPY),(0x17007FFC,0x171491F4,0x10028000),(0x2500FFFC,0x251491F4,0x20022EC0)):
            images=self.linked(entry,factory,copy)
            for c in(Case(),Case(allocated=False),Case(mutation=7),Case(input_layout=2),Case(destination=2),Case(destination=3)):self.compare(c,images,entry,factory,copy);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,two_call_bindings_and_J26_layouts=True,GNU_original_and_compiled_objects=True,raw_corruption_controls=3,guards=0)
    def test_07_actually_compiled_late_capture_is_rejected(self):
        obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()['late_capture'],'negative-late-capture');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(mutation=1);m=PacketOracle(words,fixture(c),c).run();want=capture_and_spawn(fixture(c),c)[3];self.assertNotEqual(m.copied,want);self.receipt['negative_capture']=dict(actually_compiled_late_capture_rejected=True,snapshot_must_precede_constructor=True,result_failure_not_unmapped_read=True)
    def test_08_strict_entire_image_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+100,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),141);self.receipt['image']=dict(changed_bytes=141,code_bytes=140,metadata_bytes=1,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guards_and_shared_headers_unchanged=True)
