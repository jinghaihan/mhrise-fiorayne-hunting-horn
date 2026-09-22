# MHRise Fiorayne Hunting Horn

Adds Hunting Horn support to Fiorayne with the same equipment performance and skill data as Utsushi. Existing player weapons and other follower behavior are left unchanged.

## Installation

Copy `mod/Fiorayne Hunting Horn` into the Monster Hunter Rise mods directory used by [Fluffy Mod Manager](https://www.nexusmods.com/monsterhunterrise/mods/7), then enable it in the manager.

Back up your game files and disable conflicting follower equipment mods before testing.

## Status

The generated `.user.2` files pass parser round-trip validation. In-game validation is still required.

## Credits

This scoped derivative is based on [The best music corps](https://www.nexusmods.com/monsterhunterrise/mods/3639) by **NyoiStick**. All credit for the original follower Hunting Horn implementation and modified game data goes to NyoiStick.

The build script uses [REasy](https://github.com/seifhassine/REasy) to edit and validate RE Engine data files.

## License

[MIT](./LICENSE) License © [jinghaihan](https://github.com/jinghaihan) applies to the original code and documentation in this repository. The modified game data under `mod/` is derived from NyoiStick's original work and is not relicensed under MIT; refer to the original mod page linked in [Credits](#credits).

## Building

The original mod archive is intentionally not included. To rebuild the scoped version, download v1.3 from Nexus Mods and provide a local REasy checkout:

```bash
python scripts/build.py \
  /path/to/the-best-music-corps-v1.3.rar \
  --reasy /path/to/REasy
```
