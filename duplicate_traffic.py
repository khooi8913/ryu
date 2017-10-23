from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.packet import packet, ethernet

import array

class L2Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        self.mac_table = dict()
        super(L2Switch, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        pkt = packet.Packet(array.array('B', event.msg.data))
        etherFrame = pkt.get_protocol(ethernet.ethernet)
        if etherFrame.src not in self.mac_table:
            self.mac_table[etherFrame.src] = event.msg.in_port
            print ("Adding {} into MAC table".format(etherFrame.src))

        dp = event.msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        # Forward and duplicate traffic
        if etherFrame.dst in self.mac_table:
            actions = [ofp_parser.OFPActionOutput(port=self.mac_table[etherFrame.dst]), ofp_parser.OFPActionOutput(port=3)]
            print("Destination MAC {} found in MAC table!".format(etherFrame.src))
        else:
            actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
            print("Frame flooded to all other ports.")

        out = ofp_parser.OFPPacketOut(
            datapath = dp,
            buffer_id = event.msg.buffer_id,
            in_port = event.msg.in_port,
            actions = actions
        )
        dp.send_msg(out)