#
# @author Sinu John
#         sinuvian at gmail dot com
#         www.sinujohn.wordpress.com
#

#
# Usage:
#       python clock.py [degree [time]]
#
#           'degree' is the degree of fuzziness - can have values of 1 or 2
#           'time' - give time in the format hour:minute (24-hour format)
#                               example: 9:45, 11:30, 14:25
#            Default value of 'degree' is 1, and 'time' is System time.
#

import sys
import time


def fuzzy(hour, minute, degree=1):
    """Implements the fuzzy clock.
    returns the the string that spells out the time - hour:minute
    Supports two degrees of fuzziness. Set with degree = 1 or degree = 2
    When degree = 1, time is in quantum of 5 minutes.
    When degree = 2, time is in quantum of 15 minutes."""

    if degree <= 0 or degree > 2:
        print("Please use a degree of 1 or 2. Using fuzziness degree=1")
        degree = 1

    begin = "It's "

    f0 = "almost "
    f1 = "exactly "
    f2 = "around "

    b0 = " past "
    b1 = " to "

    hourlist = (
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
    )

    s1 = s2 = s3 = s4 = ""
    base = 5

    if degree == 1:
        base = 5
        val = ("Five", "Ten", "Quarter", "Twenty", "Twenty-Five", "Half")
    elif degree == 2:
        base = 15
        val = ("Quarter", "Half")

    # to find whether we have to use 'almost', 'exactly' or 'around'
    dmin = minute % base
    if minute > 30:
        pos = int((60 - minute) / base)  # position in the tuple 'val'
    else:
        pos = int(minute / base)

    if dmin == 0:
        s1 = f1
        pos = pos - 1
    elif dmin <= base / 2:
        s1 = f2
        if minute < 30:
            pos = pos - 1
    else:
        s1 = f0
        if minute > 30:
            pos = pos - 1

    s2 = val[pos]

    if minute <= base / 2:
        # Case like "It's around/exactly Ten"
        s2 = s3 = ""
        s4 = hourlist[hour - 12 - 1]
    elif minute >= 60 - base / 2:
        # Case like "It's almost Ten"
        s2 = s3 = ""
        s4 = hourlist[hour - 12]
    else:
        # Other cases with all words, like "It's around Quarter past One"
        if minute > 30:
            s3 = b1  # to
            s4 = hourlist[hour - 12]
        else:
            s3 = b0  # past
            s4 = hourlist[hour - 12 - 1]

    return begin + s1 + s2 + s3 + s4


def main():
    deg = 1
    stm = time.localtime()
    h = stm.tm_hour
    m = stm.tm_min

    if len(sys.argv) >= 2:
        try:
            deg = int(sys.argv[1])
        except Exception:
            print("Please use a degree of 1 or 2. Using fuzziness degree=1")

        if len(sys.argv) >= 3:
            tm = sys.argv[2].split(":")
            try:
                h = int(tm[0])
                m = int(tm[1])
                if h < 0 or h > 23 or m < 0 or m > 59:
                    raise Exception
            except Exception:
                print("Bad time entered. Using the system time.")
                h = stm.tm_hour
                m = stm.tm_min
                print(fuzzy(h, m, deg))
            return


if __name__ == "__main__":
    main()
