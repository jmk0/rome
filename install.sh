# Prevent running as root.
if [ ${UID} == 0 ]; then
    echo -e "DO NOT RUN THIS SCRIPT AS 'root' !"
    echo -e "If 'root' privileges needed, you will prompted for sudo password."
    exit 1
fi

# Force script to exit if an error occurs
set -e

# Find SRCDIR from the pathname of this script
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/ && pwd )"

# Default Parameters
KLIPPER_CONFIG_DIR=""
KLIPPER_CONFIG_MMU_DIR=""
KLIPPER_CONFIG_FEEDER_DIR=""
ROME_DIR=""
ROME_BASE_DIR=""
ROME_MMU_DIR=""
ROME_FEEDER_DIR=""
ROME_EXTRUDER_DIR=""
ROME_HOTENDS_DIR=""
ROME_SENSORS_DIR=""
KLIPPY_EXTRAS="${HOME}/klipper/klippy/extras"
RATOS_V1_CONFIG_DIR="${HOME}/klipper_config"
RATOS_V2_CONFIG_DIR="${HOME}/printer_data/config"

function get_ratos_version {
    if [ -d "${RATOS_V1_CONFIG_DIR}" ]; then
        echo -e "RatOS Version 1.x"
        KLIPPER_CONFIG_DIR="${RATOS_V1_CONFIG_DIR}"
    else
        if [ -d "${RATOS_V2_CONFIG_DIR}" ]; then
            echo -e "RatOS Version 2.x"
            KLIPPER_CONFIG_DIR="${RATOS_V2_CONFIG_DIR}"
        else
            echo -e "ERROR: No RatOS config folder found."
            exit 1
        fi
    fi
    KLIPPER_CONFIG_MMU_DIR="${CONFIG_DIR}/mmu"
    KLIPPER_CONFIG_FEEDER_DIR="${CONFIG_DIR}/feeder"
    ROME_DIR="${CONFIG_DIR}/rome"
    ROME_BASE_DIR="${CONFIG_DIR}/rome/base"
    ROME_MMU_DIR="${CONFIG_DIR}/rome/mmu"
    ROME_FEEDER_DIR="${CONFIG_DIR}/rome/feeder"
    ROME_EXTRUDER_DIR="${CONFIG_DIR}/rome/extruder"
    ROME_HOTENDS_DIR="${CONFIG_DIR}/rome/hotends"
    ROME_SENSORS_DIR="${CONFIG_DIR}/rome/sensors"
}

function stop_klipper {
    if [ "$(sudo systemctl list-units --full -all -t service --no-legend | grep -F "klipper.service")" ]; then
        echo "Klipper service found! Stopping during Install."
        sudo systemctl stop klipper
    else
        echo "Klipper service not found, please install Klipper first"
        exit 1
    fi
}

function start_klipper {
    echo "Restarting Klipper service!"
    sudo systemctl restart klipper
}

function create_rome_dir {
    if [ -d "${ROME_DIR}" ]; then
        rm -rf "${ROME_DIR}" 
    fi
    if [ -d "${KLIPPER_CONFIG_DIR}" ]; then
        echo "Creating rome folder..."
        mkdir "${ROME_DIR}"
    else
        echo -e "ERROR: ${KLIPPER_CONFIG_DIR} not found."
        exit 1
    fi
    if [ -d "${ROME_DIR}" ]; then
        echo "Creating rome base folder..."
        mkdir "${ROME_BASE_DIR}"
    else
        echo -e "ERROR: ${ROME_DIR} not found."
        exit 1
    fi
    if [ -d "${ROME_DIR}" ]; then
        echo "Creating rome mmu folder..."
        mkdir "${ROME_MMU_DIR}"
    else
        echo -e "ERROR: ${ROME_DIR} not found."
        exit 1
    fi
    if [ -d "${ROME_DIR}" ]; then
        echo "Creating rome feeder folder..."
        mkdir "${ROME_FEEDER_DIR}"
    else
        echo -e "ERROR: ${ROME_DIR} not found."
        exit 1
    fi
    if [ -d "${ROME_DIR}" ]; then
        echo "Creating rome extruder folder..."
        mkdir "${ROME_EXTRUDER_DIR}"
    else
        echo -e "ERROR: ${ROME_DIR} not found."
        exit 1
    fi
    if [ -d "${ROME_DIR}" ]; then
        echo "Creating rome hotends folder..."
        mkdir "${ROME_HOTENDS_DIR}"
    else
        echo -e "ERROR: ${ROME_DIR} not found."
        exit 1
    fi
    if [ -d "${ROME_DIR}" ]; then
        echo "Creating rome sensors folder..."
        mkdir "${ROME_SENSORS_DIR}"
    else
        echo -e "ERROR: ${ROME_DIR} not found."
        exit 1
    fi
}

