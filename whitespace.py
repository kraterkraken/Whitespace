#!/usr/bin/python3
from collections import deque
import sys
import os
import re
# ------------------------------ CONSTANTS
SPACE = ' '
TAB = '\t'
LF = '\n'
HEAPSIZE = 512

# -------------------------------CLASSES
class WhitespaceVM:

    OPERATIONS = {
        "PUSH":       SPACE + SPACE,
        "DUPLICATE":  SPACE + LF    + SPACE,
        "COPY":       SPACE + TAB   + SPACE,
        "SWAP":       SPACE + LF    + TAB,
        "DISCARD":    SPACE + LF    + LF,
        "SLIDE":      SPACE + TAB   + LF,
        "ADD":        TAB   + SPACE + SPACE + SPACE,
        "SUBTRACT":   TAB   + SPACE + SPACE + TAB,
        "MULTIPLY":   TAB   + SPACE + SPACE + LF,
        "DIVIDE":     TAB   + SPACE + TAB   + SPACE,
        "MODULO":     TAB   + SPACE + TAB   + TAB,
        "STORE":      TAB   + TAB   + SPACE,
        "RETRIEVE":   TAB   + TAB   + TAB,
        "MARK":       LF    + SPACE + SPACE,
        "CALL":       LF    + SPACE + TAB,
        "JUMP":       LF    + SPACE + LF,
        "JUMPZERO":   LF    + TAB   + SPACE,
        "JUMPNEG":    LF    + TAB   + TAB,
        "RETURN":     LF    + TAB   + LF,
        "ENDPROGRAM": LF    + LF    + LF,
        "OUTCH":      TAB   + LF    + SPACE + SPACE,
        "OUTNUM":     TAB   + LF    + SPACE + TAB,
        "INCH":       TAB   + LF    + TAB   + SPACE,
        "INNUM":      TAB   + LF    + TAB   + TAB
    }

    class Token:
        def __init__(self, op="", arg=""):
            self.op = op
            self.arg = arg

    def __init__(self, code='', heapsize=HEAPSIZE):
        self.ip = 0                 # instruction pointer
        self.code = code            # string containing Whitespace code
        self.stack = deque()        # the internal data stack
        self.tokens = []            # contains the instructions after tokenizing
        self.heap = [0] * heapsize  # memory heap
        self.labels = {}            # dictionary of label,addr pairs for flow
        self.return_addrs = deque() # where to go back to when subroutine ends
        self.input_stream = ""      # a buffer to hold input
        self.next_input = 0         # the next thing to read from the stream
        self.debug_flag = False     # flag to control debug statements
        self.describe_flag = False  # flag to control whether we describe the source

    def debug_token(self, token):
        self.debug(f"{token.op} {token.arg}", showstack=True)

    def debug(self, str, end='\n', showstack=False):
        if (self.debug_flag):
            print(str, end="")
            if showstack:
                s = "["
                sep = ""
                for item in self.stack:
                    s = f"{s}{sep}{item}"
                    sep = ","
                print(f" stack={s}]")
            else:
                print("", end=end)

    def strip_comments(self):
        # since comments can be ANYWHERE, including in the middle of the
        # string of characters that represents a command, I decided the
        # easiest thing to do was to kill all the comments before parsing
        self.debug("Stripping comments ...")
        self.code = "".join([ch for ch in self.code if ch in (SPACE, TAB, LF)])

    def user_input(self):
        # read one character at a time from stdin.
        # can handle case where user types more than 1 character
        # by buffering the input into an input stream, and subsequetly
        # getting input from there until no more characters are left there.
        if self.next_input >= len(self.input_stream):
            self.next_input = 0
            self.input_stream = input()

        retval = self.input_stream[self.next_input]
        self.next_input += 1
        return retval

    def unwhite(self, s, max=-1):
        # Converts whitespace to letters, and converts everything else
        # to asterisks.  The max argument allows the caller to get at most
        # max characters back.  Note: negative max returns the entire string.
        ret = re.sub("[^ \t\n]", "*", s)
        ret = ret.replace(SPACE, "S").replace(TAB, "T").replace(LF, "L")
        if max >= 0: return ret[:max]
        else: return ret

    def parse_arg(self, operation):
        if operation in ("MARK", "CALL", "JUMP", "JUMPNEG", "JUMPZERO"):
            label = ""
            while self.ip < len(self.code) and self.code[self.ip] != LF:
                label += self.code[self.ip]
                self.ip += 1
            # not sure if python can index a dictionary with whitespace characters
            # so I'll "unwhite" the labels first.  it will be easier to read
            # during debug or describe mode anyway.
            label = self.unwhite(label)
            self.ip += 1
            return label

        elif operation in ("PUSH", "COPY", "SLIDE"):
            num = 0
            mult = 0
            if self.code[self.ip] == SPACE:
                # start of positive number
                mult = 1
            elif self.code[self.ip] == TAB:
                # start of negative number
                mult = -1
            else:
                exit("SYNTAX ERROR : BAD SIGN")

            self.ip = self.ip + 1
            while self.ip < len(self.code) and self.code[self.ip] != LF:
                # about to add a new digit, so left shift the digits we have so far
                num = num << 1
                if self.code[self.ip] == TAB:
                    # found a 1
                    num = num | 1
                elif self.code[self.ip] == SPACE:
                    # found a 0 (the left shift already put a zero in there)
                    pass
                else:
                    exit("SYNTAX ERROR : BAD NUMBER")
                self.ip = self.ip + 1
            self.ip = self.ip + 1 # ip now points to the character after the LF

            return num * mult
        else:
            return ""

    def is_op(self, candidate):
        left = len(self.code) - self.ip

        if left < len(candidate):
            # return false when there aren't enough chars left for this candidate
            return False
        elif self.code[self.ip:self.ip+len(candidate)] == candidate:
            # the current code matches the candidate we're looking for
            # so return true and move the instruction pointer so that
            # it points to the character after the instruction
            self.ip = self.ip + len(candidate)
            return True
        else:
            # we didn't find the candidate here
            return False

    def describe(self):
        for token in self.tokens:
            print(f"{token.op} {token.arg}")

    def scan_labels(self):
        # We have to scan the entire program for labels (before execution)
        # otherwise we might encounter a jump-to-label command for a label
        # that hasn't been encountered yet.
        self.debug("Scanning for labels ...")
        for i, token in enumerate(self.tokens):
            if token.op == "MARK":
                self.debug(f"  Marking token #{i} with label {token.arg}")
                self.labels[token.arg] = i

    def tokenize(self):
        # Converts the code string of incomprehensible whitespace
        # into a nice list of readable tokens for execution (and display).
        self.debug("Tokenizing ...")
        while self.ip < len(self.code):
            self.debug(f"  {self.unwhite(self.code[self.ip:], max=45)}")
            found = False
            for name, opchars in self.OPERATIONS.items():
                if self.is_op(opchars):
                    arg = self.parse_arg(name)
                    self.debug(f"  Parsed this: {self.unwhite(opchars)}-->{name} {arg}")
                    token = self.Token(name, arg)
                    self.tokens.append(token)
                    found = True
                    break
            if not found:
                exit(f"SYNTAX ERROR : BAD OPERATION : "
                    f"{self.unwhite(self.code[self.ip:], max=45)}")

    def run(self):
        self.strip_comments()
        self.tokenize()
        if (self.describe_flag):
            self.describe()
        else:
            self.scan_labels()
            self.execute()

    def execute(self):
        self.debug("Executing ...\n")
        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]
            self.debug_token(token)
            if token.op == "PUSH":
                self.stack.appendleft(token.arg)
            elif token.op == "DUPLICATE":
                self.stack.appendleft(self.stack[0]) # blows up if stack empty
            elif token.op == "COPY":
                val = self.stack[token.arg]
                self.stack.appendleft(val)
            elif token.op == "SWAP":
                data0 = self.stack.popleft()
                data1 = self.stack.popleft()
                self.stack.appendleft(data0)
                self.stack.appendleft(data1)
            elif token.op == "DISCARD":
                data = self.stack.popleft()
            elif token.op == "SLIDE":
                arg = token.arg
                arg_saved = arg
                data = self.stack.popleft()
                while arg:
                    arg = arg - 1
                    slide_data = self.stack.popleft()
                    self.debug(f"  Slided value={slide_data} off the stack")
                self.stack.appendleft(data)
            elif token.op == "ADD":
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 + data1)
            elif token.op == "SUBTRACT":
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 - data1)
            elif token.op == "MULTIPLY":
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 * data1)
            elif token.op == "DIVIDE":
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 // data1)
            elif token.op == "MODULO":
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 % data1)
            elif token.op == "STORE":
                val, addr = self.stack.popleft(),  self.stack.popleft()
                self.heap[addr] = val
                self.debug(f"  Stored {val} at heap address {addr}")
            elif token.op == "RETRIEVE":
                addr = self.stack.popleft()
                self.stack.appendleft(self.heap[addr])
            elif token.op == "MARK":
                # we've already handled this during scan_label()
                pass
            elif token.op == "CALL":
                self.return_addrs.appendleft(i+1)
                old_i = i
                i = self.labels[token.arg]
                self.debug(f"  Calling label {token.arg} instruction #{i} from #{old_i}")
                continue
            elif token.op == "JUMP":
                i = self.labels[token.arg]
                self.debug(f"  Jumping to label={token.arg}")
                continue
            elif token.op == "JUMPZERO":
                if self.stack.popleft() == 0:
                    i = self.labels[token.arg]
                    self.debug(f"  Jumping on ZERO to label={token.arg}")
                    continue
            elif token.op == "JUMPNEG":
                if self.stack.popleft() < 0:
                    i = self.labels[token.arg]
                    self.debug(f"  Jumping on NEGATIVE to label={token.arg}")
                    continue
            elif token.op == "RETURN":
                i = self.return_addrs.popleft()
                self.debug(f"  Returning to instruction #{i}")
                continue
            elif token.op == "ENDPROGRAM":
                exit("\nPROGRAM COMPLETED SUCCESSFULLY.")
            elif token.op == "OUTCH":
                self.debug("  >>>>>OUTPUT [", end='')
                print(chr(self.stack.popleft()), end='')
                self.debug("]")
            elif token.op == "OUTNUM":
                self.debug("  >>>>>OUTPUT [", end='')
                print(self.stack.popleft(), end='')
                self.debug("]")
            elif token.op == "INCH":
                addr = self.stack.popleft()
                data = ord(self.user_input())
                self.heap[addr] = data
                self.debug(f"  Read character {data} into heap at addr {addr}")
            elif token.op == "INNUM":
                addr = self.stack.popleft()
                data = int(self.user_input())
                self.heap[addr] = data
                self.debug(f"  Read character {data} into heap at addr {addr}")
            else:
                # this is only possible if I miscoded something
                exit(f"SYNTAX ERROR: BAD TOKEN: {token.op} {token.arg}")

            self.debug("  stack is now: ", showstack=True)
            # move index to the next token and loop again
            i += 1

    test_code = (
        "-----BEGIN-SUBROUTINE-TO-OUTPUT-A-SPACE"
        "\n \n \t \n----jump-to-label-#2"
        "\n   \t\n----mark-this-spot-as-#1<<<<<<<<<<<<<<<<<<<<"
        "    \n----push-addr-zero-into-stack"
        "\t\t\t----retrieve-value-at-where-stack-top-points"
        " \n ----duplicate-stack's-top-item"
        "\t\n  ----print-result-CHAR-which-should-be-a-space"
        " \n\n----discard-the-space"
        "\n\t\n----return-to-caller"
        "\n   \t \n----mark-this-spot-as-#2<<<<<<<<<<<<<<<<<<<<"
        "-----END-SUBROUTINE-TO-OUTPUT-A-SPACE"
        "    \n----heap-address-zero-pushed-onto-stack"
        "   \t     \n----asci-32-pushed-onto-stack"
        "\t\t ----store-a-space-(ascii-32)-on-the-heap-addr-zero"
        "   \t   \n----push-8-onto-stack"
        "  \t\t \n----push-negative-2-onto-stack"
        "\t   ----add"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_6"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "  \t\t \t\n----push-negative-5-onto-stack"
        "\t  \t----subtract"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_11"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "   \t\t\n----push-3-onto-stack"
        "\t  \n----multiply"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_33"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "   \t \n----push-2-onto-stack"
        "\t \t ----divide"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_16"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "   \t\t\t\n----push-7-onto-stack"
        "\t \t\t----modulo"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_2"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        " \n ----duplicate-stack's-top-item"
        "\t \t ----divide"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_1"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "----there-is-currently-1-item-on-stack,namely-1"
        "   \t\t\t\n----push-7-onto-stack"
        "   \t    \n----push-16-onto-stack"
        "   \t \t  \n----push-20-onto-stack"
        "   \t\t  \t\n----push-25-onto-stack"
        "   \t\t\t\t\t\n----push-31-onto-stack"
        " \t  \t\t\n----copy-3rd-stack-item-to-top-of-stack"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_16"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        " \n\t----swap-top-two-stack-items"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_31"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        " \n\n----discard-the-top-stack-item"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_16"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "----stack-should-be-16,25,20,16,7"
        " \t\n \t\t\n----slide-3-items-off-stack,-keeping-top-item"
        "----stack-should-be-16,7"
        "\t  \n----multiply"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_112"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "   \t \n----push-2-onto-stack"
        " \n ----duplicate-stack's-top-item"
        "\n\t  \t\t\t \n----jump-if-zero-to-#14-FAIL"
        " \n ----duplicate-stack's-top-item"
        "\n\t\t \t\t\t \n----jump-if-negative-to-#14-FAIL"
        "\n   \t     \t\n----mark-this-spot-as-#65<<<<<<<<<<<<<<<<<<<<"
        "   \t\t   \t\t\n----push-99-onto-stack"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_99"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        " \n\n----discard-the-99"
        "  \t\t \n----push-negative-2-onto-stack"
        "\t   ----add"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_0_1st-time,neg2-second-time"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "\n   \t\t\t \n----mark-this-spot-as-#14<<<<<<<<<<<<<<<<<<<<"
        " \n ----duplicate-stack's-top-item"
        "\n\t  \t     \t\n----jump-if-zero-to-#65-SUCCESS-1st-time-only"
        " \n ----duplicate-stack's-top-item"
        "\n\t\t \t  \t\t\n----jump-if-negative-to-#19-SUCCESS"
        "   \t\t\t\t\t\t\t\n----push-127-onto-stack"
        " \n ----duplicate-stack's-top-item"
        "\t\n \t----print-result......expect_NOTHING(skipped)"
        "\n \t \t\n----call-subroutine-to-print-a-space"
        "\n   \t  \t\t\n----mark-this-spot-as-#19<<<<<<<<<<<<<<<<<<<<"
        "   \t\t  \t  \n----push-100-onto-stack"
        "\t\n\t ----read-an-acii-char-from-stdin onto the heap"
        "   \t\t  \t  \n----push-100-onto-stack"
        "\t\t\t----retrieve-value-at-where-stack-top-points"
        "\t\n  ----print-result-char-expect-a-charcter-the-user-entered"
        "   \t\t  \t  \n----push-100-onto-stack"
        "\t\n\t\t----read-an-int-digit-from-stdin onto the heap"
        "   \t\t  \t  \n----push-100-onto-stack"
        "\t\t\t----retrieve-value-at-where-stack-top-points"
        "\t\n \t----print-result-int-expect-a-digit-the-user-entered"
        "\n\n\n----end"
        )

    expected_results = "6 11 33 16 2 1 16 31 16 112 99 0 99 -2"

