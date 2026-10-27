# Experiment playbook — any device

1. **Profile**: `python3 scripts/device-profile.py show generic`; create a new profile for researched device, validate it, then set `TARGET_PROFILE` and `TARGET_IP` in `.env`.
2. **Baseline**: Observe DNS and network flows on a genuinely visible gateway/TAP, not just from a Docker bridge.
3. **Hypothesis**: `python3 scripts/labctl.py start "boot baseline" "Expect DNS discovery"`. Save returned experiment ID.
4. **Single controlled change**: With permission, change one lab-owned DNS name or mock response. Do not change a production router configuration or shared DNS records.
5. **Collect**: After ending PCAP capture, run `bash scripts/analyze-now.sh`. Read Zeek summaries and correlate with API events.
6. **Compare and report**: Finish the experiment, compare experiment IDs using `scripts/labctl.py compare`, then `python3 scripts/generate-findings.py`.
7. **Rollback**: `python3 scripts/labctl.py rollback EXPERIMENT_ID`, then disable profile-specific DNS rewrites if needed.

Stateful mock scenarios live in `config/scenarios.json`, ordinary API response hypotheses in `config/rules.json`. For firmware experiments, put authorized binaries into `firmware/` and use optional Ghidra. The TCP/UDP packet capture, local test certificates, and mock replies do not constitute a vendor cloud backend.
