import sys

def my_spy(frame, event, arg):
    # Python calls this function before EVERY line runs
    # frame = information about the current line (what file, what line number, what variables exist)
    # event = what happened ("call", "line", "return", "exception")
    # arg = extra info (return value for "return" events, exception info for "exception" events)
    print(event, frame.f_lineno, frame.f_code.co_name)
    return my_spy  # IMPORTANT: return itself to keep spying

sys.settrace(my_spy)  # Start spying
# ... any code that runs after this will be spied on ...
def main():
    vara=10
    varb=20
    varc=vara+varb
    print(varc)
main()
# print(my_spy)
sys.settrace(None)    # Stop spying
