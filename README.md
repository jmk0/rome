# ROME
RatOS Multi Extruder

A multi extruder to direct extruder solution for RatOS

## Table of Content
- [Installation](#installation)
  - [Raspberry](#raspberry)
  - [Moonraker](#moonraker)
  - [Klipper](#klipper)
 
# Installation

## Raspberry
```
cd ~/
git clone https://github.com/HelgeKeck/rome.git
bash ~/rome/install.sh
```

## Moonraker
```ini
[update_manager rome]
type: git_repo
primary_branch: main
path: ~/rome
origin: https://github.com/HelgeKeck/rome.git
```

## Klipper 
```ini
# ROME
[include rome/config.cfg]
```
