"""Owner entry recycle: chain semantics, original caller, literal image and guarded schedule."""
from dataclasses import replace
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_owner_entry_recycle_match as source
from tools.tests import game_owner_entry_recycle_oracle as oracle
from tools.tests.game_owner_entry_recycle_oracle import Case,fixture,reference,public,RecycleOracle,put,read,faults,u32
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls(native=False):
    b=source.SELECTED
    rows=dict(head_not_unlinked=b.replace('*(s16 *)(owner + 0x44) = entry->next;','*(s16 *)(owner + 0x44) = index;'),
        previous_not_unlinked=b.replace('entries[previous].next = entry->next;','entries[previous].next = index;'),
        lost_free_chain=b.replace('entry->next = *(s16 *)(owner + 0x46);','entry->next = -1;'),
        wrong_free_head=b.replace('*(s16 *)(owner + 0x46) = index;','*(s16 *)(owner + 0x46) = previous;'),
        cleared_actor=b.replace('entry->next = *(s16 *)(owner + 0x46);','entry->actor = 0;\n        entry->next = *(s16 *)(owner + 0x46);'),
        skipped_head=b.replace('if (found) {','if (found && index != head) {'),
        skipped_nonhead=b.replace('if (found) {','if (found && index == head) {'),
        wrong_match=b.replace('entries[index].actor == actor','entries[index].actor != actor'),
        stopped_after_first=b.replace('index = entries[index].next;','index = -1;'))
    if not native:rows['cached_table']=b.replace('(s32)*(OwnerChainEntry150C1198 **)(owner + 0x40) + index * 8','(s32)entries + index * 8')
    return rows

