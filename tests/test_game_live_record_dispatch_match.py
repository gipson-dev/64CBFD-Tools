"""Dispatcher qualification: complete images, ABI, shared flags and original caller/cleanup."""
from pathlib import Path
from dataclasses import replace
import csv,io,itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_record_dispatch_match as source
from tools.tests import game_record_dispatch_oracle as oracle
from tools.tests.game_record_dispatch_oracle import Case,fixture,reference,DispatchOracle,public,corpus,put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]

class RecordDispatchTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>252I',cls.rom,source.ROM));images=[]
        for name in('candidate-qualified-padded.o','candidate-selected.o'):
            p=cls.fresh/name;p.write_bytes((cls.out/name).read_bytes());blob,fs=source.link_owner(ROOT,cls.fresh,p,source.OWNER);images.append(list(struct.unpack_from('>252I',blob,fs[source.FUNCTION]['value'])))
        cls.words,cls.raw=images
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c,images=None,entry=None,connected=None,cleanup=False):
        initial=fixture(c);wanted,calls=reference(initial,c,cleanup);pair=[]
        for words in images or(self.truth,self.words):
            m=DispatchOracle(words,initial,c,entry=entry,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c);pair.append(m)
        for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
        if images is None:
            m=DispatchOracle(self.raw,initial,c,entry=entry,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c)
        return pair[0]
    def rebased(self,obj,entry,s,label,normalize=False):
        text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION]
        if normalize:
            text,bindings=source.normalized_payload(*source.payload(obj));f=dict(value=0,size=1008)
        else:
            begin=f['value'];text=text[begin:begin+f['size']];bindings={at-begin:rows for at,rows in bindings.items()if begin<=at<begin+f['size']};f=dict(value=0,size=f['size'])
        asm,unknown=emit_function(text,f,bindings,source.FUNCTION,s);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%x for x in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack('>252I',sections(p.with_suffix('.elf'))['.text'][1][:1008]))
    def test_01_owner_Make_caller_and_closed_normalization(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(sum(a!=b for a,b in zip(self.raw,self.truth)),66)
        self.assertEqual(source.normalized_payload(*source.payload(self.out/'candidate-selected.o')),source.payload(self.out/'canonical-original-v2-func_15183D28.o'))
        for name in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/('candidate-'+name+'-owner.c')).read_text(),'fresh-'+name);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/('candidate-'+name+'-owner.o')),9)
        self.assertEqual(source.same_functions(self.out/'candidate-before-owner.o',self.out/'candidate-after-owner.o',(source.FUNCTION,)),8)
        self.assertEqual(source.normalized_pools(self.out/'candidate-before-owner.o'),source.normalized_pools(self.out/'candidate-after-owner.o'))
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'candidate-proposed-owner.c').read_text());self.assertEqual(source.HEADERS+source.SELECTED+'\n',(self.out/'candidate-selected-input.c').read_text())
        self.assertEqual(source.recovered_caller(self.values[source.CALLER].decode()),(self.out/'proposed-caller.c').read_text())
        commands=json.loads((self.out/'candidate-Make-commands.json').read_text());self.assertEqual({k:len(v)for k,v in commands.items()},{'owner':3,'caller':3});self.assertFalse(any('-loopunroll'in x for rows in commands.values()for row in rows for x in row))
        self.assertEqual((self.out/'candidate-make-shadow/src/game/generated_1B0740.c.o').read_bytes(),(self.out/'candidate-qualified-padded.o').read_bytes());self.assertEqual((self.out/'candidate-make-shadow/src/game_45B80.c.o').read_bytes(),self.values['conker/build/src/game_45B80.c.o'])
        report=json.loads((self.out/'owner-caller-qualification.json').read_text());self.assertEqual(report['caller_functions_unchanged'],16);self.assertTrue(report['caller_mdebug_prediction']['complete_literal_prediction']);self.assertEqual(report['caller_mdebug_prediction']['excluded_bytes'],0)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0x46814])
        for n in range(1,12):self.assertEqual(n!=11,n<11)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=252,frame=64,guards=66,direct_words=186,finite_counter_words=4,timer_setup_words=3,closed_tail_words=59,neighbors=8,caller_functions=16,caller_object_identical=True,owner_diagnostics=0,caller_inherited_warnings=3,Make_commands=6,full_caller_mdebug_literal_prediction=True)
    def test_02_guest_flags_timers_geometry_and_live_providers(self):
        count=0;seen=set()
        for c in corpus():m=self.compare(c);seen.update(m.visits);count+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+1008,4))<=seen)
        self.receipt['guest']=dict(cases=count,retail_words_visited=252,signed_flag_values=256,defined_rows=11,provider_modes=8,all_eight_geometry_arguments=True,complete_normalized_state_trace=True,raw_C_public_memory_calls=True,alias_state_preserved=True)
    def test_03_original_caller_and_connected_cleanup(self):
        caller=list(struct.unpack_from('>12I',self.rom,0x46804));seen=set();count=0
        for pattern,disabled,mode,phase in itertools.product(range(8),(0,1),(0,1),(0,8)):
            c=Case(pattern=pattern,mode=mode,phase=phase);initial=fixture(c);initial[oracle.DISABLED]=disabled;wanted,calls=reference(initial,c)if not disabled else(dict(initial),[])
            if not disabled:wanted[oracle.DISABLED]=mode&1;calls=[(source.ENTRY,())]+calls+[(oracle.AFTER1,()),(oracle.AFTER2,())]
            pair=[]
            for target in(self.truth,self.words,self.raw):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=DispatchOracle(caller,initial,c,entry=0x15019354,connected=connected);m.code[0x15019384]=0;m.code=WindowCode(m.code,m);m.code.ends=(0x15019384,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));pair.append(m);seen.update(m.visits)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);count+=1
        self.assertTrue(set(range(0x15019354,0x15019384,4))<=seen)
        original=list(struct.unpack_from('>64I',self.rom,0x1B10D8));connected={oracle.CLEANUP+4*i:w for i,w in enumerate(original)};deep=0;visited=set()
        for pattern,mode,flag,phase in itertools.product(range(8),range(4),(1,254),(0,8)):
            m=self.compare(Case(pattern=pattern,mode=mode,flag=flag,phase=phase),connected=connected,cleanup=True);visited.update(m.visits);deep+=1
        self.assertTrue(set(range(oracle.CLEANUP,oracle.CLEANUP+256,4))<=visited)
        self.receipt['integration']=dict(caller_window_words=12,caller_cases=count,caller_all_words=True,caller_gate_and_return_ignored=True,cleanup_words=64,cleanup_cases=deep,cleanup_all_words=True,original_cleanup_connected=True,bounded_providers=['func_15165C80','func_1517725C','func_15179DB0','func_1510D630','func_10004074','func_151670C0','func_15177A94'],full_rendering_or_heap_claim=False)
    def test_04_native32_and_effective_controls(self):
        p=self.fresh/'native.c';p.write_text(native_harness());rows=[]
        for opt in('-O0','-O2','-O3'):
            target=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+[str(p),'-o',str(target)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr));rows.append(dict(profile=opt,cases=780,negatives=12,UBSan_trap=True))
        self.receipt['native']=dict(profiles=rows,public_state_bytes=1168,real_pointers=True,eight_geometry_arguments=True)
    def test_05_access_fault_prefixes(self):
        count=0;deep=0;connected={oracle.CLEANUP+4*i:w for i,w in enumerate(struct.unpack_from('>64I',self.rom,0x1B10D8))}
        for link in(None,connected):
            for c in(Case(flag=1),Case(flag=254,mode=3,phase=8),Case(pattern=15,mode=2)):
                good=self.compare(c,connected=link,cleanup=bool(link))
                for cut in range(good.all_accesses):
                    pair=[]
                    for words in(self.truth,self.words):
                        m=DispatchOracle(words,fixture(c),c,connected=link);m.cut=cut
                        with self.assertRaises(faults.AccessBoundary):m.run()
                        pair.append(m)
                    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of))
                    if link:deep+=1
                    else:count+=1
        self.receipt['faults']=dict(direct_pairs=count,connected_cleanup_pairs=deep,full_state_trace_PC_delay_equal=True,portable_C_fault_semantics_claimed=False)
    def test_06_rebases_padder_and_fail_closed_guards(self):
        raw,rs=source.payload(self.out/'candidate-selected.o');rejects=0
        for row in source.GUARDS:
            bad=bytearray(raw);bad[row['offset']+3]^=1
            with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
            rejects+=1
        with self.assertRaises(ValueError):source.normalized_payload(raw[:-4],rs)
        wrong={**rs,0x1C:[('R_MIPS_HI16','D_800DDF78')]}
        with self.assertRaises(ValueError):source.normalized_payload(raw,wrong)
        before=self.values['conker/retail_word_patches.us.csv'];rows=list(csv.DictReader(io.StringIO(source.guard_manifest(before).decode())))
        for which in range(66):
            modified=[dict(x)for x in rows];selected=[x for x in modified if x['function']==source.FUNCTION];self.assertEqual(len(selected),66);selected[which]['expected']=hex(int(selected[which]['expected'],0)^1);stream=io.StringIO();writer=csv.DictWriter(stream,list(rows[0]));writer.writeheader();writer.writerows(modified);p=self.fresh/('bad-guard-%d.csv'%which);p.write_text(stream.getvalue())
            with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'candidate-after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=p)
        count=0
        for j,(entry,table,geometry,counts,ticks)in enumerate(((source.ENTRY,oracle.TABLE,oracle.GEOMETRY,oracle.COUNTS,oracle.TICKS),(0x17007FFC,0x80017F10,0x80037F90,0x80057FFC,0x80067FFC),(0x2500FFFC,0x8001FF10,0x80047FF0,0x80067FF0,0x8007FFF0))):
            s=oracle.symbols()
            if j:s.update(D_800DDE80=table,D_800DDF68=table+0xE8,D_800DDF73=table+0xF3,D_800DDF78=table+0xF8,D_800DDF60=table+0xE0,D_800DDF64=table+0xE4,D_8008D0B0=geometry,D_8008D318=geometry+616,D_8008D3C0=geometry+784,D_800A72E8=counts,D_800BE9E4=ticks,func_15165C80=entry+0x10004,func_1517725C=entry+0x20004,func_15179DB0=entry+0x30004,func_15183C28=entry+0x40004)
            images=[self.rebased(self.out/n,entry,s,'layout-%d-%d'%(j,k),normalize=k==2)for k,n in enumerate(('canonical-original-v2-func_15183D28.o','candidate-qualified-padded.o','candidate-selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2]);raw_words=self.rebased(self.out/'candidate-selected.o',entry,s,'unmodified-%d'%j)
            if j==1:
                # A shared base relocation would consume the delayed end HI16 too early.
                wrong,br=source.normalized_payload(*source.payload(self.out/'candidate-selected.o'));wrong=bytearray(wrong);struct.pack_into('>I',wrong,0x2F0,0x2463000B);br=dict(br);br[0x2C4]=[('R_MIPS_HI16','D_800DDF68')];br[0x2F0]=[('R_MIPS_LO16','D_800DDF68')]
                asm,unknown=emit_function(bytes(wrong),dict(value=0,size=1008),br,source.FUNCTION,s);self.assertFalse(unknown);p=self.fresh/'bad-end-alias.s';p.write_text(asm);subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
                bad_words=self.rebased(p.with_suffix('.o'),entry,s,'bad-end-alias-link');self.assertNotEqual(bad_words,images[0]);low=bad_words[0x2F0//4]&65535;actual_end=((bad_words[0x2C4//4]&65535)<<16)+(low if low<32768 else low-65536);self.assertEqual(actual_end,s['D_800DDF73']-0x10000)
            with oracle.layout(entry,s):
                for pattern,mode,phase in itertools.product((0,5,15),(0,3,6,7),(0,8)):
                    c=Case(pattern=pattern,mode=mode,phase=phase);self.compare(c,images,entry);wanted,calls=reference(fixture(c),c);m=DispatchOracle(raw_words,fixture(c),c,entry=entry).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));count+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=count,closed_aliases_and_HILO_carries=True,original_Make_and_normalized_identical=True,raw_C_public_equal=True,changed_word_rejections=rejects+2,padder_guard_rejections=66,effective_delayed_HI16_alias_negative=True)
    def test_07_compiled_semantic_negatives(self):
        witnesses={};cases=list(corpus())
        for name,wrong in controls().items():
            obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+wrong,'negative-'+name);self.assertFalse(diag);words=self.rebased_variable(obj,oracle.symbols(),'negative-link-'+name)
            for c in cases:
                wanted,calls=reference(fixture(c),c);m=DispatchOracle(words,fixture(c),c).run()
                if(public(m.memory),m.calls)!=(public(wanted),calls):witnesses[name]=c.__dict__;break
            else:self.fail('Ineffective compiled control: '+name)
        self.assertEqual(len(witnesses),12);self.receipt['compiled_controls']=witnesses
    def rebased_variable(self,obj,s,label):
        blob,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];return list(struct.unpack_from('>%dI'%(f['size']//4),blob,f['value']))
    def test_08_strict_image_and_input_preservation(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+1008];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'candidate-first-linked.elf').read_bytes(),truth)
        at=source.elf_slot_offset(before,source.ENTRY,1008);positions=[20,at,at+999,at+1008,2745156+8,2755492,2974884,3014548,source.elf_slot_offset(before,oracle.CLEANUP,256),source.elf_slot_offset(before,oracle.UPDATE,4)]
        for row in source.symbol_rows(before):
            if row[1]in('D_800DDF64','D_8009E7D4','D_800A72E8'):positions.append(row[3])
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards-v2.csv').read_bytes())
        self.receipt['image']=dict(changed_bytes=sum(a!=b for a,b in zip(before,expected)),code_bytes=sum(a!=b for a,b in zip(before[at:at+1008],truth)),extent_bytes=2,metadata_bytes=104,closed_cycles=3,excluded_bytes=0,effective_corruptions=len(positions)+1,protected_Game_bytes=189088)

# NATIVE_HELPERS
def controls():
    body=source.SELECTED
    def change(a,b):
        assert body.count(a)==1,(a,body.count(a));return body.replace(a,b,1)
    controls={
     'first_bound':change('if (i >= 11) break;','if (i >= 10) break;'),
     'initial_signed':change('if (*flags >= -1)','if ((u8)*flags >= minimumFlag)').replace('    s32 i;', '    s32 i;\n    s32 minimumFlag = -1;',1),
     'missing_view':change('words[0] == 0 || D_800DDF78[i] == 0','words[0] == 0 && D_800DDF78[i] == 0'),
     'timer_floor':change('remaining = 0;','remaining = 1;'),
     'timer_step':change('*timer - D_800BE9E4','*timer - 1'),
     'primary_vertex':change('(void *)D_800DDE80[i].words[2]','(void *)D_800DDE80[i].words[1]'),
     'secondary_geometry':change('&D_8008D318[i - 2]','&D_8008D0B0[i - 2]'),
     'special_index':change('func_1517725C(7);','func_1517725C(6);'),
     'dependent_flag':change('D_800DDF68[10] = 1;','D_800DDF68[10] = 0;'),
     'cleanup_flag':change('if (*flags == -2 &&','if (*flags == -1 &&'),
     'age_minus_one':change('D_800DDF68[age] >= -1','D_800DDF68[age] > -1'),
     'age_zero':change('D_800DDF68[age] > 0','D_800DDF68[age] >= 0'),
    }
    return controls

def native_harness():
    head=source.HEADERS;body=source.SELECTED;target=source.FUNCTION;mutants=controls();cases=list(corpus())
    witnesses={'first_bound': {'seed': 8, 'pattern': 1, 'mode': 1, 'ticks': 1, 'slot': -1, 'flag': 0, 'phase': 8}, 'initial_signed': {'seed': 42, 'pattern': 6, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 1, 'phase': 0}, 'missing_view': {'seed': 7, 'pattern': 1, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 1, 'phase': 0}, 'timer_floor': {'seed': 3, 'pattern': 0, 'mode': 3, 'ticks': 255, 'slot': -1, 'flag': 1, 'phase': 8}, 'timer_step': {'seed': 0, 'pattern': 0, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 1, 'phase': 0}, 'primary_vertex': {'seed': 0, 'pattern': 0, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 1, 'phase': 0}, 'secondary_geometry': {'seed': 0, 'pattern': 0, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 1, 'phase': 0}, 'special_index': {'seed': 0, 'pattern': 0, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 1, 'phase': 0}, 'dependent_flag': {'seed': 0, 'pattern': 0, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 1, 'phase': 0}, 'cleanup_flag': {'seed': 0, 'pattern': 0, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 255, 'phase': 0}, 'age_minus_one': {'seed': 0, 'pattern': 0, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 255, 'phase': 0}, 'age_zero': {'seed': 0, 'pattern': 0, 'mode': 0, 'ticks': 0, 'slot': -1, 'flag': 0, 'phase': 0}}
    blocks=((0x800DDE80,320),(0x8008D0B0,828),(0x800A72E8,16),(0x800BE9E4,4))
    def flat(m):return bytes(m[a+i]for a,n in blocks for i in range(n))
    nativecases=cases[:512]+[Case(seed=x,pattern=12,mode=x%8,ticks=(0,1,255,256,-1)[x%5],slot=x%11,flag=x,phase=(x%2)*8)for x in range(256)]
    nativecases.extend(Case(**c)for c in witnesses.values())
    vectors=[]
    for c in nativecases:
        initial=fixture(c);expected,calls=reference(initial,c);log=[x for target,args in calls for x in(target,*args)];assert len(log)<=128
        vectors.append('{'+','.join(('{'+','.join(map(str,flat(initial)))+'}','{'+','.join(map(str,flat(expected)))+'}',str(c.mode),str(len(log)),'{'+','.join(str(x)+'u'for x in log)+'}'))+'}')

    prefix=re.sub(r'^extern[^\n]*\n','',head,flags=re.M)
    harness=prefix+r'''
    typedef struct {Record15183974 table[11];u32 unusedDC;u8 timers[4];u32 unusedE4;s8 flags[11];u8 gap[5];u32 views[11];u8 tail[28];} State;
    typedef struct {RecordUpdate15183D28 rows[14];u8 *indices[11];} Geometry;
    static State state;static Geometry geometry;static u8 counts[16];static s32 ticks;
    static u8 buffers[5][65536],indexBytes[352];static u32 actualLog[128],actualCount,mode,ordinal;
    typedef char Layout[(sizeof(void*)==4&&sizeof(State)==320&&sizeof(Geometry)==828&&sizeof(RecordUpdate15183D28)==56)?1:-1];
    #define D_800DDE80 state.table
    #define D_800DDF78 state.views
    #define D_800DDF68 state.flags
    #define D_800DDF60 state.timers
    #define D_800DDF64 (state.timers+4)
    #define D_8008D0B0 geometry.rows
    #define D_8008D318 (geometry.rows+11)
    #define D_8008D3C0 geometry.indices
    #define D_800A72E8 counts
    #define D_800BE9E4 ticks
    static void cp(void *d,const void *s,u32 n){u8 *a=d;const u8 *b=s;while(n--)*a++=*b++;}
    static u32 be(const u8 *p){return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
    static void setbe(u8 *p,u32 v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
    static u32 native(const void *p){u32 v;cp(&v,p,4);return v;}
    static u32 address(u32 v){u32 i;if(!v)return 0;for(i=0;i<5;i++)if(v>=0x70000+i*65536&&v<0x80000+i*65536)return (u32)&buffers[i][v-(0x70000+i*65536)];if(v>=0xD0000&&v<0xD0160)return (u32)&indexBytes[v-0xD0000];return v;}
    static u32 canonical(u32 v){u32 i;for(i=0;i<5;i++)if(v>=(u32)buffers[i]&&v<(u32)buffers[i]+65536)return 0x70000+i*65536+v-(u32)buffers[i];if(v>=(u32)indexBytes&&v<(u32)indexBytes+352)return 0xD0000+v-(u32)indexBytes;if(v>=(u32)&geometry&&v<(u32)&geometry+828)return 0x8008D0B0+v-(u32)&geometry;return v;}
    static void load(const u8 *p){u32 i,j,v;cp(&state,p,320);cp(&geometry,p+320,828);cp(counts,p+1148,16);ticks=(s32)be(p+1164);
    for(i=0;i<11;i++){for(j=0;j<5;j++)state.table[i].words[j]=(s32)address(be(p+i*20+j*4));state.views[i]=be(p+248+i*4);geometry.indices[i]=(u8*)address(be(p+320+784+i*4));}
    for(i=0;i<14;i++)for(j=24;j<=48;j+=4){v=be(p+320+i*56+j);cp((u8*)&geometry.rows[i]+j,&v,4);}actualCount=ordinal=0;}
    static void dump(u8 *p){u32 i,j;cp(p,&state,320);cp(p+320,&geometry,828);cp(p+1148,counts,16);setbe(p+1164,(u32)ticks);
    for(i=0;i<11;i++){for(j=0;j<5;j++)setbe(p+i*20+j*4,canonical((u32)state.table[i].words[j]));setbe(p+248+i*4,state.views[i]);setbe(p+320+784+i*4,canonical((u32)geometry.indices[i]));}
    for(i=0;i<14;i++)for(j=24;j<=48;j+=4)setbe(p+320+i*56+j,native((u8*)&geometry.rows[i]+j));}
    static void effects(u32 target){u32 i,v;ordinal++;
    if(mode==1)state.flags[(ordinal+3)%11]=1;
    else if(mode==2)state.flags[7]=-2;
    else if(mode==3){state.flags[7]=1;state.table[7].words[0]=(s32)address(0x77000);state.views[7]=0xCC007;}
    else if(mode==4)state.table[(ordinal+4)%11].words[0]=0;
    else if(mode==5){v=0x3E800000+ordinal;for(i=36;i<=48;i+=4)cp((u8*)&geometry.rows[(ordinal+2)%14]+i,&v,4);}
    else if(mode==6&&target==0x15183C28){state.flags[8]=state.flags[9]=-2;state.table[9].words[0]=(s32)address(0x79000);state.views[9]=0xCC009;}
    else if(mode==7){state.flags[(ordinal+5)%11]=-1;state.views[(ordinal+6)%11]=0;ticks=(s32)0xDEADBEEF;}}
    __attribute__((noinline,noclone)) void func_15165C80(f32 *p,void *v,f32 scale,f32 *phase,f32 a,f32 b,u8 *indices,u8 count){actualLog[actualCount++]=0x15165C80;actualLog[actualCount++]=canonical((u32)p);actualLog[actualCount++]=canonical((u32)v);actualLog[actualCount++]=native(&scale);actualLog[actualCount++]=canonical((u32)phase);actualLog[actualCount++]=native(&a);actualLog[actualCount++]=native(&b);actualLog[actualCount++]=canonical((u32)indices);actualLog[actualCount++]=count;effects(0x15165C80);}
    __attribute__((noinline,noclone)) void func_1517725C(u8 index){actualLog[actualCount++]=0x1517725C;actualLog[actualCount++]=index;effects(0x1517725C);}
    __attribute__((noinline,noclone)) void func_15179DB0(u8 index){actualLog[actualCount++]=0x15179DB0;actualLog[actualCount++]=index;effects(0x15179DB0);}
    __attribute__((noinline,noclone)) void func_15183C28(s32 index){actualLog[actualCount++]=0x15183C28;actualLog[actualCount++]=index;effects(0x15183C28);}
    '''
    for name,code in dict(selected=body,**mutants).items():harness+=code.replace(target,'test_'+name)+'\n'
    harness+='typedef struct {u8 initial[1168],expected[1168];u32 mode,count,log[128];} Vector;\nstatic const Vector vectors[]={\n'+',\n'.join(vectors)+'\n};\n'
    harness+=r'''
    static int check(void(*fn)(void)){u32 n,i;u8 actual[1168];for(n=0;n<sizeof(vectors)/sizeof(vectors[0]);n++){mode=vectors[n].mode;load(vectors[n].initial);fn();dump(actual);if(actualCount!=vectors[n].count)return 1;for(i=0;i<actualCount;i++)if(actualLog[i]!=vectors[n].log[i])return 2;for(i=0;i<1168;i++)if(actual[i]!=vectors[n].expected[i])return 3;}return 0;}
    static int run(void){if(check(test_selected))return 10;
    '''
    for i,name in enumerate(mutants):harness+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
    harness+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    return harness
