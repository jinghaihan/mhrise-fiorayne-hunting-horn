#!/usr/bin/env python3

import argparse
import contextlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path


MOD_NAME = "Fiorayne Hunting Horn"
HORN_WEAPON_TYPE = 10
FIORAYNE_ID = 1
ANTIQUE_MACHINA_HORN_MODEL_ID = 143654979
ROYAL_ORDER_HORN_MODEL_ID = 143654978
VANILLA_HORN_FOLLOWER_IDS = {8, 9, 10}
ADDED_HORN_FOLLOWER_IDS = {2, 3, 4, 5, 6, 7}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Fiorayne-only Hunting Horn mod from The best music corps."
    )
    parser.add_argument("source", type=Path, help="The original v1.3 RAR archive")
    parser.add_argument(
        "--reasy",
        type=Path,
        required=True,
        help="Path to a REasy source checkout",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist"),
        help="Output directory (default: dist)",
    )
    return parser.parse_args()


def find_source_root(extracted: Path) -> Path:
    matches = list(extracted.rglob("The best music corps/modinfo.ini"))
    if len(matches) != 1:
        raise RuntimeError("Could not uniquely locate The best music corps in the archive")
    return matches[0].parent


def value_of(field):
    data = getattr(field, "__dict__", {})
    if "string" in data:
        return data["string"]
    return data.get("value", repr(field))


