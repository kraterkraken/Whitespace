#!/usr/bin/python3

from collections import deque
import sys
# ------------------------------ CONSTANTS
SPACE = ' '
TAB = '\t'
LF = '\n'
HEAPSIZE = 512
OP_PUSH     = SPACE + SPACE
OP_DUP      = SPACE + LF    + SPACE
OP_COPY     = SPACE + TAB   + SPACE
OP_SWAP     = SPACE + LF    + TAB
OP_DISCARD  = SPACE + LF    + LF
OP_SLIDE    = SPACE + TAB   + LF
OP_ADD      = TAB   + SPACE + SPACE + SPACE
OP_SUB      = TAB   + SPACE + SPACE + TAB
OP_MULT     = TAB   + SPACE + SPACE + LF
OP_DIV      = TAB   + SPACE + TAB   + SPACE
OP_MOD      = TAB   + SPACE + TAB   + TAB
OP_STORE    = TAB   + TAB   + SPACE
OP_RETRIEVE = TAB   + TAB   + TAB
OP_MARK     = LF    + SPACE + SPACE
OP_CALL     = LF    + SPACE + TAB
OP_JUMP     = LF    + SPACE + LF
OP_JUMPZERO = LF    + TAB   + SPACE
OP_JUMPNEG  = LF    + TAB   + TAB
OP_RETURN   = LF    + TAB   + LF
OP_ENDPROG  = LF    + LF    + LF
OP_OUTCH    = TAB   + LF    + SPACE + SPACE
OP_OUTNUM   = TAB   + LF    + SPACE + TAB
OP_INCH     = TAB   + LF    + TAB   + SPACE
OP_INNUM    = TAB   + LF    + TAB   + TAB

# -------------------------------CLASSES
class WhitespaceVM:

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
        self.debug_flag = False     # flag to control depub statements
        self.describe_flag = False  # flag to control whether we describe the source

    def debug_token(self, token):
        self.debug(f"{token.op} {token.arg}", showstack=True)

    def debug(self, str, end='\n', showstack=False):
        if (self.debug_flag):
            print(str, end="")
            if showstack:
                s = "["
                sep = ","
                for a in self.stack:
                    s = f"{s}{sep}{a}"
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
        #self.debug(f"  Parsed label {label}")
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
                pass
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
            if self.is_op(OP_MARK):
                self.tokens.append(self.Token(op="MARK", arg=self.parse_label()))
            elif self.is_op(OP_PUSH):
                self.tokens.append(self.Token(op="PUSH", arg=self.parse_num()))
            elif self.is_op(OP_DUP):
                self.tokens.append(self.Token(op="DUPLICATE"))
            elif self.is_op(OP_COPY):
                self.tokens.append(self.Token(op="COPY", arg=self.parse_num()))
            elif self.is_op(OP_SWAP):
                self.tokens.append(self.Token(op="SWAP"))
            elif self.is_op(OP_DISCARD):
                self.tokens.append(self.Token(op="DISCARD"))
            elif self.is_op(OP_SLIDE):
                self.tokens.append(self.Token(op="SLIDE", arg=self.parse_num()))
            elif self.is_op(OP_ADD):
                self.tokens.append(self.Token(op="ADD"))
            elif self.is_op(OP_SUB):
                self.tokens.append(self.Token(op="SUBTRACT"))
            elif self.is_op(OP_MULT):
                self.tokens.append(self.Token(op="MULTIPLY"))
            elif self.is_op(OP_DIV):
                self.tokens.append(self.Token(op="DIVIDE"))
            elif self.is_op(OP_MOD):
                self.tokens.append(self.Token(op="MODULO"))
            elif self.is_op(OP_STORE):
                self.tokens.append(self.Token(op="STORE"))
            elif self.is_op(OP_RETRIEVE):
                self.tokens.append(self.Token(op="RETRIEVE"))
            elif self.is_op(OP_CALL):
                self.tokens.append(self.Token(op="CALL", arg=self.parse_label()))
            elif self.is_op(OP_JUMP):
                self.tokens.append(self.Token(op="JUMP", arg=self.parse_label()))
            elif self.is_op(OP_JUMPZERO):
                self.tokens.append(self.Token(op="JUMPZERO", arg=self.parse_label()))
            elif self.is_op(OP_JUMPNEG):
                self.tokens.append(self.Token(op="JUMPNEG", arg=self.parse_label()))
            elif self.is_op(OP_RETURN):
                self.tokens.append(self.Token(op="RETURN"))
            elif self.is_op(OP_ENDPROG):
                self.tokens.append(self.Token(op="ENDPROGRAM"))
            elif self.is_op(OP_OUTCH):
                self.tokens.append(self.Token(op="OUTCH"))
            elif self.is_op(OP_OUTNUM):
                self.tokens.append(self.Token(op="OUTNUM"))
            elif self.is_op(OP_INCH):
                self.tokens.append(self.Token(op="INCH"))
            elif self.is_op(OP_INNUM):
                self.tokens.append(self.Token(op="INNUM"))
            else:
                exit(f"SYNTAX ERROR : BAD WHITESPACE INSTRUCTION "
                    f"{self.unwhite(self.code[self.ip:],25)}"
                    f" at location {self.ip}"
                    )

    def run(self):
        self.strip_comments()
        self.tokenize()
        self.scan_labels()
        if (self.describe_flag):
            self.describe()
        else:
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
    purpose_string = "whitepsace.py - execute a program in the Whitespace programming language\n"
    usage_string = (
        "usage: whitespace.py [--debug | --describe] filename\n"
        "usage: whitespace.py [--debug | --describe] --test\n"
        "usage: whitespace.py --help\n"
        "\n"
        "Options:\n"
        "  filename                An input file containing Whitespace code\n"
        "  --test                  Runs unit tests (overrides filename)\n"
        "  --debug                 Turns on verbose debugging\n"
        "  --describe              Describes the given Whitespace code.  Does not "
        "execute the program.\n"
        "  --help                  Prints this help info\n"
        )
    testarg = False
    debugarg = False
    describearg = False
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
        if not describearg:
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
    vm.describe_flag = describearg
    vm.run()

if __name__ == "__main__":
    main()
