import json
import sqlite3

import pytest

from app.database.db import current_db_file
from app.services.category_service import CategoryService
from app.services.dto import PromptInput
from app.services.io_service import ImportError_, IOService
from app.services.prompt_service import PromptService, parse_tags
from app.services.settings_service import Settings
from app.utils.jalali import gregorian_to_jalali
from app.utils.variables import fill_variables, find_variables, line_direction

FA = "سلام دنیا! این یک پرامپت فارسی است؛ «نیم‌فاصله» و ۱۲۳ و ي ك"


def test_default_categories_seeded_once(vault):
    names = [c.name for c in CategoryService.list()]
    assert len(names) == 10 and names[0] == "Programming" and names[-1] == "Other"
    for c in CategoryService.list():
        CategoryService.delete(c.id)
    from app.database.db import init_db
    init_db()  # restart: must NOT re-seed
    assert CategoryService.list() == []


def test_crud_and_persian_roundtrip(vault):
    cat = CategoryService.list()[0]
    p = PromptService.create(PromptInput(title="  عنوان   فارسی ", content=FA, description="توضیح",
                                         category_id=cat.id, tags=["تگ", "tag", "TAG"]))
    got = PromptService.get(p.id)
    assert got.title == "عنوان فارسی" and got.content == FA and got.description == "توضیح"
    assert sorted(got.tags) == ["tag", "تگ"] and got.category_name == "Programming"
    up = PromptService.update(p.id, PromptInput(title="New", content="x" * 10, is_favorite=True))
    assert up.is_favorite and up.updated_at >= up.created_at and up.category_id is None
    dup = PromptService.duplicate(p.id)
    assert dup.id != p.id and dup.title.endswith("(copy)")
    PromptService.delete(p.id)
    assert PromptService.get(p.id) is None
    with pytest.raises(ValueError):
        PromptService.create(PromptInput(title="   "))


def test_search_filters_and_sort(vault):
    c = CategoryService.list()
    a = PromptService.create(PromptInput(title="Alpha", content="write python code", category_id=c[0].id, tags=["dev"]))
    b = PromptService.create(PromptInput(title="Beta", content="سلام جهان", description="فارسی", is_favorite=True))
    g = PromptService.create(PromptInput(title="Gamma 100%", content="a_b", is_archived=True))
    s = lambda **k: [p.title for p in PromptService.search(**k)]
    assert s(query="python") == ["Alpha"]                 # content
    assert s(query="alp") == ["Alpha"]                    # title
    assert s(query="dev") == ["Alpha"]                    # tag
    assert s(query="جهان") == ["Beta"] and s(query="فارسی") == ["Beta"]
    assert s(query="python code") == ["Alpha"]            # multi-term AND
    assert s(category_id=c[0].id) == ["Alpha"]
    assert s(favorites_only=True) == ["Beta"]
    assert s() == ["Beta", "Alpha"] and s(sort="oldest") == ["Alpha", "Beta"]
    assert s(archived=True) == ["Gamma 100%"] and len(s(archived=None)) == 3
    assert s(query="%", archived=None) == ["Gamma 100%"]   # wildcard escaped
    assert s(query="_", archived=None) == ["Gamma 100%"]
    PromptService.mark_used(a.id)
    assert s(sort="recent")[0] == "Alpha"
    st = PromptService.stats()
    assert st["total"] == 2 and st["favorites"] == 1 and st["archived"] == 1 and st["used"] == 1
    assert [p.title for p in PromptService.recently_used()] == ["Alpha"]


def test_category_management(vault):
    c = CategoryService.create("  My   Cat ")
    assert c.name == "My Cat"
    with pytest.raises(ValueError):
        CategoryService.create("my cat")
    CategoryService.rename(c.id, "Renamed")
    p = PromptService.create(PromptInput(title="t", category_id=c.id))
    CategoryService.delete(c.id)
    assert PromptService.get(p.id).category_name == "Other"
    CategoryService.delete(CategoryService.other_id())
    assert PromptService.get(p.id).category_id is None


