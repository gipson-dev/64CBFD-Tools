"""Record color commands: canonical callback ABI, complete dispatcher and literal image."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_color_command_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
RECORD,RGB,PRIORITY,ACTIVE=0x30000,0x800DCD20,0x800DCD27,0x800DCD7C

def fixture(command,seed=0x59,phase=0,layout=0,priority=17):
    p=(RECORD,PRIORITY-17,RGB-17,STACK+phase+8-17,STACK+phase-16-17)[layout]
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-256,128)}
    m.update({p+i:(i*13+0x5A)&255 for i in range(64)})
    m.update({RGB+i:0x87+i for i in range(8)});put(m,ACTIVE,0x12345678)
    m[PRIORITY]=priority;m[p+17]=seed
    return m,p

def public(m,p):return {a:b for a,b in m.items()if not STACK-256<=a<STACK+128 or a==p+17}

def reference(initial,p,event,command,sp,chain=False):
    m=dict(initial);put(m,sp+8,command);put(m,sp,p);put(m,sp+4,event);c=command&255;calls=[]
    if c in(76,77,78,79):m[p+17]=30 if c==77 else 255
    if c in(76,79):
        v=0 if c==76 else 255;calls=[(source.HELPER,(v,v,v,255))]
        if chain:
            put(m,sp-24+12,255)
            m[RGB]=m[RGB+1]=m[RGB+2]=v;put(m,ACTIVE,1);m[PRIORITY]=255
        else:
            for i in range(4):put(m,sp-24+4*i,0xB5000000+i)
    return m,calls

class ColorOracle(RayOracle):
    def __init__(self,words,memory,p,command,event=0xDEAD4320,phase=0,entry=source.ENTRY,connected=None,helper=source.HELPER,providers=()):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=(p,event,command),connected=connected)
        self.helper,self.providers,self.p=helper,set(providers)-{0,source.ENTRY},p
        self.observed=[];self.hi=0x89ABCDEF;self.lo=0x76543210;self.condition=True
    def record_call(self,target):
        assert target in(self.helper,source.ENTRY)or target in self.providers,hex(target)
        args=self.arguments(4 if target==self.helper else 3);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.helper:self.observed.append(self.memory.get(self.p+17))
    def hook(self,target):
        assert target==self.helper or target in self.providers
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678

def controls():
    b=source.SELECTED
    result=dict(wrong_black=b.replace('(0, 0, 0, 255)','(255, 0, 0, 255)'),
        wrong_white=b.replace('(255, 255, 255, 255)','(0, 255, 255, 255)'),
        wrong_priority=b.replace(', 255);',', 254);'),
        wrong_timer=b.replace('= 30;','= 31;'),
        wrong_byte=b.replace('record->unk11','record->unk10'),
        missing_4E=b.replace('command == 0x4E','command == 0x5E'),
        wrong_sentinel=b.replace('= -1;','= 0;'),
        late_store=b.replace('record->unk11 = -1;\n        func_1515D4D4(0, 0, 0, 255);','func_1515D4D4(0, 0, 0, 255);\n        record->unk11 = -1;'))
    assert all(x!=b for x in result.values());return result

def native_harness(values,registry):
    text=source.HEADERS+source.DECLARATIONS+'''
static struct260 record,expected;
static u32 calls,error,otherCalls,expectedCalls,observedCommand,expectedCommand,expectedEvent;
static u8 expectedTimer,expectedValue;
u8 D_800DCD20[8],D_800DCD27;
s32 D_800DCD7C;
void(*D_8008A8D8[74])(struct260*,s32,u8);
typedef void(*Handler)(struct260*,s32,u8);
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(u8)==1&&
 __builtin_offsetof(struct260,unk11)==17&&__builtin_offsetof(struct260,unk13)==19)?1:-1];
'''
    provider=values['conker/src/game/generated_18A8F0.c'].decode();lo,hi=source.function_span(provider,'func_1515D4D4');text+=provider[lo:hi].replace('func_1515D4D4','real_color')+'\n'
    text+='''__attribute__((noinline,noclone)) void func_1515D4D4(s32 r,s32 g,s32 b,u8 priority){
 if(!expectedCalls||calls++||r!=expectedValue||g!=expectedValue||b!=expectedValue||priority!=255||(u8)record.unk11!=expectedTimer)error=1;
 real_color(r,g,b,priority);
}
static void other(struct260*p,s32 event,u8 command){
 if(p!=&record||(u32)event!=expectedEvent||command!=expectedCommand||otherCalls++)error=1;
 observedCommand=command;
}
'''
    for label,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,label)+'\n'
    parent=values['conker/src/game/done/game_1765E0.c'].decode();lo,hi=source.function_span(parent,'func_15149434');text+=parent[lo:hi]+'\n'
    text+='static const u32 registry[74]={'+','.join('0x%Xu'%x for x in registry)+'};\n'
    text+='''static void install(Handler fn){u32 i;for(i=0;i<74;i++)D_8008A8D8[i]=!registry[i]?0:registry[i]==0x150FA468u?fn:other;}
static int one(Handler fn,u32 command,u32 seed,u32 priority,u32 selector,u32 event,u32 indirect){
 u32 i,c=command&255,selected=selector<74?registry[selector]:0;u8 *p=(u8*)&record,*q=(u8*)&expected;
 for(i=0;i<sizeof(record);i++)p[i]=q[i]=(i*13+seed)&255;
 record.unk13=expected.unk13=selector;record.unk11=expected.unk11=(s8)seed;
 calls=error=otherCalls=0;expectedCommand=c;expectedEvent=event;observedCommand=999;
 expectedCalls=(!indirect||selected==0x150FA468u)&&(c==76||c==79);expectedTimer=c==77?30:255;expectedValue=c==76?0:255;
 if((!indirect||selected==0x150FA468u)&&c>=76&&c<=79)expected.unk11=expectedTimer;
 for(i=0;i<8;i++)D_800DCD20[i]=0x87+i;D_800DCD27=priority;D_800DCD7C=0x12345678;
 if(indirect){install(fn);func_15149434(&record,(s32)event,(u8)command);}else fn(&record,(s32)event,(u8)command);
 if(error||calls!=expectedCalls||otherCalls!=(indirect&&selected&&selected!=0x150FA468u))return 1;
 for(i=0;i<sizeof(record);i++)if(p[i]!=q[i])return 1;
 for(i=0;i<8;i++)if(D_800DCD20[i]!=(i<3&&expectedCalls?expectedValue:(u8)(0x87+i)))return 1;
 return D_800DCD27!=(expectedCalls?255:priority)||D_800DCD7C!=(expectedCalls?1:0x12345678);
}
static int variant(Handler fn){u32 c,s,p,h;for(c=0;c<256;c++)for(s=0;s<4;s++)for(p=0;p<3;p++)for(h=0;h<2;h++)
 if(one(fn,c|(h?0xFFFFFF00u:0),(u32[]){0,30,128,255}[s],(u32[]){0,254,255}[p],65,h?0xDEAD4320u:0,0))return 23;return 0;}
int run(void){u32 c,s,p;if(variant(selected))return 1;
'''
    for i,name in enumerate(controls()):text+='if(variant(%s)!=23)return %d;\n'%(name,11+i)
    text+='''for(s=0;s<256;s++)for(c=0;c<6;c++)for(p=0;p<3;p++)if(one(selected,(u32[]){0,76,77,78,79,255}[c],0x59,(u32[]){0,254,255}[p],s,0x81234567u,1))return 70;
 return 0;}\n'''
    return text+START,256*4*3*2+256*6*3

class RecordColorCommandTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>46I',rom,source.ROM));cls.parent=list(struct.unpack_from('>23I',rom,source.PARENT_ROM));cls.helper=list(struct.unpack_from('>19I',rom,source.HELPER_ROM));cls.registry=struct.unpack_from('>74I',rom,source.TABLE_ROM)
        data,fs=source.link_owner(ROOT,cls.fresh,cls.out/'qualified-padded.o',source.OWNER);cls.words=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']))
        old=cls.values['conker/build/conker.us.elf'];cls.retained_parent=list(struct.unpack_from('>23I',old,source.elf_slot_offset(old,source.PARENT,92)));cls.retained_helper=list(struct.unpack_from('>19I',old,source.elf_slot_offset(old,source.HELPER,76)))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,command,seed=0x59,phase=0,layout=0,priority=17,chain=False,images=None,entry=source.ENTRY,helper=source.HELPER):
        initial,p=fixture(command,seed,phase,layout,priority);expected,calls=reference(initial,p,0xDEAD4320,command,STACK+phase,chain);pair=[]
        for words in images or(self.truth,self.words):
            connected={source.HELPER+4*i:w for i,w in enumerate(self.helper)}if chain else None
            m=ColorOracle(words,initial,p,command,phase=phase,entry=entry,connected=connected,helper=helper).run()
            self.assertEqual(public(m.memory,p),public(expected,p),(command,seed,layout,chain));self.assertEqual([(source.HELPER if t==helper else t,a)for t,a in m.calls],calls)
            if calls:self.assertEqual(m.observed,[255])
            pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_01_complete_owner_actual_Make_registry_and_ABI(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.parent,self.retained_parent);self.assertEqual(self.helper,self.retained_helper);self.assertEqual(self.registry[65],source.ENTRY)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes())
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),18)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),17)
        self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_126F60.c.o.compact'),18);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
        self.assertEqual([i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY],[0x22F49C]);self.assertFalse(any(struct.unpack_from('>I',rom,i)[0]==jal for i in range(0,len(rom)-3,4)))
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=46,frame=24,guards=0,call_bindings=2,neighbors=17,compact_functions=18,Make_commands=3,diagnostics_empty=True,registry_index=65,entries=74,ABI='void(struct260*,s32,u8)')
    def test_02_commands_upper_words_seeds_and_ordered_aliases(self):
        visits=set();count=0
        for c,high,seed,phase in itertools.product(range(256),(0,0x12340000,0xFFFFFF00),(0,30,128,255),(0,8)):
            m=self.compare(c|high,seed,phase);visits.update(m.visits);count+=1
        for c,layout,phase in itertools.product((0,76,77,78,79,255),range(1,5),(0,8)):self.compare(c,phase=phase,layout=layout);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+184,4)))
        self.receipt['guest']=dict(cases=count,all_46_words_visited=True,all_command_bytes=True,three_incoming_upper_word_patterns=True,alias_layouts=5,complete_private_state_equal=True,ignored_event_unmapped=True)
    def test_03_complete_original_and_retained_dispatcher(self):
        count=0;visits=set()
        for parent in(self.parent,self.retained_parent):
            for selector,c,phase in itertools.product(range(256),(0,76,77,78,79,255),(0,8)):
                initial,p=fixture(c,phase=phase);initial[p+19]=selector
                for i,v in enumerate(self.registry):put(initial,source.TABLE+4*i,v)
                target=self.registry[selector]if selector<74 else 0;calls=[];expected=dict(initial)
                if target:
                    calls=[(target,(p,0xDEAD4320,c))]
                    if target==source.ENTRY:expected,extra=reference(expected,p,0xDEAD4320,c,STACK+phase-24);calls+=extra
                pair=[]
                for words in(self.truth,self.words):
                    connected={source.ENTRY+4*i:w for i,w in enumerate(words)}
                    m=ColorOracle(parent,initial,p,c,phase=phase,entry=source.PARENT,connected=connected,providers=self.registry).run()
                    self.assertEqual(m.calls,calls,(selector,c));self.assertEqual(public(m.memory,p),public(expected,p));pair.append(m);visits.update(m.visits)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.receipt['caller']=dict(cases=count,original_and_retained_23_words=True,all_256_selector_bytes=True,actual_74_entry_registry=True,three_argument_callback_envelopes=True,other_callbacks_bounded_contracts=True,visited_parent_words=len(set(range(source.PARENT,source.PARENT+92,4))&visits))
    def test_04_native32_actual_dispatcher_provider_and_effective_controls(self):
        text,count=native_harness(self.values,self.registry)
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr)
            self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_per_profile=count,typed_three_argument_indirect_calls=True,actual_dispatcher_and_color_provider_C=True,effective_controls=len(controls()),trapping_UBSan=True,store_before_helper_observed=True)
    def test_05_fault_prefixes_sparse_unknown_and_compiled_negative(self):
        count=0
        for c in(0,76,77,78,79,255):
            initial,p=fixture(c);m=self.compare(c)
            for cut in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=ColorOracle(words,initial,p,c);x.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,cut);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));count+=1
        initial,p=fixture(0);sparse={a:v for a,v in initial.items()if not p<=a<p+64}
        for words in(self.truth,self.words):self.assertFalse(ColorOracle(words,sparse,p,0).run().calls)
        body=source.SELECTED.replace('    if (command ==','    (void)*(volatile u8 *)eventAddress;\n    if (command ==',1)
        obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-event-read');self.assertFalse(diag)
        data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);info=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        with self.assertRaisesRegex(AssertionError,'unmapped read'):ColorOracle(words,sparse,p,0).run()
        self.receipt['faults']=dict(fired_prefix_pairs=count,sparse_unknown_command_needs_no_record_mapping=True,actual_compiled_unused_event_read_negative=True,guest_only_access_order=True)
    def test_06_real_padder_and_independent_GNU_call_rebases(self):
        raw,bindings=source.checked_payload(*source.payload(self.out/'selected.o'))
        for data,rs in((raw[:-4],bindings),(bytes([raw[0]^1])+raw[1:],bindings),(raw,bindings|{64:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(data,rs)
        p=self.fresh/'padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        asm,missing=emit_function(raw,dict(value=0,size=184),bindings,source.FUNCTION,dict(func_1515D4D4=source.HELPER));self.assertFalse(missing);p=self.fresh/'independent.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
        count=0
        for i,(entry,helper)in enumerate(((source.ENTRY,source.HELPER),(0x154FA468,0x1525D4D4),(0x250FA468,0x2515D4D4))):
            images=[]
            for j,object_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=func_1515D4D4=0x%X'%helper,'-o',str(elf),str(object_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])))
            self.assertEqual(*images)
            for c,phase in itertools.product((0,76,77,78,79,255),(0,8)):self.compare(c,phase=phase,images=images,entry=entry,helper=helper);count+=1
        self.receipt['rebases']=dict(layouts=3,GNU_links=6,guest_cases=count,both_R_MIPS_26_bindings=True,different_JAL_region=True,raw_negative_controls=3)
    def test_07_original_and_retained_color_provider_integration(self):
        count=0;visits=set()
        for helper in(self.helper,self.retained_helper):
            old=self.helper;self.helper=helper
            try:
                for c,priority,layout,phase in itertools.product((0,76,77,78,79,255),(0,254,255),range(5),(0,8)):
                    visits.update(self.compare(c,priority=priority,layout=layout,phase=phase,chain=True).visits);count+=1
            finally:self.helper=old
        self.assertEqual(set(range(source.HELPER,source.HELPER+76,4))-visits,set())
        self.receipt['provider']=dict(cases=count,original_and_retained_19_word_provider=True,all_provider_words_visited=True,RGB_active_and_priority_outputs=True,aliased_globals_follow_byte_store=True,hardware_or_gameplay_acceptance_claimed=False)
    def test_08_strict_full_image_frozen_inputs_and_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+184];expected=source.predicted_image(before,truth)
        source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,184);symbol=next(pos for pos,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+184,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(137,136,1,0));self.receipt['strict']=dict(changed_bytes=137,code_bytes=136,metadata_bytes=1,exclusions=0,corruptions=7,wrong_inputs=3,focused_inputs=len(values))
if __name__=='__main__':unittest.main()
