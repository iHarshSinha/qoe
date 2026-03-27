#!/usr/bin/env python3
"""
Enhanced QoE traffic generation script.
Simulates video, audio, FTP, and browsing traffic across the topology
and records QoS + QoA + Video features matching the VLC-QoS-QoEIF dataset schema.

Fix: UDP jitter and loss are read from the iperf SERVER log (not client),
     since iperf only reports those metrics on the receiver side.

Output: qoe_metrics.csv
"""

import csv
import time
import re
from mininet.net import Mininet
from mininet.node import OVSController, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.clean import cleanup

# Traffic profiles
# QoA and Video features are stream properties — they describe what kind of
# content is being sent, not measured by iperf. Values below are realistic
# defaults per traffic type, matching the dataset's VLC indicator ranges.
# 
TRAFFIC_PROFILES = {
    "video_sd": {
        "proto": "udp", "bw": "2M", "duration": 20,
        "V_content": "video", "V_norm_bitrate": 2000, "V_complexity": 3, "V_complexity_class": "medium",
        "QoA_resolution": "640x480", "QoA_bitrate": 2000, "QoA_frame_rate": 25,
        "QoA_frame_drop": 0, "QoA_audio_rate": 128, "QoA_audio_drop": 0,
    },
    "video_hd": {
        "proto": "udp", "bw": "8M", "duration": 20,
        "V_content": "video", "V_norm_bitrate": 8000, "V_complexity": 5, "V_complexity_class": "high",
        "QoA_resolution": "1280x720", "QoA_bitrate": 8000, "QoA_frame_rate": 30,
        "QoA_frame_drop": 0, "QoA_audio_rate": 192, "QoA_audio_drop": 0,
    },
    "voip": {
        "proto": "udp", "bw": "64K", "duration": 20,
        "V_content": "audio", "V_norm_bitrate": 64, "V_complexity": 1, "V_complexity_class": "low",
        "QoA_resolution": "N/A", "QoA_bitrate": 64, "QoA_frame_rate": 0,
        "QoA_frame_drop": 0, "QoA_audio_rate": 64, "QoA_audio_drop": 0,
    },
    "ftp": {
        "proto": "tcp", "bw": "10M", "duration": 20,
        "V_content": "file_transfer", "V_norm_bitrate": 10000, "V_complexity": 2, "V_complexity_class": "low",
        "QoA_resolution": "N/A", "QoA_bitrate": 10000, "QoA_frame_rate": 0,
        "QoA_frame_drop": 0, "QoA_audio_rate": 0, "QoA_audio_drop": 0,
    },
    "browsing": {
        "proto": "tcp", "bw": "512K", "duration": 20,
        "V_content": "http", "V_norm_bitrate": 512, "V_complexity": 1, "V_complexity_class": "low",
        "QoA_resolution": "N/A", "QoA_bitrate": 512, "QoA_frame_rate": 0,
        "QoA_frame_drop": 0, "QoA_audio_rate": 0, "QoA_audio_drop": 0,
    },
}

CSV_FIELDS = [
    # Identifiers
    "timestamp", "test_name", "src_host", "dst_host", "traffic_type",
    # QoS features (dataset columns)
    "QoS_bandwidth", "QoS_packet-loss", "QoS_delay", "QoS_jitter",
    # Video / content features
    "V_content", "V_norm-bitrate", "V_complexity", "V_complexity-class",
    # QoA features
    "QoA_resolution", "QoA-bitrate", "QoA-frame_rate",
    "QoA_frame-drop", "QoA_audio-rate", "QoA_audio-drop",
]

def parse_iperf_udp(output):
    """
    Parse iperf UDP output in -y C (CSV) format.
    Jitter and loss are only present in the SERVER summary line.
    Format: timestamp,src_ip,src_port,dst_ip,dst_port,id,interval,
            bytes,bps,jitter_ms,lost,total,loss_pct,out_of_order
    Returns dict with bps, jitter, loss_pct or None on failure.
    """
    lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
    for line in reversed(lines):
        # skip header or non-data lines
        if line.startswith("----") or line.lower().startswith("timestamp"):
            continue
        parts = line.split(",")
        if len(parts) >= 13:
            try:
                bps      = float(parts[8])
                jitter   = float(parts[9])
                loss_pct = float(parts[12])
                # basic sanity check
                if bps >= 0 and jitter >= 0 and 0 <= loss_pct <= 100:
                    return {"bps": bps, "jitter": jitter, "loss_pct": loss_pct}
            except (ValueError, IndexError):
                continue
    return None


