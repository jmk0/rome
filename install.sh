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
KLIPPER_CONFIG_DIR="${HOME}/klipper_config"
KLIPPY_EXTRAS="${HOME}/klipper/klippy/extras"
ROME_DIR="${HOME}/klipper_config/rome"

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
}

function link_rome_macros {
    if [ -d "${KLIPPER_CONFIG_DIR}" ]; then
        if [ -d "${ROME_DIR}" ]; then
            echo "Linking macro files..."
            ln -sf "${SRCDIR}/klipper_macro/config.cfg" "${ROME_DIR}/config.cfg"
            ln -sf "${SRCDIR}/klipper_macro/extruder_feeder.cfg" "${ROME_DIR}/extruder_feeder.cfg"
            ln -sf "${SRCDIR}/klipper_macro/extruder.cfg" "${ROME_DIR}/extruder.cfg"
            ln -sf "${SRCDIR}/klipper_macro/filament_sensor.cfg" "${ROME_DIR}/filament_sensor.cfg"
            ln -sf "${SRCDIR}/klipper_macro/mmu_splitter.cfg" "${ROME_DIR}/mmu_splitter.cfg"
            ln -sf "${SRCDIR}/klipper_macro/hardware.cfg" "${ROME_DIR}/hardware.cfg"
            ln -sf "${SRCDIR}/klipper_macro/macros.cfg" "${ROME_DIR}/macros.cfg"
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
stop_klipper
create_rome_dir
link_rome_macros
link_rome_extras
start_klipper

# If something checks status of install
exit 0
