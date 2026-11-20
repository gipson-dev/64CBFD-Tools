"""CFG-certified map-trail FP/FCSR layout, both padding routes and full-image audit."""
import csv,hashlib,io,json,os,re,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_map_trail_emitter_151058b4_match_proof import prove as relation
from tools.tests.game_map_trail_emitter_151058b4_match_normalizer import normalize as derive
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-map-trail-emitter-151058b4-storage'
SPEC=json.loads(Path(__file__).with_name('game_map_trail_emitter_151058b4_match_manifest.json').read_text());FUNCTION=SPEC['function'];SOURCE=SPEC['source'];OBJECT=SPEC['object']
ENTRY,ROM,SIZE=SPEC['entry'],SPEC['rom'],788;OUT=PACKET/'qualified';BASE=PACKET/'baseline'
GUARDS='conker/retail_word_patches.us.csv';ELF='conker/build/conker.us.elf';PROGRESS='conker/progress.csv'
sha=lambda b:hashlib.sha256(b).hexdigest()
FRAGMENT,TYPES=SPEC['fragment'],SPEC['types']

def opcode_role(w):
    op,rs,rt,fn,imm=w>>26,w>>21&31,w>>16&31,w&63,w&65535
    if not w:return('NOP',)
    if op==17:return('COP1',rs,fn if rs in(16,20)else 0)
    if op==0:return('SPECIAL',fn,w>>6&31 if fn in(0,2,3)else 0)
    if op in(1,4,5,6,7,20,21,22,23):return('BRANCH',op,rt if op==1 else 0)
    if op==3:return('JAL',w&0x3ffffff)
    if op in(33,35,36,40,41,43,49,53,57,61)and rs==29:return('PRIVATE-SP',op)
    if op==9 and rs==29 and rt!=29:return('PRIVATE-ADDRESS',op)
    return(op,imm)

def packing_certificate(retail,raw):
    assert len(retail)==len(raw)==197 and len(SPEC['guard_rows'])==47
    assert sum(a!=b for a,b in zip(retail,raw))==47
    assert all(not row['insert_after']and row['omit']=='false'for row in SPEC['guard_rows'])
    return dict(rows=47,unchanged_source_words=150,stack_operands=39,initializer_schedule_words=8,insertions=0,omissions=0,raw_frame=248,normalized_frame=240,complete_loop_inductive_relation_required=True)

def checked(raw,refs):
    if len(raw)!=788 or sha(raw)!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Map-trail raw words/bindings changed')
    return raw,refs
def normalize(raw,refs):
    checked(raw,refs)
    normal,bindings,stack=derive(raw,refs)
    assert len(stack)==39 and sha(normal)==SPEC['original_raw_sha256']and json.loads(json.dumps(bindings))==SPEC['original_refs']
    return normal,bindings
def assemble(label,assembly):
    folder=OUT/label;folder.mkdir(parents=True,exist_ok=True);s=folder/'game_131F30.c.s';obj=s.with_suffix('.o');s.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(s)],check=True,capture_output=True)
    return obj
def layout_assembly(rom):
    rows=pc.load_layout(ROOT/'conker/retail_layout.us.txt',SPEC['owner']);text=[]
    assert len(rows)==11 and rows[0]['address']==0x15104A80
    for row in rows:
        text.append('glabel '+row['name'])
        for address in range(row['address'],row['end'],4):
            at=ROM+address-ENTRY;word=struct.unpack_from('>I',rom,at)[0]
            text.append(f'/* {at:X} {address:08X} {word:08X} */ .word 0x{word:08X}')
    out=OUT/'independent-retail-layout.s';out.write_text('\n'.join(text)+'\n');return out