function link_rome_macros {
    if [ -d "${KLIPPER_CONFIG_DIR}" ]; then
        if [ -d "${ROME_DIR}" ]; then
            echo "Linking macro files..."

            # Base
            ln -sf "${SRCDIR}/klipper_macro/base/config.cfg" "${ROME_BASE_DIR}/config.cfg"
            ln -sf "${SRCDIR}/klipper_macro/base/macros.cfg" "${ROME_BASE_DIR}/macros.cfg"

            # Extruder
            ln -sf "${SRCDIR}/klipper_macro/extruder/base.cfg" "${ROME_EXTRUDER_DIR/}/base.cfg"
            ln -sf "${SRCDIR}/klipper_macro/extruder/orbiter_504.cfg" "${ROME_EXTRUDER_DIR/}/orbiter_504.cfg"
            ln -sf "${SRCDIR}/klipper_macro/extruder/orbiter_1004.cfg" "${ROME_EXTRUDER_DIR}/orbiter_1004.cfg"

            # Feeder
            ln -sf "${SRCDIR}/klipper_macro/feeder/feeder_1_orbiter_504.cfg" "${ROME_FEEDER_DIR/}/feeder_1_orbiter_504.cfg"
            ln -sf "${SRCDIR}/klipper_macro/feeder/feeder_1_orbiter_1004.cfg" "${ROME_FEEDER_DIR}/feeder_1_orbiter_1004.cfg"
            ln -sf "${SRCDIR}/klipper_macro/feeder/feeder_2_orbiter_504.cfg" "${ROME_FEEDER_DIR}/feeder_2_orbiter_504.cfg"
            ln -sf "${SRCDIR}/klipper_macro/feeder/feeder_2_orbiter_1004.cfg" "${ROME_FEEDER_DIR}/feeder_2_orbiter_1004.cfg"

            # Sensors
            ln -sf "${SRCDIR}/klipper_macro/sensors/y1.cfg" "${ROME_SENSORS_DIR}/y1.cfg"
            ln -sf "${SRCDIR}/klipper_macro/sensors/y2.cfg" "${ROME_SENSORS_DIR}/y2.cfg"
            ln -sf "${SRCDIR}/klipper_macro/sensors/f1.cfg" "${ROME_SENSORS_DIR}/f1.cfg"
            ln -sf "${SRCDIR}/klipper_macro/sensors/f2.cfg" "${ROME_SENSORS_DIR}/f2.cfg"
            ln -sf "${SRCDIR}/klipper_macro/sensors/toolhead.cfg" "${ROME_SENSORS_DIR}/toolhead.cfg"

            # MMU Stepper
            ln -sf "${SRCDIR}/klipper_macro/mmu/idler.cfg" "${ROME_MMU_DIR}/idler.cfg"
            ln -sf "${SRCDIR}/klipper_macro/mmu/pulley.cfg" "${ROME_MMU_DIR}/pulley.cfg"

            # Hotends
            ln -sf "${SRCDIR}/klipper_macro/hotends/chc_pro.cfg" "${ROME_HOTENDS_DIR}/chc_pro.cfg"
            ln -sf "${SRCDIR}/klipper_macro/hotends/rapido_hf.cfg" "${ROME_HOTENDS_DIR}/rapido_hf.cfg"
            ln -sf "${SRCDIR}/klipper_macro/hotends/rapido_uhf.cfg" "${ROME_HOTENDS_DIR}/rapido_uhf.cfg"

        else
            echo -e "ERROR: ${ROME_DIR} not found."
            exit 1
        fi
    else
        echo -e "ERROR: ${KLIPPER_CONFIG_DIR} not found."
        exit 1
    fi
}

function copy_rome_macros {
    if [ -d "${KLIPPER_CONFIG_DIR}" ]; then
        if [ -d "${ROME_DIR}" ]; then
            echo "Copy macro files..."

            # Configs
            cp "${SRCDIR}/klipper_macro/mmu_splitter.cfg" "${ROME_DIR}/mmu_splitter.cfg"
            cp "${SRCDIR}/klipper_macro/extruder_feeder.cfg" "${ROME_DIR}/extruder_feeder.cfg"

        else
            echo -e "ERROR: ${ROME_DIR} not found."
            exit 1
        fi
    else
        echo -e "ERROR: ${KLIPPER_CONFIG_DIR} not found."
        exit 1
    fi
}

function link_rome_extras {
    if [ -d "${KLIPPY_EXTRAS}" ]; then
        echo "Linking extra file..."
        ln -sf "${SRCDIR}/klipper_extra/rome.py" "${KLIPPY_EXTRAS}/rome.py"
    else
        echo -e "ERROR: ${KLIPPY_EXTRAS} not found."
        exit 1
    fi
}

### MAIN

# Parse command line arguments
while getopts "c:h" arg; do
    if [ -n "${arg}" ]; then
        case $arg in
            c)
                KLIPPER_CONFIG_DIR=$OPTARG
                break
            ;;
            [?]|h)
                echo -e "\nUsage: ${0} -c /path/to/klipper_config"
                exit 1
            ;;
        esac
    fi
    break
done

# Run steps
get_ratos_version
stop_klipper
create_rome_dir
link_rome_macros
copy_rome_macros
link_rome_extras
start_klipper

# If something checks status of install
exit 0
