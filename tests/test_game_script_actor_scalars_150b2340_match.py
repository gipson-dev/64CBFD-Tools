"""Direct actor scalars: whole owner, variadic dispatch and native32 ABI."""
import itertools,json,re,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_script_actor_scalars_150b2340_match as match
from tools.tests import game_script_actor_scalars_150b2340_oracle as guest
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=match.ROOT

def controls():
    b=match.SELECTED
    pairs={
        'flags_addition':('| 0x2000','+ 0x2000'),
        'wrong_first_key':('0x2007, 0xB7','0x2007, 0xB8'),
        'wrong_second_key':('0x2000, 0xBC','0x2000, 0xBD'),
        'wrong_blocker_key':('0x2000, 0xBB','0x2000, 0xBA'),
        'primary_one_only':('func_1509BE40(0, 0x5043, 0x1A) != 0','func_1509BE40(0, 0x5043, 0x1A) == 1'),
        'secondary_one_only':('func_1509BE40(0, 0x5045, 0x1A) != 0','func_1509BE40(0, 0x5045, 0x1A) == 1'),
        'fallback_one_only':('func_1509BE40(1, 0x4030, 6, 0x2000) != 0','func_1509BE40(1, 0x4030, 6, 0x2000) == 1'),
        'wrong_extra_count':('func_1509BE40(1, 0x4030','func_1509BE40(0, 0x4030'),
        'wrong_extra_value':('0x4030, 6, 0x2000','0x4030, 6, 0x4000'),
        'wrong_optional_flag':('unk84 |= 0x4000;','unk84 |= 0x8000;'),
        'wrong_common_flag':('unk84 |= 0x400000;','unk84 |= 0x800000;'),
        'overwrite_flags':('unk84 |= 0x400000;','unk84 = 0x400000;'),
        'negative_zero':('unk190 = 0.0f','unk190 = -0.0f'),
        'wrong_235':('235.0f','234.0f'),
        'wrong_114':('114.0f','113.0f'),
        'wrong_384':('384.0f','383.0f'),
        'wrong_60':('60.0f','61.0f'),
        'wrong_scalar_field':('unk190 = 60.0f','unk194 = 60.0f'),
        'positive_enabled':('enabled != 0','enabled > 0'),
        'wrong_blocker_sentinel':('blocker != -1','blocker != 0'),
        'condition_or':('enabled != 0 && blocker != -1','enabled != 0 || blocker != -1'),
        'wrong_set_bit':('unk5F0 |= 0x100','unk5F0 |= 0x200'),
        'missing_clear':('unk5F0 &= ~0x100','unk5F0 |= 0x100'),
    }
    rows={n:b.replace(a,z)for n,(a,z)in pairs.items()};assert all(v!=b for v in rows.values());return rows

def linked(obj,entry,label,out,helper=guest.HELPER):
    text,fs,refs=parse_object(obj);f=fs[match.FUNCTION];assembly,unknown=emit_function(text,f,refs,match.FUNCTION,{'func_1509BE40':helper});assert not unknown;p=out/label
    p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,'--defsym=func_1509BE40=0x%X'%helper,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
    return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

