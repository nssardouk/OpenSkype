#!/usr/bin/python

from rc4 import RC4_Engine
from pcap import pcapObject
from dpkt.ethernet import *
from dpkt.ip import *
from dpkt.udp import *
from skypeudp import *
#from objects import ObjectListFrame
from utils import *

#from ports import *
kazaa = 1214

#-----------------------------------------------------------------
# SkypeUDP dissection - section
#-----------------------------------------------------------------

print_PAYLOAD		= True
print_RESEND		= True
print_CRCERR		= True
print_CRCERR_RESEND	= True
print_AUDIO		= True
print_FRAGMENT		= True

counter = 1
rc4 = RC4_Engine()

def iterate(pktlen, data, timestamp):
	global counter
	global ExternalIP
	pkt = Ethernet(data)
	if pkt.type == ETH_TYPE_IP:
		ip = pkt.data
		if ip.p == IP_PROTO_UDP:
			udp = ip.data
#			if ord(udp.data[2]) & 0x0F in SKYPEUDP_TYPES_RECOGNIZED:
			if len(udp.data) > 3 and udp.sport not in [53, 137, 138, 5351, 5353, 1900, kazaa] and udp.dport not in [53, 137, 138, 5351, 5353, 1900, kazaa]:
				header = SkypeUDP(udp.data)
				objectid = hex(ord(header.objectid[0]))[2:].zfill(2) + hex(ord(header.objectid[1]))[2:].zfill(2)
				t = header.type & 0x0F
				print '-'*100
				print '#'+str(counter).ljust(4)+':\tSkype-UDP (object 0x'+objectid+', flags '+int2bin(header.type >> 4).zfill(4)+') from '+print_address(ip.src)+':'+str(udp.sport).ljust(5)+' to '+print_address(ip.dst)+':'+str(udp.dport).ljust(5)

				if t == SKYPEUDP_TYPE_PAYLOAD:

					frame = ObjectListFrame(header.data)

					if print_PAYLOAD:
						print '\tPAYLOAD: iv='+str2hex(frame.iv)+', CRC='+str2hex(frame.crc)+', +'+str(len(frame.data))+' bytes.'
						plaintext = rc4.decrypt(frame.data, ip.src, ip.dst, header.objectid, frame.iv, frame.crc)	# decrypt


				elif t == SKYPEUDP_TYPE_RESEND:

					resend = Resend(header.data)

					if print_RESEND:
						print '\tRESEND, retry no. '+str(resend.number)+', ivseed='+str2hex(resend.ivseed)+', unknown='+str2hex(resend.unknown)+', CRC='+str2hex(resend.crc)+', +'+str(len(resend.data))+' bytes.'
						plaintext = rc4.bruteforce(resend.data, crc=str2hex(resend.crc), start=str2long(resend.ivseed) & 0xFFFF0000)

				elif t == SKYPEUDP_TYPE_CRCERR:

					nat = CrcError(header.data)

					if ip.dst[0:2] == chr(192)+chr(168) or ip.dst[0:2] == rc4.ExternalIP[0:2]:	# error received, not sent
						rc4.updateIP(nat.yourip)

					if print_CRCERR:
						print '\tCRC error: your IP address: '+print_address(nat.yourip)+', a seed for you='+str2hex(nat.ivseed)

				elif t == SKYPEUDP_TYPE_CRCERR_RESEND:

					nat = CrcError(header.data)

					if ip.dst[0:2] == chr(192)+chr(168) or ip.dst[0:2] == rc4.ExternalIP[0:2]:	# error received, not sent
						rc4.updateIP(nat.yourip)
					
					if print_CRCERR_RESEND:
						print '\tCRC error: please repeat; your IP address: '+print_address(nat.yourip)+', please use this final seed='+str2hex(nat.ivseed)

				elif t == SKYPEUDP_TYPE_AUDIO:

					if print_AUDIO:
						print '\tAUDIO STREAM: '+str(len(header.data))+' bytes.'

				elif t == SKYPEUDP_TYPE_FRAGMENT:

					if print_FRAGMENT:
						frag = Fragment(header.data)

						last = frag.flag >> 4 == 0x8

						print '\tFragment: in reply to your request object 0x'+str2hex(frag.inreplyto)+'. fragment number: '+hex(frag.flag & 0x0F)+', is last fragment: '+str(last)+'.'
						print '\tmagic 0x02='+hex(frag.magic)+'. iv='+str2hex(frag.iv)+'. crc='+str2hex(frag.crc)+'. +'+str(len(frag.data))+' bytes.'

						plaintext = rc4.decrypt(frag.data, ip.src, ip.dst, header.objectid, frag.iv, frag.crc)	# decrypt

				else:
					print 'UNKNOWN ('+hex(t)+'), '+str(len(header.data))+' bytes follow'
				print
	counter += 1

import sys

try:
	fname = sys.argv[1]
except:
	fname = 'SkypeIRC.cap'

p = pcapObject()
p.open_offline (fname)
p.loop(0, iterate)


#-----------------------------------------------------------------
# SkypeTCP dissection - section
#-----------------------------------------------------------------

from tcpstreams import TCPStreams, FollowTCPStream, TCPHeader, TCPData

stream = FollowTCPStream(p, TCPStreams(p).filter(dstport=33033) )

def outgoing(pktlen, pkt, timestamp):
	tcp = TCPHeader(pkt)
	data = TCPData(pkt)
	...

def incoming(pktlen, pkt, timestamp):
	tcp = TCPHeader(pkt)
	data = TCPData(pkt)
	...
	
stream.loop(0, outgoing, incoming)

