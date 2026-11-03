"""Configured semantic oracle for func_151AF5C0's transformed-height probe."""

from pathlib import Path

from tools.tests import game_transformed_height_probe_oracle as base


ROOT = Path.cwd()
OUTPUT = ROOT / "conker/build/game-late-transformed-height-probe-151AF5C0-match"


def configure():
    base.ROOT = ROOT
    base.OUTPUT = OUTPUT
    base.FUNCTION = "func_151AF5C0"
    base.ENTRY = 0x151AF5C0
    base.ROM = 0x1DCA70
    base.WORDS = 64
    base.POINT_RIGHT = 0x800AA0F0
    base.POINT_LEFT = 0x800AA0FC
    base.POINT_RIGHT_NAME = "D_800AA0F0"
    base.POINT_LEFT_NAME = "D_800AA0FC"
    base.MODE_ONE_OFFSET = 0x800
    base.MODE_TWO_OFFSET = 0x640
    base.OWNER_OBJECT = "generated_1DCA70.c.o"
    base.SYMBOLS = {
        "D_800AA0F0": base.POINT_RIGHT,
        "D_800AA0FC": base.POINT_LEFT,
        "func_15143134": base.TRANSFORM,
        "func_1504715C": base.INITIALIZE,
        "func_15046C80": base.QUERY,
    }


def run_suite():
    configure()
    return base.run_suite()


def run_native(selected):
    configure()
    return base.run_native(selected)
