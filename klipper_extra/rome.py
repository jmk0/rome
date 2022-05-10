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
        #self.extruder_filament_sensor = self.printer.lookup_object("filament_switch_sensor extruder_filament_sensor")

        self.load_settings()
        self.register_commands()
        self.register_handle_connect()

    def load_settings(self):
        self.gear_stepper = None
        self.idler_stepper = None
        self.selector_stepper = None
        self.selector_endstop = None

        self.print_temperature = self.config.getfloat('print_temperature', 240)
        self.unload_temperature = self.config.getfloat('unload_temperature', 200)

        self.tool_positions = self.config.getintlist('tool_positions')
        self.idler_positions = self.config.getintlist('idler_positions')
        self.tool_count = len(self.tool_positions) - 1

        self.length_sensor_to_gears_mm = self.config.getfloat('length_sensor_to_gears_mm', 22.0)
        self.length_gears_to_parking_position_mm = self.config.getfloat('length_gears_to_parking_position_mm', 30.0)
        self.length_parking_position_to_nozzle_mm = self.config.getfloat('length_parking_position_to_nozzle_mm', 30.0)
        self.load_in_extruder_mm = self.config.getfloat('load_in_extruder_mm', 30.0)
        self.load_in_nozzle_mm = self.config.getfloat('load_in_nozzle_mm', 40.0)

        self.nozzle_loading_speed = self.config.getfloat('nozzle_loading_speed', 80.0)
        self.nozzle_loading_accel = self.config.getfloat('nozzle_loading_accel', 90.0)
        self.bowden_loading_speed = self.config.getfloat('bowden_loading_speed', 80.0)
        self.bowden_loading_accel = self.config.getfloat('bowden_loading_accel', 90.0)
        self.selector_loading_speed = self.config.getfloat('selector_loading_speed', 85.0)
        self.selector_loading_accel = self.config.getfloat('selector_loading_accel', 4000.0)
        self.selector_selecting_speed = self.config.getfloat('selector_selecting_speed', 45.0)
        self.selector_selecting_accel = self.config.getfloat('selector_selecting_accel', 100.0)
        self.selector_homeing_speed = self.config.getfloat('selector_homeing_speed', 45.0)
        self.selector_homeing_accel = self.config.getfloat('selector_homeing_accel', 100.0)
        self.idler_homeing_speed = self.config.getfloat('idler_homeing_speed', 40.0)
        self.idler_homeing_accel = self.config.getfloat('idler_homeing_accel', 40.0)
        self.idler_selecting_speed = self.config.getfloat('idler_selecting_speed', 125.0)
        self.idler_selecting_accel = self.config.getfloat('idler_selecting_accel', 80.0)
        self.bowden_length = self.config.getfloat('bowden_length', 900.0)
        self.selector_load_length = self.config.getfloat('selector_load_length', 120.0)
        self.selector_unload_length = self.config.getfloat('selector_unload_length', 25.0)
        self.idler_home_position = self.config.getfloat('idler_home_position', 85.0)
        self.heater_timeout = self.config.getfloat('heater_timeout', 600.0)

    def register_handle_connect(self):
        self.printer.register_event_handler("klippy:connect", self.execute_handle_connect)

    def execute_handle_connect(self):
        self.toolhead = self.printer.lookup_object('toolhead')
        self.extruder = self.printer.lookup_object('extruder')
        self.pheaters = self.printer.lookup_object('heaters')
        self.heater = self.extruder.get_heater()

        # for manual_stepper in self.printer.lookup_objects('manual_stepper'):
        #     rail_name = manual_stepper[1].get_steppers()[0].get_name()
        #     if rail_name == 'manual_stepper selector_stepper':
        #         self.selector_stepper = manual_stepper[1]
        #     if rail_name == 'manual_stepper idler_stepper':
        #         self.idler_stepper = manual_stepper[1]
        #     if rail_name == 'manual_stepper gear_stepper':
        #         self.gear_stepper = manual_stepper[1]
        # if self.selector_stepper is None:
        #     raise self.config.error("Selector Stepper not found!")
        # if self.idler_stepper is None:
        #     raise self.config.error("Idler Stepper not found!")
        # if self.gear_stepper is None:
        #     raise self.config.error("Gear Stepper not found!")

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
        self.gcode.register_command('LOAD_TOOL', self.cmd_LOAD_TOOL, desc=("LOAD_TOOL"))
        self.gcode.register_command('CHANGE_TOOL', self.cmd_CHANGE_TOOL, desc=("CHANGE_TOOL"))
        self.gcode.register_command('UNLOAD_TOOL', self.cmd_UNLOAD_TOOL, desc=("UNLOAD_TOOL"))
        self.gcode.register_command('HOME_MMU', self.cmd_HOME_MMU, desc=("HOME_MMU"))
        self.gcode.register_command('HOME_IDLER', self.cmd_HOME_IDLER, desc=("HOME_IDLER"))
        self.gcode.register_command('HOME_SELECTOR', self.cmd_HOME_SELECTOR, desc=("HOME_SELECTOR"))
        self.gcode.register_command('SELECT_TOOL', self.cmd_SELECT_TOOL, desc=("SELECT_TOOL"))
        self.gcode.register_command('RESUME_MMU', self.cmd_RESUME_MMU, desc=("RESUME_MMU"))
        self.gcode.register_command('END_PRINT_MMU', self.cmd_END_PRINT_MMU, desc=("END_PRINT_MMU"))
        self.gcode.register_command('START_PRINT_MMU', self.cmd_START_PRINT_MMU, desc=("START_PRINT_MMU"))

    def cmd_LOAD_TOOL(self, param):
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count)
        temp = param.get_int('TEMP', None, minval=-1, maxval=self.heater.max_temp)
        if not self.load_tool(tool, temp):
            self.pause_mmu()
            return

    def cmd_CHANGE_TOOL(self, param):
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count)
        if not self.change_tool(tool):
            self.pause_mmu()

    def cmd_UNLOAD_TOOL(self, param):
        tool = param.get_int('TOOL', None, minval=-1, maxval=self.tool_count)
        if tool >= 0:
            self.home_idler()
            self.stepper_move(self.idler_stepper, self.idler_positions[tool], True, self.idler_selecting_speed, self.idler_selecting_accel)
            self.Selected_Filament = tool
        if not self.unload_tool():
            self.respond("Can not unload tool!")
        self.home_idler()

    def cmd_HOME_MMU(self, param):
        self.Homed = False
        if not self.home():
            self.respond("Can not home MMU!")

    def cmd_HOME_IDLER(self, param):
        self.Idler_Homed = False
        self.home_idler()

    def cmd_HOME_SELECTOR(self, param):
        self.Selector_Homed = False
        self.home_selector()

    def cmd_SELECT_TOOL(self, param):
        tool = param.get_int('TOOL', None, minval=0, maxval=self.tool_count)
        self.select_tool(tool)

    def cmd_RESUME_MMU(self, param):
        self.resume_mmu()

    def cmd_END_PRINT_MMU(self, param):
        self.gcode.run_script_from_command("_END_PRINT_MMU")

    def cmd_START_PRINT_MMU(self, param):
        self.Tool_Swaps = 0
        TOOL = param.get_int('TOOL', None, minval=0, maxval=4)
        BED_TEMP = param.get_int('BED_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        EXTRUDER_TEMP = param.get_int('EXTRUDER_TEMP', None, minval=-1, maxval=self.heater.max_temp)
        if param.get('WIPE_TOWER', None, str) == 'true':
            self.Wipe_Tower = True
        else:
            self.Wipe_Tower = False
        self.gcode.run_script_from_command("_START_PRINT_MMU TOOL=" + str(TOOL) + " BED_TEMP=" + str(BED_TEMP) + " EXTRUDER_TEMP=" + str(EXTRUDER_TEMP))

    # -----------------------------------------------------------------------------------------------------------------------------
    # Home
    # -----------------------------------------------------------------------------------------------------------------------------
    Homed = False
    def home(self):
        self.respond("Homeing ROME...")

        self.Homed = False
        self.MMU_Paused = False
        self.Tool_Swaps = 0
        self.Selected_Tool = -1
        self.Selected_Filament = -1
        self.Idler_Homed = False
        self.Selector_Homed = False

        if not self.can_home():
            self.respond("Can not home MMU!")
            return False

        self.home_idler()
        self.home_selector()

        self.Homed = True
        self.respond("Welcome home ROME!")
        return True

    def can_home(self):

        # check extruder
        if self.filament_sensor_triggered():
            self.respond("Filament in extruder detected!")

            # check hotend temperature
            if not self.extruder_can_extrude():
                self.respond("Preheat Nozzle to configured " + self.heater.min_extrude_temp)
                self.extruder_set_temperature(self.heater.min_extrude_temp, True)

            # unload filament rom nozzle
            if not self.unload_from_nozzle():
                self.respond("Can not unload from nozzle!")
                return False

            # turn off hotend heater
            self.extruder_set_temperature(0, False)

            # check
            if self.filament_sensor_triggered():
                self.respond("Filament stuck in extruder!")
                return False

        # check selector
        if self.stepper_endstop_triggered(self.gear_stepper):

            # move from extruder to selector
            self.gear_stepper.do_set_position(0.0)
            self.stepper_homing_move(self.gear_stepper, -(self.bowden_length + 100), True, self.bowden_loading_speed, self.bowden_loading_accel, -2)

            # move from selector to mmu
            self.gear_stepper.do_set_position(0.0)
            self.stepper_move(self.gear_stepper, -self.selector_unload_length, True, self.selector_loading_speed, self.selector_loading_accel)

            # park filament
            self.gear_stepper.do_set_position(0.0)
            self.stepper_move(self.gear_stepper, -10, True, self.selector_loading_speed, self.selector_loading_accel)

            # check
            if self.stepper_endstop_triggered(self.gear_stepper):
                self.respond("Filament stuck in selector!")
                return False

        # success
        return True

    Idler_Homed = False
    def home_idler(self):
        if self.Idler_Homed:
            self.stepper_move(self.idler_stepper, self.idler_home_position, True, self.idler_homeing_speed, self.idler_homeing_accel)
            return
        home_current = 0.1
        driver_status = self.stepper_driver_status('idler_stepper')
        self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=idler_stepper CURRENT=' + str(home_current) + ' HOLDCURRENT=' + str(home_current))
        self.idler_stepper.do_set_position(0.0)
        self.stepper_move(self.idler_stepper, 7, True, self.idler_homeing_speed, self.idler_homeing_accel)
        self.stepper_homing_move(self.idler_stepper, -95, True, self.idler_homeing_speed, self.idler_homeing_accel, 1)
        self.idler_stepper.do_set_position(2.0)
        self.stepper_move(self.idler_stepper, self.idler_home_position, True, self.idler_homeing_speed, self.idler_homeing_accel)
        self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=idler_stepper CURRENT=' + str(driver_status['run_current']) + ' HOLDCURRENT=' + str(driver_status['hold_current']))
        self.Idler_Homed = True

    Selector_Homed = False
    def home_selector(self):
        if self.Selector_Homed:
            self.stepper_homing_move(self.selector_stepper, 1, True, self.selector_homeing_speed, self.selector_homeing_accel, 1)
            return
        home_current = 0.3
        driver_status = self.stepper_driver_status('selector_stepper')
        self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=selector_stepper CURRENT=' + str(home_current) + ' HOLDCURRENT=' + str(home_current))
        self.selector_stepper.do_set_position(0.0)
        self.stepper_homing_move(self.selector_stepper, 5, True, self.selector_homeing_speed, self.selector_homeing_accel, 1)
        self.selector_stepper.do_set_position(0.0)
        self.stepper_homing_move(self.selector_stepper, -76, True, self.selector_homeing_speed, self.selector_homeing_accel, 1)
        self.selector_stepper.do_set_position(0.0)
        self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=selector_stepper CURRENT=' + str(driver_status['run_current']) + ' HOLDCURRENT=' + str(driver_status['hold_current']))
        self.Selector_Homed = True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Tool loader
    # -----------------------------------------------------------------------------------------------------------------------------
    Tool_Swaps = 0
    Wipe_Tower = False

    def change_tool(self, tool):
        if self.Tool_Swaps > 0:
            self.before_change()
            # if not self.Wipe_Tower:
            #     self.gcode.run_script_from_command('_EXCHANGE')
            if not self.load_tool(tool, -1, True):
                return False
            # if not self.Wipe_Tower:
            #     self.gcode.run_script_from_command('_EXCHANGE_FILAMENT')
            self.after_change()
        self.Tool_Swaps = self.Tool_Swaps + 1
        return True

    def load_tool(self, tool, temp=-1, is_filament_change=False):
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

        # home mmu if not homed yet
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

        # unload tool if necessary
        if is_filament_change:
            if not self.unload_tool(is_filament_change):
                return False

        # load filament
        if not self.select_tool(tool):
            return False
        if not self.load_filament_to_selector(tool):
            return False
        if not self._from_selector_to_filament_sensor():
            return False
        if not self._from_filament_sensor_to_extruder_gears():
            return False
        if not self._from_extruder_gears_to_parking_position():
            return False
        if not self._from_parking_position_to_nozzle():
            return False

        self.respond("Tool " + str(tool) + " loaded")
        return True

    def unload_tool(self, is_filament_change=False):
        self.respond("Unloading tool...")

        # check for filament 
        if not is_filament_change:
            if not self.stepper_endstop_triggered(self.gear_stepper) and not self.unload_from_nozzle():
                self.respond("No filament found!")
                return True

        # Unload from extruder if necessary
        if self.filament_sensor_triggered():
            if not self.unload_from_nozzle():
                return False
            if not self.unload_from_extruder():
                return False

        # Unload from selector if necessary
        if self.stepper_endstop_triggered(self.gear_stepper):
            if not self._from_selector_to_parking_position():
                return False

        # success
        self.Selected_Tool = -1
        self.Selected_Filament = -1
        self.respond("Tool unloaded!")
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Exchange 
    # -----------------------------------------------------------------------------------------------------------------------------
    exchange_lift_speed = 60
    exchange_travel_speed = 750
    exchange_old_position = None

    nozzle_cleaner_print_head_x = 18
    nozzle_cleaner_print_head_y = 35
    nozzle_cleaner_print_head_z = 55

    def before_change(self):
        offset = 25
        self.gcode.run_script_from_command('SAVE_GCODE_STATE NAME=PAUSE_state')
        self.exchange_old_position = self.toolhead.get_position()
        if self.unload_temperature > 0:
            self.gcode.run_script_from_command('M104 ' + str(self.unload_temperature))
        self.gcode.run_script_from_command('G92 E0')
        start_time = time.clock()
        self.gcode.run_script_from_command('G0 E-5 Y' + str(self.exchange_old_position[1] + offset) + ' F7200')
        self.gcode.run_script_from_command('G0 Z' + str(self.exchange_old_position[2] + self.nozzle_cleaner_print_head_z) + ' F' + str(self.exchange_lift_speed * 60))
        self.gcode.run_script_from_command('G0 X' + str(self.nozzle_cleaner_print_head_x) + ' Y' + str(self.nozzle_cleaner_print_head_y) + ' F' + str(self.exchange_travel_speed * 60))
        self.gcode.run_script_from_command('NOZZLE_CLEANER_DEPLOY')
        self.gcode.run_script_from_command('M400')
        elapsed_time = time.clock() - start_time
        if elapsed_time < 3.:
            self.respond('elapsed_time = ' + str(elapsed_time))
            self.gcode.run_script_from_command('G4 P' + str(3. - elapsed_time))

    def after_change(self):
        self.gcode.run_script_from_command('NOZZLE_CLEANER_PARK')
        self.gcode.run_script_from_command('G4 P500')
        self.gcode.run_script_from_command('G0 X' + str(self.exchange_old_position[0]) + ' Y' + str(self.exchange_old_position[1]) + ' F' + str(self.exchange_travel_speed * 60))
        self.gcode.run_script_from_command('G0 Z' + str(self.exchange_old_position[2]) + ' F' + str(self.exchange_lift_speed * 60))

    # -----------------------------------------------------------------------------------------------------------------------------
    # MMU State 
    # -----------------------------------------------------------------------------------------------------------------------------
    MMU_Paused = False

    def pause_mmu(self):
        self.MMU_Paused = True
        self.enable_heater_timeout()
        self.gcode.run_script_from_command('_PAUSE_MMU')

    def resume_mmu(self):
        self.MMU_Paused = False
        self.disable_heater_timeout()
        self.after_change()
        self.gcode.run_script_from_command("_RESUME_MMU")

    # -----------------------------------------------------------------------------------------------------------------------------
    # select tool
    # -----------------------------------------------------------------------------------------------------------------------------
    Selected_Tool = -1
    Selected_Filament = -1

    def select_tool(self, tool):
        self.respond("Selecting tool " + str(tool) + "...")
        self.select_idler(tool)
        self.select_selector(tool)
        self.Selected_Tool = tool
        self.Selected_Filament = tool
        self.gcode.run_script_from_command("M400")
        self.respond("Tool " + str(tool) + " selected")
        return True

    def select_idler(self, tool):
        if not self.Homed:
            return
        if tool >= 0:
            self.stepper_move(self.idler_stepper, self.idler_positions[tool], True, self.idler_selecting_speed, self.idler_selecting_accel)
        else:
            self.stepper_move(self.idler_stepper, self.idler_home_position, True, self.idler_selecting_speed, self.idler_selecting_accel)

    def select_selector(self, tool):
        if not self.Homed:
            return
        if tool >= 0:
            self.stepper_move(self.selector_stepper, self.tool_positions[tool], True, self.selector_selecting_speed, self.selector_selecting_accel)
        else:
            self.stepper_move(self.selector_stepper, 0, True, self.selector_selecting_speed, self.selector_selecting_accel)

    def unselect_tool(self):

        # releasing idler
        self.respond("release idler...")
        self.select_idler(-1)
        self.Selected_Tool = -1

    # -----------------------------------------------------------------------------------------------------------------------------
    # load filament to selector
    # -----------------------------------------------------------------------------------------------------------------------------
    def load_filament_to_selector(self, tool):
        if self.stepper_endstop_triggered(self.gear_stepper):
            self.respond("Can not load Filament because it is already loaded!")
            return False
        if not self._from_parking_position_to_selector():
            return False
        if not self._test_selector_bowden_tube():
            if self._fix_filament_position_in_selector():
                return False
            if not self._push_filament_in_bowden():
                self._fix_filament_position_in_selector()
                return False
        return True

    def _from_parking_position_to_selector(self):

        # load filament to finda
        self.gear_stepper.do_set_position(0.0)
        self.stepper_homing_move(self.gear_stepper, self.selector_load_length, True, self.selector_loading_speed, self.selector_loading_accel, 2)
        self.gear_stepper.do_set_position(0.0)
        self.stepper_move(self.gear_stepper, 10, True, self.selector_loading_speed, self.selector_loading_accel)

        # check
        if not self.stepper_endstop_triggered(self.gear_stepper):
            self.respond("Could not load filament to finda!")
            return False

        # success
        return True

    def _from_selector_to_parking_position(self):

        # unload from selector
        self.gear_stepper.do_set_position(0.0)
        self.stepper_move(self.gear_stepper, -self.selector_unload_length, True, self.selector_loading_speed, self.selector_loading_accel)

        # check
        if self.stepper_endstop_triggered(self.gear_stepper):
            self.respond("Can not unload filament from selector!")
            return False

        # success
        return True

    def _test_selector_bowden_tube(self):
    
        # load filament into bowden tube
        self.gear_stepper.do_set_position(0.0)
        self.stepper_move(self.gear_stepper, self.selector_unload_length * 2, True, self.selector_loading_speed, self.selector_loading_accel)

        # unload only half the way from bowden tube
        self.stepper_move(self.gear_stepper, self.selector_unload_length, True, self.selector_loading_speed, self.selector_loading_accel)

        # sensor should still be triggered
        if not self.stepper_endstop_triggered(self.gear_stepper):
            self.respond("Could not load filament to bowden!")
            return False

        # unload from finda
        self.gear_stepper.do_set_position(0.0)
        self.stepper_homing_move(self.gear_stepper, -(self.selector_unload_length * 2), True, self.selector_loading_speed, self.selector_loading_accel, -2)
        self.gear_stepper.do_set_position(0.0)
        self.stepper_move(self.gear_stepper, -10, True, self.selector_loading_speed, self.selector_loading_accel)

        # load again to finda
        if not self._from_parking_position_to_selector():
            self.respond("Could not reload filament to bowden!")
            return False

        # success
        return True

    def _fix_filament_position_in_selector(self):
        
        # current filament position is unknown, try to fix that
        if not self._from_parking_position_to_selector():
            self.respond("Could not fix filament position!")
            return False

        # park filament 
        if not self._from_selector_to_parking_position():
            self.respond("Could park filament after fixing its position!")
            return False

        # success
        return True

    def _push_filament_in_bowden(self):
        
        # raise stepper power
        driver_status = self.stepper_driver_status('gear_stepper')
        self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=gear_stepper CURRENT=' + str(driver_status['run_current'] * 1.25) + ' HOLDCURRENT=' + str(driver_status['hold_current'] * 1.25))

        # test bowden tube
        result = self._test_selector_bowden_tube()

        # reset stepper power
        self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=gear_stepper CURRENT=' + str(driver_status['run_current']) + ' HOLDCURRENT=' + str(driver_status['hold_current']))

        # exit
        return result

    # -----------------------------------------------------------------------------------------------------------------------------
    # load filament to extruder
    # -----------------------------------------------------------------------------------------------------------------------------
    def _from_selector_to_filament_sensor(self):
    
        # move filament in front of the extruder
        self.respond("move filament in front of the extruder...")
        self.gear_stepper.do_set_position(0.0)
        self.stepper_move(self.gear_stepper, self.bowden_length, True, self.bowden_loading_speed, self.bowden_loading_accel)

        # try to find the sensor
        self.respond("try to find the sensor...")
        step_distance = 10
        max_step_count = 30
        position = self.bowden_length
        if not self.filament_sensor_triggered():
            for i in range(max_step_count):
                position = position + step_distance
                self.stepper_move(self.gear_stepper, position, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
                if self.filament_sensor_triggered():
                    break

        # check if sensor was found
        self.respond("check if sensor was found...")
        if not self.filament_sensor_triggered():
            self.respond("Could not find filament sensor!")
            return False

        # exact positioning
        self.respond("exact positioning...")
        step_distance = 1
        max_step_count = 15
        position = 0
        self.gear_stepper.do_set_position(0.0)
        for i in range(max_step_count):
            position = position - step_distance
            self.stepper_move(self.gear_stepper, position, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
            if not self.filament_sensor_triggered():
                for n in range(max_step_count):
                    position = position + step_distance
                    self.stepper_move(self.gear_stepper, position, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
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

    def _from_filament_sensor_to_extruder_gears(self):
    
        # move filament to extruder gears
        self.respond("move filament to extruder gears...")
        self.gear_stepper.do_set_position(0.0)
        self.stepper_move(self.gear_stepper, self.length_sensor_to_gears_mm, True, self.bowden_loading_speed, self.bowden_loading_accel)

        # success
        return True

    def _from_extruder_gears_to_parking_position(self):

        # park filament in hotend
        self.respond("parking filament in hotend...")
        self.gcode.run_script_from_command("G91")
        self.gcode.run_script_from_command("G92 E0")
        self.gear_stepper.do_set_position(0.0)
        self.gcode.run_script_from_command('MANUAL_STEPPER STEPPER=gear_stepper MOVE=' + str(self.length_gears_to_parking_position_mm) + ' SPEED=20 SET_POSITION=0 SYNC=0')
        self.gcode.run_script_from_command('G1 E' + str(self.length_gears_to_parking_position_mm) + ' F1200')
        self.gcode.run_script_from_command('MANUAL_STEPPER STEPPER=gear_stepper SYNC=1')
        self.gcode.run_script_from_command('MANUAL_STEPPER STEPPER=gear_stepper SET_POSITION=0')
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('M400')

        # MANUAL_STEPPER STEPPER=rome_extruder_1 MOVE=50

        # success
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # load/unload to/from Nozzle
    # -----------------------------------------------------------------------------------------------------------------------------
    def _from_parking_position_to_nozzle(self):

        # unselect tool
        self.unselect_tool()

        # wait for printing temperature
        if self.unload_temperature > 0:
            self.extruder_set_temperature(self.print_temperature, True)

        extruder_run_current = 0.707
        extruder_push_current = 1.0

        # load filament into nozzle
        self.respond("load filament into nozzle...")
        self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=extruder CURRENT=' + str(extruder_push_current))
        self.gcode.run_script_from_command('G91')
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G0 E' + str(self.length_parking_position_to_nozzle_mm) + ' F600')
        self.gcode.run_script_from_command('G4 P1000')
        self.gcode.run_script_from_command('G92 E0')
        self.gcode.run_script_from_command('G90')
        self.gcode.run_script_from_command('M400e')
        self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=extruder CURRENT=' + str(extruder_run_current))

        # driver_status = self.stepper_driver_status('gear_stepper')
        # self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=gear_stepper CURRENT=' + str(driver_status['run_current'] * 1.2) + ' HOLDCURRENT=' + str(driver_status['hold_current'] * 1.2))
        # self.gcode.run_script_from_command('G91')
        # self.gcode.run_script_from_command('G92 E0')
        # self.gcode.run_script_from_command('MANUAL_STEPPER STEPPER=gear_stepper MOVE=' + str(self.length_parking_position_to_nozzle_mm) + ' SPEED=5 SET_POSITION=0 SYNC=0')
        # self.gcode.run_script_from_command('G1 E' + str(self.length_parking_position_to_nozzle_mm) + ' F300')
        # self.gcode.run_script_from_command('MANUAL_STEPPER STEPPER=gear_stepper SYNC=1')
        # self.gear_stepper.do_set_position(0.0)
        # self.gcode.run_script_from_command('G92 E0')
        # self.gcode.run_script_from_command('G90')
        # self.gcode.run_script_from_command("M400e")
        # self.gcode.run_script_from_command('SET_TMC_CURRENT STEPPER=gear_stepper CURRENT=' + str(driver_status['run_current']) + ' HOLDCURRENT=' + str(driver_status['hold_current']))

        # unselect tool
        # self.unselect_tool()

        # success
        return True

    def unload_from_nozzle(self, is_filament_change=False):

        # cooling down nozzle to minimum extrusion temperature
        if self.unload_temperature > 0:
            self.respond('waiting for unload temperature of ' + str(self.unload_temperature))
            self.extruder_set_temperature(self.unload_temperature, True)

        # unload from nozzle
        self.respond('unloading from nozzle...')
        if is_filament_change:
            self.gcode.run_script_from_command('_FILAMENT_CHANGE_UNLOAD_WITHOUT_RAMMING_MMU')
        else:
            self.gcode.run_script_from_command('_UNLOAD_WITHOUT_RAMMING_MMU')

        # set nozzle again to printing temperature
        if self.unload_temperature > 0:
            self.extruder_set_temperature(self.print_temperature, False)

        # check if selected filament is known
        if self.Selected_Filament < 0:
            self.respond("Can not unload unknown filament!")
            self.respond("Try unloading it manually with UNLOAD_TOOL TOOL=(NUMBER OF TOOL TO UNLOAD)!")
            return False

        # select tool
        if not self.select_tool(self.Selected_Filament):
            return False

        # eject filament from extruder
        self.gear_stepper.do_set_position(0.0)
        self.stepper_move(self.gear_stepper, -self.load_in_extruder_mm, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        if self.filament_sensor_triggered():
            position = 0
            step_distance = 10
            max_step_count = 10
            self.gear_stepper.do_set_position(0.0)
            for i in range(max_step_count):
                position = position - step_distance
                self.stepper_move(self.gear_stepper, position, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
                if not self.stepper_endstop_triggered(self.gear_stepper):
                    break

        # check if filament is ejected
        if self.filament_sensor_triggered():
            if not self.clean_filament_sensor():
                return False

        # success
        return True

    def clean_filament_sensor(self):
    
        # try to clean filament sensor
        self.respond("cleaning filament sensor...")
        self.gear_stepper.do_set_position(0.0)
        self.stepper_move(self.gear_stepper, -10, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        self.stepper_move(self.gear_stepper, 10, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        self.stepper_move(self.gear_stepper, -20, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        self.stepper_move(self.gear_stepper, 20, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        self.stepper_move(self.gear_stepper, -30, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        self.stepper_move(self.gear_stepper, 30, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        self.stepper_move(self.gear_stepper, -40, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        self.stepper_move(self.gear_stepper, 40, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
        self.stepper_move(self.gear_stepper, -50, True, self.nozzle_loading_speed, self.nozzle_loading_accel)

        # check
        if self.filament_sensor_triggered():
            self.respond("Filament stuck in extruder!")
            return False

        # success
        self.respond("Filament sensor cleaned!")
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # unload filament from extruder
    # -----------------------------------------------------------------------------------------------------------------------------
    def unload_from_extruder(self):
        if self.Selected_Tool < 0:
            self.respond("No tool selected, can not unload from extruder!")
            return False
        if not self.unload_filament_from_extruder_to_selector():
            return False
        if not self._from_selector_to_parking_position():
            return False
        return True

    def unload_filament_from_extruder_to_selector(self):

        # unload from extruder to selector
        self.gear_stepper.do_set_position(0.0)
        self.stepper_homing_move(self.gear_stepper, -self.bowden_length, True, self.selector_loading_speed, self.selector_loading_accel, -2)
        if self.stepper_endstop_triggered(self.gear_stepper):
            position = 0
            step_distance = 10
            max_step_count = 30
            self.gear_stepper.do_set_position(0.0)
            for i in range(max_step_count):
                position = position - step_distance
                self.stepper_move(self.gear_stepper, position, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
                if not self.stepper_endstop_triggered(self.gear_stepper):
                    for n in range(10):
                        position = position + 1
                        self.stepper_move(self.gear_stepper, position, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
                        if self.stepper_endstop_triggered(self.gear_stepper):
                            self.stepper_move(self.gear_stepper, position - 2, True, self.nozzle_loading_speed, self.nozzle_loading_accel)
                            break
                    break

        # check
        if self.stepper_endstop_triggered(self.gear_stepper):
            self.respond("Can not unload filament from extruder to selector!")
            return False
    
        # success
        return True

    # -----------------------------------------------------------------------------------------------------------------------------
    # Helper
    # -----------------------------------------------------------------------------------------------------------------------------
    def respond(self, message):
        self.gcode.respond_raw(message)

    def stepper_move(self, stepper, dist, wait, speed, accel):
        stepper.do_move(dist, speed, accel, True)
        if wait:
            self.toolhead.wait_moves()      

    def stepper_homing_move(self, stepper, dist, wait, speed, accel, homing_move):
        stepper.do_homing_move(dist, speed, accel, homing_move > 0, abs(homing_move) == 1)
        if wait:
            self.toolhead.wait_moves()      

    def stepper_endstop_triggered(self, manual_stepper):
        endstop = manual_stepper.rail.get_endstops()[0][0]
        state = endstop.query_endstop(self.toolhead.get_last_move_time())
        return bool(state)

    # def set_filament_sensor(self, enabled):
    #     self.extruder_filament_sensor.runout_helper.sensor_enabled = enabled

    def filament_sensor_triggered(self):
        return True
        #return bool(self.extruder_filament_sensor.runout_helper.filament_present)

    def extruder_set_temperature(self, temperature, wait):
        self.pheaters.set_temperature(self.heater, temperature, wait)

    def extruder_can_extrude(self):
        status = self.extruder.get_status(self.toolhead.get_last_move_time())
        result = status['can_extrude'] 
        return result

    def extruder_temperature(self):
        status = self.extruder.get_status(self.toolhead.get_last_move_time())
        result = status['temperature'] 
        return result

    def stepper_driver_status(self, stepper_name):
        driver_config = self.printer.lookup_object("tmc2209 manual_stepper " + stepper_name)
        return driver_config.get_status()

def load_config(config):
    return ROME(config)
