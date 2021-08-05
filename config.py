import numpy as np

from glue.core.component import CategoricalComponent
from glue.core.component_id import ComponentID
from glue.core.data import BaseCartesianData, Data
from glue.utils import view_shape

import ete3
import viewer
from glue import qglue
from glue.core.data_factories.helpers import has_extension
from glue.config import data_factory, link_function, link_helper
from glue.core.link_helpers import LinkCollection


# linking info
# http://docs.glueviz.org/en/stable/developer_guide/linking.html
def tree_process(fname, is_string=False):
    import os

    result = Data()

    if is_string:
        result.label = "tree data from dendrogram"  # TODO clean this up
    else:
        result.label = "tree data[%s]" % os.path.basename(fname)

    # based on http://etetoolkit.org/docs/latest/tutorial/tutorial_trees.html#reading-and-writing-newick-trees
    # you probably don't want 0, because support values are strange
    tree = ete3.Tree(fname, format=1)
    result.tdata = tree

    result.tree_component_id = "tree nodes %s" % result.uuid

    # ignore nameless nodes as they cannot be indexed
    names = [n.name for n in tree.traverse("postorder") if n.name != ""]

    allint = all(name.isnumeric() for name in names)

    nodes = np.array([(int(name) if allint else name) for name in names])

    for node in tree.traverse("postorder"):
        if allint:
            node.idx = int(node.name) if node.name != "" else None
        else:
            node.idx = node.name

    # TODO if they are all ints, make them ints
    print(nodes)

    result.add_component(CategoricalComponent(nodes), result.tree_component_id)

    return result


@data_factory("Newick tree loader", identifier=has_extension("tre nw"), priority=1000)
def read_newick(fname):
    # TODO how to give user option to choose format?
    return tree_process(fname)


@data_factory("Tommy Dendogram Viewer")
def read_dendro(fname):
    def to_newick_str(dg):
        return "(" + ",".join(x.newick for x in dg.trunk) + ");"

    from astrodendro import Dendrogram

    dg = Dendrogram.load_from(fname)

    tree = tree_process(to_newick_str(dg), is_string=True)

    im = Data(
        intensity=dg.data, structure=dg.index_map, label="{} dendrogram".format(fname)
    )

    im.join_on_key(tree, "structure", tree.tree_component_id)

    return [tree, im]


# https://github.com/glue-viz/glue/blob/241edb32ab6f4a82adf02ef3711c16342fd214ed/glue/plugins/dendro_viewer/qt/data_viewer.py#L92


@link_helper(category="Tree Viewer")
class Link_Index_By_Value(LinkCollection):
    # inherit from linkCollection to skip this line https://github.com/glue-viz/glue/blob/5a878451a1636b141a687a482239a37287a32198/glue/config.py#L790
    cid_independent = False

    display = "Link By Value"
    description = "WARNING: once you close this dialog, this link can only be removed by restarting glue"

    labels1 = ["first value column"]
    labels2 = ["second value column"]

    _links = []

    def __init__(self, *args, cids1=None, cids2=None, data1=None, data2=None):
        # only support linking by one value now, even tho link_by_value supports multiple
        assert len(cids1) == 1
        assert len(cids2) == 1

        self.data1 = data1
        self.data2 = data2
        self.cids1 = cids1
        self.cids2 = cids2

        data1.join_on_key(data2, cids1[0], cids2[0])


# based on https://sourcegraph.com/github.com/glue-viz/glue/-/blob/glue/plugins/coordinate_helpers/link_helpers.py?L42:33
