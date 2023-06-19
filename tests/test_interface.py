import os
import shutil
import sys
import time

sys.path.insert(1, os.path.join(sys.path[0], ".."))

from hadro import HadroDB  # isort: skip


TEST_COLLECTION = "test_123"


def create_doc(docs):
    docid = str(time.monotonic_ns())
    doc = {"document": docid}
    docs[docid] = doc
    return docid, doc


def test_interface():
    # initialize the dataset
    if os.path.exists(TEST_COLLECTION):  # pragma: no cover
        shutil.rmtree(TEST_COLLECTION, ignore_errors=True)

    # create a copy of the docs for us to compare against
    comparision_set_of_docs = {}

    # OPEN COLLECTION
    hadro = HadroDB(TEST_COLLECTION)

    # SET DOCUMENT IN COLLECTION
    # subscript syntax
    docid, doc = create_doc(comparision_set_of_docs)
    hadro.append(doc)

    docid, doc = create_doc(comparision_set_of_docs)
    # set syntax
    hadro.append(doc)

    # add syntax
    docid = hadro.append(doc)
    comparision_set_of_docs[docid] = doc

    # GET DOCUMENT FROM COLLECTION
    # subscript, single doc syntax
    #    doc = hadro[docid]
    #    assert doc == comparision_set_of_docs[docid]

    # subscript, list syntax
    #    list_of_docs = hadro[comparision_set_of_docs.keys()]
    #    assert len(list_of_docs) == len(comparision_set_of_docs)

    # get syntax
    #    doc = hadro.get(docid)
    #    assert doc == comparision_set_of_docs[docid]

    # GET COLLECTION SIZE
    #    assert len(hadro) == len(comparision_set_of_docs)

    # GET KEYS IN COLLECTION
    #    keys = hadro.keys()
    #    assert len(keys) == len(comparision_set_of_docs)
    #    for key in keys:
    #        assert hadro[key] == comparision_set_of_docs[key]

    """
# DELETE DOCUMENT FROM COLLECTION
del hadro[id]
hadro.del(id[, id...])

# CONTAINMENT
id in hadro
hadro.contains(id[, id ...])

# FILTER COLLECTION
filtered_collection = hadro.where(predicate)


"""

    hadro.close()

    # tidy up
    if os.path.exists(TEST_COLLECTION):  # pragma: no cover
        shutil.rmtree(TEST_COLLECTION, ignore_errors=True)


test_interface()
