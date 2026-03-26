"""
XLSX Skill Agent Example
------------------------
Simple agent that loads the xlsx skill and validates a workbook with formula checks.

Requirements:
- OPENROUTER_API_KEY in .env file
- xlsx skill installed locally, or XLSX_SKILL_PATH set explicitly
- LibreOffice available as `soffice` for formula recalculation
"""

# ruff: noqa: E402

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from zipfile import ZIP_DEFLATED, ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core import build_agent
from core.policies import AgentSpec, CodeActPolicy, SkillsPolicy

DEFAULT_SKILL_PATH = Path.home() / ".agents" / "skills" / "xlsx"
DEFAULT_WORKBOOK_PATH = Path("tmp") / "xlsx_skill_demo.xlsx"
COMMON_SOFFICE_PATHS = [
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    Path.home() / "Applications" / "LibreOffice.app" / "Contents" / "MacOS" / "soffice",
    Path("/opt/homebrew/bin/soffice"),
    Path("/usr/local/bin/soffice"),
]


def resolve_skill_path(explicit_path: str | None) -> Path:
    configured_path = explicit_path or os.getenv("XLSX_SKILL_PATH")
    skill_path = Path(configured_path).expanduser() if configured_path else DEFAULT_SKILL_PATH
    if not skill_path.exists():
        raise FileNotFoundError(
            "Could not find the xlsx skill. Set XLSX_SKILL_PATH or pass --skill-path. "
            f"Looked for: {skill_path}"
        )
    return skill_path.resolve()


def create_sample_workbook(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = {
        "[Content_Types].xml": dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
              <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
              <Default Extension="xml" ContentType="application/xml"/>
              <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
              <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
              <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
              <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
            </Types>
            """
        ),
        "_rels/.rels": dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
              <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
              <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
            </Relationships>
            """
        ),
        "docProps/app.xml": dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
              <Application>Agentic Runtime</Application>
            </Properties>
            """
        ),
        "docProps/core.xml": dedent(
            f"""\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
              <dc:creator>Agentic Runtime</dc:creator>
              <cp:lastModifiedBy>Agentic Runtime</cp:lastModifiedBy>
              <dcterms:created xsi:type="dcterms:W3CDTF">{created_at}</dcterms:created>
              <dcterms:modified xsi:type="dcterms:W3CDTF">{created_at}</dcterms:modified>
            </cp:coreProperties>
            """
        ),
        "xl/workbook.xml": dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets>
                <sheet name="Budget" sheetId="1" r:id="rId1"/>
              </sheets>
            </workbook>
            """
        ),
        "xl/_rels/workbook.xml.rels": dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
            </Relationships>
            """
        ),
        "xl/worksheets/sheet1.xml": dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>Item</t></is></c>
                  <c r="B1" t="inlineStr"><is><t>Amount</t></is></c>
                </row>
                <row r="2">
                  <c r="A2" t="inlineStr"><is><t>Rent</t></is></c>
                  <c r="B2"><v>1800</v></c>
                </row>
                <row r="3">
                  <c r="A3" t="inlineStr"><is><t>Utilities</t></is></c>
                  <c r="B3"><v>220</v></c>
                </row>
                <row r="4">
                  <c r="A4" t="inlineStr"><is><t>Groceries</t></is></c>
                  <c r="B4"><v>460</v></c>
                </row>
                <row r="5">
                  <c r="A5" t="inlineStr"><is><t>Total</t></is></c>
                  <c r="B5"><f>SUM(B2:B4)</f><v>2480</v></c>
                </row>
                <row r="6">
                  <c r="A6" t="inlineStr"><is><t>Emergency Fund (10%)</t></is></c>
                  <c r="B6"><f>B5*10%</f><v>248</v></c>
                </row>
              </sheetData>
            </worksheet>
            """
        ),
    }

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as workbook:
        for filename, content in files.items():
            workbook.writestr(filename, content)

    return path.resolve()


def configure_soffice_path(explicit_path: str | None) -> Path | None:
    configured_path = explicit_path or os.getenv("SOFFICE_BIN")
    candidates = []

    if configured_path:
        candidates.append(Path(configured_path).expanduser())

    discovered = shutil.which("soffice")
    if discovered:
        candidates.append(Path(discovered))

    candidates.extend(COMMON_SOFFICE_PATHS)

    for candidate in candidates:
        resolved_candidate = candidate.resolve()
        if not resolved_candidate.exists() or not os.access(resolved_candidate, os.X_OK):
            continue

        soffice_dir = str(resolved_candidate.parent)
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        if soffice_dir not in path_entries:
            os.environ["PATH"] = os.pathsep.join([soffice_dir, *path_entries])

        os.environ["SOFFICE_BIN"] = str(resolved_candidate)
        return resolved_candidate

    return None


def main(
    skill_path_arg: str | None,
    workbook_path_arg: str | None,
    prepare_only: bool,
    soffice_path_arg: str | None,
) -> None:
    workbook_path = create_sample_workbook(
        Path(workbook_path_arg).expanduser() if workbook_path_arg else DEFAULT_WORKBOOK_PATH
    )
    skill_path = resolve_skill_path(skill_path_arg)

    print(f"Workbook ready: {workbook_path}")
    print(f"Using xlsx skill: {skill_path}")

    if prepare_only:
        print(
            "Preparation complete. Re-run without --prepare-only to ask the agent to validate it."
        )
        return

    soffice_path = configure_soffice_path(soffice_path_arg)
    if soffice_path is None:
        print(
            "LibreOffice was not found. Install it, set SOFFICE_BIN, or pass --soffice-path "
            "to run the xlsx skill's recalculation step."
        )
        return

    print(f"Using soffice: {soffice_path}")

    spec = AgentSpec(
        name="xlsx_skill_agent",
        model_id="z-ai/glm-5",
        codeact=CodeActPolicy(enabled=False),
        skills=SkillsPolicy(enabled=True, paths=[str(skill_path)]),
    )
    agent = build_agent(spec)

    agent.print_response(
        f"""
        Use the xlsx skill to validate the workbook at {workbook_path}.

        1. Load the xlsx skill instructions first.
        2. Run the skill's recalc script on the workbook.
        3. Tell me the recalculation status, total formula count, and whether any Excel errors were found.
        4. Keep the answer to three short bullets.
        """,
        stream=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a workbook with the xlsx skill")
    parser.add_argument(
        "--skill-path",
        type=str,
        default=None,
        help="Override the xlsx skill location (default: ~/.agents/skills/xlsx)",
    )
    parser.add_argument(
        "--workbook-path",
        type=str,
        default=None,
        help="Override the generated workbook path (default: tmp/xlsx_skill_demo.xlsx)",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only create the workbook and print paths without calling the model",
    )
    parser.add_argument(
        "--soffice-path",
        type=str,
        default=None,
        help="Override the LibreOffice soffice binary path",
    )
    args = parser.parse_args()

    main(args.skill_path, args.workbook_path, args.prepare_only, args.soffice_path)
