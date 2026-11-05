"""Exact descriptor callback, retained helpers, private state and production image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_random_colored_effect_descriptor_candidates as candidate
from tools.experiments import game_random_colored_effect_descriptor_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_random_colored_effect_descriptor_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.descriptors,m.factory_packets,m.snapshots,m.number

class RandomColoredEffectDescriptorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>67I',cls.rom,match.ROM));cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalRandomDescriptor',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-random-descriptor',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.raw==cls.words

    def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def contract(self,words,c,initial=None,s=None,entry=match.ENTRY,helpers=None):
        s=model.symbols()if s is None else s;initial=model.fixture(self.rom,c,s)if initial is None else initial
        connected=model.helper_code(self.rom,c)if helpers is None else helpers
        m=model.Oracle(words,initial,c,s,entry,connected=connected).run();expected=model.reference(initial,c,s)
        self.assertEqual(m.r[2],0,c);self.assertEqual(m.descriptors,[expected['descriptor']],c);self.assertEqual(m.calls,expected['calls'],c)
        self.assertEqual(m.snapshots,expected['snapshots'],c);self.assertEqual(m.number,expected['randoms'],c)
        self.assertEqual(model.read(m.memory,s['D_800885B0'],8),expected['seed']);self.assertEqual(model.data(m.memory,c.actor+0x34,12),expected['actor'])
        self.assertEqual(m.factory_packets,[expected['consumer']]if c.consumer else [])
        return m

    def compare(self,c,initial=None,s=None,images=None,entry=match.ENTRY,helpers=None):
        images=(self.retail,self.raw,self.words)if images is None else images
        ms=[self.contract(words,c,initial,s,entry,helpers)for words in images]
        for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
        return ms

    def test_01_complete_owner_direct_words_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['neighbors']),(67,80,0,8,35,35))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+268]
        for at in range(268):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        self.receipt('owner-contract',dict(words=67,frame=80,guards=0,bindings=8,neighbors=35,raw_corruptions=268,binding_corruptions=8,unchanged_warning=712))

    def test_02_unsigned_ranges_snapshot_colors_and_connected_providers(self):
        count=0;visited=set();modes={}
        for c in model.cases():
            ms=self.compare(c);visited.update(ms[0].visits);count+=1;modes[str((c.mode,c.consumer))]=modes.get(str((c.mode,c.consumer)),0)+1
        self.assertEqual(set(range(match.ENTRY,match.ENTRY+268,4))-visited,set())
        for entry,offset,n in(model.HELPERS[0],model.HELPERS[1]):self.assertTrue(set(range(entry,entry+n*4,4))<=visited)
        self.receipt('guest-contract',dict(cases_per_body=count,bodies=3,modes=modes,all_67_target_words=True,all_original_RNG_and_RGB_words=True,uninitialized_guest_bytes_retained=True))

    def test_03_frame_aliases_fired_cuts_and_unread_descriptor_bytes(self):
        aliases=cuts=0
        for shift,phase in itertools.product((-8,-4,0,4,8),(0,8)):
            p=model.packet(model.STACK+phase);c=model.Case(actor=p+shift-0x34,phase=phase,position=2)
            initial=model.fixture(self.rom,c);ms=[model.Oracle(words,initial,c).run()for words in(self.retail,self.raw,self.words)]
            self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(state(ms[0]),state(ms[2]));aliases+=1
        for c in(model.Case(),model.Case(mode=1,mutation=3),model.Case(mode=2,consumer=1,position=1)):
            initial=model.fixture(self.rom,c);connected=model.helper_code(self.rom,c);done=model.Oracle(self.retail,initial,c,connected=connected).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.words):
                    m=model.Oracle(words,initial,c,connected=connected);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(state(ms[0]),state(ms[2]));cuts+=1
        c=model.Case(mode=2,consumer=1);initial=model.fixture(self.rom,c);expected=model.reference(initial,c);ms=[]
        for words in(self.retail,self.raw,self.words):
            m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c));m.unmap_prefix=True;m.run()
            self.assertEqual(m.descriptors,[expected['descriptor']]);self.assertEqual(m.factory_packets,[expected['consumer']]);ms.append(m)
        self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(state(ms[0]),state(ms[2]))
        self.receipt('aliases-faults',dict(guest_copy_aliases=aliases,fired_access_prefixes=cuts,unmapped_input_gap_bytes=12,original_submitter_skips_unused_bytes=True,portable_partial_overlap_claimed=False))

    def test_04_actual_callback_dispatch_and_return_gate(self):
        self.assertEqual(match.census(ROOT)['index'],1);pc=0x1513D290;body=list(struct.unpack_from('>16I',self.rom,0x16A740));count=0
        for flag,selector,phase in itertools.product((0,1,127,128,255,0x12340001,0xFFFF8000),(0,1),(0,8)):
            c=model.Case(phase=phase,mutation=1);initial=model.fixture(self.rom,c);initial[c.actor+0x72]=selector;model.put(initial,0x80089E14,match.ENTRY);ms=[]
            for target in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+268,4),target));m=model.Oracle(body,initial,c,entry=pc,connected=code);m.r[7]=flag
                m.code[0x1513D2D0]=0;m.code=WindowCode(m.code,m);m.code.ends=(0x1513D2D0,)
                with self.assertRaises(WindowBoundary):m.run()
                active=bool(flag and selector)
                self.assertEqual(bool(m.descriptors),active)
                expected_flag=model.u32(((flag&255)^128)-128)if active else flag
                self.assertEqual(m.r[7],expected_flag)
                if active:
                    expected=model.reference(initial,c);self.assertEqual(m.descriptors,[expected['descriptor']]);self.assertEqual(m.calls,[(match.ENTRY,(c.actor,))]+expected['calls']);self.assertEqual(m.r[4],c.actor)
                else:self.assertFalse(m.calls)
                ms.append(m)
            self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(state(ms[0]),state(ms[2]));count+=1
        self.receipt('dispatcher',dict(original_words=16,cases_per_body=count,index_one=True,zero_result_preserves_active_flag=True,flag_and_index_zero_skip_callback=True,full_parent_or_gameplay_claimed=False))

    def test_05_independent_GNU_rebases_all_eight_calls(self):
        links=count=0
        for index,(entry,base)in enumerate(((match.ENTRY,0x17007FFC),(0x18018000,0x19018000),(0x1A02FFFC,0x1B00FFFC))):
            s=model.symbols()
            for i,name in enumerate(('func_150ADA20','func_151429E0','func_1518CA80')):s[name]=base+i*0x10000
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>67I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for randoms,mutation,phase in itertools.product((tuple([v]*7)for v in model.WORDS),(0,1),(0,8)):
                self.compare(model.Case(randoms=randoms,mutation=mutation,phase=phase),s=s,images=images,entry=entry,helpers={});count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,all_eight_R26_bindings=True))

    def test_06_native_initialized_fields_and_effective_IDO_controls(self):
        controls=model.controls();witnesses=list(model.cases());effective=[]
        for name,body in controls.items():
            text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1)
            obj,_=candidate.compile_owner(ROOT,self.out,text,'negative-'+name);words=model.bound(obj,model.symbols());fired=False
            for c in witnesses:
                initial=model.fixture(self.rom,c);expected=model.reference(initial,c)
                try:m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c)).run()
                except(AssertionError,IndexError,KeyError):fired=True;break
                if m.r[2]!=0 or m.descriptors!=[expected['descriptor']]or m.calls!=expected['calls']or m.snapshots!=expected['snapshots']:fired=True;break
            self.assertTrue(fired,name);effective.append(name)
        native_controls={n:b for n,b in controls.items()if n!='retained'}
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in native_controls.items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native_source(self.rom,body));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        native_rows=sum(c.phase==0 for c in model.cases())
        self.receipt('native-controls',dict(positive_executions=native_rows*3,rows_per_profile=native_rows,profiles=['O0','O2','O3'],native_controls=len(native_controls),IDO_controls=len(controls),UBSan=True,typed_indirect_calls=True,
            native_uninitialized_gap_and_padding_not_read=True,retained_byte_mutant_guest_only=True))

    def test_07_literal_full_image_corruptions(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+268]
        self.assertEqual(match.strict_image(before,after,truth),197);at=match.elf_slot_offset(after,match.ENTRY,268)
        offsets=(0,at,at+267,at+268,match.elf_slot_offset(after,0x80089E10,12),match.elf_slot_offset(after,model.RANDOM,72),len(after)-1)
        for off in offsets:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        self.receipt('strict-controls',dict(literal_ELF_changed_bytes=197,named_serialization_changes=0,corruption_controls=len(offsets),exclusions=0))

def native_source(rom,body):
    rows=[]
    for c in model.cases():
        if c.phase:continue
        initial=model.fixture(rom,c);expected=model.reference(initial,c);p=expected['descriptor']
        position=struct.unpack('>3I',p[:12]);halves=struct.unpack('>9H',p[0x16:0x28]);tail=p[0x28:0x32]
        rows.append('{{%s},{%s},0x%XULL,0x%XULL,{%s},{%s},%d,%d,%d,%d}'%(','.join('0x%Xu'%v for v in model.POSITIONS[c.position]),','.join('0x%Xu'%v for v in c.randoms),c.seed,expected['seed'],','.join(map(str,halves)),','.join(map(str,tail)),c.mode,c.pattern,c.mutation,expected['randoms']))
    palette=','.join(map(str,rom[0x22EC20:0x22EC90]))
    return '#include <ultra64.h>\n'+candidate.DECLARATIONS+body+r'''
typedef struct {u32 position[3],randoms[7];u64 seed,expectedSeed;u16 halves[9];u8 tail[10];int mode,pattern,mutation,calls;} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static const u8 originalPalette[112]={'''+palette+r'''};
static u8 actor[0x180] __attribute__((aligned(16)));static u8 palette[112];
static const Row *current;static u64 seed;static int ordinal,error,submissions;
static s32 (*volatile typedCallback)(u8 *)=func_15149EC4;
typedef char descriptor_layout[(sizeof(EffectDescriptor176A00)==52&&__builtin_offsetof(EffectDescriptor176A00,value16)==0x16&&__builtin_offsetof(EffectDescriptor176A00,firstRGB)==0x28&&__builtin_offsetof(EffectDescriptor176A00,flags)==0x31)?1:-1];
__attribute__((noinline)) s32 func_150ADA20(void){
 int n=ordinal++;if(n>=current->calls)error=1;
 if((current->mutation&1)&&n==0){u32 *p=(u32 *)(actor+0x34);p[0]=0x7FC0ABCD;p[1]=0x80000000;p[2]=0x12345678;}
 if(current->mutation&2)for(int i=36;i<60;i++)palette[i]^=(n*13+17)&255;
 if(current->mode==2){u64 mixed=((seed&1)<<32)|((seed>>1)&0xFFFFFFFFULL);mixed^=(seed&0xFFFFFULL)<<12;seed=mixed^((mixed>>20)&0xFFF);return(s32)seed;}
 return(s32)(n<7?current->randoms[n]:0);
}
__attribute__((noinline)) void func_151429E0(u8 selector,u8 *r,u8 *g,u8 *b){
 if(current->mode){u32 row=selector*12+((u32)func_150ADA20()&3)*3;*r=palette[row];*g=palette[row+1];*b=palette[row+2];}
 else{*r=selector*17;*g=selector*17+31;*b=selector*17+62;}
}
__attribute__((noinline)) void func_1518CA80(EffectDescriptor176A00 *p,u8 mode){
 submissions++;if(mode!=1)error=1;
 const u32 *position=(const u32 *)&p->position;
 for(int i=0;i<3;i++)if(position[i]!=current->position[i])error=1;
 for(int i=0;i<9;i++)if(*(u16 *)((u8 *)p+0x16+i*2)!=current->halves[i])error=1;
 for(int i=0;i<10;i++)if(*((u8 *)p+0x28+i)!=current->tail[i])error=1;
}
static int run(void){
 for(unsigned i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  current=&rows[i];seed=current->seed;ordinal=error=submissions=0;
  for(int k=0;k<0x180;k++)actor[k]=0xA5;
  for(int k=0;k<3;k++)*(u32 *)(actor+0x34+k*4)=current->position[k];
  for(int k=0;k<112;k++)palette[k]=current->pattern?(k*29+current->pattern*71)&255:originalPalette[k];
  if(typedCallback(actor)!=0||error||submissions!=1||ordinal!=current->calls||seed!=current->expectedSeed)return 1;
 }
 return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