def parse_iperf_tcp(output):
    """
    Parse iperf TCP plain-text output for bandwidth.
    Returns dict with bps or None.
    """
    match = re.search(r"(\d+\.?\d*)\s+([KMG]?)bits/sec", output)
    if match:
        val  = float(match.group(1))
        unit = match.group(2)
        multipliers = {"K": 1e3, "M": 1e6, "G": 1e9, "": 1.0}
        return {"bps": val * multipliers.get(unit, 1.0)}
    return None


def measure_delay(src_host, dst_ip, count=10):
    """Ping and return average RTT in ms, or None on failure."""
    out = src_host.cmd(f"ping -c {count} -q {dst_ip}")
    match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/", out)
    if match:
        return float(match.group(1))
    return None


def run_test(src, dst_host, profile_name, test_name, writer):
    """Run a single iperf test and write one row to the CSV."""
    profile = TRAFFIC_PROFILES[profile_name]
    dst_ip  = dst_host.IP()
    proto   = profile["proto"]
    bw      = profile["bw"]
    dur     = profile["duration"]

    info(f"    [{test_name}] {src.name} -> {dst_host.name} | {profile_name} | {bw}\n")

    # Start server
    # For UDP: server writes CSV output to a log file so we can read
    # jitter + loss from it after the client finishes.
    # For TCP: plain text output is enough for bandwidth.
    dst_host.cmd("kill %iperf 2>/dev/null; sleep 0.5")
    if proto == "udp":
        dst_host.cmd("iperf -s -u -y C > /tmp/iperf_server.log 2>&1 &")
    else:
        dst_host.cmd("iperf -s > /tmp/iperf_server.log 2>&1 &")
    time.sleep(1)  # let server start up

    # Run client
    # UDP client: plain output
    # TCP client: plain output for bandwidth parsing
    if proto == "udp":
        client_cmd = f"iperf -c {dst_ip} -u -b {bw} -t {dur}"
    else:
        client_cmd = f"iperf -c {dst_ip} -t {dur}"

    src.cmd(client_cmd)
    time.sleep(1)  # give server time to flush and write final summary

    # Measure delay via ping
    delay = measure_delay(src, dst_ip, count=10)

    # Parse stats 
    server_out = dst_host.cmd("cat /tmp/iperf_server.log")

    if proto == "udp":
        # Read jitter + loss from SERVER log
        stats = parse_iperf_udp(server_out)
        if stats:
            bandwidth = round(stats["bps"] / 1e6, 4)   # convert bps -> Mbps
            jitter    = round(stats["jitter"], 4)        # ms
            loss      = round(stats["loss_pct"], 4)      # %
        else:
            info(f"    [WARN] Could not parse UDP server output for {test_name}\n")
            info(f"    Server output was: {server_out[:300]}\n")
            bandwidth, jitter, loss = None, None, None
    else:
        # TCP: parse bandwidth from server log
        stats = parse_iperf_tcp(server_out)
        bandwidth = round(stats["bps"] / 1e6, 4) if stats else None
        jitter    = 0.0   # TCP doesn't report jitter
        loss      = 0.0   # TCP doesn't report packet loss

    # Estimate QoA frame/audio drops from measured packet loss
    frame_drop = profile["QoA_frame_drop"]
    audio_drop = profile["QoA_audio_drop"]

    if loss is not None and loss > 0:
        if profile["QoA_frame_rate"] > 0:
            # approximate frames dropped over the test duration
            frame_drop = round((loss / 100) * profile["QoA_frame_rate"] * dur)
        if profile["QoA_audio_rate"] > 0:
            # audio drop as a percentage of audio packets
            audio_drop = round(loss)

    # Write CSV row 
    row = {
        "timestamp":          time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_name":          test_name,
        "src_host":           src.name,
        "dst_host":           dst_host.name,
        "traffic_type":       profile_name,
        "QoS_bandwidth":      bandwidth,
        "QoS_packet-loss":    loss,
        "QoS_delay":          delay,
        "QoS_jitter":         jitter,
        "V_content":          profile["V_content"],
        "V_norm-bitrate":     profile["V_norm_bitrate"],
        "V_complexity":       profile["V_complexity"],
        "V_complexity-class": profile["V_complexity_class"],
        "QoA_resolution":     profile["QoA_resolution"],
        "QoA-bitrate":        profile["QoA_bitrate"],
        "QoA-frame_rate":     profile["QoA_frame_rate"],
        "QoA_frame-drop":     frame_drop,
        "QoA_audio-rate":     profile["QoA_audio_rate"],
        "QoA_audio-drop":     audio_drop,
    }
    writer.writerow(row)

    # Kill server
    dst_host.cmd("kill %iperf 2>/dev/null")
    time.sleep(2)


