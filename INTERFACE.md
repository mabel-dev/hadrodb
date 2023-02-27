

# OPEN COLLECTION
HadroDB(collection=queried_collection)

# GET DOCUMENT FROM COLLECTION
document = hadro[id[, id ...]]
document = hardo.get(id)

# SET DOCUMENT IN COLLECTION
hadro[id] = document
hadro.set(id, document)
id = hardo.add(document)

# DELETE DOCUMENT FROM COLLECTION
del hadro[id]
hadro.del(id)

# CONTAINMENT
id in hadro
hadro.contains(id)

# GET KEYS IN COLLECTION
hadro.ids()

# GET COLLECTION SIZE
len(hadro)

# FILTER COLLECTION
filtered_collection = hadro.where(predicate)

-------- NOT IMPLEMENTED

# INDEXES
hadro.indexes.list()
hadro.indexes.add(index_name, [fields][, type="b+tree"])
hadro.indexes.remove(index_name)
hadro.indexes.rebuild(index_name)

# BATCH
with hadro.transaction() as batch:
    batch.add()
    batch.add()
