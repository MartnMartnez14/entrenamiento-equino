from pathlib import Path
import re
import pytest
from scripts.build_site import ROOT, PUBLIC_FILES, build_site


def test_static_package_excludes_server_and_private_data(tmp_path):
    out = build_site(tmp_path / 'site')
    actual = {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}
    assert actual == set(PUBLIC_FILES)
    assert not any('instance' in name or name.endswith('.py') for name in actual)
    html = (out / 'index.html').read_text()
    assert 'js/demo-app.js' in html
    assert 'js/app.js' not in html
    assert 'datos ficticios' in html
    assert 'entrenamiento-equino-demo' in (out / 'js/storage.js').read_text()
    for name in actual:
        if name.endswith('.js') and not name.startswith('vendor/'):
            assert '/api/' not in (out / name).read_text()


def test_relative_assets_and_modules_resolve_under_project_path(tmp_path):
    out = build_site(tmp_path / 'entrenamiento-equino')
    html = (out / 'index.html').read_text()
    for link in re.findall(r'(?:src|href)="([^"]+)"', html):
        if link.startswith('#') or '://' in link:
            continue
        assert not link.startswith('/')
        assert (out / link).is_file(), link
    for js in (out / 'js').glob('*.js'):
        for module in re.findall(r"from ['\"]([^'\"]+)['\"]", js.read_text()):
            assert module.startswith('./')
            assert (js.parent / module).is_file()


def test_build_rejects_repository_root_and_contaminated_output(tmp_path):
    with pytest.raises(ValueError):
        build_site(ROOT)
    contaminated = tmp_path / 'site'
    contaminated.mkdir()
    (contaminated / 'private.sqlite').write_text('test-only')
    with pytest.raises(ValueError):
        build_site(contaminated)
    assert (contaminated / 'private.sqlite').read_text() == 'test-only'
