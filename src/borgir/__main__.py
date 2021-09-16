import argparse

from .bot import Borgir

# TODO: remove hardcoding.
DEFAULT_EXTENSIONS = [
    "borgir.cogs.play",
]


def main():
    parser = argparse.ArgumentParser(description="Borgir!")
    parser.add_argument("--token", required=True)
    parser.add_argument("--guild", required=True)
    parser.add_argument("--command-channel", required=True)
    parser.add_argument("--command-prefix", default="!")
    parser.add_argument("--extensions", default=DEFAULT_EXTENSIONS)
    args = parser.parse_args()

    bot = Borgir(args.guild, args.command_channel, args.command_prefix)
    for extension in args.extensions:
        bot.load_extension(extension)
    bot.run(args.token)


if __name__ == "__main__":
    main()
