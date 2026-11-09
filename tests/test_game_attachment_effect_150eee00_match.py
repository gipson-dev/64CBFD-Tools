"""Attachment debris: strict two-body delta, original dispatch and bounded native C."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_attachment_effect_150eee00_match as match
from tools.tests import game_attachment_effect_150eee00_oracle as guest
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ROOT=match.ROOT

def controls():
    b=match.SELECTED;pairs={
      'gate_inverted':('if (!(*(u32 *)(owner + 0x94) & D_800A163C[selector]))','if ((*(u32 *)(owner + 0x94) & D_800A163C[selector]))'),
      'wrong_flag':('owner + 0x94','owner + 0x90'),
      'record_stride':('selector * 12','selector * 16'),
      'matrix_stride':('D_800A1638[selector] << 6','D_800A1638[selector] << 5'),
      'helper_value':('owner, selector, 0xFF, 1','owner, selector, 0xFE, 1'),
      'helper_flags':('owner, selector, 0xFF, 1','owner, selector, 0xFF, 0'),
      'helper_result_gate':('func_150EEF80(owner, selector, 0xFF, 1);','if (func_150EEF80(owner, selector, 0xFF, 1) == 0) return;'),
      'signed_remainder':('(u32)func_150ADA20()','func_150ADA20()'),
      'wrong_divisor':('% 3 + 4','% 4 + 4'),
      'wrong_base':('% 3 + 4','% 3 + 3'),
      'header_type':('header.unk0 = 3','header.unk0 = 2'),
      'header_code':('header.unk1 = -1','header.unk1 = 0'),
      'header_kind':('header.unk4 = 0','header.unk4 = 1'),
      'coordinate_axis':('coordinates.unk8 = position[2]','coordinates.unk8 = position[0]'),
      'effect_argument':('&coordinates, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0, 0, 0xFF, 1','&coordinates, 0xFE, 0xFF, 0xFF, 0xFF, 0xFF, 0, 0, 0xFF, 1'),
      'last_pointer':('func_150F0A24(position)','func_150F0A24(position + 1)'),
    };rows={n:b.replace(a,z)for n,(a,z)in pairs.items()};assert all(v!=b for v in rows.values());return rows

def linked(obj,entry,s,label,out,negative=False):
    t,fs,rs=parse_object(obj);f=fs[match.FUNCTION];p=out/label
    if negative:
        assert set(fs)=={match.FUNCTION}and f['value']==0;source=obj
    else:
        asm,unknown=emit_function(t,f,rs,match.FUNCTION,s);assert not unknown,unknown;p.with_suffix('.s').write_text(asm);source=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(source),str(p.with_suffix('.s'))],check=True,capture_output=True)
    p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x600000 : { *(.rodata*) *(.rdata*) *(.lit4*) *(.lit8*) } }\n'%entry)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,v)for n,v in s.items()],'-o',str(p.with_suffix('.elf')),str(source)],check=True,capture_output=True)
    image=sections(p.with_suffix('.elf'));ws=list(struct.unpack_from('>%dI'%(f['size']//4),image['.text'][1]));pools={}
    if '.rodata'in image:
        a,b=image['.rodata'];pools={a+j:v for j,v in enumerate(b)}
    return ws,pools

def code(words,entry):return dict(zip(range(entry,entry+4*len(words),4),words))
def state(m):return m.r,m.f,m.hi,m.lo,m.memory,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word
def check(test,m,initial,c,home=None,s=guest.SYMS):
    expected,calls,snaps=guest.reference(initial,c,home,s);test.assertEqual((guest.public(m.memory),m.calls,m.snapshots),(guest.public(expected),calls,snaps),c)

class DebrisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>80I',cls.rom,match.ROM));cls.raw,_=linked(cls.out/'qualified-owner.o',match.ENTRY,guest.SYMS,'raw-suite',cls.out);assert cls.raw==cls.truth;cls.actual,_,_=match.load_elf_functions(str(ROOT/match.ELF),'mips-linux-gnu-objdump')
    def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def test_01_owner_actual_Make_two_body_image_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(80,96,0,42,42,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['strict_changed_bytes'],q['metadata_reorders'],q['named_metadata_rows'],q['exclusions']),(3,44,313,2,6,0));self.assertTrue(q['helper_placeholder']['still_unmatched']);self.assertEqual(q['helper_placeholder']['matching_credit'],0)
        blob,refs=match.payload(self.out/'qualified-owner.o')
        for j in range(320):
            bad=bytearray(blob);bad[j]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),refs)
        for a in refs:
            bad=dict(refs);bad[a]=[(refs[a][0][0],'wrong')]
            with self.assertRaises(ValueError):match.checked(blob,bad)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+320]
        ats=[0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,320),match.elf_slot_offset(before,match.HELPER_ENTRY,28)]
        ats.extend(p for p,n,_,_ in match.symbol_rows(before)if n in sum(match.SYMBOL_ORDER,()))
        for a in ats:
            bad=bytearray(after);bad[a]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        bad=bytearray(truth);bad[0]^=1
        with self.assertRaises(ValueError):match.strict_image(before,after,bytes(bad))
    def test_02_all_byte_selectors_live_provider_and_invalid_float_paths(self):
        visits=set();n=accesses=0
        for c in guest.cases():
            initial=guest.fixture(c,self.rom);pair=[]
            for ws in(self.truth,self.raw):
                m=guest.Oracle(ws,initial,c).run();check(self,m,initial,c);pair.append(m);visits.update(m.visits)
            self.assertEqual(state(pair[0]),state(pair[1]));n+=1;accesses+=len(pair[0].trace)
        self.assertEqual((n,len(visits)),(1792,80));self.receipt('guest-contract',dict(cases_per_body=n,visited_words=80,accesses_per_body=accesses,actual_readonly_neighbors_for_all_byte_selectors=True,unsigned_random_remainder=True,full_literal_state_equal=True,invalid_float_integer_indefinite_model_guest_only=True,portable_outside_table_claim=False))
    def test_03_GNU_rebases_wrapped_bases_and_fault_prefixes(self):
        selected=[guest.Case(),guest.Case(selector=1,mutation=63),guest.Case(selector=2,base=0),guest.Case(selector=0xAABBCC03,mutation=8),guest.Case(selector=0,base=0xFFFFFFC0,mutation=0)]
        n=0
        for j in range(6):
            entry=match.ENTRY+j*0x10000;s={k:(v+j*0x20000 if k.startswith('func_')else v+j*0x108000)for k,v in guest.SYMS.items()};ws,_=linked(self.out/'qualified-owner.o',entry,s,'rebase-'+str(j),self.out)
            for c in selected:
                initial=guest.fixture(c,self.rom);initial={(a+j*0x108000 if guest.TABLE<=a<guest.TABLE+4096 else a):v for a,v in initial.items()};m=guest.Oracle(ws,initial,c,entry,s).run();check(self,m,initial,c,s=s);n+=1
        fired=delay=0
        for c in selected:
            initial=guest.fixture(c,self.rom);full=guest.Oracle(self.truth,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for ws in(self.truth,self.raw):
                    m=guest.Oracle(ws,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));fired+=1;delay+=pair[0].delay_of is not None
        self.receipt('rebases-aliases-faults',dict(GNU_links=6,rebased_candidate_cases=n,wrapped_base_candidate_cases=6,fired_fault_pairs=fired,delay_slot_cuts=delay,home_redirection_and_selector_byte_mutation_guest_only=True))
    def test_04_complete_wrapper_dispatcher_and_registration(self):self.receipt('callers',caller_checks(self))
    def test_05_original_helper_ABI_and_point_transform_connections(self):self.receipt('connections',connection_checks(self))
    def test_06_compiled_semantic_controls(self):
        rows={};cases=[c for c in guest.cases()if c.selector&255<4]
        for name,b in controls().items():
            obj,diag=match.compile_owner(ROOT,self.out,match.HEADER+b,'negative-'+name);self.assertFalse(diag);ws,pools=linked(obj,match.ENTRY,guest.SYMS,'negative-link-'+name,self.out,True);witness=None
            for c in cases:
                initial=guest.fixture(c,self.rom);initial.update(pools);m=guest.Oracle(ws,initial,c).run()
                try:check(self,m,initial,c)
                except AssertionError:witness=c;break
            self.assertIsNotNone(witness,name);rows[name]=dict(compiled=True,counterexample=vars(witness),pool_bytes=len(pools))
        self.receipt('compiled-controls',rows)
    def test_07_native32_defined_table_domain(self):
        text,n=native_program(self.rom);p=self.out/'native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
        self.receipt('native-contract',dict(cases_per_profile=n,profiles=['O0','O2','O3'],table_domain=[0,1,2,3],typed_two_argument_target_only=True,legacy_extra_argument_not_claimed_portable=True,Header_size=6,Header2_size=12,owner_flags_offset=0x94,owner_matrix_offset=0x1D4,compiled_controls=len(controls()),all_controls_effective=True,all_owner_bytes_and_defined_packet_fields=True,Header_padding_not_read=True,UBSan_traps=True))

def caller_checks(test):
    wrapper=list(struct.unpack_from('>13I',test.rom,0x9DB40));dispatcher=list(struct.unpack_from('>16I',test.rom,0x9F1E8));test.assertEqual(test.actual['func_15070690'],wrapper);test.assertEqual(test.actual['func_15071D38'],dispatcher)
    class Caller(guest.Oracle):
        def record_call(self,t):
            if t in(guest.ENTRY,0x15070690):self.calls.append((t,tuple(map(guest.u32,self.arguments(3 if t==guest.ENTRY else 1)))))
            else:super().record_call(t)
    n=0
    for command,phase,mu in itertools.product((0x3E,0x3F,0x40,0x41,0,0xFFFFFFFF,0x8000003E,0xAABBCC3F),(0,8),(0,1,4,8,16,32)):
        c=guest.Case(selector=(command-62)&255,phase=phase,mutation=mu);initial=guest.fixture(c,test.rom);home=guest.STACK+phase-24;expected,calls,snaps=guest.reference(initial,c,home)
        for ws in(test.truth,test.raw):
            m=Caller(wrapper,initial,c,entry=0x15070690,connected=code(ws,guest.ENTRY),arguments=(command,));m.semantic_home=home;m.run();test.assertEqual((guest.public(m.memory),m.calls,m.snapshots),(guest.public(expected),[(guest.ENTRY,(c.owner,c.selector,command)),*calls],snaps))
        n+=1
    d=0
    for command,phase,mu in itertools.product((62,63),(0,8),range(64)):
        c=guest.Case(selector=command-62,phase=phase,mutation=mu);initial=guest.fixture(c,test.rom);guest.put(initial,0x800D1580,command);initial.update({0x80086150+j:b for j,b in enumerate(test.rom[0x22AC10:0x22AE10])});home=guest.STACK+phase-48;expected,calls,snaps=guest.reference(initial,c,home)
        for ws in(test.truth,test.raw):
            connected=code(wrapper,0x15070690);connected.update(code(ws,guest.ENTRY));m=Caller(dispatcher,initial,c,entry=0x15071D38,connected=connected,arguments=());m.semantic_home=home;m.run();test.assertEqual((guest.public(m.memory),m.calls,m.snapshots),(guest.public(expected),[(0x15070690,(command,)),(guest.ENTRY,(c.owner,c.selector,command)),*calls],snaps))
        d+=1
    before,after=test.prepared['predecessor_elf'].read_bytes(),test.prepared['qualified_elf'].read_bytes();at=match.elf_slot_offset(before,0x80086248,8);test.assertEqual(before[at:at+8],struct.pack('>II',0x15070690,0x15070690));test.assertEqual(before[at:at+8],after[at:at+8]);test.assertEqual((ROOT/match.CALLER_OBJECT).read_bytes(),(test.out/'frozen'/match.CALLER_OBJECT).read_bytes())
    return dict(wrapper_cases_per_body=n,dispatcher_cases_per_body=d,complete_wrapper_words=13,complete_dispatcher_words=16,baseline_exact=True,registered_commands=[62,63],extra_incoming_A2_guest_only=True,registration_and_caller_object_unchanged=True)


def connection_checks(test):
    from tools.tests.test_game_point_transform_match import PointOracle,STATUS,DIAGNOSTIC,TRANSFORM
    from tools.tests.game_attachment_position_150d88e0_oracle import transform
    helper=list(struct.unpack_from('>259I',test.rom,0x11C430));abi=0
    for owner,selector,phase in itertools.product((0,guest.OWNER),(0,1,2,255),(0,8)):
        c=guest.Case(selector=selector,phase=phase);initial=guest.fixture(c,test.rom);args=(owner,selector,0xABCD00FF,0x87654321);m=guest.Oracle(helper,initial,c,entry=match.HELPER_ENTRY,arguments=args)
        if owner and selector<2:
            m.code=WindowCode(m.code,m);m.code.ends=(0x150EEFE0,)
            with test.assertRaises(WindowBoundary):m.run()
            test.assertEqual((m.r[19],m.r[20]),(255,0x87654321))
        else:m.run();test.assertEqual(m.r[2],0)
        h=guest.STACK+phase;test.assertEqual(tuple(guest.read(m.memory,h+4*j)for j in range(3)),args[:3]);abi+=1
    stubs=0
    for selector,phase,mu in itertools.product(range(4),(0,8),(0,8,16,32)):
        c=guest.Case(selector=selector,phase=phase,mutation=mu);initial=guest.fixture(c,test.rom)
        for ws in(test.truth,test.raw):
            m=guest.Oracle(ws,initial,c,connected=code(match.HELPER_WORDS,match.HELPER_ENTRY)).run();check(test,m,initial,c)
        stubs+=1
    point=list(struct.unpack_from('>98I',test.rom,0x1705E4));matrix=list(struct.unpack_from('>40I',test.rom,0xD4E10));test.assertEqual(test.actual['func_15143134'],point);test.assertEqual(test.actual['func_150A7960'],matrix)
    class Connected(guest.Oracle,PointOracle):
        def __init__(self,ws,initial,c,program):
            self.case=c;self.syms=guest.SYMS;self.semantic_home=guest.STACK+c.phase;self.snapshots=[]
            PointOracle.__init__(self,ws,initial,(c.owner,c.selector),phase=c.phase,connected=program,entry=guest.ENTRY)
            self.trace=[];self.all_accesses=0;self.cut=None;self.copy_observations=[];self.hi=self.lo=0
        def record_call(self,t):
            if t in guest.SYMS.values():guest.Oracle.record_call(self,t)
            else:PointOracle.record_call(self,t)
        def hook(self,t):
            if t in guest.SYMS.values():guest.Oracle.hook(self,t)
            else:PointOracle.hook(self,t)
    visits=set();n=0;program=code(point,guest.SYMS['func_15143134']);program.update(code(matrix,TRANSFORM))
    for selector,phase,seed in itertools.product(range(4),(0,8),(0,1)):
        c=guest.Case(selector=selector,phase=phase,seed=seed);initial=guest.fixture(c,test.rom);p=guest.TABLE+selector*12;a=guest.MATRICES+(guest.read(initial,guest.JOINT+selector,1)<<6);values=transform(initial,a,*(guest.read(initial,p+4*j)for j in range(3)));c=replace(c,results=values);expected,calls,snaps=guest.reference(initial,c);guest.put(expected,STATUS,0);guest.put(expected,DIAGNOSTIC,a)
        for j in range(3):guest.put(expected,STATUS+8+j*4,guest.read(initial,p+j*4))
        pair=[]
        for ws in(test.truth,test.raw):
            m=Connected(ws,initial,c,program).run();rootcalls=[row for row in m.calls if row[0]in guest.SYMS.values()];test.assertEqual((guest.public(m.memory),rootcalls,m.snapshots),(guest.public(expected),calls,snaps));pair.append(m);visits.update(m.visits)
        test.assertEqual((pair[0].r,pair[0].f,pair[0].memory,pair[0].calls,pair[0].snapshots),(pair[1].r,pair[1].f,pair[1].memory,pair[1].calls,pair[1].snapshots));n+=1
    rng=list(struct.unpack_from('>18I',test.rom,0xDAED0));test.assertEqual(test.actual['func_150ADA20'],rng)
    return dict(original_helper_ABI_cases=abi,helper_prefix_and_early_returns_only=True,typed_unmatched_placeholder_connection_cases_per_body=stubs,point_connection_cases_per_body=n,point_helper_words=98,point_visited_words=sum(0x15143134<=a<0x151432BC for a in visits),matrix_words=40,matrix_visited_words=sum(TRANSFORM<=a<TRANSFORM+160 for a in visits),float_matrix_path_only=True,random_baseline_exact_words=18,random_execution_provider_only=True,whole_helper_or_hardware_claim=False)


def native_program(rom):
    chosen=[guest.Case(selector=s,flags=f,base=b,mutation=mu,random=r,seed=s%3)for s,f,b,mu,r in itertools.product(range(4),(0,0xFFFFFFFF),(0,guest.MATRICES),(0,1,8,16,32,9,24),(0,2,0x80000000,0xFFFFFFFF))]
    rows=[];arr=lambda a:'{'+','.join('0x%Xu'%guest.u32(v)for v in a)+'}'
    for c in chosen:
        initial=guest.fixture(c,rom);after,calls,snaps=guest.reference(initial,c);by={z[0]:z for z in snaps};rng=by[2][3]if 2 in by else(0,0,0);h=by[3][2]if 3 in by else bytes(6);coordinates=tuple(int.from_bytes(by[3][3][4*j:4*j+4],'big')for j in range(3))if 3 in by else(0,0,0);cv=by[3][4]if 3 in by else(0,0,0);last=by[4][2]if 4 in by else(0,0,0)
        values=[str(v)for v in(c.selector,c.flags,c.base,c.mutation,c.random,c.seed,len(calls),guest.read(after,c.owner+0x1D4),guest.read(initial,c.owner+0x90))];values.extend((arr(c.results),arr(rng),arr((h[0],h[1],int.from_bytes(h[2:4],'big'),h[4])),arr(coordinates),arr(cv),arr(last)));rows.append('{'+','.join(values)+'}')
    text=match.HEADER+r'''
typedef struct {u8 prefix[0x90];u32 spare,flags;u8 middle[0x13C];u8 *matrix;u8 tail[0x68];} Owner;
typedef char layout[sizeof(void*)==4&&sizeof(Owner)==0x240&&__builtin_offsetof(Owner,flags)==0x94&&__builtin_offsetof(Owner,matrix)==0x1D4&&sizeof(Header)==6&&sizeof(Header2)==12?1:-1];
typedef struct {u32 selector,flags,base,mutation,random,seed,calls,resource,spare,results[3],rng[3],header[4],coordinates[3],createvec[3],last[3];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
u8 D_800A163C[4]={64,32,0,0};u8 D_800A1638[4]={22,26,0,0};f32 D_800A15F0[12]={-78,0,0,78,0,0,-150,0,0,150,0,0};
static Owner owner;static f32 matrices[512],alternate[512];static const Row *current;static f32 *vector;static u32 calls,bad;
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static void begin(u32 stage){if(calls++!=stage)bad=1;}
static void checkvector(const u32 *expected){u32 j;if(!vector){bad=1;return;}for(j=0;j<3;j++)if(word(vector[j])!=expected[j])bad=1;}
s32 func_150EEF80(u8*p,u8 selector,u8 value,s32 flags){begin(0);if(p!=(u8*)&owner||selector!=current->selector||value!=255||flags!=1)bad=1;if(current->mutation&1)owner.matrix=current->base?(u8*)alternate:(u8*)matrices;return 0;}
void func_15143134(f32*p,f32*q,u8*m){u32 j;f32 *expected=D_800A15F0+current->selector*3;begin(1);vector=q;if(p!=expected)bad=1;else for(j=0;j<3;j++)if(word(p[j])!=word(expected[j]))bad=1;if(m!=owner.matrix+((u32)D_800A1638[current->selector]<<6))bad=1;for(j=0;j<3;j++)q[j]=real(current->results[j]);if(current->mutation&32)owner.matrix=0;}
s32 func_150ADA20(void){begin(2);checkvector(current->rng);if(current->mutation&8){vector[0]=real(0xC29B8000U);vector[1]=real(0x41BF0000U);vector[2]=real(0x3F000001U);}return(s32)current->random;}
struct225 *func_151602C0(Header*h,Header2*c,s32 a,s32 b,s32 d,s32 e,u8 f,u8 g,s32 offset,u8 priority,s32 flags){begin(3);if((u8)h->unk0!=current->header[0]||(u8)h->unk1!=current->header[1]||(u16)h->unk2!=current->header[2]||(u8)h->unk4!=current->header[3]||(u32)c->unk0!=current->coordinates[0]||(u32)c->unk4!=current->coordinates[1]||(u32)c->unk8!=current->coordinates[2]||a!=255||b!=255||d!=255||e!=255||f!=255||g!=0||offset!=0||priority!=255||flags!=1)bad=1;checkvector(current->createvec);if(current->mutation&16){vector[0]=10;vector[1]=-10;vector[2]=1;}return 0;}
s32 func_150F0A24(f32*p){begin(4);if(p!=vector){bad=1;return 0;}checkvector(current->last);return 0;}
'''
    functions=dict(selected=match.SELECTED,**controls())
    for n,b in functions.items():text+=b.replace(match.FUNCTION,n,1)+'\n'
    text+=r'''
static int check(void(*fn)(u8*,u8),const Row*r){u32 i;u8 *p=(u8*)&owner;current=r;calls=bad=0;vector=0;
for(i=0;i<sizeof(owner);i++)p[i]=(u8)(i*29+r->seed*17+90);owner.spare=r->spare;owner.flags=r->flags;owner.matrix=r->base?(u8*)matrices:0;
fn((u8*)&owner,(u8)r->selector);
if(calls!=r->calls||owner.spare!=r->spare||owner.flags!=r->flags||owner.matrix!=(r->resource==0x70000U?(u8*)matrices:r->resource==0x72000U?(u8*)alternate:0))bad=1;
for(i=0;i<sizeof(owner);i++)if((i<0x90||i>=0x98)&&(i<0x1D4||i>=0x1D8)&&p[i]!=(u8)(i*29+r->seed*17+90))bad=1;
return !bad;}
static int run(void){u32 i,j,killed['''+str(len(functions))+r''']={0};void(*functions[])(u8*,u8)={'''+','.join(functions)+r'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i))killed[j]=1;}
for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
    return text,len(chosen)


if __name__=='__main__':unittest.main()
