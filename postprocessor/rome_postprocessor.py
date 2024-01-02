# /usr/bin/python3

import sys
import re
import argparse
from shutil import ReadError, copy2
from os import path, remove, getenv

def argumentparser():
    """
        ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog=path.basename(__file__),
        description='** ROME Slicer Post Processing Script ** \n\r',
        epilog='Result: Removes wipe tower speed override for the first layer.')

    parser.add_argument('input_file', metavar='gcode-files', type=str, nargs='+',
                        help='One or more GCode file(s) to be processed '
                        '- at least one is required.')

    try:
        args = parser.parse_args()
        return args

    except IOError as msg:
        parser.error(str(msg))


def main(args):
    """
        MAIN
    """
    print(args.input_file)

    for sourcefile in args.input_file:
        if path.exists(sourcefile):
            process_gcodefile(args, sourcefile)


def process_gcodefile(args, sourcefile):
    """
        MAIN Processing.
        To do with ever file from command line.
    """

    # Read the ENTIRE GCode file into memory
    try:
        with open(sourcefile, "r", encoding='UTF-8') as readfile:
            lines = readfile.readlines()
    except ReadError as exc:
        print('FileReadError:' + str(exc))
        sys.exit(1)

    found_m220 = False
    rgx_find_m220 = r"^M220 S"

    found_layerchange = False
    rgx_find_layerchange = r"^;LAYER_CHANGE"

    writefile = None

    try:
        with open(sourcefile, "w", newline='\n', encoding='UTF-8') as writefile:
            # Loop over GCODE file
            for i, strline in enumerate(lines):

                if not found_m220:
                    rgx_layerchange = re.search(rgx_find_layerchange, strline, flags=re.IGNORECASE)
                    if rgx_layerchange:
                        found_layerchange = True

                rgx_m220 = re.search(rgx_find_m220, strline, flags=re.IGNORECASE)
                if rgx_m220 and found_layerchange and not found_m220:
                    found_m220 = True
                    strline = '' + '\n'

                writefile.write(strline)

    except Exception as exc:
        print("Oops! Something went wrong. " + str(exc))
        sys.exit(1)

    finally:
        writefile.close()
        readfile.close()

ARGS = argumentparser()

main(ARGS)
