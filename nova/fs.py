import os


class Filesystem(object):
    def __init__(self, app):
        self.path = os.path.abspath(app.config.get('NOVA_ROOT_PATH', '.'))

    def get_entries(self, dataset, path):
        path = path if path else '.'
        path = os.path.join(self.path, dataset.path, path)
        try:
            return (os.path.join(path, e) for e in os.listdir(path))
        except OSError:
            return []

    def get_files(self, dataset, path):
        return [(os.path.basename(e), os.stat(e).st_size) for e in self.get_entries(dataset, path) if not os.path.isdir(e)]

    def get_dirs(self, dataset, path):
        return [os.path.basename(e) for e in self.get_entries(dataset, path) if os.path.isdir(e)]

    def get_statistics(self, datasets):
        num_files = 0
        total_size = 0

        for dataset in datasets:
            for root, dirs, files in os.walk(os.path.join(self.path, dataset.path)):
                num_files += len(files)

                for filename in files:
                    path = os.path.join(root, filename)
                    total_size += os.stat(path).st_size

        return num_files, total_size

    def path_of(self, dataset):
        return os.path.join(self.path, dataset.path)
