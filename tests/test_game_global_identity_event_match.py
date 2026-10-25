"""Global identity callback: release/clear ordering, live keys and real dispatch."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_global_identity_event_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
PAIR,OWNER=0x20000,0x30000
RELEASE,BOOKKEEP,FALLBACK,CALLBACK=0x1516972C,0x151696DC,0x15169804,0x16200000
PARENT,TABLE,RELEASE_TABLE=source.PARENT,source.TABLE,0x8008B4D0
GLOBAL=source.GLOBAL
VALUES=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678)

@dataclass(frozen=True)
class Case:
    command:int=0
    pattern:int=0
    match:int=0
    key:int=255
    alias:int=0
    mutate:bool=False
    kind:int=2
    callback:bool=True


def addresses(c,phase=0):
    if c.alias>=9:
        return ((GLOBAL-0x28,PAIR),(GLOBAL-0x2C,PAIR),(OWNER,GLOBAL),
                (OWNER,GLOBAL-4),(GLOBAL,PAIR))[c.alias-9]
    owner=(OWNER,PAIR-0x28,PAIR-0x24,PAIR-0x20,PAIR-0x2C,PAIR,STACK+phase+8-0x28,OWNER,OWNER)[c.alias]
    event=STACK+phase+8 if c.alias==7 else STACK+phase-16 if c.alias==8 else PAIR
    return owner,event


def fixture(c,phase,registry):
    if len(registry)!=74:raise ValueError('Supply the actual 74-entry record event registry')
    owner,event=addresses(c,phase);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    m.update({GLOBAL+i:(i*19+0xA7)&255 for i in range(-32,64)});put(m,GLOBAL,0x12345678)
    for base,n in((owner-32,0x140),(event-32,128)):
        m.update({base+i:(i*13+0x5A)&255 for i in range(n)})
    first=VALUES[c.pattern%6];second=first if c.pattern>=6 else VALUES[(c.pattern+1)%6]
    put(m,event,first);put(m,event+4,second);m[event+8]=17;m[event+9]=231
    put(m,owner+0x28,(first,second,0xBEEFF00D,0xBEEFF00D)[c.match]);m[owner+0x2C]=c.key
    m[owner]=c.kind;m[owner+0x13]=4
    if c.match==3:m[owner+0x2C]=m[event+4]
    for i,target in enumerate(registry):put(m,TABLE+4*i,target)
    for kind in set((c.kind,7)):put(m,RELEASE_TABLE+52*kind,CALLBACK if c.callback else 0)
    return m


def mutation(m,c,owner):
    if c.mutate:
        m[owner]=7;put(m,owner+0x28,0xCAFEBABE);put(m,GLOBAL,0x55667788)


def outgoing_homes(m,sp):
    for i in range(4):put(m,sp+4*i,0xB5000000+i)


def reference(initial,c,phase=0,chain=False,incoming_sp=None,incoming_command=None):
    owner,event=addresses(c,phase);m=dict(initial);calls=[]
    sp=STACK+phase if incoming_sp is None else incoming_sp
    incoming=c.command if incoming_command is None else incoming_command
    put(m,sp+8,incoming);command=incoming&255;state=owner+0x28
    if command==45:
        current=read(m,state);first=read(m,event)
        if first==current:put(m,state,read(m,event+4));m[state+4]=m[event+9]
        elif read(m,event+4)==current:put(m,state,first);m[state+4]=m[event+8]
    elif command==0:
        first=read(m,event);current=read(m,state)
        if first==current or m[state+4]==m[event+4]:
            calls.append((RELEASE,(owner,)))
            if chain:
                calls.append((BOOKKEEP,(owner,)));mutation(m,c,owner);outgoing_homes(m,sp-48)
                if m[owner]>=2:calls.append((CALLBACK if c.callback else FALLBACK,(owner,)))
            else:mutation(m,c,owner);outgoing_homes(m,sp-24)
            put(m,GLOBAL,0)
    return m,calls


def public(m,c,phase=0,child=False):
    owner,event=addresses(c,phase)
    def relevant(a):
        return (not STACK-2048<=a<STACK+512 or owner+0x28<=a<owner+0x2D or
            event<=a<event+10 or STACK+phase+8<=a<STACK+phase+12 or
            child and STACK+phase-16<=a<STACK+phase-12)
    return {a:b for a,b in m.items()if relevant(a)}


class GlobalEventOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,arguments=None,release=RELEASE,providers=()):
        owner,event=addresses(c,phase)
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=arguments or(owner,event,c.command),connected=connected)
        self.case,self.owner,self.phase,self.release=c,owner,phase,release
        self.providers=set(providers)-{0,source.ENTRY};self.attempted=[]
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def record_call(self,target):
        self.attempted.append(target)
        assert target in(source.ENTRY,self.release,BOOKKEEP,FALLBACK,CALLBACK)or target in self.providers,hex(target)
        args=self.arguments(3 if target==source.ENTRY or target in self.providers else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in(self.release,BOOKKEEP,FALLBACK,CALLBACK)or target in self.providers
        if target in(self.release,BOOKKEEP):mutation(self.memory,self.case,self.arguments(1)[0])
        if target in self.providers:
            owner,event,command=self.arguments(3);put(self.memory,owner+0x34,target^command)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678


def controls():
    b=source.SELECTED
    return dict(and_gate=b.replace(' || ',' && '),wrong_command=b.replace('code == 0x2D','code == 0x2E'),
        wrong_release=b.replace('if (command == 0)','if (command == 1)'),
        wrong_key=b.replace('((u8 *)event)[4]','((u8 *)event)[5]'),
        wrong_first_key=b.replace('event->after_identity','event->before_identity'),
        wrong_second_key=b.replace('event->before_identity','event->after_identity'),
        missing_second=b.replace('else if (current == event->after)','else if (0)'),
        wrong_replacement=b.replace('link->owner = event->after;','link->owner = event->before;'),
        wrong_owner=b.replace('func_1516972C((struct102 *)owner);','func_1516972C((struct102 *)event);'),
        early_key=b.replace('link->owner = event->after;\n            link->identity = event->after_identity;',
            'link->identity = event->after_identity;\n            link->owner = event->after;'),
        wrong_priority=b.replace('if (current == event->before)','if (current == event->before && current != event->after)'),
        half_word=b.replace('u8 *first = event->before;',
            'u8 *first = (u8 *)(s32)((u16)((u8 *)event)[0] | ((u16)((u8 *)event)[1] << 8));'),
        missing_clear=b.replace('            D_800E0920 = NULL;',''),
        early_clear=b.replace('            func_1516972C((struct102 *)owner);\n            D_800E0920 = NULL;',
            '            D_800E0920 = NULL;\n            func_1516972C((struct102 *)owner);'),
        unconditional_clear=b.replace('    s32 code = command;','    s32 code = command;\n    D_800E0920 = NULL;'),
        wrong_clear=b.replace('D_800E0920 = NULL;','D_800E0920 = (u8 *)1;'))


def native_harness(values):
    text=values['conker/src/game_1944C0.c'].decode();lo,hi=source.function_span(text,'func_1516972C')
    helper=text[lo:hi].replace('func_1516972C','real_release')
    registry=struct.unpack_from('>74I',values['conker/conker.us.bin'],source.TABLE_ROM)
    others=sorted(set(registry)-{0,source.ENTRY})
    text=source.HEADERS+source.DECLARATIONS+'''
static u8 *arena,*expected,*currentOwner;
static u32 error,releases,bookkeeps,callbacks,fallbacks,mutationMode,present,expectedRelease;
static u32 providerCalls,seenProvider,expectedEvent,expectedCommand;
static u32 coverage[256];
u8 *D_800E0920;
struct115 D_8008B4D0[256];
void(*D_8008A8D8[74])(struct260*,s32,u8);
typedef void(*Handler)(struct260*,s32,u8);
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(struct115)==52&&__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__&&
 sizeof(PayloadOwnerLink)==8&&__builtin_offsetof(PayloadOwnerLink,identity)==4&&
 __builtin_offsetof(PayloadOwnerLinkEvent,after_identity)==9&&__builtin_offsetof(struct260,unk13)==0x13)?1:-1];
/* Read words into declared scalars; write representations through characters. */
static u32 word(const u8*p){u32 v;__builtin_memcpy(&v,p,4);return v;}
static void setword(u8*p,u32 v){const u8*b=(const u8*)&v;u32 i;for(i=0;i<4;i++)p[i]=b[i];}
__attribute__((noinline,noclone)) void func_151696DC(struct102*p){
 if((void*)p!=currentOwner)error=1;bookkeeps++;
 if(mutationMode){currentOwner[0]=7;((PayloadOwnerLink*)(void*)(currentOwner+0x28))->owner=(u8*)0xCAFEBABE;D_800E0920=(u8*)0x55667788;}
}
__attribute__((noinline,noclone)) void func_15169804(struct102*p){if((void*)p!=currentOwner)error=1;fallbacks++;}
static void callback(struct102*p){if((void*)p!=currentOwner)error=1;callbacks++;}
'''+helper+'''
__attribute__((noinline,noclone)) void func_1516972C(struct102*p){
 if(!expectedRelease||(void*)p!=currentOwner||releases++){error=1;return;}real_release(p);
}
static void provider(struct260*p,s32 event,u8 command,u32 address){
 if((void*)p!=currentOwner||(u32)event!=expectedEvent||command!=expectedCommand||providerCalls++)error=1;
 seenProvider=address;setword((u8*)p+0x34,address^command);
}
'''
    for address in others:
        text+='static void provider_%X(struct260*p,s32 e,u8 c){provider(p,e,c,0x%Xu);}\n'%(address,address)
    for label,body in dict(selected=source.SELECTED,**controls()).items():
        if label!='selected'and body==source.SELECTED:raise ValueError('Ineffective global identity-event control: '+label)
        text+=body.replace(source.FUNCTION,label)+'\n'
    parent=values[source.CALLER_SOURCE].decode();lo,hi=source.function_span(parent,'func_15149434');text+=parent[lo:hi]+'\n'
    text+='static const u32 registry[74]={'+','.join('0x%Xu'%x for x in registry)+'};\n'
    text+='static void install(Handler fn){\n'
    for i,address in enumerate(registry):
        text+='D_8008A8D8[%d]=%s;\n'%(i,'fn'if address==source.ENTRY else'provider_%X'%address if address else'0')
    text+='}\n'+'''
static const u32 vals[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678};
static int one(Handler fn,u32 command,u32 tag,u32 alias,u32 mutate,u32 selector){
 u32 i,pattern=(command+(tag>>2))%8,match=tag%4,kind=(tag&3)==3?255:tag&3;
 u32 ownerAt=(u32[]){0x200,0x100-0x28,0x100-0x24,0x100-0x20,0x100-0x2C,0x100}[alias];
 u32 state=ownerAt+0x28,first,current,release,afterKind,invoke,target,other;
 PayloadOwnerLinkEvent*event=(PayloadOwnerLinkEvent*)(void*)(arena+0x100);
 PayloadOwnerLink*link=(PayloadOwnerLink*)(void*)(arena+state);
 if(selector==256&&fn==selected)coverage[(u8)command]|=1u<<(4*pattern+match);
 for(i=0;i<0x400;i++)arena[i]=(u8)(i*13+0x5A);
 event->before=(u8*)vals[pattern%6];
 event->after=(u8*)(pattern>=6?vals[pattern%6]:vals[(pattern+1)%6]);
 event->before_identity=17;event->after_identity=231;
 link->owner=(u8*)(match==0?word(arena+0x100):match==1?word(arena+0x104):0xBEEFF00D);
 link->identity=(u8)tag;arena[ownerAt]=(u8)kind;arena[ownerAt+0x13]=(u8)selector;
 if(match==3)link->identity=arena[0x104];
 for(i=0;i<0x400;i++)expected[i]=arena[i];
 first=word(arena+0x100);current=word(arena+state);
 target=selector==256?0x1519E818u:registry[selector<74?selector:0];
 invoke=target==0x1519E818u;other=target&&!invoke;
 release=invoke&&(u8)command==0&&(first==current||arena[state+4]==arena[0x104]);
 if(invoke&&(u8)command==45){if(first==current){setword(expected+state,word(expected+0x104));expected[state+4]=expected[0x109];}
 else if(word(expected+0x104)==current){setword(expected+state,first);expected[state+4]=expected[0x108];}}
 if(other)setword(expected+ownerAt+0x34,target^(u8)command);
 mutationMode=mutate;present=tag&1;afterKind=kind;currentOwner=arena+ownerAt;
 if(release&&mutate){expected[ownerAt]=7;setword(expected+state,0xCAFEBABE);afterKind=7;}
 for(i=0;i<256;i++)D_8008B4D0[i].unk0=present?callback:0;
 error=releases=bookkeeps=callbacks=fallbacks=providerCalls=seenProvider=0;expectedRelease=release;
 expectedEvent=(u32)(arena+0x100);expectedCommand=(u8)command;D_800E0920=(u8*)0x12345678;
 if(selector!=256){install(fn);func_15149434((struct260*)(void*)currentOwner,(s32)(arena+0x100),(u8)command);}
 else fn((struct260*)(void*)currentOwner,(s32)(arena+0x100),(u8)command);
 if(error||D_800E0920!=(release?0:(u8*)0x12345678)||providerCalls!=other||seenProvider!=(other?target:0)||releases!=release||bookkeeps!=release||
 callbacks!=(release&&afterKind>=2&&present)||fallbacks!=(release&&afterKind>=2&&!present))return 23;
 for(i=0;i<0x400;i++)if(arena[i]!=expected[i])return 23;
 return 0;
}
static int variant(Handler fn,u32 full){u32 c,t,a,m;
 for(c=0;c<(full?256u:3u);c++)for(t=0;t<256;t++)for(a=0;a<6;a++)for(m=0;m<2;m++)
  if(one(fn,full?c:(u32[]){0,45,255}[c],t,a,m,256))return 23;return 0;}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u32 c,s,m;arena=allocate(0x800);if(!arena)return 97;expected=arena+0x400;
'''
    for i,label in enumerate(dict(selected=source.SELECTED,**controls())):
        text+='if(variant(%s,%d)!=%d)return %d;\n'%(label,int(label=='selected'),0 if label=='selected'else 23,11+i)
    text+='for(c=0;c<256;c++)if(coverage[c]!=0xFFFFFFFFu)return 68;\n'
    text+='for(c=0;c<256;c++)for(s=0;s<256;s++)for(m=0;m<2;m++)if(one(selected,c,c,0,m,s))return 70;\nreturn 0;}\n'
    return text+START


class GlobalIdentityEventTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);rom=cls.values['conker/conker.us.bin']
        cls.truth=list(struct.unpack_from('>45I',rom,source.ROM));cls.parent=list(struct.unpack_from('>23I',rom,0x1768E4))
        cls.registry=struct.unpack_from('>74I',rom,source.TABLE_ROM)
        cls.helper=list(struct.unpack_from('>28I',rom,0x196BDC))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>45I',data,fs[source.FUNCTION]['value']))
        cls.slot=data[fs[source.FUNCTION]['value']:fs[source.FUNCTION]['value']+180]
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=list(struct.unpack_from('>45I',data,fs[source.FUNCTION]['value']))
        old=cls.values['conker/build/conker.us.elf']
        cls.retained_parent=list(struct.unpack_from('>23I',old,source.elf_slot_offset(old,PARENT,92)))
        cls.retained_helper=list(struct.unpack_from('>28I',old,source.elf_slot_offset(old,RELEASE,112)))
    def initial(self,c,phase=0):
        return fixture(c,phase,self.registry)
    def compare(self,c=Case(),phase=0,chain=False,images=None,entry=source.ENTRY,release=RELEASE):
        initial=self.initial(c,phase);expected,calls=reference(initial,c,phase,chain);models=[]
        for words in images or(self.truth,self.words):
            connected={RELEASE+4*i:w for i,w in enumerate(self.helper)}if chain else None
            m=GlobalEventOracle(words,initial,c,phase,entry,connected,release=release).run()
            self.assertEqual(public(m.memory,c,phase),public(expected,c,phase),c)
            normalized=[(RELEASE if t==release else t,a)for t,a in m.calls];self.assertEqual(normalized,calls,c);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]
    def test_01_literal_slot_owner_Make_and_registry(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.slot,self.values['conker/conker.us.bin'][source.ROM:source.ROM+180])
        self.assertEqual(self.slot[-8:],bytes.fromhex('03E0000800000000'));self.assertEqual(self.helper,self.retained_helper);self.assertEqual(self.parent,self.retained_parent)
        q=json.loads((self.out/'qualification.json').read_text());mk=json.loads((self.out/'make-shadow.json').read_text())
        neighbors=len(source.parse_object(self.out/'before-owner.o')[1])-1
        self.assertEqual((q['body_words'],q['slot_words'],q['alignment_words'],q['new_guards'],q['preserved_neighbors']),(45,45,0,18,neighbors))
        self.assertEqual((q['preserved_global_asm'],mk['commands'],mk['compact_functions_equal']),(0,3,neighbors+1))
        self.assertTrue(mk['complete_padded_object_equal'])
        installed=(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE]
        self.assertEqual((ROOT/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'before-padded.o')).read_bytes())
        if installed:
            self.assertEqual((ROOT/source.SOURCE).read_bytes(),(self.out/'proposed-owner.c').read_bytes())
            self.assertEqual((ROOT/'conker/build/conker.us.elf').read_bytes(),(self.out/'first-linked.elf').read_bytes())
        self.assertIn('void func_1516972C(struct102 *);',(self.out/'proposed-owner.c').read_text())
        self.assertIn('#include "structs.h"',(self.out/'proposed-owner.c').read_text())
        self.assertNotIn('void func_1516972C(void *arg0);',(self.out/'proposed-owner.c').read_text())
        self.assertEqual(self.registry[4],source.ENTRY)
        old=self.values['conker/build/conker.us.elf'];self.assertEqual(struct.unpack_from('>74I',old,source.elf_slot_offset(old,TABLE,296)),self.registry)
        direct=[];literal=[];call=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF);rom=self.values['conker/conker.us.bin']
        for i in range(0,len(rom)-3,4):
            word=struct.unpack_from('>I',rom,i)[0]
            if word==source.ENTRY:literal.append(i)
            if word==call:direct.append(i)
        self.assertEqual((direct,literal),([],[0x22F3A8]))
        self.receipt['owner']=dict(body_words=45,slot_words=45,alignment_words=0,frame=24,bindings=3,guards=18,
            neighbors=neighbors,Make_commands=3,preserved_global_asm=0,actual_registry_index=4,registry_entries=74,
            canonical_ABI='void(struct260*,s32,u8)',existing_release_interface_unchanged=True,direct_sites=direct,literal_sites=literal)
    def test_02_byte_ABI_identity_priority_keys_and_aliases(self):
        count=0;visits=set()
        cases=[(Case(upper|command,command%8,command%4,(0,127,128,255)[command%4],alias),phase)
            for command,alias,(upper,phase)in itertools.product(range(256),(0,6,7,8),((0,0),(0xA5A50000,8)))]
        cases.extend((Case(upper|command,pattern,match,key,alias,True),phase)
            for command,pattern,match,key,alias,(upper,phase)in itertools.product((0,45),range(8),range(4),(0,127,128,255),range(14),((0,0),(0x87650000,8))))
        cases.extend((Case(command,2,2,key),0)for command,key in itertools.product((0,45),range(256)))
        for c,phase in cases:
            m=self.compare(c,phase);visits.update(m.visits)
            raw=GlobalEventOracle(self.raw,self.initial(c,phase),c,phase).run();expected,calls=reference(self.initial(c,phase),c,phase)
            self.assertEqual(public(raw.memory,c,phase),public(expected,c,phase));self.assertEqual(raw.calls,calls);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+180,4))-{source.ENTRY+140})
        self.receipt['guest']=dict(cases=count,all_command_bytes=True,all_key_bytes=True,full_incoming_command_home=True,
            alias_layouts=14,guest_matrix_is_partitioned=True,supported_commands_full_pattern_match_key_alias_matrix=True,
            global_word_and_key_aliases=True,global_clear_after_provider_mutation=True,
            raw_C_public_semantics_checked=True,fitted_full_private_state_equal=True,reachable_words=44,dead_word=35)
    def test_03_retained_release_helper_and_late_kind(self):
        self.assertEqual(self.helper,self.retained_helper);visits=set();count=0
        for kind,mutate,callback,phase in itertools.product((0,1,2,255),(False,True),(False,True),(0,8)):
            c=Case(0,1,0,255,0,mutate,kind,callback);m=self.compare(c,phase,True);visits.update(m.visits);count+=1
        self.assertTrue(set(range(RELEASE,RELEASE+112,4))<=visits)
        self.receipt['release']=dict(cases=count,all_28_original_and_retained_words_visited=True,late_kind_reload=True,
            pre_bookkeeping_and_callback_fallback_are_bounded_contracts=True,no_new_helper_credit=True)
    def caller_compare(self,parent,c,index,phase=0):
        owner,event=addresses(c,phase);initial=self.initial(c,phase);initial[owner+0x13]=index
        expected=dict(initial);put(expected,STACK+phase+8,c.command)
        chosen=self.registry[index if index<74 else 0];command=c.command&255;calls=[]
        if chosen==source.ENTRY:
            expected,tail=reference(expected,c,phase,incoming_sp=STACK+phase-24,incoming_command=command)
            calls=[(source.ENTRY,(owner,event,command)),*tail]
        elif chosen:
            put(expected,owner+0x34,chosen^command);outgoing_homes(expected,STACK+phase-24)
            calls=[(chosen,(owner,event,command))]
        pair=[]
        for words in(self.truth,self.words):
            connected={source.ENTRY+4*i:w for i,w in enumerate(words)}
            m=GlobalEventOracle(parent,initial,c,phase,PARENT,connected,providers=self.registry).run()
            self.assertEqual(m.calls,calls,(c,index));self.assertEqual(public(m.memory,c,phase,True),public(expected,c,phase,True),(c,index));pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_04_original_and_retained_full_dispatchers(self):
        count=0
        cases=[(Case(0xA5000000|command,command%8,command%4,command,0,True),index,phase)
            for command,index,phase in itertools.product((0,45,255),range(256),(0,8))]
        cases.extend((Case(0xA5000000|command,command%8,command%4,command,0,True),index,phase)
            for command,index,phase in itertools.product(range(256),(0,1,4,17,73,74,255),(0,8)))
        cases.extend((Case(upper|command,pattern,match,255,alias,True),index,phase)
            for command,pattern,match,alias,index,(upper,phase)in itertools.product((0,45,255),(0,7),range(4),range(1,14),(0,4),((0,0),(0x87650000,8))))
        for parent in(self.parent,self.retained_parent):
            for c,index,phase in cases:self.caller_compare(parent,c,index,phase);count+=1
        self.receipt['caller']=dict(cases=count,original_words=23,retained_words=23,actual_table_entries=74,
            all_selector_bytes=True,all_command_bytes=True,guest_matrix_is_partitioned=True,
            clamp_to_NULL_slot_zero=True,all_nonzero_provider_addresses_checked=True,
            canonical_callback_signature='void(struct260*,s32,u8)',byte_mask_before_indirect_call=True,
            other_providers_are_bounded_contracts=True,whole_parent_gameplay_claimed=False)
    def test_05_native32_actual_C_release_and_typed_dispatch(self):
        text=native_harness(self.values)
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=120).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],target_cases_per_profile=256*256*6*2,
            dispatcher_cases_per_profile=256*256*2,effective_controls=len(controls()),trap_UBSan=True,actual_retained_release_C=True,
            heap_backed_typeless_fixture=True,pointer_members_initialized_with_pointer_lvalues=True,
            character_representation_writes=True,declared_scalar_word_reads=True,little_endian_native32=True,
            wrong_width_control_uses_character_reads=True,canonical_function_pointer_interface=True,all_selector_bytes=True,
            global_checked_on_all_paths=True,release_can_mutate_global=True,global_aliases_guest_only=True,
            all_32_pattern_match_pairs_per_command_runtime_verified=True)
    def test_06_fault_prefixes_and_effective_compiled_negatives(self):
        count=0
        for c in(Case(0,0,0),Case(0,0,2),Case(0,0,3),Case(45,1,0),Case(45,3,1),Case(45,2,2),Case(45,2,0,255,3),Case(0,1,0,255,6),
                 Case(0,0,0,255,9),Case(0,0,0,255,10),Case(0,0,3,255,11),Case(45,0,0,255,12),Case(0,0,0,255,13)):
            initial=self.initial(c);m=self.compare(c)
            for fault in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=GlobalEventOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        for command,phase in itertools.product((x for x in range(256)if x not in(0,45)),(0,8)):
            c=Case(command);initial={a:b for a,b in self.initial(c,phase).items()if STACK-2048<=a<STACK+512}
            for words in(self.truth,self.words,self.raw):GlobalEventOracle(words,initial,c,phase).run()
        bad=source.SELECTED.replace('    s32 code = command;','    s32 code = command;\n    (void)*(volatile u32 *)&link->owner;')
        obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.RELEASE_DECLARATION+source.DECLARATIONS+bad,'negative-hoisted-read');self.assertFalse(diag)
        data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);info=fs[source.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        c=Case(255);initial={a:b for a,b in self.initial(c).items()if STACK-2048<=a<STACK+512}
        with self.assertRaisesRegex(AssertionError,'unmapped read'):GlobalEventOracle(words,initial,c).run()
        text=self.values[source.CALLER_SOURCE].decode();lo,hi=source.function_span(text,'func_15149434');parent=text[lo:hi]
        controls_={'bound':parent.replace('idx >= 74','idx >= 75'),'NULL':parent.replace('D_8008A8D8[idx] != 0','1')}
        for name,body in controls_.items():
            self.assertNotEqual(body,parent)
            obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+'extern void(*D_8008A8D8[74])(struct260*,s32,u8);\n'+body,'negative-parent-'+name)
            self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);info=fs['func_15149434']
            words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
            c=Case(255);initial=self.initial(c);initial[OWNER+0x13]=74 if name=='bound'else 0
            x=GlobalEventOracle(words,initial,c,entry=PARENT,providers=self.registry)
            with self.assertRaisesRegex(AssertionError,'unmapped read'if name=='bound'else'0x0'):x.run()
            if name=='NULL':self.assertEqual(x.attempted[-1],0)
        self.receipt['faults']=dict(prefix_pairs=count,ignored_modes_need_no_packet_or_owner_mapping=True,
            actual_compiled_MIPS_early_read_negative_effective=True,compiled_parent_bound_and_NULL_negatives_effective=True,
            emitted_guest_access_order_only=True)
    def test_07_literal_guard_controls_real_padder_and_rebases(self):
        global GLOBAL
        raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        for i in range(45):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        for at,rows in rs.items():
            bad=dict(rs);bad[at]=[(rows[0][0],'wrong')]
            with self.assertRaises(ValueError):source.normalized(raw,bad)
        with self.assertRaises(ValueError):source.normalized(raw[:-4],rs)
        with self.assertRaises(ValueError):source.guard_bytes(self.values['conker/retail_word_patches.us.csv']+b'\n',raw,rs)
        guard=(self.out/'qualified-guards.csv').read_text();prefix=self.values['conker/retail_word_patches.us.csv'].decode()
        self.assertTrue(guard.startswith(prefix.replace('\r\n','\n')))
        tail=guard[len(prefix.replace('\r\n','\n')):];self.assertIn('0x8C430000',tail)
        path=self.out/'negative-real-padder.csv';path.write_text(guard[:-len(tail)]+tail.replace('0x8C430000','0x8C430001',1))
        with self.assertRaises((ValueError,RuntimeError)):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
        fitted,bindings=source.normalized(raw,rs);asm,missing=emit_function(fitted,dict(value=0,size=180),bindings,source.FUNCTION,
            dict(func_1516972C=RELEASE,D_800E0920=GLOBAL))
        self.assertFalse(missing);p=self.out/'independent-fitted.s';p.write_text(asm);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
        links=0;executions=0
        layouts=((source.ENTRY,RELEASE,source.GLOBAL),(source.ENTRY+0x200000,RELEASE+0x300000,0x80507FFC),
                 (source.ENTRY+0x500000,RELEASE+0x700000,0x80518000))
        for i,(entry,release,global_address)in enumerate(layouts):
            images=[]
            for j,object_ in enumerate((source.original(ROOT,self.out),obj)):
                p=self.out/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,
                    '--defsym=func_1516972C=0x%X'%release,'--defsym=D_800E0920=0x%X'%global_address,
                    '-o',str(elf),str(object_)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>45I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            previous=GLOBAL
            try:
                GLOBAL=global_address
                for c in(Case(0),Case(45,3,0),Case(45,3,1),Case(255),Case(0,0,0,255,9),Case(0,0,3,255,11)):
                    self.compare(c,images=images,entry=entry,release=release);executions+=1
            finally:GLOBAL=previous
        self.receipt['guards_links']=dict(raw_word_controls=45,binding_controls=3,extent_controls=1,history_controls=1,
            real_padder_controls=1,independent_GNU_links=links,layouts=3,rebased_executions=executions,
            call_binding_rebased=True,global_HI_LO_carry_boundaries=True,global_aliases_rebased=True)
    def test_08_strict_full_image_and_frozen_inputs(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+180]
        pred=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        report=json.loads((self.out/'first-link.json').read_text());at=source.elf_slot_offset(before,source.ENTRY,180)
        code=sum(a!=b for a,b in zip(before[at:at+180],truth))
        self.assertEqual((report['changed_bytes'],report['code_bytes'],report['metadata_bytes'],report['exclusions']),(code+1,code,1,0))
        symbol=next(at for at,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,180),source.elf_slot_offset(pred,source.ENTRY+180,8),
                symbol+8,source.elf_slot_offset(pred,PARENT,92),source.elf_slot_offset(pred,TABLE,296)):
            bad=bytearray(pred);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
        self.receipt['strict']=dict(changed_bytes=code+1,code_bytes=code,metadata_bytes=1,exclusions=0,corruptions=7,focused_inputs=len(self.values))

if __name__=='__main__':unittest.main()