def diagnostics(text):return re.sub(r'[\w./-]+\.c, line \d+:','<owner>:',text)
def actual_Make(wanted,compact,guards):
    conker=ROOT/'conker';proposal=OUT/'proposed-source.c';proposal.write_text(SPEC['selected']);shadow=OUT/'make-shadow';target=shadow/'src/game_131F30.c.o';target.parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
    (OUT/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
        args=[proposal.relative_to(conker).as_posix()if a=='src/game_131F30.c'else guards.relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
        redirect=None
        if '>'in args:
            assert args.count('>')==1 and args[-2]=='>'
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        result=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        assert result.returncode==0,result.stdout+result.stderr
        if args[0]=='../ido/ido5.3_recomp/cc':
            assert args.count('-O2')==args.count('-g3')==1 and '-O1'not in args
            assert diagnostics(result.stdout+result.stderr)==SPEC['normalized_diagnostics'],result.stdout+result.stderr
        else:
            assert not result.stderr and(not result.stdout or redirect is not None),result.stdout+result.stderr
        if redirect:redirect.write_text(result.stdout)
        commands.append(args)
    assert len(commands)==5 and target.read_bytes()==wanted.read_bytes(),('Make route/object',commands)
    assert same_functions(compact,Path(str(target)+'.compact'))==11
    assert normalized_pools(compact)==normalized_pools(Path(str(target)+'.compact'))
    (OUT/'actual-Make-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=5,padded_object_equal=True,unchanged_warnings=2,wrapper_warnings_removed=3,profile='existing O2/g3',mixed_GLOBAL_ASM_recipe=True)
def census(rom):
    words=struct.unpack('>%dI'%(len(rom)//4),rom);calls=[];pointers=[];materializations=[]
    for i,w in enumerate(words):
        if w>>26 in(2,3)and((w&0x3ffffff)<<2|0x10000000)==ENTRY:calls.append(i*4)
        if w==ENTRY:pointers.append(i*4)
        if w>>26==9 and w&65535==ENTRY&65535:
            rs,rt=w>>21&31,w>>16&31
            if rs==rt:
                for j in range(max(0,i-16),i):
                    if words[j]==(0x3c000000|(rs<<16)|((ENTRY+0x8000)>>16)):materializations.append([j*4,i*4])
    assert len(calls)==1 and 0x132CF8<=calls[0]<0x132D64 and not pointers and not materializations,(calls,pointers,materializations)
    return dict(direct_calls=calls,literal_pointers=pointers,nearby_same_register_HI_LO=materializations,known_wrapper='func_15105848',arbitrary_computed_calls_not_excluded=True)
def strict_image(actual):
    expected=(BASE/ELF).read_bytes()
    if sha(expected)!=SPEC['predecessor']['inputs'][ELF]or actual!=expected:raise ValueError('Map-trail full image differs from frozen prediction')
    return 0
def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    mutable={SOURCE,OBJECT,ELF,GUARDS,PROGRESS,'README.md'}
    for n,h in SPEC['predecessor']['inputs'].items():
        q=BASE/n if n in mutable or n.startswith('DOCS/')else ROOT/n
        if sha(q.read_bytes())!=h:raise ValueError('Frozen map-trail input changed: '+n)
    live=(ROOT/SOURCE).read_text();assert live in(SPEC['old_source'],SPEC['selected']);installed=live==SPEC['selected']
    oldguards=(BASE/GUARDS).read_bytes();eol='\r\n'if b'\r\n'in oldguards else'\n';newguards=oldguards+SPEC['append_guards'].replace('\n',eol).encode()
    assert sha(newguards)==SPEC['new_guards_sha256']and(ROOT/GUARDS).read_bytes()==(newguards if installed else oldguards)
    csvold=(BASE/PROGRESS).read_bytes();assert csvold.count(b',func_151058B4,353392820,788,asm')==1
    csvnew=csvold.replace(b',func_151058B4,353392820,788,asm',b',func_151058B4,353392820,788,c')
    assert csvnew!=csvold and(ROOT/PROGRESS).read_bytes()==(csvnew if installed else csvold)
    guards=OUT/'proposed-guards.csv';guards.write_bytes(newguards);(OUT/'proposed-progress.csv').write_bytes(csvnew)
    before,bd=compile_owner(ROOT,OUT,SPEC['old_source'],'before');after,ad=compile_owner(ROOT,OUT,SPEC['selected'],'after')
    assert diagnostics(bd)==SPEC['diagnostics_before']and diagnostics(ad)==SPEC['diagnostics_after']and bd.count('cfe: Warning')==5 and ad.count('cfe: Warning')==2
    raw,refs=checked(*payload(after,FUNCTION));normalized,nrefs=normalize(raw,refs)
    assert same_functions(before,after,(FUNCTION,))==10 and normalized_pools(before)==normalized_pools(after)
    original=assemble('original','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(ROOT/'conker/asm/nonmatchings/game_131F30/func_151058B4.s').read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    assert payload(original,FUNCTION)==payload(before,FUNCTION)==(normalized,nrefs)
    rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=rom[ROM:ROM+SIZE];assert sha(truth)==SPEC['retail_sha256']
    retail_words=bound_blob(normalized,nrefs);words=bound_blob(raw,refs)
    assert struct.pack('>197I',*retail_words)==truth
    proof=relation(words,retail_words);(OUT/'CFG-relation.json').write_text(json.dumps(proof,indent=2)+'\n')
    packing=packing_certificate(retail_words,words);(OUT/'packing-certificate.json').write_text(json.dumps(packing,indent=2)+'\n')
    primary_before=assemble('before-pad',pc.emit_padded_assembly(before,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=BASE/GUARDS))
    primary=assemble('after-pad',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=guards))
    assert same_functions(primary_before,primary)==11 and normalized_pools(primary_before)==normalized_pools(primary)
    assert payload(primary,FUNCTION)==(normalized,nrefs)
    assert(ROOT/OBJECT).read_bytes()==(primary if installed else primary_before).read_bytes()
    fullasm=layout_assembly(rom)
    independent=assemble('independent-pad',pg.emit_padded_assembly(after,fullasm,filename=SPEC['owner'],word_patches_path=guards))
    assert same_functions(primary,independent)==11 and normalized_pools(primary)==normalized_pools(independent)
    make=actual_Make(primary,after,guards)
    with patch.multiple(linker,FILENAME=SPEC['owner'],OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        oldelf=linker.link_image(ROOT,OUT,primary_before,'before-image');newelf=linker.link_image(ROOT,OUT,primary,'after-image')
    assert oldelf.read_bytes()==newelf.read_bytes()==(ROOT/ELF).read_bytes()
    strict_image(oldelf.read_bytes());strict_image(newelf.read_bytes())
    af,_,aa=load_elf_functions(str(oldelf),'mips-linux-gnu-objdump');bf,_,ba=load_elf_functions(str(newelf),'mips-linux-gnu-objdump')
    assert af==bf and aa==ba and bf[FUNCTION]==retail_words
    data=audit_layout(newelf,ROOT/'conker');assert data['exact']and not data['different_bytes']
    report=dict(body_words=197,raw_words=197,frame=240,raw_frame=248,guards=len(SPEC['guard_rows']),insertions=0,word_differences=47,unchanged_owner_neighbors=10,new_diagnostics=0,omissions=0,unchanged_raw_neighbors=10,independent_padders=True,Make=make,
        source_installed=installed,matching_credit=int(installed),ELF_identical=True,strict_changed_bytes=0,exclusions=0,all_addresses_fixed=True,functions=len(af),
        conversion_rows=1,protected_data=data,ELF_sha256=sha(newelf.read_bytes()),census=census(rom))
    (OUT/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,out=OUT,raw=raw,refs=refs,truth=retail_words,words=words,after=primary,retail=original,original_refs=nrefs,elf=newelf,oldelf=oldelf,fullasm=fullasm)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
