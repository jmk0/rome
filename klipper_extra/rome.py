import time
from ssl import SSLSocket
from math import fabs
from re import T

class ROME:

    # -----------------------------------------------------------------------------------------------------------------------------
    # Initialize
    # -----------------------------------------------------------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.printer = self.config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.extruder_filament_sensor = self.printer.lookup_object("filament_switch_sensor extruder_filament_sensor")

        self.load_settings()
        self.register_commands()
        self.register_handle_connect()

    def load_settings(self):
        self.tool_count = 2

        self.heater_timeout = self.config.getfloat('heater_timeout', 600.0)
        self.unload_filament_after_print = self.config.getfloat('unload_filament_after_print', 1)
        self.wipe_tower_acceleration = self.config.getfloat('wipe_tower_acceleration', 5000.0)
        self.use_ooze_ex = self.config.getfloat('use_ooze_ex', 1)

        self.nozzle_loading_speed_mms = self.config.getfloat('nozzle_loading_speed_mms', 10.0)
        self.filament_homing_speed_mms = self.config.getfloat('filament_homing_speed_mms', 75.0)
        self.filament_parking_speed_mms = self.config.getfloat('filament_parking_speed_mms', 50.0)

        self.toolhead_sensor_to_reverse_bowden_mm = self.config.getfloat('toolhead_sensor_to_reverse_bowden_mm', 100.0)
        self.toolhead_sensor_to_extruder_gear_mm = self.config.getfloat('toolhead_sensor_to_extruder_gear_mm', 45.0)
        self.extruder_gear_to_parking_position_mm = self.config.getfloat('extruder_gear_to_parking_position_mm', 40.0)
        self.parking_position_to_nozzle_mm = self.config.getfloat('parking_position_to_nozzle_mm', 65.0)

    def register_handle_connect(self):
        self.printer.register_event_handler("klippy:connect", self.execute_handle_connect)

    def execute_handle_connect(self):
        self.toolhead = self.printer.lookup_object('toolhead')
        self.extruder = self.printer.lookup_object('extruder')
        self.pheaters = self.printer.lookup_object('heaters')
        self.heater = self.extruder.get_heater()

    # -----------------------------------------------------------------------------------------------------------------------------
    # Heater Timeout Handler
    # -----------------------------------------------------------------------------------------------------------------------------
    def enable_heater_timeout(self):
        waketime = self.reactor.NEVER
        if self.heater_timeout:
            waketime = self.reactor.monotonic() + self.heater_timeout
        self.heater_timeout_handler = self.reactor.register_timer(self.execute_heater_timeout, waketime)

    def disable_heater_timeout(self):
        if self.heater_timeout_handler:
            self.reactor.update_timer(self.heater_timeout_handler, self.reactor.NEVER)

    def execute_heater_timeout(self, eventtime):
        if self.Paused:
            self.respond("Heater timeout detected!")
            self.extruder_set_temperature(0, False)
        nextwake = self.reactor.NEVER
        return nextwake

    # -----------------------------------------------------------------------------------------------------------------------------
    # GCode Registration
    # -----------------------------------------------------------------------------------------------------------------------------
    def register_commands(self):
        self.gcode.register_command('HOME_ROME', self.cmd_HOME_ROME, desc=("HOME_ROME"))
        self.gcode.register_command('_PAUSE_ROME', self.cmd_PAUSE_ROME, desc=("_PAUSE_ROME"))
        self.gcode.register_command('_RESUME_ROME', self.cmd_RESUME_ROME, desc=("_RESUME_ROME"))
        self.gcode.register_command('LOAD_TOOL', self.cmd_LOAD_TOOL, desc=("LOAD_TOOL"))
        self.gcode.register_command('UNLOAD_TOOL', self.cmd_UNLOAD_TOOL, desc=("UNLOAD_TOOL"))
        self.gcode.register_command('CHANGE_TOOL', self.cmd_CHANGE_TOOL, desc=("CHANGE_TOOL"))
        self.gcode.register_command('ROME_END_PRINT', self.cmd_ROME_END_PRINT, desc=("ROME_END_PRINT"))
        self.gcode.register_command('ROME_START_PRINT', self.cmd_ROME_START_PRINT, desc=("ROME_START_PRINT"))

    def cmd_LOAD_TOOL(self, param):
        self.cmd_origin = "gcode"
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count - 1)
        temp = param.get_int('TEMP', None, minval=-1, maxval=self.heater.max_temp)
        if not self.load_tool(tool, temp):
            self.pause_rome()
            return

    def cmd_UNLOAD_TOOL(self, param):
        self.cmd_origin = "gcode"
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count - 1)
        temp = param.get_int('TEMP', None, minval=-1, maxval=self.heater.max_temp)

        # set hotend temperature
        if temp > 0:
            self.set_hotend_temperature()

        # unload tool
        self.Selected_Filament = tool
        if self.filament_sensor_triggered():
            self.unload_tool()

    def cmd_HOME_ROME(self, param):
        self.Homed = False
        if not self.home():
            self.respond("Can not home ROME!")

    def cmd_CHANGE_TOOL(self, param):
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count)
        if not self.change_tool(tool):
            self.pause_rome()

    def cmd_ROME_END_PRINT(self, param):
        self.cmd_origin = "gcode"
        self.gcode.run_script_from_command("_ROME_END_PRINT")
        if self.unload_filament_after_print == 1:
            if self.filament_sensor_triggered():
                self.unload_tool()
        self.Homed = False

    def cmd_ROME_START_PRINT(self, param):
        self.cmd_origin = "rome"
        self.mode = "native"
        self.Tool_Swaps = 0
        self.exchange_old_position = None

        self.wipe_tower_x = param.get_float('WIPE_TOWER_X', None, minval=0, maxval=999) 
        self.wipe_tower_y = param.get_float('WIPE_TOWER_Y', None, minval=0, maxval=999)
        self.wipe_tower_width = param.get_float('WIPE_TOWER_WIDTH', None, minval=0, maxval=999)
        self.wipe_tower_rotation_angle = param.get_float('WIPE_TOWER_ROTATION_ANGLE', None, minval=-360, maxval=360)

        cooling_tube_retraction = param.get_float('COOLING_TUBE_RETRACTION', None, minval=0, maxval=999) 
        cooling_tube_length = param.get_float('COOLING_TUBE_LENGTH', None, minval=0, maxval=999) 
        parking_pos_retraction = param.get_float('PARKING_POS_RETRACTION', None, minval=0, maxval=999) 
        extra_loading_move = param.get_float('EXTRA_LOADING_MOVE', None, minval=-999, maxval=999) 
        if cooling_tube_retraction == 0 and cooling_tube_length == 0 and parking_pos_retraction == 0 and extra_loading_move == 0:
            self.mode = "native"
        else:
            self.mode = "slicer"
        
        tool = param.get_int('TOOL', None, minval=0, maxval=4)
        bed_temp = param.get_int('BED_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        extruder_temp = param.get_int('EXTRUDER_TEMP', None, minval=-1, maxval=self.heater.max_temp)

        self.gcode.run_script_from_command("_ROME_START_PRINT TOOL=" + str(tool) + " BED_TEMP=" + str(bed_temp) + " EXTRUDER_TEMP=" + str(extruder_temp))

    def cmd_PAUSE_ROME(self, param):
        self.pause_rome()

    def cmd_RESUME_ROME(self, param):
        self.resume_rome()

    # -----------------------------------------------------------------------------------------------------------------------------
    # Home
    # -----------------------------------------------------------------------------------------------------------------------------
    Homed = False

    def home(self):

        # homing rome
        self.respond("Homing Rome!")
        self.Homed = False
        self.Paused = False
        self.Tool_Swaps = 0

        # precheck
        if not self.can_home():
            return False

        # home filaments
        if not self.home_filament(0):
            return False
        if not self.home_filament(1):
            return False

        self.Homed = True
        self.Selected_Filament = -1

        # success
        return True

    def can_home(self):

        # check hotend temperature
        if not self.extruder_can_extrude():
            self.respond("Preheat Nozzle to " + str(self.heater.min_extrude_temp + 10))
            self.extruder_set_temperature(self.heater.min_extrude_temp + 10, True)

        # check extruder
        if self.filament_sensor_triggered():

            # unload filament from nozzle
            if self.filament_sensor_triggered():
                if not self.unload_tool():
                    self.respond("Can not unload from nozzle!")
                    return False

            # turn off hotend heater
            self.extruder_set_temperature(0, False)

            # check
            if self.filament_sensor_triggered():
                self.respond("Filament stuck in extruder!")
                return False

        # success
        return True

    def home_filament(self, filament):
 
        # select filament
        self.select_filament(filament)

        # home filament
        if not self.load_filament_from_reverse_bowden_to_toolhead_sensor(False):
            self.respond("Filament " + str(filament) + " cant be loaded into the toolhead sensor!")
            return False
        if not self.unload_filament_from_toolhead_sensor_to_reverse_bowden(20):
            self.respond("Filament " + str(filament) + " cant be unloaded from the toolhead sensor!")
            return False

        # success
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Change Tool
    # -----------------------------------------------------------------------------------------------------------------------------
    mode = "native"
    cmd_origin = "rome"

    Tool_Swaps = 0
    ooze_move_x = 0
    exchange_old_position = None

    wipe_tower_x = 170
    wipe_tower_y = 140
    wipe_tower_width = 60
    wipe_tower_rotation_angle = 0

    def change_tool(self, tool):
        self.cmd_origin = "rome"
        if self.Tool_Swaps > 0:
            self.before_change()
            if not self.load_tool(tool, -1):
                return False
            self.after_change()
        self.Tool_Swaps = self.Tool_Swaps + 1
        return True

    def load_tool(self, tool, temp=-1):
        
        # set hotend temperature
        if temp > 0:
            self.set_hotend_temperature()

        # home if not homed yet
        if not self.Homed:
            if not self.home():
                return False

        # set temp if configured and wait for it
        if temp > 0:
            self.respond("Waiting for heater...")
            self.extruder_set_temperature(temp, True)

        # check hotend temperature
        if not self.extruder_can_extrude():
            self.respond("Hotend too cold!")
            self.respond("Heat up nozzle to " + str(self.heater.min_extrude_temp))
            self.extruder_set_temperature(self.heater.min_extrude_temp, True)

        # load filament
        if self.filament_sensor_triggered():
            if not self.unload_tool():
                self.respond("could not unload tool!")
                return False
        if not self.select_filament(tool):
            self.respond("could not select filament!")
            return False
        if not self.load_filament_from_reverse_bowden_to_toolhead_sensor():
            self.respond("could not load tool to sensor!")
            return False
        if not self.load_filament_from_toolhead_sensor_to_parking_position():
            self.respond("could not park filament!")
            return False
        if self.mode != "slicer" or self.Tool_Swaps == 0:
            if not self.load_filament_from_parking_position_to_nozzle():
                self.respond("could not load into nozzle!")
                return False

        # success
        return True

    def unload_tool(self):

        # select tool
        self.select_filament(self.Selected_Filament)

        # unload tool
        if self.mode != "slicer":
            if not self.unload_filament_from_nozzle_to_parking_position():
                return False
        if not self.unload_filament_from_parking_position_to_toolhead_sensor():
            return False
        if not self.unload_filament_from_toolhead_sensor_to_reverse_bowden():
            return False

        # success
        return True

    def before_change(self):
        if self.mode == "native":
            self.before_change_rome_native()
        elif self.mode == "slicer":
            self.before_change_rome_slicer()
        
    def after_change(self):
        if self.mode == "native":
            self.after_change_rome_native()
        elif self.mode == "slicer":
            self.after_change_rome_slicer()

    # -----------------------------------------------------------------------------------------------------------------------------
    # Rome Native
    # -----------------------------------------------------------------------------------------------------------------------------

    def before_change_rome_native(self):
        self.gcode.run_script_from_command('SAVE_GCODE_STATE NAME=PAUSE_state')
        self.exchange_old_position = self.toolhead.get_position()

        x_offset = abs(self.exchange_old_position[0] - self.wipe_tower_x)
        if x_offset < 10:
            self.ooze_move_x = self.wipe_tower_x + self.wipe_tower_width
        else:
            self.ooze_move_x = self.exchange_old_position[0] - self.wipe_tower_width

        self.gcode.run_script_from_command('M204 S' + str(self.wipe_tower_acceleration))
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E-2 F3600')
        self.gcode.run_script_from_command('M400')
        
    def after_change_rome_native(self):
        self.respond("after_change_rome_native")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Rome Slicer
    # -----------------------------------------------------------------------------------------------------------------------------

    def before_change_rome_slicer(self):
        self.respond("before_change_rome_slicer")
        self.gcode.run_script_from_command('SAVE_GCODE_STATE NAME=PAUSE_state')
        self.exchange_old_position = self.toolhead.get_position()
        self.gcode.run_script_from_command('M204 S' + str(self.wipe_tower_acceleration))
        
    def after_change_rome_slicer(self):
        self.respond("after_change_rome_slicer")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Select Filament
    # -----------------------------------------------------------------------------------------------------------------------------
    Selected_Filament = -1

    def select_filament(self, tool=-1):

        # unselect filament
        if not self.unselect_filament():
            return False

        # select filament
        if tool == 0 or tool == -1:
            self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=extruder')
        if tool == 1 or tool == -1:
            self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_2 MOTION_QUEUE=extruder')
        self.Selected_Filament = tool

        # success
        return True

    def unselect_filament(self):

        # unselect filament
        self.Selected_Filament = -1
        self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=')
        self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_2 MOTION_QUEUE=')

        # success
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Load Filament
    # -----------------------------------------------------------------------------------------------------------------------------
    def load_filament_from_reverse_bowden_to_toolhead_sensor(self, exact_positioning=True):

        # initial move
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E' + str(self.toolhead_sensor_to_reverse_bowden_mm - 20) + ' F' + str(self.filament_homing_speed_mms * 60))
        self.gcode.run_script_from_command('M400')

        # try to find the sensor
        self.respond("try to find the sensor...")
        step_distance = 20
        max_step_count = 50
        if not self.filament_sensor_triggered():
            for i in range(max_step_count):
                self.gcode.run_script_from_command('G92 E0')
                self.gcode.run_script_from_command('G0 E' + str(step_distance) + ' F' + str(self.filament_homing_speed_mms * 60))
                self.gcode.run_script_from_command('M400')
                if self.filament_sensor_triggered():
                    break

        # check if sensor was found
        self.respond("check if sensor was found...")
        if not self.filament_sensor_triggered():
            self.respond("Could not find filament sensor!")
            return False

        # exact positioning
        if exact_positioning == True:
            if not self.filament_positioning():
                self.respond("Could not position the filament in the filament sensor!")
                return False

        # success
        return True

    def load_filament_from_toolhead_sensor_to_parking_position(self):
        
        # move filament to parking position
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E' + str(self.toolhead_sensor_to_extruder_gear_mm + self.extruder_gear_to_parking_position_mm) + ' F' + str(self.filament_parking_speed_mms * 60))
        self.gcode.run_script_from_command('M400')

        # success
        return True

    def load_filament_from_parking_position_to_nozzle(self):

        # load filament into nozzle
        self.gcode.run_script_from_command('G92 E0')
        if self.cmd_origin != "rome" or self.exchange_old_position == None or self.use_ooze_ex == 0:
            self.gcode.run_script_from_command('G0 E' + str(self.parking_position_to_nozzle_mm) + ' F' + str(self.nozzle_loading_speed_mms * 60))
        else:
            self.gcode.run_script_from_command('G0 E' + str(self.parking_position_to_nozzle_mm / 2) + ' X' + str(self.ooze_move_x) + ' F' + str(self.nozzle_loading_speed_mms * 60))
            self.gcode.run_script_from_command('G0 E' + str(self.parking_position_to_nozzle_mm / 2) + ' X' + str(self.exchange_old_position[0]) + ' F' + str(self.nozzle_loading_speed_mms * 60))
        self.gcode.run_script_from_command('G4 P1000')
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('M400')

        # success
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Unload Filament
    # -----------------------------------------------------------------------------------------------------------------------------

    def unload_filament_from_nozzle_to_parking_position(self):

        # unload filament to parking position
        if self.cmd_origin != "rome" or self.use_ooze_ex == 0: 
            self.gcode.run_script_from_command('_UNLOAD_FROM_NOZZLE_TO_PARKING_POSITION')
        else:
            self.gcode.run_script_from_command('G0 X' + str(self.ooze_move_x) + ' F600')
            self.gcode.run_script_from_command('_UNLOAD_FROM_NOZZLE_TO_PARKING_POSITION')
            self.gcode.run_script_from_command('G0 X' + str(self.exchange_old_position[0]) + ' F600')
            self.gcode.run_script_from_command('G4 P1000')

        # success
        return True

    def unload_filament_from_parking_position_to_toolhead_sensor(self):
        
        # unload filament to toolhead sensor
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('M400')
        if self.cmd_origin != "rome" or self.exchange_old_position == None or self.use_ooze_ex == 0:
            self.gcode.run_script_from_command('G0 E-' + str(self.extruder_gear_to_parking_position_mm + self.toolhead_sensor_to_extruder_gear_mm) + ' F' + str(self.filament_homing_speed_mms * 60))
        else:
            self.gcode.run_script_from_command('G0 E-' + str(self.extruder_gear_to_parking_position_mm) + ' X' + str(self.exchange_old_position[0]) + ' F' + str(self.filament_homing_speed_mms * 60))
            self.gcode.run_script_from_command('G0 E-' + str(self.toolhead_sensor_to_extruder_gear_mm) + ' F' + str(self.filament_homing_speed_mms * 60))
        self.gcode.run_script_from_command('M400')

        # success
        return True

    def unload_filament_from_toolhead_sensor_to_reverse_bowden(self, offset=0):
        
        # eject filament
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E-' + str(self.toolhead_sensor_to_reverse_bowden_mm + offset) + ' F' + str(self.filament_homing_speed_mms * 60))
        self.gcode.run_script_from_command('M400')

        # check if filament is ejected
        if self.filament_sensor_triggered():
            return False

        # success
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Filament Positioning
    # -----------------------------------------------------------------------------------------------------------------------------
    def filament_positioning(self):

        # fast positioning
        if not self.fast_positioning():
            if not self.exact_positioning():
                return False

        # exact positioning
        if not self.exact_positioning():
            if not self.fast_positioning():
                return False
            if not self.exact_positioning():
                return False

        # success
        return True

    def fast_positioning(self):

        # fast positioning
        accuracy_in_mm = 4
        max_step_count = 20

        # find toolhead sensor
        for i in range(max_step_count):
            self.gcode.run_script_from_command('G92 E0')
            self.gcode.run_script_from_command('G0 E-' + str(accuracy_in_mm) + ' F' + str(self.filament_homing_speed_mms * 60))
            self.gcode.run_script_from_command('M400')
            if not self.filament_sensor_triggered():
                break

        # check positioning success
        if self.filament_sensor_triggered():
            return False

        # success
        return True
    
    def exact_positioning(self):

        # exact positioning
        accuracy_in_mm = 1
        max_step_count = 20

        # find toolhead sensor
        for n in range(max_step_count):
            self.gcode.run_script_from_command('G92 E0')
            self.gcode.run_script_from_command('G0 E' + str(accuracy_in_mm) + ' F' + str(self.filament_homing_speed_mms * 60))
            self.gcode.run_script_from_command('M400')
            if self.filament_sensor_triggered():
                break

        # check positioning success
        if not self.filament_sensor_triggered():
            return False

        # success
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Pause
    # -----------------------------------------------------------------------------------------------------------------------------
    Paused = False

    def pause_rome(self):
        self.Paused = True
        self.enable_heater_timeout()
        self.gcode.run_script_from_command('_ROME_PAUSE')

    def resume_rome(self):
        self.Paused = False
        self.disable_heater_timeout()
        if self.exchange_old_position != None:
            self.gcode.run_script_from_command('G0 Z' + str(self.exchange_old_position[2] + 2) + ' F3600')
            self.gcode.run_script_from_command('G0 X' + str(self.exchange_old_position[0]) + ' Y' + str(self.exchange_old_position[1]) + ' F3600')
            self.gcode.run_script_from_command('M400')
        self.gcode.run_script_from_command("_ROME_RESUME")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Helper
    # -----------------------------------------------------------------------------------------------------------------------------
    def set_hotend_temperature(self, temp):
        
        # set hotend temperature
        if temp < self.heater.min_temp:
            self.respond("Selected temperature " + str(temp) + " too low, must be above " + str(self.heater.min_temp))
            return False
        if temp > self.heater.max_temp:
            self.respond("Selected temperature " + str(temp) + "too high, must be below " + str(self.heater.max_temp))
            return False
        if temp < self.heater.min_extrude_temp:
            self.respond("Selected temperature " + str(temp) + " below minimum extrusion temperature " + str(self.heater.min_extrude_temp))
            return False

        # start heating
        self.respond("Heat up nozzle to " + str(temp))
        self.extruder_set_temperature(temp, False)

        # success
        return True

    def respond(self, message):
        self.gcode.respond_raw(message)

    def filament_sensor_triggered(self):
        return bool(self.extruder_filament_sensor.runout_helper.filament_present)

    def extruder_set_temperature(self, temperature, wait):
        self.pheaters.set_temperature(self.heater, temperature, wait)

    def extruder_can_extrude(self):
        status = self.extruder.get_status(self.toolhead.get_last_move_time())
        result = status['can_extrude'] 
        return result

# -----------------------------------------------------------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------------------------------------------------------
def load_config(config):
    return ROME(config)
