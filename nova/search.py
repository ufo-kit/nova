from nova import db, es
from nova.models import Dataset, Permission


def insert(dataset):
    permission = Permission.query.filter(Dataset.id == dataset.id).first()
    tokenized = dataset.name.lower().replace('_', ' ')
    body = dict(name=dataset.name, tokenized=tokenized,
                owner=permission.owner.name, description=dataset.description,
                collection=dataset.collection.name)
    es.create(index='datasets', doc_type='dataset', body=body)

