import os
import io
import tarfile


def create_tar(path):
    fileobj = io.BytesIO()
    tar = tarfile.open(mode='w:gz', fileobj=fileobj)

    for root, dirs, files in os.walk(path):
        for fn in files:
            p = os.path.join(root, fn)

            # remove one more character to remove trailing slash
            arcname = p[p.find(path)+len(path)+1:]

            if not arcname.startswith('.nova'):
                tar.add(p, arcname=arcname)

    tar.close()
    return fileobj


def extract_tar(fileobj, path):
    fileobj.seek(0)
    tar = tarfile.open(mode='r:gz', fileobj=fileobj)
    tar.extractall(path)
    tar.close()
