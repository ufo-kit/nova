import os
import shutil
from nova import app


def copy(src_path, dst_path):
    def copytree(src, dst, symlinks=False, ignore=None):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                copytree(s, d, symlinks, ignore)
            else:
                if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                    shutil.copy2(s, d)

    app.logger.info("Copy data from {} to {}".format(src_path, dst_path))
    copytree(src_path, dst_path)
