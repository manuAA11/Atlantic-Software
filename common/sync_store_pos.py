"""Distribute additive POS sources without changing historical migrations."""
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = "20261015020000_store_pos.sql"
MODULES = ("store_pos.py", "store_pos_ui.py", "store_pos_import.py")
TESTS = ("test_store_pos.py", "test_store_pos_import.py", "store_pos.mjs", "store_pos_import.mjs",
         "store_pos_owner.mjs", "store_pos_ui_smoke.py")


def synchronize():
    common = ROOT / "common"
    sources = [common / "store_pos.sql", common / "store_pos_import.sql", common / "store_pos_owner.sql"]
    if all(source.is_file() for source in sources):
        # The distributable server update is one atomic transaction. Function
        # block BEGIN has no semicolon; these are only outer SQL transactions.
        bodies = [re.sub(r"(?im)^\s*(?:begin|commit);[ \t]*$", "", source.read_text()) for source in sources]
        content = ("-- Shared Atlantic Gym POS upgrade; preserve all existing gym data.\n"
                   "begin;\nset local lock_timeout='8s';\nset local statement_timeout='90s';\n" +
                   "\n".join(bodies) + "\nnotify pgrst, 'reload schema';\ncommit;\n")
        (ROOT / "ACTUALIZAR_TIENDA_POS.sql").write_text(content)
        (ROOT / "supabase" / "migrations" / MIGRATION).write_text(content)
    for edition in ROOT.glob("GymSoft_*"):
        for name in MODULES:
            if (common / name).is_file():
                shutil.copyfile(common / name, edition / name)
        for name in TESTS:
            if (common / name).is_file():
                shutil.copyfile(common / name, edition / "tests" / name)
        source = ROOT / "ACTUALIZAR_TIENDA_POS.sql"
        if source.is_file():
            shutil.copyfile(source, edition / source.name)
            shutil.copyfile(source, edition / "supabase" / "migrations" / MIGRATION)


if __name__ == "__main__":
    synchronize()
