"""Attachment identity events: byte ABI, late keys, original dispatch and release."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_attachment_event_match as source
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
PARENT,TABLE,RELEASE_TABLE=0x150C5CC4,0x800887C8,0x8008B4D0
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
    owner=(OWNER,PAIR-0xC8,PAIR-0xC4,PAIR-0xC0,PAIR-0xCC,PAIR,STACK+phase+8-0xC8,OWNER)[c.alias]
    return owner,STACK+phase+8 if c.alias==7 else PAIR


def fixture(c,phase=0):
    owner,event=addresses(c,phase);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,n in((owner-32,0x240),(event-32,128)):
        m.update({base+i:(i*13+0x5A)&255 for i in range(n)})
    first=VALUES[c.pattern%6];second=first if c.pattern>=6 else VALUES[(c.pattern+1)%6]
    put(m,event,first);put(m,event+4,second);m[event+8]=17;m[event+9]=231
    put(m,owner+0xC8,(first,second,0xBEEFF00D,0xBEEFF00D)[c.match]);m[owner+0xCC]=c.key
    m[owner]=c.kind;m[owner+0x38]=1
    if c.match==3:m[owner+0xCC]=m[event+4]
    put(m,TABLE,0);put(m,TABLE+4,source.ENTRY)
    for kind in set((c.kind,7)):put(m,RELEASE_TABLE+52*kind,CALLBACK if c.callback else 0)
    return m


def mutation(m,c,owner):
    if c.mutate:m[owner]=7;put(m,owner+0xC8,0xCAFEBABE)


def reference(initial,c,phase=0,chain=False,home=None):
    owner,event=addresses(c,phase);m=dict(initial);calls=[];put(m,STACK+phase+8 if home is None else home,c.command)
    command=c.command&255;state=owner+0xC8
    if command==0:
        current=read(m,state);first=read(m,event)
        if current==first or m[state+4]==m[event+4]:
            calls.append((RELEASE,(owner,)))
            if chain:
                calls.append((BOOKKEEP,(owner,)));mutation(m,c,owner)
                if m[owner]>=2:calls.append((CALLBACK if c.callback else FALLBACK,(owner,)))
            else:mutation(m,c,owner)
    elif command==45:
        current=read(m,state);first=read(m,event)
        if first==current:put(m,state,read(m,event+4));m[state+4]=m[event+9]
        elif read(m,event+4)==current:put(m,state,first);m[state+4]=m[event+8]
    return m,calls


def public(m,c,phase=0):
    owner,_=addresses(c,phase)
    return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+512 or owner+0xC8<=a<owner+0xCD or STACK+phase+8<=a<STACK+phase+12}


class AttachmentOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,arguments=None,release=RELEASE):
        owner,event=addresses(c,phase)
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=arguments or(owner,event,c.command),connected=connected)
        self.case,self.owner,self.phase,self.release=c,owner,phase,release
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def record_call(self,target):
        assert target in(source.ENTRY,self.release,BOOKKEEP,FALLBACK,CALLBACK),hex(target)
        args=self.arguments(3 if target==source.ENTRY else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in(self.release,BOOKKEEP,FALLBACK,CALLBACK)
        if target in(self.release,BOOKKEEP):mutation(self.memory,self.case,self.arguments(1)[0])
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678


def controls():
    b=source.SELECTED
    return dict(and_gate=b.replace(' || ',' && '),wrong_command=b.replace('code == 0x2D','code == 0x2E'),
        wrong_release=b.replace('command == 0)','command == 1)'),wrong_key=b.replace('event[4]','event[5]'),
        wrong_first_key=b.replace('event[9]','event[8]'),wrong_second_key=b.replace('event[8]','event[9]'),
        missing_second=b.replace('*(s32 *)(event + 4) == current','0'),
        wrong_replacement=b.replace('state->value = *(s32 *)(event + 4);','state->value = first;'),
        wrong_owner=b.replace('(struct102 *)owner','(struct102 *)event'),
        early_key=b.replace('state->value = *(s32 *)(event + 4);\n            state->key = event[9];',
            'state->key = event[9];\n            state->value = *(s32 *)(event + 4);'))


def native_harness(values):
    text=values['conker/src/game_1944C0.c'].decode();lo,hi=source.function_span(text,'func_1516972C')
    helper=text[lo:hi].replace('func_1516972C','real_release')
    text=source.HEADERS+source.DECLARATIONS+'''
static u8 *arena,*expected,*currentOwner;
static u32 error,releases,bookkeeps,callbacks,fallbacks,mutationMode,present,expectedRelease;
struct115 D_8008B4D0[256];
void(*D_800887C8[2])(u8*,s32,u8);
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(struct115)==52&&
 __builtin_offsetof(AttachmentIdentityF2820,key)==4)?1:-1];
__attribute__((noinline,noclone)) void func_151696DC(struct102*p){
 if((void*)p!=currentOwner)error=1;bookkeeps++;
 if(mutationMode){currentOwner[0]=7;*(s32*)(void*)(currentOwner+0xC8)=(s32)0xCAFEBABE;}
}
__attribute__((noinline,noclone)) void func_15169804(struct102*p){if((void*)p!=currentOwner)error=1;fallbacks++;}
static void callback(struct102*p){if((void*)p!=currentOwner)error=1;callbacks++;}
'''+helper+'''
__attribute__((noinline,noclone)) void func_1516972C(struct102*p){
 if(!expectedRelease||(void*)p!=currentOwner||releases++){error=1;return;}real_release(p);
}
'''
    for label,body in dict(selected=source.SELECTED,**controls()).items():
        if label!='selected'and body==source.SELECTED:raise ValueError('Ineffective attachment control: '+label)
        text+=body.replace(source.FUNCTION,label)+'\n'
    parent=values[source.SOURCE].decode();lo,hi=source.function_span(parent,'func_150C5CC4');text+=parent[lo:hi]+'\n'
    text+='''
typedef void(*Handler)(u8*,s32,u8);
static const u32 vals[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678};
static int one(Handler fn,u32 command,u32 tag,u32 alias,u32 mutate,u32 wrapper){
 u32 i,pattern=command%6,match=tag%4,kind=(tag&3)==3?255:tag&3;
 u32 ownerAt=(u32[]){0x200,0x100-0xC8,0x100-0xC4,0x100-0xC0,0x100-0xCC,0x100}[alias];
 u32 state=ownerAt+0xC8,first,current,release,afterKind,invoke;
 for(i=0;i<0x400;i++)arena[i]=(u8)(i*13+0x5A);
 *(u32*)(void*)(arena+0x100)=vals[pattern];*(u32*)(void*)(arena+0x104)=vals[(pattern+1)%6];arena[0x108]=17;arena[0x109]=231;
 *(u32*)(void*)(arena+state)=match==0?*(u32*)(void*)(arena+0x100):match==1?*(u32*)(void*)(arena+0x104):0xBEEFF00D;
 arena[state+4]=(u8)tag;arena[ownerAt]=(u8)kind;arena[ownerAt+0x38]=(u8)(wrapper==2?0:1);
 if(match==3)arena[state+4]=arena[0x104];
 for(i=0;i<0x400;i++)expected[i]=arena[i];
 first=*(u32*)(void*)(arena+0x100);current=*(u32*)(void*)(arena+state);invoke=wrapper!=2;
 release=invoke&&(u8)command==0&&(current==first||arena[state+4]==arena[0x104]);
 if(invoke&&(u8)command==45){if(first==current){*(u32*)(void*)(expected+state)=*(u32*)(void*)(expected+0x104);expected[state+4]=expected[0x109];}
 else if(*(u32*)(void*)(expected+0x104)==current){*(u32*)(void*)(expected+state)=first;expected[state+4]=expected[0x108];}}
 mutationMode=mutate;present=tag&1;afterKind=kind;currentOwner=arena+ownerAt;
 if(release&&mutate){expected[ownerAt]=7;*(u32*)(void*)(expected+state)=0xCAFEBABE;afterKind=7;}
 for(i=0;i<256;i++)D_8008B4D0[i].unk0=present?callback:0;
 error=releases=bookkeeps=callbacks=fallbacks=0;expectedRelease=release;
 if(wrapper){D_800887C8[0]=0;D_800887C8[1]=fn;func_150C5CC4(currentOwner,(s32)(arena+0x100),(u8)command);}
 else fn(currentOwner,(s32)(arena+0x100),(u8)command);
 if(error||releases!=release||bookkeeps!=release||callbacks!=(release&&afterKind>=2&&present)||fallbacks!=(release&&afterKind>=2&&!present))return 23;
 for(i=0;i<0x400;i++)if(arena[i]!=expected[i])return 23;
 return 0;
}
static int variant(Handler fn,u32 full){u32 c,t,a,m;
 for(c=0;c<(full?256u:3u);c++)for(t=0;t<256;t++)for(a=0;a<6;a++)for(m=0;m<2;m++)
  if(one(fn,full?c:(u32[]){0,45,255}[c],t,a,m,0))return 23;return 0;}
static void *allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");
 end=p+n;__asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){u32 c,t,w;arena=allocate(0x800);if(!arena)return 97;expected=arena+0x400;
'''
    for i,label in enumerate(dict(selected=source.SELECTED,**controls())):
        text+='if(variant(%s,%d)!=%d)return %d;\n'%(label,int(label=='selected'),0 if label=='selected'else 23,11+i)
    text+='for(c=0;c<256;c++)for(t=0;t<256;t++)for(w=1;w<3;w++)if(one(selected,c,t,0,0,w))return 70;\nreturn 0;}\n'
    return text+START


class AttachmentEventTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);rom=cls.values['conker/conker.us.bin']
        cls.truth=list(struct.unpack_from('>43I',rom,source.ROM));cls.parent=list(struct.unpack_from('>18I',rom,0xF3174))
        cls.helper=list(struct.unpack_from('>28I',rom,0x196BDC))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']))
        cls.slot=data[fs[source.FUNCTION]['value']:fs[source.FUNCTION]['value']+180]
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']))
        old=cls.values['conker/build/conker.us.elf']
        cls.retained_parent=list(struct.unpack_from('>18I',old,source.elf_slot_offset(old,PARENT,72)))
        cls.retained_helper=list(struct.unpack_from('>28I',old,source.elf_slot_offset(old,RELEASE,112)))
    def compare(self,c=Case(),phase=0,chain=False,images=None,entry=source.ENTRY,release=RELEASE):
        initial=fixture(c,phase);expected,calls=reference(initial,c,phase,chain);models=[]
        for words in images or(self.truth,self.words):
            connected={RELEASE+4*i:w for i,w in enumerate(self.helper)}if chain else None
            m=AttachmentOracle(words,initial,c,phase,entry,connected,release=release).run()
            self.assertEqual(public(m.memory,c,phase),public(expected,c,phase),c)
            normalized=[(RELEASE if t==release else t,a)for t,a in m.calls];self.assertEqual(normalized,calls,c);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]
    def test_01_literal_slot_owner_Make_and_registry(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.slot,self.values['conker/conker.us.bin'][source.ROM:source.ROM+180])
        self.assertEqual(self.slot[-8:],bytes(8));self.assertEqual(self.helper,self.retained_helper)
        q=json.loads((self.out/'qualification.json').read_text());mk=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['body_words'],q['slot_words'],q['alignment_words'],q['new_guards'],q['preserved_neighbors']),(43,45,2,5,14))
        self.assertEqual((mk['commands'],mk['compact_functions_equal']),(3,15));self.assertTrue(mk['complete_padded_object_equal'])
        rom=self.values['conker/conker.us.bin'];self.assertEqual(struct.unpack_from('>2I',rom,0x22D288),(0,source.ENTRY))
        old=self.values['conker/build/conker.us.elf'];self.assertEqual(struct.unpack_from('>2I',old,source.elf_slot_offset(old,TABLE,8)),(0,source.ENTRY))
        direct=[];literal=[];call=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        for i in range(0,len(rom)-3,4):
            word=struct.unpack_from('>I',rom,i)[0]
            if word==source.ENTRY:literal.append(i)
            if word==call:direct.append(i)
        self.assertEqual((direct,literal),([],[0x22D28C]))
        self.receipt['owner']=dict(body_words=43,slot_words=45,alignment_words=2,frame=24,bindings=1,guards=5,neighbors=14,Make_commands=3,
            actual_registry_index=1,direct_sites=direct,literal_sites=literal)
    def test_02_byte_ABI_identity_priority_keys_and_aliases(self):
        count=0;visits=set()
        cases=[(Case(upper|command,pattern,match,(0,127,128,255)[pattern%4]),phase)
            for command,pattern,match,(upper,phase)in itertools.product(range(256),range(8),range(4),((0,0),(0xA5A50000,8)))]
        cases.extend((Case(upper|command,pattern,match,key,alias,True),phase)
            for command,pattern,match,key,alias,(upper,phase)in itertools.product((0,45,255),(0,3,7),range(4),(0,128,255),range(1,8),((0,0),(0x87650000,8))))
        cases.extend((Case(command,2,2,key),0)for command,key in itertools.product((0,45),range(256)))
        for c,phase in cases:
            m=self.compare(c,phase);visits.update(m.visits)
            raw=AttachmentOracle(self.raw,fixture(c,phase),c,phase).run();expected,calls=reference(fixture(c,phase),c,phase)
            self.assertEqual(public(raw.memory,c,phase),public(expected,c,phase));self.assertEqual(raw.calls,calls);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+172,4))-{source.ENTRY+132})
        self.receipt['guest']=dict(cases=count,all_command_bytes=True,all_key_bytes=True,full_incoming_command_home=True,
            alias_layouts=8,raw_C_public_semantics_checked=True,fitted_full_private_state_equal=True,reachable_words=42,dead_word=33)
    def test_03_retained_release_helper_and_late_kind(self):
        self.assertEqual(self.helper,self.retained_helper);visits=set();count=0
        for kind,mutate,callback,phase in itertools.product((0,1,2,255),(False,True),(False,True),(0,8)):
            c=Case(0,1,0,255,0,mutate,kind,callback);m=self.compare(c,phase,True);visits.update(m.visits);count+=1
        self.assertTrue(set(range(RELEASE,RELEASE+112,4))<=visits)
        self.receipt['release']=dict(cases=count,all_28_original_and_retained_words_visited=True,late_kind_reload=True,
            pre_bookkeeping_and_callback_fallback_are_bounded_contracts=True,no_new_helper_credit=True)
    def test_04_original_and_retained_dispatchers(self):
        count=0
        for parent in(self.parent,self.retained_parent):
            for command,index,phase in itertools.product(range(256),(0,1),(0,8)):
                c=Case(0xA5000000|command,command%6,command%4,command,0,True);initial=fixture(c,phase)
                initial[OWNER+0x38]=index;expected,calls=reference(initial,c,phase)
                # The dispatcher masks A2 before the callback stores its own home.
                if not index:expected=dict(initial);put(expected,STACK+phase+8,c.command);calls=[]
                pair=[]
                for words in(self.truth,self.words):
                    connected={source.ENTRY+4*i:w for i,w in enumerate(words)}
                    m=AttachmentOracle(parent,initial,c,phase,PARENT,connected).run()
                    want=[(source.ENTRY,(OWNER,PAIR,command)),*calls]if index else[]
                    self.assertEqual(m.calls,want);self.assertEqual(public(m.memory,c,phase),public(expected,c,phase));pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.receipt['caller']=dict(cases=count,original_words=18,retained_words=18,actual_table_entries=2,
            canonical_callback_signature='void(u8*,s32,u8)',byte_mask_before_indirect_call=True,whole_parent_gameplay_claimed=False)
    def test_05_native32_actual_C_release_and_typed_dispatch(self):
        text=native_harness(self.values)
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=120).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],target_cases_per_profile=256*256*6*2,
            dispatcher_cases_per_profile=256*256*2,effective_controls=len(controls()),trap_UBSan=True,actual_retained_release_C=True,
            heap_backed_typeless_fixture=True,canonical_function_pointer_interface=True)
    def test_06_fault_prefixes_and_effective_hoisted_read_negative(self):
        count=0
        for c in(Case(0,0,0),Case(0,0,2),Case(0,0,3),Case(45,1,0),Case(45,3,1),Case(45,2,2),Case(45,2,0,255,3),Case(0,1,0,255,6)):
            initial=fixture(c);m=self.compare(c)
            for fault in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=AttachmentOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        for command in(1,44,46,127,128,255):
            c=Case(command);initial={a:b for a,b in fixture(c).items()if STACK-2048<=a<STACK+512}
            for words in(self.truth,self.words,self.raw):AttachmentOracle(words,initial,c).run()
        bad=source.SELECTED.replace('    s32 code = command;','    s32 code = command;\n    (void)*(volatile s32 *)&state->value;')
        obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.DECLARATIONS+bad,'negative-hoisted-read');self.assertFalse(diag)
        data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);info=fs[source.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        c=Case(255);initial={a:b for a,b in fixture(c).items()if STACK-2048<=a<STACK+512}
        with self.assertRaisesRegex(AssertionError,'unmapped read'):AttachmentOracle(words,initial,c).run()
        self.receipt['faults']=dict(prefix_pairs=count,ignored_modes_need_no_packet_or_owner_mapping=True,
            actual_compiled_MIPS_early_read_negative_effective=True,emitted_guest_access_order_only=True)
    def test_07_literal_guard_controls_real_padder_and_rebases(self):
        raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        for i in range(43):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        with self.assertRaises(ValueError):source.normalized(raw,{68:[('R_MIPS_26','wrong')]})
        with self.assertRaises(ValueError):source.normalized(raw[:-4],rs)
        with self.assertRaises(ValueError):source.guard_bytes(self.values['conker/retail_word_patches.us.csv']+b'\n',raw,rs)
        guard=(self.out/'qualified-guards.csv').read_text();prefix=self.values['conker/retail_word_patches.us.csv'].decode()
        self.assertTrue(guard.startswith(prefix.replace('\r\n','\n')))
        tail=guard[len(prefix.replace('\r\n','\n')):];self.assertIn('0x8C430000',tail)
        path=self.out/'negative-real-padder.csv';path.write_text(guard[:-len(tail)]+tail.replace('0x8C430000','0x8C430001',1))
        with self.assertRaises((ValueError,RuntimeError)):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
        fitted,bindings=source.normalized(raw,rs);asm,missing=emit_function(fitted,dict(value=0,size=172),bindings,source.FUNCTION,dict(func_1516972C=RELEASE))
        self.assertFalse(missing);p=self.out/'independent-fitted.s';p.write_text(asm);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
        links=0
        for i,(entry,release)in enumerate(((source.ENTRY,RELEASE),(source.ENTRY+0x200000,RELEASE+0x300000),(source.ENTRY+0x500000,RELEASE+0x700000))):
            images=[]
            for j,object_ in enumerate((source.original(ROOT,self.out),obj)):
                p=self.out/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,
                    '--defsym=func_1516972C=0x%X'%release,'-o',str(elf),str(object_)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>43I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for c in(Case(0),Case(45,3,0),Case(45,3,1),Case(255)):self.compare(c,images=images,entry=entry,release=release)
        self.receipt['guards_links']=dict(raw_word_controls=43,binding_controls=1,extent_controls=1,history_controls=1,
            real_padder_controls=1,independent_GNU_links=links,layouts=3,call_binding_rebased=True)
    def test_08_strict_full_image_and_frozen_inputs(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+180]
        pred=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        report=json.loads((self.out/'first-link.json').read_text());self.assertEqual((report['changed_bytes'],report['code_bytes'],report['metadata_bytes'],report['exclusions']),(119,118,1,0))
        symbol=next(at for at,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,180),source.elf_slot_offset(pred,source.ENTRY+172,8),
                symbol+8,source.elf_slot_offset(pred,PARENT,72),source.elf_slot_offset(pred,TABLE,8)):
            bad=bytearray(pred);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
        self.receipt['strict']=dict(changed_bytes=119,code_bytes=118,metadata_bytes=1,exclusions=0,corruptions=7,focused_inputs=len(self.values))

if __name__=='__main__':unittest.main()