# -------------------------------MAIN PROGRAM
def main():
    # Handle command arguments
    purpose_string = "whitespace.py - execute a program in the Whitespace programming language\n"
    usage_string = (
        "usage: whitespace.py [--debug | --describe] filename\n"
        "usage: whitespace.py [--debug | --describe] -\n"
        "usage: whitespace.py [--debug | --describe] --test\n"
        "usage: whitespace.py --help\n"
        "\n"
        "Options:\n"
        "  filename                An input file containing Whitespace code.\n"
        "  -                       Get the Whitespace source from STDIN (overrides filename)\n"
        "  --test                  Runs unit tests (overrides filename and -)\n"
        "  --debug                 Turns on verbose debugging\n"
        "  --describe              Describes the given Whitespace code.  Does not "
        "execute the program.\n"
        "  --help                  Prints this help info\n"
        )
    testarg = False
    debugarg = False
    describearg = False
    stdinarg = False
    filename = ""
    for arg in sys.argv[1:]:
        if arg == "--debug":
            debugarg = True
        elif arg == "--describe":
            describearg = True
        elif arg == "--test":
            testarg = True
        elif arg == "--help":
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
    if not testarg and not stdinarg and filename == "":
            print(f"{sys.argv[0]}: error: bad usage, must specify --test or - or a filename\n")
            print(usage_string)
            exit()


    # Get the source code
    source_code = ""
    if testarg:
        source_code = WhitespaceVM.test_code
        if not describearg:
            print("Running unit tests.  Expected results are:")
            print(WhitespaceVM.expected_results)
            print("Actual results are:")
    elif stdinarg:
        source_code = sys.stdin.read()
        # Was running into an EOF error when doing sys.stdin.read() followed by
        # an input().  The solution below came from stackexchange, but I don't know
        # if it works on windows.
        sys.stdin.close()
        sys.stdin = open(os.ctermid())
    else:
        try:
            with open(filename) as f:
                source_code = f.read()
        except IOError:
            exit(f"{sys.argv[0]}: error: Could not open file {filename}")

    # Execute the Whitespace source code
    vm = WhitespaceVM(source_code)
    vm.debug_flag = debugarg
    vm.describe_flag = describearg
    vm.run()

if __name__ == "__main__":
    main()
