"""Owner link event gate: ordered guest model and canonical callback execution."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_owner_link_event_gate_match as source
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

PAIR,OWNER=0x20000,0x30000
RELEASE,BOOKKEEP,FALLBACK,CALLBACK=0x1516972C,0x151696DC,0x15169804,0x16200000
PARENT,TABLE,RELEASE_TABLE=source.PARENT,source.TABLE,0x8008B4D0
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
    enabled:bool=True


def addresses(c,phase=0):
    owner=(OWNER,PAIR-0x28,PAIR-0x24,PAIR-0x20,PAIR-0x2C,PAIR,STACK+phase+8-0x28,OWNER,OWNER)[c.alias]
    event=STACK+phase+8 if c.alias==7 else STACK+phase-16 if c.alias==8 else PAIR
    return owner,event


def fixture(c,phase,registry):
    if len(registry)!=74:raise ValueError('Supply the actual 74-entry actor event registry')
    owner,event=addresses(c,phase);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,n in((owner-32,0x140),(event-32,128)):
        m.update({base+i:(i*13+0x5A)&255 for i in range(n)})
    first=VALUES[c.pattern%6];second=first if c.pattern>=6 else VALUES[(c.pattern+1)%6]
    put(m,event,first);put(m,event+4,second);m[event+8]=17;m[event+9]=231
    put(m,owner+0x28,(first,second,0xBEEFF00D,0xBEEFF00D)[c.match]);m[owner+0x2C]=c.key
    m[owner]=c.kind;m[owner+0x13]=40
    if c.match==3:m[owner+0x2C]=m[event+4]
    for i,target in enumerate(registry):put(m,TABLE+4*i,target)
    for kind in set((c.kind,7)):put(m,RELEASE_TABLE+52*kind,CALLBACK if c.callback else 0)
    return m


def mutation(m,c,owner):
    if c.mutate:m[owner]=7;put(m,owner+0x28,0xCAFEBABE)


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
    elif command in(0,3,47):
        first=read(m,event);current=read(m,state)
        if first==current or m[state+4]==m[event+4]:
            calls.append((RELEASE,(owner,)))
            if chain:
                calls.append((BOOKKEEP,(owner,)));mutation(m,c,owner);outgoing_homes(m,sp-48)
                if m[owner]>=2:calls.append((CALLBACK if c.callback else FALLBACK,(owner,)))
            else:mutation(m,c,owner);outgoing_homes(m,sp-24)
    return m,calls


def public(m,c,phase=0,child=False):
    owner,event=addresses(c,phase)
    def relevant(a):
        return (not STACK-2048<=a<STACK+512 or owner+0x28<=a<owner+0xAD or
            event<=a<event+10 or STACK+phase+8<=a<STACK+phase+12 or
            child and STACK+phase-16<=a<STACK+phase-12)
    return {a:b for a,b in m.items()if relevant(a)}


class EmbeddedOwnerOracle(RayOracle):
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
    q=dict(missing3=b.replace(' || command == 3',''),missing47=b.replace(' || command == 0x2F',''),
        wrong_command=b.replace('command == 0x2D','command == 0x2E'),
        and_gate=b.replace('first == link->owner ||','first == link->owner &&'),
        wrong_key=b.replace('((u8 *)event)[4]','event->before_identity'),
        wrong_first_key=b.replace('event->after_identity','event->before_identity'),
        wrong_second_key=b.replace('link->identity = event->before_identity;','link->identity = event->after_identity;'),
        missing_second=b.replace('current == event->after','0'),
        wrong_replacement=b.replace('link->owner = event->after;','link->owner = event->before;'),
        wrong_owner=b.replace('func_1516972C((struct102 *)owner);','func_1516972C((struct102 *)event);'),
        early_key=b.replace('link->owner = event->after;','u8 savedIdentity = event->after_identity;\n            link->owner = event->after;').replace('link->identity = event->after_identity;','link->identity = savedIdentity;'),
        wrong_priority=b.replace('current == event->before','current == event->before && current != event->after'))
    assert all(x!=b for x in q.values())
    return q

def native_harness(values):
    text=values['conker/src/game_1944C0.c'].decode();lo,hi=source.function_span(text,'func_1516972C')
    helper=text[lo:hi].replace('func_1516972C','real_release')
    registry=struct.unpack_from('>74I',values['conker/conker.us.bin'],source.TABLE_ROM)
    others=sorted(set(registry)-{0,source.ENTRY})
    text=source.HEADERS+'''
static u8 *arena,*expected,*currentOwner;
static void putPointer(u8 *p,u32 bits){u8 *v=(u8*)bits;__builtin_memcpy(p,&v,4);}
static u32 pointerBits(const u8 *p){u32 v;__builtin_memcpy(&v,p,4);return v;}
static u32 error,releases,bookkeeps,callbacks,fallbacks,mutationMode,present,expectedRelease;
static u32 providerCalls,seenProvider,expectedEvent,expectedCommand;
static u32 coverage[256];
struct115 D_8008B4D0[256];
void(*D_8008A8D8[74])(struct260*,s32,u8);
typedef void(*Handler)(struct260*,s32,u8);
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(struct115)==52&&
 sizeof(EmbeddedOwnerLink)==8&&__builtin_offsetof(EmbeddedOwnerLink,owner)==0&&
 __builtin_offsetof(EmbeddedOwnerLink,identity)==4)?1:-1];
__attribute__((noinline,noclone)) void func_151696DC(struct102*p){
 if((void*)p!=currentOwner)error=1;bookkeeps++;
 if(mutationMode){currentOwner[0]=7;putPointer(currentOwner+0x28,(u32)(arena+0x900));}
}
__attribute__((noinline,noclone)) void func_15169804(struct102*p){if((void*)p!=currentOwner)error=1;fallbacks++;}
static void callback(struct102*p){if((void*)p!=currentOwner)error=1;callbacks++;}
'''+helper+'''
__attribute__((noinline,noclone)) void func_1516972C(struct102*p){
 if(!expectedRelease||(void*)p!=currentOwner||releases++){error=1;return;}real_release(p);
}
static void provider(struct260*p,s32 event,u8 command,u32 address){
 if((void*)p!=currentOwner||(u32)event!=expectedEvent||command!=expectedCommand||providerCalls++)error=1;
 seenProvider=address;*(u32*)(void*)((u8*)p+0x34)=address^command;
}
'''
    for address in others:
        text+='static void provider_%X(struct260*p,s32 e,u8 c){provider(p,e,c,0x%Xu);}\n'%(address,address)
    for label,body in dict(selected=source.SELECTED,**controls()).items():
        if label!='selected'and body==source.SELECTED:raise ValueError('Ineffective record-event control: '+label)
        text+=body.replace(source.FUNCTION,label)+'\n'
    parent=values[source.CALLER_SOURCE].decode();lo,hi=source.function_span(parent,'func_15149434');text+=parent[lo:hi]+'\n'
    text+='static const u32 registry[74]={'+','.join('0x%Xu'%x for x in registry)+'};\n'
    text+='static void install(Handler fn){\n'
    for i,address in enumerate(registry):
        text+='D_8008A8D8[%d]=%s;\n'%(i,'fn'if address==source.ENTRY else'provider_%X'%address if address else'0')
    text+='}\n'+'''
static u32 vals[6];
static int one(Handler fn,u32 command,u32 tag,u32 alias,u32 mutate,u32 selector){
 u32 i,pattern=(command+(tag>>2))%8,match=tag%4,kind=(tag&3)==3?255:tag&3;
 u32 ownerAt=(u32[]){0x200,0x100-0x28,0x100-0x24,0x100-0x20,0x100-0x2C,0x100}[alias];
 u32 state=ownerAt+0x28,first,current,release,afterKind,invoke,target,other;
 if(selector==256&&fn==selected)coverage[(u8)command]|=1u<<(4*pattern+match);
 for(i=0;i<0x400;i++)arena[i]=(u8)(i*13+0x5A);
 putPointer(arena+0x100,vals[pattern%6]);
 putPointer(arena+0x104,pattern>=6?vals[pattern%6]:vals[(pattern+1)%6]);
 arena[0x108]=17;arena[0x109]=231;
 putPointer(arena+state,match==0?pointerBits(arena+0x100):match==1?pointerBits(arena+0x104):(u32)(arena+0x980));
 arena[state+4]=(u8)tag;arena[ownerAt]=(u8)kind;arena[ownerAt+0x13]=(u8)selector;
 if(match==3)arena[state+4]=arena[0x104];
 for(i=0;i<0x400;i++)expected[i]=arena[i];
 first=pointerBits(arena+0x100);current=pointerBits(arena+state);
 target=selector==256?0x150D596Cu:registry[selector<74?selector:0];
 invoke=target==0x150D596Cu;other=target&&!invoke;
 release=invoke&&((u8)command==0||(u8)command==3||(u8)command==47)&&(first==current||arena[state+4]==arena[0x104]);
 if(invoke&&(u8)command==45){if(first==current){putPointer(expected+state,pointerBits(expected+0x104));expected[state+4]=expected[0x109];}
 else if(pointerBits(expected+0x104)==current){putPointer(expected+state,first);expected[state+4]=expected[0x108];}}
 if(other)*(u32*)(void*)(expected+ownerAt+0x34)=target^(u8)command;
 mutationMode=mutate;present=tag&1;afterKind=kind;currentOwner=arena+ownerAt;
 if(release&&mutate){expected[ownerAt]=7;putPointer(expected+state,(u32)(arena+0x900));afterKind=7;}
 for(i=0;i<256;i++)D_8008B4D0[i].unk0=present?callback:0;
 error=releases=bookkeeps=callbacks=fallbacks=providerCalls=seenProvider=0;expectedRelease=release;
 expectedEvent=(u32)(arena+0x100);expectedCommand=(u8)command;
 if(selector!=256){install(fn);func_15149434((struct260*)(void*)currentOwner,(s32)(arena+0x100),(u8)command);}
 else fn((struct260*)(void*)currentOwner,(s32)(arena+0x100),(u8)command);
 if(error||providerCalls!=other||seenProvider!=(other?target:0)||releases!=release||bookkeeps!=release||
 callbacks!=(release&&afterKind>=2&&present)||fallbacks!=(release&&afterKind>=2&&!present))return 23;
 for(i=0;i<0x400;i++)if(arena[i]!=expected[i])return 23;
 return 0;
}
static int variant(Handler fn,u32 full){u32 c,t,a,m;
 for(c=0;c<(full?256u:5u);c++)for(t=0;t<256;t++)for(a=0;a<6;a++)for(m=0;m<2;m++)
  if(one(fn,full?c:(u32[]){0,3,47,45,255}[c],t,a,m,256))return 23;return 0;}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u32 c,s,m;arena=allocate(0x1000);if(!arena)return 97;expected=arena+0x400;
 if((u32)arena&0xFFF)return 98;
 for(c=0;c<6;c++)vals[c]=(u32)(arena+0x800+0x120*c);
'''
    for i,label in enumerate(dict(selected=source.SELECTED,**controls())):
        text+='if(variant(%s,%d)!=%d)return %d;\n'%(label,int(label=='selected'),0 if label=='selected'else 23,11+i)
    text+='for(c=0;c<256;c++)if(coverage[c]!=0xFFFFFFFFu)return 68;\n'
    text+='for(c=0;c<256;c++)for(s=0;s<256;s++)for(m=0;m<2;m++)if(one(selected,c,c,0,m,s))return 70;\n'
    text+='vals[0]=0;if(one(selected,0,0,0,0,256)||one(selected,45,12,0,0,256))return 71;\nreturn 0;}\n'
    return text+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')



def images(root):
    p=root/source.BUILD;values=source.snapshot(p);rom=values['conker/conker.us.bin']
    raw,bindings=source.checked_payload(*source.payload(p/'selected.o'))
    fitted,_=source.normalized_payload(raw,bindings)
    def resolve(b):
        words=list(struct.unpack('>48I',b));words[22]=0x0C000000|(RELEASE>>2&0x3FFFFFF);return words
    truth=list(struct.unpack_from('>48I',rom,source.ROM));assert resolve(fitted)==truth
    table=struct.unpack_from('>74I',rom,source.TABLE_ROM);assert table[40]==source.ENTRY
    return values,(truth,resolve(fitted),resolve(raw)),table


def compare(root,c,phase=0,chain=False,variants=None,entry=None,release=RELEASE):
    values,default,registry=images(root) if variants is None else variants
    words=default;entry=source.ENTRY if entry is None else entry
    initial=fixture(c,phase,registry);expected,calls=reference(initial,c,phase,chain);models=[]
    helper=list(struct.unpack_from('>28I',values['conker/conker.us.bin'],0x196BDC))
    for code in words:
        connected={release+4*i:w for i,w in enumerate(helper)} if chain else None
        m=EmbeddedOwnerOracle(code,initial,c,phase,entry,connected,release=release).run()
        assert public(m.memory,c,phase)==public(expected,c,phase),(c,phase,'memory')
        assert [(RELEASE if t==release else t,a)for t,a in m.calls]==calls,(c,phase,'calls')
        models.append(m)
    assert complete(models[0])==complete(models[1]),(c,phase,'full state')
    return models


def guest_checks(root,output):
    bundle=images(root);visits=set();count=0
    cases=[(Case(upper|command,command%8,command%4,(0,127,128,255)[command%4],alias),phase)
        for command,alias,(upper,phase)in itertools.product(range(256),(0,6,7,8),((0,0),(0xA5A50000,8)))]
    cases.extend((Case(upper|command,pattern,match,key,alias,True),phase)
        for command,pattern,match,key,alias,(upper,phase)in itertools.product((0,3,47,45),range(8),range(4),(0,127,128,255),range(9),((0,0),(0x87650000,8))))
    cases.extend((Case(command,2,2,key),0)for command,key in itertools.product((0,3,47,45),range(256)))
    for c,phase in cases:
        m=compare(root,c,phase,variants=bundle)[0];visits.update(m.visits);count+=1
    expected=set(range(source.ENTRY,source.ENTRY+192,4))-{source.ENTRY+104,source.ENTRY+152}
    assert visits==expected,sorted(x-source.ENTRY for x in expected^visits)
    return dict(cases=count,reachable_words=len(visits),unreachable_offsets=[104,152],all48_literal_words_preserved=True,
        all_command_bytes=True,all_identity_bytes=True,alias_layouts=9,full_incoming_command_home=True,
        raw_C_public_semantics=True,normalized_full_state=True,supported_commands_full_pattern_match_key_alias_matrix=True)


def release_checks(root,output):
    values,words,registry=images(root);rom=values['conker/conker.us.bin'];before=values['conker/build/conker.us.elf']
    helper=rom[0x196BDC:0x196C4C];assert len(helper)==112
    at=source.elf_slot_offset(before,RELEASE,112);assert before[at:at+112]==helper
    count=0;visits=set()
    for command,kind,mutate,callback,phase in itertools.product((0,3,47),(0,1,2,255),(False,True),(False,True),(0,8)):
        c=Case(command,1,0,255,0,mutate,kind,callback)
        m=compare(root,c,phase,True,variants=(values,words,registry))[0];visits.update(m.visits);count+=1
    assert set(range(RELEASE,RELEASE+112,4))<=visits
    return dict(cases=count,retained_helper_words=28,all_helper_words_visited=True,late_kind_reload=True,
        bookkeeping_callback_fallback_are_bounded=True,no_new_helper_credit=True)


def caller_checks(root,output):
    values,words,registry=images(root);rom=values['conker/conker.us.bin'];old=values['conker/build/conker.us.elf']
    at=PARENT-0x15000000+0x2D4B0;parent=rom[at:at+92];at=source.elf_slot_offset(old,PARENT,92);retained=old[at:at+92]
    assert parent==retained
    assert struct.unpack_from('>74I',old,source.elf_slot_offset(old,TABLE,296))==registry
    allwords=struct.unpack('>%dI'%(len(rom)//4),rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(source.ENTRY>>2&0x3FFFFFF)
    assert [4*i for i,w in enumerate(allwords)if w==source.ENTRY]==[0x22F438]
    assert not any(w in(jal,jump)for w in allwords)
    count=entered=0;visits=set()
    cases=[(Case(0xA5000000|command,command%8,command%4,command,0,True),index,phase)
        for command,index,phase in itertools.product((0,3,47,45,255),range(256),(0,8))]
    cases.extend((Case(0xA5000000|command,command%8,command%4,command,0,True),index,phase)
        for command,index,phase in itertools.product(range(256),(0,40,73,74,127,128,255),(0,8)))
    cases.extend((Case(command,pattern,match,255,alias,True),40,phase)
        for command,pattern,match,alias,phase in itertools.product((0,3,47,45,255),(0,7),range(4),range(1,9),(0,8)))
    for parentbytes in(parent,retained):
        for c,index,phase in cases:
            owner,event=addresses(c,phase);initial=fixture(c,phase,registry);initial[owner+0x13]=index
            expected=dict(initial);put(expected,STACK+phase+8,c.command)
            chosen=registry[index if index<74 else 0];command=c.command&255;calls=[]
            if chosen==source.ENTRY:
                expected,tail=reference(expected,c,phase,incoming_sp=STACK+phase-24,incoming_command=command)
                calls=[(source.ENTRY,(owner,event,command)),*tail]
            elif chosen:
                put(expected,owner+0x34,chosen^command);outgoing_homes(expected,STACK+phase-24)
                calls=[(chosen,(owner,event,command))]
            pair=[]
            for code in words[:2]:
                connected={source.ENTRY+4*i:w for i,w in enumerate(code)}
                m=EmbeddedOwnerOracle(list(struct.unpack('>23I',parentbytes)),initial,c,phase,PARENT,connected,providers=registry).run()
                assert m.calls==calls,(c,index,m.calls,calls)
                assert public(m.memory,c,phase,True)==public(expected,c,phase,True),(c,index,'memory')
                pair.append(m)
            assert complete(pair[0])==complete(pair[1]);visits.update(pair[0].visits);count+=1
            entered+=sum(t==source.ENTRY for t,_ in pair[0].calls)
    assert entered and set(range(PARENT,PARENT+92,4))<=visits
    return dict(cases=count,target_calls=entered,original_current_caller_words=23,all_caller_words_visited=True,
        registry_entries=74,registry_index=40,selector_offset=19,unsigned_selector_clamps_to_zero=True,
        all_command_and_selector_bytes=True,canonical_ABI='void(struct260*,s32,u8)',direct_sites=0,literal_site='0x22f438',
        actual_registry_bytes_equal=True,other_providers_bounded=True)


def native_checks(root,output):
    values,_,_=images(root);text=native_harness(values);rows=[]
    for opt in('-O0','-O2','-O3'):
        p=output/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('')
        command=native_command(opt)+['-mstackrealign','-fno-strict-aliasing',str(p),'-o',str(binary)]
        result=subprocess.run(command,cwd=root,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
        result=subprocess.run([str(binary)],capture_output=True,timeout=120);assert result.returncode==0,(opt,result.returncode,result.stdout,result.stderr)
        rows.append(dict(profile=opt[1:],target_cases=256*256*6*2+2,dispatcher_cases=256*256*2,effective_controls=len(controls()),exit=0))
    return dict(profiles=rows,trap_UBSan=True,actual_C_dispatcher_and_release=True,allocated32bit_pointer_storage=True,
        strict_aliasing_disabled=True,aligned_start=True,canonical_function_pointer_type=True)


def fault_checks(root,output):
    bundle=images(root);values,words,registry=bundle;count=0
    for c,phase in itertools.product((Case(0,0,0),Case(3,0,2),Case(47,0,3),Case(45,1,0),Case(45,3,1),Case(45,2,2),Case(45,2,0,255,3),Case(0,1,0,255,6)),(0,8)):
        initial=fixture(c,phase,registry);m=compare(root,c,phase,variants=bundle)[0]
        for fault in range(m.root_accesses):
            pair=[]
            for code in words[:2]:
                x=EmbeddedOwnerOracle(code,initial,c,phase);x.root_fault=fault
                try:x.run()
                except faults.AccessBoundary:pass
                else:raise AssertionError('fault not fired')
                assert x.root_accesses==fault;pair.append(x)
            assert complete(pair[0])==complete(pair[1]);count+=1
    for command,phase in itertools.product((x for x in range(256)if x not in(0,3,47,45)),(0,8)):
        c=Case(command);initial={a:b for a,b in fixture(c,phase,registry).items()if STACK-2048<=a<STACK+512}
        for code in words:EmbeddedOwnerOracle(code,initial,c,phase).run()
    return dict(fired_prefix_pairs=count,ignored_commands_need_no_owner_or_event_mapping=True,emitted_guest_access_order_only=True)


def rebase_checks(root,output):
    import csv,io
    values,words,registry=images(root);p=root/source.BUILD;raw,rs=source.payload(p/'selected.o');reject=0
    for i in range(48):
        bad=bytearray(raw);bad[4*i+3]^=1
        try:source.normalized_payload(bytes(bad),rs)
        except ValueError:reject+=1
        else:raise AssertionError('word corruption accepted')
    for bad,bindings in((raw,{88:[('R_MIPS_26','wrong')]}),(raw[:-4],rs)):
        try:source.normalized_payload(bad,bindings)
        except ValueError:reject+=1
        else:raise AssertionError('extent/binding corruption accepted')
    try:source.guard_manifest(values['conker/retail_word_patches.us.csv']+b'\n')
    except ValueError:reject+=1
    else:raise AssertionError('history corruption accepted')
    guard=(p/'proposed-word-patches.csv').read_text();bad=output/'bad-guards.csv';bad.write_text(guard.replace('0x8C430000,0x8C440000','0x8C430001,0x8C440000'))
    assert bad.read_text()!=guard
    try:source.emit_padded_assembly(p/'after-owner.o',root/source.ASM,word_patches_path=bad,filename=source.OWNER)
    except (ValueError,RuntimeError):reject+=1
    else:raise AssertionError('padder accepted changed expected word')
    fitted,bindings=source.normalized_payload(raw,rs);asm,missing=emit_function(fitted,dict(value=0,size=192),bindings,source.FUNCTION,dict(func_1516972C=RELEASE));assert not missing
    s=output/'fitted.s';s.write_text(asm);obj=s.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(s)],capture_output=True,check=True)
    links=cases=0
    for i,(entry,release)in enumerate(((source.ENTRY,RELEASE),(source.ENTRY+0x200000,RELEASE+0x300000),(source.ENTRY+0x500000,RELEASE+0x700000))):
        variants=[]
        for j,object_ in enumerate((p/('original-'+source.FUNCTION+'.o'),obj,p/'selected.o')):
            script=output/('rebase-%d-%d.ld'%(i,j));elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,'--defsym=func_1516972C=0x%X'%release,'-o',str(elf),str(object_)],capture_output=True,check=True)
            variants.append(list(struct.unpack_from('>48I',sections(elf)['.text'][1])));links+=1
        assert variants[0]==variants[1]
        for c in(Case(0),Case(3),Case(47),Case(45,3,0),Case(45,3,1),Case(255)):
            compare(root,c,variants=(values,variants,registry),entry=entry,release=release);cases+=1
    negatives={k:controls()[k]for k in('missing3','missing47','wrong_key')}
    negatives['early_read']=source.SELECTED.replace('    if (command == 0 ||','    (void)*(u8 * volatile *)&link->owner;\n    if (command == 0 ||')
    effective=[]
    for name,body in negatives.items():
        obj,diag=source.compile_owner(root,output,source.HEADERS+body,'negative-'+name);assert not diag
        data,syms=source.link_owner(root,output,obj,source.OWNER);f=syms[source.FUNCTION];code=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        c={'missing3':Case(3),'missing47':Case(47),'wrong_key':Case(0,0,3),'early_read':Case(255)}[name];initial=fixture(c,0,registry)
        if name=='early_read':
            initial={a:b for a,b in initial.items()if STACK-2048<=a<STACK+512}
            try:EmbeddedOwnerOracle(code,initial,c).run()
            except AssertionError as e:assert 'unmapped read'in str(e)
            else:raise AssertionError('early-read control ineffective')
        else:
            expected,calls=reference(initial,c);m=EmbeddedOwnerOracle(code,initial,c).run()
            assert m.calls!=calls or public(m.memory,c)!=public(expected,c),name
        effective.append(name)
    return dict(GNU_links=links,layouts=3,rebased_cases=cases,rejection_controls=reject,actual_IDO_effective_controls=effective)
