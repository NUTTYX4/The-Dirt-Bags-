# Phytora temporary phone test

Use a trusted **Private** Wi-Fi/Ethernet network only. `172.23.208.1` is a WSL virtual adapter and cannot be used by a phone.

1. Confirm the physical network is Private: `Get-NetConnectionProfile`.
2. In an elevated PowerShell, add Private/LocalSubnet-only firewall rules:

```powershell
New-NetFirewallRule -DisplayName 'Phytora frontend LAN test' -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow -Profile Private -RemoteAddress LocalSubnet
New-NetFirewallRule -DisplayName 'CropScope API LAN test' -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private -RemoteAddress LocalSubnet
```

3. In another terminal: `cd frontend; .\start-phone-test.ps1`. It checks the trusted physical network, starts the existing backend and local Gemini bridge, checks readiness, then starts Vite on LAN. It uses Vite's same-origin proxy, so `.env.local` must keep `VITE_API_BASE_URL=` empty rather than hardcoding a laptop IP.

The phone MVP uses the reliable local workflow: select **Tomato** or **Chilli**, then choose **Take photo** or **Choose from gallery**. These are separate native Android inputs, so the camera button opens the camera chooser while the gallery button opens the gallery/file chooser. The selected image is processed only by the corresponding local CropScope model.

No live `getUserMedia` preview is used for the phone MVP, avoiding the HTTPS restriction on a USB/ADB localhost test. Never enable router port forwarding. Shut down with Ctrl+C and remove the two firewall rules when finished.