def build(source: Path, reasy: Path, output: Path) -> None:
    sys.path.insert(0, str(reasy))

    from file_handlers.rsz.rsz_file import RszFile
    from utils.type_registry import TypeRegistry

    registry_path = reasy / "resources/data/dumps/rszmhrise.json"
    if not registry_path.is_file():
        raise RuntimeError(f"Missing REasy registry: {registry_path}")

    with tempfile.TemporaryDirectory(prefix="fiorayne-horn-") as temp_dir:
        extracted = Path(temp_dir) / "source"
        extracted.mkdir()
        subprocess.run(
            ["bsdtar", "-xf", str(source), "-C", str(extracted)],
            check=True,
        )
        source_root = find_source_root(extracted)

        mod_root = output / MOD_NAME
        equip_output = (
            mod_root
            / "natives/STM/servant/prefab/DataHolder/EquipData/DefaultEquip"
        )
        servant_output = (
            mod_root / "natives/STM/servant/prefab/ServantManager/ServantData"
        )
        equip_output.mkdir(parents=True, exist_ok=True)
        servant_output.mkdir(parents=True, exist_ok=True)

        source_equip = (
            source_root
            / "natives/STM/servant/prefab/DataHolder/EquipData/DefaultEquip"
        )
        source_servant = (
            source_root / "natives/STM/servant/prefab/ServantManager/ServantData"
        )
        quiet = io.StringIO()
        with contextlib.redirect_stdout(quiet):
            registry = TypeRegistry(str(registry_path))

        set_fiorayne_horn_model(
            source_servant / "ServantData_1.user.2",
            servant_output / "ServantData_1.user.2",
            registry,
            RszFile,
        )

        generated = 0
        for source_file in sorted(source_equip.glob("MR*.user.2")):
            with contextlib.redirect_stdout(quiet):
                rsz = RszFile()
                rsz.filepath = str(source_file)
                rsz.type_registry = registry
                rsz.read(source_file.read_bytes())

            roots = [
                index
                for index, info in enumerate(rsz.instance_infos)
                if (registry.get_type_info(info.type_id) or {}).get("name")
                == "snow.ai.ServantQuestEquipData"
            ]
            if len(roots) != 1:
                raise RuntimeError(f"Unexpected root structure in {source_file.name}")

            root = rsz.parsed_elements[roots[0]]
            references = root["_CharacterEquipList"].values
            kept = []
            removed = []
            for reference in references:
                entry = rsz.parsed_elements[reference.value]
                follower_id = entry["_ServantId"].value
                weapon_type = entry["_WeaponType"].value
                if (
                    weapon_type == HORN_WEAPON_TYPE
                    and follower_id in ADDED_HORN_FOLLOWER_IDS
                ):
                    removed.append(reference.value)
                else:
                    kept.append(reference)

            if len(removed) != len(ADDED_HORN_FOLLOWER_IDS):
                raise RuntimeError(f"Unexpected Hunting Horn records in {source_file.name}")

            root["_CharacterEquipList"].values = kept
            with contextlib.redirect_stdout(quiet):
                built = rsz.build(special_align_enabled=False)

            destination = equip_output / source_file.name
            destination.write_bytes(built)
            validate_output(destination, registry, RszFile)
            generated += 1

        (mod_root / "modinfo.ini").write_text(
            "\n".join(
                [
                    f"name={MOD_NAME}",
                    "version=v0.1.1",
                    "description=Adds Hunting Horn support to Fiorayne with Utsushi-equivalent performance. Other followers and player weapons are unchanged.",
                    "author=jinghaihan, based on NyoiStick's work",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        if generated != 17:
            raise RuntimeError(f"Expected 17 equipment files, generated {generated}")


def set_fiorayne_horn_model(
    source: Path, destination: Path, registry, rsz_file_class
) -> None:
    quiet = io.StringIO()
    with contextlib.redirect_stdout(quiet):
        parsed = rsz_file_class()
        parsed.filepath = str(source)
        parsed.type_registry = registry
        parsed.read(source.read_bytes())

    weapon_models = [
        element
        for index, element in parsed.parsed_elements.items()
        if (registry.get_type_info(parsed.instance_infos[index].type_id) or {}).get("name")
        == "snow.ai.ServantWeaponModelList"
    ]
    if len(weapon_models) != 1:
        raise RuntimeError("Unexpected Fiorayne weapon model structure")

    horn_model = weapon_models[0]["_HornWeaponModelId"]
    if horn_model.value != ANTIQUE_MACHINA_HORN_MODEL_ID:
        raise RuntimeError("Unexpected original Fiorayne Hunting Horn model")
    horn_model.value = ROYAL_ORDER_HORN_MODEL_ID

    with contextlib.redirect_stdout(quiet):
        destination.write_bytes(parsed.build(special_align_enabled=False))


def validate_output(path: Path, registry, rsz_file_class) -> None:
    quiet = io.StringIO()
    data = path.read_bytes()
    with contextlib.redirect_stdout(quiet):
        parsed = rsz_file_class()
        parsed.filepath = str(path)
        parsed.type_registry = registry
        parsed.read(data)

    root_index = next(
        index
        for index, info in enumerate(parsed.instance_infos)
        if (registry.get_type_info(info.type_id) or {}).get("name")
        == "snow.ai.ServantQuestEquipData"
    )
    horn_entries = {}
    for reference in parsed.parsed_elements[root_index]["_CharacterEquipList"].values:
        entry = parsed.parsed_elements[reference.value]
        follower_id = entry["_ServantId"].value
        if entry["_WeaponType"].value == HORN_WEAPON_TYPE:
            horn_entries[follower_id] = entry

    expected_ids = {FIORAYNE_ID, *VANILLA_HORN_FOLLOWER_IDS}
    if set(horn_entries) != expected_ids:
        raise RuntimeError(f"Invalid Hunting Horn owners in {path.name}")

    fiorayne = {
        name: value_of(value)
        for name, value in horn_entries[FIORAYNE_ID].items()
        if name != "_ServantId"
    }
    utsushi = {
        name: value_of(value)
        for name, value in horn_entries[10].items()
        if name != "_ServantId"
    }
    if fiorayne != utsushi:
        raise RuntimeError(f"Fiorayne and Utsushi performance differ in {path.name}")

    with contextlib.redirect_stdout(quiet):
        rebuilt = parsed.build(special_align_enabled=False)
    if rebuilt != data:
        raise RuntimeError(f"Round-trip validation failed for {path.name}")


def main() -> None:
    args = parse_args()
    build(args.source.resolve(), args.reasy.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
