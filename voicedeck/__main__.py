import argparse

from .config import load_config


def main():
    p = argparse.ArgumentParser(prog="voicedeck", description="Offline voice assistant for Raspberry Pi")
    p.add_argument("--text", action="store_true", help="type commands instead of speaking (for testing)")
    p.add_argument("--quiet", action="store_true", help="print replies instead of speaking them")
    p.add_argument("--config", help="path to config.yaml")
    p.add_argument("--list-devices", action="store_true", help="show audio devices and exit")
    args = p.parse_args()

    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        return

    from .assistant import Assistant
    Assistant(load_config(args.config), text_mode=args.text, quiet=args.quiet).run()


if __name__ == "__main__":
    main()
