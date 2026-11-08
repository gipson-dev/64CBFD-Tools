"""Semantic study only: the 337-word/frame128 source is not a retail match."""
import hashlib,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_oriented_strip_1513fab4_candidates as c
from tools.tests import game_oriented_strip_1513fab4_oracle as g
from tools.tests import game_oriented_strip_1513fab4_native as native
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_projected_packet_draw import native_command

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def reachable_words(words):
    """Overapproximate control-flow reachability, including likely annulment."""
    todo=[0];processed=set();reached=set()
    def add(i):
        if 0<=i<len(words):todo.append(i)
    while todo:
        i=todo.pop()
        if i in processed:continue
        processed.add(i);reached.add(i);w=words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;imm=((w&65535)^32768)-32768
        cop=op==17 and rs==8
        if op in(1,4,5,6,7,20,21,22,23)or cop:
            take=not(op in(5,21)and rs==rt);skip=not(op in(4,20)and rs==rt)
            likely=op in(20,21,22,23)or(cop and rt&2)
            if take:reached.add(i+1);add(i+1+imm)
            if skip:
                if not likely:reached.add(i+1)
                add(i+2)
        elif op==3:reached.add(i+1);add(i+2)
        elif op==0 and w&63==8:
            if rs!=31:raise ValueError('Foreign register return')
            reached.add(i+1)
        elif op==2:
            target=((w&0x3FFFFFF)<<2)|(c.ENTRY&0xF0000000);reached.add(i+1);add((target-c.ENTRY)//4)
        else:add(i+1)
    return reached

class OrientedStripStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.receipts={}
        names=[c.SOURCE,'conker/include/functions.h','conker/include/variables.h','conker/include/structs.h','conker/Makefile','conker/retail_word_patches.us.csv','conker/build/src/game_169510.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin','conker/conker.us.bin','conker/progress.csv','graphify-out/graph.json']
        cls.protected={n:sha(cls.root/n)for n in names}
        cls.before,cls.proposed,installed=c.source_states((cls.root/c.SOURCE).read_text(encoding='utf-8'));assert not installed,'This suite does not authorize adoption'
        cls.old,cls.old_diag=c.compile_owner(cls.root,cls.out,cls.before,'study-predecessor')
        cls.new,cls.new_diag=c.compile_owner(cls.root,cls.out,cls.proposed,'study-candidate')
        cls.text,cls.functions,cls.relocations=parse_object(cls.new);f=cls.functions[c.FUNCTION];cls.raw=cls.text[f['value']:f['value']+f['size']];cls.refs={p-f['value']:v for p,v in cls.relocations.items()if f['value']<=p<f['value']+f['size']}
        cls.words=bound_blob(cls.raw,cls.refs,g.symbols());cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.elf=(cls.root/'conker/build/conker.us.elf').read_bytes();cls.truth=list(struct.unpack_from('>336I',cls.rom,c.ROM))
    @classmethod
    def tearDownClass(cls):
        assert cls.protected=={n:sha(cls.root/n)for n in cls.protected},'Research changed protected production inputs'
        cls.receipts.update(source_installed=False,matching_credit=0,adoption_ready=False,production_unchanged=True,protected_input_sha256=cls.protected,original_caller_execution_qualified=False,stack_output_aliases_qualified=False,normalization_qualified=False)
        (cls.out/'study-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def test_01_complete_owner_and_explicit_nonmatch_boundary(self):
        self.assertEqual(same_functions(self.old,self.new,(c.FUNCTION,)),58);self.assertEqual(alloc_pools(self.old),alloc_pools(self.new))
        before,after=diagnostic_rows(self.old_diag),diagnostic_rows(self.new_diag);self.assertFalse(after-before);self.assertEqual((sum(before.values()),sum(after.values()),sum((before-after).values())),(43,39,4))
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),c.RAW_SHA256);self.assertEqual((len(self.words),(-self.words[0])&65535),(337,128));self.assertNotEqual(self.words,self.truth)
        expected={48:[('R_MIPS_26','func_151D5D60')],104:[('R_MIPS_26','memcpy')],128:[('R_MIPS_26','memcpy')],152:[('R_MIPS_26','func_15144B34')],396:[('R_MIPS_26','func_150AD8B0')]}
        self.assertEqual(self.refs,expected);self.assertEqual(c.source_states(self.proposed),(self.before,self.proposed,True))
        self.receipts['owner']=dict(raw_words=337,raw_frame=128,retail_words=336,retail_frame=152,bound_word_differences_plus_extent=sum(a!=b for a,b in zip(self.words,self.truth))+1,raw_neighbors=58,pools_fixed=True,warnings_before=43,warnings_after=39,new_warnings=0,bindings=5,raw_sha256=c.RAW_SHA256,padding_not_qualified=True)
    def test_02_independent_public_model_original_helpers_and_saved_roles(self):
        seen=set();count=raw_count=0
        for case in g.cases():
            initial=g.fixture(case);e=g.reference(initial,case)
            for label,body in[('retail',self.truth)]+([]if case.private else[('raw',self.words)]):
                m=g.Oracle(body,initial,case);r=m.r[:];f=m.f[:];m.run()
                self.assertEqual((g.public(m.memory,case),m.semantic_calls,m.r[2]),(e['observed'],e['semantic_calls'],e['value']),(label,case))
                self.assertEqual(m.r[16:24],r[16:24]);self.assertEqual((m.r[29],m.r[31]),(r[29],r[31]));self.assertEqual(m.f[20:],f[20:])
                if label=='retail':seen.update(m.visits)
                else:raw_count+=1
            count+=1
        missing={i for i in range(336)if c.ENTRY+i*4 not in seen};self.assertEqual(missing,{139,232})
        reachable=reachable_words(self.truth);self.assertEqual(reachable,set(range(336))-missing)
        self.assertEqual(self.truth[139],self.truth[126]);self.assertEqual(self.truth[232],self.truth[148]);self.assertEqual((self.truth[125]>>26,self.truth[125]>>16&31,self.truth[147]>>26),(17,3,20))
        for entry,off,n in((g.COPY,0x22EC0,11),(g.BACKEND,0x203210,52),(g.CROSS,0xDAD60,19),(g.GETTER,0x171FE4,13)):
            self.assertEqual(self.elf[elf_slot_offset(self.elf,entry,n*4):elf_slot_offset(self.elf,entry,n*4)+n*4],self.rom[off:off+n*4]);self.assertGreater(len(seen&set(range(entry,entry+n*4,4))),0)
        self.assertEqual((count,raw_count),(587,582))
        self.receipts['model']=dict(retail_cases=count,raw_nonprivate_cases=raw_count,reachable_words=334,unreachable_duplicate_indices=sorted(missing),static_CFG_and_dynamic_coverage_agree=True,literal_helper_words=95,connected_copy_backend_cross_getter=True,actor_template_aliases_and_live_reads=True,private_helper_mutations=True,callee_saved_roles=True,raw_private_fault_identity_not_claimed=True,hardware_FCSR_and_nan_payload_not_emulated=True)
    def test_03_native32_typed_leaf_and_effective_controls(self):
        def run(label,body=None,opt='-O2',wrong_viewer=False):
            text=native.harness(body)
            if wrong_viewer:
                original='cameraState+view*0x9A0+0x2F8';self.assertIn(original,text);text=text.replace(original,'cameraState+0x2F8',1)
            p=self.out/(label+'.c');p.write_text(text,encoding='utf-8');exe=p.with_suffix('.elf');command=[*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(self.root)),*native.LINK_FLAGS,'-o',str(exe.relative_to(self.root))]
            v=subprocess.run(command,cwd=self.root,capture_output=True,text=True);self.assertEqual((v.returncode,v.stdout,v.stderr),(0,'',''));return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,opt=opt),0)
        body=c.CANDIDATE;variants=dict(stub=body[:body.index('{')+1]+'\nreturn NULL;\n}',wrong_return=body.replace('return scratch.first;','return scratch.cursor;'),missing_flags=body.replace('scratch.cursor->v.flag = 0;',''),wrong_normalization=body.replace('length = width / sqrtf(length);','length = width;'),wrong_height_scale=body.replace('scale[1]','scale[0]'),missing_order=body.replace('if (alternateOrder)','if (0)'))
        for name,changed in variants.items():self.assertNotEqual(changed,body);self.assertEqual(run('negative-'+name,changed),1,name)
        self.assertEqual(run('negative-viewer-return',wrong_viewer=True),1)
        self.assertEqual(len(native.cases()),503)
        self.receipts['native']=dict(cases_per_executable=503,optimizations=3,effective_semantic_negatives=list(variants),effective_wrong_viewer_return_control=True,distinct_viewer_records=True,typed_pointer_u8_scale_pointer_s16_leaf=True,SDK_Vtx16_pointer32=True,finite_representable_casts=True,trapping_UBSan=True,round_to_nearest_no_FTZ_DAZ=True,actual_renderer_chain_not_yet_executed=True)
    def test_04_complete_original_caller_inventory_without_adoption_credit(self):
        opcode=0x0C000000|((c.ENTRY>>2)&0x3FFFFFF);calls=[];pointers=[]
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==opcode:calls.append(i*4)
            if c.ENTRY<=word<c.ENTRY+336*4:pointers.append(i*4)
        self.assertEqual((calls,pointers),([0x16CF08,0x16CF4C,0x1EB9F0],[]))
        for entry,off,n in((0x1513FA2C,0x16CEDC,17),(0x1513FA70,0x16CF20,17),(0x151B863C,0x1E5AEC,11),(0x151BE4B8,0x1EB968,40)):
            p=elf_slot_offset(self.elf,entry,n*4);self.assertEqual(self.elf[p:p+n*4],self.rom[off:off+n*4])
        for slot,entry in((25,0x151B863C),(27,0x1513FA2C),(28,0x1513FA70),(29,0x151BE4B8)):self.assertEqual(struct.unpack_from('>I',self.rom,0x22E8DC+slot*4)[0],entry)
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22E978)[0],0xE7000000)
        self.receipts['caller_inventory']=dict(direct_callers=3,entry_or_interior_pointers=0,caller_words_literal_exact=85,renderer_slots=[25,27,28,29],caller_execution_not_qualified=True,pointer_return_declaration_repairs_still_private=True,normalization_padding_full_image_and_adoption_gates_remaining=True)

if __name__=='__main__':unittest.main()
