#!/usr/bin/python3

from collections import deque
import sys
# ------------------------------ CONSTANTS
SPACE = ' '
TAB = '\t'
LF = '\n'
HEAPSIZE = 512
OP_PUSH     = "".join([SPACE, SPACE])               # tested
OP_DUP      = "".join([SPACE, LF, SPACE])           # tested
OP_COPY     = "".join([SPACE, TAB, SPACE])          # tested
OP_SWAP     = "".join([SPACE, LF, TAB])             # tested
OP_DISCARD  = "".join([SPACE, LF, LF])              # tested
OP_SLIDE    = "".join([SPACE, TAB, LF])             # tested
OP_ADD      = "".join([TAB, SPACE, SPACE, SPACE])   # tested
OP_SUB      = "".join([TAB, SPACE, SPACE, TAB])     # tested
OP_MULT     = "".join([TAB, SPACE, SPACE, LF])      # tested
OP_DIV      = "".join([TAB, SPACE, TAB, SPACE])     # tested
OP_MOD      = "".join([TAB, SPACE, TAB, TAB])       # tested
OP_STORE    = "".join([TAB, TAB, SPACE])            # tested
OP_RETRIEVE = "".join([TAB, TAB, TAB])              # tested
OP_MARK     = "".join([LF, SPACE, SPACE])           # tested
OP_CALL     = "".join([LF, SPACE, TAB])             # tested
OP_JUMP     = "".join([LF, SPACE, LF])              # tested
OP_JUMPZERO = "".join([LF, TAB, SPACE])             # tested
OP_JUMPNEG  = "".join([LF, TAB, TAB])               # tested
OP_RETURN   = "".join([LF, TAB, LF])                # tested
OP_ENDPROG  = "".join([LF, LF, LF])                 # tested
OP_OUTCH    = "".join([TAB, LF, SPACE, SPACE])      # tested
OP_OUTNUM   = "".join([TAB, LF, SPACE, TAB])        # tested
OP_INCH     = "".join([TAB, LF, TAB, SPACE])        # tested
OP_INNUM    = "".join([TAB, LF, TAB, TAB])          # tested

