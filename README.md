# ROME
RatOS Multi Extruder

A multi extruder to direct extruder solution for RatOS
(Currently limited to 2 Extruders)

## Table of Content
- [Installation](#installation)
    - [Raspberry](#raspberry)
    - [Moonraker](#moonraker)
    - [Klipper](#klipper)
- [Slicer](#slicer)
    - [Native](#native)
    - [Classic](#classic)
 
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

# Slicer 

Rome can operate in two different modes.

## Native 

The Rome Native Mode handles the filament loading and unloading on the Wipe tower. Less Slicer configuration needed and more control over the process.

**Activate additional extruders**

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_capabilities.jpg" alt="" width="387"/>
Printer Settings->General->Capabilities

**Dectivate all multi material parameters**

Make sure to enter 0 in all of these fields.

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_mmu_parameters.jpg" alt="" width="407"/>
Printer Settings->General->Single extruder multi material parameters


## Classic

The Rome Classic Mode works exactly like the MMU or ERCF. You are responsible to configure the Slicer proeprly.

```ini
# ROME
[include rome/config.cfg]
```
