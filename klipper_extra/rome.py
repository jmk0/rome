from ssl import SSLSocket
import time
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

        self.print_temperature = self.config.getfloat('print_temperature', 240)
        self.unload_temperature = self.config.getfloat('unload_temperature', 200)
        self.heater_timeout = self.config.getfloat('heater_timeout', 600.0)

        self.filament_loading_speed_mms = self.config.getfloat('filament_loading_speed_mms', 10.0)
        self.filament_homing_speed_mms = self.config.getfloat('filament_homing_speed_mms', 75.0)
        self.filament_parking_speed_mms = self.config.getfloat('filament_parking_speed_mms', 75.0)

        self.sensor_to_reverse_bowden_parking_position_mm = self.config.getfloat('sensor_to_reverse_bowden_parking_position_mm', 100.0)

        self.sensor_to_extruder_gear_mm = self.config.getfloat('sensor_to_extruder_gear_mm', 45.0)
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
        if self.MMU_Paused:
            self.respond("Heater timeout detected!")
            self.extruder_set_temperature(0, False)
        nextwake = self.reactor.NEVER
        return nextwake

    # -----------------------------------------------------------------------------------------------------------------------------
    # GCode Registration
    # -----------------------------------------------------------------------------------------------------------------------------
    def register_commands(self):
        self.gcode.register_command('HOME_ROME', self.cmd_HOME_ROME, desc=("HOME_ROME"))
        self.gcode.register_command('LOAD_TOOL', self.cmd_LOAD_TOOL, desc=("LOAD_TOOL"))
        self.gcode.register_command('UNLOAD_TOOL', self.cmd_UNLOAD_TOOL, desc=("UNLOAD_TOOL"))
        self.gcode.register_command('CHANGE_TOOL', self.cmd_CHANGE_TOOL, desc=("CHANGE_TOOL"))
        self.gcode.register_command('ROME_END_PRINT', self.cmd_ROME_END_PRINT, desc=("ROME_END_PRINT"))
        self.gcode.register_command('ROME_START_PRINT', self.cmd_ROME_START_PRINT, desc=("ROME_START_PRINT"))
        self.gcode.register_command('LOAD_TO_SENSOR', self.cmd_LOAD_TO_SENSOR, desc=("LOAD_TO_SENSOR"))

    def cmd_LOAD_TO_SENSOR(self, param):
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count - 1)
        temp = param.get_int('TEMP', None, minval=-1, maxval=self.heater.max_temp)
        if not self.select_tool(tool):
            self.pause_rome()
            return
        if not self.load_to_toolhead_sensor(tool):
            self.pause_rome()
            return

    def cmd_LOAD_TOOL(self, param):
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count - 1)
        temp = param.get_int('TEMP', None, minval=-1, maxval=self.heater.max_temp)
        if not self.load_tool(tool, temp):
            self.pause_rome()
            return

    def cmd_UNLOAD_TOOL(self, param):
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

    def cmd_ROME_START_PRINT(self, param):
        self.Tool_Swaps = 0
        TOOL = param.get_int('TOOL', None, minval=0, maxval=4)
        BED_TEMP = param.get_int('BED_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        EXTRUDER_TEMP = param.get_int('EXTRUDER_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        self.gcode.run_script_from_command("_ROME_START_PRINT TOOL=" + str(TOOL) + " BED_TEMP=" + str(BED_TEMP) + " EXTRUDER_TEMP=" + str(EXTRUDER_TEMP))

    # -----------------------------------------------------------------------------------------------------------------------------
    # Home
    # -----------------------------------------------------------------------------------------------------------------------------
    Homed = False

    def home(self):
        self.respond("Homing ROME...")

        self.Homed = False
        self.ROME_Paused = False
        self.Tool_Swaps = 0

        if not self.can_home():
            self.respond("Can not home ROME!")
            return False

        if not self.home_tools():
            self.respond("Can not home ROME Tools!")
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

    Tools_Homed = False
    def home_tools(self):
        if not self.load_to_toolhead_sensor(0):
            return False
        if not self.unload_from_toolhead_sensor(0):
            return False
        if not self.load_to_toolhead_sensor(1):
            return False
        if not self.unload_from_toolhead_sensor(1):
            return False
        self.Tools_Homed = True
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tool loader
    # -----------------------------------------------------------------------------------------------------------------------------
    Tool_Swaps = 0

    def change_tool(self, tool):
        if self.Tool_Swaps > 0:
            if not self.load_tool(tool, -1, True):
                return False
        self.Tool_Swaps = self.Tool_Swaps + 1
        return True

    def load_tool(self, tool, temp=-1, is_filament_change=False):
        self.respond("Load Tool " + str(tool))

        # check selected temperature
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
            # start heating
            self.respond("Heat up nozzle to " + str(temp))
            self.extruder_set_temperature(temp, False)

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
        if not self.unload_tool():
            return False
        if not self.select_tool(tool):
            return False
        if not self.load_to_toolhead_sensor(tool):
            return False
        if not self.load_from_filament_sensor_to_parking_position():
            return False
        if not self.load_from_parking_position_to_nozzle():
            return False

        self.respond("Tool " + str(tool) + " loaded")
        return True

    def rome_unload_tool(self, tool, temp=-1):
        self.respond("Load Tool " + str(tool))

        # check selected temperature
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
            # start heating
            self.respond("Heat up nozzle to " + str(temp))
            self.extruder_set_temperature(temp, False)

        # set temp if configured and wait for it
        if temp > 0:
            self.respond("Waiting for heater...")
            self.extruder_set_temperature(temp, True)

        # check hotend temperature
        if not self.extruder_can_extrude():
            self.respond("Hotend too cold!")
            self.respond("Heat up nozzle to " + str(self.heater.min_extrude_temp))
            self.extruder_set_temperature(self.heater.min_extrude_temp, True)

        # unload filament
        self.select_tool(tool)
        self.unload_to_toolhead_sensor()
        self.unload_from_toolhead_sensor(tool)

        self.respond("Tool " + str(tool) + " unloaded")
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # unload tool
    # -----------------------------------------------------------------------------------------------------------------------------
    def unload_tool(self):
        self.respond("unload_tool")
        if self.filament_sensor_triggered():
            if self.Selected_Tool >= 0:
                return self.unload_known_tool()
            else:
                return self.unload_unknown_tool()
        return True

    def unload_known_tool(self):
        self.respond("unload_known_tool")
        self.select_tool(self.Selected_Tool)
        self.unload_to_toolhead_sensor()
        self.unload_from_toolhead_sensor(self.Selected_Tool)
        return True

    def unload_unknown_tool(self):
        self.respond("unload_unknown_tool")
        self.select_tool()
        self.unload_to_toolhead_sensor()
        self.unload_from_toolhead_sensor()
        return True

    def unload_to_toolhead_sensor(self):
        self.respond("unload_to_toolhead_sensor")
        self.unload_from_nozzle_to_parking_position()
        if not self.move_from_nozzle_to_toolhead_sensor():
            return False
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # select tool
    # -----------------------------------------------------------------------------------------------------------------------------
    Selected_Tool = -1

    def select_tool(self, tool=-1):
        self.respond("select_tool")
        self.unselect_tool()
        if tool == 0 or tool == -1:
            self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=extruder')
        if tool == 1 or tool == -1:
            self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_2 MOTION_QUEUE=extruder')
        self.Selected_Tool = tool
        return True

    def unselect_tool(self):
        self.respond("unselect_tool")
        self.Selected_Tool = -1
        self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=')
        self.gcode.run_script_from_command('SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_2 MOTION_QUEUE=')

    # -----------------------------------------------------------------------------------------------------------------------------
    # load filament
    # -----------------------------------------------------------------------------------------------------------------------------
    def load_to_toolhead_sensor(self, tool):
        self.respond("load_to_toolhead_sensor")

        # select tool
        self.select_tool(tool)

        # initial move
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E' + str(self.sensor_to_reverse_bowden_parking_position_mm - 20) + ' F' + str(self.filament_homing_speed_mms * 60))
        self.gcode.run_script_from_command('M400')
        self.gcode.run_script_from_command('M400e')

        # try to find the sensor
        self.respond("try to find the sensor...")
        step_distance = 20
        max_step_count = 50
        if not self.filament_sensor_triggered():
            for i in range(max_step_count):
                self.gcode.run_script_from_command('G92 E0')
                self.gcode.run_script_from_command('G0 E' + str(step_distance) + ' F' + str(self.filament_homing_speed_mms * 60))
                self.gcode.run_script_from_command('M400')
                self.gcode.run_script_from_command('M400e')
                if self.filament_sensor_triggered():
                    break

        # check if sensor was found
        self.respond("check if sensor was found...")
        if not self.filament_sensor_triggered():
            self.respond("Could not find filament sensor!")
            return False

        # exact positioning
        self.respond("exact positioning...")
        step_distance = 3
        max_step_count = 20
        for i in range(max_step_count):
            self.gcode.run_script_from_command('G92 E0')
            self.gcode.run_script_from_command('G0 E-' + str(step_distance) + ' F' + str(self.filament_homing_speed_mms * 60))
            self.gcode.run_script_from_command('M400')
            self.gcode.run_script_from_command('M400e')
            if not self.filament_sensor_triggered():
                step_distance = 1
                for n in range(max_step_count):
                    self.gcode.run_script_from_command('G92 E0')
                    self.gcode.run_script_from_command('G0 E' + str(step_distance) + ' F' + str(self.filament_homing_speed_mms * 60))
                    self.gcode.run_script_from_command('M400')
                    self.gcode.run_script_from_command('M400e')
                    if self.filament_sensor_triggered():
                        break
                break

        # check exact positioning success
        self.respond("check exact positioning success...")
        if not self.filament_sensor_triggered():
            self.respond("Could not position the filament in the filament sensor!")
            return False

        # success
        self.respond("success")
        return True

    def load_from_filament_sensor_to_parking_position(self):
        self.respond("load_from_filament_sensor_to_parking_position")
        
        # move filament to extruder gears
        self.respond("load_from_filament_sensor_to_parking_position...")
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E' + str(self.sensor_to_extruder_gear_mm + self.extruder_gear_to_parking_position_mm) + ' F' + str(self.filament_parking_speed_mms * 60))
        self.gcode.run_script_from_command('M400e')

        # success
        return True

    def load_from_parking_position_to_nozzle(self):
        self.respond("load_from_parking_position_to_nozzle")
    
        # wait for printing temperature
        if self.unload_temperature > 0:
            self.extruder_set_temperature(self.print_temperature, True)

        # load filament into nozzle
        self.respond("load_from_parking_position_to_nozzle...")
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E' + str(self.parking_position_to_nozzle_mm) + ' F' + str(self.filament_loading_speed_mms * 60))
        self.gcode.run_script_from_command('G4 P1000')
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('M400e')

        # success
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # unload from sensor
    # -----------------------------------------------------------------------------------------------------------------------------
    def unload_from_toolhead_sensor(self, tool=-1):

        # select tool
        if tool >= 0:
            self.select_tool(tool)

        # eject filament
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E-' + str(self.sensor_to_reverse_bowden_parking_position_mm) + ' F' + str(self.filament_homing_speed_mms * 60))
        self.gcode.run_script_from_command('M400e')

        # check if filament is ejected
        if self.filament_sensor_triggered():
            return False

        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # unload from nozzle
    # -----------------------------------------------------------------------------------------------------------------------------
    def unload_from_nozzle_to_parking_position(self):
        self.gcode.run_script_from_command('_UNLOAD_FROM_NOZZLE_TO_PARKING_POSITION')

    # -----------------------------------------------------------------------------------------------------------------------------
    # move from nozzle to toolhead sensor
    # -----------------------------------------------------------------------------------------------------------------------------
    def move_from_nozzle_to_toolhead_sensor(self):

        # eject filament from extruder
        if self.filament_sensor_triggered():
            step_distance = 20
            max_step_count = 30
            for i in range(max_step_count):
                self.gcode.run_script_from_command('G92 E0')
                self.gcode.run_script_from_command('G0 E-' + str(step_distance) + ' F' + str(self.filament_parking_speed_mms * 60))
                self.gcode.run_script_from_command('M400e')
                if not self.filament_sensor_triggered():
                    break

        # check if filament is ejected
        if self.filament_sensor_triggered():
            return False

        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # ROME State 
    # -----------------------------------------------------------------------------------------------------------------------------
    ROME_Paused = False

    def pause_rome(self):
        self.ROME_Paused = True
        self.enable_heater_timeout()
        self.gcode.run_script_from_command('_ROME_PAUSE')

    def resume_rome(self):
        self.ROME_Paused = False
        self.disable_heater_timeout()
        self.after_change()
        self.gcode.run_script_from_command("_ROME_RESUME")

    # -----------------------------------------------------------------------------------------------------------------------------
    # Helper
    # -----------------------------------------------------------------------------------------------------------------------------
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

def load_config(config):
    return ROME(config)

