# ROME
RatOS Multi Extruder

A multi extruder to direct extruder solution for RatOS

# Installation

## On your Raspberry
```
cd ~/
git clone https://github.com/HelgeKeck/rome.git
bash ~/rome/install.sh
```

## Configure Moonraker update manager
```ini
# moonraker.conf

[update_manager rome]
type: git_repo
primary_branch: main
path: ~/rome
origin: https://github.com/HelgeKeck/rome.git
```

## Activate ROME in your Klipper printer.cfg 
```ini
# printer.cfg

# ROME
[include rome/config.cfg]

```
