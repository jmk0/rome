# ROME
RatOS Multi Extruder

A multi extruder to direct extruder solution for RatOS
(Currently limited to 2 Extruders)

## Table of Content
- [Installation](#installation)
    - [Raspberry](#raspberry)
    - [Moonraker](#moonraker)
    - [RatOS](#ratos)
- [Slicer](#slicer)
    - [G-code](#G-code)
    - [Native](#native)
- [Hardware](#hardware)
 
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

## RatOS 
```ini
# ROME
[include rome/config.cfg]
```

# Slicer 

## G-code 

Printer Start G-code
```
ROME_START_PRINT EXTRUDER_TEMP=[first_layer_temperature] BED_TEMP=[first_layer_bed_temperature] TOOL=[initial_tool] WIPE_TOWER={wipe_tower} WIPE_TOWER_X={wipe_tower_x} WIPE_TOWER_Y={wipe_tower_y} WIPE_TOWER_WIDTH={wipe_tower_width} WIPE_TOWER_ROTATION_ANGLE={wipe_tower_rotation_angle} COOLING_TUBE_RETRACTION={cooling_tube_retraction} COOLING_TUBE_LENGTH={cooling_tube_length} PARKING_POS_RETRACTION={parking_pos_retraction} EXTRA_LOADING_MOVE={extra_loading_move}
```

Printer End G-code
```
ROME_END_PRINT
```

Printer Tool change G-code
```
CHANGE_TOOL TOOL=[next_extruder]
```

Filament Start G-code
```
SET_PRESSURE_ADVANCE ADVANCE=0.065 SMOOTH_TIME=0.04
SET_PRESSURE_ADVANCE ADVANCE=0.065 SMOOTH_TIME=0.04 EXTRUDER=rome_extruder_1
SET_PRESSURE_ADVANCE ADVANCE=0.065 SMOOTH_TIME=0.04 EXTRUDER=rome_extruder_2
```

## Rome Modes 

Rome can operate in two different modes, Native and Classic.

The Rome Native Mode handles the filament loading and unloading on the Wipe tower. Faster filament changes, less Slicer configuration needed and more control over the process.

The Rome Classic Mode works exactly like the MMU or ERCF. You are responsible to configure the Slicer proeprly. Configure your slicer like you would do for the MMU or ERCF.

## Native 

**Use relative E distances**

Printer Settings->General->Advanced

<img src="https://github.com/HelgeKeck/rome/blob/main/img/advanced.jpg" alt="" width="320"/>


**Activate additional extruders**

Printer Settings->General->Capabilities

<img src="https://github.com/HelgeKeck/rome/blob/main/img/capabilities.jpg" alt="" width="387"/>


**Dectivate all multi material parameters**

Printer Settings->Single extruder MM setup->Single extruder multi material parameters

<img src="https://github.com/HelgeKeck/rome/blob/main/img/mmu_parameters.jpg" alt="" width="407"/>


**Dectivate advanced wiping volume**

Printer Settings->Single extruder MM setup->Advanced wipe tower purge volume calculs

<img src="https://github.com/HelgeKeck/rome/blob/main/img/wiping_volume.jpg" alt="" width="462"/>


**Dectivate advanced wiping volume**

Printer Settings->General->Advanced wipe tower pure volume calculs

<img src="https://github.com/HelgeKeck/rome/blob/main/img/wiping_volume.jpg" alt="" width="462"/>


**Dectivate toolchange temperature**

Filament Settings->Multimaterial->Multimaterial toolchange temperature

<img src="https://github.com/HelgeKeck/rome/blob/main/img/toolchange_temperature.jpg" alt="" width="400"/>


**Dectivate skinnydip string reduction**

Filament Settings->Multimaterial->Multimaterial toolchange string reduction

<img src="https://github.com/HelgeKeck/rome/blob/main/img/dip.jpg" alt="" width="454"/>


**Dectivate cooling moves and ramming**

Filament Settings->Multimaterial->Multimaterial parameters with single extruder MM printers

<img src="https://github.com/HelgeKeck/rome/blob/main/img/toolchange_parameters.jpg" alt="" width="400"/>

<img src="https://github.com/HelgeKeck/rome/blob/main/img/ramming.jpg" alt="" width="764"/>


**Enable wipe tower**

Print Settings->multiple extruders->Wipe tower

<img src="https://github.com/HelgeKeck/rome/blob/main/img/wipe_tower.jpg" alt="" width="584"/>


# Hardware 

## Primary Extruder

Rome is by default configured to use it with Orbiter Extruders. In case you want to use other extruders you can override these sections in your printer.cfg

```ini
# -------------------------------------										
# Toolhead Extruder 
# -------------------------------------	
[extruder]
max_extrude_only_velocity: 100
max_extrude_only_accel: 1000
max_extrude_only_distance: 400
max_extrude_cross_section: 999999
```

## Secondary Extruders

```ini
# -------------------------------------										
# Rome Extruder 1
# -------------------------------------										
[extruder_stepper rome_extruder_1]
extruder:
step_pin: PG4
dir_pin: !PC1
enable_pin: !PA0
microsteps: 64
rotation_distance: 4.63
full_steps_per_rotation: 200

[tmc2209 extruder_stepper rome_extruder_1]
uart_pin: PC7
stealthchop_threshold: 0
interpolate: False
driver_TBL: 1
driver_TOFF: 3
driver_HEND: 9
driver_HSTRT: 7

# -------------------------------------										
# Rome Extruder 2
# -------------------------------------										
[extruder_stepper rome_extruder_2]
extruder:
step_pin: PF9
dir_pin: !PF10
enable_pin: !PG2
microsteps: 64
rotation_distance: 4.63
full_steps_per_rotation: 200

[tmc2209 extruder_stepper rome_extruder_2]
uart_pin: PF2
stealthchop_threshold: 0
interpolate: False
driver_TBL: 1
driver_TOFF: 3
driver_HEND: 9
driver_HSTRT: 7
```

