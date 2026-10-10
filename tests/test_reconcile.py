import json
import subprocess

from code_intelligence import indexers, sync as sync_module
from code_intelligence.config import Config
from code_intelligence.github import Repository


def repo(name="sample", owner="upfera", branch="main"):
    return Repository(name, f"{owner}/{name}", f"git@github.com:{owner}/{name}.git",
                     f"https://github.com/{owner}/{name}", branch, False, False)


def test_repo_path_uses_owner_and_repo(tmp_path):
    config = Config({"github": {"organization": "upfera"}, "repositories": {"root": str(tmp_path)}})
    assert sync_module.repo_path(config, repo()) == tmp_path / "upfera" / "sample"


def test_sync_filters_exact_repository_allowlist(monkeypatch, tmp_path):
    config = Config({"github": {"organization": "upfera"}, "repositories": {"root": str(tmp_path)}})
    monkeypatch.setattr(sync_module, "list_repositories", lambda _: [repo(), repo("other")])
    calls = []
    def update(config, repository):
        calls.append(repository.name_with_owner)
        return tmp_path, "unchanged"
    monkeypatch.setattr(sync_module, "update", update)
    result = sync_module.sync(config, {"upfera/other"})
    assert calls == ["upfera/other"]
    assert len(result) == 1


def test_index_state_written_only_after_success(monkeypatch, tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(indexers, "STATE_FILE", state_path)
    monkeypatch.setattr(indexers, "repository_head", lambda _: "abc123")
    config = Config({"indexers": {"cbm": {"enabled": True, "command": "cbm"}}})
    def failed(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["cbm"])
    monkeypatch.setattr(indexers.subprocess, "run", failed)
    try:
        indexers.index_with_cbm(config, path, "upfera/sample")
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("indexing failure should propagate")
    assert not state_path.exists()


def test_index_state_skips_matching_head(monkeypatch, tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"github.com/upfera/sample": "abc123"}))
    monkeypatch.setattr(indexers, "STATE_FILE", state_path)
    monkeypatch.setattr(indexers, "repository_head", lambda _: "abc123")
    config = Config({"indexers": {"cbm": {"enabled": True}}})
    assert indexers.index_with_cbm(config, path, "upfera/sample") is False
