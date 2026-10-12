"""Build only the independent demo; never publish the repository root."""
from pathlib import Path
import argparse
import shutil

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = {
    'index.html': 'demo.html',
    'style.css': 'style.css',
    'js/demo-app.js': 'js/demo-app.js',
    'js/domain.js': 'js/domain.js',
    'js/register-form.js': 'js/register-form.js',
    'js/charts.js': 'js/charts.js',
    'js/comparisons.js': 'js/comparisons.js',
    'js/storage.js': 'js/storage.js',
    'vendor/chart.umd.js': 'vendor/chart.umd.js',
    'vendor/LICENSE-Chart.js.md': 'vendor/LICENSE-Chart.js.md',
}


def build_site(destination, root=ROOT):
    root = Path(root).resolve()
    destination = Path(destination).resolve()
    if destination == root or destination in root.parents:
        raise ValueError('La salida debe ser una carpeta independiente del código.')
    if destination.exists():
        existing = {str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()}
        if existing - set(PUBLIC_FILES):
            raise ValueError('La salida contiene archivos ajenos a la demo; usa una carpeta vacía.')
    for output, source in PUBLIC_FILES.items():
        source_path = root / source
        if source_path.is_symlink() or root not in source_path.resolve().parents:
            raise ValueError('La entrada debe ser un archivo público del proyecto.')
        output_path = destination / output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.is_symlink():
            raise ValueError('La salida no admite enlaces simbólicos.')
        shutil.copyfile(source_path, output_path)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    args = parser.parse_args()
    output = build_site(args.output)
    print(f'Demo estática preparada: {output.name} ({len(PUBLIC_FILES)} archivos públicos)')
