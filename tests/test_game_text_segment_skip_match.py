"""Text segment cursor: bank ABI, separator reads, caller windows and named ELF cycle."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_text_segment_skip_match as source
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
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
RECORD,STATE,TABLE0,TABLE1,TEXT0,TEXT1,TEXT2=0x20000,0x60000,0x30000,0x31000,0x40000,0x41000,0x42000
U32=0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    bank:int=0
    segment:int=1
    index:int=2
    pattern:int=0
    alias:int=0
    phase:int=0

def half(x):return((x&65535)^32768)-32768

def data(pattern,row=0):
    b=bytearray([0]*(pattern%3))
    for run in range(8):
        b.extend(((pattern*31+row*43+run*29+i*17)%255+1 for i in range(1+(pattern+row+run)%7)))
        b.extend(bytes(1+(pattern+run)%4))
    return bytes(b)

def fixture(c,globals_=source.GLOBALS):
    sp=STACK+c.phase;record=RECORD if c.alias!=2 else sp+4
    m={sp+i:(i*17+0xA5)&255 for i in range(-256,512)}
    for base in(TEXT0,TEXT1,TEXT2):
        for row in range(5):
            chunk=data(c.pattern+(base-TEXT0)//4096,row)
            for i,v in enumerate(chunk):m[base+row*128+i]=v
    for p,n in((record,16),(TABLE0,40),(TABLE1,40)):
        for i in range(n):m[p+i]=(i*13+0x59)&255
    target=TEXT2+128*(c.index%5)
    if c.alias==4:
        target=sp+8
        for i,v in enumerate(data(c.pattern)):m[target+i]=v
    put(m,record,0x12345678);put(m,record+4,target if half(c.bank)==2 else c.index)
    put(m,sp-8,TEXT2+512);put(m,sp+8,c.bank)
    for which,(g,t,base)in enumerate(zip(globals_,(TABLE0,TABLE1),(TEXT0,TEXT1))):
        put(m,g,t)
        for i in range(5):put(m,t+8*i,base+128*i);put(m,t+8*i+4,TEXT2+128*((i+1)%5))
    if c.alias==1:
        record=globals_[0]-4;put(m,record,0x12345678)
    index=read(m,record+4)
    for g,base in zip(globals_,(TEXT0,TEXT1)):
        if c.alias==3:put(m,g,(sp-8-8*index)&U32)
        entry=(read(m,g)+8*index)&U32
        put(m,entry,TEXT2+512 if c.alias==3 else base+128*(index%5))
    return m,record

def reference(initial,c,record,globals_=source.GLOBALS):
    m=dict(initial);put(m,STACK+c.phase+8,c.bank);bank=half(c.bank)
    if bank in(0,1):p=read(m,(read(m,globals_[bank])+8*read(m,record+4))&U32)
    elif bank==2:p=read(m,record+4)
    else:p=read(m,STACK+c.phase-8)
    n=c.segment if c.segment<0x80000000 else c.segment-0x100000000
    for _ in range(max(0,n)):
        while m[p]!=0:p=(p+1)&U32
        while m[p]==0:p=(p+1)&U32
    return p

def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+512}

class SegmentOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),record=RECORD,entry=source.ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(record,c.segment,c.bank),connected=connected);self.trace=[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        assert target==source.ENTRY;args=self.arguments(3);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):raise AssertionError(('Unexpected text cursor helper',target))

def controls():
    b=source.SELECTED
    swap=b.replace('D_800DD254','bank_temp').replace('D_800DD258','D_800DD254').replace('bank_temp','D_800DD258')
    first='        while (*text != 0) {\n            text++;\n        }\n';second='        while (*text == 0) {\n            text++;\n        }\n'
    return dict(swapped_banks=swap,wrong_index=b.replace('source->value.index','(source->value.index ^ 1U)'),wrong_direct=b.replace('text = source->value.text;','text = source->value.text + 1;'),skip_scan=b.replace(first,''),skip_separators=b.replace(second,''),single_separator=b.replace('while (*text == 0)','if (*text == 0)'),wrong_count=b.replace('current < segment','current <= segment'),wrong_return=b.replace('return text;','return text + 1;'))

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
static TextBankEntry first[5],second[5];TextBankEntry*D_800DD254=first,*D_800DD258=second;
static u8 strings[3][5][128];static TextSegmentSource input;
typedef char ABI[(sizeof(void*)==4&&sizeof(TextBankEntry)==8&&sizeof(TextSegmentSource)==8&&__builtin_offsetof(TextSegmentSource,value)==4)?1:-1];
static u8*reference(u8*p,s32 n){while(n>0){while(*p)p++;while(!*p)p++;--n;}return p;}
static void seed(u32 pattern){u32 bank,row,run,i,at,n,g;
 for(bank=0;bank<3;bank++)for(row=0;row<5;row++){
  for(i=0;i<128;i++)strings[bank][row][i]=0xA5;at=pattern%3;
  for(i=0;i<at;i++)strings[bank][row][i]=0;
  for(run=0;run<8;run++){
   n=1+(pattern+row+run)%7;for(i=0;i<n;i++)strings[bank][row][at++]=(u8)((pattern*31+bank*83+row*43+run*29+i*17)%255+1);
   g=1+(pattern+run)%4;for(i=0;i<g;i++)strings[bank][row][at++]=0;
  }
 }
 for(i=0;i<5;i++){first[i].text=strings[0][i];second[i].text=strings[1][i];first[i].reserved=second[i].reserved=(u32)strings[2][i];}
}
static u32 fingerprint(void){u32 h=2166136261u,i;const u8*p=(const u8*)strings;for(i=0;i<sizeof(strings);i++)h=(h^p[i])*16777619u;return h;}
'''
    variants=dict(selected=source.SELECTED,**controls())
    for n,b in variants.items():t+=b.replace('u8 *'+source.FUNCTION,'static __attribute__((always_inline)) inline u8 *'+n)+'\n'
    for name in variants:
        t+='static int check_'+name+'(void){\n'+r'''
 const s32 counts[]={-2147483647-1,-2,0,1,2,3,4};u32 pattern,index,bank,j,before;u8*want,*answer,*base;
 for(pattern=0;pattern<16;pattern++)for(index=0;index<4;index++)for(bank=0;bank<3;bank++)for(j=0;j<7;j++){
  seed(pattern);input.flags=0x12345678;input.value.index=index;if(bank==2)input.value.text=strings[2][index];
  base=bank==0?first[index].text:bank==1?second[index].text:input.value.text;want=reference(base,counts[j]);before=fingerprint();
'''
        t+='  if(bank==0)answer='+name+'(&input,counts[j],0);else if(bank==1)answer='+name+'(&input,counts[j],1);else answer='+name+'(&input,counts[j],2);\n'
        t+=r'''
  if(answer!=want||fingerprint()!=before||input.flags!=0x12345678||input.value.index!=(bank==2?(u32)strings[2][index]:index))return 1;
 }
 return 0;
}
'''
    t+='static int run(void){if(check_selected())return 10;\n'
    for i,n in enumerate(controls()):t+='if(!check_'+n+'())return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class TextSegmentSkipTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,globals_=source.GLOBALS):
        initial,record=fixture(c,globals_);want=reference(initial,c,record,globals_);pair=[]
        for words in images or(self.truth,self.words):
            m=SegmentOracle(words,initial,c,record,entry).run();self.assertEqual(m.r[2],want,c);self.assertEqual(public(m.memory),public(initial),c);self.assertFalse(m.calls);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_complete_owner_actual_Make_ABI_and_reference_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFF8)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),12)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),11);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_197C20.c.o.compact'),12);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        rom=self.values['conker/conker.us.bin'];ws=struct.unpack('>%dI'%(len(rom)//4),rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[]);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[0x197DBC,0x197EA8,0x1985CC]);self.assertFalse(any(w==0x08000000|(source.ENTRY>>2&0x3FFFFFF)for w in ws))
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=8,guards=0,bindings=4,neighbors=11,compact_functions=12,Make_commands=3,ABI='u8*(TextSegmentSource*,s32,s16)',source_value_offset=4,table_stride=8,three_direct_callers=True,unsupported_selector_cursor_home=0,one_unreachable_redundant_load_literal_checked=True)
    def test_02_segments_selector_width_aliases_and_access_traces(self):
        count=0;visits=set()
        for bank,high,n,phase in itertools.product(range(256),(0,0x12340000,0xFFFF0000),(-1,0,1,3),(0,8)):
            m=self.compare(Case(bank|high,n,pattern=bank%8,phase=phase));visits.update(m.visits);count+=1
        for bank,n,index,alias,pattern in itertools.product((0,1,2,3,0x7FFF,0x8000,0xFFFF,0x10002),(-2147483648,0,2),(0,3,0x7FFFFFFF,0x80000000,U32),range(5),(0,3)):
            c=Case(bank,n,index,pattern,alias)
            if half(bank)==2 and alias==2 and n>0:
                initial,record=fixture(c);pair=[]
                for words in(self.truth,self.words):
                    m=SegmentOracle(words,initial,c,record)
                    with self.assertRaisesRegex(AssertionError,'unmapped read'):m.run()
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of))
            else:self.compare(c)
            count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4))-{source.ENTRY+104});self.receipt['guest']=dict(cases=count,reachable_words_visited=46,total_literal_words=47,dead_redundant_load_offset=104,selector_low16_and_all_low8_values=True,signed_segment_boundaries=True,five_alias_layouts=True,invalid_direct_home_alias_fault_pairs=20,fullword_wrapped_indices_guest_only=True,leading_and_consecutive_zero_runs=True,complete_private_state_and_access_trace_equal=True)
    def test_03_authentic_caller_windows_and_return_consumers(self):
        rom=self.values['conker/conker.us.bin'];windows=((0x1516A904,0x1516A918),(0x1516A9F8,0x1516AA04),(0x1516B0FC,0x1516B138));count=0
        for (start,stop),bank,segment,phase in itertools.product(windows,(0,1,2,255),(0,1,3),(0,8)):
            c=Case(bank,0 if start==0x1516A9F8 else segment,phase=phase);initial,record=fixture(c);initial.update({STATE+i:0xA5 for i in range(80)});initial[STATE+0xD]=bank;initial[STATE+0x20]=c.segment;put(initial,STATE+0x10,record);initial[record+8]=8;want=reference(initial,c,record);body=list(struct.unpack_from('>%dI'%((stop-start)//4),rom,start-0x15000000+0x2D4B0));pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=SegmentOracle(body,initial,c,record,start,connected);m.r[16]=c.segment if start==0x1516A904 else STATE;m.r[17]=STATE;m.r[18]=record;m.r[7]=record;m.f[18]=0x3F800000;m.code=StopCode(m.code,m,stop)
                with self.assertRaises(WindowEnd):m.run()
                self.assertEqual(m.calls,[(source.ENTRY,(record,c.segment,bank))]);self.assertEqual(m.r[4]if start==0x1516A904 else read(m.memory,STATE+0x24),want);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.receipt['caller']=dict(cases=count,original_windows_words=[5,3,15],argument_setup_and_byte_selector=True,returned_pointer_forward_and_state_store_verified=True,containing_parent_C_stubs_remain_uncredited=True,no_full_parent_or_text_rendering_claim=True)
    def test_04_native32_valid_banks_separator_patterns_and_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=1344,effective_controls=8,trapping_UBSan=True,three_valid_banks_only=True,constant_selector_always_inline_calls=True,source_body_unchanged=True,valid_terminated_buffers_and_nonpositive_counts=True,input_buffers_unchanged=True,unsupported_indeterminate_cursor_guest_only=True)
    def test_05_fired_fault_prefixes_and_suppressed_reads(self):
        cuts=0
        for c in(Case(),Case(bank=1,segment=3),Case(bank=2,pattern=3),Case(bank=255),Case(segment=0),Case(alias=1),Case(alias=2),Case(alias=3),Case(alias=4)):
            initial,record=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=SegmentOracle(words,initial,c,record);x.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,cut);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        for bank,n in itertools.product((0,1,2,3,255,0xFFFF0002),(0,-1,0x80000000)):
            c=Case(bank,n);initial,record=fixture(c);want=reference(initial,c,record);sparse={a:b for a,b in initial.items()if STACK-256<=a<STACK+512 or record<=a<record+8 or a in range(source.GLOBALS[0],source.GLOBALS[1]+4)or TABLE0<=a<TABLE0+40 or TABLE1<=a<TABLE1+40}
            if half(bank)not in(0,1,2):sparse={a:b for a,b in sparse.items()if STACK-256<=a<STACK+512};record=0xDEAD0000
            for words in(self.truth,self.words):m=SegmentOracle(words,sparse,c,record).run();self.assertEqual(m.r[2],want);self.assertFalse(any(e[0]=='R'and e[1]==want and e[2]==1 for e in m.events))
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,nonpositive_segments_need_no_text_mapping=True,unsupported_selectors_need_no_record_or_global_mapping=True,guest_only_fault_and_indeterminate_home_semantics=True)
    def test_06_actual_padder_raw_controls_and_GNU_signed_low_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'))
        bad_dead=bytearray(raw);bad_dead[104]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad_dead),rs),(raw,rs|{20:[('R_MIPS_HI16','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        links=0;cases=0
        for i,(entry,globals_)in enumerate(((source.ENTRY,source.GLOBALS),(0x17007FFC,(0x81007FFC,0x81008000)),(0x2500FFFC,(0x8120FFFC,0x81210000)))):
            symbols=dict(zip(('D_800DD254','D_800DD258'),globals_));asm,missing=emit_function(raw,dict(value=0,size=188),rs,source.FUNCTION,symbols);self.assertFalse(missing);p=self.fresh/('rebase-%d.s'%i);p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);images=[]
            for j,obj_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('link-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for c in(Case(),Case(bank=1,segment=3),Case(bank=2),Case(bank=255),Case(alias=1),Case(alias=3)):self.compare(c,images,entry,globals_);cases+=1
        self.receipt['rebases']=dict(GNU_links=links,layouts=3,guest_cases=cases,signed_low_carry_and_four_bindings=True,dead_word_checked_literally=True,raw_negative_controls=3,guards=0)
    def test_07_compiled_selector_width_negative_control(self):
        b=source.SELECTED.replace('s16 bank','s32 bank');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+b,'negative-wide-bank');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(bank=0x10002,segment=0);initial,record=fixture(c);want=reference(initial,c,record);m=SegmentOracle(words,initial,c,record).run();self.assertNotEqual(m.r[2],want);self.receipt['negative_width']=dict(actual_compiled_wide_selector_mutant_rejected=True,low16_bank2_differs_from_fullword_default=True)
    def test_08_strict_full_image_named_cycle_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8;cyc=next((p,s)for p,n,f,s in source.symbol_rows(before)if n=='D_800DD258')
        for offset in(20,at,at+104,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol,cyc[0],cyc[1]):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(196,136,60,0));self.receipt['strict']=dict(changed_bytes=196,code_bytes=136,metadata_bytes=60,exclusions=0,corruptions=10,wrong_inputs=3,named_symbol_and_string_cycle=list(source.SYMBOL_CYCLE_AFTER),all_named_definitions_preserved=True,focused_inputs=len(v))
if __name__=='__main__':unittest.main()
