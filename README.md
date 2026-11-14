# Pygmy

## Architecture

```mermaid
flowchart LR
    subgraph MCU["STM32 MCU (Arduino)"]
        Thermo["Modulino Thermo\n(Temp & %RH)"]
        Buzzer["Modulino Buzzer\n(1412 Hz Owl Call)"]
    end

    subgraph Linux["QRB2210 Linux (Python)"]
        Mic["USB Mic"] --> BirdNET["BirdNET AI\n(3s chunks)"]
        Timer["60s Timer"] -->|Bridge RPC| Buzzer
        BirdNET -->|All birds| DB[("birds.db")]
        BirdNET -->|Endangered species| Trigger["Lure + 5s Burst"]
        Trigger -->|Bridge RPC| Buzzer
        Trigger --> Cam["USB Camera\n(2 fps × 5s)"]
        Thermo -.->|Safe weather & metadata| Trigger
        Cam --> Zip["captures/*.zip\n(10 JPGs + metadata.json)"]
    end
```

## Project Structure

```text
├── app.yaml
├── sketch/
│   ├── sketch.ino
│   └── sketch.yaml
├── python/
│   └── main.py
├── sync-to-board.sh      # Push local git repo changes to the connected UNO Q
└── sync-from-board.sh    # Pull changes made in Arduino App Lab back to local git repo
```

##  Workflow

1. **Pull latest changes from GitHub:**
   ```bash
   git pull
   ```
2. **Push code from your laptop to the connected Arduino UNO Q:**
   ```bash
   ./sync-to-board.sh
   ```
3. **If you edited code inside the Arduino App Lab GUI, pull it back before committing:**
   ```bash
   ./sync-from-board.sh
   git add -A && git commit -m "Update" && git push
   ```
