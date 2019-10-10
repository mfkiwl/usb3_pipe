# This file is Copyright (c) 2019 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

from migen import *

from litex.soc.interconnect import stream

from usb3_pipe.lfps import LFPSUnit
from usb3_pipe.training import TSUnit
from usb3_pipe.ltssm import LTSSM
from usb3_pipe.scrambling import Scrambler

# USB3 PIPE ----------------------------------------------------------------------------------------

class USB3PIPE(Module):
    def __init__(self, serdes, sys_clk_freq):
        assert sys_clk_freq > 125e6
        self.enable = Signal(reset=1) # i
        self.ready  = Signal()        # o

        self.sink   = stream.Endpoint([("data", 32), ("ctrl", 4)])
        self.source = stream.Endpoint([("data", 32), ("ctrl", 4)])

        # # #

        # LFPS -------------------------------------------------------------------------------------
        lfps = LFPSUnit(sys_clk_freq=sys_clk_freq, serdes=serdes)
        lfps = ResetInserter()(lfps)
        self.comb += lfps.reset.eq(~self.enable)
        self.submodules.lfps = lfps

        # TS----------------------------------------------------------------------------------------
        ts = TSUnit(serdes=serdes)
        ts = ResetInserter()(ts)
        self.comb += ts.reset.eq(~self.enable)
        self.submodules.ts = ts

        # LTSSM ------------------------------------------------------------------------------------
        ltssm = LTSSM(serdes=serdes, lfps_unit=lfps, ts_unit=ts, sys_clk_freq=sys_clk_freq)
        ltssm = ResetInserter()(ltssm)
        self.comb += ltssm.reset.eq(~self.enable)
        self.submodules.ltssm = ltssm
        self.comb += self.ready.eq(ltssm.polling_fsm.idle)

        # Scrambling -------------------------------------------------------------------------------
        scrambler = Scrambler()
        scrambler = ResetInserter()(scrambler)
        self.comb += scrambler.reset.eq(~self.enable)
        self.submodules.scrambler = scrambler
        self.comb += [
            self.sink.connect(scrambler.sink),
            If(self.ready, scrambler.source.connect(serdes.sink))
        ]

        descrambler = Scrambler()
        descrambler = ResetInserter()(descrambler)
        self.comb += descrambler.reset.eq(~self.enable)
        self.submodules.descrambler = descrambler
        self.comb += [
            If(self.ready, serdes.source.connect(descrambler.sink)),
            descrambler.source.connect(self.source),
        ]
