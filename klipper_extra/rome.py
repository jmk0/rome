import time
from math import fabs
from re import T

class ROME:

    # SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=extruder

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
        self.print_temperature = self.config.getfloat('print_temperature', 240)
        self.unload_temperature = self.config.getfloat('unload_temperature', 200)

    def register_handle_connect(self):
        self.printer.register_event_handler("klippy:connect", self.execute_handle_connect)

    def execute_handle_connect(self):
        self.toolhead = self.printer.lookup_object('toolhead')
        self.extruder = self.printer.lookup_object('extruder')
        self.pheaters = self.printer.lookup_object('heaters')
        self.heater = self.extruder.get_heater()

    # -----------------------------------------------------------------------------------------------------------------------------
    # GCode Registration
    # -----------------------------------------------------------------------------------------------------------------------------
    def register_commands(self):
        self.gcode.register_command('LOAD_TOOL', self.cmd_LOAD_TOOL, desc=("LOAD_TOOL"))
        self.gcode.register_command('ROME_END_PRINT', self.cmd_ROME_END_PRINT, desc=("ROME_END_PRINT"))
        self.gcode.register_command('ROME_START_PRINT', self.cmd_ROME_START_PRINT, desc=("ROME_START_PRINT"))

    def cmd_LOAD_TOOL(self, param):
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count)
        temp = param.get_int('TEMP', None, minval=-1, maxval=self.heater.max_temp)
        if not self.load_tool(tool, temp):
            self.pause_rome()
            return

    def cmd_ROME_END_PRINT(self, param):
        self.gcode.run_script_from_command("_ROME_END_PRINT")

    def cmd_ROME_START_PRINT(self, param):
        self.Tool_Swaps = 0
        TOOL = param.get_int('TOOL', None, minval=0, maxval=4)
        BED_TEMP = param.get_int('BED_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        EXTRUDER_TEMP = param.get_int('EXTRUDER_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        self.gcode.run_script_from_command("_ROME_START_PRINT TOOL=" + str(TOOL) + " BED_TEMP=" + str(BED_TEMP) + " EXTRUDER_TEMP=" + str(EXTRUDER_TEMP))

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tool loader
    # -----------------------------------------------------------------------------------------------------------------------------
    Tool_Swaps = 0

    def load_tool(self, tool, temp=-1):
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

        # load filament
        self.gcode.run_script_from_command("SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=")
        if (tool == 1):
            self.gcode.run_script_from_command("SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_1 MOTION_QUEUE=extruder")
        else:
            self.gcode.run_script_from_command("SYNC_EXTRUDER_MOTION EXTRUDER=rome_extruder_2 MOTION_QUEUE=extruder")

        self.respond("Tool " + str(tool) + " loaded")
        return True

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
