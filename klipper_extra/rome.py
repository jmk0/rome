import time
from ssl import SSLSocket
from math import fabs
from re import T

class ROME:

    origin = "rome"
    Paused = False

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
        self.unload_after_print = self.config.getfloat('unload_after_print', 1)

        self.nozzle_loading_speed_mms = self.config.getfloat('nozzle_loading_speed_mms', 10.0)
        self.nozzle_parking_speed_mms = self.config.getfloat('nozzle_parking_speed_mms', 50.0)
        self.filament_homing_speed_mms = self.config.getfloat('filament_homing_speed_mms', 75.0)

        self.sensor_to_reverse_bowden_parking_position_mm = self.config.getfloat('sensor_to_reverse_bowden_parking_position_mm', 100.0)
        self.sensor_to_extruder_gear_mm = self.config.getfloat('sensor_to_extruder_gear_mm', 45.0)
        self.extruder_gear_to_parking_position_mm = self.config.getfloat('extruder_gear_to_parking_position_mm', 40.0)
        self.parking_position_to_nozzle_mm = self.config.getfloat('parking_position_to_nozzle_mm', 65.0)

        self.wipe_tower_acceleration = self.config.getfloat('wipe_tower_acceleration', 65.0)

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
        self.origin = "gcode"
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count - 1)
        temp = param.get_int('TEMP', None, minval=-1, maxval=self.heater.max_temp)
        if not self.load_tool(tool, temp):
            self.pause_rome()
            return

    def cmd_UNLOAD_TOOL(self, param):
        self.origin = "gcode"
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count - 1)
        temp = param.get_int('TEMP', None, minval=-1, maxval=self.heater.max_temp)
        if not self.rome_unload_tool(tool, temp):
            self.pause_rome()
            return

    def cmd_HOME_ROME(self, param):
        self.Homed = False
        if not self.home():
            self.respond("Can not home ROME!")

    def cmd_CHANGE_TOOL(self, param):
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count)
        if not self.change_tool(tool):
            self.pause_rome()

    def cmd_ROME_END_PRINT(self, param):
        self.gcode.run_script_from_command("_ROME_END_PRINT")
        if self.unload_after_print == 1:
            self.unload_tool()
        self.Homed = False

    def cmd_ROME_START_PRINT(self, param):
        self.Tool_Swaps = 0
        self.exchange_old_position = None

        self.wipe_tower_x = param.get_float('WIPE_TOWER_X', None, minval=0, maxval=999) 
        self.wipe_tower_y = param.get_float('WIPE_TOWER_Y', None, minval=0, maxval=999)
        self.wipe_tower_width = param.get_float('WIPE_TOWER_WIDTH', None, minval=0, maxval=999)
        self.wipe_tower_rotation_angle = param.get_float('WIPE_TOWER_ROTATION_ANGLE', None, minval=-360, maxval=360)

        TOOL = param.get_int('TOOL', None, minval=0, maxval=4)
        BED_TEMP = param.get_int('BED_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        EXTRUDER_TEMP = param.get_int('EXTRUDER_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        self.gcode.run_script_from_command("_ROME_START_PRINT TOOL=" + str(TOOL) + " BED_TEMP=" + str(BED_TEMP) + " EXTRUDER_TEMP=" + str(EXTRUDER_TEMP))

    def cmd_PAUSE_ROME(self, param):
        self.pause_rome()

    def cmd_RESUME_ROME(self, param):
        self.resume_rome()

    # -----------------------------------------------------------------------------------------------------------------------------
    # Home
    # -----------------------------------------------------------------------------------------------------------------------------
    Homed = False

    def home(self):
        self.respond("Homing ROME...")

        self.Homed = False
        self.Paused = False
        self.Tool_Swaps = 0

        if not self.can_home():
            self.respond("Can not home ROME!")
            return False

        if not self.home_filament(0):
            self.respond("Can not home filament 0!")
            return False

        if not self.home_filament(1):
            self.respond("Can not home filament 1!")
            return False

        self.Homed = True
        self.Selected_Tool = -1

        self.respond("Welcome home ROME!")
        return True

    def can_home(self):

        # check hotend temperature
        if not self.extruder_can_extrude():
            self.respond("Preheat Nozzle to " + str(self.heater.min_extrude_temp + 10))
            self.extruder_set_temperature(self.heater.min_extrude_temp + 10, True)

        # check extruder
        if self.filament_sensor_triggered():
            self.respond("Filament in extruder detected!")

            # unload filament rom nozzle
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
        if not self.load_to_toolhead_sensor(filament, False):
            return False
        if not self.unload_from_toolhead_sensor(filament, 30):
            return False
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Change Tool
    # -----------------------------------------------------------------------------------------------------------------------------
    Tool_Swaps = 0
    ooze_move_x = 0

    exchange_lift_speed = 60
    exchange_travel_speed = 750
    exchange_old_position = None
    exchange_safe_z = 0

    wipe_tower_x = 170
    wipe_tower_y = 140
    wipe_tower_width = 60
    wipe_tower_rotation_angle = 0

    def change_tool(self, tool):
        self.origin = "rome"
        if self.Tool_Swaps > 0:
            self.before_change()
            if not self.load_tool(tool, -1):
                return False
            self.after_change()
        self.Tool_Swaps = self.Tool_Swaps + 1
        return True

    def before_change(self):
        self.gcode.run_script_from_command('SAVE_GCODE_STATE NAME=PAUSE_state')
        self.exchange_old_position = self.toolhead.get_position()

        x_offset = abs(self.exchange_old_position[0] - self.wipe_tower_x)
        if x_offset < 10:
            self.ooze_move_x = self.wipe_tower_x + self.wipe_tower_width
        else:
            self.ooze_move_x = self.exchange_old_position[0] - self.wipe_tower_width

        # set acceleration for wipe tower
        self.gcode.run_script_from_command('M204 S' + str(self.wipe_tower_acceleration))

        # retract
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E-2 F' + str(self.exchange_travel_speed * 60))
        self.gcode.run_script_from_command('M400')
        
    def after_change(self):
        self.respond("after_change_rome")

    def rome_unload_tool(self, tool, temp=-1):
        self.respond("Unload Tool " + str(tool))

        # set selected temperature
        if not self.set_selected_temperature(temp):
            return False

        # set hotend temperature
        self.set_hotend_temperature()

        # select filament
        self.select_tool(tool)

        # unload filament from nozzle
        self.unload_from_nozzle_to_parking_position()

        # move filament from parking position to reverse bowden
        if not self.unload_from_parking_position_to_reverse_bowden():
            return False

        # success
        self.respond("Tool " + str(tool) + " unloaded")
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # select tool
    # -----------------------------------------------------------------------------------------------------------------------------
    Selected_Tool = -1

    def select_tool(self, tool=-1):
        self.respond("select_tool " + str(tool))
        self.unselect_tool()
        if tool == 0 or tool == -1:
            self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=extruder')
        if tool == 1 or tool == -1:
            self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_2 MOTION_QUEUE=extruder')
        self.Selected_Tool = tool
        return True

    def unselect_tool(self):
        self.Selected_Tool = -1
        self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=')
        self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_2 MOTION_QUEUE=')

    # -----------------------------------------------------------------------------------------------------------------------------
    # Load Tool
    # -----------------------------------------------------------------------------------------------------------------------------

    def load_tool(self, tool, temp=-1):
        if self.trace:
            self.respond("Load Tool " + str(tool))

        # set selected temperature
        if not self.set_selected_temperature(temp):
            return False

        # home if not homed yet
        if not self.Homed:
            if not self.home():
                return False

        # set hotend temperature
        self.set_hotend_temperature()

        # load filament
        if not self.unload_tool():
            self.respond("could not unload tool!")
            return False
        if not self.select_tool(tool):
            self.respond("could not select tool!")
            return False
        if not self.load_to_toolhead_sensor(tool):
            self.respond("could not load tool to sensor!")
            return False
        if not self.load_from_filament_sensor_to_parking_position():
            self.respond("could not park filament!")
            return False
        if not self.load_from_parking_position_to_nozzle():
            self.respond("could not load into nozzle!")
            return False

        self.respond("Tool " + str(tool) + " loaded")
        return True

    def load_to_toolhead_sensor(self, tool, exact_positioning=True):
    
        # select tool
        self.select_tool(tool)

        # initial move
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E' + str(self.sensor_to_reverse_bowden_parking_position_mm - 20) + ' F' + str(self.filament_homing_speed_mms * 60))
        self.gcode.run_script_from_command('M400')

        # find toolhead sensor
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
        if not self.filament_sensor_triggered():
            self.respond("Could not find filament sensor!")
            return False

        # exact positioning
        if exact_positioning == True:
            if not self.filament_positioning():
                self.respond("Could not position the filament!")
                return False

        # success
        return True

    def load_from_filament_sensor_to_parking_position(self):
       
        # move filament to extruder gears
        self.gcode.run_script_from_command('G92 E0')
        if self.origin != "rome" or self.exchange_old_position == None:
            self.gcode.run_script_from_command('G0 E' + str(self.sensor_to_extruder_gear_mm + self.extruder_gear_to_parking_position_mm) + ' F' + str(self.nozzle_parking_speed_mms * 60))
        else:
            self.gcode.run_script_from_command('G0 E' + str(self.sensor_to_extruder_gear_mm) + ' X' + str(self.ooze_move_x) + ' F' + str(self.nozzle_parking_speed_mms * 60))
            self.gcode.run_script_from_command('G0 E' + str(self.extruder_gear_to_parking_position_mm) + ' X' + str(self.exchange_old_position[0]) + ' F' + str(self.nozzle_parking_speed_mms * 60))
        self.gcode.run_script_from_command('M400')

        # success
        return True

    def load_from_parking_position_to_nozzle(self):

        # load filament into nozzle
        self.gcode.run_script_from_command('G92 E0')
        if self.origin != "rome" or self.exchange_old_position == None:
            self.gcode.run_script_from_command('G0 E' + str(self.parking_position_to_nozzle_mm) + ' F' + str(self.nozzle_loading_speed_mms * 60))
        else:
            self.gcode.run_script_from_command('G0 E' + str(self.parking_position_to_nozzle_mm / 2) + ' X' + str(self.ooze_move_x) + ' F' + str(self.nozzle_loading_speed_mms * 60))
            self.gcode.run_script_from_command('G0 E' + str(self.parking_position_to_nozzle_mm / 2) + ' X' + str(self.exchange_old_position[0]) + ' F' + str(self.nozzle_loading_speed_mms * 60))
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('M400')

        # success
        return True

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
        self.respond("success")
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
    # Unload Tool
    # -----------------------------------------------------------------------------------------------------------------------------

    def unload_tool(self):
        if not self.filament_sensor_triggered():
            return False

        if not self.select_tool(self.Selected_Tool):
            return False

        if not self.unload_from_nozzle_to_parking_position():
            return False

        if not self.unload_from_parking_position_to_reverse_bowden():
            return False

        return True

    def unload_from_toolhead_sensor(self, tool=-1, offset=0):
    
        # select tool
        if tool >= 0:
            self.select_tool(tool)

        # eject filament
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E-' + str(self.sensor_to_reverse_bowden_parking_position_mm + offset) + ' F' + str(self.filament_homing_speed_mms * 60))
        self.gcode.run_script_from_command('M400')

        # check if filament is ejected
        if self.filament_sensor_triggered():
            return False

        # success
        return True

    def unload_from_nozzle_to_parking_position(self):
        if self.origin != "rome": 
            self.gcode.run_script_from_command('_UNLOAD_PETG')
        else:
            self.gcode.run_script_from_command('_UNLOAD_FILAMENT_INITIAL_PETG')
            self.gcode.run_script_from_command('G0 X' + str(self.ooze_move_x) + ' F600')
            self.gcode.run_script_from_command('_UNLOAD_FILAMENT_DIPPING_PETG')
            self.gcode.run_script_from_command('G0 X' + str(self.exchange_old_position[0]) + ' F600')
        return True

    def unload_from_parking_position_to_reverse_bowden(self, tool=-1):

        # select tool
        if tool >= 0:
            self.select_tool(tool)

        # eject filament
        self.gcode.run_script_from_command('G92 E0')
        if self.exchange_old_position == None:
            self.gcode.run_script_from_command('G0 E-' + str(self.extruder_gear_to_parking_position_mm + self.sensor_to_extruder_gear_mm + self.sensor_to_reverse_bowden_parking_position_mm) + ' F' + str(self.filament_homing_speed_mms * 60))
        else:
            self.gcode.run_script_from_command('G0 E-' + str(self.extruder_gear_to_parking_position_mm) + ' X' + str(self.exchange_old_position[0]) + ' F' + str(self.filament_homing_speed_mms * 60))
            self.gcode.run_script_from_command('G0 E-' + str(self.sensor_to_extruder_gear_mm + self.sensor_to_reverse_bowden_parking_position_mm) + ' F' + str(self.filament_homing_speed_mms * 60))
        self.gcode.run_script_from_command('M400')

        # check if filament is ejected
        if self.filament_sensor_triggered():
            return False

        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Helper
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
            resume_z = self.exchange_safe_z
            if resume_z < self.exchange_old_position[2] + 2:
                resume_z = self.exchange_old_position[2] + 2
            self.gcode.run_script_from_command('G0 Z' + str(resume_z) + ' F' + str(self.exchange_lift_speed * 60))
            self.gcode.run_script_from_command('G0 X' + str(self.exchange_old_position[0]) + ' Y' + str(self.exchange_old_position[1]) + ' F' + str(self.exchange_travel_speed * 60))
            self.gcode.run_script_from_command('M400')
        self.gcode.run_script_from_command("_ROME_RESUME")

    def respond(self, message):
        self.gcode.respond_raw(message)

    def set_hotend_temperature(self):

        # set hotend temperature
        if not self.extruder_can_extrude():
            self.respond("Hotend too cold!")
            self.respond("Heat up nozzle to " + str(self.heater.min_extrude_temp))
            self.extruder_set_temperature(self.heater.min_extrude_temp, True)

    def set_selected_temperature(self, temp=-1):

        # set selected temperature
        if temp > 0:

            if temp < self.heater.min_temp:
                self.respond("Selected temperature " + str(temp) + " too low, must be above " + str(self.heater.min_temp))
                return False

            if temp > self.heater.max_temp:
                self.respond("Selected temperature " + str(temp) + "too high, must be below " + str(self.heater.max_temp))
                return False

            if temp < self.heater.min_extrude_temp:
                self.respond("Selected temperature " + str(temp) + " below minimum extrusion temperature " + str(self.heater.min_extrude_temp))
                return False

            # heat up extruder
            self.respond("Heat up nozzle to " + str(temp))
            self.extruder_set_temperature(temp, False)

        # success
        return True

    def filament_sensor_triggered(self):
        return bool(self.extruder_filament_sensor.runout_helper.filament_present)

    def extruder_set_temperature(self, temperature, wait):
        self.pheaters.set_temperature(self.heater, temperature, wait)

    def extruder_can_extrude(self):
        status = self.extruder.get_status(self.toolhead.get_last_move_time())
        result = status['can_extrude'] 
        return result

def load_config(config):
    return ROME(config)
