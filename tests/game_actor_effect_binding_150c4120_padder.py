"""Both owner padders; independent GNU links across code/data HI16 carries."""
import csv,io,json,struct,subprocess,sys
from tools.experiments import game_actor_effect_binding_150c4120_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc

def main():
    r,o=s.ROOT,s.OUT;conker=r/'conker';old=(o/'production-baseline/conker/retail_word_patches.us.csv').read_bytes();new=(o/'proposed-guards.csv').read_bytes()
    assert (conker/'retail_word_patches.us.csv').read_bytes() in (old,new) and new.startswith(old)
    before=list(csv.DictReader(io.StringIO(old.decode())));after=list(csv.DictReader(io.StringIO(new.decode())))
    assert after[:len(before)]==before and len(after)==len(before)+70
    assert {row['function'] for row in after[len(before):]}=={s.NAME}
    rows=[row for row in csv.DictReader(io.StringIO((conker/'retail_layout.us.txt').read_text())) if row['filename']=='generated_F15D0']
    prelude='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n';original=prelude;rom=(conker/'conker.us.bin').read_bytes()
    for row in rows:
        path=conker/'asm/nonmatchings/generated_F15D0'/(row['function']+'.s')
        if path.exists():original+=path.read_text()+'\n'
        else:
            original+='glabel '+row['function']+'\n'
            for at in range(int(row['address'],16),int(row['end'],16),4):
                off=at-0x15000000+0x2d4b0;word=struct.unpack_from('>I',rom,off)[0]
                original+='/* %X %08X %08X */ .word 0x%08X\n'%(off,at,word,word)
    whole=o/'original-owner.s';whole.write_text(original)
    target=(conker/'asm/nonmatchings/generated_F15D0'/f'{s.NAME}.s').read_text()
    texts=dict(generated=pg.emit_padded_assembly(o/'recovered.o',whole,filename='generated_F15D0',word_patches_path=o/'proposed-guards.csv'),c=pc.emit_padded_assembly(o/'recovered.o',conker/'retail_layout.us.txt','generated_F15D0',word_patches_path=o/'proposed-guards.csv'),retail=prelude+target+'\n.size '+s.NAME+',.-'+s.NAME+'\n')
    raw,refs=s.normalize(*payload(o/'recovered.o',s.NAME));mapped=refs
    for name,text in texts.items():
        asm=o/(name+'-padded.s');obj=o/(name+'-padded.o');asm.write_text(text)
        q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(asm)],cwd=conker,capture_output=True,text=True)
        assert q.returncode==0 and not q.stderr,q.stderr
        if name!='retail':assert payload(obj,s.NAME)==(raw,mapped)
    assert same_functions(o/'generated-padded.o',o/'c-padded.o')==6
    assert same_functions(o/'production-baseline/conker/build/src/game/generated_F15D0.c.o',o/'c-padded.o',(s.NAME,))==5
    assert normalized_pools(o/'generated-padded.o')==normalized_pools(o/'c-padded.o')==normalized_pools(o/'production-baseline/conker/build/src/game/generated_F15D0.c.o')
    lookup={row[1]:row[2][1] for row in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
    def link(obj,region,data_base,label):
        _,functions,_=pg.parse_object(obj);offset=functions[s.NAME]['value'];script,elf,binary=[o/(label+ext) for ext in ('.ld','.elf','.bin')]
        target=region+s.ENTRY-0x15000000;script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
        undefined=subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True)
        symbols={name:lookup[name] for line in undefined.splitlines() if (name:=line.split()[-1])}
        # Move Init memcpy with the Game code so JAL stays in its 256 MB region.
        symbols={n:(region+v-0x15000000 if 0x10000000<=v<0x17000000 else v) for n,v in symbols.items()}
        symbols={n:(v+data_base-0x800A0340 if n.startswith('D_') and 0x80000000<=v<0x81000000 else v) for n,v in symbols.items()}
        q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',s.NAME,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
        assert q.returncode==0,q.stderr
        subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
        return binary.read_bytes()[offset:offset+s.SIZE]
    for i,(region,base) in enumerate(zip((0x15000000,0x25000000,0x65000000,0x95000000),(0x800a0340,0x800a7ff0,0x800a8000,0x800afff0))):
        outputs=[link(o/(name+'-padded.o'),region,base,f'rebase-{i}-{name}') for name in texts]
        assert len(outputs[0])==s.SIZE and outputs[0]==outputs[1]==outputs[2]
        if i==0:assert outputs[0]==rom[s.ROM:s.ROM+s.SIZE]
    rejected=0
    for at in range(len(before),len(after)):
        bad=[dict(row) for row in after];bad[at]['expected']='0x%08X'%(int(bad[at]['expected'],16)^1)
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(after[0]),lineterminator='\n');writer.writeheader();writer.writerows(bad)
        path=o/'corrupt-guards.csv';path.write_text(stream.getvalue())
        for emitter in (lambda:pg.emit_padded_assembly(o/'recovered.o',whole,filename='generated_F15D0',word_patches_path=path),lambda:pc.emit_padded_assembly(o/'recovered.o',conker/'retail_layout.us.txt','generated_F15D0',word_patches_path=path)):
            try:emitter()
            except ValueError:rejected+=1
            else:raise AssertionError('Corrupt expected-word guard accepted')
    assert rejected==140
    report=dict(padders=2,owner_functions=6,neighbors=5,body_words=225,alignment_words=0,guards=70,corrupt_guards_rejected=rejected,layouts=4,gnu_links=12,readonly_pool_bytes=0,retail_pool_symbol=None,production_pools_unchanged=True)
    (o/'padder-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
