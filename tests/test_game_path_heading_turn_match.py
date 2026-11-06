"""Execution, ABI, owner, rebasing and production gates for path heading turn."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_path_heading_turn_candidates as candidate
from tools.experiments import game_path_heading_turn_match as match
from tools.experiments import game_path_heading_turn_roles as roles
from tools.tests import game_path_heading_turn_oracle as g
from tools.tests import game_path_heading_turn_native as native
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.fcsr

class PathHeadingTurnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>68I',cls.rom,match.ROM))
        ctx=type('OriginalHeading',(),dict(root=ROOT,out=cls.out));cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'original-heading',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.raw=g.bound(cls.prepared['qualified_compact']);raw,b=match.function_blob(cls.prepared['qualified_compact']);fitted,fb=match.normalized(raw,b,cls.rom[match.ROM:match.ROM+272]);cls.fitted=roles.bound_blob(fitted,fb);cls.words=g.bound(cls.prepared['qualified_owner'])
        assert g.bound(cls.original)==cls.retail==cls.fitted==cls.words
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),s=None,initial=None,entry=match.ENTRY,images=None,query=False,turn=False):
        s=g.symbols() if s is None else s;initial=g.fixture(c,s) if initial is None else initial;models=[]
        images=(self.retail,self.raw,self.fitted,self.words) if images is None else images
        for words in images:
            m=g.Oracle(words,initial,c,s,entry,g.helper_code(self.rom,query,turn));qreturn=entry+8+4*next(i for i,w in enumerate(words) if w>>26==3)
            expected,calls=g.reference(initial,c,s,m.before[31],qreturn,query,turn);m.run()
            self.assertEqual(m.memory,expected,(c,query,turn));self.assertEqual(m.calls,calls,(c,query,turn));self.assertEqual(m.fcsr,c.fcsr)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual(m.f[20:],m.before_f[20:]);models.append(m)
        for m in models[2:]:self.assertEqual(state(models[0]),state(m))
        return models
    def test_01_owner_guards_roles_and_corruption(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['raw_words'],q['frame'],q['row_byte_home'],q['guards'],q['bindings'],q['raw_neighbors'],q['neighbors']),(68,67,40,30,42,14,210,210))
        raw,b=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+272]
        for at in range(268):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),b,truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        for i in(0,24,16,60,55):
            bad=self.raw[:];w=bad[i]
            if i==0:bad[i]^=8
            elif i==16:bad[i]^=4<<26
            elif i==55:bad[i]=(w&~((31<<21)|(31<<16)))|((w>>21&31)<<16)|((w>>16&31)<<21)
            else:bad[i]^=1
            with self.assertRaises((ValueError,AssertionError)):roles.prove(self.retail,bad)
        old=(self.out/'frozen'/match.GUARDS).read_bytes();manifest=match.guard_manifest(old,raw);self.assertTrue(manifest.startswith(old));rows=list(csv.DictReader(io.StringIO(manifest.decode())))
        for target in match.ROWS:
            for field in('expected','expected_relocations'):
                bad=[dict(r) for r in rows];r=next(r for r in bad if r['function']==match.FUNCTION and r['offset']==target['offset']);r[field]='0x0' if field=='expected' else 'R_MIPS_HI16:foreign'
                buf=io.StringIO(newline='');w=csv.DictWriter(buf,bad[0].keys());w.writeheader();w.writerows(bad)
                with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],buf.getvalue().encode(),'bad-guard')
        bad=[dict(r) for r in rows]
        for r in bad:
            if r['function']==match.FUNCTION:r['insert_after']='';r['insert_after_relocations']=''
        buf=io.StringIO(newline='');w=csv.DictWriter(buf,bad[0].keys());w.writeheader();w.writerows(bad)
        omitted=match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],buf.getvalue().encode(),'missing-copy')
        self.assertNotEqual(match.function_blob(omitted),match.function_blob(self.prepared['qualified_owner']))
        self.receipt('owner-controls',raw_corruptions=268,binding_corruptions=14,guard_corruptions=84,symbolic_corruptions=5,missing_copy_rejected=True,all_210_neighbors_and_pools_fixed=True)
    def test_02_independent_guest_contract_and_coverage(self):
        seen=set();count=0
        for c in g.cases():
            ms=self.compare(c);seen.update(ms[0].visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+272,4)))
        self.receipt('guest-contract',cases_per_body=count,bodies=4,all_68_words=True,complete_memory_including_stack=True,byte_rows_and_strict_ties=True,raw_fault_or_dead_register_equality_claimed=False)
    def test_03_both_original_helpers_and_FP_control(self):
        count=0;seen_query=set();seen_turn=set()
        values=(0,0x80000000,0x3F000000,0xBF000000,0x3F800000,0xBF800000,0x4EFFFFFF,0x4F000000,0x4F7FFFFF,0x4F800000,0x7F800000,0x7FC12345)
        for query,turn,value,phase,mutation in itertools.product((False,True),(False,True),values,(0,8),(0,7)):
            c=g.Case(mode=(count*37)&255,angle=(count*263)&65535,current=(count*251)&65535,threshold=0,query_float=value,phase=phase,mutation=mutation,pattern=count%4,fcsr=(0,3,0xA5A50003)[count%3]);ms=self.compare(c,query=query,turn=turn);seen_query.update(ms[0].visits);seen_turn.update(ms[0].visits);count+=1
        for pattern,sentinel,distance,negative in itertools.product(range(4),(False,True),(1,63,64,127,128),(False,True)):
            c=g.Case(angle=((256-distance if negative else distance)<<8)&65535,threshold=0,mode=pattern+1);initial=g.fixture(c);row=pattern
            initial[g.symbols()['D_80099A3C']+row*10+2],initial[g.symbols()['D_80099A3C']+row*10+7]=((0,0),(63,127),(200,100),(255,255))[pattern]
            for off in(3,4,5,6,8,9):initial[g.symbols()['D_80099A3C']+row*10+off]=255 if sentinel else 21+off
            ms=self.compare(c,initial=initial,turn=True);seen_turn.update(ms[0].visits);count+=1
        qwords=set(range(g.QUERY,g.QUERY+200,4));self.assertEqual(qwords-seen_query,{g.QUERY+0x9C})
        self.assertTrue(set(range(g.TURN,g.TURN+264,4))<=seen_turn)
        self.receipt('helper-contract',cases_per_body=count,bodies=4,original_query_words=50,query_unreachable_word_retained='0x1505A6CC',original_turn_words=66,all_reachable_helper_words=True,bounded_nontrapping_FCSR_restored=True,atan_provider_opaque=True,full_hardware_FP_claimed=False)
    def test_04_aliases_faults_and_sparse_state(self):
        count=cuts=0
        for alias,mode,mutation,phase in itertools.product((1,2,3,4),(0,1,255),(0,7,8),(0,8)):
            c=g.Case(alias=alias,mode=mode,angle=0x8000,threshold=0,mutation=mutation,phase=phase);s=g.symbols()
            if alias==2:s['D_800D154C']=g.ACTOR+0x78
            if alias==3:s['D_80099A3C']=g.STACK+phase-40+30-((mode-1)&255)*10
            if alias==4:s['D_800D1891']=g.STACK+phase-40+30
            initial=g.fixture(c,s)
            if alias==2:
                a=(c.angle&65535)<<16
                initial.update({a+i:(i*13+89)&255 for i in range(0x340)});g.put(initial,a+0x76,c.current,2)
            raw,b=match.function_blob(self.prepared['qualified_compact']);fit,fb=match.normalized(raw,b,self.rom[match.ROM:match.ROM+272])
            images=(g.bound(self.original,s),g.bound(self.prepared['qualified_compact'],s),roles.bound_blob(fit,fb,s),g.bound(self.prepared['qualified_owner'],s))
            self.compare(c,s,initial,images=images);count+=1
        for c in(g.Case(),g.Case(angle=0,threshold=255),g.Case(mode=0,angle=0x8000,mutation=7),g.Case(alias=1,mutation=8)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.fitted,self.words):
                    m=g.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
                cuts+=1
        c=g.Case(angle=0,threshold=255);initial=g.fixture(c);del initial[g.symbols()['D_800D1891']]
        self.compare(c,initial=initial)
        self.receipt('aliases-faults',aliases=count,fired_access_prefixes=cuts,sparse_unused_notice=True,guest_only_private_home_aliases=True)
    def test_05_original_dispatch_and_discarded_return(self):
        va,end=0x1507BD00,0x1507BD74;body=list(struct.unpack_from('>29I',self.rom,va-0x15000000+0x2D4B0));count=0;seen=set()
        for opcode,poison,phase,mutation,mode in itertools.product((157,247,255),(0,1,0x80000000,0xFFFFFFFF),(0,8),(0,7),(0,1,255)):
            c=g.Case(mode=mode,angle=0x8000,threshold=0,mutation=mutation,phase=phase);s=g.symbols();initial=g.fixture(c)
            packet=(opcode,mode,173,39,41)
            for j,v in enumerate(packet):initial[g.SCRIPT+j]=v
            g.put(initial,g.actor(c)+0x218,g.SCRIPT);g.put(initial,g.DISPATCH+157*4,match.ENTRY)
            for i,words in enumerate((self.retail,self.raw,self.fitted,self.words)):
                code=dict(zip(range(match.ENTRY,match.ENTRY+len(words)*4,4),words));code[end]=0;m=g.Oracle(body,initial,c,entry=va,connected=code);m.r[16]=g.actor(c)
                for reg,p in zip((17,18,19,20),(s['D_800D1890'],s['D_800D1891'],0x800D1892,0x800D1893)):m.r[reg]=p;m.memory.setdefault(p,0)
                m.r[21]=g.DISPATCH;m.before=m.r[:];m.poison=poison;m.code=g.PoisonCode(m.code,m);m.code.ends=(end,)
                expected=dict(m.memory)
                if opcode==157:
                    for p,v in zip((s['D_800D1890'],s['D_800D1891'],0x800D1892,0x800D1893),packet[1:]):expected[p]=v
                    g.put(expected,g.actor(c)+0x218,g.SCRIPT+5);qr=match.ENTRY+8+4*next(j for j,w in enumerate(words) if w>>26==3);expected,calls=g.reference(expected,c,ra=0x1507BD68,query_return=qr);calls=[(match.ENTRY,())]+calls
                else:g.put(expected,g.actor(c)+0x218,g.SCRIPT+1);calls=[]
                with self.assertRaises(g.WindowBoundary):m.run()
                self.assertEqual(m.memory,expected);self.assertEqual(m.calls,calls);self.assertEqual(m.poison_hits,int(opcode==157));seen.update(m.visits)
            count+=1
        self.assertEqual(set(range(va,end,4))-seen,{va+0x20})
        self.receipt('caller-controls',cases_per_body=count,bodies=4,original_window_words=29,callback=157,return_poisons=4,packet_advance_5_or_1=True,whole_dispatcher_claimed=False)
    def test_06_independent_GNU_links_and_carries(self):
        links=count=0
        raw,rb=match.function_blob(self.prepared['qualified_compact']);fit,fb=match.normalized(raw,rb,self.rom[match.ROM:match.ROM+272])
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:
                base=0x81000000+k*0x08000000;s.update(D_800D154C=base+0x7FFC,D_800D2104=base+0x18000,D_800D1890=base+0x2FFFC,D_800D1891=base+0x2FFFD,D_80099A3C=base+0x37FFC,func_1505A630=entry+0x10000,func_15056A00=entry+0x20000)
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);f=dict(fs[match.FUNCTION])
                if j==2:t=t[:f['value']]+fit+t[f['value']+f['size']:];f['size']=272;rs={f['value']+at:v for at,v in fb.items()}
                asm,unknown=emit_function(t,f,rs,match.FUNCTION,s);self.assertFalse(unknown);p=self.out/('rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                n=67 if j==1 else 68;images.append(list(struct.unpack_from('>%dI'%n,sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2]);self.assertEqual(images[0],images[3])
            for c in list(g.cases())[::79]:self.compare(c,s,entry=entry,images=images);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_14_bindings=True,HI_LO_carries=True)
    def test_07_native_grid_and_semantic_controls(self):
        effective=[];live=candidate.source_states((ROOT/candidate.SOURCE).read_text(encoding='utf-8'))[1]
        witnesses=list(g.cases())
        for name,body in g.controls().items():
            self.assertNotEqual(body,candidate.SELECTED,name);obj,diag=candidate.compile_owner(ROOT,self.out,live.replace(candidate.SELECTED,body,1),'negative-'+name);words=g.bound(obj);fired=False
            for c in witnesses:
                initial=g.fixture(c);m=g.Oracle(words,initial,c)
                try:m.run();expected,calls=g.reference(initial,c,ra=m.before[31]);fired=(m.memory,m.calls)!=(expected,calls)
                except(AssertionError,KeyError,IndexError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        native_controls=dict(g.controls())
        native_controls['unsequenced-query-store']=candidate.SELECTED.replace('    u16 heading;\n','').replace('    heading = func_1505A630(x, z, 0);\n    D_800D154C->unk78 = heading;','    D_800D154C->unk78 = func_1505A630(x, z, 0);')
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0) for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1) for n,b in native_controls.items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native.source(body),encoding='utf-8');exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);r=subprocess.run([str(exe)]).returncode
            if wanted:self.assertNotEqual(r,0,name)
            else:self.assertEqual(r,0,name)
        self.receipt('native-controls',calls_per_profile=1310720,positive_executions=3932160,all_65536_heading_words=True,mode_values=[0,1,128,255],thresholds=[0,1,127,128,255],profiles=['O0','O2','O3'],UBSan=True,IDO_controls=effective,native_controls=len(native_controls),native_only_unsequenced_store_control=True,explicit_query_store_sequence=True)
    def test_08_literal_image_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+272];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,272)
        for off in(0,at,at+271,at+272,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>68I',before,match.elf_slot_offset(before,match.ENTRY,272)));initial=g.fixture();m=g.Oracle(stub,initial).run();self.assertNotEqual(m.memory,g.reference(initial,g.Case(),ra=m.before[31])[0])
        self.receipt('image-controls',literal_changed_bytes=delta,metadata_permutations=0,exclusions=0,corruptions=5,old_stub_rejected=True)

if __name__=='__main__':unittest.main()
