"""Material callback: complete owner/image, binary32 contract and real dispatcher."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_material_tile_animation_candidates as candidate
from tools.experiments import game_material_tile_animation_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_material_tile_animation_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT

def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses

class MaterialTileAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>71I',cls.rom,match.ROM))
        cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalMaterialTile',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-material-tile',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.words

    def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def contract(self,words,c,initial=None,s=None,entry=match.ENTRY):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s)if initial is None else initial
        m=model.Oracle(words,initial,c,s,entry).run();expected,value=model.reference(initial,c,s)
        self.assertEqual((m.memory,m.r[2]),(expected,value),c);self.assertFalse(m.calls)
        return m

    def compare(self,c,initial=None,s=None,images=None,entry=match.ENTRY):
        images=(self.retail,self.words)if images is None else images
        ms=[self.contract(words,c,initial,s,entry)for words in images]
        self.assertEqual(state(ms[0]),state(ms[1]));return ms

    def test_01_owner_register_guards_and_corruption_controls(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings']),(71,0,9,4))
        self.assertEqual(q['raw_neighbors'],q['neighbors']);self.assertEqual(q['changed_bodies'],[match.FUNCTION])
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+284]
        for at in range(284):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        # Every changed bit belongs to a register field, never opcode/immediate.
        for at,a,b in match.PATCHES:
            word=a>>26
            mask=0x03FFF800 if word==0 else 0x001F0000 if word==17 else 0x03FF0000
            self.assertEqual((a^b)&~mask,0)
        self.receipt('owner-contract',dict(words=71,guards=9,bindings=4,neighbors=q['neighbors'],raw_corruption_controls=284,binding_controls=4,register_fields_only=True))

    def test_02_binary32_boundaries_and_command_scan(self):
        count=0;visited=set()
        for c in model.cases():
            ms=self.compare(c);raw=self.contract(self.raw,c);self.assertEqual(raw.trace,ms[0].trace);visited.update(ms[0].visits);count+=1
        self.assertEqual(visited,set(range(match.ENTRY,match.ENTRY+284,4))-{match.ENTRY+28})
        self.receipt('guest-contract',dict(cases_per_body=count,bodies=3,reachable_words=70,unreachable_literal_offset='0x1C',binary32_each_operation=True,NaN_gate_rejected=True,negative_offset_override=True))

    def test_03_aliases_and_every_fired_access_prefix(self):
        aliases=cuts=0
        for c in(model.Case(actor=model.MATERIAL),model.Case(animation=model.MATERIAL+0x10,time=model.bits(23.)),model.Case(animation=model.MATERIAL+0x10,time=model.bits(40.))):
            self.compare(c);self.contract(self.raw,c);aliases+=1
        for alternate in(0x41C0,0x4220,0x4000):
            c=model.Case(animation=model.MATERIAL+0x10,primary=0x41B8,alternate=alternate,time=model.bits(30.))
            self.compare(c);self.contract(self.raw,c);aliases+=1
        for c in(model.Case(animation=0),model.Case(kind=0),model.Case(time=model.bits(22.)),model.Case(index=4),model.Case(scale=model.bits(-0.5),index=1)):
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.words,self.raw):
                    m=model.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual((ms[0].trace,ms[0].memory),(ms[2].trace,ms[2].memory));cuts+=1
        c=model.Case(animation=0);initial={};model.put(initial,c.actor+0x2D0,0);self.compare(c,initial)
        self.receipt('aliases-faults',dict(guest_aliases=aliases,fired_access_prefixes=cuts,raw_memory_and_trace_equal=True,fitted_complete_fault_state_equal=True,null_animation_needs_no_material=True))

    def test_04_registered_original_dispatcher_and_zero_result(self):
        self.assertEqual(match.census(ROOT)['index'],1)
        pc=0x15030578;body=list(struct.unpack_from('>11I',self.rom,0x5DA28));count=0
        for c in(model.Case(),model.Case(index=0),model.Case(kind=0),model.Case(animation=0),model.Case(time=model.bits(40.)),model.Case(scale=model.bits(-0.5))):
            initial=model.fixture(c);initial[c.material+7]=1;model.put(initial,0x800841C4,match.ENTRY)
            expected,value=model.reference(initial,c);ms=[]
            for target in(self.retail,self.words,self.raw):
                code=dict(zip(range(match.ENTRY,match.ENTRY+284,4),target));m=model.Oracle(body,initial,c,entry=pc,connected=code)
                m.r[17]=c.material;m.r[19]=c.actor;m.r[18]=0x12345678
                m.code[0x150305A4]=0;m.code=WindowCode(m.code,m);m.code.ends=(0x150305A4,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.calls,[(match.ENTRY,(c.material,c.actor))]);self.assertEqual(m.memory,expected);self.assertEqual(m.r[18],value);ms.append(m)
            self.assertEqual(state(ms[0]),state(ms[1]));count+=1
        self.receipt('dispatcher',dict(original_words=11,cases_per_body=count,table_index=1,arguments=['material','actor'],s2_consumes_zero=True,full_parent_or_gameplay_claimed=False))

    def test_05_independent_GNU_rebases_and_carry_edges(self):
        links=cases=0
        for index,(entry,table,scale)in enumerate(((match.ENTRY,0x80107FFC,0x80208000),(0x18017FFC,0x80308000,0x80407FFC),(0x1A028000,0x8050FFFC,0x80600000))):
            s={'D_80090298':table,'D_800A0B10':scale};images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>71I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2])
            for c in(model.Case(),model.Case(index=0),model.Case(time=model.bits(23.)),model.Case(time=model.bits(40.)),model.Case(scale=model.bits(-0.5)),model.Case(animation=0)):
                self.compare(c,s=s,images=(images[0],images[2]),entry=entry);self.contract(images[1],c,s=s,entry=entry);cases+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=cases,all_four_binding_carry_edges=True))

    def test_06_native_and_effective_IDO_controls(self):
        controls=model.controls();witnesses=list(model.cases())[-128:]+[model.Case(kind=0),model.Case(animation=0),model.Case(time=model.bits(23.)),model.Case(time=model.bits(40.)),model.Case(scale=model.bits(-0.5),old=0xF2FFF000),model.Case(time=model.bits(40.),scale=model.bits(-2.),old=0xF2FFF000)]
        for name,body in controls.items():
            source=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1)
            obj,diag=candidate.compile_owner(ROOT,self.out,source,'negative-'+name);self.assertFalse(diag)
            words=model.bound(obj,model.symbols());effective=False
            for c in witnesses:
                initial=model.fixture(c);model.put(initial,model.symbols()['D_80090298']+20,0xABCD1234)
                expected,value=model.reference(initial,c)
                try:m=model.Oracle(words,initial,c).run()
                except (AssertionError,KeyError):effective=True;break
                if(m.memory,m.r[2])!=(expected,value):effective=True;break
            self.assertTrue(effective,name)
        for label,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in controls.items()]:
            p=self.out/('native-'+label+'.c');p.write_text(native_source(body));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),label)
            self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,label)
        self.receipt('native-controls',dict(positive_profiles=['O0','O2','O3'],positive_executions=9600,native_controls=len(controls),IDO_controls=len(controls),UBSan=True,first_command_byte_explicit=True,portable_native_aliasing_claimed=False))

    def test_07_literal_image_corruptions(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+284]
        delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,284)
        offsets=(0,at,at+283,at+284,0x29F1DC,0x2BE30C,0x2E5966,0x2FF1DF,len(after)-1)
        for off in offsets:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        self.receipt('strict-controls',dict(literal_ELF_changed_bytes=delta,named_symbol_serialization_bytes=30,corruption_controls=len(offsets),exclusions=0))

def native_source(body):
    return '#include <ultra64.h>\n'+candidate.DECLARATIONS+body+r'''
s32 D_80090298[8]; f32 D_800A0B10;
static u8 material[64] __attribute__((aligned(16)));
static u8 actor[0x300] __attribute__((aligned(16)));
static u8 animation[32] __attribute__((aligned(16)));
static Gfx commands[12]; static Gfx *holder;
static f32 frombits(u32 b) { union { u32 u; f32 f; } x; x.u=b;return x.f; }
static int run(void) {
 const u32 times[]={0,0x41B7FFFF,0x41B80000,0x41B80001,0x41F00000,0x421FFFFF,0x42200000,0x42200001,0x7FC12345,0x7F800000};
 const u32 scales[]={0x3D70F0F1,0,0xBF000000,0xC0000000,0x40000000};
 for(unsigned t=0;t<10;t++)for(unsigned sc=0;sc<5;sc++)for(int kind=12;kind<=13;kind++)for(int present=0;present<2;present++)for(int index=0;index<8;index++)for(unsigned pattern=0;pattern<2;pattern++) {
  for(unsigned i=0;i<sizeof(material);i++)material[i]=0xA5;
  for(unsigned i=0;i<sizeof(actor);i++)actor[i]=0;
  for(int i=0;i<12;i++){commands[i].words.w0=0xDEAD0000;commands[i].words.w1=0x12340000+i;*(u8 *)&commands[i]=0xE7;}
  commands[index].words.w0=pattern?0xFFFFFFFF:0;*(u8 *)&commands[index]=0xF2;
  u32 previous=(commands[index].words.w0>>12)&0xFFF;
  D_80090298[5]=0x1234;D_80090298[6]=0x12340548;D_80090298[7]=(s32)0x87650547;
  D_800A0B10=frombits(scales[sc]);*(f32 *)(animation+8)=frombits(times[t]);
  *(u8 **)(actor+0x2D0)=present?animation:0;*(u16 *)(actor+0x84)=kind;
  holder=commands;*(Gfx ***)(material+0x24)=&holder;
  u32 old[24];for(int i=0;i<12;i++){old[2*i]=commands[i].words.w0;old[2*i+1]=commands[i].words.w1;}
  f32 time=frombits(times[t]);int active=present&&kind==13&&time>=23.0f&&time<=40.0f;
  u32 expected=old[2*index];
  if(active){volatile f32 difference=time-23.0f;volatile f32 fraction=difference*D_800A0B10;volatile f32 product=70.0f*fraction;volatile f32 sum=product+2.0f;int offset=(int)sum;int coordinate=offset<0?offset+(int)previous:offset;expected=0xF2000002|((coordinate&0xFFF)<<12);}
  s32 (*typed)(u8 *,u8 *)=func_150D82BC;
  if(typed(material,actor)!=0)return 1;
  u16 expected_material=present?(active?0x0547:0x0548):0xA5A5;
  if(*(u16 *)(material+0x18)!=expected_material)return 1;
  for(int i=0;i<12;i++)if(commands[i].words.w0!=(i==index?expected:old[2*i])||commands[i].words.w1!=old[2*i+1])return 1;
 }
 return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
