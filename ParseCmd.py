import argparse


def parse_cmd():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    init_cmd = subparsers.add_parser("init", help='initialize a new repo')
    init_cmd.add_argument(
        dest="path", nargs=1, help="Create an empty Git repository or reinitialize an existing one")

    hashobj_cmd = subparsers.add_parser(
        "hash-object", help="Compute object ID and optionally creates a blob from a file")
    hashobj_cmd.add_argument(
        "-t", "--type", choices=["blob"], default="blob", dest="type", help="Specify the type (default: \"blob\").")
    hashobj_cmd.add_argument(
        "--path", dest="path", help="Create an empty Git repository or reinitialize an existing one")

    add_cmd = subparsers.add_parser(
        "add", help="Add file contents to the index")
    add_cmd.add_argument(dest="paths", nargs="+",
                         help="path(s) of files to add")
    lsfile_cmd = subparsers.add_parser(
        "ls-files", help="List all the stage files")
    lsfile_cmd.add_argument("-s", "--stage", action="store_true", dest="stage",
                            help="Show staged contents' mode bits, object name and stage number in the output")

    status_cmd = subparsers.add_parser(
        "status", help="Show the working tree status")

    catfile_cmd = subparsers.add_parser(
        "cat-file", help="Show changes between commits, commit and working tree, etc")
    catfile_cmd.add_argument("-t", action="store_true",
                             dest="type", help="show object type")
    catfile_cmd.add_argument("-s", action="store_true",
                             dest="size", help="show object size")
    catfile_cmd.add_argument("-p", action="store_true",
                             dest="pretty", help="pretty-print object's content")
    catfile_cmd.add_argument(choices=["blob", "tree", "commit"], nargs="?", dest="mode",
                             help="The name (complete or prefix of the hash number) of the object to show")
    catfile_cmd.add_argument(dest="sha1_prefix",
                             help="Specify the object type (default: \"blob\").")

    diff_cmd = subparsers.add_parser(
        "diff", help="Show changes between commits, commit and working tree, etc")

    commit_cmd = subparsers.add_parser(
        "commit", help="Record changes to the repository")
    commit_cmd.add_argument("-m", default="", dest="msg",
                            help="Use the given <msg> as the commit message")

    log_cmd = subparsers.add_parser(
        "log")

    return parser.parse_args()
