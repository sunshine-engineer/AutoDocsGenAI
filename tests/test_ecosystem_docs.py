import json

from scripts.ecosystem_docs import compare_versions, extract_api, release_versions


def test_static_reference_preserves_signatures_methods_and_exports():
    api = extract_api('''"""Module docs."""
from .impl import Agent as PublicAgent
__all__ = ["PublicAgent", "Worker"]
class Worker(Base):
    """Worker docs."""
    async def run(self, value: int = 3) -> str:
        """Run docs."""
        pass
    def _hidden(self): pass
    def __call__(self): pass
''')
    assert api["declared_all"] == ["PublicAgent", "Worker"]
    assert api["imports"][0]["origin"] == ".impl.Agent"
    assert [item["name"] for item in api["symbols"]] == [
        "Worker",
        "Worker.run",
        "Worker.__call__",
    ]
    assert api["symbols"][1]["signature"] == "async def run(self, value: int=3) -> str"
    assert api["symbols"][1]["docstring"] == "Run docs."


def test_versions_skip_prereleases_yanked_and_choose_minor_heads():
    metadata = {
        "releases": {
            version: [{"yanked": yanked}]
            for version, yanked in [
                ("1.2.0", False),
                ("1.2.3", False),
                ("1.1.5", False),
                ("1.0.1", False),
                ("2.0.0rc1", False),
                ("2.0.0", True),
            ]
        }
    }
    assert release_versions(metadata) == ["1.2.3", "1.1.5", "1.0.1"]


def test_api_diff_does_not_report_movement_as_confirmed_breakage(tmp_path):
    for version, source in [
        ("1.0.0", "def old(a): pass"),
        ("2.0.0", "def new(a): pass"),
    ]:
        target = tmp_path / "example" / version
        target.mkdir(parents=True)
        (target / "manifest.json").write_text(
            json.dumps({"modules": {"example": extract_api(source)}})
        )
    change = compare_versions(tmp_path, "example", ["2.0.0", "1.0.0"])[0]
    assert change["removed_declarations"] == ["example.old"]
    assert change["added_declarations"] == ["example.new"]
    assert "not proven" in change["interpretation"]


def test_verified_wheel_emits_reference_and_preserves_license(tmp_path, monkeypatch):
    import hashlib
    import io
    import zipfile

    import scripts.ecosystem_docs as docs

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "example/__init__.py",
            '"""Source module."""\ndef run(x: int) -> int:\n    """Return x."""\n    return x\n',
        )
        archive.writestr("example-1.0.0.dist-info/licenses/LICENSE", "MIT example")
    payload = buffer.getvalue()
    metadata: dict = {
        "info": {"version": "1.0.0"},
        "urls": [
            {
                "packagetype": "bdist_wheel",
                "filename": "example-1.0.0-py3-none-any.whl",
                "url": "https://files.pythonhosted.org/example.whl",
                "digests": {"sha256": hashlib.sha256(payload).hexdigest()},
            }
        ],
    }
    monkeypatch.setattr(
        docs,
        "fetch",
        lambda url: json.dumps(metadata).encode() if url.endswith("/json") else payload,
    )
    result = docs.build_release("example", "1.0.0", tmp_path)
    assert result["module_count"] == 1
    assert result["symbol_count"] == 1
    assert "Return x." in (tmp_path / "example/1.0.0/example.md").read_text()
    assert (tmp_path / "example/1.0.0/licenses/LICENSE").read_text() == "MIT example"
    metadata["urls"][0]["digests"]["sha256"] = "0" * 64
    import pytest

    with pytest.raises(ValueError, match="hash mismatch"):
        docs.build_release("example", "1.0.0", tmp_path / "bad")


def test_matrix_assessment_rejects_unrelated_failures_and_missing_checks(tmp_path):
    from scripts.ecosystem_matrix import assess

    result = [{"label": "legacy", "install_exit": 0, "probe_exit": 0}]
    (tmp_path / "legacy.json").write_text(json.dumps({"checks": []}))
    assert any("incomplete" in issue for issue in assess(result, tmp_path))
    (tmp_path / "incompatible-install.log").write_text("Network connection failed")
    issues = assess([{"label": "incompatible", "install_exit": 1}], tmp_path)
    assert any("unrecognized reason" in issue for issue in issues)
