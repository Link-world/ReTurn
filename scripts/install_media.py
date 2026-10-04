"""Install the exact companion media archive after upstream terms acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accept-terms', action='store_true', help='Confirm agreement to THIRD_PARTY_MEDIA.md')
    args = parser.parse_args()
    if not args.accept_terms:
        parser.error('Read THIRD_PARTY_MEDIA.md and pass --accept-terms to confirm agreement.')
    root = args.root.resolve()
    checks = json.loads((root / 'data/media_checksums.json').read_text())
    if not checks:
        raise ValueError('Empty media checksum manifest')
    for name in checks:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or path.parts[:2] != ('data', 'media'):
            raise ValueError('Unsafe manifest path')
    with zipfile.ZipFile(args.archive) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive members')
        # Validate every expected byte before changing any installed media.
        for name, expected in checks.items():
            info = archive.getinfo(name)
            if info.file_size > 512 * 1024 * 1024:
                raise ValueError('Unexpectedly large media member')
            with archive.open(name) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(stream.read()).hexdigest()
            if actual != expected:
                raise ValueError('Checksum mismatch: ' + name)
        for name in checks:
            target = root / name
            if not target.resolve().is_relative_to(root):
                raise ValueError('Destination escapes repository')
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
                temp_path = Path(temp.name)
                try:
                    with archive.open(name) as stream:
                        while chunk := stream.read(1024 * 1024):
                            temp.write(chunk)
                    temp.close()
                    os.replace(temp_path, target)
                finally:
                    temp_path.unlink(missing_ok=True)
    print(f'Installed and verified {len(checks)} media files.')


if __name__ == '__main__':
    main()