def run():
    info("*** Cleaning up previous Mininet state\n")
    cleanup()

    net = Mininet(controller=OVSController, switch=OVSKernelSwitch,
                  link=TCLink, autoSetMacs=True)
    net.addController("c0")

    # Hosts
    hA = net.addHost("hA", ip="10.0.0.1/24")
    hB = net.addHost("hB", ip="10.0.0.2/24")
    hC = net.addHost("hC", ip="10.0.0.3/24")
    hD = net.addHost("hD", ip="10.0.0.4/24")
    hE = net.addHost("hE", ip="10.0.0.5/24")
    hF = net.addHost("hF", ip="10.0.0.6/24")
    hG = net.addHost("hG", ip="10.0.0.7/24")

    # Switches
    s1, s2, s3 = net.addSwitch("s1"), net.addSwitch("s2"), net.addSwitch("s3")
    s4, s5, s6 = net.addSwitch("s4"), net.addSwitch("s5"), net.addSwitch("s6")

    # Links
    net.addLink(hA, s1, bw=20,  delay="5ms",  loss=1,  max_queue_size=100)
    net.addLink(hB, s1, bw=15,  delay="2ms",  loss=0,  max_queue_size=50)
    net.addLink(hC, s1, bw=10,  delay="8ms",  loss=2,  max_queue_size=80)
    net.addLink(s1, s2, bw=10,  delay="8ms",  loss=2,  max_queue_size=80)
    net.addLink(s2, s3, bw=40,  delay="12ms", loss=1,  max_queue_size=180)
    net.addLink(hD, s3, bw=25,  delay="3ms",  loss=1,  max_queue_size=120)
    net.addLink(s2, s4, bw=60,  delay="7ms",  loss=35, max_queue_size=250)
    net.addLink(s4, s5, bw=45,  delay="9ms",  loss=2,  max_queue_size=160)
    net.addLink(hE, s5, bw=30,  delay="1ms",  loss=0,  max_queue_size=150)
    net.addLink(hF, s5, bw=18,  delay="4ms",  loss=1,  max_queue_size=90)
    net.addLink(s5, s6, bw=10,  delay="8ms",  loss=2,  max_queue_size=80)
    net.addLink(hG, s6, bw=35,  delay="15ms", loss=10, max_queue_size=140)

    info("*** Starting network\n")
    net.start()
    time.sleep(2)

    # Test plan
    # (src, dst, profile, label)
    # Paths chosen to exercise different parts of the topology:
    #   hD->hE / hA->hG : cross the high-loss s2->s4 backbone (35% loss)
    #   hA->hD           : clean short path via s1-s2-s3
    #   hF->hE           : same switch s5, minimal hops
    tests = [
        # hD -> hE  (via s3-s2-s4-s5, crosses high-loss backbone)
        (hD, hE, "video_sd",  "hD_hE_SD_video"),
        (hD, hE, "video_hd",  "hD_hE_HD_video"),
        (hD, hE, "voip",      "hD_hE_VoIP"),
        (hD, hE, "ftp",       "hD_hE_FTP"),

        # hA -> hG  (longest path, s1-s2-s4-s5-s6)
        (hA, hG, "video_sd",  "hA_hG_SD_video"),
        (hA, hG, "video_hd",  "hA_hG_HD_video"),
        (hA, hG, "browsing",  "hA_hG_browsing"),

        # hB -> hG  (same backbone, no loss on hB-s1 link)
        (hB, hG, "video_hd",  "hB_hG_HD_video"),
        (hB, hG, "ftp",       "hB_hG_FTP"),

        # hA -> hD  (short clean path via s1-s2-s3, low loss)
        (hA, hD, "video_sd",  "hA_hD_SD_video"),
        (hA, hD, "ftp",       "hA_hD_FTP"),
        (hC, hD, "browsing",  "hC_hD_browsing"),

        # hF -> hE  (same switch s5, minimal path)
        (hF, hE, "voip",      "hF_hE_VoIP"),
        (hF, hE, "video_sd",  "hF_hE_SD_video"),
    ]

    output_file = "qoe_metrics.csv"
    info(f"*** Writing results to {output_file}\n")

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for src, dst, profile, label in tests:
            run_test(src, dst, profile, label, writer)

    info(f"\n*** All tests complete. Results saved to {output_file}\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run()
