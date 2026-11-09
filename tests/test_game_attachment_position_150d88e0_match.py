"""Attachment positions: literal all-byte behavior and defined-domain native C."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_attachment_position_150d88e0_match as match
from tools.tests import game_attachment_position_150d88e0_oracle as guest
from tools.tests import game_actor_coordinate_effect_dispatch_oracle as parent
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ROOT=match.ROOT

def controls():
    b=match.SELECTED
    pairs={
        'wrong_joint3':('joint = 18','joint = 19'),
        'wrong_joint4':('joint = 21','joint = 22'),
        'wrong_joint5':('joint = 15','joint = 16'),
        'wrong_joint6':('joint = 24','joint = 25'),
        'wrong_x3':('x = -7.0f','x = -8.0f'),
        'wrong_x4':('x = -4.0f','x = -3.0f'),
        'wrong_x5':('joint = 15; x = 5.0f','joint = 15; x = 6.0f'),
        'wrong_x6':('joint = 24; x = 5.0f','joint = 24; x = 6.0f'),
        'wrong_z3':('z = 30.0f','z = 29.0f'),
        'wrong_z4':('z = 35.0f','z = 34.0f'),
        'wrong_z5':('z = 20.0f','z = 21.0f'),
        'wrong_z6':('z = 31.0f','z = 32.0f'),
        'wrong_y':('y = 0.0f','y = 1.0f'),
        'wrong_stride':('joint * 64','joint * 16'),
        'wrong_return':('return 1;','return 0;'),
        'wrong_axis':('position[2] = z','position[2] = x'),
        'wrong_output_pointer':('x, y, z, &x, &y, &z','x, y, z, &x, &y, &x'),
    }
    rows={n:b.replace(a,z)for n,(a,z)in pairs.items()};assert all(v!=b for v in rows.values());return rows

def guest_controls():
    b=match.SELECTED
    return dict(full_word_selector=b.replace('u8 selector','u32 selector'),default_return=b.replace('switch (selector) {','switch (selector) {\n        default: return 0;'),default_initialize=b.replace('s32 joint;','s32 joint = 0;').replace('f32 x;','f32 x = 0.0f;').replace('f32 z;','f32 z = 0.0f;'))

def linked(obj,entry,label,out,helper=guest.MATRIX):
    t,fs,rs=parse_object(obj);f=fs[match.FUNCTION];asm,unknown=emit_function(t,f,rs,match.FUNCTION,{'func_150A7960':helper});assert not unknown;p=out/label
    p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,'--defsym=func_150A7960=0x%X'%helper,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
    return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

def negative_linked(obj,label,out):
    _,fs,_=parse_object(obj);assert set(fs)=={match.FUNCTION};f=fs[match.FUNCTION];assert f['value']==0;p=out/label
    p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x600000 : { *(.rodata*) *(.rdata*) *(.lit4*) *(.lit8*) } }\n'%match.ENTRY)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,'--defsym=func_150A7960=0x%X'%guest.MATRIX,'-o',str(p.with_suffix('.elf')),str(obj)],check=True,capture_output=True)
    image=sections(p.with_suffix('.elf'));ws=list(struct.unpack_from('>%dI'%(f['size']//4),image['.text'][1]));pools={}
    for n,(address,data)in image.items():
        if n=='.rodata':pools.update({address+i:v for i,v in enumerate(data)})
    return ws,pools

def code(words,entry):return dict(zip(range(entry,entry+4*len(words),4),words))
def state(m):return m.r,m.f,m.hi,m.lo,m.memory,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word
def check(test,m,initial,c,home=None,helper=guest.MATRIX):
    expected,calls,snaps,result,destination=guest.reference(initial,c,home,helper)
    test.assertEqual((guest.public(m.memory),m.calls,m.snapshots,m.r[2],guest.data(m.memory,destination,12)),(guest.public(expected),calls,snaps,result,guest.data(expected,destination,12)),c)

class AttachmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>80I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);assert cls.raw==cls.truth
        cls.actual,_,_=match.load_elf_functions(str(ROOT/match.ELF),'mips-linux-gnu-objdump')
    def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def test_01_owner_actual_Make_image_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['slot_words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(80,80,64,0,8,8,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['strict_changed_bytes'],q['exclusions']),(3,9,247,0))
        blob,refs=match.payload(self.out/'qualified-owner.o')
        for i in range(320):
            bad=bytearray(blob);bad[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[(refs[at][0][0],'wrong')]
            with self.assertRaises(ValueError):match.checked(blob,bad)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+320]
        for i in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,320)):
            bad=bytearray(after);bad[i]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        bad=bytearray(truth);bad[0]^=1
        with self.assertRaises(ValueError):match.strict_image(before,after,bytes(bad))
    def test_02_all_selector_bytes_default_stack_and_provider_effects(self):
        visited=set();n=accesses=unsupported=0
        for c in guest.cases():
            initial=guest.fixture(c);pair=[]
            for ws in(self.truth,self.raw):
                m=guest.Oracle(ws,initial,c).run();check(self,m,initial,c);visited.update(m.visits);pair.append(m)
            self.assertEqual(state(pair[0]),state(pair[1]));n+=1;accesses+=len(pair[0].trace);unsupported+=(c.selector&255)not in guest.OFFSETS
        self.assertEqual((n,len(visited)),(1248,80));self.receipt('guest-contract',dict(cases_per_body=n,unsupported_cases_per_body=unsupported,visited_words=80,accesses_per_body=accesses,all_byte_and_high_word_selectors=True,default_reads_seeded_private_locals=True,full_literal_state_equal=True,portable_default_behavior_claim=False))
    def test_03_GNU_rebases_aliases_and_fault_prefixes(self):
        selected=[guest.Case(),guest.Case(selector=4,mutation=15),guest.Case(selector=5,phase=8),guest.Case(selector=0,stale_joint=0x81234567,mutation=2),guest.Case(selector=0xAABBCC06,mutation=4)]
        total=0
        for i in range(6):
            entry=match.ENTRY+i*0x10000;helper=guest.MATRIX+i*0x20000;ws=linked(self.out/'qualified-owner.o',entry,'rebase-'+str(i),self.out,helper)
            for c in selected:
                initial=guest.fixture(c);m=guest.Oracle(ws,initial,c,entry,helper).run();check(self,m,initial,c,helper=helper);total+=1
        aliases=0
        for output in(guest.MATRICES,guest.MATRICES+24*64,guest.OWNER+0x180,guest.STACK-16,guest.STACK-12,guest.STACK-8):
            for c in selected:
                c=replace(c,output=output);initial=guest.fixture(c);m=guest.Oracle(self.raw,initial,c).run();check(self,m,initial,c);aliases+=1
        fired=delay=0
        for c in selected:
            initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for ws in(self.truth,self.raw):
                    m=guest.Oracle(ws,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));fired+=1;delay+=pair[0].delay_of is not None
        self.receipt('rebases-aliases-faults',dict(GNU_links=6,rebase_cases_per_body=total,guest_alias_cases_per_body=aliases,fired_fault_pairs=fired,delay_slot_cuts=delay,private_local_and_home_cases_guest_only=True))
    def test_04_complete_caller_and_real_dispatch_windows(self):
        self.receipt('callers',caller_checks(self))
    def test_05_original_handwritten_matrix_helper(self):
        helper=list(struct.unpack_from('>40I',self.rom,0xD4E10));self.assertEqual(self.actual['func_150A7960'],helper);connected=code(helper,guest.MATRIX);visits=set();n=0
        for selector,phase,seed in itertools.product(range(256),(0,8),(0,1)):
            c=guest.Case(selector=selector,phase=phase,seed=seed,stale_joint=selector%32,connected=True);initial=guest.fixture(c)
            for ws in(self.truth,self.raw):
                m=guest.Oracle(ws,initial,c,connected=connected).run();check(self,m,initial,c);visits.update(m.visits)
            n+=1
        self.assertEqual(sum(guest.MATRIX<=p<guest.MATRIX+160 for p in visits),40)
        self.receipt('connections',dict(cases_per_body=n,helper_words=40,helper_visited_words=40,baseline_exact=True,balanced_single_precision_RNE_model=True,seeded_defaults_guest_only=True,hardware_FCSR_or_portable_default_claim=False))
    def test_06_compiled_controls_defined_and_guest_only(self):
        rows={};cases=list(guest.cases())
        for n,body in {**controls(),**guest_controls()}.items():
            obj,diag=match.compile_owner(ROOT,self.out,match.HEADER+body,'negative-'+n);self.assertFalse(diag);ws,pools=negative_linked(obj,'negative-link-'+n,self.out);witness=None
            for c in cases:
                if n not in guest_controls()and(c.selector&255)not in guest.OFFSETS:continue
                initial=guest.fixture(c);initial.update(pools);m=guest.Oracle(ws,initial,c).run()
                try:check(self,m,initial,c)
                except AssertionError:witness=c;break
            self.assertIsNotNone(witness,n);rows[n]=dict(compiled=True,counterexample=vars(witness),native_control=n in controls(),pool_bytes=len(pools))
        self.receipt('compiled-controls',rows)
    def test_07_native32_defined_domain_layout_and_controls(self):
        text,n=native_program();p=self.out/'native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            # The source deliberately retains retail's undefined default path.
            # Only 3..6 are called here; suppress that one static GCC warning.
            binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-Wno-maybe-uninitialized','-fno-builtin','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
        self.receipt('native-contract',dict(cases_per_profile=n,profiles=['O0','O2','O3'],defined_selectors=[3,4,5,6],caller_domain_not_assumed=True,portable_default_claim=False,expected_default_path_static_warning_suppressed=True,compiled_controls=len(controls()),all_controls_effective=True,typed_mixed_float_ABI=True,real_C_matrix_model_and_mock_provider=True,all_output_owner_and_matrix_words=True,UBSan_traps=True,private_homes_and_locals_excluded=True))

def caller_reference(initial,c,pcase,home):
    m=dict(initial);calls=[];snapshots=[];guest.put(m,home+4,pcase.selector);guest.put(m,home+8,pcase.unused)
    if not guest.read(m,c.owner+0x1D4):return m,calls,snapshots
    guest.put(m,home,c.owner);child=replace(c,output=home-12,selector=pcase.selector&255)
    calls.append((match.ENTRY,(child.output,c.owner,pcase.selector&255)));m,inner,snapshots,_,_=guest.reference(m,child,home-64);calls.extend(inner)
    v=home-12;calls.append((parent.SYMS['func_151875E0'],(guest.read(m,v),guest.read(m,v+4),guest.read(m,v+8),30,15,7,guest.read(m,0x800A0B30),guest.read(m,0x800A0B34))))
    parent.effect(m,pcase,1);owner=guest.read(m,home);height=parent.bits(parent.floating(guest.read(m,owner+0x180))+4.0)
    calls.append((parent.SYMS['func_15165F80'],(0xFFFFFFFF,parent.trunc(guest.read(m,v)),parent.trunc(height),parent.trunc(guest.read(m,v+8)),4,50,0,255,0)))
    return m,calls,snapshots

def caller_checks(test):
    original=list(struct.unpack_from('>55I',test.rom,0x105EE4));test.assertEqual(test.actual['func_150D8A34'],original)
    class Caller(parent.Oracle):
        def record_call(self,t):
            super().record_call(t)
            if t==guest.MATRIX:
                a=self.calls[-1][1];self.child_snaps.append((a,tuple(guest.read(self.memory,p)for p in a[4:]),guest.data(self.memory,self.child.output,12)))
        def hook(self,t):
            if t==guest.MATRIX:
                old=self.case;self.case=self.child;self.position_home=guest.STACK+self.child.phase-64
                try:guest.Oracle.hook(self,t)
                finally:self.case=old
            else:super().hook(t)
    cases=0
    def setup(c,pcase):
        initial=parent.fixture(pcase);initial.update(guest.fixture(c));guest.seed_locals(initial,c,guest.STACK+c.phase-64);return initial
    selectors=tuple(range(256))+(0xAABBCC03,0x80000006,0xFFFFFFFF)
    for selector,phase,active in itertools.product(selectors,(0,8),(0,guest.MATRICES)):
        c=guest.Case(selector=selector,phase=phase,base=active,mutation=(selector&15),stale_joint=selector%32);pc=parent.Case(selector=selector,phase=phase,active=active,mutation=(16,32,64)[selector%3]);initial=setup(c,pc);expected,calls,snaps=caller_reference(initial,c,pc,guest.STACK+phase)
        for ws in(test.truth,test.raw):
            m=Caller(original,initial,pc,connected=code(ws,match.ENTRY));m.child=replace(c,output=guest.STACK+phase-12,selector=selector&255);m.child_snaps=[];m.run();test.assertEqual((guest.public(m.memory),m.calls,m.child_snaps),(guest.public(expected),calls,snaps))
        cases+=1
    windows=[]
    for pc,offset,n,end in((0x15141B4C,0x16EFFC,5,0x15141B60),(0x15141BAC,0x16F05C,8,0x15141BCC)):
        count=0;words=list(struct.unpack_from('>%dI'%n,test.rom,offset))
        for selector,phase,unused in itertools.product((0,3,6,255,0xAABBCC04),(0,8),(-32768,0,32767)):
            actual_unused=0 if pc==0x15141B4C else guest.u32(unused);c=guest.Case(selector=selector,phase=phase,mutation=5);p=parent.Case(selector=selector,phase=phase,unused=actual_unused,mutation=16);initial=setup(c,p);guest.put(initial,parent.TABLE+8*8,parent.ENTRY);guest.put(initial,0x60000+14,unused,2);expected,calls,snaps=caller_reference(initial,c,p,guest.STACK+phase)
            for ws in(test.truth,test.raw):
                connected=code(original,parent.ENTRY);connected.update(code(ws,match.ENTRY));connected[end]=0;m=Caller(words,initial,p,entry=pc,connected=connected);m.child=replace(c,output=guest.STACK+phase-12,selector=selector&255);m.child_snaps=[];m.r[18]=c.owner;m.r[19]=selector;m.r[16]=parent.TABLE;m.r[14]=parent.TABLE+8*8;m.r[2]=0x60000;m.r[12]=8;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with test.assertRaises(WindowBoundary):m.run()
                test.assertEqual((guest.public(m.memory),m.calls,m.child_snaps),(guest.public(expected),[(parent.ENTRY,(c.owner,selector,actual_unused)),*calls],snaps))
            count+=1
        windows.append(dict(entry=hex(pc),cases_per_body=count))
    before=test.prepared['predecessor_elf'].read_bytes();after=test.prepared['qualified_elf'].read_bytes();at=match.elf_slot_offset(before,0x8008A0F4,8);test.assertEqual(before[at:at+8],struct.pack('>II',parent.ENTRY,0xFFFFFFFF));test.assertEqual(before[at:at+8],after[at:at+8])
    return dict(cases_per_body=cases,all_byte_contexts_and_high_words=True,complete_54_word_caller=True,caller_baseline_exact=True,resource_zero_skip=True,dispatch_windows=windows,callback_registration_unchanged=True,caller_is_unrestricted=True)

def native_program():
    chosen=[]
    for selector,seed,mutation,output,connected in itertools.product((3,4,5,6),(0,1,7),(0,1,4,8),(guest.OUTPUT,guest.MATRICES+64),(False,True)):
        if connected and mutation:continue
        chosen.append(guest.Case(selector=selector,seed=seed,mutation=mutation,output=output,connected=connected))
    rows=[];arr=lambda a:'{'+','.join('0x%Xu'%guest.u32(v)for v in a)+'}'
    for c in chosen:
        initial=guest.fixture(c);after,calls,snaps,result,destination=guest.reference(initial,c);args=calls[0][1];matrix_words=[guest.read(after,guest.MATRICES+i*4)for i in range(512)];out=[guest.read(after,guest.OUTPUT+i*4)for i in range(3)];owner=[guest.read(after,c.owner+o)for o in(0x180,0x1D4)]
        rows.append('{'+','.join((str(c.selector),str(c.seed),str(c.mutation),str(int(c.output!=guest.OUTPUT)),str(int(c.connected)),arr(c.results),str(args[0]-guest.MATRICES),arr(args[1:4]),arr(out),arr(matrix_words),arr(owner)))+'}')
    text=match.HEADER+r'''
typedef struct {u8 prefix[0x1D4];u8 *matrix;} Owner;
typedef char layout[sizeof(void*)==4&&__builtin_offsetof(Owner,matrix)==0x1D4?1:-1];
typedef struct {u32 selector,seed,mutation,alias,connected,results[3],offset,inputs[3],output[3],matrices[512],owner[2];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static Owner owner;static f32 matrices[512],alternate[512],output[3];static const Row*current;static u32 calls,bad;
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 bytes(const u8*p){return(u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);}
static void setword(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(8*i));}
void func_150A7960(f32*m,f32 x,f32 y,f32 z,f32*ox,f32*oy,f32*oz){f32 a,b,c;
if(calls++||(u8*)m!=(u8*)matrices+current->offset||word(x)!=current->inputs[0]||word(y)!=current->inputs[1]||word(z)!=current->inputs[2]||ox==oy||ox==oz||oy==oz||word(*ox)!=word(x)||word(*oy)!=word(y)||word(*oz)!=word(z))bad=1;
if(current->connected){a=(m[0]*x+m[4]*y)+(m[8]*z+m[12]);b=(m[1]*x+m[5]*y)+(m[9]*z+m[13]);c=(m[2]*x+m[6]*y)+(m[10]*z+m[14]);*ox=a;*oy=b;*oz=c;return;}
*ox=real(current->results[0]);*oy=real(current->results[1]);*oz=real(current->results[2]);
if(current->mutation&1)owner.matrix=(u8*)alternate;
if(current->mutation&4){setword((u8*)ox,bytes((u8*)ox)^0x00400000U);setword((u8*)oy,bytes((u8*)oy)^0x80000000U);}
if(current->mutation&8)setword(owner.prefix+0x180,0xC0B00000U);
}
'''
    functions=dict(selected=match.SELECTED,**controls())
    for n,b in functions.items():text+=b.replace(match.FUNCTION,n,1)+'\n'
    text+=r'''
static int check(s32(*fn)(f32*,u8*,u8),const Row*r){u32 i,j,k,w;f32 v;current=r;calls=bad=0;
for(i=0;i<sizeof(owner.prefix);i++)owner.prefix[i]=(u8)(i*29+r->seed*17+90);setword(owner.prefix+0x180,0x41280000U);owner.matrix=(u8*)matrices;
for(j=0;j<32;j++)for(k=0;k<16;k++){v=(f32)((s32)((j*7+k*3+r->seed)%19)-9)*0.25f;if(k>=12&&k<=14)v=(f32)(j*4+(k-12)*3)-(f32)r->seed*0.125f;matrices[j*16+k]=v;alternate[j*16+k]=v;}
for(i=0;i<3;i++){u8 b[4];for(k=0;k<4;k++)b[k]=(u8)((16+i*4+k)*29+r->seed*17+90);output[i]=real(((u32)b[0]<<24)|((u32)b[1]<<16)|((u32)b[2]<<8)|b[3]);}
if(fn(r->alias?matrices+16:output,(u8*)&owner,(u8)r->selector)!=1)bad=1;
if(calls!=1||bytes(owner.prefix+0x180)!=r->owner[0]||owner.matrix!=(r->owner[1]==0x71000U?(u8*)alternate:(u8*)matrices))bad=1;
for(i=0;i<3;i++)if(word(output[i])!=r->output[i])bad=1;
for(i=0;i<512;i++){w=word(matrices[i]);if(w!=r->matrices[i])bad=1;}
for(i=0;i<sizeof(owner.prefix);i++)if(i<0x180||i>=0x184){if(owner.prefix[i]!=(u8)(i*29+r->seed*17+90))bad=1;}
return !bad;}
static int run(void){u32 i,j,killed['''+str(len(functions))+r''']={0};s32(*functions[])(f32*,u8*,u8)={'''+','.join(functions)+r'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i))killed[j]=1;}
for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
    return text,len(chosen)

if __name__=='__main__':unittest.main()
