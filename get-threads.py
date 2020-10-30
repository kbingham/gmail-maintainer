#!/usr/bin/env python3

from gmail import Gmail

def main():
    g = Gmail()

    libcamera = g.label('IOB/libcamera')

    for thread in g.threads(libcamera):
        for message in thread.messages:
            print(message)

        # Pause between mail threads
        input('Next ... ')


if __name__ == '__main__':
    main()
