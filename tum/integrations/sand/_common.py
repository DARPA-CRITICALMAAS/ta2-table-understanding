from __future__ import annotations

from sm.prelude import I

from tum.dag import IdentObj, hash_dict


def set_table(table: I.ColumnBasedTable) -> IdentObj[I.ColumnBasedTable]:
    return IdentObj(key=hash_dict(table.to_dict()), value=table)
