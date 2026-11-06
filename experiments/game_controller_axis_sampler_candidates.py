"""Signed controller-axis sampling with the retail constant-allocation profile."""
from pathlib import Path
import subprocess
from unittest.mock import patch
from tools.experiments.game_remaining_donor_candidates import compile_owner as base_compile_owner
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1503F9F0','generated_6CEA0'
SOURCE,ASM='conker/src/game/generated_6CEA0.c','conker/asm/6CEA0.s'
BUILD='conker/build/game-controller-axis-sampler-1503F9F0-match'
ENTRY,ROM,WORDS=0x1503F9F0,0x6CEA0,70
OLD='s32 func_1503F9F0() {\n    return 0;\n}'
HEADERS='typedef struct ControllerAxes1503F9F0 { u16 buttons; s8 x, y; } ControllerAxes1503F9F0;\nextern ControllerAxes1503F9F0 **D_800BE728;\nextern s16 D_80084484;\n'
SELECTED='/* Sample the controller axes every fifth tick, consuming movement outside the dead zone. */\nvoid func_1503F9F0(s16 slot, s16 *x, s16 *y) {\n    s16 countdown;\n    ControllerAxes1503F9F0 *pad;\n    s32 value;\n\n    pad = D_800BE728[slot];\n    countdown = D_80084484 - 1;\n    if (countdown != 0) {\n        D_80084484 = countdown;\n        *x = 0;\n        *y = 0;\n    } else {\n        /* The table lookup has consumed slot; reuse its signed local for X. */\n        slot = pad->x;\n        D_80084484 = 5;\n        if (slot < -20 || slot > 20) {\n            *x = slot;\n        } else {\n            *x = 0;\n        }\n        value = pad->y;\n        if (value < -20 || value > 20) {\n            *y = value;\n        } else {\n            *y = 0;\n        }\n        pad->x = 0;\n        pad->y = 0;\n        *x = *x < -1 ? -1 : *x > 1 ? 1 : *x;\n        *y = *y < -1 ? -1 : *y > 1 ? 1 : *y;\n    }\n}'
NEW=HEADERS+SELECTED
PROFILE=('-O2','-g3','-Wo,-no_const_in_reg')
MAKE='conker/Makefile'
MAKE_MARKER='$(BUILD_DIR)/$(SRC_DIR)/game/generated_21D420.c.o: OPT_FLAGS := -O2'
MAKE_ADDITION='# Preserve immediate countdown addresses in the controller sampler.\n$(BUILD_DIR)/$(SRC_DIR)/game/generated_6CEA0.c.o: CFLAGS += -Wo,-no_const_in_reg\n'
def source_states(live):
    if live.count(OLD)==1 and NEW not in live:return live,live.replace(OLD,NEW,1),False
    if live.count(NEW)==1 and OLD not in live:return live.replace(NEW,OLD,1),live,True
    raise ValueError('Controller sampler source state changed')
def make_states(live):
    if live.count(MAKE_MARKER)!=1:raise ValueError('Controller sampler Make profile anchor changed')
    if MAKE_ADDITION not in live:return live,live.replace(MAKE_MARKER,MAKE_ADDITION+MAKE_MARKER,1),False
    if live.count(MAKE_ADDITION)==1:return live.replace(MAKE_ADDITION,'',1),live,True
    raise ValueError('Controller sampler Make profile changed')
def compile_owner(root,out,source,name,flags=PROFILE):
    actual=subprocess.run
    def run(argv,**kwargs):
        if any(str(a).endswith('/asm_processor.py')for a in argv):argv=[a for a in argv if not str(a).startswith('-Wo,')]
        return actual(argv,**kwargs)
    with patch.object(subprocess,'run',run):return base_compile_owner(root,out,source,name,flags=flags)
