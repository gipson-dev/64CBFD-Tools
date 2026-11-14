"""Reproduce fingerprinted private qualification of the motion-table updater."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-motion-table-150c8350-screen';manifest=out/'production-baseline/fingerprints.json'
if hashlib.sha256(manifest.read_bytes()).hexdigest()!='154c67b36e0dba34e7433c7d4379157b2e1bedd0fd8dab5d40da02fed78f15c1':raise ValueError('frozen input manifest changed')
record=json.loads(manifest.read_text())
for name,want in record['inputs'].items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=want:raise ValueError('qualification input changed: '+name)
old='s32 func_150C8350() {\n    return 0;\n}'
CANDIDATE="""typedef struct { u8 group, pad1; s8 direction; u8 pad3; s16 position, current, target; } MotionEntry150C8350;
extern u8 D_800BE9A0;
extern s32 D_800BE9E4;
/* Advance ten motion records and reflect positions at both limits. */
void func_150C8350(void) {
    s32 offset, current, target, desired, difference, magnitude, step;
    MotionEntry150C8350 *entry;
    for (offset = 0; offset < 10; offset++) {
        entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
        current = entry->current;
        target = entry->target;
        if (current != target) {
            desired = target;
            if (current < 0) desired = -target;
            difference = desired - current;
            step = (s32)((u32)D_800BE9E4 << 4);
            magnitude = difference < 0 ? -difference : difference;
            if (magnitude < step) {
                entry->current = desired;
                entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
                current = entry->current;
            } else {
                entry->current = (s32)((u32)current + (u32)step * (u32)(difference < 0 ? -1 : 1));
                entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
                current = entry->current;
            }
        }
        entry->position += current * entry->direction * D_800BE9A0;
        entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
        if (entry->position >= 0x500) {
            entry->position -= 0x500;
            entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
            entry->position = 0x500 - entry->position;
            entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
            entry->direction = -entry->direction;
            entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
            if (entry->position >= 0x500) entry->position = 0x4FF;
        } else if (entry->position < 0) {
            entry->position = -entry->position;
            entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
            entry->direction = -entry->direction;
            entry = ((MotionEntry150C8350 *)D_800BE4E0 + offset);
            if (entry->position < 0) entry->position = 0;
        }
    }
}"""
owner=(root/'conker/src/game/generated_F5800.c').read_text();assert owner.count(old)==1
baseline,bd=compile_owner(root,out,owner,'baseline');candidate,cd=compile_owner(root,out,owner.replace(old,CANDIDATE),'selected')
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(*payload(candidate,'func_150C8350'),symbols);truth=struct.unpack_from('>105I',(root/'conker/conker.us.bin').read_bytes(),0xf5800)
assert len(words)==105 and sum(a==b for a,b in zip(words,truth))==103 and same_functions(baseline,candidate,('func_150C8350',))==18 and normalized_pools(baseline)==normalized_pools(candidate) and bd==cd==''
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
for name in ('guard','behavior','controls','alias','self_alias','caller','fault','native','padder','image'):
 subprocess.run([sys.executable,'-m','tools.tests.game_motion_table_150c8350_'+name],cwd=root,env=env,check=True)
print('motion table private qualification passed; candidate remains uncredited',flush=True)