def native_harness():
    t=source.HEADERS+r'''
typedef struct {u8 pad[0x40];OwnerChainEntry150C1198 *entries;s16 head,free;} Owner;
typedef struct {u8 pad[0xA8];Owner *owner;} Actor;
static Owner owner;static Actor actors[14];static OwnerChainEntry150C1198 entries[13],expected[13];
typedef char ABI[(sizeof(void*)==4&&sizeof(OwnerChainEntry150C1198)==8&&__builtin_offsetof(Owner,entries)==0x40&&__builtin_offsetof(Owner,head)==0x44&&__builtin_offsetof(Owner,free)==0x46&&__builtin_offsetof(Actor,owner)==0xA8)?1:-1];
'''
    for name,body in dict(selected=source.SELECTED,**controls(True)).items():t+=body.replace(source.FUNCTION,'test_'+name)+'\n'
    t+=r'''
typedef void(*Fn)(u8*);
static int check(Fn fn){s32 seed,n,hit,f,d,i,j,index,previous,eh,ef;static const s16 frees[]={-32768,-1,0,1,32767};
for(seed=0;seed<12;seed++)for(n=0;n<=12;n++)for(hit=-1;hit<n;hit++)for(f=0;f<5;f++)for(d=0;d<2;d++){
 for(i=0;i<14;i++)actors[i].owner=&owner;
 for(i=0;i<13;i++){entries[i].actor=&actors[i+1];entries[i].next=(s16)(1234+i);entries[i].unused=(s16)(5678+i);}
 for(i=0;i<n;i++){index=(i*5+seed)%13;entries[index].actor=(i==hit||(d&&hit>=0&&i>hit))?(void*)&actors[0]:(void*)&actors[i+1];entries[index].next=(i+1<n)?(s16)(((i+1)*5+seed)%13):-1;}
 owner.entries=entries;owner.head=n?(s16)seed:-1;owner.free=frees[f];eh=owner.head;ef=owner.free;
 for(i=0;i<13;i++)expected[i]=entries[i];
 /* Model selects the first matching logical list position, then edits indices. */
 j=-1;for(i=0;i<n;i++)if(entries[(i*5+seed)%13].actor==&actors[0]){j=i;break;}
 if(j>=0){index=(j*5+seed)%13;previous=((j-1)*5+seed)%13;if(j==0)eh=expected[index].next;else expected[previous].next=expected[index].next;expected[index].next=(s16)ef;ef=index;}
 fn((u8*)&actors[0]);if(owner.entries!=entries||owner.head!=eh||owner.free!=ef)return 1;
 for(i=0;i<13;i++)if(entries[i].actor!=expected[i].actor||entries[i].next!=expected[i].next||entries[i].unused!=expected[i].unused)return 2;
 for(i=0;i<14;i++)if(actors[i].owner!=&owner)return 3;
}return 0;}
static int run(void){if(check(test_selected))return 10;
'''
    for i,name in enumerate(controls(True)):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class OwnerEntryRecycleTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM))
        cls.words=list(struct.unpack('>47I',source.payload(cls.out/'qualified-padded.o')[0]))
        cls.raw=list(struct.unpack('>48I',source.payload(cls.out/'selected.o')[0]))
        cls.caller=list(struct.unpack_from('>19I',cls.rom,oracle.CALLER_ROM));cls.release=list(struct.unpack_from('>28I',cls.rom,oracle.RELEASE_ROM))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=None):
        initial=fixture(c);wanted=reference(initial,c);pair=[]
        for words in images or(self.truth,self.words):
            m=RecycleOracle(words,initial,c,entry=entry).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),[]),c);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
        if images is None:
            m=RecycleOracle(self.raw,initial,c,entry=entry).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),[]),c)
        return pair[0]
    def linked(self,obj,entry,label,normalize=False):
        text,functions,bindings=parse_object(obj);f=dict(functions[source.FUNCTION])
        if normalize:
            b,rs=source.normalized_payload(*source.payload(obj));self.assertFalse(rs);text=text[:f['value']]+b+text[f['value']+f['size']:];f['size']=len(b)
        assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,{});self.assertFalse(unknown)
        p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
    def test_01_owner_Make_census_and_closed_normalization(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),2);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),7)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),6)
        self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()))
        self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        self.assertEqual(self.rom[source.ROM+source.BODY:source.ROM+source.SIZE],bytes(12))
        self.assertFalse(source.BINDINGS);self.assertEqual(len(source.GUARDS),11);self.assertEqual(sum(g['omit']for g in source.GUARDS),1)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom)
        self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22E2C0])
        self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws))
        self.assertEqual(self.caller[10],0x0320F809)
        self.assertIn('void func_1516972C(struct102 *arg0)',self.values['conker/src/game_1944C0.c'].decode())
        at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],oracle.RELEASE,112)
        self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+112],self.rom[oracle.RELEASE_ROM:oracle.RELEASE_ROM+112])
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(body_words=47,compiler_words=48,slot_words=50,frame=0,bindings=0,guards=11,omitted_redundant_copy=1,neighbors=6,compact_functions=7,Make_commands=3,inherited_diagnostics=2,new_diagnostics=0,arguments=1,void_return=True,indirect_table_ROM='0x22E2C0')
    def test_02_chain_model_signed_links_aliases_and_raw_C(self):
        count=0;seen=set()
        for length,seed,free,duplicate,phase in itertools.product(range(9),(0,4,9),(-32768,-1,0,1,32767),(False,True),(0,8)):
            for hit in range(-1,length):
                m=self.compare(Case(length,hit,free,seed,duplicate,phase));seen.update(m.visits);count+=1
        for free,phase in itertools.product((-32768,-1,0,32767),(0,8)):
            for alias in(1,2):self.compare(Case(free=free,phase=phase,alias=alias));count+=1
            for hit in range(-1,4):self.compare(Case(hit=hit,free=free,phase=phase,sparse=True));count+=1
        expected=set(range(source.ENTRY,source.ENTRY+source.BODY,4))-{source.ENTRY+0x4C}
        self.assertEqual(seen,expected)
        self.receipt['guest']=dict(cases=count,visited_words=len(seen),unreachable_original_offset='0x4C',all_original_bytes_preserved=True,complete_normalized_state_trace_equal=True,raw_C_public_memory_equal=True,first_duplicate_only=True,actor_pointer_preserved=True,signed_sparse_indices_guest_only=True,overlapping_guest_headers=True,live_table_reload=True)
    def test_03_original_dispatch_window_and_release_helper(self):
        count=0;seen=set()
        for enabled,selector,kind,post,destructor,phase,hit in itertools.product((0,1),(-1,0,1),(0,1,2,255),(-1,0,2),(False,True),(0,8),(0,2,-1)):
            c=Case(hit=hit,enabled=enabled,selector=selector,kind=kind,post_kind=post,destructor=destructor,phase=phase)
            initial=fixture(c);wanted,calls=oracle.caller_reference(initial,c);pair=[]
            for target in(self.truth,self.words,self.raw):
                m=oracle.caller_machine(self.caller,target,self.release,initial,c).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c);pair.append(m);seen.update(m.visits)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);count+=1
        self.assertTrue(set(range(oracle.CALLER,oracle.CALLER+76,4))<=seen)
        self.assertTrue(set(range(oracle.RELEASE,oracle.RELEASE+112,4))<=seen)
        self.receipt['integration']=dict(cases=count,caller_window_words=19,release_helper_words=28,all_window_and_helper_words=True,actor_reloaded_after_callback=True,live_post_unlink_type=True,destructor_stride=52,other_callback_bounded=True,unlink_fallback_destructor_bounded=True,parent_C_still_placeholder=True,full_parent_or_teardown_claimed=False)
    def test_04_native32_defined_objects_three_optimizations(self):
        p=self.fresh/'native.c';p.write_text(native_harness());logs={}
        for opt in('-O0','-O2','-O3'):
            exe=self.fresh/('native'+opt);r=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            result=subprocess.run([str(exe)],capture_output=True);self.assertEqual(result.returncode,0,(opt,result.stderr));logs[opt]=dict(exit=0,diagnostics=r.stderr)
        self.receipt['native']=dict(optimizations=logs,cases_per_optimization=10920,controls=len(controls(True)),SDK=True,pointers32=True,layout_assertions=True,trapping_UBSan=True,defined_nonnegative_indices=True,guest_header_aliases_excluded=True)
    def test_05_access_fault_prefixes_and_nonterminating_cycle(self):
        total=0;delay=0
        for c in(Case(length=0,hit=-1),Case(hit=-1),Case(hit=0),Case(hit=2),Case(alias=1),Case(alias=2)):
            initial=fixture(c);full=RecycleOracle(self.truth,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=RecycleOracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace)
                self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(pair[1].current_pc,pair[1].delay_of,cut));total+=1;delay+=pair[0].delay_of is not None
        connected=0
        for c in(Case(hit=2,post_kind=255,destructor=True),Case(hit=0),Case(selector=-1),Case(enabled=0)):
            initial=fixture(c);full=oracle.caller_machine(self.caller,self.truth,self.release,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=oracle.caller_machine(self.caller,words,self.release,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);connected+=1
        c=Case(hit=-1);initial=fixture(c);_,_,table=oracle.addresses(c);chain=oracle.indices(c);put(initial,table+chain[-1]*8+4,chain[0],2)
        with self.assertRaises(ValueError):reference(initial,c)
        for cut in(40,80,160):
            pair=[]
            for words in(self.truth,self.words):
                m=RecycleOracle(words,initial,c);m.cut=cut
                with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(public(m.memory),public(initial));pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]))
        self.receipt['faults']=dict(direct_prefixes=total,connected_prefixes=connected,delay_slot_cuts=delay,cycle_prefixes=3,cycles_not_claimed_terminating=True,normalized_complete_state_PC_trace_equal=True)
    def test_06_padder_guards_omission_rebases(self):
        raw,rs=source.payload(self.out/'selected.o');rejects=0
        for at in source.NEW_GUARDS:
            damaged=raw[:at+3]+bytes([raw[at+3]^1])+raw[at+4:]
            with self.assertRaises(ValueError):source.normalized_payload(damaged,rs)
            rejects+=1
        for damaged,b in((raw[:-4],rs),(raw,{0:[('R_MIPS_32','wrong')]})):
            with self.assertRaises(ValueError):source.normalized_payload(damaged,b)
            rejects+=1
        rows=list(csv.DictReader(io.StringIO(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']).decode())))
        for which in range(11):
            changed=[dict(r)for r in rows];new=[r for r in changed if r['function']==source.FUNCTION];new[which]['expected']=hex(int(new[which]['expected'],0)^1)
            out=io.StringIO();writer=csv.DictWriter(out,list(rows[0]));writer.writeheader();writer.writerows(changed);p=self.fresh/('bad-guard-%d.csv'%which);p.write_text(out.getvalue())
            with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=p)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'))
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
        self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        cases=0
        for j,(entry,delta)in enumerate(((source.ENTRY,0),(0x17007FFC,0x10000),(0x2500FFFC,0x20000))):
            paths=(self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_EDE60.c.o',self.out/'selected.o')
            images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),normalize=k==2)for k,p in enumerate(paths)]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2]);unmodified=self.linked(paths[2],entry,'raw-rebase-%d'%j)
            for length,hit,free,phase in itertools.product((0,4,8),(-1,0,2,7),(-32768,-1,32767),(0,8)):
                c=Case(length=length,hit=hit,free=free,phase=phase,delta=delta);self.compare(c,images,entry);initial=fixture(c);m=RecycleOracle(unmodified,initial,c,entry=entry).run();self.assertEqual(public(m.memory),public(reference(initial,c)));cases+=1
        self.receipt['rebases']=dict(layouts=3,cases=cases,raw_rejections=rejects,padder_expected_word_rejections=11,all_three_objects_linked=True,no_external_bindings=True,omission_branch_targets_derived=True,original_and_Make_exact=True,raw_C_public_equal=True)
    def test_07_effective_IDO_semantic_controls(self):
        witnesses=[Case(hit=hit,free=free)for hit,free in itertools.product((-1,0,1,2,3),(-1,0,32767))]+[Case(alias=1)]
        evidence={}
        for name,body in controls().items():
            self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag)
            words=self.linked(obj,source.ENTRY,'negative-link-'+name);effective=False
            for c in witnesses:
                initial=fixture(c);m=RecycleOracle(words,initial,c).run()
                if public(m.memory)!=public(reference(initial,c)):effective=True;evidence[name]=dict(hit=c.hit,free=c.free,alias=c.alias);break
            self.assertTrue(effective,name)
        self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,live_reload_alias_effective=True)
    def test_08_strict_entire_image_and_frozen_inputs(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth)
        source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)}
        positions=[20,at,at+source.BODY,at+source.SIZE,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.RELEASE,112),0x2A0D94,0x2B03D4,0x2CF644,0x2E7160,0x30D508]
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),134)
        self.receipt['image']=dict(changed_bytes=134,code_bytes=133,extent_bytes=1,exclusions=0,corruptions=len(positions)+1,inherited_guard_prefix_unchanged=True,new_guards=11,protected_Game_bytes=189088,focused_inputs=len(v),caller_provider_and_all_other_bodies_unchanged=True)
