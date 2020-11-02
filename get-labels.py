#!/usr/bin/env python3

from gmail import Gmail


def main():
    g = Gmail()

    # Print all lable names:
    for l in g.labels():
        print(l)

    # Print all labels as objects
    for l in g.labels().values():
        print(l)

    # Obtain all the label IDs as a list
    print("")
    print("IDs:")
    ids = [l.id for l in g.labels().values()]
    print(ids)

    # Obtain a specific label:
    print("")
    libcamera = g.label('IOB/libcamera')
    print("Libcamera: str( " + str(libcamera) + " )")
    print(" Name:" + libcamera.name + " - ID:" + libcamera.id)

if __name__ == '__main__':
    main()
