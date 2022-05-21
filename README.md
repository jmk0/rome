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


**Use relative E distances**

Printer Settings->General->Advanced

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_advanced.jpg" alt="" width="320"/>


**Activate additional extruders**

Printer Settings->General->Capabilities

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_capabilities.jpg" alt="" width="387"/>


**Dectivate all multi material parameters**

Printer Settings->Single extruder MM setup->Single extruder multi material parameters

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_mmu_parameters.jpg" alt="" width="407"/>


**Dectivate advanced wiping volume**

Printer Settings->Single extruder MM setup->Advanced wipe tower purge volume calculs

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_wiping_volume.jpg" alt="" width="462"/>


**Dectivate advanced wiping volume**

Printer Settings->General->Advanced wipe tower pure volume calculs

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_wiping_volume.jpg" alt="" width="462"/>


**Dectivate toolchange temperature**

Filament Settings->Multimaterial->Multimaterial toolchange temperature

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_toolchange_temperature.jpg" alt="" width="400"/>


**Dectivate skinnydip string reduction**

Filament Settings->Multimaterial->Multimaterial toolchange string reduction

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_dip.jpg" alt="" width="454"/>


**Dectivate cooling moves and ramming**

Filament Settings->Multimaterial->Multimaterial parameters with single extruder MM printers

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_toolchange_parameters.jpg" alt="" width="400"/>

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_ramming.jpg" alt="" width="764"/>


**Enable wipe tower**

Print Settings->multiple extruders->Wipe tower

<img src="https://github.com/HelgeKeck/rome/blob/main/img/slicer_wipe_tower.jpg" alt="" width="584"/>


## Classic

The Rome Classic Mode works exactly like the MMU or ERCF. You are responsible to configure the Slicer proeprly.

```ini
# ROME
[include rome/config.cfg]
```
