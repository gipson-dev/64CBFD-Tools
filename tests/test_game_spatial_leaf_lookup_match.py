"""Direct leaf lookup, inclusive wrapping bounds, caller ABI and whole image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_spatial_leaf_lookup_candidates as candidate
from tools.experiments import game_spatial_leaf_lookup_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_spatial_leaf_lookup_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses

class SpatialLeafLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>68I',cls.rom,match.ROM));cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalSpatialLeaf',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-spatial-leaf',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.raw==cls.words

    def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def contract(self,words,c,initial=None,s=None,entry=match.ENTRY):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s)if initial is None else initial
        m=model.Oracle(words,initial,c,s,entry).run();self.assertEqual(m.r[2],model.reference(initial,c,s),c);self.assertEqual(m.memory,initial);self.assertFalse(m.calls)
        return m

    def compare(self,c,initial=None,s=None,images=None,entry=match.ENTRY):
        images=(self.retail,self.raw,self.words)if images is None else images
        ms=[self.contract(words,c,initial,s,entry)for words in images]
        for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
        return ms

    def test_01_direct_words_owners_prototypes_and_corruption(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['neighbors']),(68,0,0,2,13))
        self.assertEqual(q['raw_neighbors'],13);self.assertEqual(len(q['caller_profiles']),13);self.assertEqual(sum(p['unchanged_functions']for p in q['caller_profiles']),217)
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+272]
        for at in range(272):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        self.receipt('owner-contract',dict(words=68,guards=0,bindings=2,neighbors=13,other_caller_owners=13,caller_function_comparisons=217,raw_corruptions=272,binding_corruptions=2))

    def test_02_relative_graphs_all_boundaries_and_word_wrapping(self):
        count=0;visited=set()
        for c in model.cases():
            ms=self.compare(c);visited.update(ms[0].visits);count+=1
        self.assertEqual(visited,set(range(match.ENTRY,match.ENTRY+272,4))-{match.ENTRY+o for o in(0x74,0x90,0xE4,0xF8)})
        self.receipt('guest-contract',dict(cases_per_body=count,bodies=3,reachable_words=64,unreachable_literal_offsets=['0x74','0x90','0xE4','0xF8'],plans=8,all_word_wrap_extremes=True,inclusive_bounds=True,signed_children_and_siblings=True))

    def test_03_read_only_aliases_short_circuits_and_fault_prefixes(self):
        aliases=cuts=0
        for offset in(0,4,8,12):
            s={'D_800DBE48':model.ROOT+offset};c=model.Case(x=0 if offset==4 else 1000,z=0 if offset==4 else 1000)
            images=tuple(model.bound(obj,s)for obj in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner']))
            self.compare(c,s=s,images=images);aliases+=1
        for c in(model.Case(plan=1,x=1000),model.Case(plan=2,x=1000)):
            initial=model.fixture(c)
            for at in(model.ROOT+10,model.ROOT+11):del initial[at]
            if c.plan==2:
                for at in range(model.ROOT+32,model.ROOT+46):initial.pop(at,None)
            self.compare(c,initial)
        c=model.Case(plan=0);initial={};model.put(initial,model.symbols()['D_800DBE48'],0);self.compare(c,initial)
        for c in(model.Case(plan=0),model.Case(),model.Case(plan=2),model.Case(plan=3),model.Case(plan=5,x=20,z=20),model.Case(plan=7,x=1000),model.Case(x=0x80000000,z=0)):
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.words):
                    m=model.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(state(ms[0]),state(ms[2]));cuts+=1
        self.receipt('aliases-faults',dict(read_only_aliases=aliases,fired_access_prefixes=cuts,unmapped_z_and_unfollowed_child=True,null_root_needs_only_pointer=True,three_complete_fault_states_equal=True))

    def test_04_all_original_call_boundaries(self):
        rows=json.loads((self.out/'call-census.json').read_text());self.assertEqual(match.census(ROOT),[r['rom']for r in rows]);count=0;delays=set()
        for row,c in itertools.product(rows,(model.Case(),model.Case(plan=0),model.Case(plan=3),model.Case(x=0x80000000,z=0))):
            pc=row['address'];body=list(struct.unpack_from('>2I',self.rom,row['rom']));delay=body[1];delays.add(hex(delay));ms=[]
            for target in(self.retail,self.raw,self.words):
                initial=model.fixture(c);initial.update({model.STACK+i:(i*17+165)&255 for i in range(128,2048)})
                code=dict(zip(range(match.ENTRY,match.ENTRY+272,4),target));m=model.Oracle(body,initial,c,entry=pc,connected=code)
                op,rs,rt=delay>>26,delay>>21&31,delay>>16&31;imm=model.half(delay)
                if op in(32,33,35,36,37):
                    m.r[rs]=0x90000;width={32:1,33:2,35:4,36:1,37:2}[op];model.put(m.memory,model.u32(0x90000+imm),c.x if rt==4 else c.z,width)
                elif op in(40,41,43,57)and rs!=29:
                    m.r[rs]=0x90000
                if op in(40,41,43,57):
                    width=1 if op==40 else 2 if op==41 else 4
                    for k in range(width):m.memory[model.u32(m.r[rs]+imm+k)]=0xA5
                before=dict(m.memory);m.code[pc+8]=0;m.code=WindowCode(m.code,m);m.code.ends=(pc+8,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(len(m.calls),1);self.assertEqual(m.calls[0][0],match.ENTRY)
                effective=replace(c,x=m.calls[0][1][0],z=m.calls[0][1][1])
                for access in m.trace:
                    if access[0]=='W':_,p,n,value=access;model.put(before,p,value,n)
                self.assertEqual(m.r[2],model.reference(before,effective));self.assertEqual(m.memory,before);ms.append(m)
            self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(state(ms[0]),state(ms[2]));count+=1
        self.receipt('callers',dict(original_sites=26,owners=14,cases_per_body=count,delay_words=sorted(delays),full_parent_functions_claimed=False))

    def test_05_independent_GNU_rebases_and_carry_edges(self):
        links=count=0
        for index,(entry,table)in enumerate(((match.ENTRY,0x80107FFC),(0x18018000,0x80208000),(0x1A02FFFC,0x8030FFFC))):
            s={'D_800DBE48':table};images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>68I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for c in(model.Case(plan=p,x=x,z=0)for p,x in itertools.product(range(8),(0,10,11,0x80000000))):
                self.compare(c,s=s,images=images,entry=entry);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,both_pointer_carry_edges=True))

    def test_06_native_full_word_domains_and_effective_IDO_controls(self):
        controls=model.controls();witnesses=list(model.cases())
        for name,body in controls.items():
            source=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1)
            obj,diag=candidate.compile_owner(ROOT,self.out,source,'negative-'+name);self.assertFalse(diag);words=model.bound(obj,model.symbols());effective=False
            for c in witnesses:
                initial=model.fixture(c);expected=model.reference(initial,c)
                try:m=model.Oracle(words,initial,c).run()
                except (KeyError,AssertionError):effective=True;break
                if m.r[2]!=expected:effective=True;break
            self.assertTrue(effective,name)
        native_controls={n:b for n,b in controls.items()if n not in('unsigned_child','unsigned_next')}
        for label,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in native_controls.items()]:
            p=self.out/('native-'+label+'.c');p.write_text(native_source(body));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),label);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,label)
        self.receipt('native-controls',dict(profiles=['O0','O2','O3'],positive_executions=12960,full_word_wrapping_defined=True,UBSan=True,native_controls=len(native_controls),IDO_controls=len(controls),invalid_native_offset_mutants_guest_only=True))

    def test_07_literal_whole_image_corruptions(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+272]
        self.assertEqual(match.strict_image(before,after,truth),189);at=match.elf_slot_offset(after,match.ENTRY,272)
        offsets=(0,at,at+271,at+272,match.elf_slot_offset(after,0x800841C0,4),len(after)-1)
        for off in offsets:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        self.receipt('strict-controls',dict(literal_ELF_changed_bytes=189,named_serialization_changes=0,corruption_controls=len(offsets),exclusions=0))

def native_source(body):
    rows=[]
    for c in model.cases():
        initial=model.fixture(c);answer=model.reference(initial,c);n=model.nodes(c)
        nodes=['{%d,%d,%d,%d,%d,%d}'%(p-model.BASE,v.next,v.radius,v.x,v.z,v.child)for p,v in n.items()]
        nodes+=['{0,0,0,0,0,0}']*(4-len(nodes))
        rows.append('{0x%Xu,0x%Xu,%d,%d,%d,{%s}}'%(model.u32(c.x),model.u32(c.z),len(n),64 if n else -1,answer-model.BASE if answer else -1,','.join(nodes)))
    return '#include <ultra64.h>\nextern u8 *D_800DBE48;\n'+body+'\nu8 *D_800DBE48;\n'+r'''
typedef struct {int at; s16 next;u16 radius;s16 x,z,child;} NodeFixture;
typedef struct {u32 x,z;int count,root,expected;NodeFixture n[4];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static u8 storage[160] __attribute__((aligned(16)));
static int run(void){
 for(unsigned i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  const Row *r=&rows[i];for(int k=0;k<160;k++)storage[k]=0xA5;
  for(int k=0;k<r->count;k++){const NodeFixture *n=&r->n[k];u8 *p=storage+n->at;
   *(s16 *)(p+4)=n->next;*(u16 *)(p+6)=n->radius;*(s16 *)(p+8)=n->x;*(s16 *)(p+10)=n->z;*(s16 *)(p+12)=n->child;
  }
  u8 before[160];for(int k=0;k<160;k++)before[k]=storage[k];
  D_800DBE48=r->root<0?0:storage+r->root;u8 *old=D_800DBE48;
  u8 *(*typed)(s32,s32)=func_1510FD20;u8 *answer=typed((s32)r->x,(s32)r->z);
  if(answer!=(r->expected<0?0:storage+r->expected)||D_800DBE48!=old)return 1;
  for(int k=0;k<160;k++)if(storage[k]!=before[k])return 1;
 }
 return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
