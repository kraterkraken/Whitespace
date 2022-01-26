#!/usr/bin/python3
import whitespace as ws
import sys
# -------------------------------CLASSES
class WhitespaceConverter(ws.WhitespaceVM):

    def __init__(self, nicecode):
        super().__init__()

        # read each line of the source and build the Whitespace code
        for line in nicecode.split("\n"):
            if line.strip() == "":
                continue # skip blank lines

            (operation, sep, arg) = line.partition(" ")
            arg = arg.strip()
            opchars = self.find_opchars(operation)
            if opchars != "":
                self.code += opchars
                if operation in ("MARK", "CALL", "JUMP", "JUMPZERO", "JUMPNEG"):
                    self.code += self.label_to_ws(arg)
                elif operation in ("PUSH", "COPY", "SLIDE"):
                    self.code += self.num_to_ws(arg)
            else:
                exit(f"SYNTAX ERROR : BAD OPERATION : -{operation}-")

    def find_opchars(self, operation):
        # Return the Whitespace characters repsenting the given operation.
        # Return empty string if there is no such operation.
        if operation in self.OPERATIONS: return self.OPERATIONS[operation]
        else: return ""

    def num_to_ws(self, numstr):
        # Convert a number to its Whitespace representation.
        sign = ""
        if int(numstr) < 0:
            sign = ws.TAB
        else:
            sign = ws.SPACE
        binstr = bin(abs(int(numstr)))[2:] # slicing off the initial '0b'
        return sign + binstr.replace("0", ws.SPACE).replace("1", ws.TAB) + ws.LF

    def label_to_ws(self, label):
        # Convert a label of S, and T characters into Whitespace
        # (S becomes space, T becomes tab, and it is terminated with a \n)
        return label.replace("S", ws.SPACE).replace("T", ws.TAB) + ws.LF

    def output(self):
        pass


# -------------------------------MAIN PROGRAM
def main():
    # Handle command arguments
    purpose_string = "mkws.py - convert an easy-to-read program into Whitespace code.\n"
    usage_string = (
        "usage: mkws.py - | filename\n"
        "\n"
        "Options:\n"
        "  filename                An input file containing readable source code.\n"
        "  -                       Get the source code from STDIN (overrides filename)\n"
        "  --help                  Prints this help info\n"
        )

    filename = ""
    stdinarg = False
    for arg in sys.argv[1:]:
        if arg == "--help":
            print(purpose_string)
            print(usage_string)
            exit()
        elif arg == "-":
            stdinarg = True
        elif arg[0] == "-":
            print(f"{sys.argv[0]}: error: unknown option {arg}\n")
            print(usage_string)
            exit()
        else:
            filename = arg

    if not stdinarg and filename == "":
            print(f"{sys.argv[0]}: error: bad usage, must specify - or a filename\n")
            print(usage_string)
            exit()

    # Get the source code
    source_code = ""
    if stdinarg:
        source_code = sys.stdin.read()
    else:
        try:
            with open(filename) as f:
                source_code = f.read()
        except IOError:
            exit(f"{sys.argv[0]}: error: Could not open file {filename}")

    # Convert the source code to Whitespace
    wsc = WhitespaceConverter(source_code)
    print(wsc.code, end='')

if __name__ == "__main__":
    main()