def test_variables():
    t = "Explain {{topic}} in {{ language }} as {{role}}. {{topic}} again {{موضوع}}"
    assert find_variables(t) == ["topic", "language", "role", "موضوع"]
    assert fill_variables(t, {"topic": "AI", "language": ""}) == \
        "Explain AI in {{ language }} as {{role}}. AI again {{موضوع}}"
    assert line_direction("سلام hello") == "rtl" and line_direction("hello سلام") == "ltr"
    assert parse_tags("a، b, a;c") == ["a", "b", "c"]


def test_json_export_import_roundtrip(vault, tmp_path):
    PromptService.create(PromptInput(title="فارسی", content=FA, tags=["x"], category_id=CategoryService.list()[1].id))
    PromptService.create(PromptInput(title="Eng", content="hello", is_archived=True))
    out = tmp_path / "e.json"
    assert IOService.export_json(out) == 2
    raw = out.read_text(encoding="utf-8")
    assert "سلام دنیا" in raw and "\\u" not in raw       # real UTF-8, not escaped
    r = IOService.import_json(out)                       # same data -> all duplicates
    assert (r.imported, r.duplicates) == (0, 2) and r.safety_backup and r.safety_backup.exists()
    for p in PromptService.search(archived=None):
        PromptService.delete(p.id)
    r = IOService.import_json(out)
    assert r.imported == 2
    got = PromptService.search(query="فارسی")[0]
    assert got.content == FA and got.tags == ["x"] and got.category_name == "Software Development"


def test_import_validation(vault, tmp_path):
    def run(payload, raw=None):
        f = tmp_path / "i.json"
        f.write_text(raw if raw is not None else json.dumps(payload), encoding="utf-8")
        return IOService.import_json(f)
    for bad, code in [(None, "import_not_json"), ({"prompts": "x"}, "import_bad_schema"),
                      ({"prompts": [1, {"title": ""}]}, "import_no_valid")]:
        with pytest.raises(ImportError_) as e:
            run(bad, raw="{oops" if bad is None else None)
        assert e.value.code == code
    r = run({"prompts": [{"title": "ok", "content": "c", "tags": ["t", 5], "category": "NewCat"}, {"nope": 1},
                         {"title": "bad", "content": 5}]})
    assert (r.imported, r.invalid, r.categories_created) == (1, 2, 1)
    assert len(run([{"title": "listform"}]).errors) == 0   # bare list accepted


def test_backup_restore(vault, tmp_path):
    p = PromptService.create(PromptInput(title="keep", content=FA))
    bk = tmp_path / "b.db"
    IOService.backup_database(bk)
    PromptService.delete(p.id)
    PromptService.create(PromptInput(title="other"))
    safety = IOService.restore_database(bk)
    assert [x.title for x in PromptService.search()] == ["keep"] and safety.exists()
    junk = tmp_path / "junk.db"
    junk.write_bytes(b"not a database at all" * 10)
    with pytest.raises(ImportError_):
        IOService.restore_database(junk)
    other = tmp_path / "other.db"
    sqlite3.connect(other).executescript("create table x(a);")
    with pytest.raises(ImportError_) as e:
        IOService.restore_database(other)
    assert e.value.code == "restore_not_vault"
    assert PromptService.search()[0].title == "keep"       # untouched by failed restores


def test_markdown_txt_export(vault, tmp_path):
    p = PromptService.create(PromptInput(title="T", content="code ```py``` here", description="d", tags=["a"]))
    md, tx = tmp_path / "a.md", tmp_path / "a.txt"
    IOService.export_text(md, [p], "md")
    IOService.export_text(tx, [p], "txt")
    assert "````text" in md.read_text(encoding="utf-8") and "# T" in md.read_text(encoding="utf-8")
    assert "Tags: a" in tx.read_text(encoding="utf-8")


def test_settings_validation(vault):
    s = Settings()
    assert s.get("language") == "fa"
    s.set("language", "en")
    with pytest.raises(ValueError):
        s.set("theme", "neon")
    assert Settings().get("language") == "en"            # persisted
    (vault / "settings.json").write_text('{"font_size": 99, "theme": "light"}')
    s2 = Settings()
    assert s2.get("font_size") == 13 and s2.get("theme") == "light"


def test_jalali():
    assert gregorian_to_jalali(2026, 3, 21) == (1405, 1, 1)
    assert gregorian_to_jalali(2024, 3, 20) == (1403, 1, 1)
    assert gregorian_to_jalali(2000, 1, 1) == (1378, 10, 11)
