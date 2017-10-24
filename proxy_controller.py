from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.packet import packet, ethernet, tcp, ipv4

import array

# Act as Proxy that redirects all traffic for 10.0.0.2:5000 to 10.0.0.3:7000
# *** It is assumed that the CAM table has the records for the respective MAC Addresses
# **** Hence some corresponding MAC are hard coded in some parts of the implementation below

class L2Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        self.mac_table = dict()
        super(L2Switch, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        pkt = packet.Packet(array.array('B', event.msg.data))

        etherFrame = pkt.get_protocol(ethernet.ethernet)
        ipPacket = pkt.get_protocol(ipv4.ipv4)
        tcpSegment = pkt.get_protocol(tcp.tcp)

        if etherFrame.src not in self.mac_table:
            self.mac_table[etherFrame.src] = event.msg.in_port
            print ("Adding {} into MAC table".format(etherFrame.src))

        dp = event.msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        if etherFrame.dst in self.mac_table:
            if not tcpSegment == None and not ipPacket == None:
                if tcpSegment.dst_port == 5000 and ipPacket.dst == '10.0.0.2':
                    actions = [ofp_parser.OFPActionSetTpDst(tp=7000),
                               ofp_parser.OFPActionSetNwDst(nw_addr='10.0.0.3'),
                               ofp_parser.OFPActionSetDlDst(dl_addr='00:00:00:00:00:03'),
                               ofp_parser.OFPActionOutput(port=self.mac_table['00:00:00:00:00:03'])]

                elif tcpSegment.src_port == 7000 and ipPacket.src == '10.0.0.3':
                    actions = [ofp_parser.OFPActionSetTpSrc(tp=5000),
                               ofp_parser.OFPActionSetNwSrc(nw_addr='10.0.0.2'),
                               ofp_parser.OFPActionSetDlSrc(dl_addr='00:00:00:00:00:02'),
                               ofp_parser.OFPActionOutput(port=self.mac_table['00:00:00:00:00:01'])]
                else:
                    actions = [ofp_parser.OFPActionOutput(port=self.mac_table[etherFrame.dst])]
            else:
                actions = [ ofp_parser.OFPActionOutput(port=self.mac_table[etherFrame.dst])]
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