def negative_linked(obj,label,out):
    # Incorrect constants may require real IDO literal pools. Link the original
    # object and preserve those read-only bytes rather than inventing values.
    _,fs,_=parse_object(obj);assert set(fs)=={match.FUNCTION};f=fs[match.FUNCTION];assert f['value']==0
    p=out/label;p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x600000 : { *(.rodata*) *(.rdata*) *(.lit4*) *(.lit8*) } }\n'%match.ENTRY)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,'--defsym=func_1509BE40=0x%X'%guest.HELPER,'-o',str(p.with_suffix('.elf')),str(obj)],check=True,capture_output=True)
    image=sections(p.with_suffix('.elf'));words=list(struct.unpack_from('>%dI'%(f['size']//4),image['.text'][1]));memory={}
    for name,(address,data)in image.items():
        if name=='.rodata':memory.update({address+i:v for i,v in enumerate(data)})
    return words,memory

def code(words,entry):return dict(zip(range(entry,entry+4*len(words),4),words))
def observed(m):return guest.public(m.memory),m.calls,m.snapshots,m.nested,m.packet_snaps
def state(m):return m.r,m.f,m.hi,m.lo,m.memory,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word

class ActorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>79I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);assert cls.raw==cls.truth
        cls.actual,_,_=match.load_elf_functions(str(ROOT/match.ELF),'mips-linux-gnu-objdump')
    def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def test_01_owner_Make_image_and_corruption_guards(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['slot_words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(79,80,40,0,4,4,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['caller']['functions'],q['caller']['actual_Make']['commands']),(5,5,1,3));self.assertEqual(q['exclusions'],0)
        raw,refs=match.payload(self.out/'qualified-owner.o')
        for i in range(316):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[(refs[at][0][0],'wrong')]
            with self.assertRaises(ValueError):match.checked(raw,bad)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+320]
        for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,320)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        bad=bytearray(truth);bad[-1]^=1
        with self.assertRaises(ValueError):match.strict_image(before,after,bytes(bad))
    def test_02_independent_actor_bytes_and_live_providers(self):
        visited=set();count=accesses=0
        for c in guest.cases():
            initial=guest.fixture(c);expected=guest.reference(initial,c);pair=[]
            for ws in(self.truth,self.raw):
                m=guest.Oracle(ws,initial,c).run();self.assertEqual(observed(m),expected,c);pair.append(m);visited.update(m.visits)
            self.assertEqual(state(pair[0]),state(pair[1]));count+=1;accesses+=len(pair[0].trace)
        self.assertEqual((count,len(visited)),(512,78));self.receipt('guest-contract',dict(cases_per_body=count,visited_body_words=len(visited),accesses_per_body=accesses,all_2464_actor_bytes=True,every_provider_snapshot=True,raw_full_literal_state_equal=True,unreachable_retail_word=70))
    def test_03_GNU_rebases_aliases_and_fault_prefixes(self):
        selected=[guest.Case(),guest.Case(results=(0x2000,0,0xFFFFFFFF,0,0),mutation=7),guest.Case(results=(0x80002005,0xFFFFFFFF,0,0,0xFFFFFFFF),mutation=1),guest.Case(results=(0xFFFFFFFF,1,0x80000000,0x80000000,0),mutation=2)]
        total=0
        for i in range(6):
            entry=match.ENTRY+i*0x10000;helper=guest.HELPER+i*0x20000;ws=linked(self.out/'qualified-owner.o',entry,'rebase-'+str(i),self.out,helper)
            for c in selected:
                initial=guest.fixture(c);m=guest.Oracle(ws,initial,c,entry,helper).run();expected=list(guest.reference(initial,c));expected[1]=[(helper,a)for t,a in expected[1]];self.assertEqual(observed(m),tuple(expected));total+=1
        aliases=[]
        for actor in(0,0x80000000,0xFFFFFF80,guest.PACKET-0x84,guest.COUNT-0x5F0):
            for c in selected:
                c=replace(c,actor=actor);initial=guest.fixture(c);m=guest.Oracle(self.raw,initial,c).run();self.assertEqual(observed(m),guest.reference(initial,c));aliases.append(actor)
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
        self.receipt('rebases-aliases-faults',dict(GNU_links=6,rebase_cases_per_body=total,guest_alias_cases_per_body=len(aliases),fired_fault_pairs=fired,delay_slot_cuts=delay,portable_C_alias_or_fault_claim=False))
    def test_04_complete_indirect_caller_and_table(self):
        self.receipt('callers',caller_checks(self))
    def test_05_original_variadic_helper_and_packet(self):
        self.receipt('connections',connection_checks(self))
    def test_06_compiled_semantic_negative_controls(self):
        rows={};cases=list(guest.cases())
        for n,fragment in controls().items():
            obj,diag=match.compile_owner(ROOT,self.out,match.HEADER+fragment,'negative-'+n);self.assertFalse(diag);ws,pools=negative_linked(obj,'negative-link-'+n,self.out);witness=None
            for c in cases:
                initial=guest.fixture(c);initial.update(pools);m=guest.Oracle(ws,initial,c).run()
                if observed(m)!=guest.reference(initial,c):witness=c;break
            self.assertIsNotNone(witness,n);rows[n]=dict(compiled=True,public_counterexample=vars(witness),literal_pool_bytes=len(pools))
        self.receipt('compiled-controls',rows)
    def test_07_native32_layout_full_actor_and_call_interfaces(self):
        text,n=native_program();p=self.out/'native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
        self.receipt('native-contract',dict(cases_per_profile=n,entry_forms=['typed','legacy_unprototyped_callback'],profiles=['O0','O2','O3'],compiled_controls=len(controls()),all_controls_effective=True,struct108_size=2464,field_offsets=list(guest.OFFSETS),all_actor_bytes_and_provider_snapshots=True,actual_variadic_argument_reads=True,UBSan_traps=True,artificial_global_aliases_excluded=True))

def caller_checks(test):
    entry=0x15130230;truth=list(struct.unpack_from('>20I',test.rom,0x15D6E0));actual=test.actual['func_15130230'];calls=0
    class Caller(guest.Oracle):
        def record_call(self,t):
            if t==match.ENTRY:self.entries.append(tuple(map(guest.u32,self.arguments(1))))
            else:super().record_call(t)
    for path,index,phase,unused in itertools.product(range(4),(0,21),(0,8),(0,0x87654321)):
        c=guest.Case(results=(5,0xFFFFFFFF,0,1 if path<2 else 0,0 if path%2==0 else 0xFFFFFFFF),mutation=7,phase=phase,seed=path);initial=guest.fixture(c);guest.put(initial,0x800B0DF0,0x70000);guest.put(initial,0x7000F,index,1);guest.put(initial,0x80089670+21*4,match.ENTRY)
        expected=guest.reference(initial,c)if index else(guest.public(initial),[],[],[],[])
        for caller in(truth,actual):
            for ws in(test.truth,test.raw):
                m=Caller(caller,initial,c,entry=entry,connected=code(ws,match.ENTRY),arguments=(c.actor,unused));m.entries=[];m.run();test.assertEqual(observed(m),expected);test.assertEqual(m.entries,[(c.actor,)]if index else[])
        calls+=1
    text=(ROOT/'conker/asm/data/22E0F0.rodata.s').read_text();part=text.split('dlabel D_80089670\n',1)[1].split('enddlabel D_80089670',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',part);start=int(rows[0][0],16);va=int(rows[0][1],16);blob=struct.pack('>%dI'%len(rows),*(int(w,16)for a,v,w in rows));test.assertEqual(test.rom[start:start+len(blob)],blob);elf=test.prepared['qualified_elf'].read_bytes();off=match.elf_slot_offset(elf,va,len(blob));test.assertEqual(elf[off:off+len(blob)],blob);test.assertEqual(struct.unpack_from('>I',blob,21*4)[0],match.ENTRY)
    return dict(cases_per_body=calls,retail_and_actual_caller_executed=True,caller_baseline_exact=actual==truth,callback_index=21,zero_selector_skip=True,table_entries=len(rows),entire_callback_table_unchanged=True,integer_address_interface=True)

def connection_checks(test):
    helper=list(struct.unpack_from('>92I',test.rom,0xC92F0));connected=code(helper,guest.HELPER);cases=0;visited=set()
    for path,enabled,blocker,mutation,phase in itertools.product(range(4),(0,0xFFFFFFFF),(0,0xFFFFFFFF),(0,7),(0,8)):
        c=guest.Case(results=((0,0x2000,0x80002005,0xFFFFFFFF)[path],enabled,blocker,1 if path<2 else 0,0 if path%2==0 else 0xFFFFFFFF),mutation=mutation,phase=phase,seed=path);initial=guest.fixture(c);expected=guest.reference(initial,c,True)
        for ws in(test.truth,test.raw):
            m=guest.Oracle(ws,initial,c,connected=connected).run();test.assertEqual(observed(m),expected);visited.update(m.visits)
        cases+=1
    table=test.rom[0x22CF58:0x22CF58+60];test.assertEqual(struct.unpack('>15I',table),guest.CALLBACKS)
    test.assertNotEqual(test.actual['func_1509BE40'],helper)
    return dict(cases_per_body=cases,helper_slot_words=92,helper_visited_words=sum(guest.HELPER<=a<guest.HELPER+368 for a in visited),extra_counts=[0,1],full_shared_packet_and_count=True,previous_count_restored=True,original_dispatch_table_exact=True,callbacks_bounded=True,helper_baseline_exact=False,helper_not_credited=True)

def native_program():
    chosen=[c for c in guest.cases()if not c.phase];rows=[]
    arr=lambda a:'{'+','.join('0x%Xu'%guest.u32(v)for v in a)+'}'
    def words(blob):return tuple(struct.unpack_from('>I',blob,o)[0]for o in guest.OFFSETS)+(blob[0x100],blob[-1])
    for c in chosen:
        initial=guest.fixture(c);after,calls,snapshots,_,_=guest.reference(initial,c);before=guest.observation(initial,c);result=guest.observation(after,c);args=[v for t,a in calls for v in(a+(0,)*(4-len(a)))];snaps=[v for s in snapshots for v in words(s)]
        rows.append('{'+','.join((str(c.seed),str(c.mutation),arr(c.results),arr(before),arr(result),arr(args),arr(snaps)))+'}')
    text=match.HEADER+r'''
typedef char pointer32[sizeof(void*)==4?1:-1];typedef char actor_size[sizeof(struct108)==0x9A0?1:-1];
typedef char offsets[(__builtin_offsetof(struct108,unk84)==0x84&&__builtin_offsetof(struct108,unk190)==0x190&&__builtin_offsetof(struct108,unk348)==0x348&&__builtin_offsetof(struct108,unk34C)==0x34C&&__builtin_offsetof(struct108,unk374)==0x374&&__builtin_offsetof(struct108,unk5F0)==0x5F0)?1:-1];
typedef struct {u32 seed,mutation,results[5],before[8],after[8],args[20],snapshots[40];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static struct108 actor;static const Row*current;static u32 calls,bad;
static const u32 offsets_words[]={0x84,0x190,0x348,0x34C,0x374,0x5F0};
static u8 expected(const u32 *words,u32 i){u32 j;for(j=0;j<6;j++)if(offsets_words[j]<=i&&i<offsets_words[j]+4)return(u8)(words[j]>>(8*(i-offsets_words[j])));if(i==0x100)return(u8)words[6];if(i==0x99F)return(u8)words[7];return(u8)(i*29+current->seed*17+90);}
static int equal(const u32*p){u32 i;for(i=0;i<sizeof(actor);i++)if(((u8*)&actor)[i]!=expected(p,i))return 0;return 1;}
static void word(u32 o,u32 v){u32 i;for(i=0;i<4;i++)((u8*)&actor)[o+i]=(u8)(v>>(8*i));}
s32 func_1509BE40(s32 count,...){__builtin_va_list ap;u32 stage=calls,flags,key,extra=0,i;
__builtin_va_start(ap,count);flags=(u32)__builtin_va_arg(ap,s32);key=(u32)__builtin_va_arg(ap,s32);if(count==1)extra=(u32)__builtin_va_arg(ap,s32);__builtin_va_end(ap);
if(stage>=5){bad=1;return 0;}if((u32)count!=current->args[stage*4]||flags!=current->args[stage*4+1]||key!=current->args[stage*4+2]||extra!=current->args[stage*4+3]||!equal(current->snapshots+stage*8))bad=1;calls++;
if(current->mutation&1){word(0x84,0x12340000U^(stage*0x01000100U)^current->seed);word(0x5F0,0x80000000U^(stage*0x00000101U)^current->seed);}
if(current->mutation&2){((u8*)&actor)[0x100]=(u8)(current->seed+stage*17);((u8*)&actor)[0x99F]=(u8)(current->seed^stage);}
if(current->mutation&4)for(i=0;i<4;i++)word(offsets_words[i+1],0xFFC01234U^(stage*0x100+i));return(s32)current->results[stage];}
'''
    functions=dict(selected=match.SELECTED,**controls())
    for n,b in functions.items():text+=b.replace(match.FUNCTION,n,1)+'\n'
    text+=r'''
static void(*legacy[])()={[21]=selected};
static int check(void(*fn)(s32),const Row*r,u32 old){u32 i;current=r;calls=bad=0;for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=expected(r->before,i);
if(old)legacy[21]((s32)&actor);else fn((s32)&actor);return !bad&&calls==5&&equal(r->after);}
static int run(void){u32 i,j,killed['''+str(len(functions))+r''']={0};void(*functions[])(s32)={'''+','.join(functions)+r'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i,0)||!check(functions[0],rows+i,1))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i,0))killed[j]=1;}
for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
    return text,len(chosen)

if __name__=='__main__':unittest.main()
