#!/usr/bin/env python3

# Copyright 2020 Linux Embedded

from gmail import Gmail
import subprocess
import re


def yes_no(answer, default=False):
    yes = set(['yes', 'y', 'ye'])
    no = set(['no', 'n'])

    while True:
        choice = input(answer + " yes/no:").lower()
        if choice in yes:
            return True
        elif choice in no:
            return False
        elif choice == '':
            return default
        else:
            print("Please respond with 'yes' or 'no'")


class Repository:
    def __init__(self, repo):
        self.gitdir = repo

    def run_command(self, args, stdin=None):
        args = ['git', '--no-pager', '--git-dir', self.gitdir] + args

        if stdin is None:
            (output, error) = subprocess.Popen(args, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE).communicate()
        else:
            pp = subprocess.Popen(args, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            (output, error) = pp.communicate(input=stdin.encode('utf-8'))

        output = output.strip().decode('utf-8', errors='replace')
        if len(error.strip()):
            print('Stderr: %s', error.decode('utf-8', errors='replace'))

        return output

    def has_commit(self, title):
        args = ['log', '--oneline', '--grep', title]
        out = self.run_command(args)
        if not out:
            return False

        return True


def main():
    g = Gmail()
    repo = Repository("/home/linuxembedded/iob/libcamera/libcamera-daily/.git")

    list_prefixes = re.compile(r'^(\[.*?\] *)+')

    libcamera = g.label('IOB/libcamera')
    done = g.label('IOB/libcamera/Done')

    completed = set()

    for thread in g.threads(libcamera):
        subject = re.sub(list_prefixes, '', thread.subject)

        default = False

        print(thread.subject)

        if repo.has_commit(subject):
            print('**********************************************')
            print('    thread: {}: \"{}\" is in the log'.format(thread.id, subject))
            print('**********************************************')
            default = True
            for message in thread.messages:
                print(message)
            print()


        if default:
            if yes_no('Mark as done?', default):
                print(" Done with that one ")
                thread.modify([libcamera], [done])
                completed.add(thread)

    print("The following threads were moved:")
    for thread in completed:
        print(thread)


if __name__ == '__main__':
    main()
