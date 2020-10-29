#!/usr/bin/env python3

from gmail import Gmail


def main():
    g = Gmail()

    for l in g.labels():
        print(l)


if __name__ == '__main__':
    main()
