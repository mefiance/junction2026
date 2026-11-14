# Pygmy

## Architecture

```mermaid
flowchart TD
    subgraph MCU["STM32 MCU"]
        Thermo["Modulino Thermo"]
        Buzzer["Modulino Buzzer"]
    end
    subgraph Linux["QRB2210 Linux"]
        Mic["USB Mic"] --> BirdNET["BirdNET AI"]
        BirdNET -->|all birds| DB[("birds.db")]
        BirdNET -->|endangered| Trigger["Lure + burst"]
        Trigger --> Buzzer
        Trigger --> Cam["USB Camera"]
        Cam --> Zip["captures.zip"]
    end
    Timer["60s Timer"] --> Buzzer
    Thermo -.-> Trigger
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