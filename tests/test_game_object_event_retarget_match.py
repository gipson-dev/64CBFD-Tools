"""Object event callback: byte ABI, paired-reference aliases, providers and strict image."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,os,re,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_object_event_retarget_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
OBJECT,EVENT,CALLBACK,ALTERNATE,RELEASE=0x20000,0x30000,0x15190550,0x15012340,0x1516972C
@dataclass(frozen=True)
class Case:
    command:int=45
    pair:int=1
    selector:int=1
    alias:int=0
    helper:int=0
    phase:int=0

def fixture(c,table=source.TABLE):
    sp=STACK+c.phase;event=(EVENT,OBJECT+8,OBJECT+12,OBJECT+16,sp+8)[c.alias]
    m={sp+i:(i*17+0xA5)&255 for i in range(-256,512)}
    for base in(OBJECT,EVENT):m.update({base+i:(i*13+0x59)&255 for i in range(0x100)})
    put(m,event,0x11223344 if c.pair in(1,3)else 0x66778899);put(m,event+4,0x11223344 if c.pair in(2,3)else 0x55667788)
    m[event+8]=0x5A;m[event+9]=0xA5;put(m,OBJECT+16,0x11223344);m[OBJECT+20]=0xC3;m[OBJECT+29]=c.selector
    for i in range(256):put(m,table+4*i,CALLBACK if i&1 else 0)
    put(m,table,0);put(m,table+4,CALLBACK);put(m,table+8,0)
    return m,event

def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+512}
def helper_effect(m,c,obj,event,sp,table):
    if c.helper==1:m[obj+29]=2;put(m,table+8,ALTERNATE)
    elif c.helper==2:m[obj+29]=1;put(m,table+4,0)
    elif c.helper==3:m[sp+11]=45;put(m,obj+16,0xCAFEBABE)
def callback_effect(m,obj,event,command):
    put(m,obj+0x34,read(m,event)^command);put(m,event,read(m,obj+16))
def observation(m,obj,event,command):
    return(read(m,obj+16),m[obj+20],m[obj+29],command,read(m,event),read(m,event+4))
def reference(initial,c,event,table=source.TABLE):
    m=dict(initial);sp=STACK+c.phase;put(m,sp+8,c.command);cmd=c.command&255;calls=[];observations=[]
    if cmd==0:
        calls.append((source.HELPER,(OBJECT,event)));helper_effect(m,c,OBJECT,event,sp,table);cmd=m[sp+11]
    elif cmd==45:
        a,b,current=read(m,event),read(m,event+4),read(m,OBJECT+16)
        if a==current:put(m,OBJECT+16,b);m[OBJECT+20]=m[event+9]
        elif b==current:put(m,OBJECT+16,a);m[OBJECT+20]=m[event+8]
    callback=read(m,table+4*m[OBJECT+29])
    if callback:
        calls.append((callback,(OBJECT,event,cmd)));observations.append(observation(m,OBJECT,event,cmd));callback_effect(m,OBJECT,event,cmd)
    return public(m),calls,observations

class EventOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),event=EVENT,entry=source.ENTRY,table=source.TABLE,helper=source.HELPER,connected=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(OBJECT,event,c.command),connected=connected)
        self.case,self.table,self.helper,self.trace=c,table,helper,[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        if target==source.ENTRY:args=self.arguments(3)
        elif target==self.helper or target==RELEASE:args=self.arguments(2 if target==self.helper else 1)
        else:
            assert target in(CALLBACK,ALTERNATE),('unbounded event callback',hex(target));args=self.arguments(3)
            self.observations.append(observation(self.memory,*args))
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        args=self.calls[-1][1]
        if target==self.helper:helper_effect(self.memory,self.case,*args,STACK+self.case.phase,self.table)
        elif target==RELEASE:put(self.memory,args[0]+0x38,0xABCD0123)
        else:callback_effect(self.memory,*args)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0xA5000010,0xA5000011

def controls():
    b=source.SELECTED
    early=b.replace('    s32 first;','    s32 first;\n    u8 selector = ((u8 *)object)[0x1D];').replace('D_8008FC64[((u8 *)object)[0x1D]]','D_8008FC64[selector]')
    return dict(skip_release=b.replace('        func_151D33FC(object, event);',''),wrong_opcode=b.replace('command == 0x2D','command == 0x2C'),wrong_first_tag=b.replace('object->unk14 = event->unk9','object->unk14 = event->unk8'),wrong_second_tag=b.replace('object->unk14 = event->unk8','object->unk14 = event->unk9'),missing_reference=b.replace('object->unk10 = event->unk4.w','object->unk10 = first'),wrong_priority=b.replace('if (first == object->unk10)','if (first == object->unk10 && event->unk4.w != object->unk10)'),early_selector=early,skip_callback=b.replace('        D_8008FC64[((u8 *)object)[0x1D]](object, event, command);',''))

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(struct224)==0x48&&sizeof(struct223)==12&&__builtin_offsetof(struct224,unk10)==16&&__builtin_offsetof(struct224,unk14)==20&&__builtin_offsetof(struct223,unk4)==4&&__builtin_offsetof(struct223,unk8)==8&&__builtin_offsetof(struct223,unk9)==9)?1:-1];
typedef struct {u32 kind; s32 value,first,second;u8 tag,selector,command,pad;} Log;
static Log logs[4],saved[4];static u32 count,mode;
static struct224 a,b;static struct223 x,y;
ObjectEventCallback D_8008FC64[3];
static void remember(u32 kind,struct224*o,struct223*e,u8 c){Log*l=&logs[count++];l->kind=kind;l->value=o->unk10;l->first=e->unk0;l->second=e->unk4.w;l->tag=o->unk14;l->selector=((u8*)o)[29];l->command=c;l->pad=0;}
static void callback(struct224*o,struct223*e,u8 c){remember(2,o,e,c);o->unk34=e->unk0^c;e->unk0=o->unk10;}
static void alternate(struct224*o,struct223*e,u8 c){remember(3,o,e,c);o->unk34=e->unk0^c;e->unk0=o->unk10;}
void func_151D33FC(struct224*o,struct223*e){remember(1,o,e,0);if(mode==1){((u8*)o)[29]=2;D_8008FC64[2]=alternate;}else if(mode==2){((u8*)o)[29]=1;D_8008FC64[1]=0;}}
static void oracle(struct224*o,struct223*e,u8 c){s32 old=o->unk10;if(!c)func_151D33FC(o,e);else if(c==45){if(e->unk0==old){o->unk10=e->unk4.w;o->unk14=e->unk9;}else if(e->unk4.w==old){o->unk10=e->unk0;o->unk14=e->unk8;}}if(D_8008FC64[((u8*)o)[29]])D_8008FC64[((u8*)o)[29]](o,e,c);}
'''
    for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace('void '+source.FUNCTION,'static void '+name)+'\n'
    t+=r'''
static int equal(const void*a_,const void*b_,u32 n){const u8*a=a_,*b=b_;u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static void reset(void){count=0;D_8008FC64[0]=0;D_8008FC64[1]=callback;D_8008FC64[2]=0;}
static int check(ObjectEventCallback fn){u32 cmd,pair,sel,i,j,want_count;
 for(cmd=0;cmd<256;cmd++)for(pair=0;pair<4;pair++)for(sel=0;sel<3;sel++)for(mode=0;mode<3;mode++){
  for(i=0;i<sizeof(a);i++)((u8*)&a)[i]=(u8)(i*13+0x59);
  for(i=0;i<sizeof(x);i++)((u8*)&x)[i]=(u8)(i*17+0xA5);
  a.unk10=0x11223344;a.unk14=0xC3;((u8*)&a)[29]=(u8)sel;
  x.unk0=(pair==1||pair==3)?0x11223344:0x66778899;x.unk4.w=(pair==2||pair==3)?0x11223344:0x55667788;x.unk8=0x5A;x.unk9=0xA5;
  b=a;y=x;reset();oracle(&b,&y,(u8)cmd);want_count=count;for(j=0;j<count;j++)saved[j]=logs[j];reset();fn(&a,&x,(u8)cmd);
  if(count!=want_count||!equal(&a,&b,sizeof(a))||!equal(&x,&y,sizeof(x))||!equal(logs,saved,count*sizeof(Log)))return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class ObjectEventRetargetTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']));local=cls.fresh/'raw.o';local.write_bytes((cls.out/'selected.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.raw=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,table=source.TABLE,helper=source.HELPER,raw=True):
        initial,event=fixture(c,table);want,calls,observations=reference(initial,c,event,table);calls=[(helper if t==source.HELPER else t,a)for t,a in calls];pair=[]
        for words in images or(self.truth,self.words):
            m=EventOracle(words,initial,c,event,entry,table,helper).run();self.assertEqual((public(m.memory),m.calls,m.observations),(want,calls,observations),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace)
        if raw and images is None:
            m=EventOracle(self.raw,initial,c,event).run();self.assertEqual(complete(m)[:-1],complete(pair[0])[:-1]);self.assertEqual(m.trace,pair[0].trace)
        return pair[0]
    def test_01_owner_Make_ABI_and_literal_table_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFE8)
        diagnostics=[]
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),19);diagnostics.append(re.findall(r'Warning [0-9]+:.*?line [0-9]+: (.*)',diag))
        self.assertEqual(diagnostics[0],diagnostics[1]);self.assertEqual(len(diagnostics[0]),14)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),18);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game_1FFF60.c.o.compact'),19);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x230C1C]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual(struct.unpack_from('>3I',self.rom,0x234724),(0,CALLBACK,0));self.assertEqual(0x8008B4A8+0x3E*0x34+0x1C,0x8008C15C)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,raw_words=46,frame=24,guards=4,inserted_words=1,bindings=3,neighbors=18,compact_functions=19,Make_commands=3,ABI='void(struct224*,struct223*,u8)',registry_type=62,registry_stride=52,registry_callback_offset=28,sole_pointer_ROM=0x230C1C,unchanged_legacy_owner_warnings=14)
    def test_02_all_command_bytes_pairs_late_dispatch_and_aliases(self):
        count=0;visits=set()
        for cmd,pair,sel,phase in itertools.product(range(256),range(4),(0,1,2),(0,8)):
            m=self.compare(Case(cmd|0xA5C00000,pair,sel,phase=phase));visits.update(m.visits);count+=1
        for cmd,pair,sel,alias,helper in itertools.product((0,45,0x100002D,1),range(4),(0,1,2),range(5),range(4)):
            self.compare(Case(cmd,pair,sel,alias,helper));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4))-{source.ENTRY+112})
        self.receipt['guest']=dict(cases=count,raw_C_and_guarded_public_and_private_final_state=True,all_256_command_bytes=True,upper_argument_garbage=True,first_match_priority=True,post_store_tag_alias_reads=True,late_selector_and_table_mutation=True,helper_can_change_guest_command_home=True,alias_layouts=5,reachable_words=46,unreachable_redundant_load_offset=112,fullword_literal_check=True)
    def test_03_original_registry_caller_and_real_release_helper(self):
        count=0;start,stop=0x15169514,0x15169528;body=list(struct.unpack_from('>5I',self.rom,start-0x15000000+0x2D4B0));registry=0x8008B4A8+62*52
        for cmd,pair,sel,phase in itertools.product((0,45,0x1234002D,0xFFFFFF01),range(4),(0,1,2),(0,8)):
            c=Case(cmd,pair,sel,phase=phase);initial,event=fixture(c);put(initial,registry+28,source.ENTRY);images=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=EventOracle(body,initial,c,event,start,connected=connected);m.r[16]=OBJECT;m.r[19]=event;m.r[20]=cmd;m.r[22]=registry;m.code[stop]=0;m.code=StopCode(m.code,m,stop)
                with self.assertRaises(WindowEnd):m.run()
                self.assertEqual(m.calls[0],(source.ENTRY,(OBJECT,event,cmd&255)));images.append(m)
            self.assertEqual(complete(images[0]),complete(images[1]));count+=1
        original=list(struct.unpack_from('>16I',self.rom,source.HELPER-0x15000000+0x2D4B0));helper_cases=0
        for pair,sel,alias in itertools.product(range(4),(0,1,2),range(5)):
            c=Case(0,pair,sel,alias);initial,event=fixture(c);images=[]
            for target in(self.truth,self.words):
                connected={source.HELPER+4*i:w for i,w in enumerate(original)};m=EventOracle(target,initial,c,event,connected=connected).run();images.append(m)
            self.assertEqual(complete(images[0]),complete(images[1]));helper_cases+=1
        self.receipt['caller']=dict(original_window_words=5,cases=count,physical_registry_type62=True,callback_argument_delay_mask_verified=True,parent_stub_uncredited=True,real_original_helper_words=16,helper_cases=helper_cases,bounded_release_provider=True,no_full_parent_or_gameplay_claim=True)
    def test_04_native32_typed_records_callbacks_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=9216,effective_controls=8,typed_valid_shared_records=True,three_in_bounds_table_slots=True,trapping_UBSan=True,guest_overlays_and_home_mutation_excluded=True)
    def test_05_fired_fault_prefixes_and_no_payload_reads_on_unrelated_commands(self):
        cuts=0
        for c in(Case(0,helper=1),Case(0,helper=3),Case(),Case(pair=2),Case(pair=3,alias=1),Case(alias=2),Case(selector=0),Case(command=1)):
            initial,event=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=EventOracle(words,initial,c,event);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        for cmd,sel in itertools.product((1,2,44,46,255),(0,2)):
            c=Case(cmd,selector=sel);initial,event=fixture(c);sparse={a:b for a,b in initial.items()if STACK-256<=a<STACK+512 or a==OBJECT+29 or source.TABLE<=a<source.TABLE+12}
            for words in(self.truth,self.words,self.raw):m=EventOracle(words,sparse,c,0xDEAD0000).run();self.assertFalse(m.calls)
        self.receipt['faults']=dict(fired_access_prefix_pairs=cuts,complete_private_state_trace_PC_delay_equal=True,unrelated_commands_with_null_callback_need_no_payload_or_reference_mapping=True)
    def test_06_four_checked_guards_raw_controls_and_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));norm,nrs=source.normalized_payload(raw,rs);self.assertEqual(len(norm),188);self.assertEqual(nrs,{36:[('R_MIPS_26','func_151D33FC')],140:[('R_MIPS_HI16','D_8008FC64')],152:[('R_MIPS_LO16','D_8008FC64')]})
        bad=bytearray(raw);bad[108]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{36:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=self.out/'proposed-word-patches.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        guards=(self.out/'proposed-word-patches.csv').read_text()
        for i,(a,b)in enumerate((('0x14C00009','0x14C00008'),('0x014,0x14C00009,0x14C0000A,-,-','0x014,0x14C00009,0x14C0000A,R_MIPS_26:wrong,-'))):
            path=self.fresh/('bad-guards-%d.csv'%i);path.write_text(guards.replace(a,b));self.assertNotEqual(path.read_text(),guards)
            with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=path)
        links=cases=0
        for i,(entry,helper,table)in enumerate(((source.ENTRY,source.HELPER,source.TABLE),(0x17007FFC,0x17018000,0x81008000),(0x2500FFFC,0x25028000,0x8120FFFC))):
            symbols=dict(func_151D33FC=helper,D_8008FC64=table);asm,missing=emit_function(norm,dict(value=0,size=188),nrs,source.FUNCTION,symbols);self.assertFalse(missing);p=self.fresh/('rebase-%d.s'%i);p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);images=[]
            for j,obj_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('link-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for c in(Case(),Case(0,helper=1),Case(0,helper=3),Case(pair=2),Case(alias=1),Case(255,selector=0)):self.compare(c,images,entry,table,helper,False);cases+=1
        self.receipt['rebases']=dict(GNU_links=links,layouts=3,guest_cases=cases,signed_low_carry_and_three_bindings=True,raw_negative_controls=3,fired_padder_controls=2,four_literal_expected_word_guards=True,one_inserted_delay_schedule_word=True)
    def test_07_actual_compiled_fullword_command_mutant_is_rejected(self):
        b=source.SELECTED.replace('u8 command','u32 command');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+b,'negative-wide-command');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(0x100002D);initial,event=fixture(c);expected=reference(initial,c,event);m=EventOracle(words,initial,c,event).run();self.assertNotEqual((public(m.memory),m.calls,m.observations),expected);self.receipt['negative_width']=dict(compiled_wide_command_mutant_rejected=True,byte45_differs_from_fullword16777261=True)
    def test_08_strict_whole_image_and_manifest_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+112,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        guards=v['conker/retail_word_patches.us.csv'];self.assertEqual(source.guard_manifest(guards),(self.out/'proposed-word-patches.csv').read_bytes())
        with self.assertRaises(ValueError):source.guard_manifest(guards+b'\n')
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),138)
        self.receipt['image']=dict(changed_bytes=138,code_bytes=137,metadata_bytes=1,target_extent_only=True,other6055_bodies_and6056_addresses_fixed=True,protected_data_bytes=189088,protected_owners=720,exclusions=0,effective_corruptions=7,inherited_guard_rows_byte_preserved=True,new_guard_rows=4)
