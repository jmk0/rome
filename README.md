# ROME
RatOS Multi Extruder

A multi extruder to direct extruder solution for RatOS

High speed multi material printing with as many extruders as you want

## Table of Content
- [Intro](#intro)
- [Installation](#installation)
    - [Raspberry](#raspberry)
    - [Moonraker](#moonraker)
    - [RatOS](#ratos)
- [Slicer](#slicer)
    - [G-code](#G-code)
    - [Native](#native)
- [Hardware](#hardware)
- [Configuration](#configuration)

## Printed Parts
  - [Filament Sensor](https://github.com/HelgeKeck/rome/tree/main/cad/stl/ptfe_tube_inline_filament_sensor)
  - [Y-Junction](https://github.com/HelgeKeck/rome/tree/main/cad/stl/ptfe_tube_y_junction)
  - [Double Spool Holder](https://github.com/HelgeKeck/rome/tree/main/cad/stl/spool_holder)

# Intro

I own a MMU and i like it, but i realized that 99% of my multimaterial prints are just two colors, or even less :-)

I had two spare extruders in my drawer and thought this could be an interesting project.

In case you have a octopus board, the additional extruders can be plugged into the free slots, no additional mcu needed.

ROME is MUCH faster then any regular MMU or ERCF setup. The whole filament unloading and loading process is multiple times faster, not only because ROME just has to park the filament behind the y-junction. In its native mode, ROME handles the loading and unloading process and skips the slicer controlled part of it. This process is highly optimized for a specific Hotend / Filament combination. No more configuration of cooling moves, skinnydip, ramming, .... 

You can even set the acceleration for the wipe tower, in combination with the slicer **max speed for the wipe tower** feature, you can speed up the process even more.

With its **Ooze Ex** feature, it lets you use the most oozing hotends on the markets, it still produces a clean wipe tower

Every MM loading and unloading setting in the slicer will be deactivated and replaced with a simple [unload macro](#unload). 

<img src="https://github.com/HelgeKeck/rome/blob/main/img/rome_top.jpg" alt="" width="800"/>
<img src="https://github.com/HelgeKeck/rome/blob/main/img/toolhead.jpg" alt="" width="800"/>

Wipe tower, printed with 300mm/s @ 25000 mm²/s acceleration on a Rapido UHF with Prusament PETG. 

<img src="https://github.com/HelgeKeck/rome/blob/main/img/wipe_tower_1.jpg" alt="" width="800"/>
<img src="https://github.com/HelgeKeck/rome/blob/main/img/wipe_tower_2.jpg" alt="" width="800"/>
<img src="https://github.com/HelgeKeck/rome/blob/main/img/wipe_tower_3.jpg" alt="" width="800"/>
<img src="https://github.com/HelgeKeck/rome/blob/main/img/wipe_tower_4.jpg" alt="" width="800"/>

Examples 

<img src="https://github.com/HelgeKeck/rome/blob/main/img/sample.jpg" alt="" width="800"/>
<img src="https://github.com/HelgeKeck/rome/blob/main/img/sample2.jpg" alt="" width="800"/>
<img src="https://github.com/HelgeKeck/rome/blob/main/img/sample3.jpg" alt="" width="800"/>

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

Add this to the users overrides section in your printer.cfg

```ini
# ROME
[include rome/config.cfg]
```

# Slicer 

## G-code 

**Printer Start G-code**
```
ROME_START_PRINT EXTRUDER_TEMP=[first_layer_temperature] BED_TEMP=[first_layer_bed_temperature] TOOL=[initial_tool] EXTRUDERS_COUNT=[extruders_count] WIPE_TOWER={wipe_tower} WIPE_TOWER_X={wipe_tower_x} WIPE_TOWER_Y={wipe_tower_y} WIPE_TOWER_WIDTH={wipe_tower_width} WIPE_TOWER_ROTATION_ANGLE={wipe_tower_rotation_angle} COOLING_TUBE_RETRACTION={cooling_tube_retraction} COOLING_TUBE_LENGTH={cooling_tube_length} PARKING_POS_RETRACTION={parking_pos_retraction} EXTRA_LOADING_MOVE={extra_loading_move}
```

**Printer End G-code**
```
ROME_END_PRINT
```

**Printer Tool change G-code**
```
CHANGE_TOOL TOOL=[next_extruder]
```

**Filament Start G-code**

This is just an example, it shows how to configure pressure advance for the used extruders

```
SET_PRESSURE_ADVANCE ADVANCE=0.065 SMOOTH_TIME=0.04
SET_PRESSURE_ADVANCE ADVANCE=0.065 SMOOTH_TIME=0.04 EXTRUDER=rome_extruder_1
SET_PRESSURE_ADVANCE ADVANCE=0.065 SMOOTH_TIME=0.04 EXTRUDER=rome_extruder_2
```

## ROME Modes 

ROME can operate in two different modes, Native and Classic.

The Classic Mode works exactly like the MMU or ERCF. You are responsible to configure the Slicer like you would for the MMU or ERCF.

The Native Mode handles the filament loading and unloading on the Wipe tower. Faster filament changes, less Slicer configuration needed and more control over the process.

## Native 

**Use relative E distances**

Printer Settings->General

<img src="https://github.com/HelgeKeck/rome/blob/main/img/advanced.jpg" alt="" width="320"/>


**Activate additional extruders**

Printer Settings->General

<img src="https://github.com/HelgeKeck/rome/blob/main/img/capabilities.jpg" alt="" width="387"/>


**Dectivate all multi material parameters**

Printer Settings->Single extruder MM setup

<img src="https://github.com/HelgeKeck/rome/blob/main/img/mmu_parameters.jpg" alt="" width="407"/>


**Dectivate advanced wiping volume**

Printer Settings->Single extruder MM setup

<img src="https://github.com/HelgeKeck/rome/blob/main/img/wiping_volume.jpg" alt="" width="462"/>


**Dectivate advanced wiping volume**

Printer Settings->General

<img src="https://github.com/HelgeKeck/rome/blob/main/img/wiping_volume.jpg" alt="" width="462"/>


**Dectivate toolchange temperature**

Filament Settings->Multimaterial

<img src="https://github.com/HelgeKeck/rome/blob/main/img/toolchange_temperature.jpg" alt="" width="400"/>


**Dectivate skinnydip string reduction**

Filament Settings->Multimaterial

<img src="https://github.com/HelgeKeck/rome/blob/main/img/dip.jpg" alt="" width="454"/>


**Dectivate cooling moves and ramming**

Filament Settings->Multimaterial

<img src="https://github.com/HelgeKeck/rome/blob/main/img/toolchange_parameters.jpg" alt="" width="400"/>

<img src="https://github.com/HelgeKeck/rome/blob/main/img/ramming.jpg" alt="" width="764"/>


**Enable wipe tower**

Print Settings->multiple extruders

<img src="https://github.com/HelgeKeck/rome/blob/main/img/wipe_tower.jpg" alt="" width="584"/>


# Hardware 

## Primary Extruder

ROME is by default configured to be used with Orbiter Extruders on an Octopus mainboard. In case you want to use other extruders or mainboard you can override these sections in your printer.cfg

```ini
# -------------------------------------										
# Toolhead Extruder 
# Orbiter 2.0 
# -------------------------------------	
[extruder]
max_extrude_only_velocity: 100
max_extrude_only_accel: 1000
max_extrude_only_distance: 400
max_extrude_cross_section: 999999
```

## Secondary Extruders

You can add as many secondary extruders as you want.

```ini
# -------------------------------------										
# Rome Extruder 1
# Orbiter 1.5 on Octopus Board Driver 3
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
# Orbiter 1.5 on Octopus Board Driver 4
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

## Filament Sensor

```ini
[filament_switch_sensor extruder_filament_sensor]
pause_on_runout: False
event_delay: 0.1
pause_delay: 0.1
switch_pin: ^!PG15
insert_gcode:
  ROME_INSERT_GCODE
runout_gcode:
  ROME_RUNOUT_GCODE
```

# Configuration

```ini
# -------------------------------------										
#  ROME CONFIGURATION
# -------------------------------------										
[rome]
tool_count: 2                                   # number of tools

heater_timeout: 600                             # Heater Timeout in case of rome paused the print

unload_filament_after_print: 1                  # 1 = unloads filament after a printing
                                                # 0 = filament stays in hotend

wipe_tower_acceleration: 25000                  # printer acceleration when printing the wipe tower

use_ooze_ex: 1                                  # 1 = rome distributes oozed material over the length of the wipe tower
                                                # 0 = try your luck 

nozzle_loading_speed_mms: 10                    # extruder speed when moving the filament between the parking position and the nozzle 
filament_homing_speed_mms: 75                   # extruder speed when moving the filament inside bowden tube
filament_parking_speed_mms: 50                  # extruder speed when moving the filament between the filament sensor and the parking position

toolhead_sensor_to_reverse_bowden_mm: 210       # distance between the filament sensor and the parking position behind the y-junction
toolhead_sensor_to_extruder_gear_mm: 45         # distance between the filament sensor and the extruder gears
extruder_gear_to_parking_position_mm: 40        # distance between the extruder gears and the parking position
parking_position_to_nozzle_mm: 35               # distance between the parking position and the nozzle
```

# Unload

By default ROME is configured for a Rapido UHF and PETG. If you have another combination, just override this macro so that it fits your needs.

```ini
# -------------------------------------										
# Unload from nozzle to parking position
# Rapido UHF
# Prusament PETG @ 250°
# -------------------------------------										
[gcode_macro _UNLOAD_FROM_NOZZLE_TO_PARKING_POSITION]
gcode:
  # initial retract
  G92 E0
  G0 E-25 F3600
  G4 P500
  # remove string
  G92 E0
  G0 E20 F3600
  G4 P100
  # move to parking position, the center of the ptfe tube that goes to your hotend
  G92 E0
  G0 E-35 F3600
  G4 P500
  # wait for movements
  M400
```
