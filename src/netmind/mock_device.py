"""
MindNet mock device.

Simulates a Cisco IOS device for local development and testing when
NETMIND_MOCK=true is set.  Responses are realistic enough to exercise
the full audit, parse, and explain pipeline without a live device.

To add new mock commands, extend the MOCK_RESPONSES dict below.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Realistic mock output for a Cisco IOS router / switch
# ---------------------------------------------------------------------------

MOCK_RESPONSES: dict[str, str] = {

    "show version": """\
Cisco IOS Software, Version 15.6(3)M, RELEASE SOFTWARE (fc1)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2017 by Cisco Systems, Inc.
Compiled Thu 23-Mar-17 16:22 by prod_rel_team

ROM: System Bootstrap, Version 15.6(3)M, RELEASE SOFTWARE (fc1)

Router uptime is 14 days, 6 hours, 48 minutes
System returned to ROM by power-on
System image file is "flash:c2900-universalk9-mz.SPA.156-3.M.bin"

cisco CISCO2921/K9 (revision 1.0) with 512000K/33792K bytes of memory.
Processor board ID FTX1524BGU7
4 Gigabit Ethernet interfaces
DRAM configuration is 64 bits wide with parity disabled.
255K bytes of non-volatile configuration memory.
255M bytes of ATA System CompactFlash 0 (Read/Write)

License Level: adventerprisek9
License Type: Permanent Right-To-Use
Next reload license Level: adventerprisek9

Configuration register is 0x2102
""",

    "show ip interface brief": """\
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     192.168.1.1     YES NVRAM  up                    up
GigabitEthernet0/1     10.0.0.1        YES NVRAM  up                    up
GigabitEthernet0/2     unassigned      YES NVRAM  administratively down down
GigabitEthernet0/3     unassigned      YES NVRAM  down                  down
Loopback0              1.1.1.1         YES NVRAM  up                    up
Tunnel0                172.16.0.1      YES manual up                    up
""",

    "show interfaces status": """\
Port      Name               Status       Vlan       Duplex  Speed Type
Gi0/0                        connected    routed     a-full  1G    RJ45
Gi0/1                        connected    routed     a-full  1G    RJ45
Gi0/2                        disabled     1          auto    auto  RJ45
Gi0/3                        notconnect   1          auto    auto  RJ45
""",

    "show cdp neighbors": """\
Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,
                  D - Remote, C - CVTA, M - Two-port Mac Relay

Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
SW-CORE-01       Gig 0/0           148         S I        WS-C3750  Gig 1/0/1
""",

    "show ip route": """\
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       o - ODR, P - periodic downloaded static route, H - NHRP, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR

Gateway of last resort is 192.168.1.254 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 192.168.1.254
      1.0.0.0/32 is subnetted, 1 subnets
C        1.1.1.1 is directly connected, Loopback0
      10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
C        10.0.0.0/30 is directly connected, GigabitEthernet0/1
L        10.0.0.1/32 is directly connected, GigabitEthernet0/1
      192.168.1.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.1.0/24 is directly connected, GigabitEthernet0/0
L        192.168.1.1/32 is directly connected, GigabitEthernet0/0
""",

    "show interfaces": """\
GigabitEthernet0/0 is up, line protocol is up
  Hardware is CN Gigabit Ethernet, address is aabb.cc00.0100
  Internet address is 192.168.1.1/24
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Full Duplex, 1000Mbps, media type is RJ45
  Input errors: 0, CRC: 0, frame: 0, overrun: 0, ignored: 0
  Output errors: 0, collisions: 0, interface resets: 2

GigabitEthernet0/3 is down, line protocol is down
  Hardware is CN Gigabit Ethernet, address is aabb.cc00.0400
  MTU 1500 bytes, BW 10000 Kbit/sec, DLY 1000 usec,
     reliability 0/255, txload 1/255, rxload 1/255
  Input errors: 147, CRC: 32, frame: 0, overrun: 0, ignored: 0
  Output errors: 0, collisions: 0, interface resets: 9
""",

    # Edge-case: err-disabled port (used for testing critical findings)
    "show interfaces gi0/3": """\
GigabitEthernet0/3 is err-disabled
  Hardware is CN Gigabit Ethernet, address is aabb.cc00.0400
  MTU 1500 bytes, BW 10000 Kbit/sec, DLY 1000 usec,
     reliability 0/255, txload 1/255, rxload 1/255
  Input errors: 147, CRC: 32, frame: 0, overrun: 0, ignored: 0
""",
}

_UNKNOWN_CMD_TEMPLATE = """\
                    ^
% Invalid input detected at '^' marker.
"""


def _load_mock_data_files() -> dict[str, str]:
    """
    Load additional mock responses from `mock_data/*.txt`.

    File names map to commands using `__` as space separators.
    Example: `show__ip__route.txt` -> `show ip route`.
    """
    base_dir = Path(__file__).resolve().parents[2]
    data_dir = base_dir / "mock_data"
    responses: dict[str, str] = {}

    if not data_dir.exists():
        return responses

    for file_path in data_dir.glob("*.txt"):
        command = file_path.stem.replace("__", " ").strip().lower()
        if not command:
            continue
        responses[command] = file_path.read_text(encoding="utf-8")
    return responses


FILE_MOCK_RESPONSES = _load_mock_data_files()


class MockDevice:
    """
    Simulates a Cisco IOS SSH session for local testing.

    Accepts the same interface as a Netmiko BaseConnection object so it
    can be used as a drop-in replacement inside open_connection().
    """

    def __init__(self, host: str) -> None:
        self.host = host

    def send_command(self, command: str, **kwargs) -> str:
        """Return canned output for known commands; IOS error for unknown ones."""
        key = command.strip().lower()

        # Prefer file-based mock responses so users can customize without code edits.
        for mock_cmd, output in FILE_MOCK_RESPONSES.items():
            if key == mock_cmd:
                return output
        for mock_cmd, output in FILE_MOCK_RESPONSES.items():
            if key.startswith(mock_cmd):
                return output

        # Try exact match first, then prefix match
        for mock_cmd, output in MOCK_RESPONSES.items():
            if key == mock_cmd.lower():
                return output
        # Partial / prefix match for convenience
        for mock_cmd, output in MOCK_RESPONSES.items():
            if key.startswith(mock_cmd.lower()):
                return output
        return _UNKNOWN_CMD_TEMPLATE

    def disconnect(self) -> None:
        """No-op disconnect for the mock."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.disconnect()