# -------------------------------CLASSES
class WhitespaceVM:
    def __init__(self, code=''):
        self.ip = 0                 # instruction pointer
        self.code = code            # string containing Whitespace code
        self.stack = deque()        # the internal data stack
        self.heap = [0] * HEAPSIZE  # memory heap
        self.labels = {}            # dictionary of label,addr pairs for flow
        self.return_addrs = deque() # where to go back to when subroutine ends
        self.input_stream = ""      # a buffer to hold input
        self.next_input = 0         # the next thing to read from the stream
        self.debug_flag = False     # flag to control depub statements

    def debug(self, str, end='\n'):
        if (self.debug_flag): print(str, end=end)

    def strip_comments(self):
        # since comments can be ANYWHERE, including in the middle of the
        # string of characters that represents a command, I decided the
        # easiest thing to do was to kill all the comments before parsing
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

    def unwhite(self, arr, max=-1):
        # Utility function for helping debug (funny thing, whitespace
        # is impossible to read).  Converts whitespace to letters, and
        # converts everything else to asterisks.
        # Note: pass in a max of -1 to convert an entire string.
        n = 0
        ret = ""
        for c in arr:
            if c == SPACE: ret += "S"
            elif c == TAB: ret += "T"
            elif c == LF: ret += "L"
            else: ret += "*"
            n = n + 1
            if max != -1 and n >= max: break
        return ret

    def parse_label(self):
        label = ""
        while self.ip < len(self.code) and self.code[self.ip] != LF:
            label += self.code[self.ip]
            self.ip += 1
        # not sure if python can index a dictionary with whitespace characters
        # so I'll "unwhite" the labels first
        label = self.unwhite(label)
        self.debug(f"Parsed label {label}")
        self.ip += 1
        return label

    def parse_num(self):
        num = 0
        mult = 0
        if self.code[self.ip] == SPACE:
            mult = 1
            # self.debug("Start of positive number ")
        elif self.code[self.ip] == TAB:
            mult = -1
            # self.debug("Start of negative number ")
        else:
            exit("SYNTAX ERROR : BAD SIGN")
        self.ip = self.ip + 1
        while self.ip < len(self.code) and self.code[self.ip] != LF:
            # about to add a new digit, so left shift the digits we have so far
            num = num << 1
            if self.code[self.ip] == TAB:
                # self.debug("1 ", end='')
                num = num | 1
            elif self.code[self.ip] == SPACE:
                # self.debug("0 ", end='')
                # don't need to do anything with a zero, as the left shift
                # already put a zero in there
                None
            else:
                exit("SYNTAX ERROR : BAD NUMBER")
            self.ip = self.ip + 1
        self.ip = self.ip + 1 # ip now points to the character after the LF
        # self.debug("")
        return num * mult

    def is_op(self, candidate):
        # self.debug(f"checking {self.unwhite(self.code[self.ip:],10)}"
        #     f" for {self.unwhite(candidate)} at ip={self.ip}")
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

    def scan_labels(self):
        # We have to scan the entire program first for labels, otherwise
        # we might encounter a jump-to-label command for a label that
        # hasn't been encountered yet.
        # This is ugly.  I hate duplicating this while loop.
        self.debug("===Begin label scan==========================")
        while self.ip < len(self.code):
            if self.is_op(OP_MARK):
                self.debug("----- OP_MARK -----")
                arg = self.parse_label()
                # remember: ip now points after the LF of the label just read
                self.labels[arg] = self.ip
                self.debug(f"Marked ip={self.ip} with label={arg}")
            elif self.is_op(OP_PUSH): self.parse_num()
            elif self.is_op(OP_DUP): pass
            elif self.is_op(OP_COPY): self.parse_num()
            elif self.is_op(OP_SWAP): pass
            elif self.is_op(OP_DISCARD): pass
            elif self.is_op(OP_SLIDE): self.parse_num()
            elif self.is_op(OP_ADD): pass
            elif self.is_op(OP_SUB): pass
            elif self.is_op(OP_MULT): pass
            elif self.is_op(OP_DIV): pass
            elif self.is_op(OP_MOD): pass
            elif self.is_op(OP_STORE): pass
            elif self.is_op(OP_RETRIEVE): pass
            elif self.is_op(OP_CALL): self.parse_label()
            elif self.is_op(OP_JUMP): self.parse_label()
            elif self.is_op(OP_JUMPZERO): self.parse_label()
            elif self.is_op(OP_JUMPNEG): self.parse_label()
            elif self.is_op(OP_RETURN): pass
            elif self.is_op(OP_ENDPROG): pass
            elif self.is_op(OP_OUTCH): pass
            elif self.is_op(OP_OUTNUM): pass
            elif self.is_op(OP_INCH): pass
            elif self.is_op(OP_INNUM): pass
            else:
                exit(f"SYNTAX ERROR : BAD INSTRUCTION "
                    f"{self.unwhite(self.code[self.ip:],25)} WHILE SCANNING LABELS")
        self.debug("===End label scan==========================")

    def run(self):
        self.strip_comments()
        self.scan_labels()
        self.ip = 0 # reset the instruction pointer to the beginning

        while self.ip < len(self.code):
            # process instructions
            if self.is_op(OP_PUSH):
                self.debug("----- OP_PUSH -----")
                arg = self.parse_num()
                self.stack.appendleft(arg)
                self.debug(f"Pushed {arg} onto stack")
            elif self.is_op(OP_DUP):
                self.debug("----- OP_DUP -----")
                self.stack.appendleft(self.stack[0]) # blows up if stack empty
                self.debug(f"Duplicated {self.stack[0]} onto stack")
            elif self.is_op(OP_COPY):
                self.debug("----- OP_COPY -----")
                arg = self.parse_num()
                val = self.stack[arg]
                self.stack.appendleft(val)
                self.debug(f"Copied {arg}th stack element value={val} onto stack")
            elif self.is_op(OP_SWAP):
                self.debug("----- OP_SWAP -----")
                data0 = self.stack.popleft()
                data1 = self.stack.popleft()
                self.stack.appendleft(data0)
                self.stack.appendleft(data1)
            elif self.is_op(OP_DISCARD):
                self.debug("----- OP_DISCARD -----")
                data = self.stack.popleft()
                self.debug(f"Discarded {data} from the stack")
            elif self.is_op(OP_SLIDE):
                self.debug("----- OP_SLIDE -----")
                arg = self.parse_num()
                arg_saved = arg
                data = self.stack.popleft()
                while arg:
                    arg = arg - 1
                    slide_data = self.stack.popleft()
                    self.debug(f"Slided value={slide_data} off the stack")
                self.stack.appendleft(data)
                self.debug(f"Slided {arg_saved} stack element(s) from stack, kept the top={data}")
            elif self.is_op(OP_ADD):
                self.debug("----- OP_ADD -----")
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 + data1)
            elif self.is_op(OP_SUB):
                self.debug("----- OP_SUB -----")
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 - data1)
            elif self.is_op(OP_MULT):
                self.debug("----- OP_MULT -----")
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 * data1)
            elif self.is_op(OP_DIV):
                self.debug("----- OP_DIV -----")
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 // data1)
            elif self.is_op(OP_MOD):
                self.debug("----- OP_MOD -----")
                data1, data0 = self.stack.popleft(),  self.stack.popleft()
                self.stack.appendleft(data0 % data1)
            elif self.is_op(OP_STORE):
                self.debug("----- OP_STORE -----")
                val, addr = self.stack.popleft(),  self.stack.popleft()
                self.heap[addr] = val
                self.debug(f"Stored {val} at heap address {addr}")
            elif self.is_op(OP_RETRIEVE):
                self.debug("----- OP_RETRIEVE -----")
                addr = self.stack.popleft()
                self.stack.appendleft(self.heap[addr])
            elif self.is_op(OP_MARK):
                self.debug("----- OP_MARK -----")
                self.parse_label()
                self.debug("Doing nothing")
                # we've already done this during scan_label()
            elif self.is_op(OP_CALL):
                self.debug("----- OP_CALL -----")
                arg = self.parse_label()
                # remember: ip now points after the LF of the label just read
                self.return_addrs.appendleft(self.ip)
                self.ip = self.labels[arg]
            elif self.is_op(OP_JUMP):
                self.debug("----- OP_JUMP -----")
                arg = self.parse_label()
                self.ip = self.labels[arg]
                self.debug(f"Jumped to label={arg}, which is at ip={self.ip}")
            elif self.is_op(OP_JUMPZERO):
                self.debug("----- OP_JUMPZERO -----")
                arg = self.parse_label()
                if self.stack.popleft() == 0:
                    self.ip = self.labels[arg]
                    self.debug(f"Jumped on ZERO to label={arg}, which is at ip={self.ip}")
            elif self.is_op(OP_JUMPNEG):
                self.debug("----- OP_JUMPNEG -----")
                arg = self.parse_label()
                if self.stack.popleft() < 0:
                    self.ip = self.labels[arg]
                    self.debug(f"Jumped on NEGATIVE to label={arg}, which is at ip={self.ip}")
            elif self.is_op(OP_RETURN):
                self.debug("----- OP_RETURN -----")
                self.ip = self.return_addrs.popleft()
            elif self.is_op(OP_ENDPROG):
                exit("\nPROGRAM COMPLETED SUCCESSFULLY.")
            elif self.is_op(OP_OUTCH):
                self.debug("----- OP_OUTCH -----")
                self.debug("\t\t>>>>>OUTPUT [", end='')
                print(chr(self.stack.popleft()), end='')
                self.debug("]")
            elif self.is_op(OP_OUTNUM):
                self.debug("----- OP_OUTNUM -----")
                self.debug("\t\t>>>>>OUTPUT [", end='')
                print(self.stack.popleft(), end='')
                self.debug("]")
            elif self.is_op(OP_INCH):
                self.debug("----- OP_INCH -----")
                addr = self.stack.popleft()
                data = ord(self.user_input())
                self.heap[addr] = data
                self.debug(f"Read character {data} into heap at addr {addr}")
            elif self.is_op(OP_INNUM):
                self.debug("----- OP_INNUM -----")
                addr = self.stack.popleft()
                data = int(self.user_input())
                self.heap[addr] = data
                self.debug(f"Read character {data} into heap at addr {addr}")

            else:
                exit(f"SYNTAX ERROR : BAD INSTRUCTION "
                    f"{self.unwhite(self.code[self.ip:],25)}")

            # there is no need to increment the ip here.
            # remember: the ip was advanced in the calls to is_op()
            # and parse_num(), so it is already pointing to the next instruction

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
    purpose_string = "whitepsace.py - execute a program in the Whitespace programming language\n"
    usage_string = (
        "usage: whitespace.py [--debug] filename\n"
        "usage: whitespace.py [--debug] --test\n"
        "usage: whitespace.py --help\n"
        "\n"
        "Options:\n"
        "  filename                An input file containing Whitespace code\n"
        "  --test                  Runs unit tests (overrides filename)\n"
        "  --debug                 Turns on verbose debugging\n"
        "  --help                  Prints this help info\n"
        )
    testarg = False
    debugarg = False
    filename = ""
    for arg in sys.argv[1:]:
        if arg == "--debug":
            debugarg = True
        elif arg == "--test":
            testarg = True
        elif arg == "--help":
            print(purpose_string)
            print(usage_string)
            exit()
        elif arg[0] == "-":
            print(f"{sys.argv[0]}: error: unknown option {arg}\n")
            print(usage_string)
            exit()
        else:
            filename = arg
    if not testarg and filename == "":
            print(f"{sys.argv[0]}: error: bad usage, must specify --test or a filename\n")
            print(usage_string)
            exit()

    # Get the source code
    source_code = ""
    if testarg:
        source_code = WhitespaceVM.test_code
        print("Running unit tests.  Expected results are:")
        print(WhitespaceVM.expected_results)
        print("Actual results are:")
    else:
        try:
            with open(filename) as f:
                source_code = f.read()
        except IOError:
            exit(f"{sys.argv[0]}: error: Could not open file {filename}")

    # Execute the Whitespace source code
    vm = WhitespaceVM(source_code)
    vm.debug_flag = debugarg
    vm.run()

if __name__ == "__main__":
    main()
